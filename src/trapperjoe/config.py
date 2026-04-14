"""
Configuration management for TrapperJoe.

Handles loading and validating configuration from trapperjoe_config.json
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any


def get_config_path() -> Path:
    """
    Determine the configuration file path.
    
    Priority:
    1. TRAPPERJOE_CONFIG environment variable
    2. ./config/trapperjoe_config.json (relative to cwd)
    
    Returns:
        Path to configuration file
    """
    env_config = os.getenv("TRAPPERJOE_CONFIG")
    if env_config:
        return Path(env_config)
    
    return Path.cwd() / "config" / "trapperjoe_config.json"


def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """
    Load configuration from JSON file.
    
    Args:
        config_path: Path to config file. If None, uses get_config_path()
        
    Returns:
        Configuration dictionary, or empty dict if file not found
    """
    if config_path is None:
        config_path = get_config_path()
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"[WARN] Config file not found: {config_path}")
        return {}
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        print(f"[CONFIG] Loaded from: {config_path}")
        return config
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in config: {e}")
        return {}
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        return {}


def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validate required configuration fields.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_sections = ["meshtastic", "email_config", "schedule_config"]
    
    for section in required_sections:
        if section not in config:
            print(f"[WARN] Missing config section: {section}")
    
    # Check meshtastic config
    mesh_cfg = config.get("meshtastic", {})
    if not mesh_cfg.get("host"):
        print("[WARN] meshtastic.host not configured")
    
    # Check email config
    email_cfg = config.get("email_config", {})
    if not email_cfg.get("user"):
        print("[WARN] email_config.user not configured")
    if not email_cfg.get("app_password"):
        print("[WARN] email_config.app_password not configured")
    if not email_cfg.get("recipients"):
        print("[WARN] email_config.recipients not configured")
    
    return True


def get_meshtastic_host(config: Dict[str, Any]) -> str:
    """Get Meshtastic host from config."""
    return config.get("meshtastic", {}).get("host", "192.168.178.76")


def get_meshtastic_port(config: Dict[str, Any]) -> int:
    """Get Meshtastic port from config."""
    return config.get("meshtastic", {}).get("port", 4403)


def get_email_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get email configuration."""
    return config.get("email_config", {})


def get_schedule_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get schedule configuration."""
    return config.get("schedule_config", {})


def get_timeout_hours(config: Dict[str, Any]) -> int:
    """Get device timeout in hours."""
    return config.get("schedule_config", {}).get("alive_timeout_hours", 24)


def get_schedule_times(config: Dict[str, Any]) -> list:
    """Get daily schedule times (e.g., ["06:45", "19:00"])."""
    return config.get("schedule_config", {}).get("schedule_times", [])
