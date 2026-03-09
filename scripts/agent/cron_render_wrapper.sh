#!/usr/bin/env bash
# cron_render_wrapper.sh — checks GPU lock before firing
# Prepend to all cron render commands
LOCKFILE="/tmp/gpu_render.lock"
if [ -f "$LOCKFILE" ]; then
    OWNER=$(python3 -c "import json; print(json.load(open('$LOCKFILE')).get('owner','?'))" 2>/dev/null || echo "agent")
    echo "$(date): GPU locked by $OWNER — skipping cron render" >> ~/protocol_pulse/logs/cron_skip.log
    exit 0
fi
exec "$@"
