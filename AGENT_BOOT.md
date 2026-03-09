# AGENT_BOOT.md — Protocol Pulse Multi-Agent Factory
# Read this if you're a Claude Code agent on this system.

## RELAY TOKENS
Two relay tokens exist. Use RT (Replit relay) for all agent sessions.

- **Ultron Relay (UT):** Used by orchestrator.py for system-level commands
  - Endpoint: https://relay.protocolpulse.io/exec
  - Token: in orchestrator/orchestrator.py (UT variable)

- **Replit Relay (RT):** Used for API key resolution and Replit comms
  - Endpoint: https://protocolpulse.replit.app/api/admin/exec  
  - Token: 581b1076ca6d8a8809997d24f0869431ffd75c64de9ea703b6ab0f3e39fbd552

## API KEY RESOLUTION
Keys are NOT in Ultron .env (only 4 keys there).
Keys live as Replit Secrets and are fetched dynamically:
```python
from relay import get_key
key = get_key('ELEVENLABS_API_KEY')  # checks local env → fetches from Replit
```
relay.py is at: video_pipeline_v3/relay.py

## TMUX SESSION NAMING
All agent sessions: agent_[feature-name]
Never create sessions with other names.
Check before launching: tmux has-session -t agent_[name]

## WORKTREE PATHS
Production (READ ONLY for agents): ~/protocol_pulse/
Agent worktrees: ~/worktrees/[feature-name]/
Always work in your worktree. Never cd to ~/protocol_pulse/ and edit.

## BEFORE ANY COMMIT
cd ~/protocol_pulse && ./regression_test.sh
Zero FAILs required. No exceptions.

## AGENT SCRIPTS
- Launch: ~/protocol_pulse/scripts/agent/launch_agent.sh [feature]
- Merge:  ~/protocol_pulse/scripts/agent/merge_agent.sh [feature]
- Kill:   ~/protocol_pulse/scripts/agent/kill_agent.sh [feature]
- GPU:    ~/protocol_pulse/scripts/agent/gpu_lock.sh acquire/release/check [session]
