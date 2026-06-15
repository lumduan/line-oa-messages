"""Unit tests for the persistence/service layer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from src import services
from src.config import settings
from src.line import client
from src.models import LineUser, Message


def test_get_or_create_user_is_idempotent(session: Session) -> None:
    first = services.get_or_create_user(session, "Uabc", fetch_profile=False)
    second = services.get_or_create_user(session, "Uabc", fetch_profile=False)
    assert first.id == second.id
    assert len(session.scalars(select(LineUser)).all()) == 1


def test_get_or_create_user_fetches_profile(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "line_channel_access_token", "tok")

    def fake_profile(user_id: str) -> object:
        return SimpleNamespace(
            display_name="Alice", picture_url="http://x/p.png", status_message="hi"
        )

    monkeypatch.setattr(client, "get_profile", fake_profile)
    user = services.get_or_create_user(session, "Uprofile")
    assert user.display_name == "Alice"
    assert user.picture_url == "http://x/p.png"
    assert user.status_message == "hi"


def test_profile_fetch_failure_does_not_block(
    session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "line_channel_access_token", "tok")

    def boom(user_id: str) -> object:
        raise RuntimeError("network down")

    monkeypatch.setattr(client, "get_profile", boom)
    user = services.get_or_create_user(session, "Ufail")
    assert user.line_user_id == "Ufail"
    assert user.display_name is None


def test_persist_inbound_event_with_plain_object(session: Session) -> None:
    event = SimpleNamespace(
        type="message",
        webhook_event_id="e-1",
        reply_token="rt-1",
        source=SimpleNamespace(type="user", user_id="Uxyz", group_id=None, room_id=None),
        message=SimpleNamespace(type="text", id="m-1", text="hi"),
    )
    message = services.persist_inbound_event(session, event, raw_body="{}")
    assert message is not None
    assert message.text == "hi"
    assert message.message_type == "text"
    assert message.line_message_id == "m-1"


def test_record_reply_links_to_message(session: Session) -> None:
    user = services.get_or_create_user(session, "Ureply", fetch_profile=False)
    message = Message(user_id=user.id, message_type="text", text="hi")
    session.add(message)
    session.flush()

    reply = services.record_reply(session, text="hello back", kind="reply", message_id=message.id)
    assert reply.message_id == message.id
    assert reply.kind == "reply"


def test_list_messages_newest_first(session: Session) -> None:
    user = services.get_or_create_user(session, "Ulist", fetch_profile=False)
    session.add(Message(user_id=user.id, message_type="text", text="first"))
    session.add(Message(user_id=user.id, message_type="text", text="second"))
    session.commit()

    rows = services.list_messages(session=session)
    assert len(rows) == 2
    assert rows[0]["text"] == "second"
    assert rows[0]["user"] == "Ulist"
    assert set(rows[0].keys()) == {"id", "user", "type", "text", "received"}
