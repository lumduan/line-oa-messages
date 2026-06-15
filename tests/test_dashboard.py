"""The dashboard app builds and mounts NiceGUI without error."""

from __future__ import annotations

from fastapi import FastAPI
from src.dashboard.app import build_dashboard_app


def test_build_dashboard_app_returns_fastapi() -> None:
    app = build_dashboard_app()
    assert isinstance(app, FastAPI)
