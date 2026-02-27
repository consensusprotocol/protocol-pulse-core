#!/usr/bin/env bash
set -euo pipefail

echo "[watchdog-timer] Installing pulse_watchdog.service + pulse_watchdog.timer"

sudo bash -c 'cat > /etc/systemd/system/pulse_watchdog.service <<EOF
[Unit]
Description=Protocol Pulse Self-Check Watchdog
After=network.target

[Service]
Type=oneshot
User=ultron
WorkingDirectory=/home/ultron/protocol_pulse
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ultron/protocol_pulse/venv/bin/python /home/ultron/protocol_pulse/scripts/watchdog.py --cooldown-sec 900 --max-retries 3
EOF'

sudo bash -c 'cat > /etc/systemd/system/pulse_watchdog.timer <<EOF
[Unit]
Description=Run Protocol Pulse watchdog every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true
Unit=pulse_watchdog.service

[Install]
WantedBy=timers.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable --now pulse_watchdog.timer
sudo systemctl start pulse_watchdog.service || true

echo "[watchdog-timer] Done. Check:"
echo "  sudo systemctl status pulse_watchdog.timer"
echo "  sudo systemctl status pulse_watchdog.service"

