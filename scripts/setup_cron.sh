#!/usr/bin/env bash
# setup_cron.sh — Idempotent cron installer for Protocol Pulse.
# Run anytime: bash ~/protocol_pulse/scripts/setup_cron.sh
set -euo pipefail

BASE="$(cd "$(dirname "$0")/.." && pwd)"
MARKER_START="# ── Protocol Pulse Automated Pipelines ──"
MARKER_END="# ── End Protocol Pulse ──"

# Ensure log directory exists
mkdir -p "${BASE}/logs"

# Build the cron block
CRON_BLOCK=$(cat <<'CRON'
# ── Protocol Pulse Automated Pipelines ──
# Updated by setup_cron.sh — do not edit between markers

# Log rotation — Weekly (Sunday midnight UTC)
0 0 * * 0 find /home/ultron/protocol_pulse/logs -name "*.log" -size +50M -exec truncate -s 0 {} \;

# Oracle Briefing — Daily at 7 AM EST (12 UTC)
0 12 * * * cd /home/ultron/protocol_pulse/oracle_briefing && /usr/bin/python3 briefing_producer.py >> /home/ultron/protocol_pulse/logs/oracle_briefing.log 2>&1

# HeyGen Oracle Briefings — Sarah (3x/day)
# Morning: 8 AM EST (13 UTC)
0 13 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type morning >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1
# Midday: 1 PM EST (18 UTC)
0 18 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type midday >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1
# Evening: 6:30 PM EST (23:30 UTC)
30 23 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/heygen_briefing.py --type evening >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1

# Newsletter — Daily at 8 AM EST (13 UTC)
0 13 * * * curl -s -X POST http://localhost:5000/api/newsletter/send -H "Authorization: Bearer 581b1076" >> /home/ultron/logs/newsletter_cron.log 2>&1

# Medley Engine V2 — Daily at 8 AM EST (13 UTC)
0 13 * * * LD_LIBRARY_PATH="/usr/local/lib/ollama/cuda_v12:/usr/local/cuda/lib64" /home/ultron/protocol_pulse/medley_engine_v2/daily_run.sh >> /tmp/medley_daily.log 2>&1

# Pulse Check V4 — Daily at 9 AM EST (14 UTC)
0 14 * * * cd /home/ultron/protocol_pulse/video_pipeline_v3 && /usr/bin/python3 daily_producer.py >> /home/ultron/protocol_pulse/logs/pulse_check.log 2>&1

# Pulse Check Cron Health Check — Daily at 11 AM EST (16 UTC)
0 16 * * * bash /home/ultron/protocol_pulse/scripts/cron_health_check.sh

# PBX Weekly Report — Tuesday + Friday at 10 AM EST (15 UTC)
0 15 * * 2,5 cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/pbx_report.py >> /home/ultron/protocol_pulse/logs/pbx_report.log 2>&1

# Mining Intel — Twice weekly (Wed + Sun at 10 AM EST = 15 UTC)
0 15 * * 3,0 cd /home/ultron/protocol_pulse/mining_intel && /usr/bin/python3 mining_intel_scheduler.py >> /home/ultron/protocol_pulse/logs/mining_intel.log 2>&1

# Pulse Check Video Pipeline V5 — Daily at 6 PM EST (23 UTC)
0 23 * * * /home/ultron/protocol_pulse/services/video_engine/run_daily.sh >> /home/ultron/protocol_pulse/logs/video_pipeline.log 2>&1

# Image Backfill — Weekly Monday 3 AM EST (08 UTC)
0 8 * * 1 cd /home/ultron/protocol_pulse && /usr/bin/python3 scripts/image_backfill_pexels.py >> /home/ultron/protocol_pulse/logs/image_backfill.log 2>&1

# Spaces Scraper — Check for live spaces every 10 minutes
*/10 * * * * cd ~/protocol_pulse && /usr/bin/python3 -m x_spaces_scraper.run_scraper >> logs/x_spaces_scraper.log 2>&1

# Channel Daemon — every 15 min
*/15 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/channel_daemon.py >> logs/channel_daemon.log 2>&1

# TradFi Monitor — every 30 min
*/30 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/tradfi_monitor.py >> logs/tradfi_monitor.log 2>&1

# Live Monitor — every 5 min
*/5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/live_monitor.py >> logs/live_monitor.log 2>&1

# Spaces Monitor — every 5 min
*/5 * * * * cd ~/protocol_pulse/video_pipeline_v3 && python3 utils/spaces_monitor.py >> logs/spaces_monitor.log 2>&1

# HeyGen Briefing Health Check — Daily at 2 PM EST (19 UTC)
0 19 * * * cd /home/ultron/protocol_pulse && export $(grep -v '^#' .env | xargs) && /usr/bin/python3 oracle_briefing/briefing_health_check.py >> /home/ultron/protocol_pulse/logs/heygen_briefing.log 2>&1

# ── End Protocol Pulse ──
CRON
)

# Get existing crontab, strip old Protocol Pulse block
EXISTING=$(crontab -l 2>/dev/null || true)

if echo "$EXISTING" | grep -q "$MARKER_START"; then
    # Remove old block between markers
    CLEANED=$(echo "$EXISTING" | sed "/${MARKER_START}/,/${MARKER_END}/d")
else
    CLEANED="$EXISTING"
fi

# Remove any standalone duplicate PP entries (from before markers were used)
CLEANED=$(echo "$CLEANED" | grep -v 'protocol_pulse' | grep -v 'Protocol Pulse' | grep -v 'pulse_check' || true)

# Preserve non-PP entries (like G'OLDS)
NON_PP=$(echo "$EXISTING" | grep -A999 "G.OLDS" || true)

# Combine: PP block + non-PP
NEW_CRON="${CRON_BLOCK}"
if [ -n "$NON_PP" ]; then
    NEW_CRON="${NEW_CRON}
${NON_PP}"
fi

# Install atomically
echo "$NEW_CRON" | crontab -

echo "Cron installed successfully. $(echo "$NEW_CRON" | grep -c '^\*\|^[0-9]') entries."
echo "Verify with: crontab -l"
