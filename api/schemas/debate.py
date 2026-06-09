from enum import Enum
from pydantic import BaseModel
from typing import Optional
from src.debate_enums import DebatePhase, Speaker


class DebateCreateRequest(BaseModel):
    topic: str
    pro_style: str = "passionate"
    con_style: str = "passionate"


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
