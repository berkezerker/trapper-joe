"""
Email handling for TrapperJoe alerts and reports.

Provides email sending via Gmail SMTP and HTML template generation.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, Any, List, Optional

from trapperjoe.utils import format_ts, get_signal_quality


def get_email_style() -> str:
    """Get common CSS styling for all HTML emails."""
    return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .header h1 { margin: 0; font-size: 28px; }
        .header p { margin: 10px 0 0 0; opacity: 0.9; }
        .content { padding: 30px; }
        .summary-cards { display: flex; gap: 15px; margin-bottom: 30px; flex-wrap: wrap; }
        .card { flex: 1; min-width: 150px; padding: 20px; border-radius: 8px; text-align: center; }
        .card-ok { background: #d4edda; border-left: 4px solid #28a745; }
        .card-alert { background: #f8d7da; border-left: 4px solid #dc3545; }
        .card-missing { background: #fff3cd; border-left: 4px solid #ffc107; }
        .card h3 { margin: 0; font-size: 32px; color: #333; }
        .card p { margin: 5px 0 0 0; color: #666; font-size: 14px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #f8f9fa; padding: 12px; text-align: left; font-weight: 600; color: #495057; border-bottom: 2px solid #dee2e6; }
        td { padding: 12px; border-bottom: 1px solid #dee2e6; }
        tr:hover { background: #f8f9fa; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
        .status-ok { background: #28a745; color: white; }
        .status-alert { background: #dc3545; color: white; }
        .status-missing { background: #ffc107; color: #333; }
        .status-unknown { background: #6c757d; color: white; }
        .footer { background: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }
        .alert-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .trap-details { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .trap-details h3 { margin-top: 0; color: #dc3545; }
        .detail-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #dee2e6; }
        .detail-label { font-weight: 600; color: #495057; }
        .detail-value { color: #6c757d; }
    </style>
    """


def send_email_html(
    subject: str,
    html_body: str,
    email_config: Dict[str, Any]
) -> bool:
    """
    Send HTML email via Gmail SMTP.
    
    Args:
        subject: Email subject
        html_body: HTML body content
        email_config: Dict with keys: user, app_password, recipients
        
    Returns:
        True if successful, False otherwise
    """
    if not email_config or not email_config.get("user"):
        print(f"[WARN] Email not configured, skipping: {subject}")
        return False
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config.get("user", "")
    msg["To"] = ", ".join(email_config.get("recipients", []))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(
                email_config.get("user", ""),
                email_config.get("app_password", "")
            )
            server.sendmail(
                msg["From"],
                email_config.get("recipients", []),
                msg.as_string()
            )
        print(f"[EMAIL] ✉️ Sent: {subject}")
        return True
    except Exception as e:
        print(f"[EMAIL] ❌ Failed: {e}")
        return False


