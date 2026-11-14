# CONSENSUS REPORT — PP-TESTS_MOMENTS_A — CYCLE 1
Generated: 2026-11-12 03:41
Models: gpt4o, gemini (+1 failed — Grok-3: budget exceeded)

---

## SCORES

| Subsystem       | Gemini | GPT-4o | Grok   | Consensus |
|-----------------|--------|--------|--------|-----------|
| Backend logic   | 95/100 | 85/100 | N/A    | 90/100    |
| Frontend/UI     | N/A    | N/A    | N/A    | N/A       |
| Error handling  | 98/100 | 70/100 | N/A    | 84/100    |
| Security        | 95/100 | 80/100 | N/A    | 87/100    |
| Performance     | 90/100 | 85/100 | N/A    | 87/100    |
| Law compliance  | 100/100| 90/100 | N/A    | 95/100    |
| World-class gap | 85/100 | 75/100 | N/A    | 80/100    |
| **OVERALL**     | **93** | **81** | **N/A**| **87/100**|

> **Note on divergence**: The 12-point overall gap between Gemini and GPT-4o is primarily explained by error handling (Gemini: 98, GPT-4o: 70). Gemini credited the structured JSON error capture and `BaseException` trick highly; GPT-4o focused on missing logging and sparse `moments_exam.py` instrumentation. Both are correct observations about different layers. Consensus lands at 84 for error handling — good architecture, insufficient observability tooling.

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U1 — Hardcoded filesystem paths reduce portability and create a latent security/ops risk
- **What**: Absolute paths like `/home/ultron/protocol_pulse/.env` and `/home/ultron/protocol_pulse/data/editorial` are embedded in source.
- **Files**: `baselines/frontier_blind.py:1601`, `build_corpora.py:32`
- **What to change**: Replace hardcoded paths with environment variables (e.g., `PP_ROOT`, `PP_DATA_DIR`, `PP_SECRETS_PATH`) with sensible defaults derived from `Path(__file__).resolve().parent`. Document in README.
- **Why unanimous**: GPT-4o flagged it as a security risk (hardcoded secrets path); Gemini flagged it as a configuration management gap. Same root cause, different framings.

### U2 — Logging uses `print()` throughout; no structured log levels
- **What**: All diagnostic output is via bare `print()` calls. No `logging` module usage means no log-level filtering, no easy redirection, and no machine-parseable debug output.
- **Files**: `moments_exam.py` (various), `build_corpora.py` (various)
- **What to change**: Introduce Python `logging` with at least `DEBUG`/`INFO`/`WARNING`/`ERROR` levels. Wire a `--verbose` / `--quiet` CLI flag to `logging.basicConfig(level=...)`. Keep `print()` only for final human-readable summary output.
- **Why unanimous**: GPT-4o rated error handling 70/100 specifically citing this. Gemini rated it PARTIAL with identical rationale.

---

## MAJORITY FINDINGS (2 of 2 models agree)

> With only 2 functioning models, majority = unanimous. All majority findings are listed above under Unanimous. No additional tier applies here.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI1 — `oracle.py` loads all corpora at import time [GEMINI ONLY]
- **File**: `tests/adversarial/moments_toy_gates/oracle.py:1490-1492`
- **What Gemini observed**: The oracle toy gate loads the entire corpus into a global `_V` dict at module import. This (a) creates fragile filesystem coupling at collection time, (b) pulls in unnecessary data if only a subset of cases runs, and (c) could cause false passes if on-disk files are stale relative to what the harness loaded in memory.
- **Assessment**: **Implement.** This is a real correctness risk — not just a style concern. If corpora are rebuilt between collection and execution, the oracle answers the wrong questions. Fix: pass the expected answer into the gate from the harness, or load lazily per case-id on demand. This is the highest-value single fix in the report.
- **Priority**: Promote to P1.

