# TrapperJoe Configuration Reference

Complete reference for all configuration options in `config/trapperjoe_config.json`.

## Quick Template

Use this as a starting point:

```json
{
  "meshtastic": {
    "host": "192.168.178.95",
    "port": 4403
  },
  "email_config": {
    "user": "your-email@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "recipients": ["alert@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 1,
    "schedule_times": ["06:45", "19:00"]
  }
}
```

## Configuration Sections

### meshtastic

Settings for connecting to your Meshtastic device.

```json
"meshtastic": {
  "host": "192.168.178.95",
  "port": 4403
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `host` | string | "192.168.178.95" | IP address of Meshtastic device (WiFi enabled) |
| `port` | integer | 4403 | TCP port for Meshtastic network API |

**Finding your Meshtastic IP:**
1. Open Meshtastic app on device
2. Go to **Radio** → **WiFi**
3. Note the IP address shown
4. Ensure "Network enabled" is checked

**Example for different setups:**

- **TCP/Network**: Configured via `meshtastic.host` and `meshtastic.port`

### email_config

Gmail configuration for sending alerts.

```json
"email_config": {
  "user": "your-email@gmail.com",
  "app_password": "xxxx xxxx xxxx xxxx",
  "recipients": ["alert@example.com", "backup@example.com"]
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `user` | string | "" | Your Gmail address (full email) |
| `app_password` | string | "" | 16-character Gmail app-specific password (not your regular password!) |
| `recipients` | array | [] | List of email addresses to send alerts to |

**⚠️ Security Notes:**
- Never use your main Gmail password — use app-specific password only
- App password looks like: `xxxx xxxx xxxx xxxx` (16 chars, 4 groups)
- Generate at: [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- Keep this file safe — it contains credentials
- Add to `.gitignore` to avoid committing secrets

**Using multiple recipients:**
```json
"recipients": [
  "primary@example.com",
  "secondary@example.com",
  "team@company.com"
]
```

### schedule_config

Scheduling for alerts and reports.

```json
"schedule_config": {
  "alive_timeout_hours": 1,
  "schedule_times": ["06:45", "19:00"]
}
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `alive_timeout_hours` | number | 1 | Hours without contact before trap marked MISSING |
| `schedule_times` | array | ["06:45", "19:00"] | Times (24h format) to send daily status reports |

#### alive_timeout_hours

Determines when offline traps trigger "MISSING" status:

- **0.5** (30 min) — Very aggressive, good for short-range tests
- **1** (60 min) — Standard, good balance
- **4** (240 min) — Loose, allows extended signal outages
- **24** (1 day) — Very loose, for unstable networks

When a trap hasn't sent a message for this duration:
1. Status changes to "MISSING"
2. Email alert sent with "Device offline" warning
3. Trap marked as problematic

**Example timeline:**
```
14:00 - Last message from trap
15:00 - Timeout reached (alive_timeout_hours = 1)
15:01 - Missing email sent
16:00 - Still no message, no duplicate email
17:00 - Still no message, no duplicate email
18:00 - Message received! Status back to OK
```

#### schedule_times

Daily status report emails sent at these times:

```json
"schedule_times": [
  "06:45",
  "19:00",
  "12:00"
]
```

- Format: `"HH:MM"` (24-hour format)
- Times in server's local timezone
- One email per day per scheduled time
- Email contains summary of all traps + recent events

**Common schedules:**

| Use Case | Times | Notes |
|----------|-------|-------|
| Morning briefing | `["08:00"]` | Check status after night |
| Daily check-in | `["09:00", "17:00"]` | Morning and evening |
| Per-shift | `["06:00", "14:00", "22:00"]` | 3x per day (8hr shifts) |
| Minimal | `["12:00"]` | Once daily at noon |
| No reports | `[]` | No scheduled emails (manual only) |

**Time Zone:**
- Uses server's local time zone
- If server is UTC, times are UTC
- For PST alert at 8am, if server is UTC: use `"15:00"` (8am PST = 3pm UTC)

### Advanced Configuration (Optional)

These settings are built into the code but can be modified if needed:

#### Listener retries (in listener_tcp.py)

```python
RECONNECT_DELAY = 1.0           # Initial wait (seconds)
MAX_RECONNECT_DELAY = 60.0      # Maximum wait (seconds)
LOG_RETENTION_DAYS = 7          # Days to keep logs
NODEDB_EXPORT_INTERVAL = 300    # Export NodeDB every 300s
DEBUG_MODE = False              # Show detailed debug logs
```

#### Notifier settings (in notifier.py)

```python
SLEEP_SECONDS = 10              # Check interval (seconds)
OLD_MSG_THRESHOLD = 60          # Ignore messages older than 60s
```

To modify, edit these variables in the listener/notifier Python files.

## Configuration Validation

Before running, validate your config:

```bash
# Check JSON syntax
python -c "import json; json.load(open('config/trapperjoe_config.json')); print('✅ Valid JSON')"

# Check all required fields
python -c "
import json
cfg = json.load(open('config/trapperjoe_config.json'))
assert 'meshtastic' in cfg, 'Missing meshtastic section'
assert 'host' in cfg['meshtastic'], 'Missing meshtastic.host'
assert 'email_config' in cfg, 'Missing email_config section'
print('✅ All required fields present')
"

# Test Gmail connection  
python -c "
import smtplib, json
cfg = json.load(open('config/trapperjoe_config.json'))
email_cfg = cfg['email_config']
try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_cfg['user'], email_cfg['app_password'])
    server.quit()
    print('✅ Gmail credentials OK')
except Exception as e:
    print(f'❌ Gmail error: {e}')
"

# Test Meshtastic connection
python -c "
from meshtastic.tcp_interface import TCPInterface
import json
cfg = json.load(open('config/trapperjoe_config.json'))
m = cfg['meshtastic']
try:
    i = TCPInterface(hostname=m['host'])
    print(f'✅ Meshtastic connected. Nodes: {list(i.nodes.keys())}')
    i.close()
except Exception as e:
    print(f'❌ Meshtastic error: {e}')
"
```

## Configuration Examples

### Example 1: Home Wildlife Monitor

Scenario: Single homeowner monitoring a few traps on property

```json
{
  "meshtastic": {
    "host": "192.168.1.100",
    "port": 4403
  },
  "email_config": {
    "user": "john.wildlife@gmail.com",
    "app_password": "abcd efgh ijkl mnop",
    "recipients": ["john.wildlife@gmail.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 2,
    "schedule_times": ["08:00", "18:00"]
  }
}
```

**Rationale:**
- 2-hour timeout: Account for outdoor signal variations
- Two daily briefings: Morning and evening checks

### Example 2: Professional Research Team

Scenario: Multi-person team monitoring 50+ traps in research area

```json
{
  "meshtastic": {
    "host": "192.168.178.95",
    "port": 4403
  },
  "email_config": {
    "user": "research.alerts@university.edu",
    "app_password": "xxxx xxxx xxxx xxxx",
    "recipients": [
      "lead@university.edu",
      "tech@university.edu",
      "team-alerts@university.edu"
    ]
  },
  "schedule_config": {
    "alive_timeout_hours": 1,
    "schedule_times": ["07:00", "13:00", "19:00"]
  }
}
```

**Rationale:**
- Multiple recipients: Entire team gets alerts
- Tight 1-hour timeout: Professional deployment, reliability important
- Three daily briefings: Morning, midday, evening coverage

### Example 3: Long-Distance Remote Monitoring

Scenario: Traps in remote areas with spotty connectivity

```json
{
  "meshtastic": {
    "host": "192.168.0.50",
    "port": 4403
  },
  "email_config": {
    "user": "remote.traps@example.com",
    "app_password": "abcd efgh ijkl mnop",
    "recipients": ["field.manager@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 6,
    "schedule_times": ["09:00"]
  }
}
```

**Rationale:**
- Long 6-hour timeout: Account for spotty mesh coverage
- Minimal notifications: Just daily summary to avoid alert fatigue

## Troubleshooting Config Issues

### "Connection refused" Error

**Error:** `ConnectionRefusedError: [Errno 111] Connection refused`

**Solution:**
1. Verify Meshtastic IP in config
2. Check "Network enabled" in Meshtastic app
3. Ensure computer is on same WiFi network
4. Restart Meshtastic device

### "Gmail login failed" Error

**Error:** `SMTPAuthenticationError: Application-specific password required`

**Solution:**
1. Verify you're using app-specific password (not main Gmail password)
2. Regenerate app password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) (requires 2FA)
3. Remove spaces from app password if present
4. Ensure Gmail account has 2-factor authentication enabled

### "No route to host" Error

**Error:** `socket.gaierror: [Errno 11001] getaddrinfo failed`

**Solution:**
1. Check if hostname/IP is correct
2. Test connectivity: `ping 192.168.178.95`
3. Ensure firewall allows outbound to port 4403
4. Check if Meshtastic device is powered on

## Security Best Practices

1. **Never commit secrets:**
   ```bash
   # Add to .gitignore
   echo "config/trapperjoe_config.json" >> .gitignore
   ```

2. **Use app-specific passwords:**
   - Gmail refuses login with plain password + app
   - Forces use of security-better method
   - Easy to rotate/revoke

3. **File permissions (Linux/Mac):**
   ```bash
   chmod 600 config/trapperjoe_config.json
   # Only owner can read
   ```

4. **Regular rotation:**
   - Regenerate Gmail app password every 90 days
   - Update config file
   - No system restart needed

5. **Backup safely:**
   - Keep config backups outside git
   - Encrypt if stored in cloud
   - Use secure password manager for app password

---

**Configuration Help:** See [SETUP.md](SETUP.md) for step-by-step configuration guide.
