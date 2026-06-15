"""End-to-end persistence: posting webhook deliveries creates the right rows."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.models import Event, LineUser, Message, Reply

from tests.conftest import make_event_body, make_follow_body, sign


def _post(client: TestClient, body: bytes) -> None:
    resp = client.post("/line/webhook", content=body, headers={"x-line-signature": sign(body)})
    assert resp.status_code == 200


def test_text_message_creates_event_user_message_reply(
    webhook_client: TestClient, session: Session
) -> None:
    _post(webhook_client, make_event_body(text="hello world"))

    events = session.scalars(select(Event)).all()
    users = session.scalars(select(LineUser)).all()
    messages = session.scalars(select(Message)).all()
    replies = session.scalars(select(Reply)).all()

    assert len(events) == 1
    assert events[0].line_event_type == "message"
    assert len(users) == 1
    assert len(messages) == 1
    assert messages[0].text == "hello world"
    assert messages[0].line_message_id == "msg-1"
    assert messages[0].reply_token == "rt-1"
    # AUTO_REPLY is on -> one echo reply was recorded.
    assert len(replies) == 1
    assert replies[0].kind == "reply"
    assert replies[0].text == "echo: hello world"


def test_duplicate_webhook_event_id_is_idempotent(
    webhook_client: TestClient, session: Session
) -> None:
    body = make_event_body(webhook_event_id="dup-1")
    _post(webhook_client, body)
    _post(webhook_client, body)

    assert len(session.scalars(select(Event)).all()) == 1
    assert len(session.scalars(select(Message)).all()) == 1


def test_follow_event_stores_event_without_message(
    webhook_client: TestClient, session: Session
) -> None:
    _post(webhook_client, make_follow_body())

    events = session.scalars(select(Event)).all()
    assert len(events) == 1
    assert events[0].line_event_type == "follow"
    assert session.scalars(select(Message)).all() == []
    assert session.scalars(select(Reply)).all() == []