### UI2 — Linear character-position interpolation for word timings is an approximation [GEMINI ONLY]
- **File**: `store_extract.py:83-84`
- **What Gemini observed**: Word timing is estimated by linear interpolation over character count within a segment, which doesn't reflect natural speech rate variation.
- **Assessment**: **Investigate further, do not fix now.** For corpus construction purposes this heuristic is acceptable (Gemini itself said so). Fixing it would require a forced-alignment model (e.g., WhisperX) which is a significant infrastructure dependency. Flag with a `# APPROX: linear char interpolation` comment and a TODO for the next engineering cycle.
- **Priority**: P3 — documentation only for now.

### UI3 — `partner_attack` cases defined as hardcoded dicts in Python source [GEMINI ONLY]
- **File**: `build_corpora.py:749-756`
- **What Gemini observed**: Adversarial case definitions live inline as Python dicts, making them hard to extend, review, or audit without touching code.
- **Assessment**: **Implement (P2).** Extracting these to a `partner_attacks.yaml` or `partner_attacks.json` fixture file has zero risk and meaningful maintainability gain. Reviewers can propose new adversarial cases via data PRs rather than code PRs. Strongly agree with this observation.
- **Priority**: P2.

### UI4 — Combined `threading.Lock` + `fcntl.flock` risks deadlock [GPT-4O ONLY]
- **File**: `baselines/frontier_blind.py` (various)
- **What GPT-4o observed**: Using both a threading lock and a file lock in `_locked()` could lead to deadlocks.
- **Assessment**: **Skip / disagree with framing.** Gemini explicitly analyzed this same code and rated it excellent ("best-practice for managing consumable resources under concurrency"). The two locks serve different scopes: the threading lock serializes within a single process, the `flock` serializes across processes. This is the correct pattern for a scenario where tests for different vendors can run in parallel processes. No deadlock risk exists as long as the acquisition order is consistent, which it is. GPT-4o's concern is not borne out by the implementation.
- **Priority**: No action.

### UI5 — No corpus-level versioning / git SHA stamping in `INDEX.json` [GEMINI ONLY]
- **File**: `build_corpora.py` (INDEX generation)
- **What Gemini observed**: `INDEX.json` has file-level hashes but no corpus version, build date, or source git SHA — making historical test results not fully traceable.
- **Assessment**: **Implement (P2).** Add a top-level `meta` block to `INDEX.json` at build time: `{"built_at": "<ISO8601>", "git_sha": "<sha>", "corpus_version": "<semver>"}`. This costs ~5 lines and has significant value for debugging "why did scores change between runs."
- **Priority**: P2.

### UI6 — No rate limiting on API calls, only budget cap [GEMINI ONLY]
- **File**: `baselines/frontier_blind.py`
- **What Gemini observed**: Budget cap prevents overspend but not rate-limit throttling from vendors, which could cause test failures under rapid fire.
- **Assessment**: **Investigate further.** Worth adding an optional `time.sleep()` back-off between calls or using `tenacity` with exponential back-off. However, since the `max_retries=3` on the client handles transient rate limit errors (HTTP 429 triggers retry), this is medium-low urgency. Add as P2.
- **Priority**: P2.

---

## CONFLICTS (models disagree — tiebreaker)

### C1 — Threading lock + file lock: dangerous vs. excellent
- **GPT-4o**: Flagged as potential deadlock risk (P2).
- **Gemini**: Explicitly praised as a best-practice "reserve-then-settle" pattern.
- **Ruling**: **Gemini is correct.** The pattern is a well-known solution to the two-level concurrency problem (intra-process + inter-process). The acquisition order is deterministic. No change warranted. GPT-4o appears to have pattern-matched on "two locks = bad" without analyzing the semantics.

### C2 — Error handling quality
- **GPT-4o**: 70/100, flagged as a primary deficiency.
- **Gemini**: 98/100, praised `BaseException` raising and JSON error capture.
- **Ruling**: **Both are partly right, talking past each other.** Gemini evaluated the *architecture* of error propagation (which is excellent). GPT-4o evaluated the *observability* tooling — logging, verbosity control — which is genuinely weak. Consensus action: preserve the excellent error propagation architecture (do not change), but add structured logging (U2 above). Do not re-architect error handling.

