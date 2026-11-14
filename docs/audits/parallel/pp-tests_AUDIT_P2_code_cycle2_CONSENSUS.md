# CONSENSUS REPORT — PP-TESTS_MOMENTS_A — CYCLE 2
Generated: 2026-11-12 03:44
Models: gpt4o, gemini (+1 failed — grok budget exceeded)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok   | Consensus |
|-----------------|--------|--------|--------|-----------|
| Backend logic   | 90/100 | 85/100 | N/A    | **88/100** |
| Frontend/UI     | N/A    | N/A    | N/A    | **N/A**    |
| Error handling  | 75/100 | 75/100 | N/A    | **75/100** |
| Security        | 75/100 | 85/100 | N/A    | **80/100** |
| Performance     | 80/100 | 80/100 | N/A    | **80/100** |
| Law compliance  | 90/100 | 90/100 | N/A    | **90/100** |
| World-class gap | 70/100 | 80/100 | N/A    | **75/100** |
| **OVERALL**     | **80** | **85** | N/A    | **82/100** |

> **Note on score divergence (Security):** Gemini downgraded security to 75 after re-weighing the hardcoded absolute path as a severe portability/security issue. GPT-4o upgraded to 85 after acknowledging the same finding. Consensus lands at 80 — the path issue is real and impactful, but the secrets-file-read pattern itself (not embedding keys in source) is correct, keeping the floor above 75.

---

## UNANIMOUS FINDINGS (all 2 models agree — implement unconditionally)

### U1 — Hardcoded absolute filesystem paths
- **What:** Paths like `/home/ultron/protocol_pulse/.env` are embedded in source, making the suite non-portable, non-reproducible on any other machine, and a mild information-disclosure risk (leaks local directory structure).
- **Files/Lines:**
  - `baselines/frontier_blind.py:1601` (secrets/env file path)
  - `corpora/store_extract.py:32` (transcript store root)
- **Fix:** Replace with paths derived from `pathlib.Path(__file__).resolve().parent` chain or from an env var with a sensible relative default (e.g., `os.getenv("PP_ROOT", str(Path(__file__).parents[N]))`). Never embed `/home/<username>/` in committed source.

### U2 — `print()` used throughout instead of structured logging
- **What:** Every diagnostic, progress, and error message uses bare `print()` statements. In a CI/CD environment or when running parallel jobs, this produces unstructured, unseparated noise that is nearly impossible to filter or instrument.
- **Files/Lines:** `moments_exam.py` (multiple), `build_corpora.py` (multiple), `test_moments_gates.py` (multiple)
- **Fix:** Replace with Python `logging` module. Configure a root logger in each entry-point script. Use `logging.getLogger(__name__)` in library modules. This immediately enables level filtering (`--verbose`/`--quiet`), log capture in test assertions, and clean CI output.

---

## MAJORITY FINDINGS (2 of 2 models agree)

All unanimous findings above are also majority findings. The two models with valid output achieved complete agreement on U1 and U2. No additional majority-only (1-of-2) findings exist beyond the unanimous set, since with only two models every shared finding is unanimous by definition.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 — `oracle.py` import-time corpus loading (Gemini)
- **What:** `moments_toy_gates/oracle.py:1490-1492` loads the entire on-disk corpus during module import, not lazily on first call. This slows test discovery, adds unnecessary I/O to every test invocation that merely imports the module, and creates a brittle dependency: if on-disk corpus is stale vs. what the harness would build, the oracle silently uses wrong data.
- **Assessment: IMPLEMENT.** This is a textbook import-time side-effect anti-pattern. Lazy initialization (load on first call, cache thereafter) is a one-line fix with meaningful reliability and performance gains.

### UI-2 — `BaseException` usage for network blocking (Gemini — noted as a strength)
- **What:** `moments_exam.py:991` raises `BaseException` rather than `Exception` to prevent gate code from accidentally swallowing the network-blocking signal with a broad `except Exception`.
- **Assessment: DO NOT CHANGE — this is intentional and correct.** Noted here so the second-pass author does not "fix" it.

