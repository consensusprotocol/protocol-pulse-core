#!/usr/bin/env bash
# scripts/pulse_check_run.sh — ONE command for a Pulse Check run (DEC-8 d, 2026-11-11). NOT installed in cron.
#
#   scripts/pulse_check_run.sh                    # AUTO: the engine's own top Bitcoin story (run_fresh.py)
#   scripts/pulse_check_run.sh --pinned PIN.json  # PINNED (e.g. the corrected Nov 10 recut)
#   options: --no-telegram   render + gates + verification pack only
#            --foreground    run in this shell (default: a detached tmux session, see below)
#
# - one run at a time: flock on /tmp/pulse_check_run.lock (a second invocation exits 75 at once)
# - tmux-safe: unless already inside a pipeline_* session (or --foreground), relaunches itself in a NEW
#   detached session pipeline_pulse_check_<UTC stamp>; scripts/tmux_cleanup.sh (cron) keeps 'pipeline'
#   sessions, so a long render is never reaped as idle. No other session is touched.
# - GPU0 only (CUDA_VISIBLE_DEVICES=0); nothing is published: drops go to the Telegram approval chat
#   only (pipeline/telegram.deliver_run): "HOLD FOR APPROVAL - all gates passed, no waivers" or
#   "REVIEW ONLY" with the failing list.
# - log: logs/pulse_check/run_<stamp>.log (git HEAD, run dir, exit code, delivery message ids)
# Exit: run_fresh's code (0 = every gate passed, 3 = HOLD), 75 = locked, 64 = usage.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SELF="$REPO/scripts/pulse_check_run.sh"
STAMP="$(date -u +%Y%m%d_%H%M%S)"

FOREGROUND=0
TELEGRAM=1
ARGS=()
ORIG=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    --pinned) [ $# -ge 2 ] || { echo "usage: --pinned PIN.json" >&2; exit 64; }
              ARGS+=(--pinned "$(cd "$(dirname "$2")" && pwd)/$(basename "$2")"); shift 2 ;;
    --no-telegram) TELEGRAM=0; shift ;;
    --foreground) FOREGROUND=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

CUR_SESSION=""
[ -n "${TMUX:-}" ] && CUR_SESSION="$(tmux display-message -p '#S' 2>/dev/null || true)"
if [ "$FOREGROUND" = 0 ] && [[ "$CUR_SESSION" != pipeline_* ]]; then
  NAME="pipeline_pulse_check_$STAMP"
  tmux new-session -d -s "$NAME" "bash '$SELF' --foreground ${ORIG[*]}"
  echo "started in tmux session $NAME (attach: tmux attach -t $NAME); log: $REPO/logs/pulse_check/"
  exit 0
fi

LOG_DIR="$REPO/logs/pulse_check"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/run_$STAMP.log"
exec 9>/tmp/pulse_check_run.lock
if ! flock -n 9; then
  echo "pulse_check_run: another run holds /tmp/pulse_check_run.lock" | tee -a "$LOG" >&2
  exit 75
fi

export CUDA_VISIBLE_DEVICES=0
cd "$REPO/pipeline" || exit 1
echo "=== pulse_check_run $STAMP | HEAD $(git -C "$REPO" rev-parse HEAD) | args: ${ARGS[*]:-auto} ===" | tee -a "$LOG"
python3 run_fresh.py "${ARGS[@]}" 2>&1 | tee -a "$LOG"
RC=${PIPESTATUS[0]}
RUN_DIR="$(grep -m1 -oP '(?<==== FRESH-TOPIC RUN ).*(?= ===)' "$LOG" || true)"
echo "run_fresh exit $RC | run dir ${RUN_DIR:-none}" | tee -a "$LOG"

if [ "$TELEGRAM" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/out/segment.mp4" ] && [ -f "$RUN_DIR/out/segment_vertical.mp4" ]; then
  python3 -c "import sys, telegram; r = telegram.deliver_run(sys.argv[1]); print('delivered:', [m.get('message_id') for m in r['messages']])" \
    "$RUN_DIR" 2>&1 | tee -a "$LOG"
elif [ "$TELEGRAM" = 1 ]; then
  echo "no finals rendered: nothing delivered (the run's REPORT.md and status.json are the ledger)" | tee -a "$LOG"
fi
exit "$RC"
