"""Read/write access to persisted debates.

These functions are deliberately thin and synchronous. SQLite is local and
fast, and staying sync sidesteps the cross-event-loop pitfalls of async
SQLAlchemy in a codebase that mixes a sync ``TestClient`` with async tests. The
single write that finalises a debate runs off the event loop via
``asyncio.to_thread`` (see :meth:`DebateService.run_debate`); the read endpoints
run in FastAPI's threadpool.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from api import db
from api.models import Debate


def save_completed_debate(
    *,
    debate_id: str,
    topic: str,
    pro_style: str,
    con_style: str,
    transcript: list[dict],
    argument_scores: Optional[dict],
    winner: Optional[str],
    created_at: datetime,
) -> None:
    """Persist a finished debate.

    Uses ``merge`` so re-saving the same ``debate_id`` is an idempotent upsert
    rather than a primary-key collision.
    """
    with db.session_scope() as session:
        session.merge(Debate(
            id=debate_id,
            topic=topic,
            pro_style=pro_style,
            con_style=con_style,
            transcript=transcript,
            argument_scores=argument_scores,
            winner=winner,
            created_at=created_at,
            completed_at=db.utcnow(),
        ))


def list_debates(session: Session, limit: int = 50) -> list[Debate]:
    """Return finished debates, most recently completed first."""
    stmt = select(Debate).order_by(Debate.completed_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars().all())


def get_debate(session: Session, debate_id: str) -> Optional[Debate]:
    """Return one debate by id, or ``None`` if it isn't persisted."""
    return session.get(Debate, debate_id)
