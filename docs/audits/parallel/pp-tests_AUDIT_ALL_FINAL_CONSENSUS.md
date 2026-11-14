# CONSENSUS REPORT — PP-TESTS_AUDIT_ALL — CYCLE 2
Generated: 2026-11-12 02:24
Models: gpt4o, gemini (+1 failed — Grok-3 budget exceeded)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok | Consensus |
|-----------------|--------|--------|------|-----------|
| Backend logic   | 95/100 | 88/100 | N/A  | **92/100** |
| Frontend/UI     | N/A    | N/A    | N/A  | **N/A**    |
| Error handling  | 70/100 | 85/100 | N/A  | **75/100** |
| Security        | 95/100 | 90/100 | N/A  | **93/100** |
| Performance     | 90/100 | 85/100 | N/A  | **88/100** |
| Law compliance  | 100/100| 100/100| N/A  | **100/100**|
| World-class gap | 90/100 | 87/100 | N/A  | **89/100** |
| **OVERALL**     | **90/100** | **90/100** | N/A | **90/100** |

> **Note on Error Handling divergence:** Gemini's 70/100 is the more credible score. GPT-4o's 85/100 reflects relative leniency after a weaker Cycle 1 baseline. Gemini correctly weighted the fact that the `call_gate` flaw was flagged in Cycle 1, explicitly surfaced again, and still not fixed — a process failure that amplifies the technical risk. Consensus skews toward Gemini's harsher assessment.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U-1 · Overly broad exception handling in `call_gate`
**File:** `tests/adversarial/test_f4_vacuity.py:1947–1956` (approximately line 1951)

**What it is:** The `call_gate` helper wraps a gate invocation in a bare `except Exception:` and returns `RAISED`. This is the right intent for catching expected application-level gate errors, but `Exception` is too broad — it also catches `MemoryError`, `RecursionError`, unexpected `AttributeError` from bugs in the test harness itself, and any other non-trivial system condition. The result is that a catastrophic failure in the code under test (or in the test fixture) silently becomes an ordinary `RAISED` verdict, which can then cause a vacuity test to pass when it absolutely should not.

**What to change:**
```python
# BEFORE (dangerous)
try:
    result = gate(...)
except Exception:
    return RAISED

# AFTER (safe)
_EXPECTED_GATE_EXCEPTIONS = (ValueError, TypeError, KeyError, LookupError)
try:
    result = gate(...)
except _EXPECTED_GATE_EXCEPTIONS:
    return RAISED
# All other exceptions (MemoryError, SystemError, bugs, etc.) propagate
# and crash the test run as intended.
```
If the codebase genuinely raises broader exceptions from gates, enumerate them explicitly. Never use a bare `except Exception` in a test harness.

**Why both models flagged this:** A test suite that can silently swallow its own catastrophic failures is not trustworthy. The harness must be held to a *higher* reliability standard than the code it tests.

---

### U-2 · Near-total absence of structured logging
**Files:** `tests/adversarial/adv_helpers.py` (all subprocess call sites), `tests/adversarial/test_f4_vacuity.py`, fixture setup code

**What it is:** The suite is architecturally sophisticated, with complex synthetic media construction, multi-step fixture chains, subprocess invocations with timeouts, and layered gate logic. When any of this breaks, the developer is completely blind. There is no logging at: subprocess call entry/exit, fixture setup success/failure, gate entry/exit, unexpected `RAISED` returns, or timeout expirations.

**What to change:**
- Add a module-level logger to `adv_helpers.py` using the standard `logging` module (not `print`).
- Log at `DEBUG` level: subprocess command, cwd, timeout value before each call.
- Log at `DEBUG` level: subprocess return code and stdout/stderr snippet (first 500 chars) after each call.
- Log at `WARNING` level: any `RAISED` result from `call_gate`, including the exception type (even if caught).
- Log at `INFO` level: fixture setup completion for session-scoped expensive operations (media generation).
- Wire to pytest's logging capture so logs appear in `--log-cli` output without polluting normal runs.

```python
import logging
log = logging.getLogger(__name__)

# In call_gate:
except _EXPECTED_GATE_EXCEPTIONS as exc:
    log.warning("call_gate: gate %r raised %s: %s", gate, type(exc).__name__, exc)
    return RAISED
```

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings. No additional majority findings emerged beyond U-1 and U-2 that do not rise to unanimous status.

