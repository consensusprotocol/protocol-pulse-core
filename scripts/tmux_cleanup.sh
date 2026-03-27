#!/bin/bash
# Auto-cleanup dead/idle tmux sessions older than 2 hours
# Preserves: watchdog_llm, pipeline, render_forensic, media_audit, intel_audit, oracle_forensic, sovereign_context, panopticon

KEEP_SESSIONS="watchdog_llm|pipeline|render_forensic|media_audit|intel_audit|oracle_forensic|sovereign_context|panopticon|zombie_fix|join_redesign"

CLEANED=0
while IFS= read -r line; do
    SESSION=$(echo "$line" | cut -d: -f1)
    # Skip sessions we want to keep
    if echo "$SESSION" | grep -qE "$KEEP_SESSIONS"; then
        continue
    fi
    # Check if session has any running processes (not just idle shell)
    PANE_OUTPUT=$(tmux capture-pane -t "$SESSION" -p 2>/dev/null | tail -3)
    # If session shows "running" or recent CC activity, keep it
    if echo "$PANE_OUTPUT" | grep -qE "Running|running|bypass permissions|Rendering|Encoding|Auditing"; then
        continue
    fi
    # Kill idle sessions
    tmux kill-session -t "$SESSION" 2>/dev/null && CLEANED=$((CLEANED+1))
done < <(tmux ls 2>/dev/null)

echo "[$(date '+%Y-%m-%d %H:%M')] Tmux cleanup: removed $CLEANED idle sessions. Active: $(tmux ls 2>/dev/null | wc -l)" >> ~/protocol_pulse/logs/tmux_cleanup.log
