"""Shared pytest fixtures.

Environment is configured BEFORE importing any ``src`` module so that the
settings singleton picks up the test database and a known channel secret.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path

TEST_CHANNEL_SECRET = "test-channel-secret"
_TMP_DIR = tempfile.mkdtemp(prefix="line-oa-test-")
_TEST_DB_PATH = Path(_TMP_DIR) / "test.db"

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["LINE_CHANNEL_SECRET"] = TEST_CHANNEL_SECRET
os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = ""
os.environ["AUTO_REPLY"] = "true"
os.environ["STORAGE_SECRET"] = "test-storage-secret"

import pytest  # noqa: E402 — import after env is configured
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from src.db import SessionLocal, reset_db  # noqa: E402
from src.line import client as line_client  # noqa: E402
from src.line.webhook import build_webhook_app  # noqa: E402


def sign(body: bytes, secret: str = TEST_CHANNEL_SECRET) -> str:
    """Compute the LINE ``X-Line-Signature`` for a raw body."""
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def make_event_body(
    *,
    text: str = "สวัสดีครับ",
    user_id: str = "Utestuser00000000000000000000001",
    webhook_event_id: str = "evt-1",
    message_id: str = "msg-1",
    reply_token: str = "rt-1",
) -> bytes:
    """Build a minimal, valid LINE text-message webhook body."""
    payload = {
        "destination": "Udestination0000000000000000000",
        "events": [
            {
                "type": "message",
                "mode": "active",
                "timestamp": 1700000000000,
                "source": {"type": "user", "userId": user_id},
                "webhookEventId": webhook_event_id,
                "deliveryContext": {"isRedelivery": False},
                "replyToken": reply_token,
                "message": {
                    "type": "text",
                    "id": message_id,
                    "quoteToken": "quote-token-0000000000000000",
                    "text": text,
                },
            }
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


def make_follow_body(
    *,
    user_id: str = "Ufollower0000000000000000000000001",
    webhook_event_id: str = "follow-1",
    reply_token: str = "rt-follow",
) -> bytes:
    """Build a minimal, valid LINE ``follow`` webhook body (no message)."""
    payload = {
        "destination": "Udestination0000000000000000000",
        "events": [
            {
                "type": "follow",
                "mode": "active",
                "timestamp": 1700000000000,
                "source": {"type": "user", "userId": user_id},
                "webhookEventId": webhook_event_id,
                "deliveryContext": {"isRedelivery": False},
                "replyToken": reply_token,
            }
        ],
    }
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")


@pytest.fixture(autouse=True)
def _fresh_db() -> Iterator[None]:
    """Reset all tables before each test for isolation."""
    reset_db()
    yield


@pytest.fixture
def session() -> Iterator[Session]:
    """A SQLAlchemy session for reading/writing directly in tests."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    finally:
        db.close()


@pytest.fixture
def webhook_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """A TestClient for the webhook app with the LINE reply call stubbed out."""

    def _noop_reply(reply_token: str, text: str) -> None:
        return None

    monkeypatch.setattr(line_client, "reply_text", _noop_reply)
    with TestClient(build_webhook_app()) as test_client:
        yield test_client
