# qwen3.8-27b (qwen/qwen3.8-27b) 73 s finish=stop usage in 16280 / out 3314 usd~0.099 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1810
# Reviewer: [Your Model]

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

**Grok's P0 (REPOST_ALIGN_MIN NameError):**
I missed this in Cycle 1. Grok correctly identified that `REPOST_ALIGN_MIN` is used in `same_speech()` (line 85) but not defined in the diff. However, the **Cycle 1 Consensus** (Claude) refuted this: it is a module-level constant from ruling 53 at `pipeline/package.py:877`, resolved at call time. The test `TestRuling76Window` calls `PK.same_speech` and passes, proving no `NameError`. **Grok was wrong here** — the constant exists in the full file, just not in the diff hunk. I should have verified against the test evidence rather than flagging it as P0.

**Qwen's P0-1 (same_speech violates L-k):**
I partially missed the nuance. Qwen argued `difflib` is "fuzzy" and violates L-k's strict canonical equality. The **Cycle 1 Consensus** correctly refuted this: L-k governs whether a LOCK's text equals spoken words (for sealing). `same_speech` governs **exclusion** of delivered speech. A wrong match loses one moment (fail-closed); a missed match reuses delivered speech (the harm ruling 76(b) forbids). The guards (≥8 words, runs ≥3, 80% of shorter) are appropriate for this purpose. I agree with the consensus refutation.

**Qwen's P0-2 (expired check order / ctx.now):**
I missed the concern about `E.age_hours` raising on malformed data. The **Cycle 1 Consensus** addressed this: `eligibility._parse_time` returns `None` for zoneless/malformed times, so `E.age_hours` returns `None`, and `expired()` returns `True` (fail-closed). No exception. I should have traced this path more carefully.

**GLM's P1-1 (same-speech before expired in usable()):**
I missed this ordering concern. In `usable()`, the `same_speech` check (lines 112–117) runs **before** the `expired` check (line 125). A moment that is both >12h old AND same-speech as a delivered clip reports `why = "ruling 76 (b)"`, not "ruling 76 (a)". Both exclude, so the moment never enters a line-up. But the `why` attribution is order-dependent. The ruling-76(d) count `inside_12h` is computed independently in the driver (line 244), so counts and `why` reasons can disagree about *why* a moment is out. This is a **reporting-accuracy issue**, not a leak. I agree with GLM: P1.

**GLM's P1-3 (transient I/O error permanently expires candidate):**
I missed this. In `proof_ledger.py` (lines 210–215), if `inputs.json` is unreadable (OSError), the `except ... pass` swallows it, and **every** moment of that candidate gets no publish time → the whole candidate expires. `expire()` runs before any candidate is tried, and expiry is "for good." A transient read error at 18:10 permanently closes a candidate whose clips are 2h old. Fail-closed (ruling-compliant), but lossy. I agree with GLM: P1.

**Grok's P1 (seed() reviving expired candidate):**
I missed this. The **Cycle 1 Consensus** refuted it: `seed()` adds a line-up only when its key is not in the registry (`if k not in reg["candidates"]`). It applies "package" only to an entry that is not closed. The test `test_ruling_76_expires_a_candidate_with_a_clip_over_12_h_for_good` (lines 279–283) seeds a later record that passes the same line-up again, and it stays closed/expired. I agree with the consensus refutation.

## 2. WHERE DO YOU AGREE OR DISAGREE?

| Finding | My Position |
|---|---|
| **Grok P0: REPOST_ALIGN_MIN NameError** | **Disagree.** The constant exists at `package.py:877` (ruling 53). Tests pass. No NameError. |
| **Grok P1: seed() revives expired** | **Disagree.** `seed()` checks `if k not in reg["candidates"]` and only applies "package" to non-closed entries. Test proves durability. |
| **Qwen P0-1: same_speech violates L-k** | **Disagree.** L-k governs lock text equality, not exclusion. `same_speech` is fail-closed for exclusion. Guards are appropriate. |
| **Qwen P0-2: expired check order / ctx.now** | **Partially agree.** The order is fine (both exclude). `E.age_hours` does not raise on malformed data (returns `None`). No P0. |
| **GLM P1-1: same-speech before expired** | **Agree.** Reporting-accuracy issue. `why` attribution is order-dependent. P1. |
| **GLM P1-2: same_speech over-count** | **Partially agree.** The 80% threshold with runs ≥3 is sound for the stated purpose. No concrete wrong-merge/miss provable. P2-uncertain. |
| **GLM P1-3: transient I/O error** | **Agree.** Permanent loss on transient error. Fail-closed but lossy. P1. |
| **GLM P1-4: pin-stage uses wall-clock now** | **Agree.** `window_problems` defaults to `datetime.now(timezone.utc)`, which is the render clock at that moment. Correct per ruling 76(c). No issue. |

## 3. NEW FINDINGS FROM THIS REVIEW

**P1-NEW-1: `window_problems` uses `datetime.fromisoformat` with `.replace("Z", "+00:00")` (line 153), but `eligibility._parse_time` (behind `expired()`) may use a different parser.**

In `package_pin.py` line 153:
```python
t = datetime.fromisoformat(str(p).replace("Z", "+00:00"))
```

In `package.py` line 92:
```python
age = E.age_hours(m.get("published_at"), now)
```

The Cycle 1 Consensus states: "eligibility._parse_time (behind usable's `expired`) reads a time WITHOUT a zone as no measurement, so expired. window_problems read it as UTC. Now both refuse it."

