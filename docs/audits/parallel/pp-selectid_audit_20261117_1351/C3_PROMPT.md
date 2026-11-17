# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1351
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 194 s finish=stop usage in 11844 / out 4088 usd_reported=0.000874 usd~0.097 (upper-bound price)

## 1. WHAT DID THEY CATCH THAT YOU MISSED?
Qwen identified three potential fragility points:
1.  **Regex Fallback:** The `stand_plain` function falls back to the raw internal reason if the regexes fail.
2.  **Positional Mapping:** `stand_soft_rows` maps segments to labels using `zip(labels(len(segs)), segs)`, which assumes a strict order.
3.  **Hard-Failure E2E Testing:** A lack of a specific end-to-end test case where `soft=True` but a hard `STAND_ALONE` failure occurs (ensuring it remains `FAIL` and not `FLAGGED`).

## 2. WHERE DO YOU AGREE OR DISAGREE?
*   **Regex Fallback: Disagree.** This is a safe fallback. The integrator matches the prefix; the tail is for the human reviewer. Returning the raw reason is better than returning `None` or crashing.
*   **Positional Mapping: Disagree.** This is a stable internal invariant. `pk["segments"]` is the ordered list of segments, and `labels()` generates labels in that exact order. This coupling is consistent with how `stand_alone_check` itself operates.
*   **Hard-Failure E2E Testing: Partially Agree.** While a dedicated E2E rig test for this specific transition would be "nice to have," the logic is rigorously covered by:
    *   Unit tests in `test_only_marked_clips_failing_only_the_opener_are_soft` (covering hook, topic, unmarked, and Bitcoin failures).
    *   The E2E rig test `test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass`, which confirms a topic-refused moment (`w`) stays out.
    *   The `inventory` guard `if soft and stand.get("soft_rows")`, which prevents `FLAGGED` status if `stand_soft_rows` returns `None`.

## 3. NEW FINDINGS FROM THIS REVIEW
No new findings. The combined analysis confirms that the "fail-closed" logic in `stand_soft_rows` is the primary safety mechanism, and it is correctly implemented.

## 4. REVISED SCORES
No changes. The implementation is precise and adheres to the ruling.

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
| :--- | :--- | :--- | :--- |
| Logic | Pass | Pass | No change |
| Integration | Pass | Pass | No change |
| Tests | Pass | Pass | No change |

## 5. FINAL PRIORITY LIST
No P0, P1, or P2 findings.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The implementation of `stand_soft_rows` as a "fail-closed" validator is the most critical piece, and it correctly ensures that only marked opener failures are softened.

## 7. PRODUCTION READY?
Yes.

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 51 s finish=stop usage in 10246 / out 8225 usd_reported=0.001336 usd~0.154 (upper-bound price)

**1. What the other models caught that I missed**

| # | Finding | Severity | Why it matters |
|---|---------|----------|----------------|
| 1 | `stand_plain` falls back to the raw `SA.opener` string if the regexes don’t match. | **P1** | The spec says the flag must contain *plain‑words* (“it opens on …”). If the upstream format changes, the flag will contain an unreadable, non‑plain string, breaking the integrator’s human‑readable audit. |
| 2 | No end‑to‑end test for a hard `stand_alone` failure in the pin row. | **P3** | The code is correct, but a regression in `stand_with_soft` could silently downgrade a hard failure to a flag. A test would catch that. |
| 3 | `stand_soft_rows` maps segments to labels by position (`labels(len(segs))`). | **P3** | Future callers could pass segments in a different order, causing a soft row to be mis‑attributed. Not a current bug, but a design‑time risk. |
| 4 | Double period when `SA.opener`’s raw string already ends with a period. | **P3** | Cosmetic, but could be confusing in logs. |
| 5 | Dense comprehension for `stand_back`. | **P3** | Readability issue, no functional impact. |

**2. Agreement / disagreement**

| # | Finding | My stance | Reason |
|---|---------|-----------|--------|
| 1 | `stand_plain` fallback | **Agree (P1)** | The requirement is to expose a *plain‑words* reason. Falling back to the raw string violates that contract. |
| 2 | End‑to‑end test missing | **Agree (P3)** | It’s a test gap, not a code defect. |
| 3 | Mapping order | **Agree (P3)** | Design choice; no current bug. |
| 4 | Double period | **Agree (P3)** | Cosmetic. |
| 5 | Dense comprehension | **Agree (P3)** | Cosmetic. |

**3. New findings from this review**

