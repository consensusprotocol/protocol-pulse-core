#!/bin/bash
# AUTOPILOT: Fire CC sessions autonomously on Ultron
# Usage: ./autopilot.sh SESSION_NAME "prompt text"
# Or:    ./autopilot.sh --status
# Or:    ./autopilot.sh --kill SESSION_NAME

if [ "$1" = "--status" ]; then
    echo "=== ACTIVE SESSIONS ==="
    tmux ls 2>/dev/null
    echo ""
    echo "=== GPU ==="
    nvidia-smi --query-gpu=index,utilization.gpu,memory.used --format=csv,noheader
    echo ""
    echo "=== RECENT COMMITS ==="
    git -C ~/protocol_pulse log --oneline -5
    exit 0
fi

if [ "$1" = "--kill" ]; then
    tmux kill-session -t "$2" 2>/dev/null && echo "Killed $2"
    exit 0
fi

SESSION=$1
PROMPT_FILE=$2

if [ -z "$SESSION" ] || [ -z "$PROMPT_FILE" ]; then
    echo "Usage: autopilot.sh SESSION_NAME /path/to/prompt.txt"
    exit 1
fi

# Kill existing session if stale
tmux kill-session -t "$SESSION" 2>/dev/null

# Boot fresh CC session in protocol_pulse dir
tmux new-session -d -s "$SESSION" -x 220 -y 50
tmux send-keys -t "$SESSION" "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter

echo "Waiting 70s for CC to boot in $SESSION..."
sleep 70

# Handle trust prompt
tmux send-keys -t "$SESSION" "1" Enter
sleep 3

# Fire the prompt
tmux load-buffer -t "$SESSION" "$PROMPT_FILE"
tmux paste-buffer -t "$SESSION"
tmux send-keys -t "$SESSION" "" Enter

echo "FIRED: $SESSION is running autonomously"
echo "Monitor: tmux attach -t $SESSION"