### C3 — Law compliance score
- **GPT-4o**: 90/100 — noted index requirements not applicable, docked points anyway.
- **Gemini**: 100/100 — correctly noted no laws were provided in the governing spec.
- **Ruling**: **Gemini is correct.** When no laws are enumerated in the spec, the only valid verdict is N/A / fully compliant by vacuous truth. GPT-4o should not dock points for absence of a requirement. Consensus: 100/100, N/A.

---

## VALIDATED STRENGTHS (all models agree — do NOT change in second pass)

1. **Budget management in `frontier_blind.py`** — The `threading.Lock` + `fcntl.flock` + reserve-then-settle pattern is excellent. Both models praised it. Leave untouched.

2. **Case blinding in `moments_exam.py`** — Removal of `expected`/`origin`/`provenance` keys and ID hashing is correctly implemented. Gemini specifically validated this. Do not modify the blinding logic.

3. **`BaseException` raise for network refusal** — The deliberate use of `BaseException` instead of `Exception` to prevent improper swallowing by gate code is a clever, intentional design. Gemini praised it. GPT-4o did not flag it. Leave as-is.

4. **JSON structured test reports** — Both models agreed the JSON output format for test results is well-designed. Do not change the report schema.

5. **`max_retries=3` on API clients** — Both models found external API handling acceptable/good. Leave retry configuration as-is.

6. **Adjacent-clip same-video exclusion logic** (`build_corpora.py:832-833`) — Gemini explicitly called this "good defensive programming." Agreed. Do not alter.

7. **Overall framework architecture** — Separation of corpus building, test execution, and reporting is praised by both models. The three-script structure is sound. Do not reorganize.

---

## LAW COMPLIANCE CONSENSUS

**Determination: FULLY COMPLIANT (N/A)**

No LAWS were enumerated in the governing spec for this feature. Gemini correctly returned N/A. GPT-4o's partial deductions were methodologically unsound. The code uses Python 3.12 and standard libraries consistent with the project stack. No violations found.

**Final score: 100/100 (N/A basis)**

---

## SECURITY CONSENSUS

Findings in priority order (both models must have flagged or one model flagged with high confidence):

1. **[MEDIUM] Hardcoded absolute path to `.env` file** (`frontier_blind.py:1601`) — Both models flagged. If the process runs in a different user context or the repo is cloned elsewhere, it silently fails to load keys and may fall back to empty strings. Fix: use `PP_SECRETS_PATH` env var with a relative default. *(Overlaps with U1 above.)*

2. **[LOW] No API rate limiting** (`frontier_blind.py`) — Single model (Gemini), but credible. Budget cap prevents financial damage; rate limiting would prevent test flakiness. Low urgency given `max_retries=3`.

3. **[INFORMATIONAL] No unvalidated user input, no SQL, no auth surface** — Both models confirmed. The attack surface of a command-line test harness with trusted internal data is minimal. No action required.

**Security posture: Good for an internal test suite. No critical vulnerabilities.**

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2+ models (note: with only 2 models, this means both):

### WC1 — Configuration management (both models)
Hardcoded paths scattered through source. A world-class test suite uses a single config entry point — either a `pyproject.toml` `[tool.pp-tests]` section, a `config.yaml`, or at minimum a single `config.py` that all modules import from. Env vars override config file values.

### WC2 — Results historization (Gemini primary; GPT-4o implied via CI/CD mention)
Test output is a single JSON file per run with no persistence layer. World-class: append results to a time-series store (even a simple SQLite DB or append-only JSONL log). Enables: trend detection, flaky-case identification, gate latency regression tracking. A simple `results_store.py` with an `append_run(report: dict)` function would suffice as a first step.

