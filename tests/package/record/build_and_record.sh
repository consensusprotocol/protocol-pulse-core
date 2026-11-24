#!/bin/bash
# THE BUILD LAUNCHER (in git since the verifier's rows 12 / 16, Nov 24; it was a scratch script). One build, routine or
# an ORDER 17:50 attempt; STATE line 1 from the build's own log and record (times and counts from the records, never
# typed); commit the build's record (never a lock, the health, judge_requests, BREAKERS or DEADLINE_TABLE files) with
# its pin when it sealed, and its outcome line (RULING 160 (2b): data/builds/outcomes.jsonl); push (a plain push).
#  - It runs ONE driver: tests/package/proof_ledger.py. There is no override (builds 166-168 ran by-hand wrappers
#    through a DRIVER= variable); the driver itself refuses any other entry point and records its entry.
#  - routine (on a ledger change): marks the watcher's baseline BEFORE the build.
#  - an attempt (--only FILE [--stop-usd X], ORDER 17:50 ET Nov 16): one candidate set; no mark; the set is kept in the
#    record as ONLY.json; line 1 says what was tried, what stopped it, dollars.
#  - ORDER 17:50 (3) guard: once the day ledger is no longer SPEND_B4.json (21:10 ET Nov 16), or the day's spend has
#    reached $1.00 (ORDER 19:28's 25 cents), a build given no --stop-usd gets the day's spend + $0.001 (free screens
#    only: no paid call fits), and says so.
#  - refuses while the render lock is held or another build is running.
# Usage: bash tests/package/record/build_and_record.sh N "WHY" [--only FILE] [--stop-usd X]
set -u
R=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)           # tests/package/record
W=$(cd "$R/../../.." && pwd)                               # the repo
DRIVER=tests/package/proof_ledger.py                       # the only driver (verifier row 16)
N=$1; WHY=$2; shift 2
EXTRA=("$@")
cd "$W" || exit 2
LK=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c 'pulse_check_run.lock')
if [ "$LK" != "0" ]; then echo "render lock held: no build, no commit"; exit 3; fi
RUN=$(ps -eo args= | awk -v d="$DRIVER" '$1 ~ /python3$/ && $3 == d' | wc -l)
if [ "$RUN" != "0" ]; then echo "another build is running ($RUN process): no build"; exit 3; fi
ONLY=""; STOP=""
for ((i=0; i<${#EXTRA[@]}; i++)); do
  case "${EXTRA[$i]}" in
    --only) ONLY="${EXTRA[$((i+1))]}";;
    --stop-usd) STOP="${EXTRA[$((i+1))]}";;
  esac
done
read SP LED <<< "$(python3 -B "$R/day_spent.py")"
OVER=$(python3 -c "print(1 if $SP >= 1.0 else 0)")
if [ -z "$STOP" ] && { [ "$LED" != "SPEND_B4.json" ] || [ "$OVER" = "1" ]; }; then
  STOP=$(python3 -c "print(f'{$SP + 0.001:.6f}')")
  EXTRA+=(--stop-usd "$STOP")
  WHY="$WHY; free screens only (ORDER 17:50 (3): --stop-usd $STOP, the day's spend + \$0.001)"
fi
LOCKARG=0; for x in "${EXTRA[@]}"; do [ "$x" = "--lock-precheck" ] && LOCKARG=1; done
if [ "$LOCKARG" = "0" ]; then EXTRA+=(--lock-precheck "${LOCK:-off}"); fi   # RULING 130 (2): no Scribe until released
echo "day ledger $LED, spend before \$$SP, stop ${STOP:-none given: the ledger limit}, lock pre-check ${LOCK:-off}"
if [ -z "$ONLY" ]; then python3 -B "$R/watch_ledger.py" --mark 2>&1 | tail -1; fi
T=$(date '+%H%M')
LOGS=$W/tests/package/proof/logs                          # *.log: never committed (.gitignore)
mkdir -p "$LOGS"
LOG=$LOGS/build${N}_$T.log
timeout 9000 python3 -B $DRIVER --build-no "$N" --routing heimdall_first --since 2026-11-13T03:01:09Z --delivered tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json tests/package/proof/fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json tests/package/proof/ledger_20261113_073738/MOMENTS_PIN_LEDGER.json tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json tests/package/proof/ledger_20261113_215708/MOMENTS_PIN_LEDGER.json "${EXTRA[@]}" > "$LOG" 2>&1
X=$?
echo "build exit $X"
grep "^no package\|^NOTHING NEW\|spend (ruling 48)\|PACKAGE\|READY\|RULING 76 (d)\|RESERVE BACK\|ORDER 17:50\|^REFUSED\|RULING 160 (2b)" "$LOG" | head -9 | cut -c1-240
if [ "$X" = "2" ]; then echo "REFUSED: no record, no STATE line, no commit"; tail -3 "$LOG" | cut -c1-300; exit 5; fi
D=$(ls -td tests/package/proof/ledger_20* | head -1)
B=$(python3 -B "$R/day118.py" 2>&1 | tail -1)
SC=$(python3 -B "$R/scorer_stale.py" 2>&1 | tail -1)      # ruling 132: a dead scorer shows on line 1 within one build
BT=$(date -r "$D" '+%H:%M'); T2=$(date '+%H:%M')
RES=$(grep -o "^no package ([^)]*)\|^NOTHING NEW[^:]*\|PACKAGE[^;]*" "$LOG" | head -1 | cut -c1-200)
NE=$(python3 -B -c "import json,sys; r=json.load(open(sys.argv[1]+'/package.json')); ne=r.get('never_empty') or {}; print('' if r.get('package') or not ne.get('soft_why_none') else 'THE NEVER-EMPTY PASS (the one that decides): ' + str(ne['soft_why_none'])[:420])" "$D" 2>/dev/null)
[ -n "$NE" ] && RES="the clean pass: ${RES:-?}; $NE"     # build 149 / 150: line 1 quoted only the clean pass's reason
OUT=$(grep -o "RULING 160 (2b): outcome [A-Z_]* at [^:]*" "$LOG" | tail -1)   # the build's one outcome line
R76=$(grep -o "RULING 76 (d): [^;]*" "$LOG" | head -1 | cut -c1-110)
H=$(grep -o "HELD for this build[^:]*: [0-9]* at step A" "$LOG" | grep -o "[0-9]* at step A" | head -1)
DOL=$(grep -o "spend (ruling 48): [^ ]* of \$[0-9.]* vendor-reported after this build (before it: \$[0-9.]*)" "$LOG" | tail -1)
TXT=$(mktemp "$LOGS/state_b${N}_XXXXXX.txt")
if [ -n "$ONLY" ]; then
  cp "$ONLY" "$D/ONLY.json"
  SUM=$(python3 -B "$R/attempt_summary.py" "$D" 2>&1 | tail -1 | cut -c1-900)
  printf '%s\n' "{T} ET: $B ORDER 17:50 ATTEMPT, BUILD $N ($(basename "$D"), $BT ET). TRIED: $WHY. ${SUM}. RESULT: ${RES:-?}; ${OUT:-RULING 160 (2b): no outcome line}; held at Grok's first screen: ${H:-none}.${SC:+ $SC} DOLLARS: ${DOL:-?} (this build's stop \$${STOP:-1.00})." > "$TXT"
else
  printf '%s\n' "{T} ET: $B BUILD $N ($(basename "$D"), $BT ET; $WHY): ${RES:-?}; ${OUT:-RULING 160 (2b): no outcome line}; ${R76:-?}; held at Grok's first screen: ${H:-none}.${SC:+ $SC}" > "$TXT"
fi
python3 -B "$R/state_line.py" "$T2" "$TXT"
rm -f "$TXT"
LK=$(ls -l /proc/[0-9]*/fd 2>/dev/null | grep -c 'pulse_check_run.lock')
if [ "$LK" != "0" ]; then echo "render lock held: no commit"; exit 3; fi
for f in "$D/FINGERPRINT.json" "$D/inputs.json" "$D/package.json" "$D/SHADOW86.md" "$D/step_a.json" "$D/NOTHING_NEW.json" "$D/ONLY.json" "$D/MOMENTS_PIN_LEDGER.json" "$D/SPOTLIGHT_PIN.json"; do [ -f "$f" ] && git add "$f"; done
for f in "$D/MOMENTS_PIN_LEDGER.json" "$D/SPOTLIGHT_PIN.json"; do [ -f "$f" ] && echo "PIN WRITTEN: $f: PIN IT TO THE INTEGRATOR NOW (ruling 106)"; done
git add docs/audits/parallel/pp-selectid_STATE.md tests/package/proof/DAY118_LEDGER.json
[ -f data/builds/outcomes.jsonl ] && git add data/builds/outcomes.jsonl          # RULING 160 (2b): the build's line
[ -f tests/package/proof/FLAGGED_DAY.json ] && git add tests/package/proof/FLAGGED_DAY.json   # ruling 136 (2): the day count
for f in docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.jsonl docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json tests/package/proof/CANDIDATES.json tests/package/proof/HOOK_CACHE.json tests/package/proof/JOIN_CACHE.json tests/package/proof/STEP_A_CACHE.json tests/package/proof/VISUAL_CACHE.json tests/package/proof/SPEND_B4.json tests/package/proof/SPEND_D*.json; do [ -f "$f" ] && { git diff --quiet -- "$f" 2>/dev/null && git ls-files --error-unmatch "$f" >/dev/null 2>&1 || git add "$f"; }; done
git ls-files --others --exclude-standard tests/package/fixtures/replies | xargs -r git add
if git diff --cached --name-only | grep -qE "\.lock$|HEIMDALL_HEALTH|judge_requests|BREAKERS|DEADLINE_TABLE"; then echo "FORBIDDEN STAGED: stopping"; exit 4; fi
git commit -q -m "pp-selectid build $N ($(basename "$D"), $BT ET): $WHY" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" && git log -1 --oneline | cut -c1-90
git push -q origin pp-selectid 2>&1 | tail -2
git status -sb | head -1