> With only two functioning models, every agreement is by definition unanimous. The majority tier is collapsed into the unanimous tier for this cycle.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 · Fragile global cache `_FINALS` (Gemini only)
**File:** `tests/adversarial/adv_helpers.py:541–554`

**What it is:** A module-level global dict `_FINALS` is used to cache generated synthetic media across test calls. This achieves the desired session-scoped performance benefit but via a fragile pattern — global mutable state that is invisible to pytest's fixture dependency tracking, cannot be reset between test sessions without a process restart, and can produce subtle cross-test contamination if any consumer modifies the cached objects.

**Assessment: Implement.** Refactoring to a `pytest` session-scoped fixture is strictly superior and idiomatic:
```python
@pytest.fixture(scope="session")
def finals_cache():
    """Session-scoped synthetic media cache. Replaces _FINALS global."""
    cache = {}
    yield cache
    # Optional: cleanup hook here
```
This is a P2 item — it doesn't break anything today, but it is technical debt that will bite during future debugging or parallelization. The refactor is mechanical and low-risk.

**Risk if skipped:** Low immediate risk. Medium long-term maintainability risk, especially if `pytest-xdist` is ever introduced for parallel test execution (globals are not safe across worker processes).

---

### UI-2 · Process failure — unanimous Cycle 1 findings not addressed (Gemini only)
**What it is:** Gemini observed that the developer's `pp-tests_AUDIT_RESPONSE.md` shows engagement with some prior feedback (e.g., promoting `NetworkBlocked` to `BaseException`) but explicit non-action on the two highest-priority unanimous findings (U-1, U-2). Gemini flags this as a process red flag, not merely a code issue.

**Assessment: Investigate further.** This is an important meta-observation. The correct response is not to override the developer's judgment, but to ensure the audit-to-action loop is clearly documented. If U-1 and U-2 were consciously deferred, that decision should be recorded with rationale. If they fell through the cracks, the triage process needs a gate that explicitly requires acknowledgment of P0/P1 findings before merge. This consensus report itself serves as that gate for this cycle.

---

### UI-3 · CI integration gap (GPT-4o only)
**What it is:** GPT-4o noted the absence of a documented CI configuration that runs the adversarial suite automatically on PRs.

**Assessment: Implement, but out of scope for this audit pass.** The suite documents "one command, under 5 minutes on CPU" (lines 2880–2891), which is a CI-ready contract. The actual CI YAML wiring is infrastructure work outside the test code. Flag it as a follow-up ticket but do not block this merge on it.

---

## CONFLICTS (models disagree — tiebreaker)

### C-1 · Error handling score: Gemini 70/100 vs GPT-4o 85/100

**Tiebreaker: Gemini is correct.**

GPT-4o's 85/100 reflects the absolute quality of the exception handling construct (it *mostly* works, it *mostly* catches the right things). Gemini's 70/100 correctly weights two additional factors that GPT-4o underweighted:
1. A test harness is held to a higher reliability standard than production code. A silent failure mode in the harness is proportionally more severe than the same flaw in a service.
2. The finding was raised in Cycle 1, explicitly acknowledged in the audit response, and not fixed. The score should reflect the residual risk of a *known unfixed defect*, not the initial discovery.

Consensus: **75/100** (split the difference, but closer to Gemini).

### C-2 · Overall score: Gemini 90/100 (down from 91) vs GPT-4o 90/100 (up from 88)

**No meaningful conflict.** Both models converged to 90/100 via different paths. This is genuine consensus.

---

## VALIDATED STRENGTHS (all models agree — do NOT touch)

The following elements were praised by both models. They are correct, clever, and battle-tested. Leave them alone.

1. **`NetworkBlocked(BaseException)` in `conftest.py`** — Subclassing `BaseException` rather than `Exception` correctly prevents production `except Exception:` clauses in the code under test from accidentally swallowing the network block signal. Brilliant and correct.

2. **End-of-session `nvidia-smi` check** — Defense-in-depth CPU enforcement. Any CUDA activity during the session would leave detectable evidence. Keep as-is.

