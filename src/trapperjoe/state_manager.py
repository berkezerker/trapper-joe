"""
State management for trap data persistence.

Handles loading/saving trap state and state transitions.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


DEFAULT_STATE = {}


def get_state_file() -> Path:
    """Get path to state file (trap_state.json in cwd)."""
    return Path.cwd() / "trap_state.json"


def load_state(state_file: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load trap state from JSON file.
    
    Args:
        state_file: Path to state file. If None, uses get_state_file()
        
    Returns:
        State dictionary, or empty dict if file not found
    """
    if state_file is None:
        state_file = get_state_file()
    
    state_file = Path(state_file)
    
    if not state_file.exists():
        return {}
    
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in state file: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load state: {e}")
        return {}


def save_state(state: Dict[str, Any], state_file: Optional[Path] = None) -> bool:
    """
    Save trap state to JSON file atomically.
    
    Args:
        state: State dictionary to save
        state_file: Path to state file. If None, uses get_state_file()
        
    Returns:
        True if successful, False otherwise
    """
    if state_file is None:
        state_file = get_state_file()
    
    state_file = Path(state_file)
    
    try:
        # Atomic write: write to temp file, then rename
        tmp_file = state_file.with_suffix(".tmp")
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        tmp_file.replace(state_file)
        print(f"[STATE] Saved: {state_file.name}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed saving state: {e}")
        return False


def initialize_trap(trap_id: str, name: str = None) -> Dict[str, Any]:
    """
    Create a new trap entry in state.
    
    Args:
        trap_id: Node ID of the trap
        name: Optional friendly name for the trap
        
    Returns:
        New trap state dict
    """
    import time
    
    now = time.time()
    return {
        "name": name or trap_id,
        "active": True,
        "state": "OK",
        "last_processed_ts": now,
        "lastHeard": now,
        "battery": None,
        "voltage": None,
        "rssi": None,
        "snr": None,
        "lastEventType": None,
    }


def get_trap(state: Dict[str, Any], trap_id: str) -> Optional[Dict[str, Any]]:
    """Get trap data from state."""
    return state.get(trap_id)


def trap_exists(state: Dict[str, Any], trap_id: str) -> bool:
    """Check if trap is registered in state."""
    return trap_id in state and not trap_id.startswith("_")


def update_trap_state(state: Dict[str, Any], trap_id: str, update: Dict[str, Any]) -> bool:
    """
    Update trap state with new data.
    
    Args:
        state: State dictionary
        trap_id: Trap ID
        update: Dictionary of fields to update
        
    Returns:
        True if trap was updated, False if trap not found
    """
    if trap_id not in state:
        return False
    
    state[trap_id].update(update)
    return True


def get_trap_status(state: Dict[str, Any], trap_id: str) -> str:
    """Get trap status (OK, ALERT, MISSING, UNKNOWN)."""
    trap = state.get(trap_id)
    if not trap:
        return "UNKNOWN"
    return trap.get("state", "UNKNOWN")


def count_traps_by_status(state: Dict[str, Any]) -> Dict[str, int]:
    """
    Count traps by their status.
    
    Returns:
        Dictionary with counts: {"OK": 5, "ALERT": 1, "MISSING": 0}
    """
    counts = {"OK": 0, "ALERT": 0, "MISSING": 0, "UNKNOWN": 0}
    
    for trap_id, trap in state.items():
        if trap_id.startswith("_"):
            continue
        
        status = trap.get("state", "UNKNOWN")
        if status in counts:
            counts[status] += 1
        else:
            counts["UNKNOWN"] += 1
    
    return counts


def get_all_traps(state: Dict[str, Any]) -> list:
    """
    Get list of all registered traps (excluding metadata entries).
    
    Returns:
        List of (trap_id, trap_data) tuples
    """
    return [(tid, tdata) for tid, tdata in state.items() if not tid.startswith("_")]


def get_last_status_day(state: Dict[str, Any]) -> Optional[str]:
    """Get last day that status report was sent (YYYY-MM-DD format)."""
    return state.get("_last_status_day")


def set_last_status_day(state: Dict[str, Any], day: str) -> None:
    """Set last day status report was sent."""
    state["_last_status_day"] = day
