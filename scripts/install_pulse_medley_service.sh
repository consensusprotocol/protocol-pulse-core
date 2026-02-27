#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ultron/protocol_pulse"
SYSTEMD_DIR="${HOME}/.config/systemd/user"
SERVICE_FILE="${SYSTEMD_DIR}/pulse_medley.service"
TIMER_FILE="${SYSTEMD_DIR}/pulse_medley.timer"
RUNNER="${ROOT}/venv/bin/python ${ROOT}/scripts/run_medley_pipeline.py"

mkdir -p "${SYSTEMD_DIR}" "${ROOT}/logs"

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=Protocol Pulse Sovereign Medley Pipeline
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=${ROOT}
Environment=PYTHONUNBUFFERED=1
Environment=MEDLEY_ANALYST_GPU=0
Environment=MEDLEY_RENDER_GPU=1
ExecStart=${RUNNER}
Nice=5

[Install]
WantedBy=default.target
EOF

cat > "${TIMER_FILE}" <<EOF
[Unit]
Description=Run pulse_medley.service daily at 04:00

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true
Unit=pulse_medley.service

[Install]
WantedBy=timers.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now pulse_medley.timer
systemctl --user list-timers --all | grep pulse_medley || true
echo "pulse_medley timer installed and enabled."

