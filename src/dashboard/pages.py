"""NiceGUI pages: a live message table plus a push-message form."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from src.db import session_scope
from src.line import client
from src.services import list_messages, record_reply

COLUMNS: list[dict[str, Any]] = [
    {"name": "id", "label": "ID", "field": "id", "align": "left", "sortable": True},
    {"name": "user", "label": "User", "field": "user", "align": "left"},
    {"name": "type", "label": "Type", "field": "type", "align": "left"},
    {"name": "text", "label": "Message", "field": "text", "align": "left"},
    {
        "name": "received",
        "label": "Received (UTC)",
        "field": "received",
        "align": "left",
        "sortable": True,
    },
]


def register_pages() -> None:
    """Register NiceGUI page routes on the global NiceGUI app."""

    @ui.page("/")
    def dashboard() -> None:
        ui.label("LINE OA Messages").classes("text-2xl font-bold")
        ui.label("Live inbound messages — auto-refresh every 2 seconds").classes(
            "text-sm text-gray-500"
        )

        table = ui.table(columns=COLUMNS, rows=list_messages(), row_key="id").classes("w-full")

        def refresh() -> None:
            table.rows = list_messages()
            table.update()

        ui.timer(2.0, refresh)

        with ui.card().classes("w-full"):
            ui.label("Push a message").classes("text-lg font-medium")
            with ui.row().classes("items-end gap-2"):
                user_input = ui.input("User ID (Uxxxx…)").classes("w-96")
                text_input = ui.input("Message").classes("w-96")

                def send() -> None:
                    user_id = (user_input.value or "").strip()
                    text = (text_input.value or "").strip()
                    if not user_id or not text:
                        ui.notify("User ID and message are required", type="warning")
                        return
                    try:
                        client.push_text(user_id, text)
                    except Exception as exc:  # noqa: BLE001 — surface send errors in the UI
                        ui.notify(f"Push failed: {exc}", type="negative")
                        return
                    with session_scope() as session:
                        record_reply(session, text=text, kind="push", to_user_id=user_id)
                    text_input.value = ""
                    ui.notify("Pushed", type="positive")

                ui.button("Push", on_click=send)