### UI-3 — Implicit thread-safety requirement on gate authors (Gemini)
- **What:** `moments_exam.py:1087` documents in a comment that `--jobs > 1` requires the gate to be thread-safe, but provides no enforcement, guardrails, or upfront validation. Future gate authors will hit flaky failures with no explanation.
- **Assessment: IMPLEMENT (P2).** At minimum, expand the docstring into a prominent warning block. Better: add a `gate_is_thread_safe: bool` sentinel that defaults to `False` and causes the harness to automatically fall back to `--jobs 1` (with a logged warning) if unset.

### UI-4 — Rate limiting absent from API calls (GPT-4o, echoed by Gemini)
- **What:** `frontier_blind.py` correctly caps total spend but does not throttle request frequency. Burst traffic can trigger vendor rate-limit errors, producing test failures that look like gate failures.
- **Assessment: IMPLEMENT (P2).** A simple token-bucket or `time.sleep` back-off with exponential retry on HTTP 429 is sufficient. The retry wrapper already exists; add rate-limiting as a pre-call step.

### UI-5 — Hardcoded 600-second subprocess timeout in test harness (Gemini)
- **What:** `test_moments_gates.py:1395` uses a hardcoded 600s timeout for subprocess invocations. This is not configurable, making it painful to adjust for different environments (slow CI, fast local).
- **Assessment: IMPLEMENT (P2).** Expose via env var `PP_EXAM_TIMEOUT_S` with a default of 600.

### UI-6 — Configuration hierarchy (CLI vs ENV) is undocumented (Gemini)
- **What:** Some options are settable via env var (`PP_MOMENTS_GATES`) and CLI (`--gates`), with no documented precedence rule.
- **Assessment: INVESTIGATE.** Add a one-line comment or README section stating the precedence order (CLI > ENV > compiled-in default). Low effort, high clarity payoff.

### UI-7 — Word-timing linear interpolation in `store_extract.py` (Gemini)
- **What:** Lines 83-84 approximate word start/end times using character-position interpolation within a segment. This is acknowledged as a heuristic.
- **Assessment: SKIP for now.** For test corpus construction, approximate timings are acceptable. Document the limitation with an inline comment. Revisit only if timing-sensitive test cases are failing due to this.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Concurrency: bug or correct-but-complex?
- **GPT-4o position:** The combined use of `threading.Lock` and `fcntl.flock` in `frontier_blind.py` is "overkill" and could lead to deadlocks.
- **Gemini position:** The pattern is correct and sophisticated; the dual locking handles intra-process (threading) and inter-process (file-level) concurrency in separate dimensions. Locks are always acquired in a consistent order within a single context manager.
- **Tiebreaker verdict: Gemini is right.** A `threading.Lock` and `fcntl.flock` protect orthogonal resources (in-process memory vs. cross-process file). Using both is not overkill — it is necessary for correctness when multiple processes may run the suite simultaneously (e.g., different vendor baselines in parallel CI jobs). There is no deadlock risk as long as acquisition order is consistent, which the code achieves via the context manager pattern. **Action:** Add a brief comment explaining the dual-locking rationale so future maintainers do not remove one of the layers thinking it's redundant.

---

## VALIDATED STRENGTHS (all models agree this is already excellent — do NOT change)

1. **Budget management "reserve-then-settle" pattern** (`frontier_blind.py:1666, 1695`): The reserve-on-call, settle-on-return pattern is best-practice for consumable resources under concurrency. Do not simplify.
2. **Blinding implementation** (`moments_exam.py:1040-1045`): Correctly strips `expected`, `origin`, and all nested `provenance` keys and hashes the ID. The implementation is sound and complete.
3. **`BaseException` for network blocking** (`moments_exam.py:991`): Intentional, correct, and sophisticated. Do not change to `Exception`.
4. **Dual-lock concurrency pattern** (`frontier_blind.py:1618`): Correct for multi-process scenarios as analyzed above. Add a comment, do not remove a layer.
5. **Adjacent-clip same-video exclusion** (`build_corpora.py:832-833`): Good defensive programming preventing trivial test cases. Keep as-is.
6. **Case blinding architecture overall**: The separation of corpus building, test execution, and reporting is architecturally sound and praised by both models.

