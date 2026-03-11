#!/usr/bin/env bash
# cron_health_check.sh — Verify yesterday's Pulse Check rendered successfully.
# If not found, trigger immediate render + Resend alert.
# Cron: 0 16 * * * bash ~/protocol_pulse/scripts/cron_health_check.sh
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${BASE}/logs/cron_health_check.log"
OUTPUT_DIR="${BASE}/video_pipeline_v3/output"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
DATE_COMPACT=$(echo "$YESTERDAY" | tr -d '-')

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Health check started" >> "$LOG"

# Look for yesterday's pulse_check video
VIDEO=$(find "${OUTPUT_DIR}/${YESTERDAY}" -name "pulse_check_${DATE_COMPACT}.mp4" -type f 2>/dev/null | head -1)

if [ -n "$VIDEO" ] && [ -f "$VIDEO" ]; then
    SIZE=$(stat -c%s "$VIDEO" 2>/dev/null || stat -f%z "$VIDEO")
    SIZE_MB=$((SIZE / 1024 / 1024))
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] OK: Found $VIDEO (${SIZE_MB}MB)" >> "$LOG"
    if [ "$SIZE_MB" -lt 50 ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] WARN: Video size ${SIZE_MB}MB < 50MB" >> "$LOG"
    fi
    exit 0
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] ALERT: No video found for $YESTERDAY — triggering render" >> "$LOG"

# Send Resend alert
cd "$BASE"
export $(grep -v '^#' .env | xargs) 2>/dev/null || true
python3 -c "
import resend, os
resend.api_key = os.environ.get('RESEND_API_KEY', '')
if resend.api_key:
    resend.Emails.send({
        'from': 'pulse@protocolpulse.io',
        'to': ['contact@consensusprotocol.org'],
        'subject': 'ALERT: Pulse Check missing for $YESTERDAY',
        'html': '<pre>No pulse_check video found for $YESTERDAY.\nTriggering immediate render.</pre>',
    })
    print('Alert sent')
else:
    print('No RESEND_API_KEY')
" 2>> "$LOG"

# Trigger immediate render
cd "${BASE}/video_pipeline_v3"
/usr/bin/python3 daily_producer.py >> "${BASE}/logs/pulse_check.log" 2>&1 &
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Recovery render triggered (PID $!)" >> "$LOG"
