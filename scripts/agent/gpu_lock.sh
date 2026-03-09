#!/usr/bin/env bash
# gpu_lock.sh — acquire or release GPU render lock
# Usage: ./gpu_lock.sh acquire <session-name>
#        ./gpu_lock.sh release <session-name>
#        ./gpu_lock.sh check
LOCKFILE="/tmp/gpu_render.lock"
ACTION="${1:-check}"
SESSION="${2:-unknown}"

case "$ACTION" in
  acquire)
    if [ -f "$LOCKFILE" ]; then
        OWNER=$(python3 -c "import json; print(json.load(open('$LOCKFILE')).get('owner','?'))" 2>/dev/null || echo "unknown")
        echo "ERROR: GPU lock held by $OWNER"
        exit 1
    fi
    python3 -c "
import json, os
json.dump({'owner': '$SESSION', 'pid': os.getpid(), 'started': __import__('datetime').datetime.utcnow().isoformat()+'Z'}, open('$LOCKFILE','w'))
"
    echo "GPU lock acquired by $SESSION"
    trap "rm -f $LOCKFILE" EXIT INT TERM
    ;;
  release)
    rm -f "$LOCKFILE"
    echo "GPU lock released"
    ;;
  check)
    if [ -f "$LOCKFILE" ]; then
        echo "LOCKED: $(cat $LOCKFILE)"
        exit 1
    else
        echo "UNLOCKED"
        exit 0
    fi
    ;;
esac
