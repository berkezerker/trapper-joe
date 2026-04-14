"""
TrapperJoe - Automated remote monitoring system for wildlife traps using Meshtastic mesh networking.

This package provides:
- Real-time trap monitoring via Meshtastic mesh network
- Email alerts on trap activation and device status changes
- State management and persistence
- Admin command processing
- Integrated listener and notifier (single process)

Entry point: Use the `trapperjoe` CLI command or `python -m trapperjoe`
"""

__version__ = "0.1.0"
__author__ = "Frank"
__license__ = "MIT"

__all__ = [
    "MeshtasticListener",
    "load_config",
    "load_state",
]

from trapperjoe.listener import MeshtasticListener
from trapperjoe.config import load_config
from trapperjoe.state_manager import load_state

__doc__ += f"\n\nVersion: {__version__}"