---

## LAW COMPLIANCE CONSENSUS

**Determination: N/A — No LAWS were provided in the governing spec.**

Both models independently confirmed that the governing spec for `pp-tests_moments_A` contains no enumerated LAWS section. The code therefore cannot be found in violation. If a LAWS section is added to the gospel in a future revision, a re-audit is required.

The code's internal consistency with the implicit constraints of the Protocol Pulse project (Python 3.12, no forbidden libraries, test-only scope with no DB writes or web routes) appears fully compliant based on both reviews.

---

## SECURITY CONSENSUS

Both models agree on the following, in priority order:

1. **HIGH — Hardcoded absolute path to secrets file** (`frontier_blind.py:1601`): The path `/home/ultron/...` both leaks the directory structure and prevents any other developer or CI runner from executing the suite without manual path surgery. This is the top security/portability issue.
2. **LOW — No additional secrets-in-code issues**: Both models confirmed that API keys themselves are read from a file, not embedded in source. The pattern is correct. The only risk is the hardcoded path to that file, addressed above.
3. **NOT APPLICABLE**: SQL injection, auth bypasses, XSS — none applicable to a local CLI test suite with no web surface.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models:

1. **Structured logging over `print()`** (both models): A world-class automated test suite emits machine-parseable, leveled log output. `print()` is a prototype-quality choice that will cause pain in any real CI pipeline. This is the single biggest ergonomics gap.
2. **Hardcoded paths killing portability** (both models): A world-class test suite should clone-and-run on any machine with the right environment variables set, with zero filesystem path surgery. The current code fails this standard.
3. **Missing rate limiting on paid API calls** (both models, Gemini via synthesis): Budget capping is necessary but insufficient. Throttle-induced failures are silent and hard to diagnose without rate limiting.
4. **Developer ergonomics for gate authors** (Gemini, confirmed as a gap by synthesis): A world-class gate framework enforces or at least loudly warns about thread-safety requirements, documents the config hierarchy, and prevents the import-time-loading anti-pattern in example gates. The current state creates traps for contributors.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Replace all hardcoded absolute paths with env vars or `Path(__file__)`-relative resolution | `frontier_blind.py:1601`, `store_extract.py:32` | both | Non-portable; leaks directory structure; blocks any CI runner or second developer |
| **P1 HIGH** | Replace all `print()` with `logging` module; configure root logger in entry points, `getLogger(__name__)` in libraries | `moments_exam.py`, `build_corpora.py`, `test_moments_gates.py` (multiple lines each) | both | Essential for CI/CD, parallel runs, and debuggability |
| **P1 HIGH** | Fix import-time corpus loading in `oracle.py` — load lazily on first call | `moments_toy_gates/oracle.py:1490-1492` | gemini (unique, high confidence) | Import-time I/O side effects are an anti-pattern; slows discovery; brittle against stale files |
| **P2 MEDIUM** | Add rate limiting / exponential back-off on HTTP 429 to API call wrapper | `frontier_blind.py` (API call site) | both (via synthesis) | Budget cap alone doesn't prevent throttle-induced flaky failures |
| **P2 MEDIUM** | Add `gate_is_thread_safe` sentinel or prominent docstring warning for `--jobs > 1` requirement | `moments_exam.py:1087` | gemini (unique, high confidence) | Silent trap for future gate authors; produces mysterious flaky failures |
| **P2 MEDIUM** | Make subprocess timeout configurable via `PP_EXAM_TIMEOUT_S` env var | `test_moments_gates.py:1395` | gemini (unique) | Hardcoded 600s is inflexible across environments |
| **P2 MEDIUM** | Add comment explaining dual-lock rationale (`threading.Lock` + `fcntl.flock`) | `frontier_blind.py:1618` | conflict resolution | Prevents future maintainer from incorrectly removing one layer as "redundant" |
| **P3 LOW** | Document CLI > ENV > default precedence in a comment or README section | `moments_exam.py` (arg-parse section) | gemini (unique) | Low-effort clarity win |
| **P3 LOW** | Add inline comment to word-timing interpolation noting it is a known heuristic | `store_extract.py:83-84` | gemini (unique) | Documents known approximation; prevents future "bug" investigations |

