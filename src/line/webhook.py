"""FastAPI webhook app: verify signature, parse events, persist, auto-echo."""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, Header, HTTPException, Request
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhook import WebhookParser

from src.config import settings
from src.db import session_scope
from src.line import client
from src.services import persist_inbound_event, record_reply

logger = logging.getLogger(__name__)

router = APIRouter(tags=["line"])
parser = WebhookParser(settings.line_channel_secret)


async def _ingest(request: Request, x_line_signature: str) -> dict[str, str]:
    """Verify the signature against the RAW body, then persist + auto-echo.

    The signature must be checked against the unmodified request bytes
    (HMAC-SHA256); the body must not be re-serialized before verification.
    """
    body = (await request.body()).decode("utf-8")
    try:
        events = parser.parse(body, x_line_signature)
    except InvalidSignatureError as exc:
        raise HTTPException(status_code=400, detail="invalid signature") from exc

    with session_scope() as session:
        for event in events:
            message = persist_inbound_event(session, event, raw_body=body)
            if message is None:
                continue
            if settings.auto_reply and message.reply_token and message.text is not None:
                reply = f"echo: {message.text}"
                try:
                    client.reply_text(message.reply_token, reply)
                except Exception:  # noqa: BLE001 — never fail ingestion on a send error
                    logger.warning("auto-reply failed", exc_info=True)
                else:
                    record_reply(
                        session,
                        text=reply,
                        kind="reply",
                        message_id=message.id,
                        to_user_id=message.user.line_user_id,
                    )
    return {"status": "ok"}


@router.get("/line/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@router.post("/line/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(...),
) -> dict[str, str]:
    """Canonical LINE webhook endpoint."""
    return await _ingest(request, x_line_signature)


@router.post("/")
async def root_webhook(
    request: Request,
    x_line_signature: str = Header(...),
) -> dict[str, str]:
    """Convenience webhook at the root path.

    The webhook runs on its own host/subdomain, so LINE may be configured with
    just ``https://<host>/``. Accept deliveries there too.
    """
    return await _ingest(request, x_line_signature)


def build_webhook_app() -> FastAPI:
    """Build the FastAPI application that serves the LINE webhook (port 9990)."""
    app = FastAPI(title="LINE OA Webhook")
    app.include_router(router)

    @app.get("/")
    def index() -> dict[str, str]:
        return {"service": "line-oa-webhook", "webhook": "/line/webhook (also POST /)"}

    return app
