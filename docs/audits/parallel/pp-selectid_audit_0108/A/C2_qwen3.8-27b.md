# qwen3.8-27b (qwen/qwen3.8-27b) 80 s finish=stop usage in 43197 / out 3518 usd~0.182 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0108A
# Reviewer: Claude (Cycle 2)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok-4.20 (SHIP yes, no P0/P1):** I missed the explicit verification that `today` routing is *unchanged* except for the 20:33 chain additions and the 120s Heimdall deadline. Grok confirmed this by checking that `today_unbounded` correctly excludes `context_verdict` from the deadline set, and that the per-type lists under `today` only override the three roles named in Ruling 88(d)/(e). I had assumed this but did not trace it line-by-line.

**Qwen3.8-27B (SHIP no, two P0s):**
- **P0-1 (LocalJudgeBackend blocks 40 min):** I *did* catch this in Cycle 1 (my P0-3, which I re-derived to P1 in my own text). Qwen escalated it to P0 on architectural grounds (blocking the worker). The consensus ruling refuted it: Ruling 87 *names* this case, `deadline_floor_s: 2400` is the agreed wait, and the second screen runs in a thread pool. I agree with the refutation — this is **by design**, not a bug. However, I now see a sharper variant Qwen did not: the `_within` wrapper (ruling 5) is supposed to "fail over instead of waiting," but for `LocalJudgeBackend` the deadline floor *overrides* the fail-over. If the local judge is the *only* backend in the Plan B chain for `context_verdict` (which it is, per `plan_b.context_verdict`), there is no fail-over target. The 40-minute block is the *intended* behavior, but it means a single stuck GPU0 render freezes the entire pin stage for 40 minutes with no escape. This is a **P1 operational risk**, not a P0 code bug.
- **P0-2 (_SEEN race):** I caught this in Cycle 1 (my P0-1, re-derived to P2). The consensus notes the fix: `_SEEN_LOCK` now guards both read and write. I verify the fix is correct in the diff (lines 148–150, 164–168). **Resolved.**

**GLM-5.3-FLASH (cut at 24k tokens):** I missed several items GLM raised before its budget ran out:
- **P0-1 (Plan B chain only for named roles):** I caught this in Cycle 1 (my P1). The test at line 1233 confirms `chain("mine")` stays Heimdall under Plan B. This is **by design** per the test. **P2.**
- **P0-3 (torn answer file):** I caught this in Cycle 1 (my P0-3, re-derived to P1). The fix is in the diff (lines 536–537: `torn` variable, polled again). **Resolved.**
- **P0-7 (HealthUnreadable escaping Router.call):** I caught this in Cycle 1 (my P1). The fix is in the diff (lines 652–654: `HealthUnreadable` caught, re-raised as `ProviderError`). **Resolved.**
- **P1 (announce() outside lock):** I caught this in Cycle 1 (my P1). The fix is in the diff (lines 124–138: `_prepend` uses `_Locked`). **Resolved.**

