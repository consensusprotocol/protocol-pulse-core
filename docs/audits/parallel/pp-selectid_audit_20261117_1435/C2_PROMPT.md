# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261117_1435
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GEMMA-4-31B-IT — CYCLE 1 OUTPUT
# gemma-4-31b-it (google/gemma-4-31b-it) 247 s finish=stop usage in 19190 / out 5244 usd_reported=0.001245 usd~0.136 (upper-bound price)

The code implements **RULING 141 (3)**, introducing a "soft failure" mechanism for the line-up selection process. It allows candidates with minor defects (low clip ratings or certain unbridged joins) to be "kept" and potentially "accepted" as "FLAGGED" rather than "FAILED," provided they stay within a total flag cap of 3.

### Audit Findings

#### 1. Logic and Law Compliance
- **Hard vs. Soft Failures**: The implementation correctly preserves HARD failures. In `lineup_soft` and `coherence_soft`, the absence of a through-line, a hook failing its own bar, or a coherence VO point below the floor results in `None`, ensuring these candidates are never "kept" or "accepted."
- **Ruling 37 (Question Hooks)**: The logic in `lineup_soft` and `ly_shape` correctly handles the "no bridge after a question" rule. By designating the first join of a question hook as a `soft_join`, the code prevents the bridge from being placed there while allowing the candidate to be accepted as "FLAGGED."
- **The "One Doubt" Rule**: The implementation of `coherence_soft` (using the `done` parameter) and `coherence_sentences` (checking the `chain` of medley failures) correctly ensures that a clip weak in both medley and coherence is counted as one flag and described by one sentence.
- **Flag Cap**: `seg_marks` correctly aggregates existing clip flags (Step A, edges, stand-alone) and the hook-bar flag, which are then summed with the new soft failures (`ks["n"]`) and compared against `package_pin.REVIEW_FLAGS_MAX` (3).
- **Retry Mechanism**: The `_build` loop correctly implements the "retry once" logic. The use of `retried` as a boolean flag and the condition `(total < lineups or (soft and kept and not retried))` prevents infinite loops and ensures the search for a clean line-up is prioritized.

#### 2. Technical Correctness
- **Complexity**: The use of `best_kept` with a tuple key `(c["n"], -c["low"])` correctly prioritizes the fewest flags, then the highest minimum rating.
- **Data Integrity**: The use of `dict(med, soft=accept_soft)` and `dict(coh, soft=cs_)` ensures that the original cached verdicts are not mutated, but rather extended with the soft-failure metadata for the accepted candidate.
- **Inventory Reporting**: The `inventory` function correctly maps the internal `soft` dictionaries to the required plain-sentence flags for the `medley`, `ly_shape`, and `coherence` rows.

#### 3. Test Coverage
- The 12 new tests in `test_ruling_137.py` cover the critical paths:
    - Soft failures being kept vs. hard failures being rejected.
    - The "best kept" selection logic.
    - The flag cap (3 flags pass, 4 fail).
    - The "one doubt" deduplication.
    - The specific interaction between question hooks and bridges.
    - The priority of clean line-ups over kept candidates.

### Minor Observations
- **[P3]** In `coherence_soft`, the `rest` lambda is defined inside the function. While not a performance issue given the small number of panel answers, it is redefined on every call.

### Final Verdict
The implementation is robust, strictly adheres to the provided Rulings, and maintains the "fail-closed" nature of the pipeline by ensuring that only explicitly defined "soft" failures are permitted to pass as "FLAGGED."

P1_OR_WORSE: 0

## GPT-OSS-20B — CYCLE 1 OUTPUT
# gpt-oss-20b (openai/gpt-oss-20b) 165 s finish=stop usage in 16550 / out 22891 usd_reported=0.003350 usd~0.393 (upper-bound price)

**Findings**

| # | Issue | Severity | Description |
|---|-------|----------|-------------|
| 1 | `inventory` uses undefined variable `med` | **P0** | In `inventory` the line `med_fl = ([f"..."] if hook_fl and medley is not None and med[0] else [])` references `med`, which is not defined in the function scope. This will raise a `NameError` and cause all tests that hit `inventory` to fail. |
| 2 | `inventory` checks `med[0]` instead of `medley[0]` | **P0** | The intended check is whether the medley was successful (`medley[0]`). Using `med[0]` is a logic error that can produce wrong flagging and further test failures. |
| 3 | `inventory` does not include join‑sentences for soft candidates when `medley[0]` is `False` | **P0** | For soft‑only failures (e.g., `J2` in the tests) `chain` is `None` because `medley[0]` is `False`. Consequently `med_fl` is empty, so the medley gate never reports the expected join‑sentence flag. |
| 4 | `lineup_soft` treats a question‑hook flagged join as a soft failure when it is the only flagged join | **P1** | If `question_hook(segs)` is `True` and the only flagged join is the first one (`js[0]`), the current logic sets `bridge = None` and includes that join in `soft_joins`. This incorrectly allows a hard failure (no bridge after a question) to be considered soft and potentially kept. |
| 5 | `lineup_soft` may incorrectly flag a hard failure as soft when `question_hook` is `True` and only the first join is flagged | **P1** | See issue #4 – this can let a hard failure slip through the soft‑pass logic and be retried, violating the hard‑gate rule. |
| 6 | `inventory` incorrectly uses `med_fl` for the `ly_shape` gate in the diff comment, but the actual code uses `join_sentences` correctly – no bug here. | **P3** | Minor documentation mismatch; no impact on functionality. |
| 7 | No other functional bugs detected that affect the current test suite. | **P3** | Minor style or documentation issues that do not break tests. |

