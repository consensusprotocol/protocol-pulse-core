# CONSENSUS REPORT — PP-TESTS_AUDIT_ALL — CYCLE 1
Generated: 2026-11-12 02:21
Models: gpt4o, gemini (+1 failed — Grok-3 budget exceeded)

---

## SCORES

| Subsystem         | Gemini        | GPT-4o  | Grok   | Consensus |
|-------------------|---------------|---------|--------|-----------|
| Backend logic     | ~95 (implied) | 85/100  | N/A    | **90/100** |
| Frontend/UI       | N/A           | N/A     | N/A    | **N/A**   |
| Error handling    | ~90 (implied) | 80/100  | N/A    | **85/100** |
| Security          | ~95 (implied) | 90/100  | N/A    | **92/100** |
| Performance       | ~90 (implied) | 85/100  | N/A    | **87/100** |
| Law compliance    | 100/100       | 100/100 | N/A    | **100/100** |
| World-class gap   | ~90 (implied) | 85/100  | N/A    | **87/100** |
| **OVERALL**       | **~95**       | **88**  | **N/A**| **91/100** |

> *Gemini did not emit numeric scores but its prose is consistently superlative. Scores are inferred from qualitative language. Grok disqualified on budget grounds; consensus is therefore 2-of-2.*

---

## UNANIMOUS FINDINGS (both models agree — implement unconditionally)

### U-1 · Exception handling in `call_gate` may silently swallow critical failures
- **What**: Both models flagged that the `call_gate` function catches exceptions and returns `RAISED`, which could mask genuinely critical problems and cause test failures to be misattributed or silently ignored rather than propagating correctly.
- **File/Line**: `tests/adversarial/test_f4_vacuity.py:1947–1956`
- **What to change**: Narrow the caught exception type to expected/recoverable exceptions only (e.g., `ValueError`, `RuntimeError`). Re-raise `SystemExit`, `KeyboardInterrupt`, and any `BaseException` subclass that signals an infrastructure fault. Add a log line before returning `RAISED` so the exception is always visible in the test output even when swallowed.

### U-2 · Logging is minimal; failures are hard to diagnose
- **What**: Both models noted that the test suite produces minimal runtime logging, making post-hoc diagnosis of failures harder than necessary.
- **File/Line**: Various — `adv_helpers.py` subprocess wrappers (~lines 388, 640, 998), `test_f4_vacuity.py` gate calls, `conftest.py` session teardown.
- **What to change**: Add structured `logging.debug`/`logging.info` calls at key decision points: before/after each subprocess invocation (with return code and truncated stdout), when a gate returns an unexpected value, and when a fixture setup path is selected. Use pytest's `caplog` fixture in existing tests that already need this or emit to stderr with a distinctive prefix so CI logs remain scannable.

---

## MAJORITY FINDINGS (2 of 2 models agree)

Both models constituted the full available majority. All unanimous findings above are also majority findings. No additional majority-but-not-unanimous items exist given the 2-model pool.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 (Gemini only) · Dependency versions are undeclared — no `requirements.txt` or `pyproject.toml`
- **What**: `pp-tests_STATE.md` documents library versions used, but there is no machine-enforceable pin file. A future test run on a different machine or after a `pip install --upgrade` could produce different results without warning.
- **Assessment**: **Implement.** This is a real, practical reproducibility risk. It is not a "nice to have" at the maturity level this suite has reached. A `requirements-tests.txt` or a `[test]` extras group in `pyproject.toml` with pinned versions is a one-time, low-effort investment.
- **Action**: Create `tests/adversarial/requirements-adv-tests.txt` (or add a `[tool.pytest.ini_options]` block and `[project.optional-dependencies]` section in `pyproject.toml`) with every library version from `pp-tests_STATE.md`.

### UI-2 (Gemini only) · Property-based testing (Hypothesis) would expand the adversarial input space
- **What**: The adversarial sentence generator is currently deterministic/hand-seeded. A Hypothesis-based fuzzer would explore the combinatorial space more broadly and could find `canon.py` edge cases the current set misses.
- **Assessment**: **Investigate further — do not implement in this pass.** This is a valid long-term improvement but it would substantially change the test architecture (determinism, CI runtime budget, xfail management). Flag as a P3 backlog item.