def html_status_report(
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Generate HTML status report for all traps.
    
    Args:
        state: Trap state dictionary
        config: Configuration dictionary
        
    Returns:
        HTML string
    """
    counts = {"OK": 0, "ALERT": 0, "MISSING": 0, "UNKNOWN": 0}
    traps = []
    
    for trap_id, t in state.items():
        if trap_id.startswith("_"):
            continue
        traps.append((trap_id, t))
        status = t.get("state", "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    
    cards = f"""
    <div class="summary-cards">
        <div class="card card-ok">
            <h3>{counts['OK']}</h3>
            <p>✅ Operational</p>
        </div>
        <div class="card card-alert">
            <h3>{counts['ALERT']}</h3>
            <p>⚠️ Alert Active</p>
        </div>
        <div class="card card-missing">
            <h3>{counts['MISSING']}</h3>
            <p>📡 No Connection</p>
        </div>
    </div>
    """
    
    rows = ""
    for trap_id, t in sorted(traps, key=lambda x: x[1].get("name", x[0])):
        status = t.get("state", "UNKNOWN")
        badge_class = f"status-{status.lower()}"
        name = t.get("name", trap_id)
        
        battery = t.get("battery", "N/A")
        if battery != "N/A" and battery is not None:
            battery = f"{battery}%"
        
        voltage = t.get("voltage", "N/A")
        if voltage != "N/A" and voltage is not None:
            voltage = f"{voltage}V"
        
        rssi = t.get("rssi", "N/A")
        snr = t.get("snr", "N/A")
        
        _, rssi_color = get_signal_quality(rssi)
        last_msg = t.get("lastEventType", "No Events")
        
        rows += f"""
        <tr>
            <td><strong>{name}</strong><br><small style="color:#6c757d;">{trap_id}</small></td>
            <td><span class="status-badge {badge_class}">{status}</span></td>
            <td>{format_ts(t.get('lastHeard'))}</td>
            <td>{battery}</td>
            <td>{voltage}</td>
            <td style="color:{rssi_color};"><strong>{rssi}</strong> dBm</td>
            <td>{snr} dB</td>
            <td style="font-size:13px;">{last_msg}</td>
        </tr>
        """
    
    timeout = config.get('schedule_config', {}).get('alive_timeout_hours', 'N/A')
    times = ', '.join(config.get('schedule_config', {}).get('schedule_times', []))
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {get_email_style()}
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 TrapperJoe Status Report</h1>
                <p>{datetime.now().strftime("%d.%m.%Y %H:%M:%S")}</p>
            </div>
            <div class="content">
                {cards}
                
                <h2 style="margin-top:30px; color:#333;">All Traps Overview</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Trap</th>
                            <th>Status</th>
                            <th>Last Update</th>
                            <th>Battery</th>
                            <th>Voltage</th>
                            <th>RSSI</th>
                            <th>SNR</th>
                            <th>Event</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                
                <div style="margin-top:30px; padding:15px; background:#f8f9fa; border-radius:8px;">
                    <p style="margin:5px 0; color:#6c757d;"><strong>⏰ Scheduled Reports:</strong> {times}</p>
                    <p style="margin:5px 0; color:#6c757d;"><strong>⏱️ Timeout:</strong> {timeout} hours</p>
                </div>
            </div>
            <div class="footer">
                TrapperJoe Monitoring System | Auto-generated
            </div>
        </div>
    </body>
    </html>
    """


def html_alert_mail(
    trap_id: str,
    trap_data: Dict[str, Any],
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Generate alert email for trap activation.
    
    Args:
        trap_id: ID of trap that triggered
        trap_data: Trap state data
        state: Full system state
        config: Configuration
        
    Returns:
        HTML string
    """
    name = trap_data.get("name", trap_id)
    battery = trap_data.get("battery", "N/A")
    if battery != "N/A" and battery is not None:
        battery = f"{battery}%"
    
    voltage = trap_data.get("voltage", "N/A")
    if voltage != "N/A" and voltage is not None:
        voltage = f"{voltage}V"
    
    rssi = trap_data.get("rssi", "N/A")
    snr = trap_data.get("snr", "N/A")
    last_event = trap_data.get("lastEventType", "No Events")
    last_heard = format_ts(trap_data.get("lastHeard"))
    
    signal_quality, signal_color = get_signal_quality(rssi)
    
    other_alerts = sum(
        1 for tid, t in state.items()
        if not tid.startswith("_") and tid != trap_id and t.get("state") == "ALERT"
    )
    
    alert_info = ""
    if other_alerts > 0:
        alert_info = f"""
        <div class="alert-box">
            ⚠️ <strong>Note:</strong> There are {other_alerts} other active alarms in the system.
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {get_email_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
                <h1>🚨 ALARM TRIGGERED</h1>
                <p>A trap has detected an event</p>
            </div>
            <div class="content">
                {alert_info}
                
                <div class="trap-details">
                    <h3>🎯 Affected Trap: {name}</h3>
                    
                    <div class="detail-row">
                        <span class="detail-label">Trap ID:</span>
                        <span class="detail-value">{trap_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value"><span class="status-badge status-alert">ALERT</span></span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Time:</span>
                        <span class="detail-value">{last_heard}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Battery:</span>
                        <span class="detail-value">{battery}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Voltage:</span>
                        <span class="detail-value">{voltage}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">RSSI:</span>
                        <span class="detail-value" style="color:{signal_color};"><strong>{rssi} dBm</strong> ({signal_quality})</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">SNR:</span>
                        <span class="detail-value">{snr} dB</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Event:</span>
                        <span class="detail-value">{last_event}</span>
                    </div>
                </div>
                
                <div style="background:#fff3cd; padding:15px; border-radius:8px; margin-top:20px;">
                    <p style="margin:0; color:#856404;">
                        <strong>📋 Next Steps:</strong><br>
                        1. Check trap and verify catch<br>
                        2. Reset if needed: <code>trap -reset</code><br>
                        3. Get full status: <code>trap -statusmail</code>
                    </p>
                </div>
            </div>
            <div class="footer">
                TrapperJoe Monitoring System | Auto-generated
            </div>
        </div>
    </body>
    </html>
    """


def html_reset_mail(
    trap_id: str,
    trap_data: Dict[str, Any],
    state: Dict[str, Any],
    config: Dict[str, Any]
) -> str:
    """
    Generate reset confirmation email.
    
    Args:
        trap_id: ID of reset trap
        trap_data: Trap state data
        state: Full system state
        config: Configuration
        
    Returns:
        HTML string
    """
    name = trap_data.get("name", trap_id)
    last_heard = format_ts(trap_data.get("lastHeard"))
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {get_email_style()}
    </head>
    <body>
        <div class="container">
            <div class="header" style="background: linear-gradient(135deg, #6f86d6 0%, #48dbfb 100%);">
                <h1>🔄 Trap Reset</h1>
                <p>A trap has been successfully reset</p>
            </div>
            <div class="content">
                <div class="trap-details">
                    <h3 style="color:#6f86d6;">✅ Trap: {name}</h3>
                    
                    <div class="detail-row">
                        <span class="detail-label">Trap ID:</span>
                        <span class="detail-value">{trap_id}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value"><span class="status-badge status-ok">OK</span></span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Reset Time:</span>
                        <span class="detail-value">{last_heard}</span>
                    </div>
                </div>
                
                <div style="background:#d4edda; padding:15px; border-radius:8px; margin-top:20px; border-left:4px solid #28a745;">
                    <p style="margin:0; color:#155724;">
                        ✅ The trap is now operational and actively monitoring.
                    </p>
                </div>
            </div>
            <div class="footer">
                TrapperJoe Monitoring System | Auto-generated
            </div>
        </div>
    </body>
    </html>
    """
