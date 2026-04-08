#!/bin/bash
INPUT=$(cat)
CMD=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('command', ''))
except: pass
" <<< "$INPUT")

# Block .env exposure
if echo "$CMD" | grep -qE 'cat.*\.env|echo.*\.env|head.*\.env|tail.*\.env|less.*\.env|more.*\.env'; then
    echo "BLOCKED: Cannot print .env contents — security rule" >&2
    exit 2
fi

# Block sed on .env
if echo "$CMD" | grep -qE 'sed.*\.env'; then
    echo "BLOCKED: Cannot sed .env — use nano for .env edits" >&2
    exit 2
fi

# Block force push
if echo "$CMD" | grep -qE 'git push.*(-f|--force)'; then
    echo "BLOCKED: Force push prohibited" >&2
    exit 2
fi

# Block avatar_server
if echo "$CMD" | grep -qE 'avatar_server'; then
    echo "WARNING: Satomi Oracle avatar_server is a PROTECTED live service — DO NOT KILL" >&2
    exit 2
fi

# Block export ANTHROPIC_API_KEY
if echo "$CMD" | grep -qE 'export ANTHROPIC_API_KEY'; then
    echo "BLOCKED: Never export ANTHROPIC_API_KEY before CC" >&2
    exit 2
fi

# Block rm -rf critical
if echo "$CMD" | grep -qE 'rm -rf\s+(/home/ultron/protocol_pulse|/home/ultron|/|~)$'; then
    echo "BLOCKED: Cannot rm -rf critical directories" >&2
    exit 2
fi

exit 0
