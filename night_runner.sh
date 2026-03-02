#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PROTOCOL PULSE — NIGHT RUNNER
# Chains Claude Code tasks sequentially on Ultron
# Each task gets full attention — no rushing, no skipping
# ═══════════════════════════════════════════════════════════════

set -euo pipefail

LOG_DIR="$HOME/protocol_pulse/logs/night_runner"
PROMPT_DIR="$HOME/protocol_pulse/night_prompts"
WORK_DIR="$HOME/protocol_pulse"
SESSION_NAME="night_build"
CHECK_INTERVAL=60  # seconds between completion checks
MAX_WAIT=7200      # max seconds per task (2 hours)

mkdir -p "$LOG_DIR" "$PROMPT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MASTER_LOG="$LOG_DIR/night_run_${TIMESTAMP}.log"

# ─── Task Queue ───────────────────────────────────────────────
# Order matters. Each task runs AFTER the previous one completes.
# Format: "task_name|prompt_file"
TASKS=(
    "avatar_upgrade|CLAUDE_CODE_AVATAR_UPGRADE.md"
    "pulse_check_v4|CLAUDE_CODE_PULSE_CHECK_V4.md"
    "oracle_briefing|CLAUDE_CODE_ORACLE_BRIEFING.md"
    "xspaces_scraper|CLAUDE_CODE_XSPACES_SCRAPER.md"
    "image_backfill|CLAUDE_CODE_IMAGE_BACKFILL.md"
    "mining_intel|CLAUDE_CODE_MINING_INTEL.md"
)

# ─── Functions ────────────────────────────────────────────────

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$MASTER_LOG"
}

wait_for_claude_ready() {
    # Wait for Claude Code to show its prompt (ready to receive input)
    local max_wait=120
    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        local pane_content
        pane_content=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -5)
        if echo "$pane_content" | grep -q "❯\|bypass permissions"; then
            return 0
        fi
        sleep 3
        elapsed=$((elapsed + 3))
    done
    log "WARNING: Claude Code didn't show ready prompt after ${max_wait}s"
    return 1
}

wait_for_task_completion() {
    local task_name="$1"
    local elapsed=0
    local last_activity=$(date +%s)
    
    log "Monitoring task: $task_name (max ${MAX_WAIT}s)"
    
    while [ $elapsed -lt $MAX_WAIT ]; do
        sleep "$CHECK_INTERVAL"
        elapsed=$((elapsed + CHECK_INTERVAL))
        
        # Capture the last 10 lines of the tmux pane
        local pane_content
        pane_content=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -10)
        
        # Check if Claude Code is at idle prompt (task finished)
        # Claude Code shows "❯" when waiting for input after completing work
        # But it also shows "❯" during work with "thinking" or "Crunching"
        # The key: idle prompt has ❯ with NO "thinking", "Crunching", "Reading", "Writing" above it
        
        local is_idle=false
        if echo "$pane_content" | grep -q "❯"; then
            # Check it's truly idle — no activity indicators
            if ! echo "$pane_content" | grep -qiE "thinking|crunching|reading|writing|running|bash|creating|editing|searching|envisioning"; then
                # Double-check: wait 30 more seconds and check again
                sleep 30
                pane_content=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | tail -10)
                if echo "$pane_content" | grep -q "❯" && ! echo "$pane_content" | grep -qiE "thinking|crunching|reading|writing|running|bash|creating|editing|searching|envisioning"; then
                    is_idle=true
                fi
            fi
        fi
        
        if $is_idle; then
            log "✅ Task '$task_name' COMPLETED after ${elapsed}s"
            
            # Capture full session output for the log
            tmux capture-pane -t "$SESSION_NAME" -p -S -500 > "$LOG_DIR/${task_name}_output_${TIMESTAMP}.txt" 2>/dev/null
            log "Session output saved to ${task_name}_output_${TIMESTAMP}.txt"
            return 0
        fi
        
        # Progress update every 5 minutes
        if [ $((elapsed % 300)) -eq 0 ]; then
            local last_line
            last_line=$(tmux capture-pane -t "$SESSION_NAME" -p 2>/dev/null | grep -v "^$" | tail -1)
            log "⏳ Task '$task_name' still running (${elapsed}s elapsed). Last: ${last_line:0:80}"
        fi
    done
    
    log "⚠️ Task '$task_name' TIMED OUT after ${MAX_WAIT}s"
    tmux capture-pane -t "$SESSION_NAME" -p -S -500 > "$LOG_DIR/${task_name}_timeout_${TIMESTAMP}.txt" 2>/dev/null
    return 1
}