* The `stand_soft_rows` helper returns `None` when `stand.get("medley_names_bitcoin")` is `None`. This is intentional (treat as hard), but the code could be clearer by explicitly checking for `is not None` before accessing `get("pass")`.  
* The `stand_ok` helper uses `bool(stand_soft_rows(...))`. If `stand_soft_rows` returns an empty dict (which it never does because it returns `None` when empty), the logic is still correct, but the intent could be expressed more clearly with `stand_soft_rows(...) is not None`.  
* The `stand_back` comprehension uses `for p in [stand_plain(m)] if p`. If `stand_plain` returns an empty string (unlikely), the comprehension would silently drop the moment. This is fine but could be documented.

**4. Revised scores**

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|-----------|---------|---------|-------------|
| `stand_plain` | P0 | **P1** | Fallback to raw string violates spec. |
| `stand_soft_rows` | P0 | P0 | No functional bug. |
| `stand_ok` | P0 | P0 | Correct logic. |
| `stand_with_soft` | P0 | P0 | Correct logic. |
| `stand_back` | P0 | P0 | Correct logic. |
| `inventory` flagging | P0 | P0 | Correct logic. |
| `package_pin.SOFT_GATES` | P0 | P0 | Correct. |
| Tests | P0 | P0 | No new failures. |

**P1_OR_WORSE: 1**

**5. Final priority list**

| Priority | Item | File / Line | Action |
|----------|------|-------------|--------|
| **P1** | `stand_plain` must not silently return the raw `SA.opener` string. | `pipeline/package.py` lines 13‑30 | 1. Add a clear fallback path: log a warning and return a generic “unknown reason” string. 2. Add a unit test (`test_stand_plain_fallback`) that monkey‑patches `SA.opener` to return an unexpected format and asserts the fallback. |
| **P1** | End‑to‑end test for hard `stand_alone` failure in the pin row. | `tests/package/test_ruling_137.py` | Add a test that builds a pin with `soft=True` where the hook row fails (or topic fails) and asserts the row status is `"FAIL"` and that `gate_problems()` is non‑empty. |
| **P2** | Document the positional invariant of `stand_soft_rows`. | `pipeline/package.py` lines 33‑50 | Add a comment or docstring noting that `segs` must be in the order produced by `stand_alone_check`. |
| **P3** | Cosmetic: double period when `why` already ends with a period. | `pipeline/package.py` line 156 | Add a small helper to strip a trailing period before concatenation. |
| **P3** | Dense comprehension for `stand_back`. | `pipeline/package.py` lines 101‑102 | Rewrite as a clearer loop or list comprehension for readability. |

**6. The single highest‑leverage change**

Add a robust fallback in `stand_plain` that logs a warning and returns a clear, human‑readable “unknown reason” string instead of the raw `SA.opener` output, and add a test to guarantee this behavior.

**7. Production ready?**

**Yes, with conditions.**  
- Implement the `stand_plain` fallback and corresponding test.  
- Add the hard‑failure end‑to‑end test.  
- Document the positional invariant of `stand_soft_rows`.  
Once those changes are in place, the code satisfies the RULING 141 (2) contract and is ready for release.

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 149 s finish=stop usage in 11149 / out 12151 usd_reported=0.009182 usd~0.216 (upper-bound price)



# PROTOCOL PULSE — CYCLE 2 CODE AUDIT (Final)
## Feature: pp-selectid-20261117_1351 — RULING 141 (2): STAND_ALONE SOFT

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Qwen's [P2] on the missing end-to-end hard-failure pin test:** I initially considered this covered by the unit tests on `stand_soft_rows` (every hard case returns `None`), and the consensus agrees. However, I now see the specific gap more clearly: there is no test that drives `PK.inventory(…, stand=stand_with_soft(segs_with_hook_failure), soft=True, …)` and asserts the row is `"FAIL"` with a non-empty `gate_problems`. The safety net is the `if soft and stand.get("soft_rows")` guard in inventory, but that guard is the *only* thing preventing a regression in `stand_with_soft` (e.g., always emitting `soft_rows={}`) from silently downgrading a hard FAIL to a FLAGGED with an empty flag list. I missed this in Cycle 1 because I focused on the logic of `stand_soft_rows` itself rather than the inventory's consumption of its output.

**Qwen's [P2] on positional coupling:** I noted this in Cycle 1 but didn't fully trace the invariant. The consensus correctly identifies that `stand_alone_check` builds its EDL from the same `segs` in the same order, and `check_edl` labels rows positionally. I agree this is by design and not a defect.

**Gemma's clean read:** I agree with Gemma's assessment that the implementation is precise and maintains clean-pass integrity. No disagreement.

