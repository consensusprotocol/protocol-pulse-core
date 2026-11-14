# heimdall_qwen (qwen/qwen3.8-27b, 196.6 s, $0.020, finish stop)

## SECTION 1: CORRECTNESS

The change is minimal and surgically precise. It addresses a specific integration point (R12) where the builder's `probe_due` function now accepts a `who` parameter to claim probe slots.

**Signature Check (downsignal.py:118-121):**
The code uses `inspect.signature(self.hh.probe_due).parameters` to check for the `who` parameter. This is sound for a plain Python function. The `try/except (TypeError, ValueError)` fallback handles edge cases where `inspect.signature` might fail (e.g., if `probe_due` were a C extension or a built-in, though unlikely here). The fallback sets `takes_who = False`, which is the safe default (don't pass `who` if unsure).

**Probe Lifecycle (downsignal.py:167-171):**
The `tick()` method calls `self._call("probe_due", now=_utc(now), **self.probe_kw)`. This correctly passes the `who` parameter only if the module supports it. The rest of the probe lifecycle (`_start_probe`, `_report_probe`, `_probing`) is unchanged and remains correct. The claim mechanism in the builder's module (stamping `last_probe_utc` and `last_probe_by` under the flock) ensures that if this watcher claims a slot but fails to report, the slot is still spent, preventing double-probing. This is the intended behavior per R12.

**No Race Conditions:**
The `probe_kw` is set once in `__init__` and never modified. The `tick()` method is called from a single thread (the signal loop), so there is no concurrent access to `probe_kw`. The builder's module handles its own locking for the state file.

**Edge Cases:**
- If the module is older (no `who` parameter), `probe_kw` is `{}`, and `probe_due` is called without `who`. This is correct.
- If the module is newer (has `who` parameter), `probe_kw` is `{"who": "pp-ingest probe"}`, and `probe_due` is called with `who`. This is correct.
- If `inspect.signature` fails, `takes_who` is `False`, and `probe_kw` is `{}`. This is safe.

**Verdict:** The change is correct. It does what it claims: it takes up the builder's probe claim by passing the `who` parameter when supported.

## SECTION 2: LAW COMPLIANCE

- **L-x (NO SINGLE MODEL, ULTRON FIRST):** COMPLIANT. The change does not affect the provider interface or model selection. The probe role still uses the configured back-ends.
- **L-l (a model reply counts only whole):** COMPLIANT. The change does not affect reply validation.
- **L-j / L-m (fail closed; nothing measured is never a pass):** COMPLIANT. The change does not affect fail-closed behavior. If the module cannot be loaded, the signal is marked as "not read" (downsignal.py:125).
- **L-h / L-k (transcript text is read as spoken):** COMPLIANT. The change does not affect transcript handling.
- **L-e (word timing for anything heard):** COMPLIANT. The change does not affect word timing.
- **L-u (hard exclusions):** COMPLIANT. The change does not affect exclusions.
- **L-v (speaker / transcript truth; re-uploads):** COMPLIANT. The change does not affect re-upload detection.
- **Secrets:** COMPLIANT. The change does not introduce any secrets.
- **SPEND FREEZE:** COMPLIANT. The change does not affect the spend freeze.

**Verdict:** All laws are compliant. The change is a narrow integration point that does not touch any law-relevant code.

## SECTION 3: SECURITY

- **SQL injection:** N/A. The change does not involve SQL.
- **Authentication bypasses:** N/A. The change does not involve authentication.
- **Rate limiting gaps:** N/A. The change does not involve rate limiting.
- **Secrets in code:** COMPLIANT. No secrets are introduced.
- **Unvalidated user input:** N/A. The change does not involve user input.

**Verdict:** No security issues.

## SECTION 4: FRONTEND QUALITY

N/A. This is a backend service with no frontend.

## SECTION 5: BACKEND QUALITY

- **DB operations:** N/A. The change does not involve DB operations.
- **External API calls:** COMPLIANT. The change does not introduce new external API calls. The probe call is already handled by the existing `router.run` mechanism.
- **Cron job:** N/A. The change does not involve cron jobs.
- **Memory leaks:** COMPLIANT. The change does not introduce any large objects.
- **Logging:** COMPLIANT. The change does not introduce any new logging. The existing logging in `tick()` and `_start_probe` is sufficient.

**Verdict:** Backend quality is maintained. The change is minimal and does not introduce any new risks.

## SECTION 6: WORLD-CLASS GAP ANALYSIS

This is a backend service, so "world-class" in the context of Bloomberg Terminal or Coinbase Advanced is not directly applicable. However, in the context of a robust, production-grade backend service:

- **Observability:** The change adds `probe_claimed_as` to the snapshot (downsignal.py:360), which is a good addition for observability. It allows operators to see which prober claimed the last probe slot.
- **Resilience:** The change is resilient to module version differences (older modules without `who` parameter). This is a good practice for backward compatibility.
- **Documentation:** The change is well-documented in the docstring (downsignal.py:118-121) and the commit message.

**Verdict:** The change is well-executed and does not introduce any gaps. The service is already production-grade, and this change maintains that standard.

## SECTION 7: SCORES (0-100 each)

- Backend logic: 95/100
- Frontend/UI: N/A
- Error handling: 95/100
- Security: 100/100
- Performance: 100/100
- Law compliance: 100/100
- World-class gap: 95/100
- OVERALL: 95/100

## SECTION 8: PRIORITY ACTION PLAN

P3 LOW | Add a test for the case where `inspect.signature` fails | downsignal.py:118-121 | The fallback is safe, but a test would confirm it works as expected.

## SECTION 9: THE ONE THING

The change is correct and well-executed; the only improvement would be to add a test for the `inspect.signature` fallback to ensure it works as expected in edge cases.

## SECTION 10: FINAL VERDICT

This code is ready for production. The change is minimal, correct, and well-documented. It addresses a specific integration point (R12) without introducing any new risks or breaking existing functionality. The only recommendation is to add a test for the `inspect.signature` fallback, but this is a low-priority enhancement.