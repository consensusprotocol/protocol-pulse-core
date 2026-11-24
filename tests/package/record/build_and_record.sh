#!/bin/bash
# THE BUILD LAUNCHER, the one committed command for a build (the orchestrator's acceptance list, 09:20 ET Nov 24, item 9,
# and its amendment C, 09:35: it replaces the scratch build_and_record.sh, whose defects are each answered here):
#  - ONE driver, fixed: tests/package/proof_ledger.py. An environment that names another (DRIVER=..., as build 168 was
#    started) is REFUSED before anything runs; the driver itself refuses any other entry point and any tree with code
#    changed and not committed (its own and the integrator's), before any model call, and records its path, both
#    commits and whether a tree was dirty.
#  - a unique build id (--build-id), and this run's OWN record folder: the driver writes its path into --out-dir-file
#    (never "the newest folder").
#  - the lock pre-check ON, always; ONE spend setting: the driver's day cap (proof_ly.DAY_CAP_USD, $1.50 a day), an
#    optional --stop-usd no higher (the driver checks it); no other spend rule here.
#  - the outer time limit stays 9000 s (the orchestrator, 09:55 ET Nov 24); at it the driver is stopped (SIGTERM) and
#    still writes its one outcome line (data/builds/outcomes.jsonl), with its time per stage.
#  - committed, pushed code only: refuses a changed driver, changed code under pipeline/ or tests/, unpushed commits.
#  - STATE line 1 from the build's own record (state_line.py, under the file's flock); the record, its outcome line and
#    its pin committed and pushed; a sealed pin goes straight to the integrator's render, as its own script takes it:
#    /home/ultron/protocol_pulse/scripts/pulse_check_run.sh --pinned PIN (its readiness check first; it detaches).
# Usage: bash tests/package/record/build_and_record.sh N "WHY" [--only FILE] [--stop-usd X]
set -u
if [ -n "${DRIVER:-}" ]; then   # the acceptance list, item 9: "start it the way build 168 was started; it refuses"
  echo "REFUSED: DRIVER=${DRIVER} names another driver, and a build runs only tests/package/proof_ledger.py, as committed: nothing was started."
  exit 2
fi
R=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)           # tests/package/record
W=$(cd "$R/../../.." && pwd)                               # the repository
THE_DRIVER=tests/package/proof_ledger.py
RENDER=${PP_RENDER_SCRIPT:-/home/ultron/protocol_pulse/scripts/pulse_check_run.sh}   # the integrator's, unchanged
if [ $# -lt 2 ]; then echo "usage: bash tests/package/record/build_and_record.sh N \"WHY\" [--only FILE] [--stop-usd X]"; exit 64; fi
N=$1; WHY=$2; shift 2
EXTRA=("$@")
for x in "${EXTRA[@]}"; do
  case "$x" in --lock-precheck|--build-id|--out-dir-file|--build-no) echo "REFUSED: $x is the launcher's own setting"; exit 64;; esac
