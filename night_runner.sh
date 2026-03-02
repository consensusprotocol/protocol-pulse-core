#!/bin/bash
set -euo pipefail
LOG_DIR="$HOME/protocol_pulse/logs/night_runner"
PROMPT_DIR="$HOME/protocol_pulse/night_prompts"
WORK_DIR="$HOME/protocol_pulse"
SESSION_NAME="night_build"
CHECK_INTERVAL=60
MAX_WAIT=7200
mkdir -p "$LOG_DIR" "$PROMPT_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOG_DIR/night_run_${TIMESTAMP}.log"
TASKS=(
    "avatar_gpu_cache|PHASE2_01_AVATAR_GPU_CACHE.md"
    "pulse_check_v4|PHASE2_02_PULSE_CHECK_V4.md"
    "oracle_briefing|PHASE2_03_ORACLE_BRIEFING.md"
    "activate_systems|PHASE2_04_ACTIVATE_BACKFILL.md"
    "replit_deploy|PHASE2_05_REPLIT_DEPLOY.md"
)
log() { echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1" | tee -a "$MASTER_LOG"; }
wait_for_claude_ready() {
    local elapsed=0
    log "Waiting for Claude Code ready..."
    while [ $elapsed -lt 180 ]; do
        sleep 5; elapsed=$((elapsed + 5))
        if tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | grep -q "bypass permissions"; then
            log "Claude Code ready (${elapsed}s)"; return 0
        fi
        [ $((elapsed % 30)) -eq 0 ] && log "  ...still waiting (${elapsed}s)"
    done
    log "TIMEOUT waiting for Claude Code"; return 1
}
handle_plan_menu() {
    local pane=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null)
    if echo "$pane" | grep -q "Would you like to proceed"; then
        log "  Plan menu detected — auto-accepting..."
        tmux send-keys -t "$SESSION_NAME" "1" Enter
        sleep 5; return 0
    fi
    return 1
}
wait_for_task_completion() {
    local task_name="$1" elapsed=0
    log "Monitoring: $task_name (max $((MAX_WAIT/60))min)"
    while [ $elapsed -lt $MAX_WAIT ]; do
        sleep "$CHECK_INTERVAL"; elapsed=$((elapsed + CHECK_INTERVAL))
        handle_plan_menu || true
        local pane=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -15)
        if echo "$pane" | grep -q "bypass permissions"; then
            if ! echo "$pane" | grep -qiE "thinking|crunching|reading|writing|running|bash|creating|editing|searching|Churned|tokens|Would you like"; then
                sleep 30; elapsed=$((elapsed + 30))
                handle_plan_menu || true
                pane=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -15)
                if echo "$pane" | grep -q "bypass permissions" && ! echo "$pane" | grep -qiE "thinking|crunching|reading|writing|running|bash|creating|editing|searching|Churned|tokens|Would you like"; then
                    log "COMPLETED: $task_name (${elapsed}s)"
                    tmux capture-pane -t "$SESSION_NAME" -p -S -500 > "$LOG_DIR/${task_name}_output_${TIMESTAMP}.txt" 2>/dev/null
                    return 0
                fi
            fi
        fi
        [ $((elapsed % 300)) -eq 0 ] && log "  WORKING (${elapsed}s): $(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | grep -v '^$' | tail -1 | head -c 100)"
    done
    log "TIMEOUT: $task_name"; tmux capture-pane -t "$SESSION_NAME" -p -S -500 > "$LOG_DIR/${task_name}_timeout_${TIMESTAMP}.txt" 2>/dev/null; return 1
}
start_claude_session() {
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true; sleep 3
    tmux new-session -d -s "$SESSION_NAME"; sleep 1
    tmux send-keys -t "$SESSION_NAME" "cd $WORK_DIR && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
    log "Started tmux: $SESSION_NAME"; wait_for_claude_ready
}
send_prompt() {
    [ ! -f "$1" ] && { log "ERROR: $1 not found"; return 1; }
    tmux load-buffer "$1" \; paste-buffer -t "$SESSION_NAME"
    sleep 3; tmux send-keys -t "$SESSION_NAME" Enter
    log "Prompt sent ($(wc -c < "$1") bytes)"; sleep 10; return 0
}
git_checkpoint() {
    cd "$WORK_DIR"; git add -A 2>/dev/null || true
    local c=$(git diff --cached --stat 2>/dev/null | tail -1)
    [ -n "$c" ] && { git commit -m "phase2: $1 [auto]" 2>/dev/null || true; git push origin main 2>/dev/null || true; log "Git: $1 — $c"; } || log "Git: no changes"
}
log "==============================================================="
log "NIGHT RUNNER v3 PHASE 2 | Tasks: ${#TASKS[@]} | Plan auto-accept: ON"
log "==============================================================="
for i in "${!TASKS[@]}"; do IFS="|" read -r n f <<< "${TASKS[$i]}"; log "  $((i+1)). $n"; done
COMPLETED=0; FAILED=0; TOTAL=${#TASKS[@]}
for i in "${!TASKS[@]}"; do
    IFS="|" read -r task_name prompt_file <<< "${TASKS[$i]}"
    log "=== TASK $((i+1))/${TOTAL}: $task_name ==="
    if ! start_claude_session; then FAILED=$((FAILED+1)); continue; fi
    if ! send_prompt "$PROMPT_DIR/$prompt_file"; then FAILED=$((FAILED+1)); continue; fi
    if wait_for_task_completion "$task_name"; then COMPLETED=$((COMPLETED+1)); git_checkpoint "$task_name"
    else FAILED=$((FAILED+1)); git_checkpoint "${task_name}_partial"; fi
    sleep 10
done
log "==============================================================="
log "PHASE 2 COMPLETE: $COMPLETED/$TOTAL"
log "==============================================================="
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
cd "$WORK_DIR"; git add -A 2>/dev/null || true
git commit -m "phase2: batch ($COMPLETED/$TOTAL)" 2>/dev/null || true
git push origin main 2>/dev/null || true
log "Done."
