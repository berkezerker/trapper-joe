"""
Tests for utils module.
"""

import pytest
from datetime import datetime

from trapperjoe.utils import (
    format_ts,
    convert_to_serializable,
    time_since_seconds,
    get_signal_quality,
    safe_get_nested
)


def test_format_ts():
    """Test timestamp formatting."""
    # Valid timestamp
    ts = 1712000000
    result = format_ts(ts)
    assert isinstance(result, str)
    assert "2024" in result or "2025" in result or "2026" in result
    
    # None
    assert format_ts(None) == "N/A"
    
    # Zero
    assert format_ts(0) == "N/A"
    
    # Empty string
    assert format_ts("") == "N/A"


def test_convert_to_serializable():
    """Test converting objects to serializable format."""
    # Dict
    assert convert_to_serializable({"a": 1}) == {"a": 1}
    
    # List
    assert convert_to_serializable([1, 2, 3]) == [1, 2, 3]
    
    # bytes
    assert convert_to_serializable(b"hello") == "68656c6c6f"
    
    # Nested
    result = convert_to_serializable({"data": b"test", "list": [1, b"data"]})
    assert result["data"] == "74657374"
    assert result["list"][1] == "64617461"


def test_time_since_seconds():
    """Test time duration formatting."""
    assert time_since_seconds(45) == "45s"
    assert time_since_seconds(60) == "1m"
    assert time_since_seconds(3600) == "1h"
    assert time_since_seconds(3900) == "1h 5m"
    assert time_since_seconds(86400) == "1d"
    assert time_since_seconds(90000) == "1d 1h"


def test_get_signal_quality():
    """Test signal quality assessment."""
    # Excellent
    quality, color = get_signal_quality(-70)
    assert quality == "Excellent"
    assert color == "#28a745"
    
    # Good
    quality, color = get_signal_quality(-90)
    assert quality == "Good"
    assert color == "#ffc107"
    
    # Poor
    quality, color = get_signal_quality(-110)
    assert quality == "Poor"
    assert color == "#dc3545"
    
    # Invalid
    quality, color = get_signal_quality(None)
    assert quality == "Unknown"
    assert color == "#6c757d"


def test_safe_get_nested():
    """Test safe nested dict access."""
    data = {
        "a": {
            "b": {
                "c": "value"
            }
        },
        "x": "y"
    }
    
    # Valid path
    assert safe_get_nested(data, ["a", "b", "c"]) == "value"
    
    # Partial path
    assert safe_get_nested(data, ["a", "b"]) == {"c": "value"}
    
    # Invalid path
    assert safe_get_nested(data, ["a", "z"]) is None
    
    # With default
    assert safe_get_nested(data, ["x", "y"], default="default") == "default"
    
    # Top level
    assert safe_get_nested(data, ["x"]) == "y"