But the diff shows `window_problems` explicitly checks `if t.tzinfo is None` (line 157) and rejects zoneless times. If `E.age_hours` also rejects zoneless times (returns `None`), then both paths agree. **However, the diff does not show `E.age_hours`'s implementation.** If `E.age_hours` treats zoneless times as UTC (the pipeline's convention, per the docstring at line 146), then `expired()` would return `False` for a zoneless time, while `window_problems()` returns a problem. This would be a **discrepancy**: a moment could pass `usable()` (not expired) but fail `window_problems()` at pin time.

**Scenario:** A moment with `published_at = "2026-11-13T06:00:00"` (no zone). `E.age_hours` treats it as UTC → age = 12h → not expired → passes `usable()`. `window_problems` sees `tzinfo is None` → problem → pin refused. The moment enters a line-up but the pin is refused. This is **fail-closed** (the pin is refused), but the `why` attribution is inconsistent: `usable()` says "usable," `window_problems()` says "no measurement."

**Verdict:** P1. The two parsers must agree on zoneless times. The diff does not show `E.age_hours`, so I cannot verify they agree. The Cycle 1 Consensus claims they now both refuse, but the evidence is not in the diff.

**P2-NEW-1: `same_speech` uses `difflib.SequenceMatcher` with `autojunk=False` (line 84), which is correct for token lists, but the threshold `REPOST_ALIGN_MIN * short` uses floating-point multiplication.**

`REPOST_ALIGN_MIN = 0.80`, `short` is an integer. `0.80 * 8 = 6.4`. The sum of matching block sizes is an integer. `6 >= 6.4` is `False`. This is correct: 6 words in runs of ≥3 is not 80% of 8. But floating-point precision could cause edge cases: `0.80 * 10 = 8.0`, `8 >= 8.0` is `True`. This is fine. No issue.

**P2-NEW-2: The `--hours` refusal (line 197) checks `0 < a.hours <= package_pin.WINDOW_H`. If `a.hours` is `NaN`, `0 < NaN` is `False`, so it refuses. Correct.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `package.usable()` | P1 (ordering) | P1 (ordering + parser discrepancy) | GLM's P1-1 confirmed; new P1-NEW-1 on zoneless time handling. |
| `same_speech()` | P2 (uncertain) | P2 (uncertain) | No concrete wrong-merge/miss provable. Guards are sound. |
| `candidates.expire()` | P1 (I/O error) | P1 (I/O error) | GLM's P1-3 confirmed. |
| `window_problems()` | P2 (clock) | P1 (parser discrepancy) | New P1-NEW-1: zoneless time handling may differ from `E.age_hours`. |
| `proof_ledger.py` driver | P1 (I/O error) | P1 (I/O error) | Same as above. |
| Tests | OK | OK | Tests cover the new branches and the mutated refusal paths. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:**
1. **`package_pin.py:153` vs `package.py:92`: zoneless time handling discrepancy.** `window_problems` rejects zoneless times (`tzinfo is None`). `expired()` calls `E.age_hours`, whose implementation is not in the diff. If `E.age_hours` treats zoneless times as UTC, a moment could pass `usable()` but fail `window_problems()`. **Fix:** Verify `E.age_hours` rejects zoneless times (returns `None`). If it does not, change `window_problems` to treat zoneless times as UTC (the pipeline's convention) or change `E.age_hours` to reject them. The two must agree.
2. **`proof_ledger.py:210–215`: transient I/O error permanently expires candidate.** If `inputs.json` is unreadable, the `except ... pass` swallows it, and every moment of that candidate gets no publish time → the whole candidate expires. **Fix:** Log the error and retry, or treat a transient I/O error as "unknown age" for that candidate only, not all its moments. Alternatively, accept the loss (fail-closed) but document it.
3. **`package.py:112–125`: `same_speech` before `expired` in `usable()`.** A moment that is both >12h old AND same-speech reports `why = "ruling 76 (b)"`, not "ruling 76 (a)". **Fix:** Reorder the checks so `expired` runs first, or accept the order-dependent `why` attribution and document it.

**P2 MEDIUM:**
1. **`package.py:85`: `same_speech` threshold.** The 80% threshold with runs ≥3 is sound, but the edge case of a 9-word shared phrase in a 10-word shorter text merging even if the 10th word differs is worth noting. **Fix:** No change needed; the ruling's intent is "the same speech re-posted," and 9/10-word overlap is the same speech.
2. **`proof_ledger.py:197`: `--hours` refusal.** The bound `--hours 12` is accepted, and the run goes on past the check. The test's refusal guard stops it at the proof dir. **Fix:** No change needed; the test covers this.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Verify that `E.age_hours` and `window_problems` agree on zoneless time handling.** If they disagree, a moment could pass `usable()` but fail `window_problems()`, causing inconsistent `why` attribution and potential pin refusals that are not reported as "expired" in the line-up. This is the only P1 that could cause a **discrepancy** between the build stage and the pin stage, violating ruling 76(c)'s requirement that the pin stage re-checks (a) on the render clock.

## 7. PRODUCTION READY?

**Yes with conditions.**

**Conditions:**
1. **Verify `E.age_hours` rejects zoneless times** (returns `None`). If it does not, change `window_problems` to treat zoneless times as UTC, or change `E.age_hours` to reject them. The two must agree.
2. **Document the transient I/O error behavior** in `proof_ledger.py:210–215`. If `inputs.json` is unreadable, the candidate expires for good. This is fail-closed (ruling-compliant), but lossy. Add a log message and a comment explaining the behavior.
3. **Reorder `expired` before `same_speech` in `usable()`** (or document the order-dependent `why` attribution). This ensures that a moment that is both >12h old AND same-speech reports `why = "ruling 76 (a)"`, not "ruling 76 (b)".

If these three conditions are met, the change is production-ready. The 12h window is enforced on every path, the registry expiry is for good, the pin-stage re-check uses the render clock, and the window can never be widened by an argument.