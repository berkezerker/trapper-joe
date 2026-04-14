# TrapperJoe – Remote Trap Monitoring System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue?logo=python)](https://www.python.org/)

**TrapperJoe** is an automated remote monitoring system for wildlife traps using **Meshtastic** mesh networking. It detects trap activations, monitors device health (battery, signal strength), and sends email alerts when traps trigger or devices lose connectivity.

## 🎯 Features

- **🌐 Mesh Networking** — Uses Meshtastic for reliable long-range wireless communication
- **📊 Real-time Monitoring** — Tracks trap status (OK, ALERT, MISSING) with live telemetry
- **📧 Smart Alerts** — 
  - 🚨 **Alert emails** when trap is triggered
  - ⚠️ **Missing device emails** when timeout exceeded
  - ✅ **Reset confirmations** for manual trap resets
  - 📊 **Daily status reports** with all trap states
- **🤖 Admin Commands** — Remote trap management via mesh messages
- **🌐 Network Connection** — TCP/WiFi to Meshtastic device
- **🔄 Auto-Reconnect** — Exponential backoff retry logic for robust recovery
- **💾 Data Persistence** — Append-only JSONL logs for all events
- **📈 Signal Monitoring** — Tracks RSSI/SNR for connection quality assessment
- **🔋 Battery Alerts** — Monitors device power levels and reports critically low battery

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Meshtastic device (e.g., T-Deck, Heltec V3, etc.) with mesh network
- Gmail account with app-specific password for email notifications

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/trapper-joe.git
cd trapper-joe

# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp config/trapperjoe_config.example.json config/trapperjoe_config.json
# Edit config with your Meshtastic IP, Gmail credentials, etc.
```

### Running the System

**Single unified process:**

```bash
python meshtastic/listener_tcp.py
```

This single process handles:
- ✅ TCP connection to Meshtastic device
- ✅ Real-time message reception and classification
- ✅ Immediate alert email generation
- ✅ Background scheduler for timeouts and daily reports
- ✅ Automatic reconnection with exponential backoff

For production deployment, use a service manager like systemd (Linux), Task Scheduler (Windows), or Docker to run this process continuously.

## 📋 Project Structure

```
trapper-joe/
├── README.md                    # This file
├── requirements.txt             # Python dependencies
├── trap_state.json              # Runtime trap status (auto-generated)
├── config/
│   └── trapperjoe_config.json   # Configuration (edit this!)
├── meshtastic/
│   ├── listener_tcp.py          # Main process (TCP + alerts + scheduler)
│   ├── nodedb.json              # Mesh network node database (auto-generated)
│   └── ...
├── docs/                        # Documentation
│   ├── SETUP.md                 # Detailed setup guide
│   ├── ARCHITECTURE.md          # System design
│   ├── CONFIGURATION.md         # Config reference
│   ├── API.md                   # Admin commands
│   └── TROUBLESHOOTING.md       # Common issues
└── LICENSE
```

## 🔧 System Architecture

**Single unified process for real-time event-driven monitoring:**

```
Remote Trap Nodes (Meshtastic)
           │
           ├─ DETECTION_SENSOR_APP  ──┐
           ├─ TEXT_MESSAGE_APP        │  (Trap events, admin commands)
           └─ TELEMETRY_APP           │  (Battery, RSSI, etc.)
                                      ▼
        ┌─────────────────────────────────────────┐
        │  MeshtasticListener (Main Process)      │
        │  (meshtastic/listener_tcp.py)           │
        │                                         │
        │  Main Thread:                           │
        │  • TCP connection to Meshtastic         │
        │  • Event-driven message routing         │
        │  • Real-time alert generation           │
        │  • State management                     │
        │                                         │
        │  Background Scheduler Thread:           │
        │  • Timeout detection                    │
        │  • Scheduled status reports             │
        │  • NodeDB snapshots                     │
        └─────────────────┬───────────────────────┘
                          │
              ┌───────────┴───────────┬──────────┐
              ▼                       ▼          ▼
        trap_state.json         Email Alerts  nodedb.json
        (trap statuses)          (immediate)   (mesh snapshot)
```

**Data Flow:**
1. Remote trap sensor triggers → Meshtastic mesh broadcasts
2. Listener receives via TCP (real-time pub/sub)
3. Message routed by type and classified
4. Trap state updated immediately
5. Alert email sent instantly on state change
6. Background scheduler checks for timeouts & schedules reports

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed component breakdown.

## 📖 Documentation

- **[SETUP.md](docs/SETUP.md)** — Step-by-step installation and configuration
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design and data flow
- **[CONFIGURATION.md](docs/CONFIGURATION.md)** — All config settings explained
- **[API.md](docs/API.md)** — Admin commands and message formats
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** — Common issues and solutions

## 🔐 Security Notes

- **Config file** contains Gmail credentials — keep it safe and don't commit to public repos
- Use `.gitignore` to exclude sensitive files (see included `.gitignore`)
- Email credentials should be app-specific passwords, not your main Gmail password
- Admin commands require sender node ID to be registered in state

## 📊 Data Formats

### Messages Log (JSONL)
```json
{
  "ts": 1712960123.456,
  "id": "^all",
  "msg": "trap detected",
  "rssi": -105,
  "snr": 8.5,
  "short": "Trap1",
  "battery": 85,
  "voltage": 4.15
}
```

### Telemetry Log (JSONL)
```json
{
  "ts": 1712960130.123,
  "id": "^all",
  "type": "telemetry",
  "battery": 85,
  "voltage": 4.15,
  "channelUtilization": 12.5,
  "temperature": 22.3
}
```

### Trap State (JSON)
```json
{
  "^all": {
    "name": "Trap1",
    "state": "OK",
    "active": true,
    "lastHeard": 1712960130,
    "battery": 85,
    "voltage": 4.15,
    "rssi": -105,
    "snr": 8.5,
    "lastEventType": "DETECTION",
    "last_alert_ts": 1712960100
  }
}
```

## 🛠️ Configuration Example

```json
{
  "meshtastic": {
    "host": "192.168.178.95",
    "port": 4403
  },
  "email_config": {
    "user": "your-gmail@gmail.com",
    "app_password": "your-app-specific-password",
    "recipients": ["alert@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 1,
    "schedule_times": ["06:45", "19:00"]
  }
}
```

Full configuration reference: [docs/CONFIGURATION.md](docs/CONFIGURATION.md)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.

## 🆘 Support

- Check [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for common issues
- Review logs in `meshtastic/messages_log.jsonl` and `trap_state.json`
- Enable `DEBUG_MODE` in listener files for more detail output

## 🎓 Learn More

- [Meshtastic Documentation](https://meshtastic.org/)
- [Python Meshtastic SDK](https://meshtastic.org/docs/developers/protobufs/api/)
- [JSONL Format](https://jsonlines.org/)

---

**Made with ❤️ for wildlife conservation**
