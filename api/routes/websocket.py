import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.services.debate_service import debate_service
from api.schemas.debate import WSMessageType

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
            "data": {"message": "Debate session not found"}
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

            # If vote is required, wait for client response
            if event["type"] == WSMessageType.VOTE_REQUIRED:
                try:
                    # Wait for vote from client
                    vote_data = await websocket.receive_json()
                    if vote_data.get("type") == "vote":
                        debate_service.submit_vote(debate_id, vote_data.get("vote", "TIE"))
                except Exception:
                    # Default to TIE if no vote received
                    debate_service.submit_vote(debate_id, "TIE")

    except WebSocketDisconnect:
        # Client disconnected
        pass
    except Exception as e:
        await websocket.send_json({
            "type": WSMessageType.ERROR.value,
            "debate_id": debate_id,
            "data": {"message": str(e)}
        })