---

## CYCLE 2 VERDICT

**Production-ready with conditions.** The core algorithmic logic — corpus construction, test blinding, budget management, concurrency pattern, and baseline execution — is sound and demonstrates genuine engineering sophistication. Both reviewing models were complimentary of the architecture.

**Absolute final blockers before production:**

1. **P0 — Hardcoded paths** (`frontier_blind.py:1601`, `store_extract.py:32`): The suite literally cannot run on any machine other than the original developer's workstation without manual intervention. This is a hard blocker for CI/CD adoption.
2. **P1 — Structured logging**: Not a correctness blocker for a local developer, but a hard blocker for reliable automated pipeline integration.

The P1 `oracle.py` lazy-load fix is fast (5-minute change) and should be bundled into the same pass. All P2 items are improvements, not blockers, but the rate-limiting and thread-safety sentinel items should be tracked and scheduled promptly.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_MOMENTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_moments_A_CONSENSUS_C2.md.

This is the FINAL PASS for pp-tests_moments_A.
The first build was reviewed by 2 independent AI models across 2 cycles.
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Replace all hardcoded absolute paths with env vars or Path(__file__)-relative resolution | frontier_blind.py:1601, store_extract.py:32 | models: both | Non-portable; leaks directory structure; blocks CI runners and all collaborators

P1 HIGH | Replace all print() with logging module; configure root logger in entry-point scripts, use logging.getLogger(__name__) in library modules | moments_exam.py, build_corpora.py, test_moments_gates.py (multiple lines each) | models: both | Required for CI/CD, parallel job output separation, and debuggability

P1 HIGH | Fix import-time corpus loading in oracle.py — load corpus lazily on first function call, not at module import | tests/adversarial/moments_toy_gates/oracle.py:1490-1492 | models: gemini | Import-time I/O is an anti-pattern; slows test discovery; brittle against stale on-disk corpus

P2 MEDIUM | Add rate limiting / exponential back-off on HTTP 429 responses to the API call wrapper | baselines/frontier_blind.py (API call site) | models: both via synthesis | Budget cap alone does not prevent vendor throttling from causing flaky test failures

P2 MEDIUM | Add gate_is_thread_safe sentinel flag (default False) that causes harness to warn and fall back to --jobs 1, OR add a prominent docstring block warning that gate authors must ensure thread safety when --jobs > 1 | tests/adversarial/moments_exam.py:1087 | models: gemini | Silent trap for future gate authors; produces mysterious flaky failures with no diagnostic path

P2 MEDIUM | Make subprocess timeout configurable via PP_EXAM_TIMEOUT_S env var, default 600 | tests/adversarial/test_moments_gates.py:1395 | models: gemini | Hardcoded 600s is inflexible across fast/slow CI environments

P2 MEDIUM | Add inline comment explaining why both threading.Lock AND fcntl.flock are used (they protect orthogonal scopes: in-process vs cross-process) | baselines/frontier_blind.py:1618 | models: conflict resolution | Prevents future maintainer from removing one layer as "redundant", which would reintroduce a real bug

P3 LOW | Document CLI > ENV > compiled-in-default precedence order in a comment near argparse setup | tests/adversarial/moments_exam.py (argparse section) | models: gemini | Low-effort clarity; prevents configuration confusion for new contributors

P3 LOW | Add inline comment to word-timing interpolation noting it is a character-position heuristic and a known approximation | corpora/store_extract.py:83-84 | models: gemini | Documents known limitation; prevents future spurious bug investigations

