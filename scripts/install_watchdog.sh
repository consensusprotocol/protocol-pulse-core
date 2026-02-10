#!/usr/bin/env bash

# Protocol Pulse - Sovereign Watchdog installer
# This script sets up a systemd service on the Ultron server to keep
# the intelligence loop (X-Sentry + article generator) running 24/7.
#
# NOTE: This script is intended to be run on the Ultron host where
# the project lives at /home/ultron/protocol_pulse.

set -euo pipefail

echo "[watchdog] Creating systemd unit for pulse_intel.service..."

sudo bash -c 'cat > /etc/systemd/system/pulse_intel.service <<EOF
[Unit]
Description=Protocol Pulse Intelligence Watchdog
After=network.target

[Service]
User=ultron
WorkingDirectory=/home/ultron/protocol_pulse
ExecStart=/home/ultron/protocol_pulse/venv/bin/python manage.py run_intelligence_loop
Restart=always
RestartSec=10
Environment=USE_LOCAL_GPU=true LLM_DEVICE=0

[Install]
WantedBy=multi-user.target
EOF'

echo "[watchdog] Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "[watchdog] Enabling pulse_intel.service..."
sudo systemctl enable pulse_intel.service

echo "[watchdog] Starting pulse_intel.service..."
sudo systemctl start pulse_intel.service

echo "[watchdog] Done. Check status with: sudo systemctl status pulse_intel.service"

