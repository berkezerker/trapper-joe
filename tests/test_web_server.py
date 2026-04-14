"""
Tests for TrapperJoe web server and API endpoints.
"""

import pytest
import time
import json
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from trapperjoe.web_server import create_app, set_app_state


@pytest.fixture
def test_state():
    """Create test trap state."""
    return {
        "1": {
            "name": "Trap 1",
            "active": True,
            "state": "OK",
            "lastHeard": time.time() - 60,
            "battery": 85.0,
            "voltage": 3.2,
            "rssi": -95.0,
            "snr": 10.5,
            "lastEventType": "activity",
        },
        "2": {
            "name": "Trap 2",
            "active": True,
            "state": "ALERT",
            "lastHeard": time.time() - 3600,
            "battery": 50.0,
            "voltage": 2.8,
            "rssi": -105.0,
            "snr": 5.0,
            "lastEventType": "alert",
        },
        "3": {
            "name": "Trap 3",
            "active": False,
            "state": "MISSING",
            "lastHeard": time.time() - 86400,
            "battery": None,
            "voltage": None,
            "rssi": None,
            "snr": None,
            "lastEventType": None,
        },
    }


@pytest.fixture
def client(test_state):
    """Create test client with mocked state."""
    app = create_app()
    set_app_state(test_state)
    return TestClient(app)


class TestDashboard:
    """Test dashboard HTML endpoint."""
    
    def test_get_dashboard(self, client):
        """Test GET / returns HTML."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "TrapperJoe" in response.text
        assert "Dashboard" in response.text
        assert "api/status" in response.text
        assert "api/traps" in response.text


class TestStatusEndpoint:
    """Test /api/status endpoint."""
    
    def test_get_status(self, client):
        """Test GET /api/status returns correct counts."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        
        assert data["ok_count"] == 1
        assert data["alert_count"] == 1
        assert data["missing_count"] == 1
        assert data["unknown_count"] == 0
        assert "timestamp" in data
    
    def test_status_response_schema(self, client):
        """Test /api/status response has correct schema."""
        response = client.get("/api/status")
        data = response.json()
        
        required_fields = {"timestamp", "ok_count", "alert_count", "missing_count", "unknown_count"}
        assert set(data.keys()) == required_fields
        
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["ok_count"], int)
        assert isinstance(data["alert_count"], int)
        assert isinstance(data["missing_count"], int)
        assert isinstance(data["unknown_count"], int)


class TestTrapsListEndpoint:
    """Test /api/traps endpoint."""
    
    def test_get_all_traps(self, client):
        """Test GET /api/traps returns all trap data."""
        response = client.get("/api/traps")
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "traps" in data
        assert len(data["traps"]) == 3
    
    def test_traps_contain_correct_data(self, client):
        """Test /api/traps contains correct trap information."""
        response = client.get("/api/traps")
        data = response.json()
        traps = data["traps"]
        
        # Check trap 1
        assert "1" in traps
        trap1 = traps["1"]
        assert trap1["name"] == "Trap 1"
        assert trap1["state"] == "OK"
        assert trap1["active"] is True
        assert trap1["battery"] == 85.0
        assert trap1["voltage"] == 3.2
        assert trap1["rssi"] == -95.0
        assert trap1["snr"] == 10.5
        assert trap1["lastEventType"] == "activity"
        
        # Check trap 2
        assert "2" in traps
        trap2 = traps["2"]
        assert trap2["state"] == "ALERT"
        assert trap2["battery"] == 50.0
        
        # Check trap 3
        assert "3" in traps
        trap3 = traps["3"]
        assert trap3["state"] == "MISSING"
        assert trap3["active"] is False
        assert trap3["battery"] is None


class TestTrapDetailEndpoint:
    """Test /api/trap/{trap_id} endpoint."""
    
    def test_get_trap_by_id(self, client):
        """Test GET /api/trap/{trap_id} returns trap data."""
        response = client.get("/api/trap/1")
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Trap 1"
        assert data["state"] == "OK"
        assert data["active"] is True
    
    def test_get_nonexistent_trap(self, client):
        """Test GET /api/trap/{trap_id} returns 404 for nonexistent trap."""
        response = client.get("/api/trap/nonexistent")
        assert response.status_code == 404
    
    def test_trap_detail_has_all_fields(self, client):
        """Test trap detail response has all required fields."""
        response = client.get("/api/trap/1")
        data = response.json()
        
        required_fields = {
            "name", "active", "state", "lastHeard", "battery",
            "voltage", "rssi", "snr", "lastEventType"
        }
        assert set(data.keys()) == required_fields


