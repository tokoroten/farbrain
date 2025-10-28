"""Integration tests for WebSocket functionality."""

import pytest
import json
import asyncio
from uuid import uuid4
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.db.base import engine, Base
from backend.app.websocket.manager import manager


@pytest.fixture(scope="function")
def test_client():
    """Create sync test client for WebSocket testing."""
    # Note: WebSocket tests must use synchronous TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_session(test_client):
    """Create a test session."""
    response = test_client.post(
        "/api/sessions/",
        json={"title": "WebSocket Test Session", "duration": 3600}
    )
    return response.json()


class TestWebSocketConnection:
    """Test cases for WebSocket connection management."""

    def test_websocket_connection(self, test_client, test_session):
        """Test basic WebSocket connection and disconnection."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Connection should be established
            assert session_id in manager.active_connections
            assert len(manager.active_connections[session_id]) == 1

        # After context exit, connection should be cleaned up
        assert session_id not in manager.active_connections or len(manager.active_connections[session_id]) == 0

    def test_multiple_connections_same_session(self, test_session):
        """Test multiple clients connecting to the same session."""
        session_id = test_session["id"]

        # Create two separate clients for multiple connections
        with TestClient(app) as client1, TestClient(app) as client2:
            with client1.websocket_connect(f"/ws/{session_id}") as ws1:
                with client2.websocket_connect(f"/ws/{session_id}") as ws2:
                    # Both connections should be active
                    assert session_id in manager.active_connections
                    assert len(manager.active_connections[session_id]) == 2

                # After ws2 closes, only ws1 should remain
                assert len(manager.active_connections[session_id]) == 1

        # After all close, session should be cleaned up
        assert session_id not in manager.active_connections or len(manager.active_connections[session_id]) == 0

    def test_ping_pong(self, test_client, test_session):
        """Test WebSocket ping/pong heartbeat."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Send ping
            websocket.send_text("ping")

            # Receive pong
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "pong"


