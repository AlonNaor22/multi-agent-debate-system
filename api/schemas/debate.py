"""Pydantic request/response models for the REST API and the WebSocket protocol.

These define the wire contract between the FastAPI backend and the React client:
the REST shapes for creating and browsing debates, and the typed envelope for
every event streamed over the WebSocket. The TypeScript counterparts live in
``frontend/src/types/debate.ts`` and are kept in sync by hand.
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
# DebatePhase/Speaker carry no extra fields here, but their values travel in the
# WebSocket payloads, so they're re-exported as part of this contract surface
# (and imported from here by tests/test_schemas.py).
from src.debate_enums import DebatePhase, Speaker


class DebateCreateRequest(BaseModel):
    """Body for ``POST /api/debates`` — the topic plus each side's style."""
    topic: str = Field(..., min_length=1, max_length=500)
    pro_style: str = "passionate"
    con_style: str = "passionate"

    @field_validator("topic")
    @classmethod
    def topic_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("topic must not be blank")
        return v.strip()


class DebateCreateResponse(BaseModel):
    """Reply to a created debate: its new id plus the setup echoed back."""
    debate_id: str
    topic: str
    pro_style: str
    con_style: str


class StyleInfo(BaseModel):
    """One selectable debater style and its short UI description."""
    name: str
    description: str


class StylesResponse(BaseModel):
    """Reply for ``GET /api/config/styles`` — the selectable debater styles."""
    styles: list[StyleInfo]


class DebateSummary(BaseModel):
    """A persisted debate as shown in the 'past debates' list.

    Intentionally omits the (potentially large) transcript and scoreboard — the
    list view only needs the headline facts. ``from_attributes`` lets FastAPI
    build this straight from the ``Debate`` ORM row, including its
    ``message_count`` property.
    """
    model_config = ConfigDict(from_attributes=True)

    id: str
    topic: str
    pro_style: str
    con_style: str
    winner: Optional[str] = None
    message_count: int
    created_at: datetime
    completed_at: datetime


class DebateDetail(DebateSummary):
    """A persisted debate with its full transcript and structured scoreboard."""
    transcript: list[dict]
    argument_scores: Optional[dict] = None


# WebSocket message types
class WSMessageType(str, Enum):
    """The ``type`` tag on every event the server streams over the WebSocket.

    The client switches on these to drive the live UI (see ``App.handleWSMessage``
    and the mirrored ``WSMessageType`` union in the frontend types).
    """
    DEBATE_STARTED = "debate_started"
    PHASE_CHANGE = "phase_change"
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_COMPLETE = "message_complete"
    VOTE_REQUIRED = "vote_required"
    VOTE_RECEIVED = "vote_received"
    ARGUMENT_SCORES = "argument_scores"
    DEBATE_COMPLETE = "debate_complete"
    ERROR = "error"


class WSMessage(BaseModel):
    """Envelope for one streamed WebSocket event.

    Documents and validates the frame shape; the streaming path builds these
    dicts directly for speed, but the schema pins the contract the client
    relies on (``data`` is a free-form per-event payload).
    """
    type: WSMessageType
    debate_id: str
    data: dict
