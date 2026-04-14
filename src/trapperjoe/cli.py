"""
Command-line interface for TrapperJoe.

Provides commands for starting the listener, checking status, etc.
"""

import argparse
import signal
import sys
import time
import threading
from pathlib import Path

from trapperjoe.listener import MeshtasticListener
from trapperjoe.config import load_config, validate_config, get_meshtastic_host, get_meshtastic_port
from trapperjoe.state_manager import load_state, get_all_traps, count_traps_by_status
from trapperjoe.utils import format_ts
from trapperjoe import web_server


_shutdown = False
_web_server_thread = None


def handle_sigterm(signum, frame):
    """Handle shutdown signals."""
    global _shutdown
    print("\n🛑 Shutdown signal received.")
    _shutdown = True


def cmd_start(args):
    """Start the listener."""
    global _shutdown
    global _web_server_thread
    
    _shutdown = False
    signal.signal(signal.SIGINT, handle_sigterm)
    signal.signal(signal.SIGTERM, handle_sigterm)
    
    # Load config
    cfg = load_config()
    validate_config(cfg)
    
    HOST = get_meshtastic_host(cfg)
    PORT = get_meshtastic_port(cfg)
    
    print("\n🌐 TrapperJoe Integrated Listener (TCP + Notifier)")
    print(f"   Host: {HOST}:{PORT}")
    print(f"   State: {Path.cwd() / 'trap_state.json'}")
    print(f"   Config: {Path.cwd() / 'config' / 'trapperjoe_config.json'}")
    print(f"   NodeDB: {Path.cwd() / 'meshtastic' / 'nodedb.json'}\n")
    
    listener = MeshtasticListener(HOST)
    
    # Load initial state
    listener.state = listener.load_state_from_file()
    trap_count = len([k for k in listener.state.keys() if not k.startswith('_')])
    print(f"[INIT] Loaded state with {trap_count} trap(s)")
    
    # Start scheduler
    listener.start_scheduler()
    
    # Start web server
    print("[WEB] Starting web server on http://localhost:8000")
    _web_server_thread = web_server.run_server_async(listener.state)
    time.sleep(0.5)  # Give web server time to start
    
    # Initial connection
    if not listener.connect():
        print("\n💡 Connection tips:")
        print("   1. Is device on network and WiFi enabled?")
        print("   2. Is Network Server enabled in Settings → Network → WiFi?")
        print("   3. Is IP address correct?\n")
        
        while not _shutdown:
            if listener.try_reconnect():
                break
    
    print("\n🚀 Listener running. Waiting for messages...\n")
    
    try:
        while not _shutdown:
            try:
                if not listener.connected:
                    listener.try_reconnect()
                else:
                    listener.health_check()
                
                listener.save_state_to_file()
                time.sleep(0.5)
            
            except KeyboardInterrupt:
                break
            except Exception as e:
                print("❌ Unexpected error in main loop:")
                print(f"   {e}")
                listener.safe_disconnect()
                time.sleep(1)
    
    finally:
        print("\n👋 Shutting down...")
        
        # Stop scheduler
        listener.stop_scheduler()
        
        # Final state save
        listener.save_state_to_file()
        
        # Final nodedb export
        if listener.interface:
            listener.export_nodedb()
        
        # Cleanup
        listener.safe_disconnect()
        print("✋ Goodbye.\n")


def cmd_status(args):
    """Show current trap status."""
    state = load_state()
    
    if not state:
        print("No traps registered.")
        return
    
    traps = get_all_traps(state)
    counts = count_traps_by_status(state)
    
    print("\n📊 Trap Status Summary")
    print("=" * 60)
    print(f"  ✅ Operational:     {counts['OK']}")
    print(f"  ⚠️  Alert Active:    {counts['ALERT']}")
    print(f"  📡 No Connection:   {counts['MISSING']}")
    print(f"  ❓ Unknown:         {counts['UNKNOWN']}")
    print("=" * 60)
    
    if traps:
        print("\nDetailed Status:")
        print("-" * 120)
        print(f"{'Trap ID':<12} {'Name':<20} {'Status':<10} {'Battery':<10} {'RSSI':<10} {'Last Heard':<20}")
        print("-" * 120)
        
        for trap_id, trap_data in sorted(traps, key=lambda x: x[1].get("name", x[0])):
            name = trap_data.get("name", "N/A")[:18]
            status = trap_data.get("state", "UNKNOWN")
            battery = trap_data.get("battery")
            battery_str = f"{battery}%" if battery else "N/A"
            rssi = trap_data.get("rssi")
            rssi_str = f"{rssi} dBm" if rssi else "N/A"
            last_heard = format_ts(trap_data.get("lastHeard"))
            
            print(f"{trap_id:<12} {name:<20} {status:<10} {battery_str:<10} {rssi_str:<10} {last_heard:<20}")
        
        print("-" * 120)


def cmd_config(args):
    """Show configuration."""
    cfg = load_config()
    
    if not cfg:
        print("No configuration loaded.")
        return
    
    print("\n⚙️  Configuration")
    print("=" * 60)
    
    mesh_cfg = cfg.get("meshtastic", {})
    print(f"\nMeshtastic:")
    print(f"  Host: {mesh_cfg.get('host', 'N/A')}")
    print(f"  Port: {mesh_cfg.get('port', 'N/A')}")
    
    email_cfg = cfg.get("email_config", {})
    print(f"\nEmail:")
    print(f"  User: {email_cfg.get('user', 'N/A')}")
    print(f"  Recipients: {len(email_cfg.get('recipients', []))} configured")
    
    sched_cfg = cfg.get("schedule_config", {})
    print(f"\nSchedule:")
    print(f"  Timeout: {sched_cfg.get('alive_timeout_hours', 'N/A')} hours")
    print(f"  Daily Reports: {', '.join(sched_cfg.get('schedule_times', []))}")
    
    print("=" * 60)


def cmd_version(args):
    """Show version."""
    from trapperjoe import __version__
    print(f"TrapperJoe {__version__}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="trapperjoe",
        description="TrapperJoe - Wildlife Trap Monitoring System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trapperjoe start              # Start the listener
  trapperjoe status             # Show trap status
  trapperjoe config             # Show configuration
  trapperjoe version            # Show version
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # start command
    subparsers.add_parser("start", help="Start the listener")
    
    # status command
    subparsers.add_parser("status", help="Show trap status")
    
    # config command
    subparsers.add_parser("config", help="Show configuration")
    
    # version command
    subparsers.add_parser("version", help="Show version")
    
    # If no command, default to start
    args = parser.parse_args()
    
    if not args.command:
        args.command = "start"
    
    try:
        if args.command == "start":
            cmd_start(args)
        elif args.command == "status":
            cmd_status(args)
        elif args.command == "config":
            cmd_config(args)
        elif args.command == "version":
            cmd_version(args)
        else:
            parser.print_help()
            return 1
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        return 130
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