VALIDATED (do NOT touch — all models confirmed excellent):
- Budget "reserve-then-settle" pattern in frontier_blind.py:1666,1695 — correct best-practice for consumable resources under concurrency
- Case blinding implementation in moments_exam.py:1040-1045 — correctly strips expected/origin/provenance and hashes ID; do not alter
- BaseException (not Exception) for network blocking in moments_exam.py:991 — intentional, correct, sophisticated; do NOT change to Exception
- Dual-lock pattern (threading.Lock + fcntl.flock) in frontier_blind.py:1618 — correct for multi-process scenario; add a comment but do NOT remove a layer
- Adjacent-clip same-video exclusion in build_corpora.py:832-833 — correct defensive programming; keep as-is

After implementing: regression_test.sh must show zero FAILs.
git add -A && git commit -m "feat(pp-tests_moments_A): post-audit pass — consensus improvements"
git push origin pp-tests
```

---

# WINNER DETERMINATION

# WINNER: **Gemini** — Gemini consistently identified the highest-impact, most technically nuanced issues (the `BaseException` subtlety, `oracle.py` import-time loading, word timing heuristic approximation) that the other models either missed or only acknowledged after Gemini surfaced them. Its analysis demonstrated genuine depth beyond surface-level pattern matching, correctly praised what was well-engineered while precisely characterizing what was flawed, and its findings drove the Cycle 2 consensus more than any other model's output.

---

# FINAL SECOND-PASS PRIORITY LIST

Ordered by: (severity × portability impact × implementation cost⁻¹). Implement top-down.

---

## P0 — CRITICAL / DO FIRST (blocks reproducibility or correctness)

### P0-1 — Hardcoded Absolute Paths [U1]
**Files:** `baselines/frontier_blind.py:1601`, `corpora/store_extract.py:32`
**Fix:**
```python
# Replace /home/ultron/protocol_pulse/.env with:
_ROOT = Path(__file__).resolve().parents[N]  # tune N per file depth
_ENV_PATH = Path(os.getenv("PP_ROOT", str(_ROOT))) / ".env"
```
Never commit `/home/<username>/` to source. Breaks every other machine, leaks directory structure.

---

### P0-2 — `oracle.py` Import-Time Corpus Loading [Gemini-unique]
**File:** `oracle.py` (import-level code)
**Problem:** Loads all corpora from disk at module import. Triggers on test *discovery*, not test *execution*. Causes slow startup, brittle filesystem dependency, and silent failures during collection.
**Fix:**
```python
# Replace module-level:
CORPORA = _load_all_corpora()

# With lazy initialization:
_CORPORA_CACHE = None
def get_corpora():
    global _CORPORA_CACHE
    if _CORPORA_CACHE is None:
        _CORPORA_CACHE = _load_all_corpora()
    return _CORPORA_CACHE
```

---

## P1 — HIGH / IMPLEMENT THIS SPRINT

### P1-1 — Replace `print()` with Structured Logging [U2]
**Files:** All — `frontier_blind.py`, `moments_exam.py`, `build_corpora.py`, `store_extract.py`
**Fix:**
```python
import logging
log = logging.getLogger(__name__)
# Replace print("Building case...") with log.info("Building case %s", case_id)
# Replace print(f"ERROR: {e}") with log.exception("Failed during corpus build")
```
Add a root logging config in the test entry point. This is not cosmetic — silent `print()` output disappears in CI log aggregators.

---

### P1-2 — Add Vendor API Rate Limiting to `frontier_blind.py` [Both models]
**Problem:** Budget cap (`fcntl.flock` + `threading.Lock` reserve/settle pattern) controls *cost* only, not *request frequency*. Vendor throttling causes intermittent test failures that are misattributed to gate logic.
**Fix:**
```python
import time
from threading import Semaphore

_RATE_LIMITER = Semaphore(5)  # max concurrent inflight requests
_MIN_REQUEST_GAP = 0.2        # seconds between requests per vendor