3. **Rich synthetic data generation in `adv_helpers.py`** — The `gen_cases` function, `TEEN_TY` swaps, `ACTOR_SWAPS`, and the full surface-variant × meaning-mutant matrix are architecturally excellent. The domain-specific test cases (Fed vs. Treasury, 16 vs. 60) reflect genuine production failure modes.

4. **`pytest.fail` for control/precondition failures** — Using `pytest.fail` (not `assert`) for fixture setup and control assertions ensures that a broken test fixture surfaces as `FAIL`/`ERROR`, not as a masked `xfail`. This is subtle, important, and correct.

5. **Multi-layered environment guards** — The triple guard (CUDA blocked, network blocked, Whisper model loading blocked) is a mature, production-grade test isolation strategy.

6. **Mutation testing for auth (Family 3)** — The exhaustive mutation coverage of release authorization (PASS waived, digest of different file, file swap during delivery, cross-run attestation reuse) is world-class adversarial thinking.

7. **Settlement of the "G8 9:16 failure" open claim (Family 5)** — Using tests to provide definitive, evidence-based answers to open questions in the requirements is exactly how mature engineering teams should operate.

8. **`xfail` precision for known bugs** — Pinning known idempotence bugs (e.g., `test_idempotent_on_adjacent_spoken_numbers`) with strict `xfail` rather than skipping them is the correct way to track known defects without hiding them.

---

## LAW COMPLIANCE CONSENSUS

**Final determination: FULLY COMPLIANT on all stated laws.**

| Law | Status | Evidence |
|-----|--------|----------|
| TESTS ONLY | ✅ COMPLIANT | No production files modified |
| CPU ONLY | ✅ COMPLIANT | CUDA blocked in conftest; nvidia-smi end-of-session check |
| Real public entry points | ✅ COMPLIANT | All tests exercise public APIs |
| Every test passes or strict xfail | ✅ COMPLIANT | Verified by both models |
| Genuine-pass AND must-fail in every family | ✅ COMPLIANT | Both polarities present in all 5 families |
| Nothing measured is never a pass (L-m) | ✅ COMPLIANT | Family 4 specifically enforces this |
| Fail closed | ✅ COMPLIANT | Unauthorized releases blocked |
| Never change what a check accepts | ✅ COMPLIANT | Tests expose defects without altering acceptance criteria |
| One command, under 5 minutes CPU | ✅ COMPLIANT | Documented at lines 2880–2891 |

Both models awarded 100/100 for law compliance. This score stands.

---

## SECURITY CONSENSUS

No security vulnerabilities were identified by either model. The relevant security observations are:

1. **No secrets in code** — Confirmed by both models. ✅
2. **No SQL injection surface** — Not applicable; no DB interaction. ✅
3. **No authentication bypass** — Not applicable in test code. ✅
4. **Subprocess calls have timeouts** — Correctly implemented at lines 389, 641, 998. ✅
5. **Test isolation from GPU/network** — The sandbox is unusually robust for a test suite. ✅

**Security consensus: No action required.** The operational security of the test environment (sandboxing from real infrastructure) is a genuine strength.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2 models only:

| Gap | Models | Assessment |
|-----|--------|-----------|
| Overly broad exception handling in `call_gate` | Both | P0 — Directly prevents "world-class" reliability of the harness itself |
| Absence of structured logging | Both | P1 — World-class test suites are self-documenting on failure |

Items mentioned by 1 model (included for completeness but below the 2-model threshold for this section):
- Global cache pattern (`_FINALS`) — Gemini only. Valid but minor.
- CI integration — GPT-4o only. Infrastructure concern, not code quality.

**Combined verdict:** The design and coverage are genuinely world-class. The two unanimous gaps are the only things standing between "exceptional" and "world-class." Fixing them is fast work (hours, not days) and would push this suite into the top tier of adversarial test infrastructure.

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Narrow exception handling in call_gate from bare `except Exception`
            | to an explicit tuple of expected application-level exceptions;
            | allow all system/unexpected exceptions to propagate and crash the
            | test run. Log caught exceptions at WARNING level before returning RAISED.
            | File: tests/adversarial/test_f4_vacuity.py:1951
            | Models: BOTH (unanimous, flagged in Cycle 1, still unaddressed)
            | Why: A test harness that silently swallows catastrophic failures
            |      cannot be trusted. This is the single highest-risk defect.

