"""Thin wrappers around line-bot-sdk v3 for sending messages and reading profiles.

This is the ONLY module that performs network calls to the LINE platform, which
makes it the single thing to mock in tests.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)

from src.config import settings


@contextmanager
def _messaging_api() -> Iterator[MessagingApi]:
    """Yield a configured ``MessagingApi`` bound to a short-lived client."""
    config = Configuration(access_token=settings.line_channel_access_token)
    with ApiClient(config) as api_client:
        yield MessagingApi(api_client)


def reply_text(reply_token: str, text: str) -> None:
    """Reply to an inbound message using its one-time reply token."""
    with _messaging_api() as api:
        api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


def push_text(to: str, text: str) -> None:
    """Push a message to a user/group/room by id (no reply token needed)."""
    with _messaging_api() as api:
        api.push_message(PushMessageRequest(to=to, messages=[TextMessage(text=text)]))


def get_profile(user_id: str) -> Any:
    """Fetch a user's profile (displayName, pictureUrl, statusMessage)."""
    with _messaging_api() as api:
        return api.get_profile(user_id)
