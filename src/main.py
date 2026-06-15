"""Entrypoint: run the webhook and the dashboard as two uvicorn servers.

One process, one container, two ports:

* ``9990`` — LINE webhook (FastAPI)
* ``9991`` — dashboard (NiceGUI)
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal

import uvicorn

from src.config import settings
from src.dashboard.app import build_dashboard_app
from src.db import init_db
from src.line.webhook import build_webhook_app

logger = logging.getLogger(__name__)


async def _serve() -> None:  # pragma: no cover - exercised only when running the server
    init_db()

    servers = [
        uvicorn.Server(
            uvicorn.Config(
                build_webhook_app(),
                host=settings.app_host,
                port=settings.webhook_port,
                log_level=settings.log_level.lower(),
            )
        ),
        uvicorn.Server(
            uvicorn.Config(
                build_dashboard_app(),
                host=settings.app_host,
                port=settings.dashboard_port,
                log_level=settings.log_level.lower(),
            )
        ),
    ]

    # Running two servers in one loop: neutralize each server's own signal
    # capture (uvicorn 0.49 uses Server.capture_signals) and install a single
    # shared handler so the container stops both cleanly.
    for server in servers:
        # Dynamic assignment is intentional (a plain assignment trips mypy's
        # method-assign check); setattr keeps both linters happy.
        setattr(server, "capture_signals", contextlib.nullcontext)  # noqa: B010

    def _request_shutdown() -> None:
        for server in servers:
            server.should_exit = True

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):  # non-POSIX platforms
            loop.add_signal_handler(sig, _request_shutdown)

    logger.info(
        "webhook -> http://%s:%s/line/webhook | dashboard -> http://%s:%s/",
        settings.app_host,
        settings.webhook_port,
        settings.app_host,
        settings.dashboard_port,
    )
    await asyncio.gather(*(server.serve() for server in servers))


def main() -> None:  # pragma: no cover - process entrypoint
    logging.basicConfig(level=settings.log_level.upper())
    asyncio.run(_serve())


if __name__ == "__main__":  # pragma: no cover
    main()
