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
#   only (pipeline/telegram.deliver_run), and ONLY for a run release_auth.authorise passes (its attestation is
#   ALL_PASS and every bound file has its attested sha256): "HOLD FOR APPROVAL - all release gates passed, no
#   waivers" (orchestrator 2026-11-11 08:30: a HOLD is never sent; its run dir is the record). Children never
#   inherit the lock fd (9>&-), so an orphaned child cannot keep the next run out.
# - log: logs/pulse_check/run_<stamp>.log (git HEAD, run dir, exit code, delivery message ids)
# - DEC-9 story ledger: an AUTO run whose two finals went out as HOLD FOR APPROVAL is recorded in
#   data/pulse_check/story_ledger.jsonl (its counted evidence statements); later auto runs never select an
#   event resting on one of them (pipeline/story_ledger.py)
# - preflight first (pipeline/preflight.py: GPU0, Ollama, yt-dlp, ElevenLabs quota, Telegram, disk, a clean pushed
#   HEAD, no other run, brand assets + registry): a failure exits 3 (HOLD) before run_fresh starts
# Exit (--foreground, and in the log): run_fresh's code (0 = every release gate passed, 3 = HOLD), 70 = the run
# passed but was not delivered (the drop failed or was refused by release_auth, or no finals were found), 71 =
# delivered but the DEC-9 story ledger write failed,
# 75 = locked, 64 = usage. The detached launcher exits 0 once the
# tmux session is up (1 if tmux failed, 75 if a run already holds the lock); the run's code is in the log.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SELF="$REPO/scripts/pulse_check_run.sh"
STAMP="$(date -u +%Y%m%d_%H%M%S)"

FOREGROUND=0
TELEGRAM=1
MODE=auto                     # DEC-9: only an AUTO run delivered HOLD FOR APPROVAL enters the story ledger
ARGS=()
ORIG=("$@")
while [ $# -gt 0 ]; do
  case "$1" in
    --pinned) [ $# -ge 2 ] && [ -f "$2" ] || { echo "usage: --pinned PIN.json (file must exist)" >&2; exit 64; }
              ARGS+=(--pinned "$(realpath "$2")"); MODE=pinned; shift 2 ;;
    --no-telegram) TELEGRAM=0; shift ;;
    --foreground) FOREGROUND=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

CUR_SESSION=""
[ -n "${TMUX:-}" ] && CUR_SESSION="$(tmux display-message -p '#S' 2>/dev/null || true)"
if [ "$FOREGROUND" = 0 ] && [[ "$CUR_SESSION" != pipeline_* ]]; then
  if ! ( exec 9>/tmp/pulse_check_run.lock; flock -n 9 ); then
    echo "pulse_check_run: another run holds /tmp/pulse_check_run.lock" >&2; exit 75
  fi
  NAME="pipeline_pulse_check_$STAMP"
  CMD="bash $(printf '%q' "$SELF") --foreground"
  # the RESOLVED arguments (a relative PIN path is not re-resolved inside the new session: GPT-gates F39)
  for a in "${ARGS[@]}"; do CMD+=" $(printf '%q' "$a")"; done
  [ "$TELEGRAM" = 0 ] && CMD+=" --no-telegram"
  if ! tmux new-session -d -s "$NAME" "$CMD"; then
    echo "pulse_check_run: tmux could not start session $NAME" >&2; exit 1
  fi
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
# law L-r ONE OWNER: the GPU0 lease (pipeline/gpu0.py) on fd 8 for the whole run; preflight and run_fresh inherit
# the descriptor (custody), nothing else may load onto GPU0 meanwhile; released when this script exits
GPU0_LEASE="${PP_GPU0_LEASE:-/tmp/pulse_gpu0.lease}"
exec 8>>"$GPU0_LEASE"
if ! flock -n 8; then
  echo "pulse_check_run: the GPU0 lease is held: $(cat "$GPU0_LEASE" 2>/dev/null)" | tee -a "$LOG" >&2
  exit 75