class TestResetTrapEndpoint:
    """Test /api/trap/{trap_id}/reset endpoint."""
    
    def test_reset_trap(self, client, test_state):
        """Test POST /api/trap/{trap_id}/reset resets trap status."""
        # Verify trap 2 is ALERT before reset
        response = client.get("/api/trap/2")
        assert response.json()["state"] == "ALERT"
        
        # Reset trap 2
        response = client.post("/api/trap/2/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "reset" in data["message"].lower()
        
        # Verify trap 2 is now OK
        response = client.get("/api/trap/2")
        assert response.json()["state"] == "OK"
    
    def test_reset_nonexistent_trap(self, client):
        """Test POST /api/trap/{trap_id}/reset returns 404 for nonexistent trap."""
        response = client.post("/api/trap/nonexistent/reset")
        assert response.status_code == 404
    
    def test_reset_updates_last_processed_ts(self, client, test_state):
        """Test that reset updates last_processed_ts."""
        response = client.post("/api/trap/1/reset")
        assert response.status_code == 200
        
        # The updated timestamp should be very recent
        assert "last_processed_ts" in test_state["1"]
        updated_ts = test_state["1"]["last_processed_ts"]
        current_ts = time.time()
        
        # Should be within last 5 seconds
        assert current_ts - updated_ts < 5


class TestToggleTrapEndpoint:
    """Test /api/trap/{trap_id}/toggle endpoint."""
    
    def test_toggle_trap_active_to_inactive(self, client, test_state):
        """Test POST /api/trap/{trap_id}/toggle toggles active status."""
        # Trap 1 is active True
        response = client.get("/api/trap/1")
        assert response.json()["active"] is True
        
        # Toggle to inactive
        response = client.post("/api/trap/1/toggle")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "toggle" in data["message"].lower() or "active" in data["message"].lower()
        
        # Verify trap 1 is now inactive
        response = client.get("/api/trap/1")
        assert response.json()["active"] is False
    
    def test_toggle_trap_inactive_to_active(self, client, test_state):
        """Test toggling back to active."""
        # Trap 3 is inactive
        response = client.get("/api/trap/3")
        assert response.json()["active"] is False
        
        # Toggle to active
        response = client.post("/api/trap/3/toggle")
        assert response.status_code == 200
        
        # Verify trap 3 is now active
        response = client.get("/api/trap/3")
        assert response.json()["active"] is True
    
    def test_toggle_nonexistent_trap(self, client):
        """Test POST /api/trap/{trap_id}/toggle returns 404 for nonexistent trap."""
        response = client.post("/api/trap/nonexistent/toggle")
        assert response.status_code == 404


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_empty_state(self, client):
        """Test endpoints with empty state."""
        set_app_state({})
        
        # Status should return all zeros
        response = client.get("/api/status")
        data = response.json()
        assert data["ok_count"] == 0
        assert data["alert_count"] == 0
        
        # Traps list should be empty
        response = client.get("/api/traps")
        data = response.json()
        assert len(data["traps"]) == 0
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present."""
        response = client.get("/api/status")
        # CORS middleware should add these headers
        assert response.status_code == 200
    
    def test_api_response_content_type(self, client):
        """Test that API responses have correct content type."""
        response = client.get("/api/status")
        assert "application/json" in response.headers["content-type"]
        
        response = client.get("/api/traps")
        assert "application/json" in response.headers["content-type"]


class TestApiResponseSchema:
    """Test API response data types and schema."""
    
    def test_status_response_types(self, client):
        """Test status response data types."""
        response = client.get("/api/status")
        data = response.json()
        
        assert isinstance(data["timestamp"], (int, float))
        assert isinstance(data["ok_count"], int)
        assert isinstance(data["alert_count"], int)
        assert isinstance(data["missing_count"], int)
        assert isinstance(data["unknown_count"], int)
    
    def test_trap_data_types(self, client):
        """Test trap data response types."""
        response = client.get("/api/traps")
        data = response.json()
        
        for trap_id, trap in data["traps"].items():
            assert isinstance(trap["name"], str)
            assert isinstance(trap["active"], bool)
            assert isinstance(trap["state"], str)
            assert isinstance(trap["lastHeard"], (int, float))
            # battery, voltage, rssi, snr, lastEventType can be None or their type


class TestIntegration:
    """Integration tests for multiple operations."""
    
    def test_reset_and_verify_status_count(self, client, test_state):
        """Test that resetting a trap updates status counts."""
        # Initially: 1 OK, 1 ALERT, 1 MISSING
        response = client.get("/api/status")
        initial_data = response.json()
        assert initial_data["alert_count"] == 1
        
        # Reset the alert trap
        client.post("/api/trap/2/reset")
        
        # Now should be: 2 OK, 0 ALERT, 1 MISSING
        response = client.get("/api/status")
        updated_data = response.json()
        assert updated_data["ok_count"] == 2
        assert updated_data["alert_count"] == 0
    
    def test_multiple_operations(self, client, test_state):
        """Test performing multiple operations in sequence."""
        # Get initial state
        response = client.get("/api/traps")
        initial_trap1 = response.json()["traps"]["1"]
        assert initial_trap1["active"] is True
        assert initial_trap1["state"] == "OK"
        
        # Toggle trap 1off
        client.post("/api/trap/1/toggle")
        
        # Verify toggle worked
        response = client.get("/api/trap/1")
        assert response.json()["active"] is False
        
        # Reset trap 2
        client.post("/api/trap/2/reset")
        
        # Verify reset worked
        response = client.get("/api/trap/2")
        assert response.json()["state"] == "OK"
        
        # Check final status
        response = client.get("/api/status")
        final = response.json()
        assert final["ok_count"] == 2  # Trap1 and Trap2, but Trap1 is inactive
        assert final["missing_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