### UI-3 (Gemini only) · Containerization for bit-for-bit reproducibility
- **What**: The suite relies on system-installed tools (notably `ffmpeg`). Without a container, cross-machine variance is possible.
- **Assessment**: **Implement incrementally.** Add a `Dockerfile.test` or `docker-compose.test.yml` as a secondary run path. The primary `one command, under 5 minutes on CPU` law must remain satisfied outside the container for fast local dev. The container is a CI/CD supplement, not a replacement.

### UI-4 (GPT-4o only) · CI integration not present
- **What**: GPT-4o noted there is no documented CI pipeline (GitHub Actions, etc.) wiring the test command into automated checks.
- **Assessment**: **Implement.** At the suite's level of maturity, manual invocation is the only gap between "excellent" and "world-class". A minimal `.github/workflows/pp-tests.yml` that runs `pytest tests/adversarial/ -x --tb=short` on every PR is a low-effort, high-value addition.

---

## CONFLICTS (models disagree — tiebreaker)

### C-1 · Overall quality assessment
- **GPT-4o**: "Ready for production" with caveats; scored 88/100 overall; flagged exception handling as a genuine P1 concern.
- **Gemini**: "An exceptional piece of software engineering"; effectively a ~95/100 assessment; treated exception handling as worth noting but did not emphasize it as a blocking issue.
- **Tiebreaker**: **GPT-4o is more cautious and correct** on the exception handling issue. The `call_gate` concern is a real gap: a test suite that silently absorbs infrastructure errors and reports `RAISED` instead of crashing hard makes it possible for the CI light to stay green while the system under test is fundamentally broken. This deserves P1 treatment. Gemini's overall praise is warranted for the broader architecture, but caution on this specific point is the right call.

### C-2 · Whether the suite is effectively "done"
- **Gemini**: Treats the suite as nearly world-class with the gaps being frontier/aspirational.
- **GPT-4o**: Calls for P2 improvements across several areas.
- **Tiebreaker**: Both are right at different levels of analysis. Gemini is correct that the *architecture and coverage* are exceptional. GPT-4o is correct that *operational maturity* (logging, CI, dependency pinning) has genuine gaps. Second pass should treat architecture as locked and operational maturity as the work to be done.

---

## VALIDATED STRENGTHS (both models confirm — do NOT change in second pass)

The following are validated by both reviewers as genuinely excellent. Leave them strictly alone:

1. **CPU-only enforcement (`conftest.py`)** — multi-layer guard (env vars + stubs + system call interception + end-of-session `nvidia-smi`) is correct and exemplary. Do not simplify it.
2. **`NetworkBlocked(BaseException)` exception hierarchy** — inheriting from `BaseException` rather than `Exception` is intentional and correct; prevents production `except Exception` clauses from absorbing it. Do not change the inheritance.
3. **`adv_helpers.py` case generation** (`gen_cases`, `TEEN_TY` swaps, `ACTOR_SWAPS`, surface variants) — the combinatorial design is sound and comprehensive. Do not restructure it.
4. **Family 3 (Auth) mutation coverage** — the exhaustive mutation list (waived pass, digest of different file, file swap during delivery, cross-run attestation) is exactly right. Do not reduce coverage.
5. **Family 4 (Vacuity) layered strategy** — the defense-in-depth test (`test_whatever_a_gate_returns_on_nothing_release_blocks_it`) is architecturally mature. Do not remove or weaken it.
6. **`xfail` discipline** — using `pytest.fail` for broken *setup* vs. `assert` for the *defect under test* ensures xfails can't be triggered by infrastructure failures. This distinction is critical. Do not collapse them.
7. **Documentation ecosystem** (`REQUESTS.md`, `STATE.md`, `BIBLE_ADDITIONS.md`, `AUDIT_RESPONSE.md`) — the auditable record is a genuine differentiator. Do not replace with inline comments.
8. **`release_run` fixture function (`adv_helpers.py:577`)** — clean, complex, correct. Do not refactor.
9. **Synthetic media approach with known audio timings (`adv_helpers.py:476`)** — avoids any real-network dependency. Do not replace with live fixtures.
10. **Family 5 reference integrity tests** — frozen references, hash validation, manifest consistency checks. Do not relax any of these constraints.

---

## LAW COMPLIANCE CONSENSUS