---

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My position |
|---------|-------------|
| Qwen [P2] `stand_plain` fallback | **Agree with consensus: BY DESIGN.** The two regexes parse `SA.opener`'s own clip wordings. Any other wording is the render's reason verbatim. The integrator matches the prefix, not the tail. No gate is bypassed. |
| Qwen [P2] No e2e hard-failure pin test | **Partially agree.** The unit tests on `stand_soft_rows` cover every hard case. But the inventory-level guard (`if soft and stand.get("soft_rows")`) is untested in the specific scenario where `stand_with_soft` might regress to always emit `soft_rows`. I'd call this [P2], not [P1], because the current code is correct and the unit tests kill the relevant mutations. |
| Qwen [P2] Positional `labels()` mapping | **Agree with consensus: BY DESIGN.** The EDL is built from the same `segs` in the same order. |
| Qwen [P3] Double period | **Agree: DECLINED.** Neither of `SA.opener`'s clip wordings ends with a period. |
| Qwen [P3] Dense comprehension | **Agree: DECLINED.** Cosmetic. |
| Gemma: No violations | **Agree.** The implementation is correct. |

---

## 3. NEW FINDINGS FROM THIS REVIEW

### [P2] No unit test for the `not in trims` guard (mutation S3 survivor)

**Location:** `package.py` line 101 (`stand_back` comprehension)

The condition `m["moment_id"] not in trims` ensures that a moment with an *affirmed* trim variant is not also brought back as a flagged clip. The trim is the preferred (clean) version; the original would be redundant and would carry a `stand_soft` flag unnecessarily.

No test exercises this path. The end-to-end rig uses moments "h", "x", "z", "w" — none have trim variants. If the `not in trims` condition were removed, a moment with an affirmed trim would appear in the pool *twice* (original with flag, trim without). The lineup rule "one video at most once" prevents both in the same lineup, but the picker could select the flagged original over the clean trim, producing an unnecessary flag.

**Suggestion:** Add a unit test: construct a moment that fails the opener, give it an affirmed trim variant, run `_build(soft=True)`, and assert the original is NOT in `stand_back` while the trim IS in the pool.

### [P3] No test for a non-conjunction moment (low clip score) carrying a `stand_soft` mark into the hook position

**Location:** `package.py` lines 46–48 (`stand_soft_rows`), line 57 (`stand_ok`)

A moment that opens on "Bitcoin" (not a conjunction) but receives a clip score of 2.0 would be brought back by `stand_back` with a `stand_soft` mark. If the lineup picker then selects it as the hook, the hook row in `stand_soft_rows` is checked: if it passes, the mark is irrelevant; if it fails, `stand_soft_rows` returns `None` and the lineup is rejected. The logic is sound, but no test drives this specific path (non-conjunction, low-score moment as hook).

This is low-risk because the hook opener rule (`SA.opener("hook", …)`) is a different check from the clip opener rule, and a moment that passes the hook opener but fails the clip opener is a narrow edge case.

### [P3] `soft_record` includes `"soft_stand": None` when no moments are brought back

**Location:** `package.py` line 145

```python
"soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}
```

