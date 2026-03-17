#!/bin/bash
# Avatar server watchdog - runs every 5 min via cron
LOG=/home/ultron/protocol_pulse/oracle/logs/watchdog.log
PID_FILE=/home/ultron/protocol_pulse/oracle/avatar_server.pid

# Check if server is responding
if ! curl -sf http://localhost:8200/health > /dev/null 2>&1; then
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
