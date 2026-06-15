"""The outbound LINE client builds the correct SDK request objects (no network)."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from src.line import client


class _FakeApi:
    def __init__(self) -> None:
        self.replies: list[Any] = []
        self.pushes: list[Any] = []
        self.profiles: list[str] = []

    def reply_message(self, request: Any) -> None:
        self.replies.append(request)

    def push_message(self, request: Any) -> None:
        self.pushes.append(request)

    def get_profile(self, user_id: str) -> Any:
        self.profiles.append(user_id)
        return SimpleNamespace(display_name="Bob")


@pytest.fixture
def fake_api(monkeypatch: pytest.MonkeyPatch) -> _FakeApi:
    api = _FakeApi()

    @contextmanager
    def _ctx() -> Iterator[_FakeApi]:
        yield api

    monkeypatch.setattr(client, "_messaging_api", _ctx)
    return api


def test_reply_text_builds_reply_request(fake_api: _FakeApi) -> None:
    client.reply_text("rt-9", "hi there")
    assert len(fake_api.replies) == 1
    request = fake_api.replies[0]
    assert request.reply_token == "rt-9"
    assert request.messages[0].text == "hi there"


def test_push_text_builds_push_request(fake_api: _FakeApi) -> None:
    client.push_text("Uabc", "ping")
    assert len(fake_api.pushes) == 1
    request = fake_api.pushes[0]
    assert request.to == "Uabc"
    assert request.messages[0].text == "ping"


def test_get_profile_passes_user_id(fake_api: _FakeApi) -> None:
    profile = client.get_profile("Uabc")
    assert fake_api.profiles == ["Uabc"]
    assert profile.display_name == "Bob"
