#!/bin/bash
# Avatar server watchdog — checks health, restarts if down
# Cron: */2 * * * * /bin/bash /home/ultron/protocol_pulse/scripts/avatar_watchdog.sh >> /home/ultron/protocol_pulse/logs/avatar_watchdog.log 2>&1

HEALTH_URL="http://localhost:8200/health"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
    echo "$LOG_PREFIX avatar_server healthy"
    exit 0
fi

echo "$LOG_PREFIX avatar_server DOWN — restarting..."

# Kill any lingering processes
kill -9 $(pgrep -f avatar_server.py) 2>/dev/null || true
sleep 3

# Restart
cd /home/ultron/protocol_pulse/oracle && nohup python3 avatar_server.py >> /home/ultron/protocol_pulse/logs/avatar_server.log 2>&1 &
NEW_PID=$!
echo $NEW_PID > /home/ultron/protocol_pulse/avatar_server.pid
echo "$LOG_PREFIX avatar_server restarted PID=$NEW_PID"
