#!/bin/bash
INPUT=$(cat)

# Prevent infinite loop
IS_ACTIVE=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('stop_hook_active', False))
except: print('False')
" <<< "$INPUT")

if [ "$IS_ACTIVE" = "True" ]; then
    exit 0
fi

cd /home/ultron/protocol_pulse
ISSUES=""

# Check uncommitted Python files
UNCOMMITTED=$(git status --porcelain -- '*.py' 2>/dev/null | wc -l)
if [ "$UNCOMMITTED" -gt 0 ]; then
    ISSUES="$ISSUES | $UNCOMMITTED uncommitted .py files — git add+commit+push!"
fi

# Check waitress
if ! pgrep -f "waitress.*5000" > /dev/null 2>&1; then
    ISSUES="$ISSUES | CRITICAL: Waitress DOWN — website offline!"
fi

if [ -n "$ISSUES" ]; then
    python3 -c "
import json
print(json.dumps({'decision': 'block', 'reason': 'POST-SESSION AUDIT: $ISSUES'}))
"
    exit 0
fi

exit 0
