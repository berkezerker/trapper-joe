"""
Meshtastic listener for TrapperJoe.

Main listener class that handles connection, message parsing, and state management.
"""

import time
import traceback
import threading
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from pubsub import pub
from meshtastic.tcp_interface import TCPInterface

from trapperjoe.config import load_config, get_meshtastic_host, get_meshtastic_port
from trapperjoe.state_manager import (
    load_state, save_state, initialize_trap, trap_exists, update_trap_state
)
from trapperjoe.email_handler import (
    send_email_html, html_status_report, html_alert_mail, html_reset_mail
)
from trapperjoe.utils import format_ts, convert_to_serializable


# Configuration constants
RECONNECT_DELAY = 1.0
MAX_RECONNECT_DELAY = 60.0
NODEDB_EXPORT_INTERVAL = 300  # 5 minutes


class MeshtasticListener:
    """Listens for Meshtastic messages and manages trap state."""
    
    def __init__(self, hostname: str, port: int = 4403):
        """
        Initialize listener.
        
        Args:
            hostname: IP address of Meshtastic device
            port: TCP port (deprecated - TCPInterface doesn't support this)
        """
        self.hostname = hostname
        self.port = port  # Stored for reference but not used by TCPInterface
        self.interface: Optional[TCPInterface] = None
        self.connected = False
        self.backoff = RECONNECT_DELAY
        self.subscribed = False
        self.last_nodedb_export = 0
        self.known_nodes = set()
        self.node_cache = {}
        
        # State management
        self.state: Dict[str, Any] = {}
        self.state_changed = False
        
        # Scheduled tasks
        self.scheduler_thread = None
        self.scheduler_stop = threading.Event()
        
        # Paths
        self.nodedb_file = Path.cwd() / "meshtastic" / "nodedb.json"
    
    # ========================================================
    # Connection Management
    # ========================================================
    
    def connect(self) -> bool:
        """
        Establish TCP connection to Meshtastic device.
        
        Returns:
            True if connected successfully
        """
        try:
            # Note: TCPInterface only accepts hostname, not port
            self.interface = TCPInterface(hostname=self.hostname)
            self.connected = True
            self.backoff = RECONNECT_DELAY
            print("Connected to Meshtastic device.")
            
            if not self.subscribed:
                pub.subscribe(self.on_receive, "meshtastic.receive")
                self.subscribed = True
                print("📡 Subscribed to meshtastic.receive")
            
            time.sleep(2)
            self.export_nodedb_if_needed(force=True)
            
            self.known_nodes = set(self.interface.nodes.keys())
            for node_id, node_data in self.interface.nodes.items():
                self.node_cache[node_id] = dict(node_data)
            
            return True
        
        except ConnectionRefusedError:
            print(f"❌ Connection refused: {self.hostname}:{self.port}")
            print("   → Network server enabled on device?")
            self.connected = False
            self.interface = None
            return False
        
        except TimeoutError:
            print(f"❌ Timeout connecting to {self.hostname}:{self.port}")
            print("   → Is device on network?")
            self.connected = False
            self.interface = None
            return False
        
        except Exception as e:
            print(f"❌ Connection error: {e}")
            self.connected = False
            self.interface = None
            return False
    
    def try_reconnect(self) -> bool:
        """
        Reconnect with exponential backoff.
        
        Returns:
            True if reconnected successfully
        """
        self.safe_disconnect()
        
        print(f"⏳ Waiting {self.backoff:.1f}s before reconnect...")
        time.sleep(self.backoff)
        self.backoff = min(self.backoff * 2, MAX_RECONNECT_DELAY)
        
        if self.connect():
            print("🔄 Reconnected successfully.")
            return True
        else:
            print("🔄 Reconnect failed.")
            return False
    
    def safe_disconnect(self) -> None:
        """Gracefully close connection."""
        if self.subscribed:
            try:
                pub.unsubscribe(self.on_receive, "meshtastic.receive")
                print("🔕 Unsubscribed from meshtastic.receive")
            except Exception:
                pass
            self.subscribed = False
        
        if self.interface:
            try:
                print("🔒 Closing TCPInterface...")
                self.interface.close()
            except Exception as e:
                print(f"⚠️ Error closing interface: {e}")
            finally:
                self.interface = None
        
        self.connected = False
    
    # ========================================================
    # NodeDB Export
    # ========================================================
    
    def export_nodedb_if_needed(self, force: bool = False) -> bool:
        """
        Export NodeDB periodically or on demand.
        
        Args:
            force: Force export immediately
            
        Returns:
            True if exported
        """
        current_time = time.time()
        
        if force or (current_time - self.last_nodedb_export) >= NODEDB_EXPORT_INTERVAL:
            if self.export_nodedb():
                self.last_nodedb_export = current_time
                return True
        
        if NODEDB_EXPORT_INTERVAL and self.interface:
            try:
                current_nodes = set(self.interface.nodes.keys())
                if current_nodes != self.known_nodes:
                    new_nodes = current_nodes - self.known_nodes
                    if new_nodes:
                        print(f"🆕 New node(s): {new_nodes}")
                        for node_id in new_nodes:
                            if node_id in self.interface.nodes:
                                self.node_cache[node_id] = dict(self.interface.nodes[node_id])
                    self.known_nodes = current_nodes
                    if self.export_nodedb():
                        self.last_nodedb_export = current_time
                        return True
            except Exception as e:
                print(f"⚠️ Error tracking nodes: {e}")
        
        return False
    
    def export_nodedb(self) -> bool:
        """
        Export NodeDB as JSON snapshot.
        
        Returns:
            True if successful
        """
        try:
            if not self.interface or not hasattr(self.interface, 'nodes'):
                return False
            
            nodedb = {
                "exportTime": time.time(),
                "exportTimeFormatted": __import__("datetime").datetime.now().isoformat(),
                "nodeCount": 0,
                "myInfo": {},
                "nodes": {}
            }
            
            if hasattr(self.interface, 'myInfo') and self.interface.myInfo:
                nodedb["myInfo"] = convert_to_serializable(self.interface.myInfo)
            
            all_node_ids = set(self.interface.nodes.keys()) | set(self.node_cache.keys())
            
            for node_id in all_node_ids:
                try:
                    node_data = dict(self.interface.nodes.get(node_id, {}))
                    
                    if node_id in self.node_cache:
                        cached = self.node_cache[node_id]
                        for key in ["deviceMetrics", "environmentMetrics", "powerMetrics", "lastHeard", "rssi", "snr"]:
                            if key in cached:
                                node_data[key] = cached[key]
                    
                    nodedb["nodes"][node_id] = convert_to_serializable(node_data)
                
                except Exception as e:
                    print(f"⚠️ Error converting node {node_id}: {e}")
            
            nodedb["nodeCount"] = len(nodedb["nodes"])
            
            # Ensure directory exists
            self.nodedb_file.parent.mkdir(parents=True, exist_ok=True)
            
            tmp_file = self.nodedb_file.with_suffix(".tmp")
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(nodedb, f, indent=2, ensure_ascii=False, default=str)
            
            tmp_file.replace(self.nodedb_file)
            
            timestamp = __import__("datetime").datetime.fromtimestamp(
                nodedb["exportTime"]
            ).strftime("%H:%M:%S")
            print(f"[{timestamp}] 💾 NodeDB exported: {nodedb['nodeCount']} nodes")
            return True
        
        except Exception as e:
            print(f"❌ NodeDB export error: {e}")
            return False
    
    def update_node_cache(self, node_id: str, telemetry_data: Dict = None, message_data: Dict = None) -> None:
        """
        Update node cache with fresh data.
        
        Args:
            node_id: Node ID
            telemetry_data: Optional telemetry data
            message_data: Optional message metadata (rssi, snr)
        """
        if node_id not in self.node_cache:
            try:
                if self.interface and node_id in self.interface.nodes:
                    self.node_cache[node_id] = dict(self.interface.nodes[node_id])
                else:
                    self.node_cache[node_id] = {"num": 0, "user": {"id": node_id}}
            except Exception:
                self.node_cache[node_id] = {"num": 0, "user": {"id": node_id}}
        
        self.node_cache[node_id]["lastHeard"] = int(time.time())
        
        if telemetry_data:
            for key in ["deviceMetrics", "environmentMetrics", "powerMetrics"]:
                if key in telemetry_data:
                    self.node_cache[node_id][key] = telemetry_data[key]
        
        if message_data:
            for key in ["rssi", "snr"]:
                if key in message_data:
                    self.node_cache[node_id][key] = message_data[key]
    
    # ========================================================
    # Message Processing
    # ========================================================
    
    def on_receive(self, packet: Dict, interface) -> None:
        """
        Callback for received packets.
        
        Args:
            packet: Meshtastic packet dict
            interface: TCPInterface instance
        """
        try:
            if not isinstance(packet, dict):
                return
            
            decoded = packet.get("decoded", {})
            portnum = decoded.get("portnum")
            node_id = packet.get("fromId")
            
            if not node_id or not portnum:
                return
            
            cfg = self.load_config()
            email_cfg = cfg.get("email_config", {})
            
            # TEXT_MESSAGE_APP
            if portnum in ("TEXT_MESSAGE_APP", 1):
                payload = decoded.get("payload")
                msg = payload.decode("utf-8") if isinstance(payload, (bytes, bytearray)) else str(payload)
                
                rssi = packet.get("rxRssi") or packet.get("rssi")
                snr = packet.get("rxSnr") or packet.get("snr")
                
                msg_dict = {
                    "id": node_id,
                    "ts": time.time(),
                    "msg": msg,
                    "rssi": rssi,
                    "snr": snr
                }
                
                state_changed, _ = self.process_trap_message(msg_dict, cfg, email_cfg)
                self.state_changed |= state_changed
            
            # DETECTION_SENSOR_APP
            elif portnum in ("DETECTION_SENSOR_APP", 4):
                rssi = packet.get("rxRssi") or packet.get("rssi")
                snr = packet.get("rxSnr") or packet.get("snr")
                
                msg_dict = {
                    "id": node_id,
                    "ts": time.time(),
                    "msg": "trap detected",
                    "rssi": rssi,
                    "snr": snr
                }
                
                state_changed, _ = self.process_trap_message(msg_dict, cfg, email_cfg)
                self.state_changed |= state_changed
            
            # TELEMETRY_APP
            elif portnum == "TELEMETRY_APP":
                telemetry = decoded.get("telemetry", {})
                if telemetry:
                    self.update_node_cache(node_id, telemetry_data=telemetry)
                    
                    telem_dict = {
                        "id": node_id,
                        "ts": time.time(),
                        "type": "telemetry",
                        "battery": telemetry.get("deviceMetrics", {}).get("batteryLevel"),
                        "voltage": telemetry.get("deviceMetrics", {}).get("voltage"),
                        "rssi": packet.get("rxRssi") or packet.get("rssi"),
                        "snr": packet.get("rxSnr") or packet.get("snr")
                    }
                    
                    state_changed = self._process_telemetry(telem_dict)
                    self.state_changed |= state_changed
            
            # Export nodedb on message
            self.export_nodedb_if_needed()
        
        except Exception as e:
            print(f"⚠️ Error in on_receive: {e}")
            traceback.print_exc()
    
    def process_trap_message(
        self, msg: Dict[str, Any], cfg: Dict[str, Any], email_cfg: Dict[str, Any]
    ) -> Tuple[bool, bool]:
        """
        Process trap message (detection, reset, or admin command).
        
        Args:
            msg: Message dict with id, ts, msg
            cfg: Configuration
            email_cfg: Email configuration
            
        Returns:
            (state_changed, cfg_changed) tuple
        """
        nid = msg.get("id")
        msg_ts = msg.get("ts", 0)
        text = (msg.get("msg") or "").strip().lower()
        
        # Admin commands
        state_changed, cfg_changed, is_admin = self.handle_admin_command(msg, cfg, email_cfg)
        if is_admin:
            return state_changed, cfg_changed
        
        # Only registered traps
        if not trap_exists(self.state, nid):
            print(f"[TRAP] [{nid}] Unregistered, ignoring message.")
            return False, False
        
        trap = self.state.get(nid)
        
        # Duplicate check
        last_ts = trap.get("last_processed_ts", 0)
        if msg_ts <= last_ts:
            print(f"[TRAP] [{nid}] Already processed ts={msg_ts}.")
            return False, False
        
        trap["last_processed_ts"] = msg_ts
        
        # RESET event
        if text == "trap reset":
            prev_reset = trap.get("last_reset_ts", 0)
            if msg_ts > prev_reset:
                trap["last_reset_ts"] = msg_ts
                trap["state"] = "OK"
                trap["lastEventType"] = "RESET"
                html = html_reset_mail(nid, trap, self.state, cfg)
                send_email_html(f"Trap Reset: {trap.get('name', nid)}", html, email_cfg)
                print(f"[TRAP] [{nid}] Reset processed.")
                return True, False
        
        # DETECTION event
        if "detected" in text:
            prev_alert = trap.get("last_alert_ts", 0)
            if msg_ts > prev_alert:
                trap["last_alert_ts"] = msg_ts
                trap["state"] = "ALERT"
                trap["lastEventType"] = "DETECTION"
                html = html_alert_mail(nid, trap, self.state, cfg)
                send_email_html(f"ALERT: {trap.get('name', nid)}", html, email_cfg)
                print(f"[TRAP] [{nid}] Alert processed.")
                return True, False
        
        # Other message
        if trap.get("state") != "ALERT":
            trap["state"] = "OK"
        
        return True, False
    
    def handle_admin_command(
        self, msg: Dict[str, Any], cfg: Dict[str, Any], email_cfg: Dict[str, Any]
    ) -> Tuple[bool, bool, bool]:
        """
        Route admin commands (trap -register, -reset, etc.).
        
        Args:
            msg: Message dict
            cfg: Configuration
            email_cfg: Email configuration
            
        Returns:
            (state_changed, cfg_changed, is_admin) tuple
        """
        text = (msg.get("msg") or "").strip()
        sender = msg.get("id")
        msg_ts = msg.get("ts", 0)
        
        if not text.startswith("trap -"):
            return False, False, False
        
        parts = text.split()
        if len(parts) < 2:
            return False, False, True
        
        cmd = parts[1].lower()
        trap = self.state.get(sender)
        
        # trap -register
        if cmd == "-register":
            name = parts[2] if len(parts) > 2 else sender
            if trap:
                trap["name"] = name
                print(f"[TRAP] [{sender}] Updated name: {name}")
            else:
                self.state[sender] = initialize_trap(sender, name)
                print(f"[TRAP] New trap registered: {name}")
            
            html = html_status_report(self.state, cfg)
            send_email_html(f"Trap Registered: {name}", html, email_cfg)
            return True, False, True
        
        if not trap:
            print(f"[TRAP] [{sender}] Trap not registered, ignoring command.")
            return False, False, True
        
        # trap -status
        if cmd == "-status":
            print(f"----- Status {trap.get('name', sender)} -----")
            print(f"State: {trap.get('state', 'UNKNOWN')}")
            print(f"Last heard: {format_ts(trap.get('lastHeard'))}")
            print(f"Battery: {trap.get('battery')}")
            print(f"Voltage: {trap.get('voltage')}")
            print(f"Last Event: {trap.get('lastEventType', 'None')}")
            return False, False, True
        
        # trap -statusmail
        if cmd == "-statusmail":
            last_mail_ts = trap.get("last_statusmail_ts", 0)
            if msg_ts <= last_mail_ts:
                print(f"[TRAP] [{sender}] Statusmail already sent for ts={msg_ts}.")
                return False, False, True
            
            trap["last_statusmail_ts"] = msg_ts
            html = html_status_report(self.state, cfg)
            send_email_html("Status Report (Manual Request)", html, email_cfg)
            print(f"[TRAP] [{sender}] Statusmail sent.")
            return True, False, True
        
        # trap -reset
        if cmd == "-reset":
            trap["state"] = "OK"
            trap["lastEventType"] = "RESET"
            html = html_reset_mail(sender, trap, self.state, cfg)
            send_email_html(f"Trap Reset: {trap.get('name', sender)}", html, email_cfg)
            print(f"[TRAP] [{sender}] State manually reset to OK.")
            return True, False, True
        
        # trap -remove
        if cmd == "-remove":
            if sender in self.state:
                removed_name = self.state[sender].get("name", sender)
                del self.state[sender]
                print(f"[TRAP] [{sender}] Removed from state.")
                
                html = html_status_report(self.state, cfg)
                send_email_html(f"Trap Removed: {removed_name}", html, email_cfg)
                return True, False, True
        
        print(f"[TRAP] [{sender}] Unknown command: {cmd}")
        return False, False, True
    
    def _process_telemetry(self, entry: Dict[str, Any]) -> bool:
        """
        Process telemetry (battery, RSSI, SNR, etc.).
        
        Args:
            entry: Telemetry data dict
            
        Returns:
            True if state changed
        """
        nid = entry.get("id")
        entry_ts = entry.get("ts", 0)
        
        if not trap_exists(self.state, nid):
            return False
        
        trap = self.state.get(nid)
        
        # Duplicate check
        last_telem_ts = trap.get("last_telemetry_ts", 0)
        if entry_ts <= last_telem_ts:
            return False
        
        trap["last_telemetry_ts"] = entry_ts
        trap["lastHeard"] = entry_ts
        trap["battery"] = entry.get("battery")
        trap["voltage"] = entry.get("voltage")
        trap["rssi"] = entry.get("rssi")
        trap["snr"] = entry.get("snr")
        
        print(f"[TELEM] [{nid}] Battery={trap['battery']}%, Voltage={trap['voltage']}V")
        return True
    
    # ========================================================
    # Config & State Management
    # ========================================================
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        return load_config()
    
    def load_state_from_file(self) -> Dict[str, Any]:
        """Load trap state from file."""
        return load_state()
    
    def save_state_to_file(self) -> None:
        """Save trap state to file if changed."""
        if self.state_changed:
            save_state(self.state)
            self.state_changed = False
    
    # ========================================================
    # Health Check
    # ========================================================
    
    def health_check(self) -> None:
        """Periodic health check and scheduled tasks."""
        try:
            if self.connected and self.interface:
                _ = self.interface.nodes
                self.export_nodedb_if_needed()
        
        except Exception:
            print("❌ Health check failed → Connection lost.")
            self.safe_disconnect()
            self.connected = False
    
    # ========================================================
    # Scheduler (Background Tasks)
    # ========================================================
    
    def start_scheduler(self) -> None:
        """Start background scheduler thread."""
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        print("📅 Scheduler thread started.")
    
    def _scheduler_loop(self) -> None:
        """Background thread for timeouts and scheduled reports."""
        import datetime as dt_module
        
        while not self.scheduler_stop.is_set():
            try:
                cfg = self.load_config()
                now = time.time()
                
                # Check for timeouts
                timeout_hours = cfg.get("schedule_config", {}).get("alive_timeout_hours", 24)
                timeout_seconds = timeout_hours * 3600
                
                for trap_id, trap in self.state.items():
                    if trap_id.startswith("_"):
                        continue
                    
                    last_heard = trap.get("lastHeard", 0)
                    if last_heard == 0:
                        continue
                    
                    time_since_heard = now - last_heard
                    
                    if time_since_heard > timeout_seconds:
                        old_state = trap.get("state")
                        trap["state"] = "MISSING"
                        
                        if old_state != "MISSING":
                            print(f"[TIMEOUT] [{trap_id}] Status: MISSING")
                            html = html_status_report(self.state, cfg)
                            trap_name = trap.get("name", trap_id)
                            email_cfg = cfg.get("email_config", {})
                            send_email_html(f"⚠️ Timeout: {trap_name}", html, email_cfg)
                            self.state_changed = True
                
                # Check scheduled times for daily status report
                today = dt_module.datetime.now().strftime("%Y-%m-%d")
                now_str = dt_module.datetime.now().strftime("%H:%M")
                sched_times = cfg.get("schedule_config", {}).get("schedule_times", [])
                
                if now_str in sched_times and self.state.get("_last_status_day") != today:
                    html = html_status_report(self.state, cfg)
                    email_cfg = cfg.get("email_config", {})
                    send_email_html("📊 Daily Status Report", html, email_cfg)
                    self.state["_last_status_day"] = today
                    self.state_changed = True
                    print(f"[SCHEDULE] Daily status report sent.")
                
                # Save state if changed
                self.save_state_to_file()
                
                time.sleep(30)  # Check every 30 seconds
            
            except Exception as e:
                print(f"⚠️ Error in scheduler loop: {e}")
                time.sleep(30)
    
    def stop_scheduler(self) -> None:
        """Stop scheduler thread gracefully."""
        self.scheduler_stop.set()
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        print("📅 Scheduler stopped.")
