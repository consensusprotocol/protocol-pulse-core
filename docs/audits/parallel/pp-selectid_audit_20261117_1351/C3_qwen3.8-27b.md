# qwen3.8-27b (qwen/qwen3.8-27b) 105 s finish=stop usage in 12680 / out 6573 usd_reported=0.005276 usd~0.137 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261117_1351 — RULING 141 (2): STAND_ALONE SOFT

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**GPT-OSS-20B's P1 on `stand_plain`'s raw-string fallback:** This was the single real defect in Cycle 1, and it is now fixed. I confirm the fix below. In Cycle 1 I should have flagged this more prominently; I treated the fallback as "safe" (agreeing with Gemma) rather than as a spec violation of ruling 138 (3) ("no codes in flags"). GPT-OSS was correct: the raw `SA.opener` string *can* carry a fault code like `starts_mid_thought`, and the spec requires plain words.

**Qwen's P2 on the `not in trims` guard (mutation S3):** I missed this in Cycle 1. The condition `m["moment_id"] not in trims` on line 102 of the diff prevents a moment with an affirmed trim variant from being *also* brought back as a flagged original. No unit test exercises this path. The E2E rig uses moments "h", "x", "z", "w" — none have trim variants. If the guard were removed, a moment with an affirmed trim would appear in the pool twice (original with flag, trim without). The lineup rule "one video at most once" prevents both in the same lineup, but the picker could select the flagged original over the clean trim, producing an unnecessary flag. This is a [P2] test gap, not a code defect.

**Qwen's P3 on `soft_record` including `"soft_stand": None`:** When `stand_back` is empty, line 119 omits the key (`**({"soft_stand": stand_back} if stand_back else {})`), so `soft.get("soft_stand")` on line 146 returns `None`. The record will contain `"soft_stand": None`. This is cosmetic — it's a debug record, and `None` correctly means "no moments were brought back." [P3], declined.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Source | My position | Reason |
|---------|--------|-------------|--------|
| `stand_plain` fallback is a P1 (raw string can carry a code) | GPT-OSS-20B | **Agree. Now fixed.** | The fix replaces the raw `why` with the fixed sentence `"the clip scorer does not confirm it stands alone"`. The new test (line 205–206) patches `SA.opener` to return an unknown wording and asserts the fixed sentence. Ruling 138 (3) is satisfied. |
| `stand_plain` fallback is safe / by design | Gemma-4-31B-IT | **Disagree (Cycle 1). Now moot.** | Gemma argued the integrator matches the prefix, not the tail, so the raw string was harmless. This is true for the *integrator's* matching, but the flag text is also shown to a human reviewer in the pin's `flags` list, and ruling 138 (3) explicitly forbids codes in that text. The fix is correct. |
| Positional `labels()` mapping is by design | All three models | **Agree.** | `stand_alone_check` builds its EDL from the same `segs` in the same order. `check_edl` labels rows positionally. The coupling is an internal invariant, not a defect. |
| No E2E test for hard `stand_alone` failure in the pin row | GPT-OSS-20B (P3), Qwen (P2) | **Partially agree. [P2].** | The unit tests on `stand_soft_rows` cover every hard case (hook, topic, unmarked clip, medley, `ok=True`). The E2E rig test `test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass` confirms a topic-refused moment ("w") stays out. The specific gap is: no test drives `inventory(…, stand=stand_with_soft(segs_with_hook_failure), soft=True, …)` and asserts the row is `"FAIL"` with non-empty `gate_problems`. The `if soft and stand.get("soft_rows")` guard in inventory is the *only* thing preventing a regression in `stand_with_soft` from silently downgrading a hard FAIL to FLAGGED. Current code is correct; this is a test gap. |
| Double period when `why` ends with a period | GPT-OSS-20B (P3) | **Agree: DECLINED.** | Neither of `SA.opener`'s two clip-refusal wordings ends with a period. The fixed fallback sentence also does not. The inventory flag appends exactly one period: `f"{why}."`. No double period is possible. |
| Dense comprehension for `stand_back` | GPT-OSS-20B (P3) | **Agree: DECLINED.** | Cosmetic. The comprehension is correct and the intent is clear from the comment. |
| `stand_ok` uses `bool(stand_soft_rows(...))` instead of `is not None` | GPT-OSS-20B | **Agree: DECLINED.** | `stand_soft_rows` returns either `None` or a non-empty dict (the `out or None` on line 51 guarantees this). `bool({})` is `False`, `bool(None)` is `False`, `bool({"clip_01": "why"})` is `True`. The logic is correct. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] No unit test for the `not in trims` guard (mutation S3 survivor)

**Location:** `pipeline/package.py`, line 102 of the diff (`stand_back` comprehension)

The condition `m["moment_id"] not in trims` ensures a moment with an *affirmed* trim variant is not also brought back as a flagged original. No test exercises this path. The E2E rig's moments ("h", "x", "z", "w") have no trim variants. If the guard were removed, a moment with an affirmed trim would appear in the pool twice. The lineup rule prevents both in the same lineup, but the picker could select the flagged original over the clean trim.