P1 HIGH     | Add structured logging (stdlib `logging`, not print) at key points:
            | subprocess entry/exit with command+returncode+stderr snippet,
            | gate entry/exit with verdict, RAISED captures with exception type,
            | session-scoped fixture setup completion. Wire to pytest log capture.
            | Files: tests/adversarial/adv_helpers.py (all subprocess sites),
            |        tests/adversarial/test_f4_vacuity.py (call_gate, _cases)
            | Models: BOTH (unanimous, flagged in Cycle 1, still unaddressed)
            | Why: Suite complexity without logging makes failures undiagnosable
            |      in CI. This is a maintenance time-bomb.

P2 MEDIUM   | Replace `_FINALS` global dict cache with a pytest session-scoped
            | fixture. Eliminates global mutable state, improves idiomatic
            | correctness, and future-proofs against pytest-xdist parallelization.
            | File: tests/adversarial/adv_helpers.py:541-554
            | Models: Gemini only (unique insight, well-reasoned)
            | Why: Low immediate risk, meaningful long-term maintainability gain.
            |      Mechanical refactor, low regression risk.

P3 LOW      | Document the CI integration contract (which command, which runner
            | spec, expected wall-clock time) in a CI YAML or README addendum.
            | The "one command, under 5 minutes" law is stated but not wired.
            | Files: CI configuration / README
            | Models: GPT-4o only
            | Why: Infrastructure work, out of scope for this code pass.
            |      Track as separate ticket.
```

---

## CYCLE 2 VERDICT

**Production-ready: YES, with two non-negotiable conditions.**

The test suite is architecturally exceptional — among the best adversarial test suite designs either model had encountered. The five-family structure, the law-to-test mapping, the multi-layered environment sandboxing, and the mutation-testing approach to auth verification are all production-grade and beyond.

**The absolute final blockers are:**

1. **P0 — `call_gate` exception handling** must be fixed before this suite is used as a gate for production releases. A release gate enforced by a test harness that might silently swallow its own failures is not a gate — it's a false sense of security. This is a one-hour fix.

2. **P1 — Structured logging** must be added before this suite is handed to any engineer other than its author. The fix is a few hours of work. Without it, the first time this suite fails in CI on a build agent, the responsible engineer will have no actionable signal.

**These two items were flagged unanimously in Cycle 1. They remain unaddressed. They are the only things between this suite and an unconditional production sign-off.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_audit_ALL_CONSENSUS_C2.md.

This is the FINAL PASS for pp-tests_audit_ALL.
The suite was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Narrow exception handling in call_gate
            | File: tests/adversarial/test_f4_vacuity.py:1951
            | Change: Replace bare `except Exception:` with an explicit tuple
            | of expected application-level gate exceptions (enumerate from the
            | actual gate implementations — ValueError, TypeError, LookupError,
            | KeyError, or whatever the gates actually raise). Add a WARNING-level
            | log line inside the except clause capturing exception type and message
            | before returning RAISED. All other exceptions must propagate freely
            | and crash the test run. Do NOT use except BaseException.

P1 HIGH     | Add structured logging throughout the adversarial test helpers
            | Files: tests/adversarial/adv_helpers.py,
            |        tests/adversarial/test_f4_vacuity.py
            | Change: Add `log = logging.getLogger(__name__)` at module level.
            | Log DEBUG before/after every subprocess call (command, cwd, timeout,
            | returncode, first 500 chars of stderr). Log WARNING on every RAISED
            | return from call_gate (exception type + message). Log INFO on
            | session-scoped fixture setup completion (synthetic media generation).
            | Use pytest's built-in log capture — do not add any log handlers;
            | just emit via the standard logger.

P2 MEDIUM   | Replace _FINALS global dict with a pytest session-scoped fixture
            | File: tests/adversarial/adv_helpers.py:541-554
            | Change: Convert _FINALS dict and _finals() function into a
            | session-scoped pytest fixture. Update all callers that currently
            | call _finals() to accept the fixture via dependency injection.
            | Verify the refactor does not change observable test behavior.

VALIDATED — do NOT touch (all models confirmed excellent):
- NetworkBlocked(BaseException) subclass in conftest.py — keep exactly as-is
- End-of-session nvidia-smi check — keep exactly as-is
- gen_cases() / TEEN_TY / ACTOR_SWAPS synthetic data generation — keep exactly as-is
- pytest.fail() usage for control/precondition assertions — keep exactly as-is
- All five test family structures and their xfail annotations — keep exactly as-is
- Multi-layered environment guards (CUDA + network + Whisper) — keep exactly as-is
- Family 3 auth mutation coverage — keep exactly as-is
- Family 4 vacuity defense-in-depth pattern — keep exactly as-is
- Family 5 open-claim settlement methodology — keep exactly as-is
- All subprocess timeout implementations at lines 389, 641, 998 — keep exactly as-is

After implementing all P0 and P1 items (and P2 at your discretion):
1. Run the full adversarial suite: bash regression_test.sh
2. Confirm zero FAILs and zero ERRORs
3. Confirm all existing xfail tests still xfail (not unexpectedly passing)
4. Confirm the new logging appears correctly under: pytest --log-cli-level=DEBUG
5. Confirm that a manually injected MemoryError inside a gate now propagates
   as a test ERROR rather than being swallowed as RAISED

git add -A && git commit -m "feat(pp-tests_audit_ALL): post-audit pass — consensus improvements

- P0: Narrow call_gate exception handling; log caught exceptions
- P1: Add structured logging to adv_helpers and test_f4_vacuity
- P2: Replace _FINALS global cache with session-scoped fixture

Addresses unanimous C1+C2 findings from pp-tests_audit_ALL_CONSENSUS_C2.
All validated strengths preserved unchanged."

git push origin pp-tests
```

