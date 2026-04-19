# TrapperJoe Installation Guide for Raspberry Pi

> Automated wildlife trap monitoring via Meshtastic mesh networking

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Raspberry Pi Setup](#2-raspberry-pi-setup)
3. [TrapperJoe Installation](#3-trapperjoe-installation)
4. [Configuration](#4-configuration)
5. [Automatic Start (Systemd Service)](#5-automatic-start-systemd-service)
6. [Service Management](#6-service-management)
7. [Troubleshooting](#7-troubleshooting)
8. [Additional Resources](#8-additional-resources)

---

## 1. Prerequisites

### Hardware
- Raspberry Pi 4 (recommended) or Pi 3B+
- SD card (min. 16 GB, recommended 32 GB) or USB SSD
- Power supply (5V/3A for Pi 4)
- Meshtastic device (T-Deck, Heltec V3, etc.) with WiFi enabled

### Software
- Raspberry Pi OS (Lite or Desktop) — latest version recommended
- SSH access to the Raspberry Pi
- Python 3.11 or newer

### External Requirements
- Meshtastic device connected to the same local network via TCP/IP
- Gmail account with an App Password (if using email notifications)

---

## 2. Raspberry Pi Setup

### Step 1: Install Raspberry Pi OS

1. Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
2. Flash Raspberry Pi OS Lite or Desktop to your SD card
3. Boot the Raspberry Pi and complete initial setup

### Step 2: System Update

Connect via SSH and run:

```bash
sudo apt update
sudo apt upgrade -y
```

### Step 3: Install Python and Required Tools

```bash
# Python and build tools
sudo apt install -y python3 python3-pip python3-venv git

# Dependencies for Meshtastic
sudo apt install -y libusb-1.0-0-dev libusb-dev
```

### Step 4: Prepare Working Directory

```bash
mkdir -p ~/apps/trapper-joe
cd ~/apps/trapper-joe
```

---

## 3. TrapperJoe Installation

### Step 1: Clone the Repository

```bash
cd ~/apps/trapper-joe
git clone git@github.com:berkezerker/trapper-joe.git .
```

> ⚠️ The repository is private. Make sure your SSH key is set up on this Raspberry Pi and added to GitHub before cloning. Run `ssh-keygen -t ed25519 -C "RaspberryPi"` and add the public key to GitHub under Settings → SSH keys.

### Step 2: Create a Virtual Environment

```bash
cd ~/apps/trapper-joe
python3 -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` at the start of your terminal prompt.

### Step 3: Install Dependencies

```bash
# Make sure the venv is active
source .venv/bin/activate

# Install TrapperJoe and all dependencies
pip install --upgrade pip setuptools wheel
pip install -e '.[dev]'
```

Verify the installation:

```bash
trapperjoe --help
python3 -c "import meshtastic; print('OK: meshtastic')"
python3 -c "import fastapi; print('OK: fastapi')"
```

---

## 4. Configuration

### Step 1: Create the Config File

```bash
mkdir -p ~/apps/trapper-joe/config
nano ~/apps/trapper-joe/config/trapperjoe_config.json
```

Paste and adjust the following template:

```json
{
  "meshtastic": {
    "host": "192.168.x.x",
    "port": 4403
  },
  "email_config": {
    "user": "your-email@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "recipients": ["recipient@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 24,
    "schedule_times": ["08:00", "20:00"]
  }
}
```

> ⚠️ Use an App Password for Gmail — not your regular password. Go to [myaccount.google.com](https://myaccount.google.com) → Security → App Passwords (requires 2FA to be enabled).

### Step 2: Create the Logs Directory

```bash
mkdir -p ~/apps/trapper-joe/logs
chmod 755 ~/apps/trapper-joe/logs
```

---

## 5. Automatic Start (Systemd Service)

### Step 1: Create the Service File

```bash
sudo nano /etc/systemd/system/trapperjoe.service
```

Paste the following — replace `YOUR_USERNAME` with your actual Linux username (run `whoami` to check):

```ini
[Unit]
Description=TrapperJoe - Meshtastic Remote Trap Monitoring
After=network-online.target
Wants=network-online.target

[Service]
User=YOUR_USERNAME
Group=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/apps/trapper-joe
Environment="PATH=/home/YOUR_USERNAME/apps/trapper-joe/.venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/YOUR_USERNAME/apps/trapper-joe/.venv/bin/python -m trapperjoe start
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

### Step 2: Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable trapperjoe
sudo systemctl start trapperjoe
sudo systemctl status trapperjoe
```

### Step 3: Check Logs

```bash
# Live logs (Ctrl+C to stop)
sudo journalctl -u trapperjoe -f

# Last 50 lines
sudo journalctl -u trapperjoe -n 50
```

---

## 6. Service Management

| Command | Description |
|---|---|
| `sudo systemctl start trapperjoe` | Start the service |
| `sudo systemctl stop trapperjoe` | Stop the service |
| `sudo systemctl restart trapperjoe` | Restart the service |
| `sudo systemctl status trapperjoe` | Show current status |
| `sudo systemctl enable trapperjoe` | Enable auto-start on boot |
| `sudo systemctl disable trapperjoe` | Disable auto-start |

---

## 7. Troubleshooting

### Service Does Not Start After Reboot

```bash
sudo systemctl is-enabled trapperjoe
sudo systemctl enable trapperjoe
sudo journalctl -u trapperjoe -n 50
```

### ModuleNotFoundError or Import Errors

```bash
cd ~/apps/trapper-joe
source .venv/bin/activate
pip install -e '.[dev]' --force-reinstall
sudo systemctl restart trapperjoe
```

> ⚠️ If `fastapi` is missing specifically, run: `pip install fastapi uvicorn`

### Meshtastic Connection Failed

```bash
# Check the device is reachable
ping 192.168.x.x

# Test TCP port
telnet 192.168.x.x 4403

# Check config
nano ~/apps/trapper-joe/config/trapperjoe_config.json
```

Make sure **Network Server** is enabled in the Meshtastic app under Settings → Network → WiFi.

### Emails Not Being Sent

- Verify the Gmail App Password is correct (not your regular password)
- Make sure 2-Factor Authentication is enabled on your Google account
- Check logs: `sudo journalctl -u trapperjoe -f`

### Reduce SD Card Writes (Log Limits)

```bash
sudo nano /etc/systemd/journald.conf
```

Add or adjust:

```ini
SystemMaxUse=500M
RuntimeMaxUse=100M
MaxFileSec=1week
```

Then restart journald:

```bash
sudo systemctl restart systemd-journald
```

---

## 8. Additional Resources

- [Meshtastic Documentation](https://meshtastic.org/docs/)
- [Raspberry Pi Documentation](https://www.raspberrypi.com/documentation/)
- [Systemd Documentation](https://www.freedesktop.org/software/systemd/man/)
- [TrapperJoe Repository](https://github.com/berkezerker/trapper-joe)

---

*For issues, check the logs first and open a GitHub issue with relevant log output.*
