"""WebSocket connection manager for real-time session updates."""

import json
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        """Initialize connection manager."""
        # Maps session_id -> list of WebSocket connections
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, session_id: str | UUID) -> None:
        """Accept a new WebSocket connection and add to session room."""
        await websocket.accept()
        session_key = str(session_id)

        if session_key not in self.active_connections:
            self.active_connections[session_key] = []

        self.active_connections[session_key].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str | UUID) -> None:
        """Remove a WebSocket connection from session room."""
        session_key = str(session_id)

        if session_key in self.active_connections:
            self.active_connections[session_key].remove(websocket)

            # Clean up empty session rooms
            if not self.active_connections[session_key]:
                del self.active_connections[session_key]

    async def send_personal_message(self, message: dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket connection."""
        await websocket.send_text(json.dumps(message))

    async def broadcast_to_session(self, session_id: str | UUID, message: dict[str, Any]) -> None:
        """Broadcast a message to all connections in a session."""
        session_key = str(session_id)

        if session_key not in self.active_connections:
            return

        # Send to all connections in the session
        disconnected = []
        for connection in self.active_connections[session_key]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                # Mark for removal if connection is broken
                disconnected.append(connection)

        # Clean up broken connections
        for connection in disconnected:
            self.disconnect(connection, session_id)

    async def send_idea_created(
        self,
        session_id: str | UUID,
        idea_id: str | UUID,
        user_id: str | UUID,
        user_name: str,
        formatted_text: str,
        raw_text: str,
        x: float,
        y: float,
        cluster_id: int | None,
        novelty_score: float,
        closest_idea_id: str | None = None,
        timestamp: str | None = None,
        coordinates_recalculated: bool = False,
    ) -> None:
        """Broadcast new idea creation to all session participants."""
        message = {
            "type": "idea_created",
            "data": {
                "id": str(idea_id),
                "user_id": str(user_id),
                "user_name": user_name,
                "formatted_text": formatted_text,
                "raw_text": raw_text,
                "x": x,
                "y": y,
                "cluster_id": cluster_id,
                "novelty_score": novelty_score,
                "closest_idea_id": str(closest_idea_id) if closest_idea_id else None,
                "timestamp": timestamp,
                "coordinates_recalculated": coordinates_recalculated,
            },
        }
        await self.broadcast_to_session(session_id, message)

    async def send_coordinates_updated(
        self,
        session_id: str | UUID,
        updates: list[dict[str, Any]],
    ) -> None:
        """Broadcast coordinate updates (after UMAP recalculation)."""
        message = {
            "type": "coordinates_updated",
            "data": {"updates": updates},
        }
        await self.broadcast_to_session(session_id, message)

    async def send_clusters_updated(
        self,
        session_id: str | UUID,
        clusters: list[dict[str, Any]],
    ) -> None:
        """Broadcast cluster updates (after clustering or labeling)."""
        message = {
            "type": "clusters_updated",
            "data": {"clusters": clusters},
        }
        await self.broadcast_to_session(session_id, message)

    async def send_clusters_recalculated(
        self,
        session_id: str | UUID,
    ) -> None:
        """Broadcast that clusters have been recalculated (full refresh needed)."""
        message = {
            "type": "clusters_recalculated",
            "data": {},
        }
        await self.broadcast_to_session(session_id, message)

    async def send_user_joined(
        self,
        session_id: str | UUID,
        user_id: str | UUID,
        user_name: str,
    ) -> None:
        """Broadcast new user joining the session."""
        message = {
            "type": "user_joined",
            "data": {
                "user_id": str(user_id),
                "user_name": user_name,
            },
        }
        await self.broadcast_to_session(session_id, message)

    async def send_scoreboard_updated(
        self,
        session_id: str | UUID,
        rankings: list[dict[str, Any]],
    ) -> None:
        """Broadcast scoreboard updates."""
        message = {
            "type": "scoreboard_updated",
            "data": {"rankings": rankings},
        }
        await self.broadcast_to_session(session_id, message)

    async def send_session_status_changed(
        self,
        session_id: str | UUID,
        status: str,
        accepting_ideas: bool,
    ) -> None:
        """Broadcast session status changes (ended, accepting_ideas toggled)."""
        message = {
            "type": "session_status_changed",
            "data": {
                "status": status,
                "accepting_ideas": accepting_ideas,
            },
        }
        await self.broadcast_to_session(session_id, message)


# Global connection manager instance
manager = ConnectionManager()