class TestWebSocketBroadcast:
    """Test cases for WebSocket broadcast messages."""

    def test_idea_created_broadcast(self, test_client, test_session):
        """Test broadcasting idea_created event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast idea_created event
            asyncio.run(manager.send_idea_created(
                session_id=session_id,
                idea_id=uuid4(),
                user_id=uuid4(),
                user_name="Test User",
                formatted_text="Formatted idea",
                raw_text="Raw idea",
                x=0.5,
                y=0.5,
                cluster_id=1,
                novelty_score=75.0,
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "idea_created"
            assert "data" in data
            assert data["data"]["user_name"] == "Test User"
            assert data["data"]["formatted_text"] == "Formatted idea"
            assert data["data"]["x"] == 0.5
            assert data["data"]["y"] == 0.5
            assert data["data"]["novelty_score"] == 75.0

    def test_user_joined_broadcast(self, test_client, test_session):
        """Test broadcasting user_joined event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast user_joined event
            user_id = uuid4()
            asyncio.run(manager.send_user_joined(
                session_id=session_id,
                user_id=user_id,
                user_name="New User",
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "user_joined"
            assert data["data"]["user_id"] == str(user_id)
            assert data["data"]["user_name"] == "New User"

    def test_coordinates_updated_broadcast(self, test_client, test_session):
        """Test broadcasting coordinates_updated event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast coordinates_updated event
            updates = [
                {"idea_id": str(uuid4()), "x": 0.1, "y": 0.2},
                {"idea_id": str(uuid4()), "x": 0.3, "y": 0.4},
            ]
            asyncio.run(manager.send_coordinates_updated(
                session_id=session_id,
                updates=updates,
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "coordinates_updated"
            assert data["data"]["updates"] == updates

    def test_clusters_updated_broadcast(self, test_client, test_session):
        """Test broadcasting clusters_updated event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast clusters_updated event
            clusters = [
                {
                    "id": 1,
                    "label": "Technology",
                    "convex_hull": [[0.1, 0.2], [0.3, 0.4]],
                    "idea_count": 5,
                },
            ]
            asyncio.run(manager.send_clusters_updated(
                session_id=session_id,
                clusters=clusters,
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "clusters_updated"
            assert data["data"]["clusters"] == clusters

    def test_scoreboard_updated_broadcast(self, test_client, test_session):
        """Test broadcasting scoreboard_updated event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast scoreboard_updated event
            rankings = [
                {
                    "rank": 1,
                    "user_id": str(uuid4()),
                    "user_name": "Top User",
                    "total_score": 225.0,
                    "idea_count": 3,
                },
            ]
            asyncio.run(manager.send_scoreboard_updated(
                session_id=session_id,
                rankings=rankings,
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "scoreboard_updated"
            assert data["data"]["rankings"] == rankings

    def test_session_status_changed_broadcast(self, test_client, test_session):
        """Test broadcasting session_status_changed event."""
        session_id = test_session["id"]

        with test_client.websocket_connect(f"/ws/{session_id}") as websocket:
            # Broadcast session_status_changed event
            asyncio.run(manager.send_session_status_changed(
                session_id=session_id,
                status="ended",
                accepting_ideas=False,
            ))

            # Receive broadcast
            response = websocket.receive_text()
            data = json.loads(response)

            assert data["type"] == "session_status_changed"
            assert data["data"]["status"] == "ended"
            assert data["data"]["accepting_ideas"] is False


class TestWebSocketMultiClient:
    """Test cases for multi-client WebSocket scenarios."""

    def test_broadcast_to_multiple_clients(self, test_session):
        """Test that broadcasts reach all connected clients."""
        session_id = test_session["id"]

        # Create two separate clients for multiple connections
        with TestClient(app) as client1, TestClient(app) as client2:
            with client1.websocket_connect(f"/ws/{session_id}") as ws1:
                with client2.websocket_connect(f"/ws/{session_id}") as ws2:
                    # Broadcast to all clients
                    asyncio.run(manager.send_user_joined(
                        session_id=session_id,
                        user_id=uuid4(),
                        user_name="Broadcast Test",
                    ))

                    # Both clients should receive the message
                    response1 = ws1.receive_text()
                    response2 = ws2.receive_text()

                    data1 = json.loads(response1)
                    data2 = json.loads(response2)

                    assert data1["type"] == "user_joined"
                    assert data2["type"] == "user_joined"
                    assert data1["data"]["user_name"] == "Broadcast Test"
                    assert data2["data"]["user_name"] == "Broadcast Test"

    def test_no_broadcast_to_different_session(self, test_client):
        """Test that broadcasts are isolated to their sessions."""
        # Create two sessions
        response1 = test_client.post(
            "/api/sessions/",
            json={"title": "Session 1", "duration": 3600}
        )
        session1_id = response1.json()["id"]

        response2 = test_client.post(
            "/api/sessions/",
            json={"title": "Session 2", "duration": 3600}
        )
        session2_id = response2.json()["id"]

        # Create two separate clients for different sessions
        with TestClient(app) as client1, TestClient(app) as client2:
            with client1.websocket_connect(f"/ws/{session1_id}") as ws1:
                with client2.websocket_connect(f"/ws/{session2_id}") as ws2:
                    # Broadcast to session 1 only
                    asyncio.run(manager.send_user_joined(
                        session_id=session1_id,
                        user_id=uuid4(),
                        user_name="Session 1 User",
                    ))

                    # ws1 should receive the message
                    response1 = ws1.receive_text()
                    data1 = json.loads(response1)
                    assert data1["type"] == "user_joined"

                    # ws2 should not receive anything (timeout expected)
                    # We'll send a ping to ws2 to verify it's still alive
                    ws2.send_text("ping")
                    response2 = ws2.receive_text()
                    data2 = json.loads(response2)
                    assert data2["type"] == "pong"  # Should only get pong, not user_joined
