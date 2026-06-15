"""Build the NiceGUI dashboard mounted on its own FastAPI app (port 9991)."""

from __future__ import annotations

from fastapi import FastAPI
from nicegui import ui

from src.config import settings
from src.dashboard.pages import register_pages


def build_dashboard_app() -> FastAPI:
    """Return a FastAPI app with NiceGUI mounted at the root path.

    NiceGUI is kept at ``/`` (not a sub ``mount_path``) to avoid the known
    websocket bug (zauberzeug/nicegui#2515). The app is served by uvicorn in
    :mod:`src.main`, so we use ``ui.run_with`` rather than ``ui.run``.
    """
    app = FastAPI(title="LINE OA Dashboard")
    register_pages()
    ui.run_with(app, storage_secret=settings.storage_secret, title="LINE OA Messages")
    return app