**P1_OR_WORSE**: 2 (issues #4 and #5)

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 786 s finish=stop usage in 18182 / out 28878 usd_reported=0.024691 usd~0.488 (upper-bound price)



# Code Audit — pp-selectid / RULING 141 (3) THE LINE-UP CHAIN, PHASE A

## Scope of review

I reviewed the 462-line diff (C1_STEP.diff) covering `pipeline/package.py`, `pipeline/package_pin.py`, and `tests/package/test_ruling_137.py`, against the five questions posed, the governing laws, and the technology-stack constraints.

---

## Findings

### [P2] `over_budget(ai)` gate sits before the retry and can silently suppress it

**Location:** `package.py` lines 140–144 (the `_build` loop).

```python
if over_budget(ai):
    break
if total >= lineups:                      # RULING 141 (3): the judged-line-up budget ran out
    k_ = best_kept(kept)
    swapped, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
```

The retry is designed to fire when the *judged-line-up* budget (`total < lineups`) is exhausted. However, the per-angle `over_budget(ai)` check executes first and `break`s out of the loop entirely. The retry consumes **zero** new model calls (the verdict is read from `judged[key]`, and `total` does not increment for cached verdicts at line 162). If `over_budget` is a per-angle API-call budget, the retry is correctly blocked. If it is a per-angle *judged-line-up* budget (same axis as `total`), the retry is incorrectly suppressed: a valid kept candidate is discarded even though no new call is needed.

The ruling text says "the judged-line-up budget ran out: only the kept candidate's one retry reaches here." It does not mention the per-angle budget. **Clarify whether `over_budget` is the same axis as `total` or a different one; if it is the same axis, move the retry before the `over_budget` check or add an exception for the cached-retry case.**

---

### [P2] `coherence_soft` does not validate the main verdict's `vo_point` value when a panel is present

**Location:** `package.py` lines 64–69.

```python
if any(type(cl.get(lb)) is not int for lb in labs[1:]) or type(coh.get("vo_point")) is not int:
    return None
rest = lambda a: _line_ok(a.get("through_line")) and type(a.get("vo_point")) is int and \
    a["vo_point"] >= fl["vo_point"]
ans = (coh.get("panel") or {}).get("answers")
if not (sum(bool(rest(a)) for a in ans) * 2 > len(ans) if ans else rest(coh)):
    return None
```

When `ans` is non-empty, the majority-of-answers check is the decision. The main `coh["vo_point"]` is type-checked (line 64) but its **value** is never compared to `fl["vo_point"]`. A coherence verdict with `vo_point = 1` (far below the floor of 3) and a panel where 2-of-3 answers have `vo_point = 4` would pass `coherence_soft`. This is likely intentional (the panel is the decision-maker, not the aggregate), but the ruling text says "the VO point at its floor" without qualifying "per panel answer." **Add a comment or an explicit check on `coh["vo_point"] >= fl["vo_point"]` when a panel is present, to make the intent unambiguous for future readers.**

---

### [P2] `lineup_soft` and `coherence_soft` assume `floors` dict keys without a guard

**Location:** `package.py` lines 37, 63, 67, 71.

```python
floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
# ...
fl = coh.get("floors") or STANDARD_LINEUP["coherence"]
# ...
a["vo_point"] >= fl["vo_point"]
# ...
cl[lb] < fl["clip"]
```

If a medley or coherence verdict carries a `floors` dict that is missing the `"clip"` or `"vo_point"` key, a `KeyError` propagates uncaught. M12 (fail closed) is satisfied in the sense that the exception rejects the package, but the failure mode is an unhandled exception rather than a clean `None` return. **Wrap the key access in a `.get()` with a fallback to the standard floor, or add an explicit key-presence check that returns `None`.**

---

### [P3] `kept` list can accumulate duplicate entries for the same key

**Location:** `package.py` lines 173–179.

If the search re-encounters the same set of segments (same `key`) in a later iteration of the while loop, the candidate is appended to `kept` again. `best_kept` picks the same entry (identical `n` and `low`), so the retry is correct. The duplicate is harmless but wastes a small amount of memory and makes the `soft_record` log noisier. **Consider a `key in {k["key"] for k in kept}` guard before appending.**

---

### [P3] `test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too` has a hard-to-read conditional assertion

**Location:** `test_ruling_137.py` lines 427–429.

```python
self.assertEqual(sum(bool(t.get("kept")) for t in out["never_empty"]["soft_record"]["tried"]
                     if t.get("kept")) if not out.get("package") else len([t for t in out["tried"]
                                                                          if t.get("kept")]), 2)
```

The ternary switches the data source based on whether a package was sealed, making the assertion difficult to verify by eye. **Split into two asse

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus (pp-selectid_audit_20261117_1435, ruling 141 (3): the line-up chain, phase A)

SEATS ANSWERED: 3 of 3. qwen3.8-27b: P0/P1 none (three P2s, four P3s). gemma-4-31b-it: P0/P1 none. gpt-oss-20b: three
P0 and two P1 claimed (its "**P1_OR_WORSE**: 2" line is bold, so the driver's tally reads 0); each is answered below.

## gpt-oss's claims
1. [P0] "inventory uses an undefined `med` / `med[0]`": REFUTED. The code reads `medley[0]` (package.py:4561-4564).
   `grep -c "med\[0\]" pipeline/package.py` is 0. Every inventory test (and the 911-test suite) passes.
2. [P0] "`med[0]` instead of `medley[0]`": REFUTED (the same line).
3. [P0] "no join sentences when medley[0] is False": REFUTED. For the accepted candidate the loop sets ok_m True before the
   inventory (package.py:4016: `ok_m, med = True, dict(med, soft=accept_soft)`), and the inventory gets
   medley=(ok_m, med). The two-joins end-to-end test asserts the medley and ly_shape rows FLAGGED with the join sentence.
4-5. [P1] "a question hook's flagged first join is hard (ruling 37)": BY THE AGREED SCOPE. The coordinator's 14:35 ET
   update, after the integrator's answer, makes ruling 37's join SOFT ("may be flagged too"): its render's R1 is soft at
   validate. What stays hard is the rule's purpose, no bridge after a question. The bridge never goes there (lineup_soft
   skips it as bridgeable, bj skips soft joins, ly_shape's other checks are unchanged), and the question-hook end-to-end
   test asserts nothing is written after the question (write join None, pk["bridge"] None).

## qwen's P2s
- "over_budget(ai) sits before the retry and can suppress it": BY DESIGN. over_budget is ruling 41's money stop for the
  angle; the retried candidate pays the same later gates (vision, the writes), so no retry once the money says stop.
- "coherence_soft does not check the summary vo_point under a panel": BY DESIGN. The panel decides by majority
  (package.py:2102); coherence_soft applies the same majority to each answer's through-line and VO point, and still
  requires an int summary vo_point. A panel minority with a stated line cannot pass it.
- "floors keys without a guard": DECLINED. medley() and coherence() always write floors from lineup_floors (calibrated or
  standard, the same keys). Every existing reader uses the same access (last_clip_only, ruling 116's lines).
- P3s (duplicate kept entries of one key: harmless, retried once; rec["kept"] is the record; the tuple `done`;
  a test's conditional assertion): DECLINED (no behaviour change).

## No change from cycle 1 to cycle 2.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261117_1435/C2_STEP.diff (462 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index dd41fd9..5bd269c 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -2217,6 +2217,102 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
   6 |                      cached=bool(getattr(r, "cached", False)))
   7 |  
   8 |  
   9 | +def chain_cap():
  10 | +    """RULING 136 (2) / 141 (1): the most flags a package may carry (package_pin.REVIEW_FLAGS_MAX: one source)."""
  11 | +    import package_pin
  12 | +    return package_pin.REVIEW_FLAGS_MAX
  13 | +
  14 | +
  15 | +def seg_marks(segs):
  16 | +    """RULING 141 (3): the flags a line-up's clips already carry from the never-empty pass's per-clip gates, one sentence
  17 | +    each as the inventory writes them: step A's soft codes (context_a), a sentence edge (cuttable), STAND_ALONE
  18 | +    (stand_alone), the hook under the calibrated bar (the medley row's hook sentence)."""
  19 | +    n = sum(len(set(m.get("step_a_flags") or [])) + len(m.get("edge_flags") or []) + bool(m.get("stand_soft"))
  20 | +            for m in segs or [])
  21 | +    return n + bool((hook_own(segs[0]) or {}).get("flagged")) if segs else n
  22 | +
  23 | +
  24 | +def lineup_soft(segs, med):
  25 | +    """RULING 141 (3), THE LINE-UP CHAIN (phase A) in the never-empty pass: a clips-alone verdict whose ONLY failures are
  26 | +    soft -> {"weak": {label: rating}, "floor", "soft_joins": [join], "n": the flags it adds}, else None. Soft: a clip
  27 | +    rated under the verdict's floor (ruling 116); a flagged join past the one bridge L-y 2 allows (the first bridgeable
  28 | +    flagged join keeps its bridge); the question hook's first join (ruling 37: no bridge goes there). Hard (None): not
  29 | +    measured, no stated through-line, the hook not passing its own bar (the soft hook bar included), a clip with no
  30 | +    rating, or nothing to flag."""
  31 | +    if not segs or not isinstance(med, dict) or med.get("measured") is not True or \
  32 | +            not _line_ok(med.get("through_line")) or not (hook_own(segs[0]) or {}).get("passes"):
  33 | +        return None
  34 | +    labs, cl = labels(len(segs)), med.get("clips") or {}
  35 | +    if any(type(cl.get(lb)) is not int for lb in labs[1:]):
  36 | +        return None
  37 | +    floor = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
  38 | +    js = joins(labs)
  39 | +    flagged = [j for j in js if j in (med.get("flagged") or [])]
  40 | +    bridge = next((j for j in flagged if not (question_hook(segs) and j == js[0])), None)
  41 | +    soft_joins = [j for j in flagged if j != bridge]
  42 | +    weak = {lb: cl[lb] for lb in labs[1:] if cl[lb] < floor}
  43 | +    if not weak and not soft_joins:
  44 | +        return None
  45 | +    return {"weak": weak, "floor": floor, "soft_joins": soft_joins, "n": len(weak) + len(soft_joins)}
  46 | +
  47 | +
  48 | +def soft_joins_of(med):
  49 | +    """RULING 141 (3): the joins an ACCEPTED kept candidate carries unbridged, flagged (none on any other verdict)."""
  50 | +    return list(((med or {}).get("soft") or {}).get("soft_joins") or [])
  51 | +
  52 | +
  53 | +def coherence_soft(coh, segs, done=()):
  54 | +    """RULING 141 (3), phase A, for the kept candidate retried accepting: a coherence verdict whose ONLY failure is clip
  55 | +    ratings under its own floor -> {"weak": {label: rating}, "floor", "n": the NEW flags (a clip in `done`, already
  56 | +    flagged by the clips-alone verdict, is one doubt, flagged once)}, else None: not measured, the hook not passing
  57 | +    its own bar, no stated through-line or the VO point under its floor (for the free panel: not a majority of its
  58 | +    answers with both), a rating missing, or no weak clip."""
  59 | +    if not segs or not isinstance(coh, dict) or coh.get("measured") is not True or \
  60 | +            not (coh.get("hook_own") or {}).get("passes"):
  61 | +        return None
  62 | +    labs, cl = labels(len(segs)), coh.get("clips") or {}
  63 | +    fl = coh.get("floors") or STANDARD_LINEUP["coherence"]
  64 | +    if any(type(cl.get(lb)) is not int for lb in labs[1:]) or type(coh.get("vo_point")) is not int:
  65 | +        return None
  66 | +    rest = lambda a: _line_ok(a.get("through_line")) and type(a.get("vo_point")) is int and \
  67 | +        a["vo_point"] >= fl["vo_point"]
  68 | +    ans = (coh.get("panel") or {}).get("answers")
  69 | +    if not (sum(bool(rest(a)) for a in ans) * 2 > len(ans) if ans else rest(coh)):
  70 | +        return None
  71 | +    weak = {lb: cl[lb] for lb in labs[1:] if cl[lb] < fl["clip"]}
  72 | +    return {"weak": weak, "floor": fl["clip"], "n": sum(lb not in done for lb in weak)} if weak else None
  73 | +
  74 | +
  75 | +def chain_sentences(soft, who):
  76 | +    """RULING 141 (3) / 138 (3): lineup_soft's flags in plain words, each naming its clip (clip ratings, then joins)."""
  77 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  78 | +    return [f"{CLIP_PLACE.get(lb, 'A clip')} ({ch(lb)}): the checker rated how much it adds to the line-up's point "
  79 | +            f"{x} of 5, needs {soft['floor']}." for lb, x in (soft.get("weak") or {}).items()] + \
  80 | +        join_sentences(soft.get("soft_joins"), who)
  81 | +
  82 | +
  83 | +def join_sentences(js, who):
  84 | +    """RULING 141 (3): one plain sentence per unbridged flagged join."""
  85 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  86 | +    return [f"Between {CLIP_PLACE.get(a, 'A clip').lower()} ({ch(a)}) and {CLIP_PLACE.get(b, 'A clip').lower()} "
  87 | +            f"({ch(b)}): the checker could not follow the jump." for a, b in (j.split(" -> ") for j in js or [])]
  88 | +
  89 | +
  90 | +def coherence_sentences(cs, chain, who):
  91 | +    """RULING 141 (3): the coherence acceptance's flags; a clip the clips-alone verdict already flagged keeps that one
  92 | +    sentence (one doubt, flagged once: review_flags_of gives each sentence once)."""
  93 | +    ch = lambda lb: (who or {}).get(lb) or "its channel"
  94 | +    first = dict(zip((chain or {}).get("weak") or {}, chain_sentences(dict(chain, soft_joins=[]), who))) if chain \
  95 | +        else {}
  96 | +    return [first.get(lb) or f"{CLIP_PLACE.get(lb, 'A clip')} ({ch(lb)}): with the narration, the checker rated how "
  97 | +            f"much it supports the point {x} of 5, needs {cs['floor']}." for lb, x in (cs.get("weak") or {}).items()]
  98 | +
  99 | +
 100 | +def best_kept(kept):
 101 | +    """RULING 141 (3): the kept candidate to retry: the fewest flags, then the highest lowest clip rating."""
 102 | +    return min(kept, key=lambda c: (c["n"], -c["low"]))
 103 | +
 104 | +
 105 |  def last_clip_only(segs, med):
 106 |      """RULING 62 (12:00): whether a clips-alone failure is its LAST clip's alone: measured, the through-line stated,
 107 |      the hook passing its calibrated bar (ruling 115: hook_own of the line-up's own hook, as medley() judges it), every
 108 | @@ -2908,10 +3004,10 @@ def ly_shape(pk):
 109 |      med = pk.get("medley") or {}
 110 |      if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 111 |          fails.append("the clips-alone verdict was not measured (L-y 3)")
 112 | -    elif question_hook(segs) and js and js[0] in med["flagged"]:
 113 | +    elif question_hook(segs) and js and js[0] in med["flagged"] and js[0] not in soft_joins_of(med):
 114 |          fails.append(f"ruling 37: a hook ending on a question takes no bridge after it, so {js[0]} must be followable "
 115 |                       f"(the render's R1 reads the sealed clips-alone verdict)")
 116 | -    elif sorted(bridged) != sorted(med["flagged"]):
 117 | +    elif sorted(bridged) != sorted(j for j in med["flagged"] if j not in soft_joins_of(med)):   # 141 (3)
 118 |          fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 119 |                       f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 120 |      rec = pk.get("bridge") or {}
 121 | @@ -3826,6 +3922,8 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 122 |      with ThreadPoolExecutor(max_workers=8) as pool:
 123 |          for ai, angle in (enumerate(angles) if candidate is None else [(candidate["ai"], angles[0])]):
 124 |              dropped, n_lineup, swapped, filled = set(), 0, None, None
 125 | +            kept, retried, accept_key, accept_soft = [], False, None, None   # RULING 141 (3): the never-empty pass's
 126 | +            #   kept candidates (soft failures only), and the one retried accepting
 127 |              sel = story_pool(angle, cleared, by_story)    # RULING 118 (4): a story's angle chooses inside its story
 128 |              #   (its join table, the fill, every swap; lineup_for and the search choose only among the angle's own and
 129 |              #   its join table's moments, so the story holds there by construction)
 130 | @@ -3844,12 +3942,15 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 131 |                      + (f"; NOT ASKED: {jt_err}" if jt_err else "") + f" ({time.time() - t0:.0f} s)")
 132 |              if candidate is not None:                     # RULING 66: its own seeds, so its recorded calls are served
 133 |                  n_lineup, swapped = candidate["n_lineup"] - 1, cand_segs
 134 | -            while total < lineups and not out["packages"] and not out.get("budget_stop") and \
 135 | -                    not out.get("lock_stop"):
 136 | +            while (total < lineups or (soft and kept and not retried)) and not out["packages"] and \
 137 | +                    not out.get("budget_stop") and not out.get("lock_stop"):
 138 |                  if candidate is not None and n_lineup >= candidate["n_lineup"]:
 139 |                      break                                 # RULING 66: the candidate alone, never re-lined or swapped
 140 |                  if over_budget(ai):
 141 |                      break
 142 | +                if total >= lineups:                      # RULING 141 (3): the judged-line-up budget ran out: only the
 143 | +                    k_ = best_kept(kept)                  # kept candidate's one retry reaches here (the condition above)
 144 | +                    swapped, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
 145 |                  if swapped is not None:                   # ruling 41: the swapped line-up is judged next
 146 |                      segs, swapped = swapped, None
 147 |                      exception = supply_exception(segs, ctx)
 148 | @@ -3876,6 +3977,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 149 |                                                   hook_only=True)   # FIRST: the
 150 |                          # pool completes it. A re-line after a drop moves on to the next angle, as before
 151 |                          exception = supply_exception(segs, ctx) if segs is not None else None
 152 | +                if segs is None and soft and kept and not retried:   # RULING 141 (3): the search ran out: the best
 153 | +                    k_ = best_kept(kept)                                # kept candidate, retried once, accepting
 154 | +                    segs, retried, accept_key, accept_soft = list(k_["segs"]), True, k_["key"], k_["soft"]
 155 | +                    exception = supply_exception(segs, ctx)
 156 |                  rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 157 |                         "supply_exception": exception, "attempts": [],
 158 |                         **({"pool_filled": filled} if filled else {}),
 159 | @@ -3908,6 +4013,9 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 160 |                                         writer_family=writers_f)
 161 |                      judged[key] = (ok_m, med)
 162 |                      total += 0 if med.get("replayed") or med.get("cached") else 1   # 12:00: JUDGED line-ups
 163 | +                if key == accept_key:                       # RULING 141 (3): the kept candidate retried ACCEPTING:
 164 | +                    ok_m, med = True, dict(med, soft=accept_soft)   # its cached verdict's soft failures are its flags
 165 | +                    rec["accepted_soft"] = accept_soft
 166 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 167 |                  if jt and med.get("measured"):            # RULING 117 (3): the table's joins against the verdict's
 168 |                      ids_ = [m["moment_id"] for m in segs]
 169 | @@ -3932,6 +4040,13 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 170 |                  if candidate is not None and not ok_m:    # RULING 66: a candidate failing a gate is closed
 171 |                      rec["why"] = "ruling 66: the candidate fails its clips-alone verdict now: closed"
 172 |                      break
 173 | +                if soft and candidate is None and key != accept_key and med.get("measured") and \
 174 | +                        (not ok_m or (question_hook(segs) and joins(labs)[0] in (med.get("flagged") or []))):
 175 | +                    ks = lineup_soft(segs, med)             # RULING 141 (3): soft failures only: KEPT (the search goes
 176 | +                    if ks is not None and seg_marks(segs) + ks["n"] <= chain_cap():   # on, a clean line-up first)
 177 | +                        kept.append({"segs": list(segs), "key": key, "soft": ks, "n": seg_marks(segs) + ks["n"],
 178 | +                                     "low": min(med["clips"][lb] for lb in labs[1:])})
 179 | +                        rec["kept"] = ks
 180 |                  if not ok_m and jt and med.get("measured"):   # RULING 117: the search over the table picks the next
 181 |                      floor_ = (med.get("floors") or STANDARD_LINEUP["clips_alone"])["clip"]
 182 |                      for lb_, mm in zip(labs[1:], segs[1:]):
 183 | @@ -3989,15 +4104,17 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 184 |                                    f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, no swap fits the "
 185 |                                    f"line-up rules: re-lined")
 186 |                      continue
 187 | -                if question_hook(segs) and joins(labs)[0] in med["flagged"]:   # ruling 37: no bridge after a question
 188 | +                if question_hook(segs) and joins(labs)[0] in med["flagged"] and \
 189 | +                        joins(labs)[0] not in soft_joins_of(med):   # ruling 37: no bridge after a question (141: flagged)
 190 |                      dropped.add(segs[1]["moment_id"])
 191 |                      rec["why"] = (f"ruling 37: the join after the question hook must be followable without a bridge, and "
 192 |                                    f"the clips alone flag {joins(labs)[0]}: re-lined")
 193 |                      continue
 194 |                  join = None
 195 | -                if med["flagged"]:
 196 | -                    k = joins(labs).index(med["flagged"][0])
 197 | -                    join = (k, med["joins"][med["flagged"][0]]["why"])
 198 | +                bj = next((j for j in med["flagged"] if j not in soft_joins_of(med)), None)   # 141 (3): soft ones flag
 199 | +                if bj is not None:
 200 | +                    k = joins(labs).index(bj)
 201 | +                    join = (k, med["joins"][bj]["why"])
 202 |                  extra, relined, w_used, written = "", False, 0, ()
 203 |                  pre, no_verdict = None, False
 204 |                  if lock_check is not None:                  # RULINGS 68 / 72: the render's own lock, before any write;
 205 | @@ -4134,12 +4251,12 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 206 |                              break
 207 |                      if join is not None and fields["bridge"] is None:
 208 |                          dropped.add(segs[join[0] + 1]["moment_id"])
 209 | -                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 210 | +                        rec["why"] = (f"the clips-alone verdict flagged {bj}; the writer judged it "
 211 |                                        f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 212 |                          relined = True
 213 |                          break
 214 |                      if fields["bridge"] is not None:
 215 | -                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 216 | +                        fields["bridge_confirmed_by"] = {"join": bj, "why": join[1],
 217 |                                                           "backend": med.get("backend")}
 218 |                      fields["supply_exception"] = exception
 219 |                      pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 220 | @@ -4269,6 +4386,10 @@ def _build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=
 221 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 222 |                      ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f,
 223 |                                            hook=segs[0])     # then on the takeaway; ruling 61: the hook's cached
 224 | +                    cs_ = coherence_soft(coh, segs, (accept_soft or {}).get("weak") or ()) \
 225 | +                        if not ok_c and key == accept_key else None   # RULING 141 (3): the accepted candidate only
 226 | +                    if cs_ is not None and seg_marks(segs) + accept_soft["n"] + cs_["n"] <= chain_cap():
 227 | +                        ok_c, coh = True, dict(coh, soft=cs_)     # its clip ratings under coherence's floor: flagged
 228 |                      att["coherence"] = coh
 229 |                      log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 230 |                          f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 231 | @@ -4437,6 +4558,11 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 232 |      det = fid["deterministic"]
 233 |      viol = {v["rule"] for v in ctx_.get("violations") or []}
 234 |      hook_fl = ((medley[1].get("hook_own") or {}).get("flagged") if soft and medley is not None else None)   # 2b
 235 | +    chain = medley[1].get("soft") if soft and medley is not None and medley[0] else None   # RULING 141 (3)
 236 | +    med_fl = ([f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated it under the "
 237 | +               f"hook bar ({hook_fl})."] if hook_fl and medley is not None and medley[0] else []) + \
 238 | +        (chain_sentences(chain, who) if chain else [])
 239 | +    coh_fl = coherence_sentences(coh["soft"], chain, who) if soft and coh_ok and (coh or {}).get("soft") else []
 240 |      lab = lambda mid: (mids or {}).get(mid, mid)                      # truth is by moment id; flags name the clip
 241 |      edge_fl = [flag_sentence(lab(mid), (who or {}).get(lab(mid)), c) for mid, t in (truth or {}).items()   # RULING
 242 |                 if soft and (t.get("edges") or {}).get("cuttable") is not True for c in (soft_edges(t) or [])]   # 137 2a
 243 | @@ -4488,14 +4614,14 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 244 |                              if edge_fl and truth and all((t.get("edges") or {}).get("cuttable") is True or soft_edges(t)
 245 |                                                           for t in truth.values()) else {})),
 246 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 247 | -                          **votes_of(coh)),
 248 | +                          **votes_of(coh), **({"status": "FLAGGED", "flags": coh_fl} if coh_fl else {})),   # 141 (3)
 249 |          **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 250 |                                 measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"),
 251 | -                           **({"status": "FLAGGED", "flags": [            # RULING 137 stage 2b: the hook under the bar
 252 | -                               f"{CLIP_PLACE['hook']} ({(who or {}).get('hook') or 'its channel'}): the checker rated "
 253 | -                               f"it under the hook bar ({hook_fl})."]} if hook_fl and medley[0] else {}))}
 254 | +                           **({"status": "FLAGGED", "flags": med_fl} if med_fl else {}))}   # 2b hook bar; 141 (3)
 255 |             if medley is not None else {}),
 256 | -        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 257 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]),
 258 | +                             **({"status": "FLAGGED", "flags": join_sentences(chain["soft_joins"], who)}   # 141 (3)
 259 | +                                if chain and chain["soft_joins"] and shape[0] else {}))}
 260 |             if shape is not None else {}),
 261 |          **({"house_style": dict(row(not style, "code (house_style.lint_lines, ruling 6)"),
 262 |                                  why=[f"{v['slot']}: {v['detail']}" for v in style])}
 263 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 264 | index 727abc7..e2403da 100644
 265 | --- a/pipeline/package_pin.py
 266 | +++ b/pipeline/package_pin.py
 267 | @@ -39,6 +39,9 @@ SOFT_GATES = frozenset({"context_a",                     # stage 1: step A's sof
 268 |                          #   word check, "second_pass", stays HARD)
 269 |                          "medley",                          # stage 2b: the hook under the calibrated bar (its own
 270 |                          #   rater's rating; no calibration or another rater stays HARD)
 271 | +                        "coherence", "ly_shape",           # RULING 141 (3), the line-up chain phase A: clip
 272 | +                        #   ratings and unbridged joins of a kept candidate (the through-line and every other L-y check
 273 | +                        #   stay HARD; the takeaway's value rows are not soft)
 274 |                          "stand_alone"})                    # RULING 141 (2): a clip's STAND_ALONE opener (the topic
 275 |  #   rule, ruling 34, and the medley naming Bitcoin stay HARD)
 276 |  REVIEW_FLAGS_MAX = 3
 277 | diff --git a/tests/package/test_ruling_137.py b/tests/package/test_ruling_137.py
 278 | index 6ef4cf8..b0e276d 100644
 279 | --- a/tests/package/test_ruling_137.py
 280 | +++ b/tests/package/test_ruling_137.py
 281 | @@ -374,6 +374,180 @@ class TestRuling141StandAloneSoft(unittest.TestCase):
 282 |          self.assertEqual((row(False)["status"], "flags" in row(False)), ("FAIL", False))
 283 |  
 284 |  
 285 | +class TestRuling141LineUpChain(unittest.TestCase):
 286 | +    """RULING 141 (3), THE LINE-UP CHAIN, PHASE A, in the never-empty pass: a line-up refused ONLY by soft line-up gates
 287 | +    (clip ratings under the clips-alone floor, joins past the one bridge, the question hook's first join) is KEPT, the
 288 | +    search goes on (a clean line-up first), and when it runs out the best kept one is retried once ACCEPTING: its soft
 289 | +    failures, and its clip ratings under coherence's own floor, become plain flags within the cap of 3. The through-line,
 290 | +    the hook's own bar and every other L-y check stay HARD; the writes and the value verdict are untouched."""
 291 | +    H = {"moment_id": "h", "text": "Bitcoin h x.", "hook_rating": {"scroll": 5, "alone": 5, "setup": 5, "backend": "xai:grok"}}
 292 | +    X, Y = {"moment_id": "x", "text": "Bitcoin x x."}, {"moment_id": "y", "text": "Bitcoin y x."}
 293 | +
 294 | +    def med(self, ratings=None, flagged=(), line="Nobody can change the rules of Bitcoin.", measured=True):
 295 | +        labs = PK.labels(3)
 296 | +        return {"measured": measured, "through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
 297 | +                "flagged": [j for j in PK.joins(labs) if j in flagged], "floors": {"clip": 3}}
 298 | +
 299 | +    def test_what_a_clips_alone_verdict_keeps(self):
 300 | +        segs = [self.H, self.X, self.Y]
 301 | +        self.assertEqual(PK.lineup_soft(segs, self.med({"clip_02": 2})),
 302 | +                         {"weak": {"clip_02": 2}, "floor": 3, "soft_joins": [], "n": 1})
 303 | +        two = self.med(flagged=("hook -> clip_01", "clip_01 -> clip_02"))
 304 | +        self.assertEqual(PK.lineup_soft(segs, two)["soft_joins"], ["clip_01 -> clip_02"])     # the first keeps a bridge
 305 | +        q = [dict(self.H, text="Is Bitcoin h x?"), self.X, self.Y]
 306 | +        self.assertEqual(PK.lineup_soft(q, self.med(flagged=("hook -> clip_01",)))["soft_joins"], ["hook -> clip_01"])
 307 | +        for bad in (self.med({"clip_02": 2}, line="none"), self.med({"clip_02": 2}, measured=False), self.med()):
 308 | +            self.assertIsNone(PK.lineup_soft(segs, bad), bad)                  # the through-line stays hard
 309 | +        under = dict(self.H, hook_rating=dict(self.H["hook_rating"], scroll=2))
 310 | +        self.assertIsNone(PK.lineup_soft([under, self.X, self.Y], self.med({"clip_02": 2})))   # the hook's own bar
 311 | +        self.assertIsNone(PK.lineup_soft(segs, dict(self.med(), clips={"hook": 5, "clip_01": 5})))   # unmeasured clip
 312 | +        self.assertEqual(PK.seg_marks([dict(self.H), dict(self.X, step_a_flags=["REFERENT_OUTSIDE", "UNCERTAIN"]),
 313 | +                                       dict(self.Y, edge_flags=["EDGE_IN"], stand_soft="why")]), 4)
 314 | +
 315 | +    def test_what_coherence_accepts(self):
 316 | +        segs = [self.H, self.X, self.Y]
 317 | +        coh = {"measured": True, "hook_own": {"passes": True}, "through_line": "Nobody can change the rules of Bitcoin.",
 318 | +               "clips": {"hook": 5, "clip_01": 2, "clip_02": 2}, "vo_point": 4, "floors": {"clip": 3, "vo_point": 3}}
 319 | +        self.assertEqual(PK.coherence_soft(coh, segs, ("clip_02",)),
 320 | +                         {"weak": {"clip_01": 2, "clip_02": 2}, "floor": 3, "n": 1})   # clip_02 is flagged already
 321 | +        for bad in (dict(coh, vo_point=2), dict(coh, through_line="none"), dict(coh, measured=False),
 322 | +                    dict(coh, hook_own={"passes": False}), dict(coh, clips={"hook": 5, "clip_01": 4, "clip_02": 4})):
 323 | +            self.assertIsNone(PK.coherence_soft(bad, segs), bad)
 324 | +        ans = lambda tl, vo: {"through_line": tl, "vo_point": vo}
 325 | +        panel = lambda *a: dict(coh, panel={"answers": list(a)})
 326 | +        self.assertIsNotNone(PK.coherence_soft(panel(ans("Nobody can change the rules here.", 4),
 327 | +                                                     ans("Nobody can change the rules here.", 3), ans("none", 4)), segs))
 328 | +        self.assertIsNone(PK.coherence_soft(panel(ans("none", 4), ans("none", 4),
 329 | +                                                  ans("Nobody can change the rules here.", 4)), segs))   # no majority
 330 | +
 331 | +    def rig(self, medleys, writes, never_empty=True, **kw):
 332 | +        import test_medley as TM                            # the never-empty pass asks the angle writer again
 333 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], medleys, writes,
 334 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]}, **kw)
 335 | +        r.build_kw = {"never_empty": never_empty}
 336 | +        return r, r.run()
 337 | +
 338 | +    WEAK = (False, [], {"clip_02": 2}, "Nobody can change the rules of Bitcoin.")
 339 | +
 340 | +    def test_a_weak_clip_seals_flagged_only_in_the_never_empty_pass(self):
 341 | +        _, clean = self.rig([self.WEAK] * 2, [], never_empty=False)
 342 | +        self.assertIsNone(clean["package"])
 343 | +        r, out = self.rig([self.WEAK] * 4, [None])
 344 | +        pk = out["package"]
 345 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])      # the best kept: retried
 346 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 347 | +        want = [f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
 348 | +                f"needs 3."]
 349 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["medley"]["flags"]), ("FLAGGED", want))
 350 | +        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
 351 | +                         (want, []))
 352 | +        self.assertEqual(len(r.medley_calls), 4)                           # the retry read its cached verdict
 353 | +
 354 | +    LINE = "Nobody can change the rules of Bitcoin."
 355 | +    J2 = (False, ["hook -> clip_01", "clip_01 -> clip_02"], None, LINE)
 356 | +    B = {"text": "First, why the rules hold.", "cites": ["x"], "why": "the next speaker's 'it' has no referent"}
 357 | +
 358 | +    def test_joins_past_the_one_bridge_flag_and_the_first_keeps_its_bridge(self):
 359 | +        _, out = self.rig([self.J2] * 8, [self.B])          # each pass: 2 line-ups and ruling 63's reorders
 360 | +        pk = out["package"]
 361 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 362 | +        want = [f"Between the second clip ({ch['clip_01']}) and the third clip ({ch['clip_02']}): the checker could "
 363 | +                f"not follow the jump."]
 364 | +        self.assertEqual(pk["bridge"]["join"], "hook -> clip_01")            # the first flagged join: bridged
 365 | +        self.assertEqual({g: (pk["gates"][g]["status"], pk["gates"][g].get("flags")) for g in ("medley", "ly_shape")},
 366 | +                         {"medley": ("FLAGGED", want), "ly_shape": ("FLAGGED", want)})
 367 | +        self.assertEqual((PP.review_flags_of(pk["gates"]), PP.gate_problems(pk["gates"], PP.required_gates(pk))),
 368 | +                         (want, []))                                         # one doubt, flagged once
 369 | +
 370 | +    THREE = (False, ["hook -> clip_01", "clip_01 -> clip_02"], {"clip_01": 2, "clip_02": 2}, LINE)
 371 | +
 372 | +    def test_three_flags_are_kept_and_a_fourth_never(self):
 373 | +        _, out = self.rig([self.THREE] * 8, [self.B])
 374 | +        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # 2 clips + 1 join: the cap
 375 | +        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}   # + the hook under the bar: 4
 376 | +        _, out = self.rig([self.THREE] * 8, [self.B], hooks=under)
 377 | +        self.assertIsNone(out["package"])
 378 | +        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 379 | +
 380 | +    def test_a_clean_line_up_found_later_wins(self):
 381 | +        ok = (True, [], None, self.LINE)
 382 | +        r, out = self.rig([self.WEAK, self.WEAK, self.WEAK, ok], [None])
 383 | +        pk = out["package"]
 384 | +        self.assertEqual(([s["moment_id"] for s in pk["segments"]], pk["gates"]["medley"]["status"]),
 385 | +                         (["h", "x", "z"], "PASS"))
 386 | +        self.assertEqual(PP.review_flags_of(pk["gates"]), [])
 387 | +        self.assertTrue([t for t in out["tried"] if t.get("kept")])          # kept, never needed
 388 | +
 389 | +    def test_coherence_ratings_flag_only_for_the_accepted_candidate(self):
 390 | +        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 5)])
 391 | +        pk = out["package"]
 392 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 393 | +        alone = (f"The third clip ({ch['clip_02']}): the checker rated how much it adds to the line-up's point 2 of 5, "
 394 | +                 f"needs 3.")
 395 | +        coh = (f"The second clip ({ch['clip_01']}): with the narration, the checker rated how much it supports the "
 396 | +               f"point 2 of 5, needs 3.")
 397 | +        self.assertEqual((pk["gates"]["coherence"]["status"], sorted(pk["gates"]["coherence"]["flags"])),
 398 | +                         ("FLAGGED", sorted([coh, alone])))
 399 | +        self.assertEqual(sorted(PP.review_flags_of(pk["gates"])), sorted([alone, coh]))   # clip_02 flagged once
 400 | +        _, out = self.rig([self.WEAK] * 4, [None], coherences=[(False, 2, 2)])   # the VO point too: today's path
 401 | +        self.assertIsNone(out["package"])
 402 | +
 403 | +    def test_a_question_hook_join_flags_with_no_bridge_at_the_question(self):
 404 | +        import test_medley as TM
 405 | +        ms = [dict(m, text="Is Bitcoin h x?") if m["moment_id"] == "h" else m for m in TM.TestBuildLoop.MS]
 406 | +        q = (True, ["hook -> clip_01"], None, self.LINE)          # one flagged join: ruling 37 refuses it today
 407 | +        r = TM.Rig(ms, ["h", "x", "y", "z"], [q] * 8, [None],
 408 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
 409 | +        r.build_kw = {"never_empty": True}
 410 | +        pk = r.run()["package"]
 411 | +        ch = {s["label"]: s["channel"] for s in pk["segments"]}
 412 | +        want = [f"Between the opening clip ({ch['hook']}) and the second clip ({ch['clip_01']}): the checker could not "
 413 | +                f"follow the jump."]
 414 | +        self.assertEqual((pk.get("bridge"), r.write_calls[-1][1]), (None, None))   # nothing written after the question
 415 | +        self.assertEqual((pk["gates"]["ly_shape"]["status"], PP.review_flags_of(pk["gates"])), ("FLAGGED", want))
 416 | +
 417 | +    def test_coherence_counts_one_doubt_per_clip_against_the_cap(self):
 418 | +        under = {"h": (2, 5, 5), "x": (1, 1, 1), "y": (1, 1, 1), "z": (1, 1, 1)}     # the hook's flag: 1
 419 | +        _, out = self.rig([self.WEAK] * 8, [None], hooks=under, coherences=[(False, 2, 5)])
 420 | +        self.assertEqual(len(PP.review_flags_of(out["package"]["gates"])), 3)   # hook + clip_02 + clip_01: 3, not 4
 421 | +        _, out = self.rig([self.J2] * 8, [self.B], hooks=under, coherences=[(False, 2, 5)])
 422 | +        self.assertIsNone(out["package"])                  # hook + a join + 2 new weak clips: 4, over the cap
 423 | +
 424 | +    def test_the_retry_takes_the_fewest_flags_and_the_budget_end_retries_too(self):
 425 | +        two = (False, [], {"clip_01": 2, "clip_02": 2}, self.LINE)   # [h, x, y]: y weak (1 flag), then [h, x, z]:
 426 | +        r, out = self.rig([self.WEAK, two, self.WEAK, two], [None])  # x and z weak (2 flags); both kept
 427 | +        self.assertEqual(sum(bool(t.get("kept")) for t in out["never_empty"]["soft_record"]["tried"]
 428 | +                             if t.get("kept")) if not out.get("package") else len([t for t in out["tried"]
 429 | +                                                                                  if t.get("kept")]), 2)
 430 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "x", "y"])   # 1 flag, not 2
 431 | +        import test_medley as TM
 432 | +        r = TM.Rig(TM.TestBuildLoop.MS, ["h", "x", "y", "z"], [self.WEAK] * 2, [None],
 433 | +                   follow_up={"angles": [TM.angle(["h", "x", "y", "z"], "h")]})
 434 | +        r.build_kw = {"never_empty": True, "lineups": 1}  # one judged line-up a pass: the budget ends first
 435 | +        self.assertEqual([s["moment_id"] for s in r.run()["package"]["segments"]], ["h", "x", "y"])
 436 | +
 437 | +    def test_the_rows_flag_only_in_the_soft_pass_and_only_on_a_passing_shape(self):
 438 | +        t = {"ok": True, "replayed": False, "edges": {"cuttable": True, "in": {"ok": True}, "out": {"ok": True}}}
 439 | +        soft_med = {"backend": "xai:grok", "replayed": False, "measured": True, "flagged": ["clip_01 -> clip_02"],
 440 | +                    "hook_own": {"passes": True}, "soft": {"weak": {}, "floor": 3, "soft_joins": ["clip_01 -> clip_02"],
 441 | +                                                           "n": 1}}
 442 | +        coh = {"backend": "b", "replayed": False, "measured": True, "soft": {"weak": {"clip_01": 2}, "floor": 3, "n": 1}}
 443 | +        who = {"hook": "A", "clip_01": "B", "clip_02": "C"}
 444 | +        inv = lambda soft, shape: PK.inventory(**dict(TestStage2a().base(t), coh=coh), medley=(True, soft_med),
 445 | +                                               shape=shape, soft=soft, who=who)
 446 | +        g = inv(True, (True, []))
 447 | +        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["FLAGGED"] * 3)
 448 | +        g = inv(False, (True, []))
 449 | +        self.assertEqual([g[k]["status"] for k in ("medley", "ly_shape", "coherence")], ["PASS"] * 3)
 450 | +        self.assertEqual(inv(True, (False, ["3 bridges"]))["ly_shape"]["status"], "FAIL")   # a hard L-y failure
 451 | +
 452 | +    def test_no_through_line_is_never_kept(self):
 453 | +        none = (False, [], {"clip_02": 2}, "none")
 454 | +        _, out = self.rig([none] * 4, [None])
 455 | +        self.assertIsNone(out["package"])
 456 | +        self.assertFalse([t for t in out["never_empty"]["soft_record"]["tried"] if t.get("kept")])
 457 | +
 458 | +
 459 |  class TestTheDayCount(unittest.TestCase):
 460 |      def test_counted_per_day_ledger(self):
 461 |          with tempfile.TemporaryDirectory() as d:
 462 | 