When `stand_back` is empty, `soft` has no `"soft_stand"` key, so `soft.get

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 2 consensus (pp-selectid_audit_20261117_1351, ruling 141 (2): STAND_ALONE soft, the builder's half)

SEATS ANSWERED: 3 of 3. qwen3.8-27b and gemma-4-31b-it: P0/P1 none. gpt-oss-20b: one P1: stand_plain's fallback to the
raw stand_alone.opener string can put a code ("fault starts_mid_thought") in front of PBX if opener's wording changes;
ruling 138 (3) says no codes. qwen raised the same as a P2 in cycle 1.

## ACCEPTED AND FIXED (the only change from cycle 2 to cycle 3)
stand_plain's last line no longer returns the raw reason: any wording other than opener's two clip refusals now reads
"the clip scorer does not confirm it stands alone" (a fixed plain sentence). New test: opener patched to an unknown
wording, the fixed sentence comes back. Unreachable today (opener's not-ok clip wordings are exactly the two matched,
plus "empty segment" for a moment with no text, which never reaches the pool), and safe if that changes.
Suites after the fix: tests/package test_ruling_137 / test_medley / test_angles 316 passed; dev59 suites (before the
one-line fix) 41 files / 899 tests, exit 0.

## Cycle 3 is asked to confirm the fix only.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1351/C3_STEP.diff (274 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 68e6942..dd41fd9 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1569,6 +1569,65 @@ def scorer_pass(ms, sources, ctx, verdicts_path, candidates_path, build_name, ex
   6 |      return {"index": index, "record": rec}
   7 |  
   8 |  
   9 | +STAND_SOFT_PREFIX = "The clip ({channel}) may not stand alone: "   # RULING 141 (2): the integrator's render matches
  10 | +#   this prefix exactly (it then skips its own flag for that channel's clip)
  11 | +
  12 | +
  13 | +def stand_plain(m):
  14 | +    """RULING 141 (2): the render's STAND_ALONE opener refusal of moment m as a CLIP, in plain words (the clip scorer's
  15 | +    reason), e.g. "it opens on 'but' and the clip scorer has no verdict for it"; None when the clip role passes."""
  16 | +    import stand_alone as SA
  17 | +    v = verdict_of(m)
  18 | +    ok, why = SA.opener("clip", m.get("text") or "", v["score"] if v else None, v["fault"] if v else None,
  19 | +                        moments=True)
  20 | +    if ok:
  21 | +        return None
  22 | +    x = re.match(r"clip opens on (.+?) and no clip-scorer verdict is available", why)
  23 | +    if x:
  24 | +        return f"it opens on {x.group(1)} and the clip scorer has no verdict for it"
  25 | +    x = re.match(r"clip opens on (.+?); the clip scorer does not affirm it stands alone \(([^,]+), fault (.+)\)$", why)
  26 | +    if x:
  27 | +        f = x.group(3).replace("_", " ")
  28 | +        return f"it opens on {x.group(1)} and the clip scorer rated it {x.group(2)} of 5" + \
  29 | +            (f" ({f})" if f not in ("None", "none", "") else "")
  30 | +    return "the clip scorer does not confirm it stands alone"   # any other wording: plain, never a code (ruling 138 (3);
  31 | +    #   audit 20261117_1351: qwen C1, gpt-oss C2)
  32 | +
  33 | +
  34 | +def stand_soft_rows(stand, segs):
  35 | +    """RULING 141 (2) (STAND_ALONE soft in the never-empty pass): {label: plain reason} for the CLIP rows of a check_edl
  36 | +    result `stand` (stand_alone_check(segs)) that fail ONLY its opener rule, each on a moment that pass brought back
  37 | +    (its "stand_soft" mark); None when the check passes or any other failure stands: the hook's row, any topic row
  38 | +    (ruling 34), the medley not naming Bitcoin, a failing row of an unmarked clip (these stay HARD)."""
  39 | +    if not isinstance(stand, dict) or stand.get("ok") is True or \
  40 | +            (stand.get("medley_names_bitcoin") or {}).get("pass") is not True:
  41 | +        return None
  42 | +    by, out = dict(zip(labels(len(segs)), segs)), {}
  43 | +    for r in stand.get("rows") or []:
  44 | +        if r.get("pass") is True:
  45 | +            continue
  46 | +        m = by.get(r.get("segment"))
  47 | +        if r.get("segment") == "hook" or m is None or not m.get("stand_soft") or \
  48 | +                (r.get("topic") or {}).get("pass") is not True or (r.get("opener") or {}).get("pass") is not False:
  49 | +            return None
  50 | +        out[r["segment"]] = m["stand_soft"]
  51 | +    return out or None
  52 | +
  53 | +
  54 | +def stand_ok(segs):
  55 | +    """The render's STAND_ALONE on a line-up for the line-up rules (lineup_ok, lineup_for): it passes, or RULING 141 (2),
  56 | +    its only failures are clips the never-empty pass brought back failing only the opener rule (stand_soft_rows)."""
  57 | +    st = stand_alone_check(segs)
  58 | +    return st["ok"] is True or bool(stand_soft_rows(st, segs))
  59 | +
  60 | +
  61 | +def stand_with_soft(segs):
  62 | +    """The pin stage's STAND_ALONE (stand_alone_check) with RULING 141 (2)'s soft rows when there are any."""
  63 | +    st = stand_alone_check(segs)
  64 | +    sr = stand_soft_rows(st, segs)
  65 | +    return dict(st, soft_rows=sr) if sr else st
  66 | +
  67 | +
  68 |  def no_topic(m):
  69 |      """Why a moment can take NO place under the render's topic rule with the pin's screen (ruling 34), else None: it
  70 |      fails the miner's about-Bitcoin screen, and could not complete a previous claim even right after a segment that
  71 | @@ -1800,7 +1859,7 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  72 |      dur = sum(m["duration_s"] for m in segs)
  73 |      if not lo <= dur <= hi:
  74 |          return False, f"{dur:.1f} s outside {lo}-{hi} s"
  75 | -    if not stand_alone_check(segs)["ok"]:
  76 | +    if not stand_ok(segs):                                   # RULING 141 (2): only marked clips' openers flag
  77 |          return False, "the render's STAND_ALONE"
  78 |      return True, "ok"
  79 |  
  80 | @@ -1937,7 +1996,7 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  81 |                      continue
  82 |                  if accept is not None and not accept([h] + order):       # the caller's own condition (pool_fill)
  83 |                      continue
  84 | -                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  85 | +                if need_stand_alone and not stand_ok([h] + order):     # RULING 141 (2): marked clips flag
  86 |                      continue
  87 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  88 |                  if now is not None:                       # ruling 57: a fresh clip first, then the newest clips,
  89 | @@ -3198,6 +3257,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  90 |      scorer = scorer_pass(ms, sources, ctx, scorer_verdicts_path, scorer_candidates_path, build_name,   # ruling 56
  91 |                           extra=scorer_extra)                                                       # ruling 90
  92 |      ms = [with_verdict(m, scorer["index"]) for m in ms]
  93 | +    for m in ms:                                       # RULING 141 (2)'s soft mark is this pass's own, never carried in
  94 | +        m.pop("stand_soft", None)
  95 |      no_role = {m["moment_id"]: r for m in ms                    # both reasons when both rules fire (audit 0426 C2)
  96 |                 for r in ["; ".join(x for x in (no_role_on_screen(m), no_topic(m)) if x)] if r}
  97 |      admitted = sorted(m["moment_id"] for m in ms if verdict_of(m) and m["moment_id"] not in no_role)   # ruling 56
  98 | @@ -3206,6 +3267,16 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
  99 |               for v in [trim_variant(m, sources)] if v}                      # joins the pool (the original stays a clip)
 100 |      trim_out = {k: why for k, v in trims.items() for why in [trim_refused(v)] if why}   # ruling 56: never sealed
 101 |      trims = {k: v for k, v in trims.items() if k not in trim_out}
 102 | +    stand_back = {m["moment_id"]: p for m in ms if soft and m["moment_id"] in no_role and m["moment_id"] not in trims
 103 | +                  and no_topic(m) is None for p in [stand_plain(m)] if p}   # RULING 141 (2): STAND_ALONE SOFT in the
 104 | +    for m in ms:                                                            # never-empty pass: a moment left out ONLY
 105 | +        if m["moment_id"] in stand_back:                                    # by the opener rule (no topic refusal, no
 106 | +            m["stand_soft"] = stand_back[m["moment_id"]]                    # affirmed trim) comes back as a clip,
 107 | +    if stand_back:                                                          # flagged; it never opens (the hook rule)
 108 | +        log(f"  RULING 141 NEVER EMPTY (STAND_ALONE soft): {len(stand_back)} moment(s) left out only by the render's "
 109 | +            f"STAND_ALONE opener rule come back as clips, flagged: " +
 110 | +            ", ".join(f"{mid[:8]} ({p})" for mid, p in stand_back.items()))
 111 | +    no_role = {k: v for k, v in no_role.items() if k not in stand_back}
 112 |      ms = [m for m in ms if m["moment_id"] not in no_role] + list(trims.values())     # ruling 33 part 2 (item 42);
 113 |      #   a variant of a moment that keeps its own place (ruling 94 a) sits beside it: one line-up never takes both (one
 114 |      #   video at most once, L-y 4)
 115 | @@ -3248,6 +3319,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 116 |      cleared, back = cleared_pool(ms, a_by, fails, soft)  # RULING 137 stage 1: the never-empty pass adds back, flagged
 117 |      levels = current_levels(sources.values(), ctx)
 118 |      out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
 119 | +           **({"soft_stand": stand_back} if stand_back else {}),          # RULING 141 (2): back, flagged
 120 |             "no_role": no_role, "ad_read": ad_read, "trimmed": {k: v["moment_id"] for k, v in trims.items()},
 121 |             "reposted": reposted,
 122 |             "scorer": dict(scorer["record"], admitted=admitted, trims_affirmed=sorted(trims), trims_out=trim_out),
 123 | @@ -3717,7 +3789,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 124 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
 125 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 126 |                                  hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 127 | -                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 128 | +                                stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 129 |                                  visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 130 |                                  last_resort=pin_last_resort(pk), soft=soft,   # RULING 102; RULING 137 stage 1
 131 |                                  who={sg["label"]: sg.get("channel") for sg in pk["segments"]},   # RULING 138 (3)
 132 | @@ -4206,7 +4278,7 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 133 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 134 |                                              style=HS.lint_lines(pk["lines"]),
 135 |                                              hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 136 | -                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 137 | +                                            stand=stand_with_soft([cleared[sg["moment_id"]] for sg in pk["segments"]]),
 138 |                                              visual=[cleared[sg["moment_id"]].get("visual") for sg in pk["segments"]],
 139 |                                              value=val,                       # ruling 91: the takeaway earned its place
 140 |                                              last_resort=pin_last_resort(pk),      # RULING 102: on the pin
 141 | @@ -4327,7 +4399,7 @@ def build(*args, never_empty=False, flagged_today=0, **kw):
 142 |      soft = _build(*args, soft=True, **kw)
 143 |      info = {"stage": "2b", "clean_why_none": out.get("why_none"), "soft_why_none": soft.get("why_none"),
 144 |              "soft_back": (soft.get("prescreen") or {}).get("soft_back"),
 145 | -            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried")}}   # the pass's own record
 146 | +            "soft_record": {k: soft.get(k) for k in ("prescreen", "hook_pool", "tried", "soft_stand")}}   # its record
 147 |      return dict(soft, never_empty=info) if soft.get("package") else dict(out, never_empty=info)
 148 |  
 149 |  
 150 | @@ -4438,7 +4510,10 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 151 |                                      "affirming one a conjunction, reply-fragment or trimmed opener fails closed)"),
 152 |                                  rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 153 |                                        f"topic: {r['topic']['why']}" for r in stand.get("rows") or []],
 154 | -                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"))}
 155 | +                                medley_names_bitcoin=stand.get("medley_names_bitcoin"), screen=stand.get("screen"),
 156 | +                                **({"status": "FLAGGED", "flags": [           # RULING 141 (2): one plain sentence a clip
 157 | +                                    STAND_SOFT_PREFIX.format(channel=(who or {}).get(lb) or "its channel") + f"{why}."
 158 | +                                    for lb, why in stand["soft_rows"].items()]} if soft and stand.get("soft_rows") else {}))}
 159 |             if stand is not None else {}),
 160 |          **({"visual": dict(row(bool(visual) and all((v or {}).get("measured") is True for v in visual),
 161 |                                 sorted({str((v or {}).get("backend")) for v in visual}) or None,
 162 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 163 | index 1fb3855..727abc7 100644
 164 | --- a/pipeline/package_pin.py
 165 | +++ b/pipeline/package_pin.py
 166 | @@ -37,8 +37,10 @@ MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"
 167 |  SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's soft codes
 168 |                          "cuttable",                        # stage 2a: a sentence edge at a word boundary (L-v 2's
 169 |                          #   word check, "second_pass", stays HARD)
 170 | -                        "medley"})                         # stage 2b: the hook under the calibrated bar (its own
 171 | -#   rater's rating; no calibration or another rater stays HARD)
 172 | +                        "medley",                          # stage 2b: the hook under the calibrated bar (its own
 173 | +                        #   rater's rating; no calibration or another rater stays HARD)
 174 | +                        "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 175 | +#   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 176 |  REVIEW_FLAGS_MAX = 3
 177 |  
 178 |  
 179 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 180 | index f61260a..6ef4cf8 100644
 181 | --- a/tests/package/test_ruling_137.py
 182 | +++ b/tests/package/test_ruling_137.py
 183 | @@ -290,6 +290,90 @@ class TestStage2bHookBar(unittest.TestCase):
 184 |          self.assertEqual(PK.HOOK_SOFT_MAX, 2)
 185 |  
 186 |  
 187 | +class TestRuling141StandAloneSoft(unittest.TestCase):
 188 | +    """RULING 141 (2): STAND_ALONE SOFT in the never-empty pass (the builder's half; the integrator's render already only
 189 | +    flags an opener refusal and holds on the topic rule and the medley naming Bitcoin). A moment left out ONLY by the
 190 | +    render's STAND_ALONE opener rule comes back as a clip, flagged "The clip (<channel>) may not stand alone: <reason>."
 191 | +    (the integrator matches that prefix); it never opens; the topic rule, the hook's row, an unmarked clip and the medley
 192 | +    naming Bitcoin stay hard."""
 193 | +
 194 | +    def m(self, text, verdict=None):
 195 | +        x = {"moment_id": "q", "text": text}
 196 | +        return dict(x, scorer_verdict=dict(verdict, text_sha256=PK.text_sha(text))) if verdict else x
 197 | +
 198 | +    def test_the_reason_in_plain_words(self):
 199 | +        self.assertEqual(PK.stand_plain(self.m("But Bitcoin q x.")),
 200 | +                         "it opens on 'but' and the clip scorer has no verdict for it")
 201 | +        self.assertEqual(PK.stand_plain(self.m("And Bitcoin q x.", {"score": 2.0, "fault": "starts_mid_thought",
 202 | +                                                                     "reason": "r"})),
 203 | +                         "it opens on 'and' and the clip scorer rated it 2.0 of 5 (starts mid thought)")
 204 | +        self.assertIsNone(PK.stand_plain(self.m("Bitcoin q x.")))
 205 | +        with mock.patch("stand_alone.opener", lambda *a, **k: (False, "clip q (2.0, fault x_y) new wording")):
 206 | +            self.assertEqual(PK.stand_plain(self.m("Bitcoin q x.")), "the clip scorer does not confirm it stands alone")
 207 | +        self.assertTrue(PK.STAND_SOFT_PREFIX.format(channel="X").startswith("The clip (X) may not stand alone: "))
 208 | +
 209 | +    def test_only_marked_clips_failing_only_the_opener_are_soft(self):
 210 | +        segs = [{"moment_id": "h", "stand_soft": "why h"}, {"moment_id": "a", "stand_soft": "why a"},
 211 | +                {"moment_id": "b"}]                                     # a mark on the hook never softens its row
 212 | +        row = lambda seg, o, t=True: {"segment": seg, "pass": o and t, "opener": {"pass": o}, "topic": {"pass": t}}
 213 | +        st = {"ok": False, "rows": [row("hook", True), row("clip_01", False), row("clip_02", True)],
 214 | +              "medley_names_bitcoin": {"pass": True}}
 215 | +        self.assertEqual(PK.stand_soft_rows(st, segs), {"clip_01": "why a"})
 216 | +        for bad in ([row("hook", False), row("clip_01", False), row("clip_02", True)],      # the hook's own row
 217 | +                    [row("hook", True), row("clip_01", False, False), row("clip_02", True)],   # its topic too
 218 | +                    [row("hook", True), row("clip_01", False), row("clip_02", False)]):     # an unmarked clip
 219 | +            self.assertIsNone(PK.stand_soft_rows(dict(st, rows=bad), segs), bad)
 220 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin={"pass": False}), segs))
 221 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, medley_names_bitcoin=None), segs))   # unmeasured: hard
 222 | +        self.assertIsNone(PK.stand_soft_rows(dict(st, ok=True), segs))
 223 | +
 224 | +    def rig(self, never_empty, carry=False):
 225 | +        import test_medley as TM
 226 | +        from test_moments import pm
 227 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), dict(pm("z", "C", 13.0), text="But Bitcoin z x."),
 228 | +              dict(pm("w", "D", 13.0), text="But nothing here at all.")]   # w: the topic rule (ruling 34) too
 229 | +        ms = [dict(m, stand_soft="carried in") for m in ms] if carry else ms
 230 | +        r = TM.Rig(ms, ["h", "x", "z"], [(True, [], None, TM.Rig.LINE)], [None])
 231 | +        r.build_kw = {"never_empty": never_empty}
 232 | +        return r.run()
 233 | +
 234 | +    def test_a_clip_left_out_only_by_the_opener_rule_seals_flagged_only_in_the_never_empty_pass(self):
 235 | +        clean = self.rig(False)
 236 | +        self.assertIsNone(clean["package"])
 237 | +        self.assertIn("z", clean["no_role"])                        # the clean pass: 2 channels, no paid verdict
 238 | +        out = self.rig(True)
 239 | +        pk = out["package"]
 240 | +        segs = {s["moment_id"]: s for s in pk["segments"]}
 241 | +        self.assertEqual((set(segs), pk["segments"][0]["moment_id"]), ({"h", "x", "z"}, "h"))   # never the hook
 242 | +        want = [f"The clip ({segs['z']['channel']}) may not stand alone: it opens on 'but' and the clip scorer has no "
 243 | +                f"verdict for it."]
 244 | +        self.assertEqual((pk["gates"]["stand_alone"]["status"], pk["gates"]["stand_alone"]["flags"]), ("FLAGGED", want))
 245 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), want)
 246 | +        self.assertEqual(PP.gate_problems(pk["gates"], PP.required_gates(pk)), [])   # the seal's own check takes it
 247 | +        self.assertEqual(out["soft_stand"], {"z": "it opens on 'but' and the clip scorer has no verdict for it"})
 248 | +        self.assertIn("w", out["no_role"])                              # the topic rule stays HARD: never back
 249 | +
 250 | +    def test_a_mark_carried_in_is_never_read(self):
 251 | +        self.assertIsNone(self.rig(False, carry=True)["package"])
 252 | +
 253 | +    def test_the_line_up_rules_take_a_marked_clip_and_refuse_an_unmarked_one(self):
 254 | +        from test_moments import pm
 255 | +        h = dict(pm("h", "A", 12.0), hook_onset={"pass": True})
 256 | +        z = dict(pm("z", "C", 13.0), text="But Bitcoin z x.")
 257 | +        segs = [h, pm("x", "B", 14.0), z]
 258 | +        self.assertEqual(PK.lineup_ok(segs), (False, "the render's STAND_ALONE"))
 259 | +        self.assertEqual(PK.lineup_ok([h, segs[1], dict(z, stand_soft="it opens on 'but'")]), (True, "ok"))
 260 | +
 261 | +    def test_the_row_flags_only_in_the_soft_pass(self):
 262 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 263 | +        st = {"ok": False, "rows": [], "medley_names_bitcoin": {"pass": True}, "soft_rows": {"clip_02": "why z"}}
 264 | +        row = lambda soft: PK.inventory(**TestStage2a().base(t), stand=st, soft=soft, who={"clip_02": "Yahoo Finance"})[
 265 | +            "stand_alone"]
 266 | +        self.assertEqual((row(True)["status"], row(True)["flags"]), (
 267 | +            "FLAGGED", ["The clip (Yahoo Finance) may not stand alone: why z."]))
 268 | +        self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))
 269 | +
 270 | +
 271 |  class TestTheDayCount(unittest.TestCase):
 272 |      def test_counted_per_day_ledger(self):
 273 |          with tempfile.TemporaryDirectory() as d:
 274 | 
```

