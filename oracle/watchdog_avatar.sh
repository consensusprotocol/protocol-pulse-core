#!/bin/bash
# Avatar server watchdog - runs every 5 min via cron
LOG=/home/ultron/protocol_pulse/oracle/logs/watchdog.log
PID_FILE=/home/ultron/protocol_pulse/oracle/avatar_server.pid
STARTUP_GRACE=600  # 10 min grace for Chatterbox model loading on CUDA

# Check if server is responding
if ! curl -sf http://localhost:8200/health > /dev/null 2>&1; then
    # Grace period: if PID file exists and process is alive but young, skip restart
    if [ -f "$PID_FILE" ]; then
        AVATAR_PID=$(cat $PID_FILE)
        if kill -0 $AVATAR_PID 2>/dev/null; then
            # Process alive — check age
            PROC_START=$(stat -c %Y /proc/$AVATAR_PID 2>/dev/null || echo 0)
            NOW=$(date +%s)
            AGE=$(( NOW - PROC_START ))
            if [ "$AGE" -lt "$STARTUP_GRACE" ]; then
                echo "[$(date)] Avatar starting (${AGE}s old, grace ${STARTUP_GRACE}s) — skipping restart" >> $LOG
                exit 0
            fi
        fi
    fi
    echo "[$(date)] Avatar server DOWN - restarting" >> $LOG
    # Kill any stale process
    if [ -f "$PID_FILE" ]; then
        kill $(cat $PID_FILE) 2>/dev/null || true
        sleep 2
    fi
    pkill -f "python3 avatar_server.py" 2>/dev/null || true
    sleep 3
    # Restart
    cd /home/ultron/protocol_pulse/oracle
    nohup python3 avatar_server.py >> $LOG 2>&1 &
    echo $! > $PID_FILE
    echo "[$(date)] Restart issued, PID: $!" >> $LOG
else
    echo "[$(date)] Avatar OK ($(curl -sf http://localhost:8200/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'uptime={d.get(chr(117)+chr(112)+chr(116)+chr(105)+chr(109)+chr(101)+chr(95)+chr(115)+chr(101)+chr(99),0):.0f}s')" 2>/dev/null))" >> $LOG
fi
