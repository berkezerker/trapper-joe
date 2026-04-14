# TrapperJoe Troubleshooting Guide

Quick solutions to common problems.

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [No Alerts Received](#no-alerts-received)
3. [Email Problems](#email-problems)
4. [Data & Logging Issues](#data--logging-issues)
5. [Performance Issues](#performance-issues)
6. [Advanced Debugging](#advanced-debugging)

## Connection Issues

### Listener won't start - "Connection refused"

**Error Message:**
```
❌ Verbindung abgelehnt: ...
ConnectionRefusedError: [Errno 111] Connection refused
```

**Causes:** Meshtastic device not reachable or not configured

**Solutions:**

1. **Check Meshtastic IP address**
   ```bash
   # In Meshtastic app: Radio → WiFi → note the IP address
   # Should be like 192.168.178.95
   # Update in config/trapperjoe_config.json
   ```

2. **Verify WiFi is enabled on device**
   - Meshtastic app → Radio → WiFi
   - Check "Enable WiFi"
   - Check "Enable NetworkServer"

3. **Test connectivity**
   ```bash
   # From your computer
   ping 192.168.178.95
   
   # Should see responses like:
   # 64 bytes from 192.168.178.95: ...
   ```

4. **Test Python connection directly**
   ```bash
   python -c "
   from meshtastic.tcp_interface import TCPInterface
   try:
       i = TCPInterface(hostname='192.168.178.95')
       print('✅ Connected! Nodes:', list(i.nodes.keys()))
       i.close()
   except Exception as e:
       print(f'❌ Error: {e}')
   "
   ```

5. **Restart Meshtastic device**
   - Power cycle or soft reboot
   - Wait 30 seconds for initialization
   - Retry connection

---

### "Timeout beim Verbinden" Error

**Error Message:**
```
❌ Timeout beim Verbinden: ...
TimeoutError: Host unreachable
```

**Causes:** Device not responding to network requests

**Solutions:**

1. **Check WiFi network**
   - Meshtastic device on same WiFi as computer?
   - Try: `ping -c 5 192.168.178.95`

2. **Wait longer**
   - Initial connection can take 10-15 seconds
   - Listener retries automatically

3. **Check firewall**
   - Windows Defender Firewall blocking port 4403?
   - Try temporarily disabling, then retry

4. **Verify port number**
   - Is `port` in config set to 4403?
   - Try other Meshtastic instances if port conflicts

---

### Listener connects then disconnects randomly

**Symptom:** Listener connects, works briefly, then shows reconnect attempts

**Causes:** Network instability or device sleep

**Solutions:**

1. **Check WiFi stability**
   - Move device closer to WiFi router
   - Check for interference (2.4GHz microwave, etc.)
   - Look at WiFi signal strength on device

2. **Disable device sleep**
   - Meshtastic settings → PowerConfig → Sleep disabled
   - Keep device plugged in if battery-powered

3. **Increase timeout thresholds**
   - In listener_tcp.py, increase `RECONNECT_DELAY` and `MAX_RECONNECT_DELAY`
   - Allows longer wait between attempts

4. **Check for device hang**
   - If device is hot or acting sluggish
   - Restart Meshtastic device completely

---

## No Alerts Received

### Messages received but no emails

**Symptom:** Can see messages in terminal but no emails arrive

**Check 1: Is Notifier running?**

```bash
# Terminal 1: Listener
$ python meshtastic/listener_tcp.py
🚀 Listener läuft...

# Terminal 2: Notifier (must be separate process!)
$ python notifier.py
🚀 TrapperJoe gestartet...
```

If Notifier terminal shows nothing, it's not running!

**Check 2: Is trap registered?**

```bash
# Look at trap_state.json
cat trap_state.json | python -m json.tool | head -20

# Should see your trap with entry like:
# "^all": {
#   "name": "Trap1",
#   "state": "OK",
#   "active": true,
#   ...
# }
```

If empty `{}`, no traps registered. Send: `trap -register MyTrap1`

**Check 3: Check Gmail config**

```bash
python -c "
import json
cfg = json.load(open('config/trapperjoe_config.json'))
print(f'Email: {cfg[\"email_config\"][\"user\"]}')
print(f'Recipients: {cfg[\"email_config\"][\"recipients\"]}')
print(f'Has password: {bool(cfg[\"email_config\"][\"app_password\"])}')
"
```

**Check 4: Test Gmail manually**

```bash
python -c "
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

cfg = json.load(open('config/trapperjoe_config.json'))
email_cfg = cfg['email_config']

msg = MIMEMultipart('alternative')
msg['Subject'] = '✅ TrapperJoe Test Email'
msg['From'] = email_cfg['user']
msg['To'] = email_cfg['recipients'][0]
msg.attach(MIMEText('TrapperJoe test message', 'html'))

try:
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(email_cfg['user'], email_cfg['app_password'])
    server.sendmail(msg['From'], email_cfg['recipients'], msg.as_string())
    server.quit()
    print('✅ Test email sent successfully')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

If this works, Gmail is OK. Check trap registration.

---

### Trap detection not triggering alert

**Symptom:** See `🚨 trapped detected` in listener but no ALERT email

**Check 1: Message format**

Listener should show:
```
🚨 ^xyz: trap detected (RSSI=-105, SNR=8.5)
```

If shows `✉️` (envelope) instead of `🚨`, message format is wrong.

**Solution:** Trap sensor must send exactly "trap detected" or use DETECTION_SENSOR_APP portnum.

**Check 2: Duplicate detection**

```bash
# Look in trap_state.json
grep "last_alert_ts" trap_state.json

# If timestamp is recent, last alert already sent
# Notifier prevents duplicate alerts within 10s
```

**Check 3: Trap not registered**

```bash
# Trap ID must exist in state
grep -o '"\\^[a-f0-9]*"' trap_state.json

# Trap ID should match sender in listener log
# If missing: send trap -register command
```

---

## Email Problems

### "Gmail authentication failed" / "Invalid credentials"

**Error Message:**
```
SMTPAuthenticationError: Application-specific password required
```

**Causes:** Wrong password or 2FA not enabled

**Solutions:**

1. **Check app-specific password format**
   ```bash
   # Should be 16 characters (4 groups of 4)
   # Example: xxxx xxxx xxxx xxxx
   # App password is NOT your Gmail password!
   ```

2. **Regenerate app password**
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select Mail and Windows Computer
   - Generate new password
   - Copy exactly (remove spaces or keep them? Try both)
   - Update in config file

3. **Verify 2FA is enabled**
   ```bash
   # account → Security → 2-Step Verification
   # Must be ON to generate app passwords
   ```

4. **Test password directly**
   ```bash
   python -c "
   import smtplib
   user = 'your-email@gmail.com'
   pwd = 'xxxx xxxx xxxx xxxx'  # Paste app password here
   try:
       s = smtplib.SMTP('smtp.gmail.com', 587)
       s.starttls()
       s.login(user, pwd)
       s.quit()
       print('✅ Password works')
   except Exception as e:
       print(f'❌ {e}')
   "
   ```

---

### Email sent but not received

**Symptom:** No error in logs but email doesn't arrive

**Check 1: Check spam folder**
- Gmail might filter autogenerated emails
- Add `trapperjoe@...` to contacts to whitelist

**Check 2: Check recipient address**
```bash
grep "recipients" config/trapperjoe_config.json

# Make sure emails are valid:
# - No typos
# - Complete addresses (include @domain)
# - Use lowercase if needed
```

**Check 3: Gmail less secure apps settings**
- Old Gmail accounts might need additional setup
- (Newer accounts with app passwords usually OK)

**Check 4: Check sent mail**
- Gmail Sent folder should show emails were sent
- If not there, authentication/config issue

---

## Data & Logging Issues

### Messages not being logged

**Symptom:** Listener running but messages_log.jsonl stays empty or unchanged

**Check 1: Verify messages arriving**
```bash
# Terminal running listener should show:
# 🚨 ^xyz: trap detected (RSSI=-105, SNR=8.5)

# If nothing shows, no messages received
# → Check Meshtastic device transmission
```

**Check 2: Check file permissions**
```bash
# Can we write to meshtastic directory?
ls -la meshtastic/

# Should not show permission denied errors
# If needed, fix permissions:
chmod 755 meshtastic/
```

**Check 3: Check disk space**
```bash
# Is there disk space available?
df -h

# Should not show < 1GB free
# Listener won't write if disk full
```

---

### Telemetry not updating

**Symptom:** Telemetry fields in trap_state.json empty (null values)

**Check 1: Device sending telemetry?**
```bash
# Check telemetry_log.jsonl
tail meshtastic/telemetry_log.jsonl

# Should see entries like:
# {"ts": 1712960..., "id": "^xyz", "type": "telemetry", "battery": 85, ...}

# If empty, device not sending telemetry
```

**Check 2: Enable device telemetry**
- Meshtastic app → Telemetry → enable options
- "Send device telemetry on interval"
- Set to reasonable interval (30s - 5m)

---

## Performance Issues

### Notifier CPU usage high / slow processing

**Possible causes:**
- Large log files (> 100MB)
- Network delays sending emails

**Solutions:**

1. **Archive old logs**
   ```bash
   # Logs older than 7 days auto-deleted
   # Manually clean:
   gzip meshtastic/messages_log.jsonl
   mv meshtastic/messages_log.jsonl.gz backup/
   
   # Notifier creates fresh log on next run
   ```

2. **Increase sleep interval**
   - In notifier.py: `SLEEP_SECONDS = 10` → `20` or `30`
   - Notifier checks less frequently
   - Slight delay in alert notices, better CPU

---

## Advanced Debugging

### Enable DEBUG mode

**Listener Debug:**
```python
# In listener_tcp.py, change:
DEBUG_MODE = False
# to:
DEBUG_MODE = True
```

**Notifier Debug:**
```bash
# Already has debug output with [DEBUG] prefix
python notifier.py 2>&1 | grep DEBUG
```

### Check raw message format

**View raw JSONL entries:**
```bash
# Last 5 messages
tail -5 meshtastic/messages_log.jsonl | python -m json.tool

# Last 5 telemetry entries
tail -5 meshtastic/telemetry_log.jsonl | python -m json.tool

# Trap state (formatted)
python -m json.tool < trap_state.json | head -50
```

### Monitor logs in real-time

**Linux/Mac:**
```bash
# Watch messages as they arrive
tail -f meshtastic/messages_log.jsonl | while read line; do 
    echo "$line" | python -m json.tool
done

# Watch notifier
tail -f /tmp/notifier.log  # or wherever logging points
```

**Windows:**
```powershell
# Watch listener output
Get-Content meshtastic\messages_log.jsonl -Wait -Tail 1
```

### Reset to clean state

**If everything is broken:**
```bash
# Backup current state
cp trap_state.json trap_state.json.bak
cp meshtastic/messages_log.jsonl meshtastic/messages_log.jsonl.bak

# Remove state and logs
rm trap_state.json
rm meshtastic/messages_log.jsonl
rm meshtastic/telemetry_log.jsonl

# Re-register traps
# Send: trap -register Trap1 (from each trap)

# System will recreate clean state
```

---

## Still Having Issues?

**Debug Checklist:**

- [ ] Meshtastic device connected and visible in app?
- [ ] WiFi enabled on Meshtastic device?
- [ ] Listener process running (shows connection message)?
- [ ] Notifier process running (separate terminal)?
- [ ] Config file has valid IP address?
- [ ] Gmail 2FA enabled and app password generated?
- [ ] Trap registered (`trap -register MyTrap`)?
- [ ] At least one trap sending messages?
- [ ] Check /tmp or logs for error messages?

**Gather info for support:**

```bash
# Create debug info file
{
    echo "=== System Info ==="
    python --version
    echo ""
    echo "=== Config (sanitized) ==="
    python -c "import json; c=json.load(open('config/trapperjoe_config.json')); c['email_config']['app_password']='***'; print(json.dumps(c,indent=2))"
    echo ""
    echo "=== Trap State ==="
    cat trap_state.json | python -m json.tool | head -30
    echo ""
    echo "=== Recent Messages ==="
    tail -5 meshtastic/messages_log.jsonl | python -m json.tool
} > debug_info.txt

# Share with support team
```

---

**Questions or still stuck?** Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.
