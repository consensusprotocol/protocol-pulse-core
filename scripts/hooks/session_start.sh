#!/bin/bash
RULES_FILE="/home/ultron/protocol_pulse/video_pipeline_v3/PIPELINE_LAWS.md"
RULES=""

if [ -f "$RULES_FILE" ]; then
    RULES="$(head -100 $RULES_FILE)"
fi

RULES="$RULES
--- PROTOCOL PULSE SYSTEM RULES (ENFORCED BY HOOK) ---
RULE: Every commit must include git add+commit+push.
RULE: Never assign PBX manual tasks. Solve autonomously.
RULE: Triple-verify every feature before claiming done.
RULE: Never print .env contents or expose API keys.
RULE: Never sed .env files. Use nano for .env edits.
RULE: One Claude Code session at a time on same repo.
RULE: AUDIT-FIRST LAW — read files before changing them.
RULE: Waitress serves port 5000. Gunicorn is RETIRED.
RULE: Avatar server is DISABLED until new HeyGen avatar.
RULE: Ollama models auto-unload (KEEP_ALIVE=5m).
RULE: PBX time references in New York Eastern Time (ET).
RULE: Git repo is consensusprotocol/protocol-pulse-core.
RULE: assembler.py has been SPLIT into modules — edit render_narrator.py, render_clip.py, render_social.py etc, NOT assembler.py directly."

python3 -c "
import json, sys
ctx = sys.stdin.read()
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': ctx}}))
" <<< "$RULES"
exit 0
