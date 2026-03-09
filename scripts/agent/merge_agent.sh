#!/usr/bin/env bash
# merge_agent.sh — agent completion, PR, and cleanup
# Usage: ./scripts/agent/merge_agent.sh <feature-name>
set -euo pipefail
FEATURE="${1:-}"
[ -z "$FEATURE" ] && echo "Usage: $0 <feature-name>" && exit 1

BASE=~/protocol_pulse
WORKTREE_DIR=~/worktrees/$FEATURE
BRANCH="agent/$FEATURE"
SESSION="agent_$FEATURE"

echo "============================================================"
echo " MERGE AGENT: $FEATURE"
echo "============================================================"

# Verify worktree exists
[ ! -d "$WORKTREE_DIR" ] && echo "ERROR: Worktree not found: $WORKTREE_DIR" && exit 1

# Run regression test in worktree
echo "[TEST] Running regression in worktree..."
cd "$WORKTREE_DIR"
if ! ~/protocol_pulse/regression_test.sh; then
    echo "ERROR: Regression FAILED — fix before merging"
    exit 1
fi
echo "[TEST] Passed."

# Ensure all committed
UNCOMMITTED=$(git -C "$WORKTREE_DIR" status --porcelain | wc -l)
if [ "$UNCOMMITTED" -gt 0 ]; then
    echo "ERROR: $UNCOMMITTED uncommitted changes in worktree"
    git -C "$WORKTREE_DIR" status --short
    exit 1
fi

# Push branch
git -C "$WORKTREE_DIR" push origin "$BRANCH" 2>/dev/null || echo "[WARN] push failed — check manually"

# Open PR via GitHub CLI (if available)
if command -v gh &>/dev/null; then
    gh pr create \
        --title "feat($FEATURE): agent build complete" \
        --body "Automated PR from agent_$FEATURE. Regression tests passed. Ready for review." \
        --base main --head "$BRANCH" 2>/dev/null && echo "[PR] Opened on GitHub" || echo "[WARN] gh pr create failed"
else
    echo "[INFO] gh CLI not available — open PR manually:"
    echo "  https://github.com/consensusprotocol/protocol-pulse-core/compare/main...$BRANCH"
fi

# Kill tmux session
tmux kill-session -t "$SESSION" 2>/dev/null && echo "[TMUX] Session $SESSION killed" || echo "[INFO] Session already gone"

# Remove worktree and branch
cd "$BASE"
git worktree remove "$WORKTREE_DIR" --force 2>/dev/null && echo "[WORKTREE] Removed $WORKTREE_DIR"
git branch -d "$BRANCH" 2>/dev/null || echo "[INFO] Branch retained (has unmerged changes — normal before PR merge)"

echo ""
echo "============================================================"
echo " AGENT $FEATURE COMPLETE"
echo " Review + merge PR on GitHub, then pull main."
echo "============================================================"
