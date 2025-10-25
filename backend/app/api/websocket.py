"""WebSocket endpoints for real-time communication."""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.app.websocket.manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: UUID):
    """
    WebSocket endpoint for real-time session updates.

    Events sent to clients:
    - idea_created: New idea submitted
    - coordinates_updated: UMAP recalculation completed
    - clusters_updated: Clustering completed with new labels
    - user_joined: New user joined session
    - scoreboard_updated: Rankings changed
    - session_status_changed: Session ended or accepting_ideas toggled
    """
    await manager.connect(websocket, session_id)

    try:
        # Keep connection alive and listen for client messages (if needed)
        while True:
            # Receive messages from client (currently just for keep-alive)
            data = await websocket.receive_text()

            # Echo back a pong for heartbeat (optional)
            if data == "ping":
                await manager.send_personal_message(
                    {"type": "pong"},
                    websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket, session_id)