```

---

pp-selectid: RULING 141 (3) (orchestrator 13:40 ET Nov 17), THE LINE-UP CHAIN, PHASE A: the approved R136 design (2)'s
KEPT CANDIDATES for clip ratings and joins, in the never-empty pass only. Context: package.build runs the clean pass, and
only when it seals nothing runs _build(soft=True); soft gates flag in one plain sentence each; at most 3 flags seal
(package_pin.REVIEW_FLAGS_MAX, package_pin.py:47; review_flags_of :399 gives each sentence once; flagged_ok :392 needs
non-empty string flags). Scope agreed with the integrator (14:35 ET): its render never holds on unbridged flagged joins
(R11 does not read medley.flagged; R1 is soft at validate; check_pin_only checks no joins); its check_pin_only REFUSES
a pin whose takeaway_value is not exactly PASS (package_pin TAKEAWAY_GATES :68), so the writes and the value verdict are
UNTOUCHED here. The through-line stays HARD (ruling 141 (1): "those four clips do not make a video").

THE CHANGE (package.py; the clean pass is unchanged):
(a) lineup_soft (:2235): a clips-alone verdict (medley(), its ok rule :2212: hook passing, through-line stated, every clip
    >= the floor, <= LY_MAX_BRIDGES flagged joins) whose ONLY failures are soft: clips under the floor; flagged joins
    past the one bridge (the first bridgeable flagged join keeps its bridge); the question hook's first join (ruling 37:
    no bridge after a question). None (hard) when not measured, no through-line, the hook failing its own bar, a clip
    unrated, or nothing to flag.
(b) THE LOOP, per angle: kept / retried / accept_key reset at :3925. KEEP (:4043): in the soft pass, a verdict failing
    (or ruling 37 refusing) with lineup_soft non-None and seg_marks (:2226: the clips' own flags) + its flags <= 3 is
    appended; the search then goes on exactly as before (a clean line-up wins first: it seals and the loop ends).
    RETRY: when the search runs out (:3980, where today "no line-up" breaks) or the judged-line-up budget ends (the
    condition :3945 and :3951), the best kept candidate (best_kept :2311: fewest flags, then the highest lowest rating) is
    retried ONCE; its clips-alone verdict is the cached one (judged, :4008; no new call, total unchanged) and is taken as
    passing with med["soft"] (:4016). Ruling 37 skips a soft join (:4107); the bridge goes to the first flagged join that
    is not soft (bj, :4114, also used for the declined-bridge reason and bridge_confirmed_by). Every later gate runs as
    today: the lock (HARD), vision, the writes, the re-screen.
(c) COHERENCE, the accepted candidate only (:4389): a failure whose ONLY cause is clip ratings under coherence's own floor
    (coherence_soft :2264: measured, the hook passing, the through-line stated and the VO point at its floor; for the
    free panel (:2102's majority) a majority of answers with both) is accepted when every flag stays within 3; a clip the
    clips-alone verdict already flagged is one doubt (counted once, its same sentence reused). Any other failure follows
    today's path (the VO point under the floor still rewrites the takeaway).
(d) ly_shape (:2973): its ruling-37 check and "every flagged join bridged" accept exactly the soft joins of an accepted
    candidate (soft_joins_of :2259; empty for any other verdict). Its other checks stay HARD.
(e) inventory (:4536, :4561): the medley row FLAGGED with the hook-bar sentence (2b) + the clip and join sentences; the
    ly_shape row FLAGGED with the join sentences (only when the shape passes); the coherence row FLAGGED with its
    sentences. package_pin.SOFT_GATES adds "coherence" and "ly_shape".

TESTS (test_ruling_137, 12 new; test_medley's Rig runs the real build): the units of (a) and (c); END TO END: a weak clip
seals flagged only in the never-empty pass (the retry reads its cached verdict); two flagged joins: the bridge at the
first, the second flagged on medley and ly_shape, once in review_flags; a question hook's join flags with nothing
written after the question; 3 flags keep and a 4th never; a clean line-up found later wins; coherence flags only for
the accepted candidate (the VO point under its floor still fails); the cap counts one doubt per clip; the retry takes
the fewest flags and the budget's end retries too; the rows flag only in the soft pass and only on a passing shape; no
through-line is never kept. Mutations: 22 of 24 killed. C1 (the retry's `soft`) is equivalent: kept fills only in the
soft pass. C12 is NOT UNIT-TESTED, please read: coherence is softened only for key == accept_key; the mutant widens it to
any later line-up of the angle after a retry, reachable only through the writer re-screen's hard refusal and its swap
(:4240) after the accepted candidate.

PLEASE CHECK: (1) can a HARD failure be kept or accepted (the through-line, the hook's own bar, the lock, a non-join
L-y check, coherence's VO point)? (2) the clean pass unchanged; (3) the retry: once per angle, the cached verdict, the
budget condition cannot loop; (4) the cap (unique sentences) and the one-doubt rule; (5) the tests.


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


Tag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), [P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.