**What I genuinely missed:**
1. **The `probe_once` down-mark restoration logic** (lines 736–742): When a probe fails, the down mark is restored *only if* `was is not None and n not in self.down`. This is correct, but I did not verify it in Cycle 1. The test at line 1246 confirms it.
2. **The `call_parsed` loop prevention** (lines 591–592): If a model that was skipped (due to out-of-contract answer) answers again, it raises `ProviderError`. This prevents infinite loops. I did not trace this in Cycle 1.
3. **The shadow's own recording** (lines 753, 762–765): The shadow uses role `"shadow86:<role>"`, so its recordings are separate from the deciding backend's. The test at line 1572 confirms `shadow["cached"]` is `True` on the second call. I did not verify this in Cycle 1.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | Source | My Verdict | Reason |
|---|---|---|---|
| P0-1: LocalJudgeBackend blocks 40 min | Qwen | **Disagree (P1, not P0)** | By design per Ruling 87. `deadline_floor_s: 2400` is the agreed wait. No fail-over target in Plan B for `context_verdict`. Operational risk, not code bug. |
| P0-2: _SEEN race | Qwen | **Agree (resolved)** | Fixed with `_SEEN_LOCK`. Verified in diff. |
| P0-3: Torn answer file | GLM | **Agree (resolved)** | Fixed with `torn` variable. Verified in diff. |
| P0-7: HealthUnreadable escape | GLM | **Agree (resolved)** | Fixed with `ProviderError` re-raise. Verified in diff. |
| P1: announce() outside lock | GLM | **Agree (resolved)** | Fixed with `_Locked` in `_prepend`. Verified in diff. |
| P1: Plan B chain only for named roles | GLM | **Agree (P2, by design)** | Test confirms `chain("mine")` stays Heimdall. |
| P2: today routing unchanged | Grok | **Agree** | Verified: `today_unbounded` excludes `context_verdict`; per-type lists only override 3 roles. |
| P2: coherence gap (xAI down + deepseek writing) | Grok | **Agree (documented)** | Ruling 88(d) takes glm out, (e) bars qwen. Gap is documented by `TestRuling85NoXai`. |
| P2: shadow never decides | Grok | **Agree** | Verified: shadow runs in thread, never raises into build, recorded separately. |
| P2: spend on same ledger | Grok | **Agree** | Verified: shadows, probes, and Plan B calls all use `self._reserve` / `self._settle`. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `probe_once` can mark a family down *during* a probe, then restore it, but the restoration is racy with the main thread.**
`providers.py:736–742`:
```python
was = self.down.pop(n, None)
try:
    r = self.call(f"probe87:{n}", ...)
    ok = ok or bool(r.text.strip())
except Exception:
    if was is not None and n not in self.down:
        self.down[n] = was
```
The `self.down` dict is shared between the probe thread and the main build thread. If the main thread marks `n` down *between* the `pop` and the `except` block, the restoration `self.down[n] = was` will overwrite the main thread's mark. This is a **lost update** on `self.down`. The impact is low (the family will be re-marked down on its next failure), but it is a data race. **P2** (low impact, self-correcting).

**P1-NEW-2: `LocalJudgeBackend.complete` does not clean up the request file on timeout.**
`providers.py:544–546`:
```python
if time.time() - t0 >= self.WAIT_S:
    raise Unavailable(...)
```
The request file `tests/package/proof/judge_requests/<rid>.json` is left on disk. If the integrator's judge service is slow but eventually answers, the answer file will be written, but the request file remains. This is not a correctness issue (the answer is keyed by `rid` and `pid`), but it is a **disk leak** over many builds. **P2.**

**P1-NEW-3: `GeminiBackend.complete` does not handle `safetyAttributes` or `promptFeedback` in the response.**
`providers.py:489–492`:
```python
parts = j["candidates"][0]["content"]["parts"]
text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
```
If Gemini returns a `promptFeedback` with a `blockReason` (e.g., `PROHIBITED_CONTENT`), `j["candidates"]` may be empty, and the `IndexError` is caught and re-raised as `RequestRejected`. This is correct fail-closed behavior. However, if `candidates[0]` exists but `content` is `None` (which can happen with some safety blocks), the `TypeError` is caught. **No issue.**

**P1-NEW-4: The `routing` field in `model_providers.json` is `"today"`, but the `--routing` CLI argument defaults to `None`, which falls back to the config's `routing.mode`.**
`proof_ledger.py:943`:
```python
routing = a.routing or rt.get("mode") or "today"
```
This is correct. However, if the config's `routing.mode` is changed to `"heimdall_first"` without updating the CLI, the build will use `heimdall_first` silently. This is **by design** (the config is the source of truth), but it is a **configuration risk**. **P2.**

