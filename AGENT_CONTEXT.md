# AGENT BOOT CONTEXT — AUTO-GENERATED
# Generated: 2026-03-09 UTC
# Feature: terminal-api-v2 | Branch: agent/terminal-api-v2 | Session: agent_terminal-api-v2

## IDENTITY
You are a Claude Code agent in the Protocol Pulse multi-agent factory.
Your ONLY job is the feature described in FEATURE_SPEC.md.
You are in an isolated git worktree. Main branch is PRODUCTION — never touch it.

## CRITICAL RULES
1. Read FEATURE_SPEC.md completely before touching any code.
2. Read ~/protocol_pulse/PULSE_TERMINAL_LAWS.md before any Terminal work.
3. Only modify files listed in FEATURE_SPEC.md under FILES_TO_TOUCH.
4. Use test_data/ for all data writes — never write to ~/protocol_pulse/data/
5. Run your test command before every commit. Zero failures required.
6. When done: signal completion — DO NOT manually merge.

## KEY PATHS
- Your worktree: /home/ultron/worktrees/terminal-api-v2
- Production (READ ONLY): ~/protocol_pulse/
- Test data: /home/ultron/worktrees/terminal-api-v2/test_data/
- Replit Flask app: ~/app/ on Replit (push via git after every edit)

## DONE SIGNAL
When complete: run ~/protocol_pulse/regression_test.sh from worktree, confirm 0 FAILs,
then run ~/protocol_pulse/scripts/agent/merge_agent.sh terminal-api-v2