fi
python3 -c 'import json, sys, time; json.dump({"pid": int(sys.argv[1]), "owner": "pulse_check_run " + sys.argv[2] + " (" + sys.argv[3] + ")", "since": time.time()}, open(sys.argv[4], "w"))' \
  "$$" "$STAMP" "${ARGS[*]:-auto}" "$GPU0_LEASE"

export CUDA_VISIBLE_DEVICES=0
export CUDA_DEVICE_ORDER=PCI_BUS_ID      # law L-r: CUDA device 0 is nvidia-smi GPU 0 (gpu0.require checks it)
cd "$REPO/pipeline" || exit 1
echo "=== pulse_check_run $STAMP | HEAD $(git -C "$REPO" rev-parse HEAD) | args: ${ARGS[*]:-auto} ===" | tee -a "$LOG"
# preflight (orchestrator 2026-11-11 '21:10'): seconds, before any hour is spent; a failure is a HOLD with the reason
python3 preflight.py 9>&- 2>&1 | tee -a "$LOG" 9>&-
if [ "${PIPESTATUS[0]}" != 0 ]; then
  echo "run_fresh exit 3 | run dir none (preflight HOLD: run_fresh not started)" | tee -a "$LOG"
  exit 3
fi
python3 run_fresh.py "${ARGS[@]}" 9>&- 2>&1 | tee -a "$LOG" 9>&-
RC=${PIPESTATUS[0]}
RUN_DIR="$(grep -m1 -oP '(?<==== FRESH-TOPIC RUN ).*(?= ===)' "$LOG" || true)"
echo "run_fresh exit $RC | run dir ${RUN_DIR:-none}" | tee -a "$LOG"

if [ "$TELEGRAM" = 1 ] && [ "$RC" != 0 ]; then
  # orchestrator 2026-11-11 08:30: PBX gets a run only when it passes; a HOLD is never sent (its REPORT.md,
  # GATE_REPORT.json and contact sheets in the run dir are the record)
  echo "HOLD (run_fresh exit $RC): not delivered; see $RUN_DIR/REPORT.md" | tee -a "$LOG"
elif [ "$TELEGRAM" = 1 ] && [ -n "$RUN_DIR" ] && [ -f "$RUN_DIR/out/segment.mp4" ] && [ -f "$RUN_DIR/out/segment_vertical.mp4" ]; then
  python3 -c "import sys, telegram; r = telegram.deliver_run(sys.argv[1]); print('delivered:', [m.get('message_id') for m in r['messages']])" \
    "$RUN_DIR" 9>&- 2>&1 | tee -a "$LOG" 9>&-
  if [ "${PIPESTATUS[0]}" != 0 ]; then
    echo "pulse_check_run: Telegram delivery FAILED (see above); run dir $RUN_DIR" | tee -a "$LOG"
    exit 70
  fi
  # DEC-9 ledger, from the delivery record just written (a separate step: a ledger fault never reads as a
  # failed drop, and is never silent: the next auto run could select this story again)
  python3 -c "import json, os, sys, story_ledger; r = json.load(open(os.path.join(sys.argv[1], 'TELEGRAM_DELIVERY.json'))); e = story_ledger.record_if_approved(sys.argv[1], r, sys.argv[2]); print('story ledger:', 'recorded ' + e['run'] if e else 'not recorded (pinned, review-only or option)')" \
    "$RUN_DIR" "$MODE" 9>&- 2>&1 | tee -a "$LOG" 9>&-
  if [ "${PIPESTATUS[0]}" != 0 ]; then
    echo "pulse_check_run: delivered, but the story ledger was NOT recorded (see above): the next auto run may select this story again; run dir $RUN_DIR" | tee -a "$LOG"
    exit 71
  fi
elif [ "$TELEGRAM" = 1 ]; then
  # run_fresh exited 0 (every release gate passed) but no run dir / finals were found: nothing was delivered,
  # and that is never a success (GPT-gates F38, Claude-gates P2)
  echo "pulse_check_run: run_fresh exit 0 but run dir '${RUN_DIR:-none}' has no finals: NOT delivered" | tee -a "$LOG"
  exit 70
fi
exit "$RC"