**P1-NEW-5: `shadow_wait` uses a single `end` time for all threads, so if one shadow takes 800s and another takes 100s, the second is joined with `max(0.0, end - time.time())` which is ~100s, not 900s.**
`providers.py:785–788`:
```python
end = time.time() + timeout_s
for t in list(self._shadows):
    t.join(max(0.0, end - time.time()))
```
This is **correct**: the total wait is bounded by `timeout_s`, not the sum of individual waits. The second thread is joined with the *remaining* time, so the total wait is at most `timeout_s`. **No issue.**

**P1-NEW-6: The `plan_b_chains` filter in `proof_ly.py` excludes `local:` and `openai_stt:` prefixes, but not `local_judge:`.**
`proof_ly.py:1008`:
```python
return {r: [b for b in ch if not b.startswith(("local:", "openai_stt:"))]
        for r, ch in ((cfg.get("routing") or {}).get("plan_b") or {}).items()}
```
The `local_judge:gemma3:27b` backend has vendor `local_judge`, not `local`. So it is **not** filtered out. This is **correct**: the local judge is a Plan B backend for `context_verdict`. **No issue.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `heimdall_health.py` | P1 (stale _SEEN, torn file) | **P2** | All P1s resolved. Remaining issues are low-impact (disk leak, down-mark race). |
| `providers.py` (Router) | P1 (HealthUnreadable escape, announce lock) | **P2** | All P1s resolved. New P2s: down-mark race, request file leak. |
| `providers.py` (LocalJudgeBackend) | P1 (40-min block) | **P1** | By design, but operational risk: no fail-over target, disk leak. |
| `providers.py` (GeminiBackend) | P2 | **P2** | No new issues. |
| `model_providers.json` | P2 | **P2** | Configuration risk (silent routing change). |
| `proof_ledger.py` | P2 | **P2** | No new issues. |
| `proof_ly.py` | P2 | **P2** | No new issues. |
| Tests | P2 | **P2** | Comprehensive. The coherence gap is documented. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. **`providers.py:544–546` (LocalJudgeBackend):** The 40-minute block is by design, but there is no fail-over target in Plan B for `context_verdict`. A stuck GPU0 render freezes the pin stage for 40 minutes. **Condition:** Acceptable if the integrator's judge service has a hard timeout < 40 min and the build is run in a thread pool (which it is, per the consensus). **No code change required**, but document the operational risk.
2. **`providers.py:736–742` (probe_once down-mark race):** The `self.down` dict is shared between the probe thread and the main thread. A lost update can occur. **Fix:** Use a lock for `self.down` accesses, or accept the low impact (self-correcting). **P2 if accepted.**

**P2 MEDIUM:**
1. **`providers.py:544–546` (LocalJudgeBackend):** Request file not cleaned up on timeout. Disk leak over many builds. **Fix:** `os.unlink(final)` in a `finally` block.
2. **`model_providers.json:304` (routing.mode):** Silent routing change if config is updated without CLI. **Fix:** Log the routing mode at build start (already done at `proof_ledger.py:952`).
3. **`providers.py:736–742` (probe_once down-mark race):** See P1-2.
4. **`heimdall_health.py:149–150` (stale _SEEN return):** The return value of `note()` is discarded by `Router._note`, so the staleness is only informational. **No fix required.**

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Add a lock for `self.down` accesses in `Router` to prevent the probe thread and main thread from racing on the down-mark dict.** This is the only remaining data race in the code, and it is the most likely source of subtle, hard-to-reproduce bugs in production.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Accept the 40-minute LocalJudgeBackend block** as by design (Ruling 87). Ensure the integrator's judge service has a hard timeout < 40 min.
2. **Accept the probe down-mark race** as low-impact (self-correcting), or add a lock for `self.down` accesses.
3. **Clean up the LocalJudgeBackend request file** on timeout to prevent disk leak.
4. **Document the coherence gap** (xAI down + deepseek writing) in the build report, as it is a known, ruled limitation.

**SHIP: yes with conditions**