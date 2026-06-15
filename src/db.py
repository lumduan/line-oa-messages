"""Database engine, session helpers, and the declarative base.

A single synchronous SQLAlchemy engine backed by SQLite is the simplest robust
choice for this single-process POC. WAL mode is enabled so concurrent reads
(dashboard) don't block the occasional write (webhook).
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _ensure_sqlite_dir(database_url: str) -> None:
    """Create the parent directory for a file-based SQLite database, if needed."""
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return
    raw_path = database_url[len(prefix) :]
    if not raw_path or raw_path == ":memory:":
        return
    Path(raw_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def _make_engine(database_url: str) -> Engine:
    _ensure_sqlite_dir(database_url)
    engine = create_engine(
        database_url,
        # SQLite + multiple uvicorn servers in one process may touch the
        # connection from different threads.
        connect_args={"check_same_thread": False},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


engine: Engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def init_db() -> None:
    """Create all tables if they do not yet exist."""
    # Importing models registers them on ``Base.metadata``.
    from src import models  # noqa: F401

    Base.metadata.create_all(engine)


def reset_db() -> None:
    """Drop and recreate all tables — used by tests for isolation."""
    from src import models  # noqa: F401

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
