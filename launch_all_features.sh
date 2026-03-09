#!/bin/bash
# PROTOCOL PULSE — PARALLEL FEATURE BUILD LAUNCHER
# Fires 10 simultaneous Claude Code sessions, one per feature branch
# Each session reads its gospel doc and builds autonomously
# Usage: bash launch_all_features.sh [feature1 feature2 ...] or no args = all
# Created: 2026-03-09

set -e
BASE_DIR=~/protocol_pulse
GOSPELS_DIR=$BASE_DIR/docs/gospels
WORKTREES_DIR=~/worktrees
LOG_DIR=$BASE_DIR/logs/feature_builds

mkdir -p $WORKTREES_DIR $LOG_DIR

# Feature definitions: name|branch|gospel|gpu_needed
FEATURES=(
  "f1-avatar-oracle|feature/f1-avatar-oracle|F1_AVATAR_ORACLE_GOSPEL.md|yes"
  "f2-briefing-room|feature/f2-briefing-room|F2_BRIEFING_ROOM_GOSPEL.md|no"
  "f3-schiff-bot|feature/f3-schiff-bot|F3_SCHIFF_BOT_GOSPEL.md|no"
  "f4-nostr|feature/f4-nostr|F4_NOSTR_GOSPEL.md|no"
  "f5-node-watch|feature/f5-node-watch|F5_NODE_WATCH_GOSPEL.md|no"
  "f6-marketing-os|feature/f6-marketing-os|F6_MARKETING_OS_GOSPEL.md|no"
  "v30-terminal-api|feature/v30-terminal-api|V30_TERMINAL_API_GOSPEL.md|no"
  "b1-newsletter|feature/b1-newsletter|B1_NEWSLETTER_GOSPEL.md|no"
  "v22-multi-format|feature/v22-multi-format|V22_MULTI_FORMAT_GOSPEL.md|no"
)

# NOTE: VIDEO_AUDIO_FIX is excluded from auto-launch — needs PBX forensic notes first

launch_feature() {
  local NAME=$1
  local BRANCH=$2
  local GOSPEL=$3
  local GPU_NEEDED=$4
  local WORKTREE=$WORKTREES_DIR/$NAME
  local LOG=$LOG_DIR/${NAME}.log

  echo "=== LAUNCHING $NAME ==="

  # Create git worktree (isolated checkout on its own branch)
  if [ ! -d "$WORKTREE" ]; then
    cd $BASE_DIR
    git worktree add $WORKTREE -b $BRANCH 2>/dev/null || git worktree add $WORKTREE $BRANCH
    echo "  worktree created: $WORKTREE"
  else
    echo "  worktree exists: $WORKTREE"
  fi

  # Copy gospel to worktree for easy access
  cp $GOSPELS_DIR/$GOSPEL $WORKTREE/GOSPEL.md

  # Build the opening prompt for this session
  PROMPT="Read $WORKTREE/GOSPEL.md in full — this is your complete spec.
You are building feature branch: $BRANCH
Worktree: $WORKTREE
Base repo: $BASE_DIR

RULES FOR THIS SESSION:
1. This is a dedicated worktree — you cannot affect other features
2. All DB migrations use alembic or direct SQL in a migration script
3. Run bash $BASE_DIR/regression_test.sh at the end — zero FAILs required
4. git add -A && git commit -m 'feat($NAME): [description]' when done
5. git push origin $BRANCH when done — do NOT merge to main
6. Log all decisions to $LOG

START: Read GOSPEL.md now, then execute the BUILD section step by step."

  # Write prompt to file for tmux injection
  echo "$PROMPT" > /tmp/prompt_${NAME}.txt

  # Launch tmux session
  tmux new-session -d -s "build_${NAME}" \
    "cd $WORKTREE && unset ANTHROPIC_API_KEY && claude --dangerously-skip-permissions 2>&1 | tee $LOG"

  # Give Claude Code 3 seconds to start, then send the prompt
  sleep 3
  tmux send-keys -t "build_${NAME}" "$(cat /tmp/prompt_${NAME}.txt)" Enter

  echo "  session: build_${NAME} | log: $LOG"
  echo ""
}

# Determine which features to launch
if [ $# -gt 0 ]; then
  TARGETS=("$@")
else
  # Launch all (skip video-audio-fix — needs PBX notes)
  TARGETS=()
  for feature in "${FEATURES[@]}"; do
    NAME=$(echo $feature | cut -d'|' -f1)
    TARGETS+=($NAME)
  done
fi

echo "================================================"
echo "PROTOCOL PULSE PARALLEL BUILD LAUNCHER"
echo "Launching ${#TARGETS[@]} feature sessions"
echo "================================================"
echo ""

# First: ensure main is up to date
cd $BASE_DIR && git pull origin main 2>/dev/null || true

# Launch each feature
for feature in "${FEATURES[@]}"; do
  NAME=$(echo $feature | cut -d'|' -f1)
  BRANCH=$(echo $feature | cut -d'|' -f2)
  GOSPEL=$(echo $feature | cut -d'|' -f3)
  GPU=$(echo $feature | cut -d'|' -f4)

  # Check if this feature is in targets
  for target in "${TARGETS[@]}"; do
    if [ "$target" == "$NAME" ]; then
      launch_feature $NAME $BRANCH $GOSPEL $GPU
      sleep 5  # 5s stagger between launches (API rate limit buffer)
      break
    fi
  done
done

echo "================================================"
echo "ALL SESSIONS LAUNCHED"
echo ""
echo "Monitor all sessions:"
echo "  tmux ls | grep build_"
echo ""
echo "Attach to specific session:"
echo "  tmux attach -t build_f1-avatar-oracle"
echo ""
echo "Watch all logs:"
echo "  tail -f $LOG_DIR/*.log"
echo ""
echo "Check completion (git branches with commits):"
echo "  git branch -a | grep feature/"
echo "  git log --oneline --all --graph | head -30"
echo "================================================"
