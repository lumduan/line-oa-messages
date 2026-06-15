"""Persistence orchestration — pure-ish functions over a SQLAlchemy ``Session``.

These functions contain no FastAPI/NiceGUI imports so they are trivially testable.
The only external dependency is :mod:`src.line.client`, which is mocked in tests.
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.db import session_scope
from src.line import client
from src.models import Event, LineUser, Message, Reply

logger = logging.getLogger(__name__)


def _event_to_json(event: object) -> str:
    """Best-effort JSON serialization of an SDK webhook event."""
    for attr in ("to_json", "model_dump_json"):
        fn = getattr(event, attr, None)
        if callable(fn):
            try:
                result = fn()
            except TypeError:
                continue
            if isinstance(result, str):
                return result
    to_dict = getattr(event, "to_dict", None)
    if callable(to_dict):
        return json.dumps(to_dict(), default=str, ensure_ascii=False)
    return json.dumps(str(event), ensure_ascii=False)


def _source_id(source: object) -> str | None:
    """Return the most specific source id (group/room/user)."""
    for attr in ("group_id", "room_id", "user_id"):
        value = getattr(source, attr, None)
        if value:
            return str(value)
    return None


def get_or_create_user(
    session: Session,
    line_user_id: str,
    *,
    fetch_profile: bool = True,
) -> LineUser:
    """Return the stored user, creating it (and fetching its profile) if new."""
    user = session.scalar(select(LineUser).where(LineUser.line_user_id == line_user_id))
    if user is not None:
        return user

    display_name = picture_url = status_message = None
    if fetch_profile and settings.line_channel_access_token:
        try:
            profile = client.get_profile(line_user_id)
            display_name = getattr(profile, "display_name", None)
            picture_url = getattr(profile, "picture_url", None)
            status_message = getattr(profile, "status_message", None)
        except Exception:  # noqa: BLE001 — profile lookup must never block ingestion
            logger.warning("could not fetch profile for %s", line_user_id, exc_info=True)

    user = LineUser(
        line_user_id=line_user_id,
        display_name=display_name,
        picture_url=picture_url,
        status_message=status_message,
    )
    session.add(user)
    session.flush()
    return user


def persist_inbound_event(session: Session, event: object, *, raw_body: str) -> Message | None:
    """Store a webhook event (idempotently) and, if it carries a message, the message.

    Returns the newly created :class:`Message` for a fresh message event, else ``None``
    (non-message events, or a redelivered event we have already stored).
    """
    del raw_body  # event is serialized individually; the raw body is not stored per-event

    webhook_event_id = getattr(event, "webhook_event_id", None)
    if webhook_event_id:
        existing = session.scalar(select(Event).where(Event.webhook_event_id == webhook_event_id))
        if existing is not None:
            return None

    source = getattr(event, "source", None)
    event_row = Event(
        line_event_type=str(getattr(event, "type", "unknown")),
        webhook_event_id=webhook_event_id,
        source_type=getattr(source, "type", None),
        source_id=_source_id(source),
        raw_json=_event_to_json(event),
    )
    session.add(event_row)
    session.flush()

    message = getattr(event, "message", None)
    user_line_id = getattr(source, "user_id", None)
    if message is None or not user_line_id:
        return None

    user = get_or_create_user(session, str(user_line_id))
    message_row = Message(
        user_id=user.id,
        event_id=event_row.id,
        line_message_id=getattr(message, "id", None),
        message_type=str(getattr(message, "type", "text")),
        text=getattr(message, "text", None),
        reply_token=getattr(event, "reply_token", None),
    )
    session.add(message_row)
    session.flush()
    return message_row


def record_reply(
    session: Session,
    *,
    text: str,
    kind: str = "reply",
    message_id: int | None = None,
    to_user_id: str | None = None,
) -> Reply:
    """Store an outbound message we sent (reply or push)."""
    reply = Reply(text=text, kind=kind, message_id=message_id, to_user_id=to_user_id)
    session.add(reply)
    session.flush()
    return reply


def _serialize_messages(session: Session, limit: int) -> list[dict[str, object]]:
    stmt = select(Message).order_by(Message.id.desc()).limit(limit)
    rows: list[dict[str, object]] = []
    for message in session.scalars(stmt):
        user = message.user
        rows.append(
            {
                "id": message.id,
                "user": (user.display_name or user.line_user_id) if user else "?",
                "type": message.message_type,
                "text": message.text or "",
                "received": message.created_at.isoformat(sep=" ", timespec="seconds"),
            }
        )
    return rows


def list_messages(limit: int = 200, session: Session | None = None) -> list[dict[str, object]]:
    """Return recent inbound messages (newest first) as dashboard-ready dicts."""
    if session is not None:
        return _serialize_messages(session, limit)
    with session_scope() as scoped:
        return _serialize_messages(scoped, limit)
