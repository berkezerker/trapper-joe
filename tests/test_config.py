"""
Tests for config module.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from trapperjoe.config import (
    load_config,
    validate_config,
    get_meshtastic_host,
    get_meshtastic_port,
    get_email_config,
    get_schedule_config
)


def test_load_config_with_file(mock_config):
    """Test loading config from file."""
    cfg = load_config(mock_config)
    
    assert cfg is not None
    assert "meshtastic" in cfg
    assert "email_config" in cfg
    assert "schedule_config" in cfg


def test_load_config_nonexistent_file():
    """Test loading non-existent config returns empty dict."""
    cfg = load_config(Path("/nonexistent/config.json"))
    
    assert cfg == {}


def test_load_config_invalid_json(tmp_path):
    """Test loading invalid JSON returns empty dict."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json")
    
    cfg = load_config(bad_file)
    
    assert cfg == {}


def test_validate_config(mock_config):
    """Test config validation."""
    cfg = load_config(mock_config)
    assert validate_config(cfg) is True


def test_get_meshtastic_host(mock_config):
    """Test getting meshtastic host."""
    cfg = load_config(mock_config)
    host = get_meshtastic_host(cfg)
    
    assert host == "192.168.1.100"


def test_get_meshtastic_port(mock_config):
    """Test getting meshtastic port."""
    cfg = load_config(mock_config)
    port = get_meshtastic_port(cfg)
    
    assert port == 4403


def test_get_email_config(mock_config):
    """Test getting email config."""
    cfg = load_config(mock_config)
    email_cfg = get_email_config(cfg)
    
    assert email_cfg["user"] == "test@gmail.com"
    assert email_cfg["app_password"] == "test_password"
    assert len(email_cfg["recipients"]) == 1


def test_get_schedule_config(mock_config):
    """Test getting schedule config."""
    cfg = load_config(mock_config)
    sched_cfg = get_schedule_config(cfg)
    
    assert sched_cfg.get("alive_timeout_hours") == 24
    assert len(sched_cfg.get("schedule_times", [])) == 2


def test_get_config_missing_section():
    """Test getting config with missing sections."""
    cfg = {}
    
    assert get_meshtastic_host(cfg) == "192.168.178.76"  # default
    assert get_meshtastic_port(cfg) == 4403  # default
    assert get_email_config(cfg) == {}
    assert get_schedule_config(cfg) == {}
