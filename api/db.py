"""SQLAlchemy engine, session factory, and declarative base for persistence.

Completed debates are written to a small SQLite database so they survive a
server restart and can be browsed in the "past debates" view. The *live*,
in-flight debate still lives in the in-memory store on
:class:`~api.services.debate_service.DebateService` — that session holds an
``asyncio.Event`` for voting and the agent objects, neither of which is
serialisable — so this module is the durable record of the *finished* result,
not a replacement for the runtime session.

Everything routes through the module-level ``engine`` / ``SessionLocal`` so a
test fixture can repoint them at a throwaway database without touching the real
``debates.db`` (see ``conftest._test_db``). The functions below read those
module globals at call time, which is what makes that monkeypatch take effect.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import DATABASE_URL


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model (see api/models.py)."""


def utcnow() -> datetime:
    """Naive UTC timestamp for the DB.

    SQLite's ``DateTime`` column has no timezone, so we store a tz-naive UTC
    value rather than feed it an aware datetime it would silently flatten.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


# check_same_thread=False lets the one-off write that finalises a debate run on a
# worker thread (asyncio.to_thread) while reads happen on the event loop.
_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create the debate tables if they don't exist yet (idempotent)."""
    import api.models  # noqa: F401 — imported for its side effect: registering models on Base
    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a read session that is always closed."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session for writes: commit on success, roll back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
