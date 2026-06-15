"""The entrypoint module imports cleanly and exposes ``main``."""

from __future__ import annotations


def test_main_module_importable() -> None:
    import src.main

    assert callable(src.main.main)
    assert callable(src.main._serve)
