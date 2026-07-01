import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.debate_service import debate_service, VOTE_TIMEOUT_SECONDS
from api.schemas.debate import WSMessageType
from messages import DEBATE_SESSION_NOT_FOUND, WS_UNEXPECTED_ERROR

logger = logging.getLogger(__name__)

VALID_VOTES = {"PRO", "CON", "TIE"}

router = APIRouter()


@router.websocket("/ws/debates/{debate_id}")
async def debate_websocket(websocket: WebSocket, debate_id: str):
    """WebSocket endpoint for real-time debate streaming."""
    await websocket.accept()

    session = debate_service.get_session(debate_id)
    if not session:
        await websocket.send_json({
            "type": WSMessageType.ERROR.value,
            "debate_id": debate_id,
            "data": {"message": DEBATE_SESSION_NOT_FOUND}
        })
        await websocket.close()
        return

    try:
        # Start the debate and stream events
        async for event in debate_service.run_debate(session):
            # Convert enum to string for JSON serialization
            event_dict = {
                "type": event["type"].value if hasattr(event["type"], "value") else event["type"],
                "debate_id": event["debate_id"],
                "data": event["data"]
            }
            await websocket.send_json(event_dict)

            # If a vote is required, wait for the client's response — but never
            # indefinitely. VOTE_TIMEOUT_SECONDS is the single authoritative
            # bound on the audience vote (run_debate no longer guards it too); a
            # client that receives the prompt and then goes silent, disconnects,
            # or sends garbage defaults to TIE so the debate proceeds and its
            # session is cleaned up rather than leaking. Every branch below
            # submits exactly one vote so run_debate always unblocks.
            if event["type"] == WSMessageType.VOTE_REQUIRED:
                try:
                    vote_data = await asyncio.wait_for(
                        websocket.receive_json(), timeout=VOTE_TIMEOUT_SECONDS
                    )
                    raw = (
                        vote_data.get("vote", "TIE")
                        if vote_data.get("type") == "vote"
                        else "TIE"
                    )
                    debate_service.submit_vote(debate_id, raw if raw in VALID_VOTES else "TIE")
                except asyncio.TimeoutError:
                    logger.info(
                        "Audience vote timed out for debate_id=%s; recording TIE", debate_id
                    )
                    debate_service.submit_vote(debate_id, "TIE")
                except (WebSocketDisconnect, json.JSONDecodeError):
                    debate_service.submit_vote(debate_id, "TIE")
                except Exception:
                    logger.exception("Unexpected error reading vote for debate_id=%s", debate_id)
                    debate_service.submit_vote(debate_id, "TIE")

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Unhandled error during debate websocket for debate_id=%s", debate_id)
        await websocket.send_json({
            "type": WSMessageType.ERROR.value,
            "debate_id": debate_id,
            "data": {"message": WS_UNEXPECTED_ERROR}
        })