---

pp-selectid: RULING 141 (2) (orchestrator 13:40 ET Nov 17): STAND_ALONE becomes SOFT, the first item of stage 2b; the
builder's half. Context: the never-empty pass (package.build runs _build(soft=True) only when the clean pass sealed
nothing) flags soft gates in one plain sentence each; at most 3 flags seal (package_pin.REVIEW_FLAGS_MAX). STAND_ALONE
left out 77 of 110 usable moments today. The integrator's side needs no change: since its batch 105 (11:51 ET) its
render's validate re-asks every opener and only FLAGS an unaffirmed / unrated / conjunction opener; it HOLDS only on the
topic rule (ruling 34), the medley naming Bitcoin, and a malformed ruling-119 floor mark. Its next batch skips its own
flag for a channel whose pin already carries "The clip (<channel>) may not stand alone:", so that prefix must be exact.
Files: pipeline/package.py, pipeline/package_pin.py, tests/package/test_ruling_137.py.

THE CHANGE (never-empty pass only; the clean pass is unchanged):
(a) _build: no_role (package.py:3261: no_role_on_screen :1640, the opener rule; no_topic :1630, the topic rule) still
    leaves out what it did. In the soft pass, a moment left out ONLY by the opener rule (no_topic None) and with no
    affirmed trim variant (trims, :3264, the clean path, kept first) comes back (stand_back, :3269), carrying its plain
    reason as the mark "stand_soft" (stand_plain :1576: "it opens on 'but' and the clip scorer has no verdict for it" /
    "... rated it 2.0 of 5 (starts mid thought)"). The mark is popped after with_verdict, so it never carries in. It
    never opens: the hook role still needs SA.opener("hook") in _can_open (:1809), which every conjunction fails.