start_claude_session() {
    # Kill any existing session
    tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
    sleep 2
    
    # Start fresh tmux session with Claude Code
    tmux new-session -d -s "$SESSION_NAME" \; send-keys "cd $WORK_DIR && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions" Enter
    
    log "Started Claude Code session: $SESSION_NAME"
    
    # Wait for Claude to be ready
    if ! wait_for_claude_ready; then
        log "ERROR: Claude Code failed to start"
        return 1
    fi
    
    log "Claude Code is ready"
    return 0
}

send_prompt() {
    local prompt_file="$1"
    
    if [ ! -f "$prompt_file" ]; then
        log "ERROR: Prompt file not found: $prompt_file"
        return 1
    fi
    
    # Use tmux load-buffer + paste to send large prompts
    # This handles prompts of any size without character limits
    tmux load-buffer "$prompt_file" \; paste-buffer -t "$SESSION_NAME"
    sleep 2
    # Send Enter to submit
    tmux send-keys -t "$SESSION_NAME" Enter
    
    log "Prompt sent from: $prompt_file"
    return 0
}

git_checkpoint() {
    local task_name="$1"
    cd "$WORK_DIR"
    
    # Stage and commit any changes
    git add -A 2>/dev/null || true
    local changes
    changes=$(git diff --cached --stat 2>/dev/null | tail -1)
    
    if [ -n "$changes" ]; then
        git commit -m "night-runner: $task_name completed [auto]" 2>/dev/null || true
        git push origin main 2>/dev/null || true
        log "Git checkpoint: $task_name — $changes"
    else
        log "Git checkpoint: $task_name — no new changes"
    fi
}

# ─── Main Execution ───────────────────────────────────────────

log "═══════════════════════════════════════════════════════════"
log "NIGHT RUNNER STARTED"
log "Tasks queued: ${#TASKS[@]}"
log "Max time per task: ${MAX_WAIT}s"
log "═══════════════════════════════════════════════════════════"

# Print task list
for i in "${!TASKS[@]}"; do
    IFS='|' read -r name file <<< "${TASKS[$i]}"
    log "  $((i+1)). $name ($file)"
done
log ""

COMPLETED=0
FAILED=0
TOTAL=${#TASKS[@]}

for i in "${!TASKS[@]}"; do
    IFS='|' read -r task_name prompt_file <<< "${TASKS[$i]}"
    
    log "───────────────────────────────────────────────────────"
    log "TASK $((i+1))/${TOTAL}: $task_name"
    log "Prompt: $prompt_file"
    log "───────────────────────────────────────────────────────"
    
    # Start a fresh Claude Code session for each task
    if ! start_claude_session; then
        log "❌ Failed to start Claude Code for: $task_name"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Send the prompt
    if ! send_prompt "$PROMPT_DIR/$prompt_file"; then
        log "❌ Failed to send prompt for: $task_name"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    # Wait for task to complete
    if wait_for_task_completion "$task_name"; then
        COMPLETED=$((COMPLETED + 1))
        
        # Git checkpoint after each successful task
        git_checkpoint "$task_name"
    else
        FAILED=$((FAILED + 1))
        log "Moving to next task despite failure/timeout"
        
        # Still try to save progress
        git_checkpoint "${task_name}_partial"
    fi
    
    # Brief pause between tasks
    sleep 10
done

# ─── Final Report ─────────────────────────────────────────────

log ""
log "═══════════════════════════════════════════════════════════"
log "NIGHT RUNNER COMPLETE"
log "═══════════════════════════════════════════════════════════"
log "  Completed: $COMPLETED/$TOTAL"
log "  Failed:    $FAILED/$TOTAL"
log "  Log:       $MASTER_LOG"
log "  Outputs:   $LOG_DIR/"
log "═══════════════════════════════════════════════════════════"

# Kill the final tmux session
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Final git push
cd "$WORK_DIR"
git add -A 2>/dev/null || true
git commit -m "night-runner: batch complete ($COMPLETED/$TOTAL tasks)" 2>/dev/null || true
git push origin main 2>/dev/null || true

log "All done. Good night. 🌙"