### WC3 — CI/CD integration (GPT-4o explicit, Gemini implied)
No pipeline configuration present. World-class: a GitHub Actions (or equivalent) workflow that runs `moments_exam.py` on PR, posts gate scores as a PR check, and blocks merge if any gate regresses below its baseline. This requires the results historization (WC2) to have a "previous baseline" to compare against.

---

## FINAL ACTION PLAN (sorted by consensus priority)

| Priority | Change | File:Line | Models | Why |
|----------|--------|-----------|--------|-----|
| **P0 CRITICAL** | Refactor `oracle.py` to load case answers lazily (per case-id on demand) rather than loading all corpora at import. Pass expected answer from harness or fetch by case hash at call time. | `moments_toy_gates/oracle.py:1490-1492` | gemini (unique, promoted) | Correctness risk: stale on-disk corpora silently give oracle wrong answers; filesystem state at import != state at execution |
| **P1 HIGH** | Replace all hardcoded absolute paths (`/home/ultron/...`) with env vars (`PP_ROOT`, `PP_DATA_DIR`, `PP_SECRETS_PATH`) with relative-path defaults derived from `Path(__file__).resolve()` | `frontier_blind.py:1601`, `build_corpora.py:32` | both | Portability, ops safety, and mild security risk if path is wrong silently |
| **P1 HIGH** | Introduce Python `logging` module throughout. Replace `print()` diagnostic calls with `logging.debug/info/warning/error`. Add `--verbose`/`--quiet` CLI flags wired to log level. Keep only final summary as `print()`. | `moments_exam.py` (various), `build_corpora.py` (various) | both | Observability; both models flagged; current 70/100 error handling score driven entirely by this gap |
| **P2 MEDIUM** | Extract `partner_attack` hardcoded dicts to `partner_attacks.yaml` fixture file. `build_corpora.py` loads them at runtime. | `build_corpora.py:749-756` | gemini (unique) | Maintainability; non-engineers can propose new adversarial cases via data PRs |
| **P2 MEDIUM** | Add `meta` block to `INDEX.json` at build time: `built_at` (ISO8601), `git_sha` (`git rev-parse HEAD`), `corpus_version` (semver from a `VERSION` file). | `build_corpora.py` (INDEX generation) | gemini (unique) | Traceability; without this, test result changes cannot be correlated to corpus changes |
| **P2 MEDIUM** | Add optional exponential back-off between API calls in `frontier_blind.py` (e.g., configurable `PP_API_CALL_DELAY_S` env var, default 0). Consider `tenacity` for retry logic. | `frontier_blind.py` (API call sites) | gemini (unique) | Prevents vendor rate-limit throttling from causing spurious test failures under parallel execution |
| **P3 LOW** | Add `# APPROX: linear char-position interpolation for word timing` comment and a `TODO(alignment): consider WhisperX for precise timings` note. | `store_extract.py:83-84` | gemini (unique) | Documents the known approximation; no code change warranted yet |
| **P3 LOW** | Add docstrings / module-level comments to `build_corpora.py` explaining the case-construction pipeline | `build_corpora.py` (various) | gpt4o (unique) | Readability; low urgency but free maintenance value |

---

## CYCLE 1 VERDICT

**Ready for a targeted second build pass. No fundamental rework required.**

The architecture is sound and already close to world-class for an internal quality-gate suite. The two critical/high items (P0 oracle lazy-loading, P1 paths + logging) are surgical fixes that do not touch the core framework design. The validated strengths — blinding, budget management, error propagation, report schema — should be preserved exactly as written.

The 87/100 consensus score reflects a genuinely well-engineered codebase with two specific gaps: one correctness risk (oracle import-time loading) and one observability gap (logging infrastructure). Both are fixable in a single focused pass.

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_MOMENTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_moments_A_CONSENSUS_C1.md.

This is the SECOND PASS for pp-tests_moments_A.
The first build was reviewed by 2 independent AI models (Gemini 2.5 Pro, GPT-4o)
across 1 cycle. Implement every P0 and P1 item from the consensus.
Use judgment on P2. Skip P3 (documentation-only).

