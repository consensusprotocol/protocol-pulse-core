#!/bin/bash
# Protocol Pulse Site Health Monitor
# Runs every 5 min via cron. Logs failures. Auto-restarts waitress if needed.
LOG="/home/ultron/protocol_pulse/logs/site_health.log"

FAILED=0
DETAILS=""

# Check BTC price (most visible — header ticker)
BTC=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000/api/btc-price 2>/dev/null)
if [ "$BTC" != "200" ]; then
    FAILED=$((FAILED+1))
    DETAILS="$DETAILS | btc-price=$BTC"
fi

# Check health
HEALTH=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000/health 2>/dev/null)
if [ "$HEALTH" != "200" ]; then
    FAILED=$((FAILED+1))
    DETAILS="$DETAILS | health=$HEALTH"
    # Auto-restart waitress if health endpoint is down
    echo "$(date) CRITICAL: Waitress down (health=$HEALTH) — auto-restarting" >> "$LOG"
    fuser -k 5000/tcp 2>/dev/null
    sleep 2
    cd /home/ultron/protocol_pulse/core
    nohup python3 -m waitress --port=5000 --threads=4 --channel-timeout=300 app:app >> /home/ultron/protocol_pulse/logs/waitress.log 2>&1 &
fi

# Check pro-metrics
PRO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000/api/pro-metrics 2>/dev/null)
if [ "$PRO" != "200" ]; then
    FAILED=$((FAILED+1))
    DETAILS="$DETAILS | pro-metrics=$PRO"
fi

# Check KOL sentiment
KOL=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:5000/api/kol/sentiment 2>/dev/null)
if [ "$KOL" != "200" ]; then
    FAILED=$((FAILED+1))
    DETAILS="$DETAILS | kol=$KOL"
fi

if [ $FAILED -gt 0 ]; then
    echo "$(date) FAIL ($FAILED endpoints) $DETAILS" >> "$LOG"
else
    # Only log healthy every hour (not every 5 min)
    MIN=$(date +%M)
    if [ "$MIN" -lt 5 ]; then
        echo "$(date) OK — all endpoints healthy" >> "$LOG"
    fi
fi