| Law | Status | Notes |
|-----|--------|-------|
| TESTS ONLY (no prod file changes) | ✅ COMPLIANT | Unanimous |
| CPU ONLY | ✅ COMPLIANT | Unanimous; multi-layer enforcement confirmed |
| Real public entry points | ✅ COMPLIANT | Unanimous; documented exception for `run_fresh._samples` is justified |
| Every test passes or strict xfail | ✅ COMPLIANT | Unanimous |
| Genuine-pass AND must-fail in every family | ✅ COMPLIANT | Unanimous |
| Nothing measured is never a pass (L-m) | ✅ COMPLIANT | Unanimous; entire Family 4 enforces this |
| Fail closed (L-j) | ✅ COMPLIANT | Unanimous; entire Family 3 enforces this |
| Never change what a check accepts | ✅ COMPLIANT | Unanimous |
| One command, under 5 minutes on CPU | ✅ COMPLIANT | Unanimous; documented in STATE.md |

**Final determination: FULLY LAW-COMPLIANT. No violations detected by either model.**

---

## SECURITY CONSENSUS

No security vulnerabilities were found by either model. The suite runs in a trusted test environment with:

- No live network access (blocked and tested)
- No hardcoded secrets
- No user-supplied input
- Subprocess calls using internally-generated arguments only (no shell injection vectors)
- Temporary files managed via `pytest`'s `tmp_path` (auto-cleaned)

**Security status: CLEAN.** No action required in second pass.

---

## WORLD-CLASS GAP CONSENSUS

Items mentioned by 2 models (or by 1 model with strong independent justification):

| Gap | Models | Priority |
|-----|--------|----------|
| Dependency version pinning (no enforceable pin file) | Gemini (explicit) + GPT-4o (CI implies it) | P1 |
| CI pipeline integration | GPT-4o (explicit) + Gemini (implicit in containerization discussion) | P1 |
| Exception handling robustness in `call_gate` | Both explicit | P1 |
| Logging depth for failure diagnosis | Both explicit | P2 |
| Containerization for cross-machine reproducibility | Gemini (explicit) | P2 |
| Property-based testing (Hypothesis) | Gemini (explicit) | P3 backlog only |

---

## FINAL ACTION PLAN (sorted by consensus priority)

```
P0 CRITICAL | Narrow exception catch in call_gate; re-raise BaseException subclasses | tests/adversarial/test_f4_vacuity.py:1947–1956 | models: both | Silent infrastructure failures can produce false green CI; a test suite that absorbs its own crashes is worse than no test suite.

P1 HIGH     | Add structured logging at subprocess boundaries and gate call sites | adv_helpers.py:388,640,998 + test_f4_vacuity.py gate calls | models: both | Without actionable log output, a CI failure requires re-running locally with added print statements; this is avoidable cost.

P1 HIGH     | Create enforceable dependency pin file (requirements-adv-tests.txt or pyproject.toml extras) | tests/adversarial/ root | models: gemini (explicit), gpt4o (implied via CI) | Library drift between STATE.md documentation and actual runtime is an invisible reproducibility hazard.

P1 HIGH     | Add minimal CI pipeline definition | .github/workflows/pp-tests.yml (new file) | models: gpt4o (explicit), gemini (implicit) | The suite is excellent but runs only on demand; automating it on every PR is the final step to "world-class operational posture".

P2 MEDIUM   | Add Dockerfile.test for bit-for-bit reproducible CI runs (supplement, not replace, bare-metal path) | repo root | models: gemini (explicit) | ffmpeg version variance is a known risk; container solves it without breaking the one-command law.

P3 BACKLOG  | Evaluate Hypothesis for property-based adversarial input generation | tests/adversarial/adv_helpers.py | models: gemini (explicit) | High value long-term but changes architecture and runtime budget; defer to a dedicated spike.
```

---

## CYCLE 1 VERDICT

**The code does NOT need fundamental rework.** The architecture, coverage, law compliance, and documentation are all at an exceptionally high level — both available models confirmed this independently. The suite is ready for a targeted second pass focused exclusively on operational maturity gaps (exception safety, logging, dependency pinning, CI wiring) rather than any structural changes.

**Verdict: APPROVED FOR SECOND PASS — operational hardening only.**

---

## SECOND PASS PROMPT (ready to fire into Claude Code)

