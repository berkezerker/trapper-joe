"""
FastAPI web server for TrapperJoe trap status dashboard.

Serves HTML dashboard and REST API for trap data.
"""

import time
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from trapperjoe import state_manager
from trapperjoe.utils import format_ts, get_signal_quality


# Request/Response Models
class TrapData(BaseModel):
    """Trap data model."""
    name: str
    active: bool
    state: str
    lastHeard: float
    battery: Optional[float]
    voltage: Optional[float]
    rssi: Optional[float]
    snr: Optional[float]
    lastEventType: Optional[str]


class StatusResponse(BaseModel):
    """Status summary response."""
    timestamp: float
    ok_count: int
    alert_count: int
    missing_count: int
    unknown_count: int


class TrapsListResponse(BaseModel):
    """List of all traps."""
    timestamp: float
    traps: Dict[str, TrapData]


class ApiResponse(BaseModel):
    """Generic API response."""
    success: bool
    message: str


# Global state reference
_app_state = {"state": {}, "lock": threading.Lock()}


def create_app() -> FastAPI:
    """Create and configure FastAPI app."""
    app = FastAPI(
        title="TrapperJoe Web Dashboard",
        description="Monitor trap status and manage traps",
        version="1.0.0"
    )
    
    # CORS middleware (allow all origins for LAN use)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/", response_class=HTMLResponse)
    async def get_dashboard():
        """Serve the main dashboard."""
        return get_dashboard_html()
    
    @app.get("/api/status", response_model=StatusResponse)
    async def get_status():
        """Get trap count summary."""
        with _app_state["lock"]:
            state = _app_state["state"]
        
        counts = state_manager.count_traps_by_status(state)
        
        return StatusResponse(
            timestamp=time.time(),
            ok_count=counts.get("OK", 0),
            alert_count=counts.get("ALERT", 0),
            missing_count=counts.get("MISSING", 0),
            unknown_count=counts.get("UNKNOWN", 0),
        )
    
    @app.get("/api/traps", response_model=TrapsListResponse)
    async def get_traps():
        """Get all trap data."""
        with _app_state["lock"]:
            state = _app_state["state"]
        
        traps = {}
        for trap_id, trap_data in state_manager.get_all_traps(state):
            traps[trap_id] = TrapData(
                name=trap_data.get("name", trap_id),
                active=trap_data.get("active", True),
                state=trap_data.get("state", "UNKNOWN"),
                lastHeard=trap_data.get("lastHeard", 0),
                battery=trap_data.get("battery"),
                voltage=trap_data.get("voltage"),
                rssi=trap_data.get("rssi"),
                snr=trap_data.get("snr"),
                lastEventType=trap_data.get("lastEventType"),
            )
        
        return TrapsListResponse(
            timestamp=time.time(),
            traps=traps
        )
    
    @app.get("/api/trap/{trap_id}", response_model=TrapData)
    async def get_trap(trap_id: str):
        """Get individual trap data."""
        with _app_state["lock"]:
            state = _app_state["state"]
        
        trap = state_manager.get_trap(state, trap_id)
        if not trap:
            raise HTTPException(status_code=404, detail=f"Trap {trap_id} not found")
        
        return TrapData(
            name=trap.get("name", trap_id),
            active=trap.get("active", True),
            state=trap.get("state", "UNKNOWN"),
            lastHeard=trap.get("lastHeard", 0),
            battery=trap.get("battery"),
            voltage=trap.get("voltage"),
            rssi=trap.get("rssi"),
            snr=trap.get("snr"),
            lastEventType=trap.get("lastEventType"),
        )
    
    @app.post("/api/trap/{trap_id}/reset", response_model=ApiResponse)
    async def reset_trap(trap_id: str):
        """Reset trap status to OK."""
        with _app_state["lock"]:
            state = _app_state["state"]
            
            if not state_manager.trap_exists(state, trap_id):
                raise HTTPException(status_code=404, detail=f"Trap {trap_id} not found")
            
            # Reset the trap state
            update = {
                "state": "OK",
                "last_processed_ts": time.time(),
            }
            state_manager.update_trap_state(state, trap_id, update)
            
            # Save the updated state
            state_manager.save_state(state)
        
        return ApiResponse(
            success=True,
            message=f"Trap {trap_id} reset to OK"
        )
    
    @app.post("/api/trap/{trap_id}/toggle", response_model=ApiResponse)
    async def toggle_trap_active(trap_id: str):
        """Toggle trap active status."""
        with _app_state["lock"]:
            state = _app_state["state"]
            
            if not state_manager.trap_exists(state, trap_id):
                raise HTTPException(status_code=404, detail=f"Trap {trap_id} not found")
            
            trap = state_manager.get_trap(state, trap_id)
            new_active = not trap.get("active", True)
            
            update = {
                "active": new_active,
                "last_processed_ts": time.time(),
            }
            state_manager.update_trap_state(state, trap_id, update)
            
            # Save the updated state
            state_manager.save_state(state)
        
        return ApiResponse(
            success=True,
            message=f"Trap {trap_id} active set to {new_active}"
        )
    
    return app