(b) stand_soft_rows(stand, segs) (:1596): the clip rows of check_edl (stand_alone.py:176-222: one row a segment, the
    opener and topic results, plus medley_names_bitcoin) that fail ONLY the opener, each on a marked moment. None if
    the check passes, the hook's row fails (even marked), any topic row fails, an unmarked clip's row fails, or the
    medley does not name Bitcoin (also when that record is missing).
(c) stand_ok(segs) (:1616) = the check passes, or only (b)'s rows fail. It replaces the bare check in lineup_ok (:1861)
    and in lineup_for's picker (:1998). stand_with_soft (:1623) adds the soft rows to the pin stage's check at both
    inventory call sites.
(d) inventory: the "stand_alone" row is FLAGGED with "The clip (<channel>) may not stand alone: <reason>." for each soft
    row (STAND_SOFT_PREFIX :1572, the integrator's exact prefix), only when soft. package_pin.SOFT_GATES adds
    "stand_alone". The record keeps out["soft_stand"].

TESTS (test_ruling_137, 7 new): the plain reason; (b)'s every hard case; END TO END through test_medley's Rig: a 3-moment
pool whose third channel opens on "But": the clean pass leaves it out and stops at 2 channels; the never-empty pass seals
with the stand_alone row FLAGGED in the exact sentence, review_flags_of equal to it, gate_problems() empty, the hook not
the flagged clip; a moment failing the topic rule too stays out. lineup_ok takes a marked clip and refuses an unmarked
one. The row flags only in the soft pass. Mutations: 11 of 14 killed. Survivors: S13 (the pop of a carried mark) and
S14 (the explicit opener check) are equivalent today; S3, preferring an affirmed trim, is NOT UNIT-TESTED: please read
:3269's "not in trims".

PLEASE CHECK: (1) can anything the topic rule, the medley-names-Bitcoin rule or the hook rule refuses get through? (2) the
clean pass unchanged; (3) lineup_ok / lineup_for / the pin row agree; (4) the exact prefix; (5) the tests.


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.


THIS THIRD CYCLE CHECKS THE FIX OF CYCLE 2'S REAL DEFECT: stand_plain's fallback returned the raw stand_alone.opener reason, which can carry a code (ruling 138 (3)); now a fixed plain sentence


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
