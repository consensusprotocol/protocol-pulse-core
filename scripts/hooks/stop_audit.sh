#!/bin/bash
# Protocol Pulse CC Stop Hook — post-session audit + verification
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
UNCOMMITTED=$(git diff --name-only -- '*.py' 2>/dev/null | wc -l)
STAGED=$(git diff --cached --name-only -- '*.py' 2>/dev/null | wc -l)
if [ "$UNCOMMITTED" -gt 0 ] || [ "$STAGED" -gt 0 ]; then
    FILES=$(git diff --name-only -- '*.py' 2>/dev/null | head -5 | tr '\n' ', ')
    ISSUES="$ISSUES | UNCOMMITTED: $FILES — run git add+commit+push!"
fi

# Syntax check all recently modified .py files
for f in $(git diff --name-only -- '*.py' 2>/dev/null | head -10); do
    if [ -f "$f" ]; then
        ERR=$(python3 -m py_compile "$f" 2>&1)
        if [ $? -ne 0 ]; then
            ISSUES="$ISSUES | SYNTAX ERROR in $f"
        fi
    fi
done

# Check waitress
if ! pgrep -f "waitress.*5000" > /dev/null 2>&1; then
    ISSUES="$ISSUES | CRITICAL: Waitress DOWN — restart immediately!"
fi

# Check for RAM hogs that shouldn't be running
if pgrep -f "avatar_server" > /dev/null 2>&1; then
    ISSUES="$ISSUES | WARNING: avatar_server is running (should be DISABLED)"
fi

# Run regression tests if pipeline files were modified
PIPELINE_CHANGED=$(git diff --name-only -- 'video_pipeline_v3/*.py' 2>/dev/null | wc -l)
if [ "$PIPELINE_CHANGED" -gt 0 ] && [ -x video_pipeline_v3/regression_test.sh ]; then
    REG_OUT=$(bash video_pipeline_v3/regression_test.sh 2>&1)
    if [ $? -ne 0 ]; then
        FAIL_COUNT=$(echo "$REG_OUT" | grep -c "FAIL:")
        ISSUES="$ISSUES | REGRESSION: $FAIL_COUNT tests failed — run regression_test.sh"
    fi
fi

if [ -n "$ISSUES" ]; then
    python3 -c "
import json
print(json.dumps({'decision': 'block', 'reason': 'POST-SESSION AUDIT FAILED: $ISSUES'}))
"
    exit 0
fi

exit 0