**Suggestion:** Add a unit test: construct a moment that fails the opener, give it an affirmed trim variant, run `_build(soft=True)`, and assert the original is NOT in `stand_back` while the trim IS in the pool.

### [P3] No test for a non-conjunction, low-clip-score moment carrying a `stand_soft` mark into the hook position

**Location:** `pipeline/package.py`, lines 46–48 (`stand_soft_rows`), line 57 (`stand_ok`)

A moment that opens on "Bitcoin" (not a conjunction) but receives a clip score of 2.0 would be brought back by `stand_back` with a `stand_soft` mark. If the lineup picker then selects it as the hook, the hook row in `stand_soft_rows` is checked: `r.get("segment") == "hook"` causes an immediate `return None`. The logic is sound, but no test drives this specific path. Low-risk because the hook opener rule (`SA.opener("hook", …)`) is a different check from the clip opener rule, and a moment that passes the hook opener but fails the clip opener is a narrow edge case.

### [P3] `soft_record` includes `"soft_stand": None` when no moments are brought back

**Location:** `pipeline/package.py`, line 146 of the diff

When `stand_back` is empty, line 119 omits the `"soft_stand"` key from the `soft` record. Line 146 then does `soft.get("soft_stand")`, which returns `None`. The `soft_record` dict will contain `"soft_stand": None`. This is a debug record; `None` correctly means "no moments were brought back." Cosmetic.

---

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_plain` | P1 (raw-string fallback) | **Pass** | Fixed: last line now returns `"the clip scorer does not confirm it stands alone"`. New test covers the fallback path. Ruling 138 (3) satisfied. |
| `stand_soft_rows` | Pass | Pass | No change. Fail-closed logic is correct. |
| `stand_ok` | Pass | Pass | No change. |
| `stand_with_soft` | Pass | Pass | No change. |
| `stand_back` / `not in trims` | Pass | Pass (code) / P2 (test gap) | Code is correct; no unit test for the trim guard. |
| `inventory` flagging | Pass | Pass | No change. Exact prefix confirmed. |
| `package_pin.SOFT_GATES` | Pass | Pass | No change. `"stand_alone"` added correctly. |
| `lineup_ok` / `lineup_for` | Pass | Pass | No change. Both use `stand_ok`. |
| Clean pass unchanged | Pass | Pass | `stand_back` gated on `soft`; `m.pop("stand_soft", None)` prevents carry-in. |
| Tests | Pass | Pass (6/7) | 6 new test methods cover the plain reason, all hard cases, E2E rig, carry-in guard, lineup rules, and soft-only flagging. The `not in trims` path is untested (P2). |

---

## 5. FINAL PRIORITY LIST

| Priority | Item | File / Line | Action |
|----------|------|-------------|--------|
| **P2** | No unit test for the `not in trims` guard in `stand_back` | `pipeline/package.py` line 102 (diff) | Add a test: moment fails opener, has affirmed trim, `_build(soft=True)` → original NOT in `stand_back`, trim IS in pool. |
| **P2** | No E2E test for hard `stand_alone` failure (hook row) in the pin row with `soft=True` | `tests/package/test_ruling_137.py` | Add a test: build a pin with `soft=True` where the hook row fails; assert row status is `"FAIL"` and `gate_problems()` is non-empty. |
| **P3** | `soft_record` includes `"soft_stand": None` when empty | `pipeline/package.py` line 146 (diff) | Optional: filter out `None` values, or accept as-is. |
| **P3** | No test for non-conjunction low-score moment as hook with `stand_soft` mark | `pipeline/package.py` lines 46–48 | Optional: add a unit test. |

No P0 or P1 findings.

---

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The fix to `stand_plain`'s fallback — replacing the raw `SA.opener` string with the fixed plain sentence `"the clip scorer does not confirm it stands alone"` — is the single most important change in this cycle, because it closes the one ruling 138 (3) violation (no codes in flags) that was the sole P1 from Cycle 1, and the new mock-patched test guarantees it stays closed.

---

## 7. PRODUCTION READY?

**Yes.**

The one P1 from Cycle 1 (`stand_plain` returning a raw string that could carry a code) is fixed and tested. The fix is minimal (one line changed, one test added), correct, and documented. The remaining findings are P2 test gaps (the `not in trims` guard, the hard-failure E2E pin test) and P3 cosmetics. None of them represent a defect in the current code; they are regression-prevention opportunities.

The clean pass is unchanged. The exact prefix `"The clip ({channel}) may not stand alone: "` is confirmed by test. The topic rule, the medley-names-Bitcoin rule, and the hook rule all stay hard. `lineup_ok`, `lineup_for`, and the pin row agree via `stand_ok` / `stand_with_soft`. The `m.pop("stand_soft", None)` guard prevents carry-in. The `if soft and stand.get("soft_rows")` guard in inventory prevents FLAGGED status when `stand_soft_rows` returns `None`.

P1_OR_WORSE: 0