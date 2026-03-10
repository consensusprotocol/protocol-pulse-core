#!/bin/bash
# PROTOCOL PULSE — PHASE 3 PARALLEL FEATURE LAUNCHER
# Launches 7 Claude Code sessions, each in its own tmux window, each feature
# in its own git worktree. Every session runs Phase 0 LLM council FIRST,
# then builds, audits, and commits autonomously.
# Usage: bash launch_p3_features.sh [feature-name ...] or no args = all 7
# Generated: 2026-03-09

set -euo pipefail

BASE_DIR=/home/ultron/protocol_pulse
GOSPELS_DIR=$BASE_DIR/docs/gospels
WORKTREES_DIR=/home/ultron/worktrees
LOG_DIR=$BASE_DIR/logs/p3_builds
AUDIT_ENGINE=$BASE_DIR/utils/cross_llm_audit.py

mkdir -p "$WORKTREES_DIR" "$LOG_DIR" "$BASE_DIR/docs/audits"

# Load .env for ANTHROPIC_API_KEY
source "$BASE_DIR/.env" 2>/dev/null || true

# Phase 3 features: name|branch|gospel
P3_FEATURES=(
  "p3-media-unified|feature/p3-media-unified|P3_MEDIA_UNIFIED_GOSPEL.md"
  "p3-sponsor-agent|feature/p3-sponsor-agent|P3_SPONSOR_AGENT_GOSPEL.md"
  "p3-mining-intel|feature/p3-mining-intel|P3_MINING_INTEL_GOSPEL.md"
  "p3-premium-stripe|feature/p3-premium-stripe|P3_PREMIUM_STRIPE_GOSPEL.md"
  "p3-charts|feature/p3-charts|P3_CHARTS_GOSPEL.md"
  "p3-sentiment-intel|feature/p3-sentiment-intel|P3_SENTIMENT_INTEL_GOSPEL.md"
  "p3-affiliates|feature/p3-affiliates|P3_AFFILIATES_GOSPEL.md"
)

launch_p3_feature() {
  local FEATURE="$1" BRANCH="$2" GOSPEL="$3"
  local WORKTREE="$WORKTREES_DIR/$FEATURE"
  local SESSION="build_${FEATURE}"
  local LOG="$LOG_DIR/${FEATURE}.log"
  local PROMPT_FILE="/tmp/cc_p3_${FEATURE}.txt"

  echo ""
  echo "════════════════════════════════════════════════════════════════"
  echo " LAUNCHING: $FEATURE"
  echo " Branch:    $BRANCH"
  echo " Worktree:  $WORKTREE"
  echo " Session:   $SESSION"
  echo "════════════════════════════════════════════════════════════════"

  # Kill existing session if present
  tmux kill-session -t "$SESSION" 2>/dev/null || true

  # Setup git worktree
  cd "$BASE_DIR"
  git fetch origin 2>/dev/null || true
  if [ ! -d "$WORKTREE" ]; then
    git worktree add "$WORKTREE" -b "$BRANCH" 2>/dev/null \
      || git worktree add "$WORKTREE" "$BRANCH" 2>/dev/null \
      || { echo "  [WARN] Worktree already exists — using existing"; }
  fi

  # Copy gospel + law files into worktree
  cp "$GOSPELS_DIR/$GOSPEL" "$WORKTREE/GOSPEL.md"
  cp "$BASE_DIR/CROSS_LLM_AUDIT_LAW.md" "$WORKTREE/" 2>/dev/null || true
  cp "$BASE_DIR/VISUAL_DESIGN_SYSTEM.md" "$WORKTREE/" 2>/dev/null || true
  cp "$BASE_DIR/PROTOCOL_PULSE_HANDOFF.md" "$WORKTREE/" 2>/dev/null || true

  # Write the CC prompt with feature-specific substitutions
  sed -e "s|{NAME}|$FEATURE|g" \
      -e "s|{BRANCH}|$BRANCH|g" \
      -e "s|{WORKTREE}|$WORKTREE|g" \
      /tmp/cc_p3_master_prompt_template.txt > "$PROMPT_FILE"

  # Start tmux session + launch Claude Code
  tmux new-session -d -s "$SESSION" -x 220 -y 50

  # Setup environment in session
  tmux send-keys -t "$SESSION" "export ANTHROPIC_API_KEY=\"$ANTHROPIC_API_KEY\"" Enter
  sleep 0.3
  tmux send-keys -t "$SESSION" "cd \"$WORKTREE\"" Enter
  sleep 0.3

  # Launch Claude Code with the prompt file piped in
  tmux send-keys -t "$SESSION" \
    "unset ANTHROPIC_API_KEY && ANTHROPIC_API_KEY=\"$ANTHROPIC_API_KEY\" claude --dangerously-skip-permissions < \"$PROMPT_FILE\" 2>&1 | tee \"$LOG\"" \
    Enter

  echo "  ✓ Session '$SESSION' launched"
  echo "  ✓ Log: $LOG"
  echo "  ✓ Monitor: tmux attach -t $SESSION"
}

# Determine which features to launch
if [ $# -gt 0 ]; then
  TARGETS=("$@")
else
  TARGETS=()
  for entry in "${P3_FEATURES[@]}"; do
    IFS='|' read -r name _ _ <<< "$entry"
    TARGETS+=("$name")
  done
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   PROTOCOL PULSE — PHASE 3 PARALLEL FEATURE LAUNCHER        ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║   Each session: Phase0 LLM Council → Build → Audit → Push   ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Launching ${#TARGETS[@]} feature build(s)..."
echo ""

LAUNCHED=0
for entry in "${P3_FEATURES[@]}"; do
  IFS='|' read -r name branch gospel <<< "$entry"
  for target in "${TARGETS[@]}"; do
    if [ "$name" = "$target" ]; then
      launch_p3_feature "$name" "$branch" "$gospel"
      LAUNCHED=$((LAUNCHED + 1))
      sleep 3   # stagger launches to avoid simultaneous git operations
      break
    fi
  done
done

echo ""
echo "════════════════════════════════════════════════════════════════"
echo " $LAUNCHED SESSIONS LAUNCHED"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Monitor all sessions:"
echo "  tmux ls"
echo ""
echo "Attach to specific session:"
for entry in "${P3_FEATURES[@]}"; do
  IFS='|' read -r name _ _ <<< "$entry"
  for target in "${TARGETS[@]}"; do
    if [ "$name" = "$target" ]; then
      echo "  tmux attach -t build_${name}"
    fi
  done
done
echo ""
echo "Watch all logs live:"
echo "  tail -f $LOG_DIR/p3-*.log"
echo ""
echo "Check completion:"
echo "  ls $WORKTREES_DIR/p3-*/BUILD_COMPLETE.md 2>/dev/null && echo DONE || echo IN PROGRESS"
echo ""
