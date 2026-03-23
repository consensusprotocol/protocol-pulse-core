#!/bin/bash
# Auto-start on boot — Protocol Pulse critical services
sleep 30  # wait for network

# Start render loop
cd /home/ultron/protocol_pulse
tmux new-session -d -s render_main 2>/dev/null || true
tmux send-keys -t render_main "cd ~/protocol_pulse && python3 overnight_render_loop.py --daemon" Enter

# Watchdog is handled by cron (*/1 * * * *) — no explicit start needed
echo "Protocol Pulse boot startup complete at $(date)" >> /home/ultron/protocol_pulse/logs/boot_startup.log
