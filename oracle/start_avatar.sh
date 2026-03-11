#!/bin/bash
# Oracle Avatar Server — auto-restart on crash
# Usage: tmux new-session -d -s avatar 'bash ~/protocol_pulse/oracle/start_avatar.sh'
# Crontab: @reboot tmux new-session -d -s avatar 'bash ~/protocol_pulse/oracle/start_avatar.sh'

while true; do
    echo "[$(date)] Starting avatar server..."
    cd ~/protocol_pulse/oracle && python3 avatar_server.py
    EXIT_CODE=$?
    echo "[$(date)] Avatar server exited with code $EXIT_CODE, restarting in 5s..."
    sleep 5
done