def get_dashboard_html() -> str:
    """Generate dashboard HTML with embedded CSS and JS."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TrapperJoe - Trap Status Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --ok-color: #28a745;
            --alert-color: #dc3545;
            --missing-color: #ffc107;
            --unknown-color: #6c757d;
        }
        
        body {
            background-color: #f8f9fa;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .navbar {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .navbar-brand {
            font-weight: bold;
            font-size: 1.5rem;
        }
        
        .header-info {
            color: rgba(255, 255, 255, 0.8);
            font-size: 0.9rem;
        }
        
        .container-main {
            max-width: 1200px;
            margin: 30px auto;
            padding: 0 15px;
        }
        
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card-summary {
            background: white;
            border-radius: 10px;
            padding: 25px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
            border-left: 5px solid;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .card-summary:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .card-ok { border-left-color: var(--ok-color); }
        .card-alert { border-left-color: var(--alert-color); }
        .card-missing { border-left-color: var(--missing-color); }
        .card-unknown { border-left-color: var(--unknown-color); }
        
        .card-count {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 10px 0;
        }
        
        .card-ok .card-count { color: var(--ok-color); }
        .card-alert .card-count { color: var(--alert-color); }
        .card-missing .card-count { color: var(--missing-color); }
        .card-unknown .card-count { color: var(--unknown-color); }
        
        .card-label {
            color: #666;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
            color: white;
        }
        
        .badge-ok { background-color: var(--ok-color); }
        .badge-alert { background-color: var(--alert-color); }
        .badge-missing { background-color: var(--missing-color); }
        .badge-unknown { background-color: var(--unknown-color); }
        
        .trap-table {
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            overflow: hidden;
        }
        
        .trap-table table {
            margin-bottom: 0;
        }
        
        .trap-table thead {
            background: #f8f9fa;
            border-bottom: 2px solid #dee2e6;
        }
        
        .trap-table th {
            padding: 15px;
            font-weight: 600;
            color: #495057;
            border: none;
        }
        
        .trap-table td {
            padding: 15px;
            border-bottom: 1px solid #dee2e6;
            vertical-align: middle;
        }
        
        .trap-table tbody tr:hover {
            background-color: #f8f9fa;
        }
        
        .trap-name {
            font-weight: 600;
            color: #333;
        }
        
        .trap-actions {
            display: flex;
            gap: 5px;
            flex-wrap: wrap;
        }
        
        .trap-actions button {
            padding: 4px 8px;
            font-size: 0.8rem;
        }
        
        .active-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        
        .active-badge.yes { background: #d4edda; color: #28a745; }
        .active-badge.no { background: #f8d7da; color: #dc3545; }
        
        .controls-section {
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
        }
        
        .last-update {
            color: #666;
            font-size: 0.9rem;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid var(--alert-color);
        }
        
        .admin-panel {
            background: #fff3cd;
            padding: 15px;
            border-left: 4px solid var(--missing-color);
            border-radius: 5px;
            margin-top: 20px;
            display: none;
        }
        
        .admin-panel.show {
            display: block;
        }
        
        @media (max-width: 768px) {
            .summary-cards {
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            }
            
            .trap-table table {
                font-size: 0.9rem;
            }
            
            .trap-table th, .trap-table td {
                padding: 10px;
            }
            
            .trap-actions button {
                padding: 3px 6px;
                font-size: 0.7rem;
            }
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <div class="container-fluid">
            <span class="navbar-brand">🪤 TrapperJoe Dashboard</span>
            <span class="header-info">Real-time trap monitoring</span>
        </div>
    </nav>
    
    <div class="container-main">
        <div class="controls-section">
            <div>
                <button class="btn btn-outline-secondary btn-sm" onclick="refreshData()">
                    🔄 Refresh Now
                </button>
                <button class="btn btn-outline-info btn-sm" onclick="toggleAdminPanel()">
                    ⚙️ Admin
                </button>
            </div>
            <div class="last-update">
                Last updated: <span id="lastUpdate">--</span>
            </div>
        </div>
        
        <div id="errorContainer"></div>
        
        <div id="statusCards" class="summary-cards loading">
            Loading...
        </div>
        
        <div class="trap-table">
            <table id="trapTable">
                <thead>
                    <tr>
                        <th>Trap Name</th>
                        <th>Status</th>
                        <th>Active</th>
                        <th>Last Heard</th>
                        <th>Battery %</th>
                        <th>Voltage (V)</th>
                        <th>RSSI (dBm)</th>
                        <th>SNR (dB)</th>
                        <th>Last Event</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="trapTableBody">
                    <tr><td colspan="10" class="loading">Loading trap data...</td></tr>
                </tbody>
            </table>
        </div>
        
        <div class="admin-panel" id="adminPanel">
            <h5>⚙️ Admin Functions</h5>
            <p><strong>⚠️ Note:</strong> Admin functions are available without authentication. Use in trusted networks only.</p>
            <p>Admin actions will be performed on individual traps via the Actions column above.</p>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const REFRESH_INTERVAL = 5000; // 5 seconds
        let refreshTimer = null;
        
        // Format timestamp to readable date-time
        function formatTime(timestamp) {
            if (!timestamp) return 'N/A';
            return new Date(timestamp * 1000).toLocaleString();
        }
        
        // Format time ago (e.g., "5 minutes ago")
        function formatTimeAgo(timestamp) {
            if (!timestamp) return 'N/A';
            const now = Math.floor(Date.now() / 1000);
            const diff = now - timestamp;
            
            if (diff < 60) return 'Just now';
            if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
            if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
            return Math.floor(diff / 86400) + 'd ago';
        }
        
        // Get status badge CSS class
        function getStatusClass(status) {
            const map = {
                'OK': 'badge-ok',
                'ALERT': 'badge-alert',
                'MISSING': 'badge-missing',
                'UNKNOWN': 'badge-unknown'
            };
            return map[status] || 'badge-unknown';
        }
        
        // Get card-status CSS class
        function getCardClass(status) {
            const map = {
                'OK': 'card-ok',
                'ALERT': 'card-alert',
                'MISSING': 'card-missing',
                'UNKNOWN': 'card-unknown'
            };
            return map[status] || 'card-unknown';
        }
        
        // Get label for status card
        function getStatusLabel(status) {
            const map = {
                'ok_count': 'OK / Operational',
                'alert_count': 'ALERT / Critical',
                'missing_count': 'MISSING / Not Heard',
                'unknown_count': 'UNKNOWN'
            };
            return map[status] || status;
        }
        
        // Clear error message
        function clearError() {
            document.getElementById('errorContainer').innerHTML = '';
        }
        
        // Show error message
        function showError(message) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message';
            errorDiv.textContent = '❌ ' + message;
            document.getElementById('errorContainer').innerHTML = '';
            document.getElementById('errorContainer').appendChild(errorDiv);
        }
        
        // Refresh dashboard data
        async function refreshData() {
            try {
                clearError();
                
                const [statusRes, trapsRes] = await Promise.all([
                    fetch('/api/status'),
                    fetch('/api/traps')
                ]);
                
                if (!statusRes.ok || !trapsRes.ok) {
                    throw new Error('Failed to fetch data from server');
                }
                
                const status = await statusRes.json();
                const trapsData = await trapsRes.json();
                
                updateStatusCards(status);
                updateTrapTable(trapsData.traps);
                updateLastUpdateTime(status.timestamp);
                
            } catch (error) {
                console.error('Error refreshing data:', error);
                showError(error.message);
            }
        }
        
        // Update status summary cards
        function updateStatusCards(status) {
            const html = `
                <div class="card-summary card-ok">
                    <div class="card-count">${status.ok_count}</div>
                    <div class="card-label">${getStatusLabel('ok_count')}</div>
                </div>
                <div class="card-summary card-alert">
                    <div class="card-count">${status.alert_count}</div>
                    <div class="card-label">${getStatusLabel('alert_count')}</div>
                </div>
                <div class="card-summary card-missing">
                    <div class="card-count">${status.missing_count}</div>
                    <div class="card-label">${getStatusLabel('missing_count')}</div>
                </div>
                <div class="card-summary card-unknown">
                    <div class="card-count">${status.unknown_count}</div>
                    <div class="card-label">${getStatusLabel('unknown_count')}</div>
                </div>
            `;
            document.getElementById('statusCards').innerHTML = html;
        }
        
        // Update trap data table
        function updateTrapTable(traps) {
            const tbody = document.getElementById('trapTableBody');
            
            if (Object.keys(traps).length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" class="text-center" style="padding: 40px;">No traps registered yet</td></tr>';
                return;
            }
            
            let html = '';
            for (const [trapId, trap] of Object.entries(traps)) {
                const statusClass = getStatusClass(trap.state);
                const activeClass = trap.active ? 'yes' : 'no';
                const activeText = trap.active ? 'Yes' : 'No';
                
                html += `
                    <tr>
                        <td class="trap-name">${trap.name}</td>
                        <td><span class="status-badge ${statusClass}">${trap.state}</span></td>
                        <td><span class="active-badge ${activeClass}">${activeText}</span></td>
                        <td>${formatTimeAgo(trap.lastHeard)}<br><small style="color: #999;">${formatTime(trap.lastHeard)}</small></td>
                        <td>${trap.battery !== null ? trap.battery.toFixed(1) + '%' : 'N/A'}</td>
                        <td>${trap.voltage !== null ? trap.voltage.toFixed(2) : 'N/A'}</td>
                        <td>${trap.rssi !== null ? trap.rssi.toFixed(0) : 'N/A'}</td>
                        <td>${trap.snr !== null ? trap.snr.toFixed(1) : 'N/A'}</td>
                        <td>${trap.lastEventType || 'N/A'}</td>
                        <td class="trap-actions">
                            <button class="btn btn-sm btn-outline-success" onclick="resetTrap('${trapId}')" title="Reset to OK">↻ Reset</button>
                            <button class="btn btn-sm btn-outline-warning" onclick="toggleTrap('${trapId}')" title="Toggle Active">${trap.active ? '✓ Disable' : '✗ Enable'}</button>
                        </td>
                    </tr>
                `;
            }
            
            tbody.innerHTML = html;
        }
        
        // Update last refresh time
        function updateLastUpdateTime(timestamp) {
            const now = new Date(timestamp * 1000);
            document.getElementById('lastUpdate').textContent = now.toLocaleTimeString();
        }
        
        // Reset trap status
        async function resetTrap(trapId) {
            if (!confirm(`Reset trap "${trapId}" to OK status?`)) return;
            
            try {
                const res = await fetch(`/api/trap/${trapId}/reset`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to reset trap');
                }
                
                // Refresh data immediately
                await refreshData();
                
            } catch (error) {
                console.error('Error resetting trap:', error);
                showError(`Failed to reset trap: ${error.message}`);
            }
        }
        
        // Toggle trap active status
        async function toggleTrap(trapId) {
            try {
                const res = await fetch(`/api/trap/${trapId}/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                
                if (!res.ok) {
                    const err = await res.json();
                    throw new Error(err.detail || 'Failed to toggle trap');
                }
                
                // Refresh data immediately
                await refreshData();
                
            } catch (error) {
                console.error('Error toggling trap:', error);
                showError(`Failed to toggle trap: ${error.message}`);
            }
        }
        
        // Toggle admin panel visibility
        function toggleAdminPanel() {
            document.getElementById('adminPanel').classList.toggle('show');
        }
        
        // Start auto-refresh
        function startAutoRefresh() {
            refreshTimer = setInterval(refreshData, REFRESH_INTERVAL);
        }
        
        // Stop auto-refresh
        function stopAutoRefresh() {
            if (refreshTimer) {
                clearInterval(refreshTimer);
                refreshTimer = null;
            }
        }
        
        // Initialize on page load
        document.addEventListener('DOMContentLoaded', function() {
            refreshData();
            startAutoRefresh();
        });
        
        // Stop refresh when page is hidden (tab not active)
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                stopAutoRefresh();
            } else {
                refreshData();
                startAutoRefresh();
            }
        });
    </script>
</body>
</html>"""


def set_app_state(state: Dict[str, Any]) -> None:
    """Set the application state reference (thread-safe)."""
    with _app_state["lock"]:
        _app_state["state"] = state


def run_server() -> None:
    """
    Run the FastAPI server in a blocking manner.
    
    This should be called in a separate thread by the CLI.
    """
    import uvicorn
    
    app = create_app()
    
    print("[WEB] Starting FastAPI web server on http://localhost:8000")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="warning",
        )
    except Exception as e:
        print(f"[ERROR] Failed to start web server: {e}")


def run_server_async(state: Dict[str, Any]) -> threading.Thread:
    """
    Start the FastAPI server in a background thread.
    
    Args:
        state: Trap state dictionary to serve
        
    Returns:
        Thread object for the web server
    """
    set_app_state(state)
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.name = "TrapperJoe-WebServer"
    thread.start()
    
    return thread
