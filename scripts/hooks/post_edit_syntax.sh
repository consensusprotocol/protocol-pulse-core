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
        # Pipeline files: hard block (exit 1) to prevent broken commits
        if [[ "$FILE_PATH" == */video_pipeline_v3/* ]]; then
            echo "PIPELINE SYNTAX ERROR in $FILE_PATH: $ERR" >&2
            exit 1
        fi
        # Non-pipeline .py: warn but don't block
        python3 -c "
import json
print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext': 'SYNTAX ERROR: $ERR — FIX THIS BEFORE PROCEEDING'}}))
"
    fi
fi
exit 0
