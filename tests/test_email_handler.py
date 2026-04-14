"""
Tests for email_handler module.
"""

import pytest
from unittest.mock import patch, MagicMock

from trapperjoe.email_handler import (
    send_email_html,
    html_status_report,
    html_alert_mail,
    html_reset_mail,
    get_email_style
)


def test_get_email_style():
    """Test email style generation."""
    style = get_email_style()
    
    assert "<style>" in style
    assert ".container" in style
    assert ".header" in style


def test_send_email_html_success(mock_smtp):
    """Test successful email sending."""
    email_config = {
        "user": "test@gmail.com",
        "app_password": "password",
        "recipients": ["recipient@example.com"]
    }
    
    result = send_email_html("Test Subject", "<h1>Test</h1>", email_config)
    
    assert result is True
    mock_smtp.starttls.assert_called_once()
    mock_smtp.login.assert_called_once()
    mock_smtp.sendmail.assert_called_once()


def test_send_email_html_no_config():
    """Test email sending with missing config."""
    result = send_email_html("Test Subject", "<h1>Test</h1>", {})
    
    assert result is False


def test_send_email_html_failure(mock_smtp):
    """Test email sending failure."""
    mock_smtp.login.side_effect = Exception("Auth failed")
    
    email_config = {
        "user": "test@gmail.com",
        "app_password": "password",
        "recipients": ["recipient@example.com"]
    }
    
    result = send_email_html("Test Subject", "<h1>Test</h1>", email_config)
    
    assert result is False


def test_html_status_report():
    """Test status report generation."""
    state = {
        "trap1": {
            "name": "Trap 1",
            "state": "OK",
            "battery": 85,
            "voltage": 4.2,
            "rssi": -95,
            "snr": 8.5,
            "lastHeard": 1712000000,
            "lastEventType": "DETECTION"
        },
        "trap2": {
            "name": "Trap 2",
            "state": "ALERT",
            "battery": 50,
            "voltage": 3.8,
            "rssi": -110,
            "snr": 2.0,
            "lastHeard": 1712000000,
            "lastEventType": "DETECTION"
        }
    }
    
    config = {
        "schedule_config": {
            "alive_timeout_hours": 24,
            "schedule_times": ["06:45", "19:00"]
        }
    }
    
    html = html_status_report(state, config)
    
    assert "<!DOCTYPE html>" in html
    assert "Trap 1" in html
    assert "Trap 2" in html
    assert "status-ok" in html.lower() or "ok" in html.lower()
    assert "85%" in html


def test_html_alert_mail():
    """Test alert email generation."""
    trap_data = {
        "name": "Test Trap",
        "state": "ALERT",
        "battery": 75,
        "voltage": 4.0,
        "rssi": -95,
        "snr": 8.5,
        "lastHeard": 1712000000,
        "lastEventType": "DETECTION"
    }
    
    state = {"trap1": trap_data}
    config = {"schedule_config": {}}
    
    html = html_alert_mail("trap1", trap_data, state, config)
    
    assert "<!DOCTYPE html>" in html
    assert "ALARM" in html
    assert "Test Trap" in html
    assert "trap1" in html
    assert "ALERT" in html


def test_html_reset_mail():
    """Test reset email generation."""
    trap_data = {
        "name": "Test Trap",
        "state": "OK",
        "lastHeard": 1712000000
    }
    
    state = {"trap1": trap_data}
    config = {"schedule_config": {}}
    
    html = html_reset_mail("trap1", trap_data, state, config)
    
    assert "<!DOCTYPE html>" in html
    assert "Reset" in html
    assert "Test Trap" in html
    assert "trap1" in html
    assert "status-ok" in html.lower() or "ok" in html.lower()
