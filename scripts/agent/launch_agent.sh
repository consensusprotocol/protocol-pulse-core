#!/usr/bin/env bash
# ============================================================
# launch_agent.sh — Protocol Pulse Multi-Agent Factory
# Usage: ./scripts/agent/launch_agent.sh <feature-name>
# Example: ./scripts/agent/launch_agent.sh tradfi-segment
# ============================================================
set -euo pipefail

FEATURE="${1:-}"
if [ -z "$FEATURE" ]; then
    echo "ERROR: feature name required"
    echo "Usage: $0 <feature-name>"
    echo "Available specs:"
    ls ~/protocol_pulse/scripts/agent/specs/ 2>/dev/null | sed 's/SPEC_//' | sed 's/.md//'
    exit 1
fi

BASE=~/protocol_pulse
WORKTREE_BASE=~/worktrees
WORKTREE_DIR="$WORKTREE_BASE/$FEATURE"
BRANCH="agent/$FEATURE"
SESSION="agent_$FEATURE"
SPEC="$BASE/scripts/agent/specs/SPEC_${FEATURE}.md"

echo "============================================================"
echo " PROTOCOL PULSE AGENT LAUNCHER"
echo " Feature: $FEATURE"
echo " Branch:  $BRANCH"
echo " Worktree: $WORKTREE_DIR"
echo " Session: $SESSION"
echo "============================================================"

# ── GUARD: spec must exist ──
if [ ! -f "$SPEC" ]; then
    echo "ERROR: No spec found at $SPEC"
    echo "Create it first from the template: scripts/agent/FEATURE_SPEC_TEMPLATE.md"
    exit 1
fi

# ── GUARD: session must not already exist ──
if tmux has-session -t "$SESSION" 2>/dev/null; then
    echo "ERROR: Session $SESSION already exists."
    echo "Attach: tmux attach -t $SESSION"
    echo "Kill first: ./scripts/agent/kill_agent.sh $FEATURE"
    exit 1
fi

# ── GUARD: worktree must not already exist ──
if [ -d "$WORKTREE_DIR" ]; then
    echo "ERROR: Worktree $WORKTREE_DIR already exists."
    echo "Kill first: ./scripts/agent/kill_agent.sh $FEATURE"
    exit 1
fi

# ── GUARD: regression must pass on main first ──
echo "[PRE-FLIGHT] Running regression test on main..."
cd "$BASE"
if ! ./regression_test.sh > /tmp/regression_preflight.log 2>&1; then
    echo "ERROR: Regression test FAILED on main. Fix before launching agent."
    cat /tmp/regression_preflight.log
    exit 1
fi
echo "[PRE-FLIGHT] Regression passed."

# ── CREATE WORKTREE ──
echo "[WORKTREE] Creating branch $BRANCH from main..."
mkdir -p "$WORKTREE_BASE"
cd "$BASE"
git checkout -b "$BRANCH" main 2>/dev/null || git checkout "$BRANCH"
git worktree add "$WORKTREE_DIR" "$BRANCH"
echo "[WORKTREE] Created: $WORKTREE_DIR"

# ── SET UP TEST DATA DIR ──
mkdir -p "$WORKTREE_DIR/test_data/output"
mkdir -p "$WORKTREE_DIR/test_data/intelligence"

# Copy synthetic test data
cp "$BASE/video_pipeline_v3/data/intelligence/live_signals.json" \
   "$WORKTREE_DIR/test_data/intelligence/live_signals_template.json" 2>/dev/null || true

# ── WRITE AGENT BOOT CONTEXT ──
cat > "$WORKTREE_DIR/AGENT_CONTEXT.md" << CONTEXT
# AGENT BOOT CONTEXT — AUTO-GENERATED
# Generated: $(date -u '+%Y-%m-%d %H:%M:%S UTC')
# Feature: $FEATURE | Branch: $BRANCH | Session: $SESSION

## IDENTITY
You are a Claude Code agent in the Protocol Pulse multi-agent factory.
Your ONLY job is the feature described in FEATURE_SPEC.md.
You are in an isolated git worktree. Main branch is PRODUCTION — never touch it.

## CRITICAL RULES
1. Read FEATURE_SPEC.md completely before touching any code.
2. Read PIPELINE_LAWS.md completely before touching pipeline code.
3. Only modify files listed in FEATURE_SPEC.md under FILES_TO_TOUCH.
4. Set TEST_MODE=true for all renders and API calls.
5. Use test_data/ for all data writes — never write to ~/protocol_pulse/data/
6. Run your test command before every commit. Zero failures required.
7. When done: run merge_agent.sh — do NOT manually merge.

## KEY PATHS
- Your worktree: $WORKTREE_DIR
- Production (READ ONLY): ~/protocol_pulse/
- Test data: $WORKTREE_DIR/test_data/
- GPU lock: /tmp/gpu_render.lock (acquire before any render)

## RELAY / API KEYS
Keys resolve via relay.py: get_key('KEY_NAME') → checks env → fetches from Replit
Both tokens documented in AGENT_BOOT.md

## WHEN DONE
Run: ~/protocol_pulse/scripts/agent/merge_agent.sh $FEATURE
CONTEXT

echo "[BOOT] Agent context written"

# ── PUSH BRANCH TO ORIGIN ──
git -C "$WORKTREE_DIR" push -u origin "$BRANCH" 2>/dev/null || echo "[WARN] Could not push branch to origin — push manually when ready"

# ── LAUNCH TMUX SESSION ──
echo "[TMUX] Launching session: $SESSION"
tmux new-session -d -s "$SESSION" -c "$WORKTREE_DIR"

# Load context and launch Claude Code
tmux send-keys -t "$SESSION" \
    "export TEST_MODE=true AGENT_DEV_MODE=true AGENT_FEATURE=$FEATURE && \
     echo '=== AGENT $FEATURE BOOTED ===' && \
     echo 'Reading spec...' && \
     cat FEATURE_SPEC.md && \
     echo '' && echo 'Starting Claude Code...' && \
     unset ANTHROPIC_API_KEY && \
     claude --dangerously-skip-permissions" Enter

echo ""
echo "============================================================"
echo " AGENT LAUNCHED"
echo " Attach: tmux attach -t $SESSION"
echo " Kill:   ./scripts/agent/kill_agent.sh $FEATURE"
echo " Merge:  ./scripts/agent/merge_agent.sh $FEATURE"
echo "============================================================"