---

# WINNER DETERMINATION

# WINNER: Gemini

Gemini delivered consistently superior depth across both cycles — it identified the `call_gate` exception-handling flaw with precise technical reasoning (distinguishing application-level errors from system-level exceptions), mapped test families to specific compliance laws systematically, and in Cycle 2 correctly escalated the severity of U-1 because it remained unaddressed, demonstrating analytical continuity rather than simply re-summarizing. While GPT-4o was accurate and well-structured, its Cycle 1 baseline was shallower and its Cycle 2 leniency on error handling (85/100 vs Gemini's credible 70/100) reflects a weaker calibration to process risk.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by severity × exploitability × implementation cost (lowest cost, highest severity first).

---

## P0 — Fix Immediately (blocks trust in the test suite)

### P0-1 · Narrow the `except` clause in `call_gate`
**File:** `tests/adversarial/test_f4_vacuity.py:1947–1956`
**Why P0:** A system-level exception (MemoryError, RecursionError, AttributeError from a fixture bug) silently becomes a `RAISED` verdict, potentially causing a vacuity test to pass when the code under test has catastrophically failed. The suite's integrity guarantee collapses.

```python
# BEFORE
try:
    result = gate_fn(*args, **kwargs)
except Exception:
    return RAISED

# AFTER
_HARNESS_BUGS = (AttributeError, TypeError, NameError)  # always re-raise
_SYSTEM_ERRORS = (MemoryError, RecursionError, SystemExit, KeyboardInterrupt)

try:
    result = gate_fn(*args, **kwargs)
except (*_SYSTEM_ERRORS, *_HARNESS_BUGS):
    raise  # never swallow; crash the test visibly
except Exception:
    return RAISED  # legitimate application-level gate rejection
```

**Acceptance criterion:** Inject a `raise MemoryError("synthetic")` inside a gate stub; confirm pytest reports `ERROR`, not a passing vacuity test.

---

## P1 — Implement Before Next Release Cycle

### P1-1 · Replace hardcoded reference root path with validated env-var resolution
**File:** `tests/adversarial/adv_helpers.py` (reference root construction)
**Why P1:** Hardcoded paths cause silent wrong-directory resolution on any non-standard CI runner, producing false passes against stale fixtures.

```python
# AFTER
import os, pathlib

def _reference_root() -> pathlib.Path:
    raw = os.environ.get("ADV_REFERENCE_ROOT")
    if not raw:
        raise EnvironmentError(
            "ADV_REFERENCE_ROOT must be set. "
            "See docs/test_environment.md for setup instructions."
        )
    p = pathlib.Path(raw).resolve()
    if not p.is_dir():
        raise EnvironmentError(f"ADV_REFERENCE_ROOT={p!r} is not a directory.")
    return p
```

**Acceptance criterion:** Unset `ADV_REFERENCE_ROOT`; confirm suite fails with the descriptive error above, not a silent wrong-path resolution.

---

### P1-2 · Add vacuity guards — gates must reject empty / trivially short inputs
**File:** `tests/adversarial/test_f4_vacuity.py`
**Why P1:** If a gate returns `PASS` on a zero-length or single-token input, every downstream test that depends on that gate's verdict is built on a false foundation.

```python
@pytest.mark.parametrize("empty_input", [
    "",
    "   ",
    ".",
    "a",          # single token
    "\n" * 50,    # whitespace-only bulk
])
def test_gate_rejects_vacuous_input(empty_input):
    result = call_gate(production_gate, empty_input)
    assert result != PASS, (
        f"Gate returned PASS on vacuous input {empty_input!r}; "
        "gate is not making a genuine decision."
    )
```

**Acceptance criterion:** Each parametrized case must either return `RAISED` or a non-PASS verdict. Any PASS fails the test.

---

## P2 — Implement Within Current Sprint

### P2-1 · Add structured failure logging to `call_gate` and family runners
**Why P2:** With zero logging, diagnosing which fixture, which variant, and which gate produced an unexpected verdict requires manual re-execution with print statements. At the suite's current scale, this is unsustainable.

```python
import logging
_LOG = logging.getLogger("adv_harness")

try:
    result = gate_fn(*args, **kwargs)
except (*_SYSTEM_ERRORS, *_HARNESS_BUGS):
    _LOG.critical(
        "Harness-level exception in call_gate",
        exc_info=True,
        extra={"gate": gate_fn.__name__, "args_repr": repr(args)[:200]},
    )
    raise
except Exception as exc:
    _LOG.debug("Gate raised (expected path): %s — %r", gate_fn.__name__, exc)
    return RAISED
```

**Acceptance criterion:** Run suite with `--log-cli-level=DEBUG`; confirm every `RAISED` verdict produces a log line with gate name and truncated input repr.

---

### P2-2 · Pin CI execution budget with a hard timeout per test family
**Why P2:** "Under 5 minutes on CPU" is documented but not enforced. A regression that causes a family to hang will block CI indefinitely.

```ini
# pytest.ini or pyproject.toml [tool.pytest.ini_options]
timeout = 280          # 280 s hard wall for entire session
timeout_method = thread

# Per slow family (marker-based):
# @pytest.mark.timeout(60)  on each family's module-level fixture
```

**Acceptance criterion:** Inject a `time.sleep(400)` in one test; confirm pytest reports `TIMEOUT ERROR` within 300 seconds.

---

## P3 — Backlog (quality-of-life, non-blocking)

### P3-1 · Document the Law-to-test mapping in a machine-readable index
**Why:** Gemini's review had to reconstruct the L-a/L-b/L-j mapping manually. A `compliance_index.yaml` that maps each law identifier to the test file, class, and parametrize ID makes compliance audits instant and prevents drift.

```yaml
# compliance_index.yaml
- law: L-a
  description: "CPU only — no GPU"
  tests:
    - file: tests/adversarial/conftest.py
      marker: session-scoped nvidia-smi check
- law: L-m
  description: "Fail closed on missing references"
  tests:
    - file: tests/adversarial/test_f2_provenance.py
      ids: ["test_missing_ref_fails[*]"]
```

---

### P3-2 · Convert `xfail` pins to issue-tracker references
**Why:** `test_idempotent_on_adjacent_spoken_numbers` and similar pinned xfails carry no traceability. When the bug is fixed the xfail silently becomes an `XPASS` and may be ignored.

```python
# BEFORE
@pytest.mark.xfail(reason="known idempotence bug")

# AFTER
@pytest.mark.xfail(
    reason="canon.py idempotence failure on adjacent spoken numbers — ISSUE-4471",
    strict=True,   # XPASS → hard failure, forces explicit unpin
)
```

---

## Implementation Order Summary

| Priority | Item | Effort | Risk if Skipped |
|----------|------|--------|-----------------|
| P0-1 | Narrow `call_gate` except | 30 min | Suite integrity void |
| P1-1 | Env-var reference root | 1 hour | Silent wrong-fixture passes |
| P1-2 | Vacuity input guards |