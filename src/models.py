"""SQLAlchemy 2.0 typed ORM models: users, raw events, messages, replies."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db import Base


def _utcnow() -> datetime:
    """Naive UTC timestamp (SQLite has no native tz-aware datetime)."""
    return datetime.now(UTC).replace(tzinfo=None)


class LineUser(Base):
    """A LINE user we have seen (enriched from the profile API when possible)."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_user_id: Mapped[str] = mapped_column(unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(default=None)
    picture_url: Mapped[str | None] = mapped_column(default=None)
    status_message: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    messages: Mapped[list[Message]] = relationship(back_populates="user")


class Event(Base):
    """Every inbound webhook event, stored raw for auditing/debugging."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    line_event_type: Mapped[str] = mapped_column(index=True)
    webhook_event_id: Mapped[str | None] = mapped_column(unique=True, default=None)
    source_type: Mapped[str | None] = mapped_column(default=None)
    source_id: Mapped[str | None] = mapped_column(default=None)
    raw_json: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(default=_utcnow)


class Message(Base):
    """An inbound message extracted from a ``message`` event."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id"), default=None)
    line_message_id: Mapped[str | None] = mapped_column(unique=True, default=None)
    message_type: Mapped[str] = mapped_column(default="text")
    text: Mapped[str | None] = mapped_column(Text, default=None)
    reply_token: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    user: Mapped[LineUser] = relationship(back_populates="messages")


class Reply(Base):
    """An outbound message we sent (reply or push)."""

    __tablename__ = "replies"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), default=None)
    to_user_id: Mapped[str | None] = mapped_column(default=None)
    kind: Mapped[str] = mapped_column(default="reply")  # "reply" | "push"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
