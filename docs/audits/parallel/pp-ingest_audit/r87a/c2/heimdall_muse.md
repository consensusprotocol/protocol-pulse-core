# heimdall_muse (meta-models/muse-spark-open-816b-a42b, 267.0 s, $0.030, finish stop)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT: pp-ingest (a6921162 vs 2ec81efc, with C1 fixes at 3259bae1)

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Qwen caught the unbounded join (P0).** My Cycle 1 called `_start_probe` "Correct" — `join()` with no timeout. A hung family (glm's 391s runaway) would hold `probe_out=None` indefinitely, `probe_thread.is_alive()=True`, `_probing()=True`, no new probe, clock never reset. I noted "daemon=True, joined before reading" as correct and moved on. Wrong. The fix (bounded wait = max timeout + 15s, `join(deadline)`, treat still-alive as `False`) is verified by the new test `test_a_family_that_hangs_never_holds_back_the_answer`.

**Qwen caught the KeyError on thread death (P1).** If `ask()` raised `BaseException` not caught by its two handlers, `outs[bid]` never set, `got = [outs[b] for b in sorted(outs)]` would `KeyError` inside the daemon thread, `probe_out` never set, probe lost. I listed "Probe thread exception: Caught as None (not asked) — Correct" — I assumed the `except Exception` covered it. It didn't cover `BaseException`/`SystemExit`. Fix: `except Exception` → `outs[bid]=(None,...)` plus `got` now checks `b in outs` and `a.is_alive()`.

**GLM's deep read of `_flush` ordering was more careful than mine.** I called the `p["fail"] < fams[0][1]` branch "Benign" in one line. GLM walked the actual time-order semantics and the interaction with the module's `failing_since_utc` — correct that the code's strict `<` is the right time-order, not the design's looser wording. I was right on verdict, shallow on reasoning.

**I missed nothing that GLM flagged as a defect that survived C1.** GLM's F31/F22/#4 were correctly refuted in consensus as by-design.

## 2. WHERE I AGREE / DISAGREE

| Finding | Verdict | Why |
|---------|---------|-----|
| **Qwen P0: unbounded join** | **Agree — was P0, now fixed** | Verified by mutation test. My Cycle 1 missed it. |
| **Qwen P1: KeyError on thread death** | **Agree — was P1, now fixed** | `SystemExit` test proves it. My Cycle 1 mis-classified. |
| **Qwen: spend meter under-reporting** | **Disagree — not a bug** | `local_since` reset on `measure()` is correct; `measured_spend` is fleet total by design. Qwen's own analysis concludes "This looks correct." |
| **Qwen: `offset_before` bisection** | **Out of scope** | Not in diff; truncated in output. No finding to evaluate. |
| **Muse (my) P1: strict `<` benign** | **Agree with self, with GLM's nuance** | Same timestamp → same clock start. No time lost. |
| **Muse (my) P1: staging base URL** | **Agree — recorded, not a bug** | `base_url_env` override exists. Pre-existing. |
| **GLM: no P0, probe time correct** | **Agree** | `max(at)` over `a is True` only, `ts=None` for failures — correct. |
| **GLM: GIL dict atomicity note** | **Agree — acceptable** | Distinct keys, joined before read. Now also guarded by `b in outs` check. |
| **Consensus C1-3: real module test** | **Agree — valuable** | Fake-module tests missed the `failing_families` interaction; real module test closes gap. |

## 3. NEW FINDINGS FROM COMBINED ANALYSIS

**None that change the ship decision.** The diff is now narrow and well-tested. Three observations worth recording (P2, not blocking):

1. **`downsignal.py:377-378` — `got` comprehension re-evaluates `a.is_alive()` after timed join.** A thread that finishes *between* the `join(timeout)` return and the `got` comprehension will be `not alive` but `b in outs` true → correctly counted as answered/failed, not as "no answer within probe's Xs". Correct, but subtle — relies on `outs` write happening before thread exit. Documented by test.

2. **`downsignal.py:150-155` — `probe_due(families=...)` only when signature takes it.** If builder adds a new required param to `probe_due` without `families`, `_takes` check passes for `families` but call still fails on missing required param. Low risk — builder's API is additive, and `_call` catches and `_fail`s without crashing.

3. **`providers.json:95-103` — `heimdall_muse_probe` at 512 tokens with `reasoning: none`.** GLM noted muse at 512 tokens may still reason and hit `finish_reason: length` → `empty` → probe leg fails. With `effort: none` this is mitigated, but if muse ignores `effort: none` under load, that leg fails while qwen/glm answer — still `answered=True` overall. Acceptable; the probe is `any` not `all`.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| **downsignal probe** | 7/10 (missed P0) | 9/10 | P0+P1 fixed, bounded wait + safe `got`, mutation-tested |
| **downsignal families** | 9/10 | 9/10 | No change — correct, now tested against real module |
| **providers.json** | 9/10 | 9/10 | No change — families + probe chain correct |
| **Overall pp-ingest** | 8/10 "ready" | 9/10 "ready" | C1 P0 was the only ship-blocker; fixed |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL — none.** C1 P0/P1 fixed and tested.

**P1 HIGH — none.**

**P2 MEDIUM (record, don't block):**
- `downsignal.py:372-378` — Add comment that `a.is_alive()` check after timed join is intentional (thread that just finished is counted via `outs`, not as timeout). Prevents future "simplification" regression.
- `providers.json:95` — Monitor `heimdall_muse_probe` `finish_reason: length` rate at 512 tokens; bump to 1024 if >5% of probes lose muse leg to truncation.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The bounded probe wait (`max timeout + 15s` with `join(deadline)`) — it turned a single hung family from a 15-minute false outage into a 75-second probe that still reports the other families' answers.

## 7. PRODUCTION READY?

**Yes.** C1 P0/P1 fixed, 7 mutation tests each fail without fix, family path verified against real builder module + flock, backward compat with older module preserved (`_takes` gate). No conditions.

### Answers to the 4 reviewer questions

1. **Probe time later than latest real answer?** No. `at = [ts for a is True]` where `ts = self.clock()` stamped *after* `router.run` returns per thread; `max(at)` is latest answer's completion. Failures carry `ts=None`, excluded. When no answer, `t = self.clock()` at report time — only affects `answered=False/None` path where module doesn't reset clock on time.

2. **Failure lost or out of order?** No. `noted()` first-write-wins per family (`if fam not in`), `pending["fail"]` first-write-wins, answer clears both. `_flush` builds `notes` answer-first then families sorted by time, familyless prepended only if strictly earlier — correct time order.

3. **Older module (no family/families)?** Yes, exactly as before. `_takes(note,"family")` false → `note_family=False` → `else: notes.append((False, p["fail"], None))` single note. `_takes(probe_due,"families")` false → `probe_kw` has only `who` (or empty), no `families` kwarg.

4. **Parallel probe holds lock/thread/slot past deadline or double-starts?** No. No lock held during `router.run` (only `self.lock` for `probe_out` write). Threads are `daemon=True`, joined with deadline, left to die — each holds `sems[bid]` (1 slot) + `gsem` only for its `router.run` duration, then releases. `_probing()` checks `is_alive()` + `probe_out is not None`, so no second probe starts in same slot; `_report_probe()` runs before `probe_due()` check each tick.