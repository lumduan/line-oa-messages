"""Signature verification and basic routing for the webhook app."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import make_event_body, sign


def test_valid_signature_returns_ok(webhook_client: TestClient) -> None:
    body = make_event_body()
    resp = webhook_client.post(
        "/line/webhook",
        content=body,
        headers={"x-line-signature": sign(body)},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_invalid_signature_returns_400(webhook_client: TestClient) -> None:
    body = make_event_body()
    resp = webhook_client.post(
        "/line/webhook",
        content=body,
        headers={"x-line-signature": "definitely-not-valid"},
    )
    assert resp.status_code == 400


def test_tampered_body_returns_400(webhook_client: TestClient) -> None:
    body = make_event_body(text="original")
    signature = sign(body)
    tampered = make_event_body(text="tampered")
    resp = webhook_client.post(
        "/line/webhook",
        content=tampered,
        headers={"x-line-signature": signature},
    )
    assert resp.status_code == 400


def test_missing_signature_header_returns_422(webhook_client: TestClient) -> None:
    body = make_event_body()
    resp = webhook_client.post("/line/webhook", content=body)
    assert resp.status_code == 422


def test_health_and_index(webhook_client: TestClient) -> None:
    assert webhook_client.get("/line/health").json() == {"status": "ok"}
    index = webhook_client.get("/")
    assert index.status_code == 200
    assert "/line/webhook" in index.json()["webhook"]


def test_root_path_also_accepts_webhook(webhook_client: TestClient) -> None:
    body = make_event_body()
    resp = webhook_client.post("/", content=body, headers={"x-line-signature": sign(body)})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
