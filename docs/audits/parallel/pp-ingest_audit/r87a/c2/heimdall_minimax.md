# heimdall_minimax (minimax/minimax-m3.1-flash, 419.5 s, $0.010, finish length)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (pp-ingest, diff a6921162 vs 2ec81efc)

*Note on honesty: I did not answer in Cycle 1, so I have no Cycle-1 scores of my own to revise. The Cycle-1 column below is my reconstruction of what I would have scored after reading the diff alone; the Cycle-2 column is my actual verdict after reading the three other reviews and re-deriving the code.*

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**qwen's P0 (unbounded join) and P1 (KeyError on a dead thread) — both real, both already fixed in the Cycle-1 patch (C1-1, C1-2).** I re-derived the current `_start_probe` and confirm the fixes are real and correctly implemented:

- `downsignal.py:376` — `a.join(max(0.0, end - time.monotonic()))` against one shared deadline. The join is bounded. ✔
- `downsignal.py:377-379` — the outcome is read **by key** (`outs[b] if b in outs else …`), so a thread that died without writing cannot raise `KeyError`. ✔
- The precedence in that comprehension is right: `outs[b] if b in outs else ((False, …) if a.is_alive() else (None, …))` — a written outcome always wins over the liveness test, so a thread that wrote its outcome microseconds before the deadline is not misread as "ended without an outcome". ✔

**muse's "strict `<` on equal timestamps" — benign, I agree.** If the familyless failure and the first family failure share a timestamp, the family note starts the clock at the same instant; no time is lost.

**muse's "the probe's `outs` dict is written by 3 threads without a lock" — benign, I agree.** Distinct keys, CPython atomic item assignment, and the read happens after the joins.

**glm's Q1 analysis — I agree with the conclusion** (the reported time is the latest *successful* answer's completion time, never later than a real answer).

**What I did not catch in Cycle 1 (and neither did they):** the *dropped* familyless failure (finding N1 below), the *discarded late answer* (N3), the *throttle can eat the whole probe budget* (N3), and the *hung thread holding a global in-flight slot forever* (N4). These are all in the new parallel-probe path and none of the three reviews surfaced them.

---

## 2. WHERE I AGREE / DISAGREE

| Reviewer finding | My verdict | Why |
|---|---|---|
| qwen P0: unbounded join held back the answer that resets the clock | **Agree (fixed)** | `downsignal.py:372-376`. The deadline is `max(timeout_s) + 15 s`; a hung family can no longer delay the report. |
| qwen P1: a family thread that ended without an outcome made `run()` raise `KeyError` | **Agree (fixed)** | `downsignal.py:377-379`. Read by key; a dead thread is `(None, …)` → not counted, and the other families' answers are still reported. |
| qwen: spend meter under-reporting (`spend.py:115-118`) | **Disagree** | `measure()` resets `local_since` only on a *successful* reading; on failure `local_since` keeps accumulating and `measured_spend` keeps its last value, so `estimate()` never loses spend. `add_local` is called on every attempt, failed ones included (`providers.py:959,976`). Correct as written. |
| qwen: `offset_before` bisection edge case | **Out of scope** | `ledger.py` is untouched by this diff. |
| glm: the familyless-first-failure ordering | **Partially agree — glm understates it** | glm reads the code as "the familyless note is reordered to keep strict time order". It is not reordered: when the familyless failure is *later* than the earliest family failure it is **never noted at all** (`downsignal.py:327-329`). Harmless for the clock (the family note already started it), but it is a dropped note, not a reordered one. See N1. |
| glm: `outs` relies on GIL dict-assignment atomicity | **Agree** | Acceptable in this codebase's idiom; the joins provide the happens-before. |
| muse: no logic error in the diff; the family path is correct | **Agree, with the N1 caveat** | The family bookkeeping itself is right: first failure per family wins, an answer clears the families, the older-module path is byte-for-byte the old behaviour. |
| muse: the probe's `answered` is `True` if any family answered | **Agree** | Matches the ruling ("any answer is the probe's answer"). |
| consensus: "the latest-answer time: never later than a real answer" | **Agree** | `at = [ts for a, _, ts in got if a is True]`; `max(at)` is the latest *successful* family's completion stamp. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — a familyless failure later than the earliest family failure is silently dropped.**
`downsignal.py:325-331`:
```python
if p["fail"] < fams[0][1]:
    notes.append((False, p["fail"], None))
notes += [(False, t, f) for f, t in fams]
```
`p["fail"]` is the *first* failure of the window (any back-end). If that first failure belonged to a family, `p["fail"] == fams[0][1]`, the `<` is false, and the familyless failure — which may exist later in the window — is **never noted**. The clock is unaffected (the family note already started it), but the module never sees that failure, `failures_noted` under-counts, and the evidence file loses the event. The design text ("a first failure of a back-end naming no family is noted first, without one") reads as *always noted, first if it is first*. Fix: always emit the familyless note, in time order, and de-duplicate the case where `p["fail"]` *is* the earliest family failure (i.e. only emit it when the first failure had no family).

