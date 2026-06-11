"""ORM model for a persisted (finished) debate."""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class Debate(Base):
    """A completed debate: its setup, full transcript, and the judge's scores.

    The transcript and scores are stored as JSON columns. They are always read
    and written whole (never queried field-by-field), so exploding them into
    per-turn / per-argument tables would add joins without buying anything —
    the only column we filter or sort on is ``completed_at``. ``winner`` is
    denormalised out of the scores so the list view can show it without
    deserialising the whole scoreboard.
    """

    __tablename__ = "debates"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    topic: Mapped[str] = mapped_column(String, nullable=False)
    pro_style: Mapped[str] = mapped_column(String, nullable=False)
    con_style: Mapped[str] = mapped_column(String, nullable=False)
    winner: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transcript: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    argument_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    @property
    def message_count(self) -> int:
        """Number of transcript entries — surfaced in the list view summary."""
        return len(self.transcript or [])
