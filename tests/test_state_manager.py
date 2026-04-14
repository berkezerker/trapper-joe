"""
Tests for state_manager module.
"""

import pytest
import time
from pathlib import Path

from trapperjoe.state_manager import (
    load_state,
    save_state,
    initialize_trap,
    get_trap,
    trap_exists,
    update_trap_state,
    get_trap_status,
    count_traps_by_status,
    get_all_traps,
    get_last_status_day,
    set_last_status_day
)


def test_load_state_with_file(mock_state):
    """Test loading state from file."""
    state = load_state(mock_state)
    
    assert state is not None
    assert "12345" in state
    assert state["12345"]["name"] == "Trap 1"


def test_load_state_nonexistent():
    """Test loading state from nonexistent file returns empty dict."""
    state = load_state(Path("/nonexistent/state.json"))
    
    assert state == {}


def test_save_state(tmp_path):
    """Test saving state to file."""
    state_file = tmp_path / "state.json"
    state = {
        "trap1": {"name": "Trap 1", "state": "OK"},
        "trap2": {"name": "Trap 2", "state": "ALERT"}
    }
    
    result = save_state(state, state_file)
    
    assert result is True
    assert state_file.exists()
    
    loaded = load_state(state_file)
    assert loaded["trap1"]["name"] == "Trap 1"


def test_initialize_trap():
    """Test initializing a new trap."""
    trap = initialize_trap("12345", "Test Trap")
    
    assert trap["name"] == "Test Trap"
    assert trap["active"] is True
    assert trap["state"] == "OK"
    assert "lastHeard" in trap
    assert trap["battery"] is None


def test_get_trap():
    """Test getting trap from state."""
    state = {
        "trap1": {"name": "Trap 1", "state": "OK"}
    }
    
    trap = get_trap(state, "trap1")
    assert trap["name"] == "Trap 1"
    
    # Non-existent trap
    trap = get_trap(state, "trap2")
    assert trap is None


def test_trap_exists():
    """Test checking if trap exists."""
    state = {
        "trap1": {"name": "Trap 1"},
        "_metadata": {"key": "value"}
    }
    
    assert trap_exists(state, "trap1") is True
    assert trap_exists(state, "trap2") is False
    assert trap_exists(state, "_metadata") is False  # metadata key


def test_update_trap_state():
    """Test updating trap state."""
    state = {
        "trap1": {"name": "Trap 1", "state": "OK"}
    }
    
    result = update_trap_state(state, "trap1", {"state": "ALERT", "battery": 50})
    
    assert result is True
    assert state["trap1"]["state"] == "ALERT"
    assert state["trap1"]["battery"] == 50
    assert state["trap1"]["name"] == "Trap 1"  # unchanged


def test_get_trap_status():
    """Test getting trap status."""
    state = {
        "trap1": {"state": "OK"},
        "trap2": {"state": "ALERT"},
        "trap3": {}
    }
    
    assert get_trap_status(state, "trap1") == "OK"
    assert get_trap_status(state, "trap2") == "ALERT"
    assert get_trap_status(state, "trap3") == "UNKNOWN"
    assert get_trap_status(state, "trap4") == "UNKNOWN"


def test_count_traps_by_status():
    """Test counting traps by status."""
    state = {
        "trap1": {"state": "OK"},
        "trap2": {"state": "OK"},
        "trap3": {"state": "ALERT"},
        "trap4": {"state": "MISSING"},
        "_metadata": {}
    }
    
    counts = count_traps_by_status(state)
    
    assert counts["OK"] == 2
    assert counts["ALERT"] == 1
    assert counts["MISSING"] == 1
    assert counts["UNKNOWN"] == 0


def test_get_all_traps():
    """Test getting all registered traps."""
    state = {
        "trap1": {"name": "Trap 1"},
        "trap2": {"name": "Trap 2"},
        "_metadata": {}
    }
    
    traps = get_all_traps(state)
    
    assert len(traps) == 2
    assert ("trap1", {"name": "Trap 1"}) in traps
    assert ("trap2", {"name": "Trap 2"}) in traps


def test_last_status_day():
    """Test getting/setting last status day."""
    state = {}
    
    # Initially None
    assert get_last_status_day(state) is None
    
    # Set day
    set_last_status_day(state, "2026-04-12")
    assert get_last_status_day(state) == "2026-04-12"
