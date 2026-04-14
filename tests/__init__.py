"""
Pytest configuration and fixtures for TrapperJoe tests.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch


@pytest.fixture
def temp_config():
    """Create a temporary config file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        config = {
            "meshtastic": {
                "host": "192.168.1.100",
                "port": 4403
            },
            "email_config": {
                "user": "test@gmail.com",
                "app_password": "test_password",
                "recipients": ["recipient@example.com"]
            },
            "schedule_config": {
                "alive_timeout_hours": 24,
                "schedule_times": ["06:45", "19:00"]
            }
        }
        json.dump(config, f)
        f.flush()
        yield Path(f.name)
        Path(f.name).unlink()


@pytest.fixture
def temp_state():
    """Create a temporary state file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        state = {
            "12345": {
                "name": "Trap 1",
                "active": True,
                "state": "OK",
                "battery": 85,
                "voltage": 4.2,
                "rssi": -95,
                "snr": 8.5,
                "lastHeard": 1712000000,
                "lastEventType": "DETECTION"
            }
        }
        json.dump(state, f)
        f.flush()
        yield Path(f.name)
        Path(f.name).unlink()


@pytest.fixture
def mock_config(temp_config):
    """Mock config loading to use temp config."""
    with patch('trapperjoe.config.get_config_path', return_value=temp_config):
        yield temp_config


@pytest.fixture
def mock_state(temp_state):
    """Mock state loading to use temp state."""
    with patch('trapperjoe.state_manager.get_state_file', return_value=temp_state):
        yield temp_state


@pytest.fixture
def sample_trap_data():
    """Sample trap data for testing."""
    return {
        "id": "12345",
        "name": "Test Trap",
        "active": True,
        "state": "OK",
        "battery": 85,
        "voltage": 4.2,
        "rssi": -95,
        "snr": 8.5,
        "lastHeard": 1712000000,
        "lastEventType": "DETECTION"
    }


@pytest.fixture
def sample_message():
    """Sample incoming message for testing."""
    return {
        "id": "12345",
        "ts": 1712000000,
        "msg": "trap detected",
        "rssi": -90,
        "snr": 9.0
    }


@pytest.fixture
def mock_smtp():
    """Mock SMTP connection."""
    with patch('smtplib.SMTP') as mock:
        mock_instance = MagicMock()
        mock.return_value.__enter__.return_value = mock_instance
        yield mock_instance
