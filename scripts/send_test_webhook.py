"""Send a correctly-signed sample webhook to a locally running instance.

The signature is computed exactly as LINE does: base64(HMAC-SHA256(channel_secret,
raw_body)). Credentials and ports are read from ``.env`` via the app settings.

Usage::

    # Terminal 1 — run offline so a fake reply token doesn't call LINE:
    AUTO_REPLY=false uv run python -m src.main

    # Terminal 2:
    uv run python scripts/send_test_webhook.py "hello from the test script"
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time

import httpx
from src.config import settings


def main() -> int:
    if not settings.line_channel_secret:
        print("LINE_CHANNEL_SECRET is not set — fill in .env first.", file=sys.stderr)
        return 1

    text = sys.argv[1] if len(sys.argv) > 1 else "สวัสดีจากสคริปต์ทดสอบ 👋"
    host = "127.0.0.1" if settings.app_host in ("0.0.0.0", "") else settings.app_host
    url = f"http://{host}:{settings.webhook_port}/line/webhook"

    unique = str(int(time.time() * 1000))
    payload = {
        "destination": "Udestination0000000000000000000",
        "events": [
            {
                "type": "message",
                "mode": "active",
                "timestamp": int(time.time() * 1000),
                "source": {"type": "user", "userId": "Utestuser00000000000000000000001"},
                "webhookEventId": f"local-{unique}",
                "deliveryContext": {"isRedelivery": False},
                "replyToken": f"local-reply-{unique}",
                "message": {
                    "type": "text",
                    "id": f"msg-{unique}",
                    "quoteToken": f"quote-{unique}",
                    "text": text,
                },
            }
        ],
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = base64.b64encode(
        hmac.new(settings.line_channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")

    response = httpx.post(
        url,
        content=body,
        headers={"content-type": "application/json", "x-line-signature": signature},
        timeout=10.0,
    )
    print(f"POST {url} -> {response.status_code} {response.text}")
    return 0 if response.status_code == 200 else 2


if __name__ == "__main__":
    raise SystemExit(main())
