#!/bin/bash
# Oracle Avatar Session Chain Monitor — auto-launches sessions 2-5 after each commit
KEYWORDS=("SESSION 1" "SESSION 2" "SESSION 3" "SESSION 4")
SESSIONS=(2 3 4 5)
echo "[MONITOR] Started at $(date)"
for i in "${!SESSIONS[@]}"; do
  S="${SESSIONS[$i]}"
  KW="${KEYWORDS[$i]}"
  PROMPT="$HOME/protocol_pulse/oracle_live/sessions/session${S}_prompt.txt"
  NAME="cc_s${S}"
  echo "[MONITOR] Waiting for '$KW' commit..."
  while true; do
    git -C ~/protocol_pulse log --oneline -20 2>/dev/null | grep -q "$KW" && break
    sleep 30
  done
  echo "[MONITOR] '$KW' found — launching Session $S"
  tmux kill-session -t "$NAME" 2>/dev/null; sleep 2
  tmux new-session -d -s "$NAME" 'bash'; sleep 2
  PROMPT_TEXT=$(cat "$PROMPT")
  tmux send-keys -t "$NAME" "cd ~/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
  sleep 5
  tmux send-keys -t "$NAME" "$PROMPT_TEXT" Enter
  echo "[MONITOR] Session $S live in tmux $NAME"
  sleep 120
done
echo "[MONITOR] All sessions launched. Final log:"
git -C ~/protocol_pulse log --oneline -8