def _rate_limited_call(fn, *args, **kwargs):
    with _RATE_LIMITER:
        result = fn(*args, **kwargs)
        time.sleep(_MIN_REQUEST_GAP)
        return result
```
Wrap all vendor API calls. Configure limits per-vendor via env vars (`PP_OPENAI_RPS`, etc.).

---

### P1-3 — Improve Error Message Specificity in Error Handlers [GPT-4o + Cycle 2]
**Problem:** Several `except` blocks raise or log generic messages with no context about *which* corpus, *which* case ID, or *which* gate failed.
**Fix pattern:**
```python
# Instead of:
except Exception as e:
    print(f"Error: {e}")

# Write:
except Exception as e:
    log.exception(
        "Gate %s failed on case %s (corpus: %s)",
        gate_fn.__name__, case_id, corpus_path
    )
    raise
```
Every caught exception must include: gate name, case ID, corpus path. Non-negotiable for debuggability.

---

## P2 — MEDIUM / NEXT SPRINT

### P2-1 — Document All Environment Variables [GPT-4o]
**Deliverable:** Add `ENV_VARS.md` or expand `README.md` with a table:

| Variable | Required | Default | Description |
|---|---|---|---|
| `PP_ROOT` | No | Derived from `__file__` | Repo root override |
| `PP_OPENAI_RPS` | No | `5` | Max concurrent OpenAI requests |
| `PP_TRANSCRIPT_STORE` | Yes | None | Path to transcript store root |

No env var that affects behavior should be undocumented. Discovery-by-grep is not documentation.

---

### P2-2 — Annotate Word Timing Heuristic Limitation [Gemini-unique]
**File:** `store_extract.py:83-84`
**Problem:** Linear interpolation of word timings by character position is documented nowhere. Downstream consumers of timing data may treat these as ground truth.
**Fix:**
```python
# Current (undocumented approximation):
word_start = seg_start + (char_offset / seg_chars) * seg_duration

# Add above the calculation:
# NOTE: Word timings are estimated via linear character-position interpolation
# within each transcript segment. Character count is a proxy for duration;
# actual word timing error can be ±200ms on fast/slow speech. Do not use
# these values for frame-accurate alignment.
```
Also add an `_timing_confidence: "interpolated"` field to the output JSON so consumers can gate on it.

---

### P2-3 — Concurrency Audit: Verify Lock Ordering is Consistent [GPT-4o concern, Gemini disagrees]
**File:** `frontier_blind.py:1618`
**Status:** Gemini correctly assessed the `threading.Lock` + `fcntl.flock` combination as sound for the multi-process use case. GPT-4o's deadlock concern is *valid in theory* but requires a specific interleaving that the reserve/settle pattern makes unlikely.
**Action:** Add a code comment explaining the lock ordering contract, and add a 5-second `flock` timeout with a `BlockingIOError` handler to prevent indefinite hangs in degenerate cases:
```python
try:
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    log.warning("SPEND file locked after timeout; skipping budget check")
    raise BudgetUnavailableError("Could not acquire spend lock")
```

---

## P3 — LOW / BACKLOG

### P3-1 — Transcript Store Unavailability Handling [GPT-4o]
Add an explicit, early-exit check in `build_corpora.py` when the transcript store path does not exist or is unreadable, with a human-readable error message rather than a downstream `FileNotFoundError` stack trace.

### P3-2 — Consider Corpus Lazy-Loading Index
If corpus count grows, replace full-load in `oracle.py` (after P0-2 fix) with an index file listing available cases; load individual cases on demand. Not urgent at current scale; revisit when corpus > 10k cases.

---

## IMPLEMENTATION ORDER SUMMARY

| Priority | Item | Owner Signal | Effort |
|---|---|---|---|
| P0-1 | Hardcoded paths | Any engineer | 30 min |
| P0-2 | oracle.py lazy load | Any engineer | 1 hr |
| P1-1 | Structured logging | Any engineer | 2 hrs |
| P1-2 | Rate limiting | Backend | 3 hrs |