**N2 (P2) — the probe's "answered" is stricter than the module's.**
`downsignal.py:49` defines `ANSWERED = {"ok", "invalid"}` for real calls, but the probe's `ask()` treats a `rejected` outcome as *not* answered (`downsignal.py:361-365`). A probe reply that the gateway produced but the validator rejected is, by the module's own definition, an answer. In practice this is unreachable — the probe's validator is `_any_text` (`downsignal.py:88-91`), which accepts any non-empty text, and the back-end already raises `empty` for an empty body — but the two definitions of "answered" should be one, or the divergence will bite when the probe prompt/validator changes.

**N3 (P2) — the probe's budget can be consumed entirely by the throttle, and a late answer is discarded.**
`Router._try` calls `th.wait()` *before* the call (`providers.py:942`). A probe back-end that took a 429 has `throttle.until` up to `max_s = 60 s` in the future. The probe's whole budget is `60 + 15 = 75 s` (`downsignal.py:352-353`). So a throttled family sleeps ~60 s, starts its call, and cannot finish inside the deadline: the thread is still alive at the deadline → counted as not answered → and the answer that arrives at ~120 s is **written to `outs` after `run()` has already read it**, so it is silently discarded and never reported. If all three families are throttled at once (a gateway-wide 429), the probe reports "not answered" and `probe_result(False)` resets the module's three-good-probe streak — plan_b then fails to close even though the gateway is healthy. The clock is not wrongly started (a failed probe never starts it), so this is a false-negative on *recovery*, not a false outage.

**N4 (P2) — a hung probe thread keeps a back-end slot and a global in-flight slot forever.**
The `ask` threads are never cancelled at the deadline (`downsignal.py:355-367`); they are daemon threads that run until the HTTP timeout, or forever if the socket hangs. A hung thread holds `sems[bid]` (the probe back-end's `max_inflight: 1`) and one of the router's 20 global slots (`providers.py:769-771`) indefinitely. Consequences: (a) up to 3 of the 20 global slots can be lost; (b) the *next* probe of that family blocks on `sems[bid]` and is therefore never answered — that family is silently out of the probe forever. The probe still works (the other families answer), but the family coverage the whole change exists to provide degrades to zero for that family, with no alarm.

**N5 (P2) — `wait` is derived from the *maximum* `timeout_s` in the probe chain.**
`downsignal.py:352-353`. Today all three probe back-ends are 60 s, so `wait = 75 s`. But the value is a config-driven constant: adding one probe back-end with `timeout_s: 600` stretches the probe's slot to 615 s, well past the module's 120 s probe interval — the slot can then be claimed by another prober while this probe is still running, and the probe's answer arrives stale. The wait should be per-back-end (each thread's own deadline) or the max should be capped.

**N6 (P3) — the evidence line can say "not answered" for a family that did answer.**
`downsignal.py:377`: a family still asking at the deadline is recorded as `"{b}: no answer within the probe's {wait:.0f} s"`. If it answered one second later, the audit trail in `down_signal.jsonl` is wrong about it. The `why` string should say "still asking at the deadline" rather than "no answer".

**N7 (P3) — the counter's meaning changed.** `failures_noted` (`downsignal.py:341`) now counts *family notes*, not flushes; `live.json`'s `counts` block changes shape without a note. Cosmetic, but the STATE/live readers should know.

**N8 (P3) — with an older module the probe now makes up to three calls instead of one or two.** The module-facing calls are exactly as before (verified: `note` without `family`, `probe_due` without `families`), but the probe's *internal* behaviour changed for every module, old or new. That is the amendment's intent, but it is a spend increase (three 512-token calls every 2 min while the clock runs) that the older-module path now also incurs.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 (reconstructed) | Cycle 2 | Why changed |
|---|---|---|---|
| `downsignal._start_probe` (parallel, bounded) | 7.0 | **8.0** | The bounded join and the by-key read are correct and well-tested; N3/N4/N