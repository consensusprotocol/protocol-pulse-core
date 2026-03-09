#!/bin/bash
# PROTOCOL PULSE — PARALLEL FEATURE BUILD + AUDIT LAUNCHER
# Flow: Build code -> 2-cycle LLM audit -> second pass -> PR-ready
# Usage: bash launch_all_features.sh [f1-avatar-oracle f5-node-watch ...] or no args = all

set -e
BASE_DIR=~/protocol_pulse
GOSPELS_DIR=$BASE_DIR/docs/gospels
WORKTREES_DIR=~/worktrees
LOG_DIR=$BASE_DIR/logs/feature_builds
AUDIT_ENGINE=$BASE_DIR/utils/cross_llm_audit.py

mkdir -p $WORKTREES_DIR $LOG_DIR $BASE_DIR/docs/audits

FEATURES=(
  "f1-avatar-oracle|feature/f1-avatar-oracle|F1_AVATAR_ORACLE_GOSPEL.md|y"
  "f2-briefing-room|feature/f2-briefing-room|F2_BRIEFING_ROOM_GOSPEL.md|y"
  "f3-schiff-bot|feature/f3-schiff-bot|F3_SCHIFF_BOT_GOSPEL.md|n"
  "f4-nostr|feature/f4-nostr|F4_NOSTR_GOSPEL.md|n"
  "f5-node-watch|feature/f5-node-watch|F5_NODE_WATCH_GOSPEL.md|n"
  "f6-marketing-os|feature/f6-marketing-os|F6_MARKETING_OS_GOSPEL.md|n"
  "v30-terminal-api|feature/v30-terminal-api|V30_TERMINAL_API_GOSPEL.md|y"
  "b1-newsletter|feature/b1-newsletter|B1_NEWSLETTER_GOSPEL.md|n"
  "v22-multi-format|feature/v22-multi-format|V22_MULTI_FORMAT_GOSPEL.md|y"
)

launch_feature() {
  local NAME=$1 BRANCH=$2 GOSPEL=$3 HIGH_STAKES=$4
  local WORKTREE=$WORKTREES_DIR/$NAME
  local LOG=$LOG_DIR/${NAME}.log

  echo ""; echo "=== LAUNCHING: $NAME ===" ; echo "  branch: $BRANCH  log: $LOG"

  cd $BASE_DIR
  if [ ! -d "$WORKTREE" ]; then
    git worktree add $WORKTREE -b $BRANCH 2>/dev/null || git worktree add $WORKTREE $BRANCH
  fi

  cp $GOSPELS_DIR/$GOSPEL $WORKTREE/GOSPEL.md
  cp $GOSPELS_DIR/POST_BUILD_AUDIT_PROTOCOL.md $WORKTREE/AUDIT_PROTOCOL.md 2>/dev/null || true

  # Write the prompt to a file
  cat > /tmp/cc_prompt_${NAME}.txt << PROMPT_EOF
Read $WORKTREE/GOSPEL.md IN FULL before writing a single line of code.
This is your complete specification. Every law in it is inviolable.

You are building feature: $NAME
Branch: $BRANCH | Worktree: $WORKTREE | Base repo: $BASE_DIR

PHASE 1 - BUILD:
Execute the BUILD section of GOSPEL.md step by step.
Build complete frontend AND backend. World-class quality, not a prototype.
Every route: try/except. Every API call: timeout + fallback. Every DB write: rollback.
Every async frontend op: loading/error/empty states all handled.
Every ORDER BY / WHERE column: indexed.
CSS animations only - no Three.js, no WebGL.

When complete:
1. cd $BASE_DIR && bash regression_test.sh -- fix until zero FAILs
2. git add -A && git commit -m "feat($NAME): initial build"
3. git push origin $BRANCH

PHASE 2 - LLM AUDIT (fires automatically after build):
python3 $BASE_DIR/utils/cross_llm_audit.py --feature $NAME
This fires 2-cycle audit with Gemini+OpenAI+Grok, writes FINAL_CONSENSUS.md.
Wait for it to complete -- it will print AUDIT COMPLETE when done.

PHASE 3 - SECOND PASS:
Read $BASE_DIR/docs/audits/$NAME/FINAL_CONSENSUS.md
Implement every P0 and P1 item from the FINAL ACTION PLAN.
Do NOT change anything in VALIDATED STRENGTHS.
regression_test.sh -- zero FAILs required.
git add -A && git commit -m "feat($NAME): post-audit second pass"
git push origin $BRANCH

Print final summary: files created, test results, audit scores, PR ready: YES/NO
PROMPT_EOF

  tmux kill-session -t "build_${NAME}" 2>/dev/null || true
  tmux new-session -d -s "build_${NAME}" \
    "source ~/protocol_pulse/.env && export ANTHROPIC_API_KEY && cd $WORKTREE && claude --dangerously-skip-permissions < /tmp/cc_prompt_${NAME}.txt 2>&1 | tee $LOG; echo SESSION_COMPLETE_${NAME} >> $LOG"

  echo "  session launched: build_${NAME}"
}

if [ $# -gt 0 ]; then TARGETS=("$@")
else
  TARGETS=()
  for f in "${FEATURES[@]}"; do TARGETS+=("$(echo $f | cut -d'|' -f1)"); done
fi

echo ""; echo "PROTOCOL PULSE PARALLEL BUILD LAUNCHER"
echo "Launching ${#TARGETS[@]} sessions: Build + 2-cycle audit + second pass"
echo ""

cd $BASE_DIR && git pull origin main --quiet 2>/dev/null || true

LAUNCHED=0
for feature_def in "${FEATURES[@]}"; do
  NAME=$(echo $feature_def | cut -d'|' -f1)
  BRANCH=$(echo $feature_def | cut -d'|' -f2)
  GOSPEL=$(echo $feature_def | cut -d'|' -f3)
  HIGH=$(echo $feature_def | cut -d'|' -f4)
  for target in "${TARGETS[@]}"; do
    if [ "$target" == "$NAME" ]; then
      launch_feature $NAME $BRANCH $GOSPEL $HIGH
      LAUNCHED=$((LAUNCHED + 1))
      sleep 8
      break
    fi
  done
done

echo ""; echo "$LAUNCHED SESSIONS LAUNCHED"
echo ""
echo "Monitor: tmux ls | grep build_"
echo "Attach:  tmux attach -t build_f1-avatar-oracle  (Ctrl+B D to detach)"
echo "Logs:    tail -f $LOG_DIR/*.log"
echo "Audits:  ls $BASE_DIR/docs/audits/*/FINAL_CONSENSUS.md"
echo "Branches: cd $BASE_DIR && git branch -a | grep feature/"
