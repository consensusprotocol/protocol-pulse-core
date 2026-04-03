#!/bin/bash
INPUT=$(cat)
FILE_PATH=$(python3 -c "
import json, sys
try:
    d = json.loads(sys.stdin.read())
    print(d.get('tool_input', {}).get('file_path', ''))
except: pass
" <<< "$INPUT")

if [[ "$FILE_PATH" == *.py ]] && [ -f "$FILE_PATH" ]; then
    ERR=$(python3 -m py_compile "$FILE_PATH" 2>&1)
    if [ $? -ne 0 ]; then
        python3 -c "
import json
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': 'SYNTAX ERROR: $ERR — FIX THIS BEFORE PROCEEDING'}}))
"
    fi
fi
exit 0
