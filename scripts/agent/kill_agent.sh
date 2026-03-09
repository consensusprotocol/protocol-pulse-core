#!/usr/bin/env bash
# kill_agent.sh — emergency agent cleanup
# Usage: ./scripts/agent/kill_agent.sh <feature-name>
FEATURE="${1:-}"
[ -z "$FEATURE" ] && echo "Usage: $0 <feature-name>" && exit 1

BASE=~/protocol_pulse
WORKTREE_DIR=~/worktrees/$FEATURE
BRANCH="agent/$FEATURE"
SESSION="agent_$FEATURE"

echo "Killing agent: $FEATURE"
rm -f /tmp/gpu_render.lock && echo "GPU lock released"
tmux kill-session -t "$SESSION" 2>/dev/null && echo "Session $SESSION killed" || echo "Session not found"
cd "$BASE"
git worktree remove "$WORKTREE_DIR" --force 2>/dev/null && echo "Worktree removed" || echo "Worktree not found"
git branch -D "$BRANCH" 2>/dev/null && echo "Branch deleted" || echo "Branch not found"
echo "Agent $FEATURE cleaned up."
