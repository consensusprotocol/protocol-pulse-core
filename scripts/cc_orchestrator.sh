#!/bin/bash
# Protocol Pulse CC Session Orchestrator
# Fires 5 CC sessions sequentially, waiting for each to complete

SESSIONS=(
    "/tmp/cc_session_1_pronunciation.md:ElevenLabs Pronunciation Dictionary"
    "/tmp/cc_session_2_uptime_monitor.md:UptimeRobot Free Monitoring"
    "/tmp/cc_session_3_pm2.md:PM2 Process Manager"
    "/tmp/cc_session_4_batch_api.md:Anthropic Batch API"
    "/tmp/cc_session_5_cf_workers.md:Cloudflare Workers Cache"
)

LOG="/home/ultron/protocol_pulse/logs/cc_orchestrator.log"
TMUX_SESSION="cc_bugs"

echo "$(date) — CC Session Orchestrator starting (5 sessions)" >> "$LOG"

# Session 1 is already running. Start monitoring from session 2.
for i in "${!SESSIONS[@]}"; do
    IFS=':' read -r prompt_file session_name <<< "${SESSIONS[$i]}"
    
    if [ "$i" -eq 0 ]; then
        echo "$(date) — Session 1 ($session_name) already running, monitoring..." >> "$LOG"
    else
        echo "$(date) — Waiting for previous session to complete..." >> "$LOG"
    fi
    
    # Wait for CC to return to prompt (❯ symbol visible, no "thinking" or "working")
    while true; do
        # Check if CC is at the prompt (idle)
        PANE=$(tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null | tail -5)
        if echo "$PANE" | grep -q "^❯"; then
            # CC is at prompt — previous session done
            if [ "$i" -gt 0 ]; then
                echo "$(date) — Firing Session $((i+1)): $session_name" >> "$LOG"
                tmux load-buffer "$prompt_file"
                tmux paste-buffer -t "$TMUX_SESSION"
                sleep 2
                tmux send-keys -t "$TMUX_SESSION" Enter
            fi
            break
        fi
        sleep 30
    done
    
    # Wait for this session to start working
    sleep 15
    echo "$(date) — Session $((i+1)) ($session_name) is working..." >> "$LOG"
done

# Wait for final session to complete
while true; do
    PANE=$(tmux capture-pane -t "$TMUX_SESSION" -p 2>/dev/null | tail -5)
    if echo "$PANE" | grep -q "^❯"; then
        break
    fi
    sleep 30
done

echo "$(date) — ALL 5 SESSIONS COMPLETE" >> "$LOG"
echo "$(date) — Check git log for commits:" >> "$LOG"
cd /home/ultron/protocol_pulse && git log --oneline -5 >> "$LOG"