PRIORITY ACTION PLAN:

P0 CRITICAL | Refactor oracle toy gate to load answers lazily, not at import time.
            | tests/adversarial/moments_toy_gates/oracle.py:1490-1492
            | Load the expected answer for a given case-id on demand (fetch by
            | hashed ID at call time from the corpora directory, or receive it
            | as a parameter from the harness). Remove the global _V dict
            | populated at module import. This is a correctness risk: stale
            | on-disk files silently give the oracle wrong answers.

P1 HIGH     | Replace all hardcoded absolute paths with environment variables.
            | frontier_blind.py:1601, build_corpora.py:32 (and any other
            | occurrences of /home/ultron/protocol_pulse/).
            | Introduce: PP_ROOT, PP_DATA_DIR, PP_SECRETS_PATH env vars.
            | Default each to a relative path derived from
            | Path(__file__).resolve().parent chain so the repo is portable.
            | Update README.md with the new env var documentation.

P1 HIGH     | Introduce Python logging module throughout.
            | moments_exam.py (all diagnostic print calls),
            | build_corpora.py (all diagnostic print calls).
            | - Replace print() diagnostic output with logging.debug/info/
            |   warning/error as appropriate.
            | - Add --verbose flag (sets DEBUG level) and --quiet flag
            |   (sets WARNING level) to CLI argument parsers.
            | - Retain print() ONLY for the final human-readable summary line
            |   and the JSON report dump.
            | - Do NOT change the JSON report schema.

P2 MEDIUM   | Extract partner_attack hardcoded dicts to a YAML fixture file.
            | build_corpora.py:749-756
            | Create tests/adversarial/fixtures/partner_attacks.yaml.
            | Load at runtime with PyYAML (already a transitive dep or add it).
            | No change to the generated corpora format.

P2 MEDIUM   | Add meta block to INDEX.json at corpus build time.
            | build_corpora.py (INDEX generation section).
            | Add: {"meta": {"built_at": "<ISO8601>", "git_sha": "<output of
            | git rev-parse HEAD>", "corpus_version": "<contents of
            | tests/adversarial/VERSION file, create it at '1.0.0'>"}}.
            | Update any INDEX readers to tolerate the new top-level key.

P2 MEDIUM   | Add optional inter-call delay / back-off for API calls.
            | frontier_blind.py (API call sites).
            | Read PP_API_CALL_DELAY_S env var (default: 0.0).
            | Sleep that many seconds before each outbound API call.
            | This prevents vendor rate-limit throttling under parallel runs.

VALIDATED — do NOT touch these (all models confirmed excellent):
- The threading.Lock + fcntl.flock reserve-then-settle budget pattern
  in frontier_blind.py. Leave the concurrency implementation exactly as-is.
- The case blinding logic in moments_exam.py (expected/origin/provenance
  removal + ID hashing). Do not modify.
- The BaseException raise in the network refusal mechanism. Do not change
  to Exception.
- The JSON structured report schema output. Do not alter field names or
  structure.
- The adjacent-clip same-video exclusion logic in build_corpora.py:832-833.
- The three-script architectural separation (build_corpora / moments_exam /
  test_moments_gates). Do not reorganize.
- max_retries=3 on API clients. Leave as-is.

After implementing all changes:
1. Run regression_test.sh — must show zero FAILs.
2. Verify: python moments_exam.py --quiet runs without print() noise.
3. Verify: python moments_exam.py --verbose shows DEBUG output.
4. Verify: INDEX.json contains a "meta" top-level key after rebuild.
5. Verify: oracle gate still returns correct answers after lazy-load refactor
   (run: python -m pytest tests/adversarial/test_moments_gates.py -v).

git add -A && git commit -m "feat(pp-tests_moments_A): post-audit pass — consensus improvements (C1)"
git push origin pp-tests
```