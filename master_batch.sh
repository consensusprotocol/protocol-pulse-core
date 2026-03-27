#!/usr/bin/env bash
set -euo pipefail
LOG="/home/ultron/protocol_pulse/logs/master_batch_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1
echo "=== Master Batch — $(date -u) ==="

# ──────────────────────────────────────────────────────
# 1. Kill dead tmux sessions, keep only the sacred six
# ──────────────────────────────────────────────────────
KEEP="watchdog_llm|pipeline|pcaf_training|value_stream|sponsor_agent|satomi_orbital"
KILLED=0
while IFS= read -r sess; do
  if ! echo "$sess" | grep -qxE "$KEEP"; then
    tmux kill-session -t "$sess" 2>/dev/null && ((KILLED++)) || true
  fi
done < <(tmux list-sessions -F '#{session_name}' 2>/dev/null)
echo "[1/4] Killed $KILLED dead sessions. Survivors:"
tmux list-sessions -F '  #{session_name} (#{session_windows} windows)' 2>/dev/null

# ──────────────────────────────────────────────────────
# 2. Check value_stream + sponsor_agent pane state
# ──────────────────────────────────────────────────────
echo ""
echo "[2/4] Pane state check:"
for S in value_stream sponsor_agent; do
  LAST=$(tmux capture-pane -t "$S" -p 2>/dev/null | grep -v '^$' | tail -3)
  echo "  $S:"
  echo "$LAST" | sed 's/^/    /'
done

# ──────────────────────────────────────────────────────
# 3. Launch mempool_fix and kol_fix Claude Code sessions
# ──────────────────────────────────────────────────────
echo ""
echo "[3/4] Launching CC sessions..."

tmux new-session -d -s mempool_fix -x 220 -y 50
tmux send-keys -t mempool_fix "cd /home/ultron/protocol_pulse && claude --resume" Enter
echo "  mempool_fix: launched"

tmux new-session -d -s kol_fix -x 220 -y 50
tmux send-keys -t kol_fix "cd /home/ultron/protocol_pulse && claude --resume" Enter
echo "  kol_fix: launched"

# ──────────────────────────────────────────────────────
# 4. Fire render: daily_producer --reuse-content, GPU 0
# ──────────────────────────────────────────────────────
echo ""
echo "[4/4] Firing render (--reuse-content, GPU 0)..."
cd /home/ultron/protocol_pulse
CUDA_VISIBLE_DEVICES=0 nohup python3 -m video_pipeline_v3.daily_producer --reuse-content \
  >> "$LOG" 2>&1 &
RENDER_PID=$!
echo "  Render PID: $RENDER_PID"

echo ""
echo "=== Master Batch complete — $(date -u) ==="
echo "Render running in background (PID $RENDER_PID). Tail: tail -f $LOG"
