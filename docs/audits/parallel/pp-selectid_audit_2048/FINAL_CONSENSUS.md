# pp-selectid audit 2048: final consensus (2 cycles)

- **Cycle 2, grok:** "SHIP: yes". No P0 or P1. One P2.
- **Cycle 2, qwen:** "SHIP: yes with conditions". No P0 or P1. Three P2s, plus two checks.
- **glm-5.3-flash:** its cycle-1 answer came at 801 s, at 21:02, after cycle 2 had started, and was cut at its
  24,000-token budget (finish=length). It was not asked in cycle 2. Cycle 2 rests on grok (xAI) and qwen
  (Heimdall): two vendors, two families. glm's cycle-1 points are read below.

## glm cycle 1 (late), read after cycle 2

- **P0:** none ("the core arithmetic and ordering invariants hold").
- Most of its numbered "P1"s end in its own "verified" or a check mark. The rest:
  - **P1-23 (a filler in an EQUAL span dropped, making a phantom difference):** refuted. attest.diff returns only
    the non-equal opcodes (`if o[0] != "equal"`), so `drop` holds only fillers inside differences. A test now pins
    it: "so, um, yes" against "so um yes" gives no difference, and "so, um, the" against "so um a" gives exactly
    the one function word. This is a test-only addition after cycle 2.
  - **P1-12 (ruling 67's re-seal tool passes its own run_rule):** refuted. tests/package/reseal_attested.py never
    calls lock_precheck.attested; it builds its own record.
  - **P1-11 / P1-29 (spoken "um" against approved "the" leaves a drop of "the"):** this is the integrator's own
    procedure too. Fillers are dropped from the second recogniser's side, and what is left is a pure drop judged by
    ruling 67's class (rule 5). Both sides agree.
  - **P1-15 (filler entries listed before the other differences):** cosmetic. The record lists every difference
    with its class.
  - **P1-36 (on_abandon raising):** this is grok's cycle-1 P2, already fixed: the log comes first, then the call
    stops on SpendLimit.

## Cycle 1 items, after the fixes

Both cycle-2 reviewers confirm:
- the missed-deadline line is written before the booking (grok's cycle-1 P2);
- the late ledger write is one atomic method, and its failure goes on record (qwen's P1-4);
- qwen's cycle-1 P0s are refuted. qwen withdraws them in its own cycle-2 text.

## Cycle 2 P2s

- **grok P2, providers.py:273 (a drift between the booked value and prompt_usd):** refuted. _late never recomputes
  the booking. It reads `ab["usd"]`, the exact value abandon() passed to _settle. A later change to prompt_usd cannot
  make the two differ.
- **qwen P2-1 (clamp usd_unreported_estimate at 0):** refuted. The subtraction and the addition are in ONE
  _replace_booking under the ledger lock, with one _save at the end, so no intermediate value is ever written or
  read. A clamp would silently change the total whenever the arithmetic went wrong, which is the opposite of fail
  closed. The tests pin the end values exactly.
- **qwen P2-2 (on_late errors outside the ledger are dropped):** recorded. Router._log_slow already turns a write
  failure into a notice (it never raises). abandon() always builds the record fields _late reads. What remains is a
  programming error in a thread nobody can catch. The booking stands either way.
- **qwen P2-3 (`one += k is not None`):** style. Left as is, because the behaviour is pinned by tests and nothing
  changes after cycle 2 except the condition below.

## Conditions

- **The DECODER constant (qwen's check 2).** It is applied as the integrator's live value when its ruling-84 change is
  live, in pipeline/lock_precheck.py only (the comment and the 12-hex value). Nothing else changes after cycle 2. The
  final diff is FINAL_STEP.diff.
- **The log before _settle in abandon() (qwen's check 3):** present in the final diff.
- **Applied after cycle 2 (21:14 ET):** DECODER = "962353613cb0", from the integrator's 21:13 message (ea426cb9,
  pushed; the full sha 962353613cb0e065008ab0405ca8550111ddd3ca3ba70f0ae65b4b77ab1876d8). It matches the sha computed
  read-only from the main tree's CODE files. Two tests pin the result-file name, and now name 962353613cb0. The
  old-decoder test now also refuses 8a101f222598's file. lock_precheck 17 OK; regression 26 PASS, 0 FAIL.

## Verdict

SHIP. The consensus fixes are implemented. Every other finding is refuted or recorded with the evidence above.

## Suites

All 15 OK on the fixed code (455 tests; providers 20, attest 10 with glm's equal-span check, lock_precheck 17,
medley 160).
