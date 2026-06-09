from enum import Enum
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from src.debate_enums import DebatePhase, Speaker


class DebateCreateRequest(BaseModel):
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
    debate_id: str
    topic: str
    pro_style: str
    con_style: str


class StyleInfo(BaseModel):
    name: str
    description: str


class StylesResponse(BaseModel):
    styles: list[StyleInfo]


# WebSocket message types
class WSMessageType(str, Enum):
    DEBATE_STARTED = "debate_started"
    PHASE_CHANGE = "phase_change"
    MESSAGE_START = "message_start"
    MESSAGE_CHUNK = "message_chunk"
    MESSAGE_COMPLETE = "message_complete"
    VOTE_REQUIRED = "vote_required"
    VOTE_RECEIVED = "vote_received"
    DEBATE_COMPLETE = "debate_complete"
    ERROR = "error"


class WSMessage(BaseModel):
    type: WSMessageType
    debate_id: str
    data: dict
