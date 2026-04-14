# TrapperJoe System Architecture

Comprehensive documentation of the TrapperJoe system design, components, and data flow.

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Architecture](#component-architecture)
3. [Data Flow](#data-flow)
4. [Database & State Management](#database--state-management)
5. [Message Types & Protocols](#message-types--protocols)
6. [Event Processing Pipeline](#event-processing-pipeline)
7. [Health & Recovery](#health--recovery)

## System Overview

TrapperJoe is a **unified IoT monitoring system** with integrated event processing:

```
TIER 1: Sensors                    TIER 2: Processing & Alerts
        (Remote Nodes)             (Single Process)

┌──────────────────┐              ┌─────────────────────────────────┐
│ Trap Sensors     │              │  MeshtasticListener Process     │
│ (Mesh Network)   │──────TCP────>│  ┌─────────────────────────┐   │
│                  │              │  │ • TCP Connection Mgmt   │   │
│                  │              │  │ • Event-driven Router   │   │
└──────────────────┘              │  │ • Alert Engine (Email)  │   │
                                  │  │ • State Manager         │   │
                                  │  └─────────────────────────┘   │
                                  │                                 │
                                  │  Background Scheduler Thread:   │
                                  │  • Timeout Detection            │
                                  │  • Scheduled Reports            │
                                  │  • NodeDB Snapshots             │
                                  └─────────────────────────────────┘
                                           │
                                           v
                                  Persistent State:
                                  - trap_state.json (authority)
                                  - nodedb.json (snapshot)
                                  - config/trapperjoe_config.json
```

**Architecture Principle:** Everything runs in a **single process**, eliminating inter-process log coupling and race conditions. Event-driven processing ensures immediate response to trap events.

## Component Architecture

### 1. Remote Trap Sensors

**Role:** Detect trap activation and environmental conditions

**Hardware:** Meshtastic nodes with trap sensors
- Detection sensor module (trap spring trigger)
- Optional: temperature, humidity, battery monitoring

**Output:** Broadcasts messages on the mesh network:
- `DETECTION_SENSOR_APP` → "trap detected" (trap triggered)
- `TEXT_MESSAGE_APP` → "trap reset" (manual reset) or admin commands
- `TELEMETRY_APP` → Device metrics (battery %, voltage, temperature)

**Portnum Values:**
- `TEXT_MESSAGE_APP` = 1 or "TEXT_MESSAGE_APP"
- `DETECTION_SENSOR_APP` = 4 or "DETECTION_SENSOR_APP"
- `TELEMETRY_APP` = 67 or "TELEMETRY_APP"

### 2. MeshtasticListener (Integrated Process)

**File:** `meshtastic/listener_tcp.py`

**Role:** Single unified process that combines:
- TCP connection to Meshtastic device
- Event-driven message routing
- Real-time alert generation
- Trap state management
- Background scheduler for timeouts and reports

**Architecture:**

```
┌─────────────────────────────────────────────────────┐
│  MeshtasticListener Main Process                    │
│                                                     │
│  Main Thread:                                       │
│  ├─ TCP Connection Manager (auto-reconnect)        │
│  ├─ Pub/Sub Event Router (on_receive callback)     │
│  ├─ Message Classifier (by portnum)                │
│  ├─ Trap State Updater (trap_state.json)           │
│  └─ Email Alert Dispatcher                         │
│                                                     │
│  Background Scheduler Thread:                      │
│  ├─ Timeout Detection (device offline check)      │
│  ├─ Scheduled Reports (daily status mail)         │
│  ├─ NodeDB Snapshots (nodedb.json export)         │
│  └─ Periodic Health Checks                         │
└─────────────────────────────────────────────────────┘
```

**Key Classes & Functions:**

| Component | Purpose |
|-----------|---------|
| `MeshtasticListener` | Main orchestrator class |
| `connect()` | Establish TCP connection with exponential backoff |
| `on_receive(packet)` | Real-time callback when packet arrives |
| `process_trap_message()` | Parse and classify trap events (detected/reset) |
| `process_telemetry()` | Extract device metrics (battery, RSSI, SNR) |
| `handle_admin_command()` | Parse and execute remote admin commands |
| `send_email_alert()` | Generate and send HTML email alerts |
| `_scheduler_loop()` | Background thread: timeouts, reports, exports |

**Key Responsibilities:**

**Real-time (Main Thread - on_receive callback):**
- Subscribe to Meshtastic message events
- Route packets by portnum (TEXT, DETECTION, TELEMETRY)
- Update trap_state.json immediately
- Generate and send alert emails on state changes
- Handle admin commands synchronously

**Scheduled (Background Thread - every 10 seconds):**
- Check for device timeouts (alive_timeout_hours exceeded)
- Send "device offline" warnings
- Check scheduled times for daily status reports
- Export NodeDB snapshot periodically
- Verify TCP connection health

**Error Handling:**
- Automatic reconnect on connection loss (exponential backoff: 1s → 60s max)
- Graceful shutdown on SIGTERM/SIGINT
- Email send failures logged but don't crash system
- Malformed message handling (parse errors logged)

### 3. Configuration Manager

**File:** `config/trapperjoe_config.json`

**Structure:**
```json
{
  "meshtastic": {
    "host": "192.168.178.95",
    "port": 4403
  },
  "email_config": {
    "user": "your-email@gmail.com",
    "app_password": "xxxx xxxx xxxx xxxx",
    "recipients": ["alert1@example.com", "alert2@example.com"]
  },
  "schedule_config": {
    "alive_timeout_hours": 1,
    "schedule_times": ["06:45", "19:00"]
  }
}
```

See [CONFIGURATION.md](CONFIGURATION.md) for complete reference.

## Data Flow

### 1. Real-time Message Reception & Processing

```
Trap Sensor (Mesh Node)
        ↓
    Broadcasts Message
        ↓
Meshtastic Device (WiFi/Radio)
        ↓
Listener TCP Connection (port 4403)
        ↓
    Pub/Sub: "meshtastic.receive" event
        ↓
    on_receive(packet) callback [REAL-TIME]
        ↓
    Parse portnum → Classify by type:
        ├─ portnum=1 (TEXT_MESSAGE_APP)
        │   └─> process_trap_message()
        │
        ├─ portnum=4 (DETECTION_SENSOR_APP)
        │   └─> Auto-convert to "trap detected"
        │
        └─ portnum=67 (TELEMETRY_APP)
            └─> process_telemetry()
        ↓
    Extract: RSSI, SNR, battery, voltage, timestamp
        ↓
    Update trap_state.json (immediate state change)
        ↓
    State changed? → Send alert email immediately
```

**Key Point:** Processing happens **immediately on receipt** (milliseconds), not polling from log files.

### 2. Admin Command Flow

```
Authorized Sender → "trap -register Name"
        ↓
    on_receive(packet) callback
        ↓
    Message starts with "trap -"?
        ↓
    handle_admin_command(msg)
        ├─ trap -register [name]   → Create/update trap entry
        ├─ trap -status            → Console output
        ├─ trap -reset             → Set state to OK
        ├─ trap -remove            → Delete trap
        └─ trap -statusmail        → Send immediate status report
        ↓
    Update trap_state.json
        ↓
    Send confirmation email
```

### 3. Timeout Detection Flow (Background Thread)

```
Background Scheduler Loop (every 10 seconds):
        ↓
    For each trap in trap_state.json:
        ↓
    Calculate: time_since_heard = now - lastHeard
        ↓
    if time_since_heard > alive_timeout_hours × 3600:
        ├─ if state != "MISSING":
        │  ├─ old_state = state
        │  ├─ state = "MISSING"
        │  ├─ Add to alert queue
        │  └─ Send timeout email
        │
        └─ else: no change
        ↓
    repeat
```

### 4. Scheduled Status Report Flow (Background Thread)

```
Background Scheduler Loop (every 10 seconds):
        ↓
    current_time matches schedule_times?
    (e.g., "06:45" or "19:00")
        ↓
    YES:
        ├─ Generate status_report_html()
        ├─ Include all trap statuses (OK/ALERT/MISSING)
        ├─ Send email to recipients
        ├─ Update _last_status_day to prevent duplicates
        └─ Mark as sent
        ↓
    NO: Continue loop
```

## Database & State Management

### trap_state.json Structure

```json
{
  "_last_status_day": "2024-04-12",   // Last status report date (prevents duplicates)
  "^all": {
    "name": "Trap1",                  // User-defined trap name
    "state": "OK",                    // OK | ALERT | MISSING
    "active": true,                   // Is trap being monitored?
    "lastHeard": 1712960130,          // Unix timestamp of last message
    "battery": 85,                    // Battery percentage (0-100)
    "voltage": 4.15,                  // Voltage (V)
    "rssi": -105,                     // Signal strength (dBm), lower is weaker
    "snr": 8.5,                       // Signal-to-noise ratio (dB)
    "lastEventType": "DETECTION",     // DETECTION | RESET | (empty)
    "last_alert_ts": 1712960100,      // Timestamp of last alert (prevent duplicates)
    "last_reset_ts": 1712960050,      // Timestamp of last reset confirmation
    "last_statusmail_ts": 1712900000  // Timestamp of last status report
  }
}
```

**Key Field Explanations:**

- **state**: Current trap condition
  - `OK` — Trap ready, no recent detections
  - `ALERT` — Recent detection, needs investigation
  - `MISSING` — Device offline (no contact for `alive_timeout_hours`)

- **lastHeard**: Unix timestamp when device last sent any message (used to calculate timeout)

- **battery/voltage**: Device power status
  - Low battery triggers warning in emails
  - Voltage used for power state assessment

- **rssi**: Received Signal Strength Indicator
  - Range: -40 (excellent) to -120 (unusable)
  - Used to assess connection quality

- **snr**: Signal-to-Noise Ratio
  - Higher is better (typical range: -5 to +10 dB)
  - Combined with RSSI for quality assessment

### nodedb.json Structure

Periodic snapshot of mesh network nodes:

```json
{
  "^all": {
    "num": 42,
    "user": {
      "id": "^all",
      "shortName": "Trap1",
      "longName": "Trap1-Sensor",
      "hwModel": "T3_V1_5"
    },
    "position": {
      "latitude": 47.5,
      "longitude": 8.9,
      "altitude": 500,
      "time": 1712960000
    },
    "deviceMetrics": {
      "batteryLevel": 85,
      "voltage": 4150,
      "channelUtilization": 12.5,
      "airUtilTx": 2.3,
      "uptimeSeconds": 86400
    },
    "lastHeard": 1712960130
  }
}
```

**Purpose:** Archive of mesh topology for debugging and historical reference. Updated periodically by background scheduler.

## Message Types & Protocols

### Supported Message Types

#### 1. TEXT_MESSAGE_APP (portnum = 1)

**Source:** Any Meshtastic node sending text

**Parsed Messages:**

| Message | Action | Result |
|---------|--------|--------|
| "trap detected" | Set ALERT state | Alert email sent |
| "trap reset" | Set OK state | Reset email sent |
| "trap -register [name]" | Register trap | Status report sent |
| "trap -status" | Query trap status | Console output |
| "trap -statusmail" | Request report | Status email sent |
| "trap -remove" | Unregister trap | Trap deleted from state |

#### 2. DETECTION_SENSOR_APP (portnum = 4)

**Source:** Trap sensor module broadcasting detection

**Message:** Always "trap detected"

**Behavior:**
- Automatically converted to "trap detected" by listener
- Triggers ALERT state and alert email
- No text parsing needed

#### 3. TELEMETRY_APP (portnum = 67)

**Source:** Device sending metrics (battery, temp, etc.)

**Data Extracted:**
- Battery level (%)
- Voltage (mV)
- Temperature (°C)
- Channel utilization
- Air TX utilization
- Uptime (seconds)

**Processing:**
- Extracted and immediately stored in trap_state.json
- Used to update device metrics
- No messages generated

## Event Processing Pipeline

### Real-time Message Processing

When a Meshtastic message arrives, the `on_receive()` callback executes immediately:

```
1. Packet received via Pub/Sub
   └─> on_receive(packet) callback triggered [< 1ms]

2. Extract message metadata
   ├─ packet.from (sender node ID)
   ├─ packet.rx_time (timestamp)
   ├─ packet.rx_rssi (signal strength)
   ├─ packet.rx_snr (noise ratio)
   └─ packet.decoded.portnum (message type)

3. Classify by portnum
   ├─ portnum=1 (TEXT): process_trap_message()
   ├─ portnum=4 (DETECTION): Auto-convert to "detected"
   └─ portnum=67 (TELEMETRY): process_telemetry()

4. Load trap_state.json
   └─> if trap_id not registered: skip (untracked device)

5. Check for admin commands (starts with "trap -")
   ├─ YES: handle_admin_command()
   │   ├─ trap -register: create/update trap entry
   │   ├─ trap -reset: set state=OK
   │   ├─ trap -remove: delete trap
   │   ├─ trap -status: print to console
   │   └─ trap -statusmail: send immediate report
   │
   └─ NO: check message content

6. Classify trap message
   ├─ "detected" → new_state = ALERT
   ├─ "reset"    → new_state = OK
   └─ other      → new_state = current (no change)

7. State transition check
   ├─ State changed?
   │   ├─ OK → ALERT: send alert email immediately
   │   ├─ ALERT → OK: send reset confirmation email
   │   └─ Other: send timeout warning email
   └─ State unchanged: no email

8. Update trap_state.json
   ├─ state = new_state
   ├─ lastHeard = now
   ├─ update battery/rssi/snr/voltage
   ├─ lastEventType = message type
   └─ save to disk (atomic write)
```

**Timing:** Entire flow completes in ~10-50ms, ensuring real-time responsiveness.

### Background Scheduler Loop (Every 10 Seconds)

Runs in dedicated thread, independent of real-time processing:

```
while running:
   │
   ├─> FOR EACH trap in trap_state.json:
   │   │
   │   ├─ Time since device last heard: delta = now - lastHeard
   │   │
   │   ├─ If delta > alive_timeout_hours × 3600:
   │   │   ├─ if state != MISSING:
   │   │   │  ├─ State change: state = MISSING
   │   │   │  ├─ Queue timeout email
   │   │   │  └─ Send email to recipients
   │   │   │
   │   │   └─ else: no email (already MISSING)
   │   │
   │   └─ Else: state unchanged (device recently heard)
   │
   ├─> IF current_time matches schedule_times:
   │   ├─ AND today != _last_status_day:
   │   │  ├─ Generate status report (all trap statuses)
   │   │  ├─ Send email to recipients
   │   │  ├─ Update _last_status_day = today
   │   │  └─ Write trap_state.json
   │   │
   │   └─ else: skip (already sent today)
   │
   ├─> Check NodeDB export schedule:
   │   ├─ Export nodedb.json if needed
   │   └─ Health check TCP connection
   │
   └─> Sleep 10 seconds, repeat
```

**Thread Safety:**
- Background thread uses file-based locking on trap_state.json
- Real-time thread and scheduler thread never access JSON simultaneously
- All state updates are atomic (write + rename)

## Health & Recovery

### Automatic Reconnection

**Exponential Backoff Strategy:**
- Initial wait: `RECONNECT_DELAY` (1 second)
- Max wait: `MAX_RECONNECT_DELAY` (60 seconds)
- Multiplier: 2x on each failure
- Sequence: 1s → 2s → 4s → 8s → 16s → 32s → 60s → 60s...

**Code:**
```python
self.backoff = min(self.backoff * 2, MAX_RECONNECT_DELAY)
time.sleep(self.backoff)
ok = self.connect()
```

### Health Checks

**Main Thread Health Check (continuous):**
```python
# TCP connection monitored via Pub/Sub events
# If no packets received and connection appears dead:
# → Trigger reconnection
```

**Background Thread:**
```python
# Runs every 10 seconds
# Checks trap states, timeouts, schedules
# Exports NodeDB periodically
# If TCP connection is dead: main thread will reconnect
```

### Error Handling

| Error | Handler | Result |
|-------|---------|--------|
| TCP Connection Refused | Retry with exponential backoff | Attempts reconnect loop |
| Malformed message | Log warning, skip packet | Doesn't crash |
| Email send failure | Log error, retry next cycle | Ensures notification retry |
| Config file missing | Error on startup | Prevents data loss |
| trap_state.json corruption | Reload from backup or empty | Continue with clean state |

### Data Persistence

**On Shutdown:**
- trap_state.json saved with current state
- Listener unsubscribes from events
- TCP interface properly closed
- Background thread stopped gracefully

**On Startup:**
- trap_state.json loaded (if exists)
- Last status report date checked (prevents duplicate emails after restart)
- TCP connection established
- Background scheduler started

---

## Troubleshooting Guide

**System stops receiving messages:**
1. Check listener logs for connection errors
2. Verify Meshtastic device IP/port in config
3. Check network connectivity to Meshtastic device
4. Restart listener process: `python meshtastic/listener_tcp.py`

**Alerts not sending:**
1. Check email configuration in `config/trapperjoe_config.json`
2. Verify sender account has Gmail app password set up
3. Check firewall allows SMTP to Gmail (port 587)
4. Review listener logs for email send errors

**Device shows MISSING but is online:**
1. Check `alive_timeout_hours` setting (default 1 hour)
2. Verify Meshtastic device is in mesh range with good reception
3. Check RSSI/SNR values in trap state (very low signal = timeouts likely)
4. Reset trap state with `trap -reset` command

**High CPU usage:**
1. Check for network communication errors (too many reconnects)
2. Verify scheduler thread isn't stuck in loop (check logs)
3. Review for email send failures causing retries