done
cd "$W" || exit 2
LK=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c 'pulse_check_run.lock')
if [ "$LK" != "0" ]; then echo "render lock held: no build, no commit"; exit 3; fi
RUN=$(ps -eo args= | awk -v d="$THE_DRIVER" '$1 ~ /python3$/ && $3 == d' | wc -l)
if [ "$RUN" != "0" ]; then echo "another build is running ($RUN process): no build"; exit 3; fi
# RULING 163 (5): the launcher REFUSES any driver that is not the committed one; a build runs on committed, pushed code
if ! git diff --quiet HEAD -- "$THE_DRIVER"; then echo "REFUSED (ruling 163 (5)): $THE_DRIVER differs from the committed one: no build"; exit 6; fi
DIRTY=$(git status --porcelain -- pipeline tests | grep -v '^??' | awk '{print $NF}' | grep -E '\.(py|sh)$' | tr '\n' ' ')
if [ -n "$DIRTY" ]; then echo "REFUSED (ruling 163 (5)): code changed and not committed: $DIRTY: no build"; exit 6; fi
AHEAD=$(git rev-list --count '@{u}..HEAD' 2>/dev/null || echo "unknown (no upstream)")
if [ "$AHEAD" != "0" ]; then echo "REFUSED (ruling 160 (1)): commits not pushed: $AHEAD: pushed code only: no build"; exit 6; fi
ONLY=""
for ((i=0; i<${#EXTRA[@]}; i++)); do [ "${EXTRA[$i]}" = "--only" ] && ONLY="${EXTRA[$((i+1))]:-}"; done
read SP LED <<< "$(python3 -B "$R/day_spent.py")"
echo "day ledger $LED, spend before \$$SP (the day cap is the driver's), lock pre-check on, time limit 9000 s"
if [ -z "$ONLY" ]; then python3 -B "$R/watch_ledger.py" --mark 2>&1 | tail -1; fi
T=$(date '+%H%M')
STAMP=$(date -u '+%Y%m%dT%H%M%SZ')
BUILD_ID="b${N}-${STAMP}-$$"                               # unique: the number, the second it starts, this process
LOGS=$W/tests/package/proof/logs                          # *.log: never committed (.gitignore)
mkdir -p "$LOGS"
LOG=$LOGS/build${N}_$T.log
OUTF=$LOGS/${BUILD_ID}.outdir
timeout --signal=TERM 9000 python3 -B "$THE_DRIVER" --build-no "$N" --build-id "$BUILD_ID" --out-dir-file "$OUTF" --lock-precheck on --routing heimdall_first --since 2026-11-13T03:01:09Z --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json tests/package/proof/fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json tests/package/proof/ledger_20261113_073738/MOMENTS_PIN_LEDGER.json tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json tests/package/proof/ledger_20261113_215708/MOMENTS_PIN_LEDGER.json "${EXTRA[@]}" > "$LOG" 2>&1
X=$?
echo "build exit $X ($BUILD_ID)"
grep "^no package\|^NOTHING NEW\|spend (ruling 48)\|PACKAGE\|RULING 76 (d)\|^REFUSED\|RULING 160 (2b)" "$LOG" | head -9 | cut -c1-240
D=$(cat "$OUTF" 2>/dev/null)                              # this run's own record folder, as the driver made it
if [ -z "$D" ] || [ ! -d "$D" ]; then echo "REFUSED or stopped before its record (exit $X): no record, no STATE line, no commit"; tail -3 "$LOG" | cut -c1-300; exit 5; fi
B=$(python3 -B "$R/day118.py" 2>&1 | tail -1)
SC=$(python3 -B "$R/scorer_stale.py" 2>&1 | tail -1)      # ruling 132: a dead scorer shows on line 1 within one build
BT=$(date -r "$D" '+%H:%M'); T2=$(date '+%H:%M')
RES=$(grep -o "^no package ([^)]*)\|^NOTHING NEW[^:]*\|PACKAGE[^;]*" "$LOG" | head -1 | cut -c1-200)
NE=$(python3 -B -c "import json,sys; r=json.load(open(sys.argv[1]+'/package.json')); ne=r.get('never_empty') or {}; print('' if r.get('package') or not ne.get('soft_why_none') else 'THE NEVER-EMPTY PASS (the one that decides): ' + str(ne['soft_why_none'])[:420])" "$D" 2>/dev/null)
[ -n "$NE" ] && RES="the clean pass: ${RES:-?}; $NE"     # build 149 / 150: line 1 quoted only the clean pass's reason
OUT=$(grep -o "RULING 160 (2b): outcome [A-Z_]* at [^:]*" "$LOG" | tail -1)   # the build's one outcome line
R76=$(grep -o "RULING 76 (d): [^;]*" "$LOG" | head -1 | cut -c1-110)
DOL=$(grep -o "spend (ruling 48): [^ ]* of \$[0-9.]* vendor-reported after this build (before it: \$[0-9.]*)" "$LOG" | tail -1)
TXT=$(mktemp "$LOGS/state_b${N}_XXXXXX.txt")
if [ -n "$ONLY" ]; then
  cp "$ONLY" "$D/ONLY.json"
  SUM=$(python3 -B "$R/attempt_summary.py" "$D" 2>&1 | tail -1 | cut -c1-900)
  printf '%s\n' "{T} ET: $B ATTEMPT, BUILD $N ($BUILD_ID, $(basename "$D"), $BT ET). TRIED: $WHY. ${SUM}. RESULT: ${RES:-?}; ${OUT:-no outcome line}.${SC:+ $SC} DOLLARS: ${DOL:-?}." > "$TXT"
else
  printf '%s\n' "{T} ET: $B BUILD $N ($BUILD_ID, $(basename "$D"), $BT ET; $WHY): ${RES:-?}; ${OUT:-no outcome line}; ${R76:-?}.${SC:+ $SC}" > "$TXT"
fi
python3 -B "$R/state_line.py" "$T2" "$TXT"
rm -f "$TXT"
LK=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c 'pulse_check_run.lock')
if [ "$LK" != "0" ]; then echo "render lock held: no commit"; exit 3; fi
for f in "$D/FINGERPRINT.json" "$D/inputs.json" "$D/package.json" "$D/SHADOW86.md" "$D/step_a.json" "$D/NOTHING_NEW.json" "$D/ONLY.json" "$D/MOMENTS_PIN_LEDGER.json" "$D/SPOTLIGHT_PIN.json"; do [ -f "$f" ] && git add "$f"; done
git add docs/audits/parallel/pp-selectid_STATE.md tests/package/proof/DAY118_LEDGER.json
[ -f data/builds/outcomes.jsonl ] && git add data/builds/outcomes.jsonl          # RULING 160 (2b): the build's line
[ -f tests/package/proof/FLAGGED_DAY.json ] && git add tests/package/proof/FLAGGED_DAY.json   # ruling 136 (2): the day count
for f in docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.jsonl docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json tests/package/proof/CANDIDATES.json tests/package/proof/HOOK_CACHE.json tests/package/proof/JOIN_CACHE.json tests/package/proof/STEP_A_CACHE.json tests/package/proof/VISUAL_CACHE.json tests/package/proof/OUT_EDGE_CACHE.json tests/package/proof/SPEND_D*.json; do [ -f "$f" ] && { git diff --quiet -- "$f" 2>/dev/null && git ls-files --error-unmatch "$f" >/dev/null 2>&1 || git add "$f"; }; done
git ls-files --others --exclude-standard tests/package/fixtures/replies | xargs -r git add
if git diff --cached --name-only | grep -qE "\.lock$|HEIMDALL_HEALTH|judge_requests|BREAKERS|DEADLINE_TABLE"; then echo "FORBIDDEN STAGED: stopping"; exit 4; fi
git commit -q -m "pp-selectid build $N ($BUILD_ID, $(basename "$D"), $BT ET): $WHY" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log -1 --oneline | cut -c1-90
git push -q origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -2
git status -sb | head -1
for PIN in "$D/MOMENTS_PIN_LEDGER.json" "$D/SPOTLIGHT_PIN.json"; do   # a sealed pin goes to the render itself, after
  [ -f "$PIN" ] || continue                                           # its commit (no session sits between them)
  SAID=$(mktemp "$LOGS/render_${BUILD_ID}_XXXXXX.txt")
  T0=$(date +%s.%N)
  bash "$RENDER" --pinned "$PIN" > "$SAID" 2>&1; RX=$?
  RS=$(python3 -c "print(round($(date +%s.%N) - $T0, 1))")   # the render call's own wall-clock seconds
  tail -3 "$SAID" | cut -c1-240
  echo "RENDER: $RENDER --pinned $PIN exit $RX ($RS s)"
  python3 -B tests/package/outcomes.py --render "$(basename "$D")" "$RX" "$PIN" "$SAID" "$RS"   # the build's one line
  rm -f "$SAID"
  git add data/builds/outcomes.jsonl && git commit -q -m "pp-selectid build $N ($BUILD_ID): the render call, exit $RX" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git push -q origin "$(git rev-parse --abbrev-ref HEAD)" 2>&1 | tail -2
done
