#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# PROTOCOL PULSE — AUTONOMOUS BUILD PIPELINE ORCHESTRATOR
# Chains CC sessions sequentially. Each waits for the previous
# to commit before firing the next. All inside this tmux session.
# ═══════════════════════════════════════════════════════════════

set -e
cd /home/ultron/protocol_pulse

LOG="logs/pipeline_orchestrator.log"
mkdir -p logs

log() { echo "[$(date '+%H:%M ET')] $1" | tee -a "$LOG"; }

wait_for_commit() {
  local KEYWORD="$1"
  local TIMEOUT="${2:-7200}"  # 2h default
  local START=$(date +%s)
  log "Waiting for commit matching: $KEYWORD"
  while true; do
    if git log --oneline -5 | grep -qi "$KEYWORD"; then
      log "✅ Commit detected: $(git log --oneline -1)"
      return 0
    fi
    local NOW=$(date +%s)
    if (( NOW - START > TIMEOUT )); then
      log "⚠️  Timeout waiting for: $KEYWORD — continuing anyway"
      return 1
    fi
    sleep 30
    git fetch origin main --quiet 2>/dev/null || true
    git pull --ff-only --quiet 2>/dev/null || true
  done
}

run_cc_session() {
  local SESSION_NAME="$1"
  local PROMPT_FILE="$2"
  local DIRECTIVE="$3"

  log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  log "STARTING: $SESSION_NAME"
  log "Prompt: $PROMPT_FILE"
  log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  # Kill any existing session with this name
  tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true
  sleep 1

  # Start CC in new tmux window (nested in current tmux session)
  tmux new-window -n "$SESSION_NAME" "cd /home/ultron/protocol_pulse && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions"
  sleep 8

  # Send the prompt
  tmux send-keys -t "$SESSION_NAME" "$DIRECTIVE" Enter
  log "Prompt sent to $SESSION_NAME — CC is running"
}

# ─────────────────────────────────────────────────────────────
log "PIPELINE STARTING — Sessions S2 (Onboarding) + S3 (Landing)"
log "Session 1 (UI Redesign) already committed: $(git log --oneline -1)"

# ─────────────────────────────────────────────────────────────
# SESSION 2 — Onboarding + Stripe
# ─────────────────────────────────────────────────────────────
run_cc_session "s2_onboarding" \
  "docs/cc_session2_onboarding.md" \
  "Read docs/cc_session2_onboarding.md then execute every step. Audit first — GPT-4o and Grok on all 6 onboarding questions. No confirmation. Go."

# Wait for S2 commit
wait_for_commit "onboarding\|join page\|stripe\|demo mode" 7200
log "SESSION 2 COMPLETE ✅"

sleep 10

# ─────────────────────────────────────────────────────────────
# SESSION 3 — Landing Page
# ─────────────────────────────────────────────────────────────
run_cc_session "s3_landing" \
  "docs/cc_session3_landing.md" \
  "Read docs/cc_session3_landing.md then execute every step. Audit first — GPT-4o and Grok on all 5 landing page questions. No confirmation. Go."

# Wait for S3 commit
wait_for_commit "landing\|intelligence-terminal\|demo panel\|OG meta" 7200
log "SESSION 3 COMPLETE ✅"

# ─────────────────────────────────────────────────────────────
log ""
log "════════════════════════════════════════"
log "ALL SESSIONS COMPLETE"
log "Recent commits:"
git log --oneline -5 | tee -a "$LOG"
log ""
log "Live pages:"
log "  https://protocolpulse.io/intelligence"
log "  https://protocolpulse.io/intelligence/scenarios"
log "  https://protocolpulse.io/intelligence/alerts"
log "  https://protocolpulse.io/join"
log "  https://protocolpulse.io/intelligence-terminal"
log "════════════════════════════════════════"
