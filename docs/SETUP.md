# TrapperJoe Setup Guide

A complete step-by-step guide to install and configure TrapperJoe for monitoring remote wildlife traps.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Meshtastic Device Setup](#meshtastic-device-setup)
4. [Gmail Configuration](#gmail-configuration)
5. [TrapperJoe Configuration](#trapperjoe-configuration)
6. [Running the System](#running-the-system)
7. [Production Deployment](#production-deployment)

## Prerequisites

### Hardware Requirements

- **Meshtastic Device**: T-Deck, Heltec V3, RAK4631, or compatible device with mesh capability (WiFi enabled)
- **Computer/Server**: Windows, Linux, or Mac running Python 3.8+
- **Network**: Network access to Meshtastic device via WiFi or Ethernet

### Software Requirements

- Python 3.8 or higher
- pip (Python package manager)
- Git (for cloning the repository)
- Gmail account (for email alerts)

### Internet Requirements

- Outbound SMTP access to Gmail (port 587) for email notifications

## Installation

### Step 1: Clone the Repository

```bash
# Clone from GitHub
git clone https://github.com/yourusername/trapper-joe.git
cd trapper-joe
```

Or download as ZIP from the web interface.

### Step 2: Create Python Virtual Environment (Recommended)

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **meshtastic** — Meshtastic Python SDK
- **pypubsub** — Message pub/sub library for event handling
- **schedule** — Job scheduling for periodic tasks
- **flask** — (Optional, for future web dashboard)
- **requests** — HTTP library
- **python-dotenv** — Environment variable management

Verify installation:
```bash
python -c "import meshtastic; print(meshtastic.__version__)"
```

## Meshtastic Device Setup

### Step 1: Update Device Firmware

1. Connect your Meshtastic device to your computer via USB
2. Use the [Meshtastic Flasher](https://meshtastic.org/docs/software/web-client/) or command line
3. Flash latest stable firmware
4. Reboot device

### Step 2: Enable WiFi (for TCP Connection, Recommended)

**Via Meshtastic Client App:**
1. Open Meshtastic app (web or mobile)
2. Navigate to **Radio** → **WiFi**
3. Enable **WiFi enabled**
4. Enter your WiFi SSID and password
5. Enable **Network enabled** (for TCP access)
6. Save configuration

**Note the IP address** displayed in the WiFi settings — you'll need this for TrapperJoe config.

### Step 3: Configure Message Forwarding (Optional)

If you want the device to forward to a specific channel:
1. Go to **Channels**
2. Configure channel to receive trap sensor messages
3. Ensure your trap nodes are broadcasting on the same channel

### Step 4: Test Connection

```bash
python -c "from meshtastic.tcp_interface import TCPInterface; i = TCPInterface(hostname='192.168.178.95'); print('✅ Connected! Nodes:', list(i.nodes.keys()))"
```

Replace IP address with your device IP.

## Gmail Configuration

### Step 1: Enable 2-Factor Authentication

1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Click **Security** in the left menu
3. Under "How you sign in to Google", enable **2-Step Verification**
4. Follow the prompts to complete setup

### Step 2: Create App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Choose **Mail** and **Windows Computer** (or your device type)
3. Google will generate a unique 16-character app password
4. **Copy this password** — you'll need it in the config file

**⚠️ Important:** Never share this password. It only works for this app.

### Step 3: Test Gmail Connection

```bash
python -c "
import smtplib
user = 'your-email@gmail.com'
password = 'xxxx xxxx xxxx xxxx'  # Paste your app password (remove spaces)
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(user, password)
    server.quit()
    print('✅ Gmail authentication successful!')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

If you see `✅ Gmail authentication successful!`, you're ready to configure TrapperJoe.

## TrapperJoe Configuration

### Step 1: Create Configuration File

```bash
cd trapper-joe
cp config/trapperjoe_config.json config/trapperjoe_config.json.bak  # Backup
```

### Step 2: Edit Configuration

Open `config/trapperjoe_config.json` in your text editor:

```json
{
  "meshtastic": {
    "host": "192.168.178.95",
    "port": 4403
  },
  "email_config": {
    "user": "your-email@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "recipients": ["alert@example.com", "another@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 1,
    "schedule_times": ["06:45", "19:00"]
  }
}
```

**Configuration Options:**

| Setting | Value | Example | Notes |
|---------|-------|---------|-------|
| `host` | Meshtastic device IP | `192.168.178.95` | For TCP mode. Find via Meshtastic app WiFi settings |
| `port` | TCP port | `4403` | Standard Meshtastic port, rarely changes |
| `user` | Gmail address | `yourname@gmail.com` | Your full Gmail address |
| `app_password` | 16-char app password | `xxxx xxxx xxxx xxxx` | From Gmail app passwords (remove spaces) |
| `recipients` | Email list | `["admin@example.com"]` | Where alerts are sent! |
| `alive_timeout_hours` | Hours before "MISSING" | `1` | Sets timeout for device offline detection |
| `schedule_times` | Report times (24h) | `["06:45", "19:00"]` | When daily status emails are sent |

See [docs/CONFIGURATION.md](CONFIGURATION.md) for all available options.

### Step 3: Validate Configuration

```bash
python -c "
import json
with open('config/trapperjoe_config.json') as f:
    cfg = json.load(f)
    print('✅ Config is valid JSON')
    print(f'   Meshtastic: {cfg[\"meshtastic\"][\"host\"]}:{cfg[\"meshtastic\"][\"port\"]}')
    print(f'   Email: {cfg[\"email_config\"][\"user\"]}')
    print(f'   Recipients: {cfg[\"email_config\"][\"recipients\"]}')
"
```

## Running the System

### Single-Process Architecture

TrapperJoe runs as **a single unified process** that handles message collection, event routing, and email alerts in real-time:

```
Meshtastic Device ─── TCP ──→ listener_tcp.py ─── Event-driven ──→ Email Alerts
                               ├─ Real-time processing
                               └─ Background scheduler (timeouts + reports)
```

### Start the Listener

```bash
python meshtastic/listener_tcp.py
```

Output:
```
🌐 TrapperJoe Listener [Single Process]
   Host: 192.168.178.95:4403
   State: ./trap_state.json
   Config: ./config/trapperjoe_config.json
   
🔌 Connecting to Meshtastic (192.168.178.95:4403)...
✅ TCP connected
📡 Ready for trap events
🚀 Listener running. Waiting for messages...
```

The process will:
- ✅ Connect to Meshtastic device via TCP
- ✅ Subscribe to all message types (trap detected, admin commands, telemetry)
- ✅ Process events **in real-time** (no polling delays)
- ✅ Send alert emails immediately on state changes
- ✅ Run background scheduler for timeouts & daily reports
- ✅ Auto-reconnect on connection loss
- ✅ Handle graceful shutdown (CTRL+C)

### Testing the System

1. **Listener running:**
   ```bash
   python meshtastic/listener_tcp.py
   ```
   Should show: `✅ TCP connected` and `🚀 Listener running`

2. **Send test message from Meshtastic device:**
   - From a trap node, send: `"trap detected"`
   - In listener terminal: See message logged
   - In your email: Receive **Alert email** within seconds (no delays!)

3. **Send admin command:**
   - From authorized node: `"trap -register TestTrap1"`
   - In your email: Receive setup confirmation email

Congratulations! System is working in real-time! 🎉

## Production Deployment

### Linux/macOS (Systemd - Recommended)

Create `/etc/systemd/system/trapperjoe.service`:

```ini
[Unit]
Description=TrapperJoe Trap Monitoring System
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/trapper-joe
ExecStart=/home/pi/trapper-joe/venv/bin/python meshtastic/listener_tcp.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Resource limits to prevent resource exhaustion
MemoryMax=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable trapperjoe
sudo systemctl start trapperjoe

# Check status
sudo systemctl status trapperjoe

# View real-time logs
sudo journalctl -u trapperjoe -f
```

### Windows (Task Scheduler - Recommended)

1. Open **Task Scheduler** (Win + R → `taskschd.msc`)
2. Right-click **Task Scheduler Library** → **Create Basic Task**
3. **General tab:**
   - Name: `TrapperJoe Listener`
   - Description: Trap monitoring system
   - Checkbox: "Run whether user is logged in or not"
4. **Triggers tab:** Click **New**
   - Begin the task: "At startup"
   - Click OK
5. **Actions tab:** Click **New**
   - Action: "Start a program"
   - Program: `C:\full\path\to\venv\Scripts\python.exe`
   - Arguments: `C:\path\to\listener_tcp.py`
   - Start in: `C:\path\to\trapper-joe`
   - Click OK
6. **Conditions tab:**
   - Uncheck "Start the task only if the computer is on AC power"
7. **Settings tab:**
   - Check "Restart task if it fails"
   - Restart every: 10 seconds
   - Check "Run task as soon as possible after a scheduled start time is missed"
8. Click OK and test by rebooting

**Verify it's running:**
```cmd
tasklist | findstr python
```

### Docker (Optional)

Create `Dockerfile`:

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "meshtastic/listener_tcp.py"]
```

Build and run:
```bash
docker build -t trapperjoe .
docker run -d \
  --name trapperjoe \
  --restart always \
  -v /path/to/trapper-joe/config:/app/config \
  -v /path/to/trapper-joe/trap_state.json:/app/trap_state.json \
  trapperjoe
```

Check logs:
```bash
docker logs -f trapperjoe
```

## Troubleshooting

See [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

**Quick checks:**

```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
pip list | grep meshtastic

# Check Meshtastic connection
python -c "from meshtastic.tcp_interface import TCPInterface; TCPInterface(hostname='YOUR_IP')"

# Check Gmail connection
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"

# Check log files exist
ls meshtastic/messages_log.jsonl meshtastic/telemetry_log.jsonl
```

## Next Steps

1. ✅ System is running — monitor logs for a few days
2. 📝 Read [docs/API.md](API.md) to learn admin commands
3. 🔧 Fine-tune settings in config based on your needs
4. 📊 Check [docs/ARCHITECTURE.md](ARCHITECTURE.md) to understand data flow

---

**Happy trapping! 🪤**
