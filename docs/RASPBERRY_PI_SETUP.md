# TrapperJoe Installation Guide für Raspberry Pi

Eine vollständige Anleitung zur Installation von TrapperJoe auf einem Raspberry Pi mit automatischem Start nach jedem Neustart.

## Inhaltsverzeichnis

1. [Voraussetzungen](#voraussetzungen)
2. [Raspberry Pi Vorbereitung](#raspberry-pi-vorbereitung)
3. [TrapperJoe Installation](#trapperjoe-installation)
4. [Konfiguration](#konfiguration)
5. [Automatischer Start (Systemd Service)](#automatischer-start-systemd-service)
6. [Verwaltung und Debugging](#verwaltung-und-debugging)
7. [Tipps und Troubleshooting](#tipps-und-troubleshooting)

## Voraussetzungen

### Hardware
- Raspberry Pi 3B+ oder neuer (empfohlen: Pi 4 oder Pi 5)
- SD-Karte (mindestens 16 GB, empfohlen 32 GB)
- Netzteil (5V/3A für Pi 4)
- Optional: Gehäuse und Kühlkörper

### Software
- Raspberry Pi OS (Lite oder Desktop) - empfohlen: aktuellste Version
- SSH-Zugriff zum Raspberry Pi

### Externe Anforderungen
- Meshtastic Gerät (T-Deck, Heltec V3, etc.) mit WiFi-Verbindung
- Gmail Konto mit App-spezifisches Passwort
- Internetverbindung

---

## Raspberry Pi Vorbereitung

### Schritt 1: Raspberry Pi OS installieren

1. Laden Sie den **Raspberry Pi Imager** herunter: https://www.raspberrypi.com/software/
2. Flashen Sie Raspberry Pi OS Lite oder Desktop auf die SD-Karte
3. Starten Sie den Raspberry Pi und führen Sie die erste Konfiguration durch

### Schritt 2: System-Update durchführen

Verbinden Sie sich per SSH mit dem Raspberry Pi und führen Sie folgende Befehle aus:

```bash
sudo apt update
sudo apt upgrade -y
```

### Schritt 3: Python 3.11+ und benötigte Tools installieren

```bash
# Python und Build-Tools installieren
sudo apt install -y python3 python3-pip python3-venv git

# Abhängigkeiten für Meshtastic
sudo apt install -y libusb-1.0-0-dev libusb-dev

# Systemd-Utils (für Service-Verwaltung)
sudo apt install -y systemd
```

### Schritt 4: Arbeitsverzeichnis vorbereiten

```bash
# Erstellen Sie ein Verzeichnis für TrapperJoe
mkdir -p ~/apps/trapper-joe
cd ~/apps/trapper-joe
```

---

## TrapperJoe Installation

### Schritt 1: Repository klonen

```bash
cd ~/apps/trapper-joe
git clone https://github.com/yourusername/trapper-joe.git .
```

Falls Sie ein ZIP heruntergeladen haben:
```bash
cd ~/apps/trapper-joe
unzip /pfad/zu/trapper-joe.zip
```

### Schritt 2: Python Virtual Environment erstellen

```bash
cd ~/apps/trapper-joe

# Virtual Environment anlegen
python3 -m venv venv

# Virtual Environment aktivieren
source venv/bin/activate
```

### Schritt 3: Dependencies installieren

```bash
# Stelle sicher, dass das venv aktiviert ist
source venv/bin/activate

# Installiere Requirements
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

Überprüfe die Installation:
```bash
python -c "import meshtastic; print('✓ Meshtastic installiert')"
python -c "import schedule; print('✓ Schedule installiert')"
```

### Schritt 4: TrapperJoe als Paket installieren

```bash
# Stelle sicher, dass das venv aktiviert ist
source venv/bin/activate

# Installiere TrapperJoe im Development-Modus
pip install -e .
```

Überprüfe die Installation:
```bash
trapperjoe --help
```

---

## Konfiguration

### Schritt 1: Gmail App-Passwort erstellen

1. Öffne https://myaccount.google.com/
2. Gehe zu **Sicherheit** → **App-Passwörter** (2FA muss aktiviert sein)
3. Wähle **Mail** und **Windows-Computer**
4. Kopiere das generierte 16-stellige Passwort

### Schritt 2: TrapperJoe Konfigurationsdatei erstellen

```bash
cd ~/apps/trapper-joe
cp config/trapperjoe_config.example.json config/trapperjoe_config.json
```

Bearbeite die Konfigurationsdatei:
```bash
nano config/trapperjoe_config.json
```

**Wichtige Einstellungen:**

```json
{
  "meshtastic": {
    "host": "192.168.x.x",
    "port": 4403,
    "connection_type": "tcp"
  },
  "email": {
    "sender_email": "deine-email@gmail.com",
    "sender_password": "xxxx xxxx xxxx xxxx",
    "recipient_emails": ["empfaenger@example.com"],
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587
  },
  "logging": {
    "log_file": "/home/pi/apps/trapper-joe/logs/trapperjoe.log",
    "log_level": "INFO"
  }
}
```

### Schritt 3: Logs-Verzeichnis erstellen

```bash
mkdir -p ~/apps/trapper-joe/logs
chmod 755 ~/apps/trapper-joe/logs
```

---

## Automatischer Start (Systemd Service)

### Schritt 1: Systemd Service-Datei erstellen

Erstelle eine neue Service-Datei:

```bash
sudo nano /etc/systemd/system/trapperjoe.service
```

Füge folgende Inhalte ein:

```ini
[Unit]
Description=TrapperJoe - Meshtastic Remote Trap Monitoring
After=network-online.target
Wants=network-online.target

[Service]
# Benutzer, unter dem der Service läuft
User=pi
Group=pi

# Arbeitsverzeichnis
WorkingDirectory=/home/pi/apps/trapper-joe

# Umgebungsvariablen
Environment="PATH=/home/pi/apps/trapper-joe/venv/bin"
Environment="PYTHONUNBUFFERED=1"

# Start-Befehl
ExecStart=/home/pi/apps/trapper-joe/venv/bin/python -m trapperjoe

# Neustart-Einstellungen
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Timeout-Einstellungen
TimeoutStopSec=30
KillMode=mixed

[Install]
WantedBy=multi-user.target
```

### Schritt 2: Service aktivieren und starten

```bash
# Systemd-Konfiguration neu laden
sudo systemctl daemon-reload

# Service aktivieren (startet automatisch nach Reboot)
sudo systemctl enable trapperjoe

# Service jetzt starten
sudo systemctl start trapperjoe

# Status prüfen
sudo systemctl status trapperjoe
```

### Schritt 3: Logs überprüfen

```bash
# Live-Logs anschauen
sudo journalctl -u trapperjoe -f

# Letzte 50 Zeilen anschauen
sudo journalctl -u trapperjoe -n 50

# Logs mit Zeitstempel
sudo journalctl -u trapperjoe --no-pager | tail -20
```

---

## Verwaltung und Debugging

### Service-Kommandos

```bash
# Service starten
sudo systemctl start trapperjoe

# Service stoppen
sudo systemctl stop trapperjoe

# Service neu starten
sudo systemctl restart trapperjoe

# Status anschauen
sudo systemctl status trapperjoe

# Auto-Start deaktivieren
sudo systemctl disable trapperjoe

# Auto-Start aktivieren
sudo systemctl enable trapperjoe
```

### Logs überprüfen

```bash
# Echtzeit-Logs (Ctrl+C zum Beenden)
sudo journalctl -u trapperjoe -f --output=short-iso

# Fehler der letzten Stunde
sudo journalctl -u trapperjoe --since "1 hour ago" --priority err

# Alle Logs für heute
sudo journalctl -u trapperjoe --since today

# Logs exportieren in Datei
sudo journalctl -u trapperjoe -n 1000 > trapperjoe-logs.txt
```

### Debugging: Service manuell testen

```bash
# SSH in den Pi verbinden
ssh pi@192.168.x.x

# In das Verzeichnis wechseln
cd ~/apps/trapper-joe

# Virtual Environment aktivieren
source venv/bin/activate

# TrapperJoe direkt starten (zeigt Fehler direkt an)
python -m trapperjoe

# Mit Ctrl+C beenden
```

### Konfiguration testen

```bash
# Meshtastic-Verbindung testen
cd ~/apps/trapper-joe
source venv/bin/activate
python -c "import meshtastic; iface = meshtastic.mesh_pb2; print('✓ Meshtastic arbeitet')"

# Konfiguration laden und überprüfen
python -c "import json; print(json.dumps(json.load(open('config/trapperjoe_config.json')), indent=2))"
```

---

## Tipps und Troubleshooting

### Problem: Service startet nicht nach Reboot

**Lösung:**
```bash
# Überprüfe, ob der Service aktiviert ist
sudo systemctl is-enabled trapperjoe

# Falls nicht aktiviert:
sudo systemctl enable trapperjoe

# Logs prüfen für Fehler
sudo journalctl -u trapperjoe -n 50
```

### Problem: "ModuleNotFoundError" oder Import-Fehler

**Lösung:**
```bash
# Stelle sicher, dass das venv komplett installiert ist
cd ~/apps/trapper-joe
source venv/bin/activate
pip install -r requirements.txt --force-reinstall

# Service neu starten
sudo systemctl restart trapperjoe
```

### Problem: Meshtastic-Verbindung fehlgeschlagen

**Lösung:**
```bash
# Überprüfe die IP-Adresse des Meshtastic-Geräts
# Öffne die Meshtastic-App und notiere die IP

# Teste die Verbindung manuell
ping 192.168.x.x

# Teste die TCP-Verbindung
telnet 192.168.x.x 4403

# In der Konfiguration überprüfen:
nano config/trapperjoe_config.json
# Stelle sicher, dass "host" und "port" korrekt sind
```

### Problem: E-Mails werden nicht gesendet

**Lösung:**
```bash
# Überprüfe Gmail App-Passwort und E-Mail-Adresse
nano config/trapperjoe_config.json

# Test E-Mail manuell senden (Logs prüfen)
sudo journalctl -u trapperjoe -f

# Stelle sicher, dass "Weniger sichere Apps" in Gmail aktiviert ist:
# https://myaccount.google.com/security
```

### Problem: Hohe CPU- oder Memory-Auslastung

**Lösung:**
```bash
# Überprüfe Resource-Nutzung
top -p $(pgrep -f "python -m trapperjoe")

# Überprüfe Fehler in den Logs
sudo journalctl -u trapperjoe --priority err
```

### Service-Logs begrenzen (um SD-Karte zu schonen)

Bearbeite die Systemd-Journald-Konfiguration:

```bash
sudo nano /etc/systemd/journald.conf
```

Füge folgende Zeilen hinzu oder passe sie an:

```ini
SystemMaxUse=500M
RuntimeMaxUse=100M
MaxFileSec=1week
```

Speichere und starten Sie neu:

```bash
sudo systemctl restart systemd-journald
```

### Automatische Logs-Rotation

Erstelle eine Logrotate-Konfiguration:

```bash
sudo nano /etc/logrotate.d/trapperjoe
```

Füge folgende Inhalte ein:

```
/home/pi/apps/trapper-joe/logs/trapperjoe.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0640 pi pi
}
```

---

## Zusätzliche Ressourcen

- **Meshtastic Dokumentation**: https://meshtastic.org/docs/
- **Raspberry Pi Dokumentation**: https://www.raspberrypi.com/documentation/
- **Systemd Dokumentation**: https://www.freedesktop.org/software/systemd/man/

## Support

Falls du auf Probleme stößt:

1. Überprüfe die Logs: `sudo journalctl -u trapperjoe -n 100`
2. Teste die Komponenten einzeln (Meshtastic, Gmail, etc.)
3. Öffne ein Issue auf GitHub mit Logs und Fehlermeldungen
