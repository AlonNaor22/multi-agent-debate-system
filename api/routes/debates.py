from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.db import get_db
from api.schemas.debate import (
    DebateCreateRequest,
    DebateCreateResponse,
    DebateDetail,
    DebateSummary,
    StylesResponse,
    StyleInfo
)
from api.services import debate_repository
from api.services.debate_service import debate_service
from config import AVAILABLE_STYLES
from messages import STYLE_DESCRIPTIONS, INVALID_STYLE, DEBATE_NOT_FOUND

router = APIRouter(prefix="/api", tags=["debates"])


@router.get("/config/styles", response_model=StylesResponse)
async def get_styles():
    """Get available personality styles for debaters."""
    styles = [
        StyleInfo(name=style, description=STYLE_DESCRIPTIONS.get(style, ""))
        for style in AVAILABLE_STYLES
    ]
    return StylesResponse(styles=styles)


@router.post("/debates", response_model=DebateCreateResponse)
async def create_debate(request: DebateCreateRequest):
    """Create a new debate session."""
    # Validate styles
    if request.pro_style not in AVAILABLE_STYLES:
        raise HTTPException(
            status_code=400,
            detail=INVALID_STYLE.format(field="pro_style", styles=AVAILABLE_STYLES)
        )
    if request.con_style not in AVAILABLE_STYLES:
        raise HTTPException(
            status_code=400,
            detail=INVALID_STYLE.format(field="con_style", styles=AVAILABLE_STYLES)
        )

    session = debate_service.create_debate(
        topic=request.topic,
        pro_style=request.pro_style,
        con_style=request.con_style
    )

    return DebateCreateResponse(
        debate_id=session.debate_id,
        topic=session.topic,
        pro_style=session.pro_style,
        con_style=session.con_style
    )


# Sync endpoints (run in FastAPI's threadpool) backed by the SQLite store. These
# read finished debates; the live debate streams over the WebSocket.
@router.get("/debates", response_model=list[DebateSummary])
def list_debates(db_session: Session = Depends(get_db)):
    """List previously completed debates, most recently finished first."""
    return debate_repository.list_debates(db_session)


@router.get("/debates/{debate_id}", response_model=DebateDetail)
def get_debate(debate_id: str, db_session: Session = Depends(get_db)):
    """Return one previously completed debate in full (transcript + scores)."""
    debate = debate_repository.get_debate(db_session, debate_id)
    if debate is None:
        raise HTTPException(status_code=404, detail=DEBATE_NOT_FOUND)
    return debate
