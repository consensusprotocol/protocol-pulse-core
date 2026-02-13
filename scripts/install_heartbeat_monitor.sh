#!/usr/bin/env bash
set -euo pipefail

sudo bash -c 'cat > /etc/systemd/system/pulse_heartbeat_monitor.service <<EOF
[Unit]
Description=Protocol Pulse heartbeat self-healing monitor
After=network.target

[Service]
Type=oneshot
User=ultron
WorkingDirectory=/home/ultron/protocol_pulse
ExecStart=/home/ultron/protocol_pulse/venv/bin/python /home/ultron/protocol_pulse/scripts/heartbeat_monitor.py
EOF'

sudo bash -c 'cat > /etc/systemd/system/pulse_heartbeat_monitor.timer <<EOF
[Unit]
Description=Run pulse heartbeat monitor every 5 minutes

[Timer]
OnCalendar=*:0/5
Persistent=true
Unit=pulse_heartbeat_monitor.service

[Install]
WantedBy=timers.target
EOF'

sudo systemctl daemon-reload
sudo systemctl enable --now pulse_heartbeat_monitor.timer
echo "installed pulse_heartbeat_monitor.timer"

