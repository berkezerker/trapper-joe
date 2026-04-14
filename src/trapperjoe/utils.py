"""
Utility functions for TrapperJoe.

Includes time formatting, logging setup, and other helpers.
"""

import logging
import sys
from datetime import datetime


def format_ts(ts: float) -> str:
    """
    Format Unix timestamp to readable string.
    
    Args:
        ts: Unix timestamp (seconds since epoch)
        
    Returns:
        Formatted datetime string "YYYY-MM-DD HH:MM:SS" or "N/A" if invalid
    """
    if not ts:
        return "N/A"
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return "N/A"


def setup_logging(name: str = "trapperjoe", level: int = logging.INFO) -> logging.Logger:
    """
    Setup basic logging configuration.
    
    Args:
        name: Logger name
        level: Logging level (default: INFO)
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Console handler
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def convert_to_serializable(obj):
    """
    Convert non-JSON-serializable objects to serializable format.
    
    Handles:
    - bytes/bytearray → hex string
    - Objects with __dict__ → dict
    - Recursive conversion for dicts and lists
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON-serializable version of object
    """
    if isinstance(obj, dict):
        return {k: convert_to_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, (bytes, bytearray)):
        return obj.hex()
    elif hasattr(obj, "__dict__"):
        return convert_to_serializable(obj.__dict__)
    else:
        return obj


def time_since_seconds(seconds: int) -> str:
    """
    Convert seconds to human-readable duration.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable string like "2h 30m" or "45s"
    """
    if seconds < 60:
        return f"{seconds}s"
    
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        if remaining_minutes:
            return f"{hours}h {remaining_minutes}m"
        return f"{hours}h"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours:
        return f"{days}d {remaining_hours}h"
    return f"{days}d"


def get_signal_quality(rssi: float) -> tuple:
    """
    Get signal quality assessment from RSSI.
    
    Args:
        rssi: RSSI value in dBm
        
    Returns:
        Tuple of (quality_description, color_hex)
        Colors: green (#28a745), yellow (#ffc107), red (#dc3545)
    """
    if not rssi or isinstance(rssi, str):
        return ("Unknown", "#6c757d")
    
    try:
        rssi_val = float(rssi)
        if rssi_val > -80:
            return ("Excellent", "#28a745")
        elif rssi_val > -100:
            return ("Good", "#ffc107")
        else:
            return ("Poor", "#dc3545")
    except (ValueError, TypeError):
        return ("Unknown", "#6c757d")


def safe_get_nested(obj: dict, keys: list, default=None):
    """
    Safely get value from nested dictionary.
    
    Args:
        obj: Dictionary to access
        keys: List of keys to traverse (e.g., ["a", "b", "c"])
        default: Default value if key not found
        
    Returns:
        Value at nested path or default
    """
    for key in keys:
        if isinstance(obj, dict):
            obj = obj.get(key)
        else:
            return default
    return obj if obj is not None else default