```
Read ~/protocol_pulse/docs/gospels/PP_TESTS_GOSPEL.md.
Read ~/protocol_pulse/docs/audits/pp-tests_audit_ALL_CONSENSUS_C1.md.

This is the SECOND PASS for pp-tests_audit_ALL.
The first build was reviewed by 2 independent AI models across 1 cycle.
(Grok-3 was disqualified on budget; consensus is 2-of-2 gpt4o + gemini.)
Implement every P0 and P1 item from the consensus. Use judgment on P2.

PRIORITY ACTION PLAN:

P0 CRITICAL | Narrow exception catch in call_gate; re-raise BaseException subclasses
            | tests/adversarial/test_f4_vacuity.py:1947–1956
            | Currently catches all exceptions and returns RAISED, which can silently
            | absorb infrastructure crashes. Fix: catch only (ValueError, RuntimeError,
            | TypeError, AssertionError) or the specific exception types the gate
            | contract promises to raise. For anything inheriting from BaseException but
            | not Exception (KeyboardInterrupt, SystemExit, GeneratorExit) re-raise
            | unconditionally. Add a logging.warning() call before returning RAISED so
            | the absorbed exception is always visible in pytest output.

P1 HIGH     | Add structured logging at subprocess boundaries and gate call sites
            | adv_helpers.py:388, 640, 998 + test_f4_vacuity.py gate calls
            | Use logging.debug for pre-call entry (command + key args), logging.info
            | for post-call summary (returncode, stdout[:200]), logging.warning for
            | unexpected return codes. Use pytest's caplog fixture or a module-level
            | logger named "pp_tests". Do NOT add print() statements.

P1 HIGH     | Create enforceable dependency pin file
            | tests/adversarial/requirements-adv-tests.txt (new file)
            | Populate from the library versions listed in pp-tests_STATE.md.
            | Pin to exact versions (==) for all direct dependencies.
            | Add a note in pp-tests_STATE.md pointing to this file.
            | Optionally: add a conftest.py session-scoped check that
            | importlib.metadata.version() matches the pinned versions and
            | calls pytest.skip("wrong library version") with an explanatory message
            | if they diverge — do NOT fail hard, since this may run in an env
            | the developer controls intentionally.

P1 HIGH     | Add minimal CI pipeline definition
            | .github/workflows/pp-tests.yml (new file)
            | Trigger: on pull_request targeting main/pp-tests branches.
            | Runner: ubuntu-latest (CPU only — no GPU runner).
            | Steps: checkout → setup-python (pin to version in STATE.md) →
            | pip install -r tests/adversarial/requirements-adv-tests.txt →
            | pytest tests/adversarial/ -x --tb=short -q
            | Add a 5-minute job timeout to enforce the one-command-under-5-minutes law.
            | Do NOT add any secrets or tokens; network is blocked by conftest anyway.

P2 MEDIUM   | Add Dockerfile.test for reproducible CI runs
            | Dockerfile.test (new file, repo root)
            | Base: python:3.X-slim (match version from STATE.md).
            | Install: ffmpeg at the pinned version from STATE.md, then
            | pip install -r tests/adversarial/requirements-adv-tests.txt.
            | ENTRYPOINT: ["pytest", "tests/adversarial/", "-x", "--tb=short"]
            | Add a docker-compose.test.yml for one-command local container runs.
            | Update pp-tests_STATE.md with the docker run invocation.
            | The bare-metal pytest command must continue to work unchanged.

VALIDATED — do NOT touch these (both models confirmed excellent):
- CPU-only enforcement in conftest.py (multi-layer guard, nvidia-smi check at session end)
- NetworkBlocked(BaseException) inheritance — intentional, correct, do not change to Exception
- adv_helpers.py gen_cases / TEEN_TY / ACTOR_SWAPS case generation logic
- Family 3 (Auth) mutation coverage — exhaustive list, do not reduce
- Family 4 (Vacuity) defense-in-depth test (test_whatever_a_gate_returns_on_nothing_release_blocks_it)
- xfail discipline: pytest.fail for broken setup vs assert for the defect — do not collapse
- Documentation ecosystem (REQUESTS.md, STATE.md, BIBLE_ADDITIONS.md, AUDIT_RESPONSE.md)
- release_run fixture function (adv_helpers.py:577)
- Synthetic media approach with known audio timings (adv_helpers.py:476)
- Family 5 reference integrity tests — do not relax any constraints

After implementing all P0 and P1 items, and any P2 items you judge feasible:
1. Run: pytest tests/adversarial/ -x --tb=short
   → Must show zero FAILs. xfails are acceptable. ERRORs are not.
2. Verify: the new CI yml passes yamllint or GitHub's action schema validator.
3. Verify: requirements-adv-tests.txt covers every import in tests/adversarial/.

git add -A && git commit -m "feat(pp-tests_audit_ALL): post-audit pass — consensus improvements (exception safety, logging, dep pinning, CI)"
git push origin pp-tests
```