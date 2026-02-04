from fastapi import APIRouter, HTTPException

from api.schemas.debate import (
    DebateCreateRequest,
    DebateCreateResponse,
    StylesResponse,
    StyleInfo
)
from api.services.debate_service import debate_service
from config import AVAILABLE_STYLES
from src.prompts import PRO_STYLES

router = APIRouter(prefix="/api", tags=["debates"])


# Style descriptions for the UI
STYLE_DESCRIPTIONS = {
    "passionate": "Persuasive with logical arguments and rhetorical techniques",
    "aggressive": "Confrontational and relentless, attacks opponent's logic directly",
    "academic": "Formal, research-oriented with citations and structured frameworks",
    "humorous": "Witty with satire, clever analogies, and entertaining delivery"
}


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
            detail=f"Invalid pro_style. Must be one of: {AVAILABLE_STYLES}"
        )
    if request.con_style not in AVAILABLE_STYLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid con_style. Must be one of: {AVAILABLE_STYLES}"
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
