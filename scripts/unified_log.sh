#!/bin/bash
# Protocol Pulse Unified Log Viewer
# Usage: ./unified_log.sh [follow]

LOGS=(
    ~/protocol_pulse/logs/waitress.log
    ~/protocol_pulse/logs/tweet_machine_cron.log
    ~/protocol_pulse/logs/morning_brief_cron.log
    ~/protocol_pulse/logs/sovereign_context.log
    ~/protocol_pulse/logs/transcript_intel.log
    ~/protocol_pulse/logs/nitter_scraper.log
    ~/protocol_pulse/logs/social_daemon.log
    ~/protocol_pulse/logs/convergence_cycle.log
    /tmp/v5_render.log
)

if [ "$1" = "follow" ] || [ "$1" = "-f" ]; then
    tail -f ${LOGS[@]} 2>/dev/null
else
    echo "=== PROTOCOL PULSE LOG SUMMARY ==="
    echo "Generated: $(date)"
    echo ""
    for log in "${LOGS[@]}"; do
        if [ -f "$log" ]; then
            name=$(basename $log)
            last=$(tail -1 "$log" 2>/dev/null | head -c 100)
            age_min=$(( ($(date +%s) - $(stat -c %Y "$log")) / 60 ))
            echo "[$name] (${age_min}m ago) $last"
        fi
    done
fi
