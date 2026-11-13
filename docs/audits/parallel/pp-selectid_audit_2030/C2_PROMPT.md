# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2030
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 84 s finish=stop usage in 40263 / out 4867 usd~0.194 (upper-bound price)

# Audit: pp-selectid — L-y medley (package.py, package_pin.py, providers.py, proof_ly.py, tests)

## P0

**P0-1. `ly_shape` accepts a bridge at the hook join when the flagged join is a *clip* join, and vice versa — actually it's stricter than that; the real P0 is the intro/bridge slot mismatch in `assemble_medley` vs `ly_shape`'s `bridged` computation.**
`package.py:541` — `bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] ...]`. In `assemble_medley` (line 222-224), when the bridge sits after the hook (`k == 0`), `vo["intro"] = b["text"]` and `bridges_after_clip = [n_clips]` (takeaway only). So `after[:-1]` is empty and `bridged = [js[0]]` — correct. But when the bridge sits after clip k>0, `vo["intro"] = None` and `bridges = [bridge_text, takeaway]`, `after = [k, n_clips]`; `bridged = [js[k]]` — correct. However `texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]` (line 542): for the k==0 case, `texts = [bridge_text]` and `bridged = [js[0]]` — lengths match. For the mid-bridge case, `texts = [] + [bridge_text]` — matches. **But** if a *non-medley* package (old `assemble`, no `shape` key) reaches `cheap_checks`, `ly_shape` is skipped (line 584, `pk.get("shape") == "medley"`), yet `inventory` is called with `shape=ly_shape(pk)` unconditionally in `build` (line 792) — for an old-shape package `ly_shape` reads `vo["bridges"]` where the last element is a *bridge*, not the takeaway, and `after[-1] != n_clips` (old shape's last bridge is after the last clip, not after clip n_clips... actually old shape's `bridges_after_clip = range(1, nb+1)`, so `after[-1] = nb = len(segs)-2 = n_clips-1 ≠ n_clips`) → `ly_shape` fails → the `ly_shape` inventory row is FAIL → pin refused. Currently `build` only produces medleys, so this is latent, not live. Downgrade: **P1**.

**P0-2. `medley()`'s contract check omits `vo_point`-style extras but the deeper issue: `ok` requires `min(v["clips"].values()) >= COHERENCE_MIN` — yet the hook's rating is included, and `build`'s failure path (line 697-698) drops weak clips by label but `by_lab` maps labels→segs of the *current* line-up while `med["clips"]` keys are those same labels; if `med` was not measured, `med.get("clips")` is None and `weak` stays empty → `rec["why"]` set, `break` — correct. Verified consistent.** No P0 here.

**P0-3. `write_takeaway` budget fallback silently violates the runtime gate.** `package.py:472` — `budget = takeaway_budget(content, other) or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)`. When `takeaway_budget` returns None (clips too long/short for 60-70 s), the writer is told 8-30 words, the package is assembled, and `cheap_checks` then fails RUNTIME — but only after a paid write. Worse: `medley_content_range()` (line 102-108) computes the clips' seconds assuming the takeaway is *exactly* at the cap/min, and `lineup_for` enforces `lo <= dur <= hi` — so the fallback should be unreachable for the no-bridge case. But with `other` (a bridge) the budget uses the *actual* bridge words while `lineup_for` used `medley_content_range()` with the *default* `LY_BRIDGE_WORDS=12`; a writer's bridge of, say, 20 words shifts the needed clip seconds by (20-12)/2.5 = 3.2 s, which can push a dur near the `hi` edge out of 60-70 → RUNTIME FAIL after the fact. Concrete: clips dur = 51.4 s (just inside default hi 51.5), bridge 20 words → needed content hi = 51.5 - 8/2.5 = 48.3... wait, `medley_content_range(n_bridges=1)` hi = 70 - 14.30 - (12/2.5+1) - (8/2.5+1) = 48.3; dur 51.4 > 48.3 → no takeaway of ≥8 words lands 70 s → `takeaway_budget` returns None → fallback 8-30 words → RUNTIME gate fails, write wasted, and after `WRITES` attempts the angle dies with no diagnostic that the *line-up* was at fault. **P1** (the loop does re-line only via other paths; here `extra = _redo(cheap)` tells the writer to "change the takeaway's length", which cannot fix it — the writer is asked for 8-30 words again, infinite-until-`writes` failure). Actually `_redo` says "change the takeaway's length" while the prompt's budget is unchanged — the retry cannot succeed. **P1, arguably P0 for wasted spend**; the loop terminates (writes bounded) so: P1.

## P1

**P1-1. `ly_shape` "flagged join left unbridged" vs "bridge at unflagged join" — the `sorted(bridged) != sorted(med["flagged"])` check (line 550) compares join *strings*; `med["flagged"]` comes from the stored verdict, but `build` (line 734-739) drops the line-up when the writer declines the bridge *without* re-asking the verdict — correct per L-y 2. However when the writer *gives* the bridge, `fields["bridge_confirmed_by"]` records it, but `ly_shape` never checks the bridge's `cites` reference the flagged join's clips — only that a `why` exists. A bridge whose cites point at unrelated ids passes. Minor: P2.**

**P1-2. `providers.py` ledger: `usd_reported` accumulates at the *run* level (`d["us

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 85 s finish=stop usage in 39454 / out 624 usd~0.213 (upper-bound price)

**Findings (from diff only):**
- **P2: pipeline/package.py:689** (build loop): For a line-up passing medley() with flagged joins, write_takeaway() is called with `join=(k, why)`; if writer returns `{"bridge": null, ...}` the code does `dropped.add(segs[join[0]+1]["moment_id"])` and re-lines. Concrete failure: input angle with moments ["h","c1","c2"] (play order), medley flags "clip_01 -> clip_02", writer returns valid takeaway+title+caption but explicit null bridge → line-up is dropped and angle exhausted even though L-y 2 explicitly allows writer to judge the jump followable without narration (no re-line trigger needed; clips-alone already passed).
- **P2: pipeline/package_pin.py:889** (bridge_slots): For medley shape with intro bridge (k=0), returns ["takeaway"] only; line_problems then checks `by.get(s) != t for s,t in zip(slots, bridges)`. Concrete failure: package with vo={"intro":"Bridge text", "bridges":["Takeaway text"], "bridges_after_clip":[0,2]}, lines slot "intro" present but bridge_slots omits it → "bridges" mismatch, PinRefused on bytes that match the rendered VO (violates L-j exact bytes + L-y 2 exception for hook join).
- **P2: pipeline/package.py:840** (inventory): medley row uses `measured=bool(medley[1].get("measured"))` but ly_shape row is always emitted with status from `shape=(ok, fails)` even if medley["measured"]=False. Concrete failure: medley reply raises ValueError (out-of-contract, measured=False, flagged=None) → cheap_checks adds LY_SHAPE violation but inventory still emits "ly_shape":{"status":"FAIL"} while medley row is "NOT RUN"; gate_problems(required_gates(pk)) treats missing PASS as blocker but L-m + L-j require every REQUIRED row exactly PASS with n>=1 on final bytes (inconsistent inventory for must-fail preview reference).

No other violations of L-y 1-6, L-j (exact gates on final bytes, fail-closed), L-k (canon not touched), L-l (strict JSON contracts + reject on bad fields), M2/LAW20 (no gate reclassification), or LAW22 (old assemble path preserved for v2f). providers.py ledger tracks reported cost beside estimate but never bypasses limit_usd guard on estimate. test_medley.py proves every ly_shape must-fail, medley contract, lineup order/repeat_exception, takeaway_budget arithmetic, and pin rows. Removed plain_vo/write_v3 is dead under new default (L-y 1).

**SHIP: yes with conditions** (fix the 3 P2 edge cases on bridge_after=0, null-bridge re-line, and inventory measured=False before merge; re-run proof_ly.py table).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 90 s finish=stop usage in 44698 / out 4128 usd~0.196 (upper-bound price)

# Code Audit: pp-selectid-2030 (L-y Medley)

## P0 Findings

### P0-1: `ly_shape` allows a bridge at an unflagged join when the clips-alone verdict is unmeasured
**File:** `pipeline/package.py`, `ly_shape()` (lines ~547-552 in diff)

**Scenario:**
1. `medley()` fails (e.g., provider error, out-of-contract JSON) → returns `ok=False, verdict={"measured": False, "flagged": None}`.
2. In `build()`, `if not ok_m:` is true. `med.get("measured")` is `False`, so `if not med.get("measured") or not weak:` → `rec["why"] = "..."` and `break`. **No package is assembled.**

This path is safe. **However**, consider the case where `medley()` *succeeds* but the writer is asked for a bridge at a join, and the writer returns a bridge. The `ly_shape` check compares `sorted(bridged) != sorted(med["flagged"])`. If `med["flagged"]` is `[]` (no joins flagged) but the writer still returns a non-null bridge (which `write_takeaway` should reject via `if join is None: raise ValueError`), this is caught.

**Re-examination:** The real risk is in `write_takeaway`: if `join is None` and the model returns a non-null bridge, it raises `ValueError`. If `join is not None` and the model returns `null`, `build()` drops the clip and re-lines. So the writer contract is enforced.

**Verdict on P0-1:** Not a P0. The fail-closed path in `build()` prevents unmeasured verdicts from reaching `ly_shape`. Downgrading.

---

### P0-2: `takeaway_budget` can return a range where the *lower* bound produces a runtime estimate below 60 s
**File:** `pipeline/package.py`, `takeaway_budget()` (lines ~111-124 in diff)

**Scenario:**
- `content_s = 33.0` (just above `medley_content_range()[0]` = 32.7).
- `fixed = 33.0 + 14.30 + 0 = 47.30` (no other VO lines).
- `words_at(61.5) = 2.5 * (61.5 - 47.30 - 1.0) = 2.5 * 13.2 = 33.0` → `lo = max(8, ceil(33.0 - 1e-9)) = 33`.
- `words_at(68.5) = 2.5 * (68.5 - 47.30 - 1.0) = 2.5 * 20.2 = 50.5` → `hi = min(30, floor(50.5 + 1e-9)) = 30`.
- `lo = 33 > hi = 30` → falls through to `RUNTIME_S` check:
  - `words_at(60.0) = 2.5 * (60.0 - 47.30 - 1.0) = 2.5 * 11.7 = 29.25` → `lo = max(8, 29) = 29`.
  - `words_at(70.0) = 2.5 * (70.0 - 47.30 - 1.0) = 2.5 * 21.7 = 54.25` → `hi = min(30, 54) = 30`.
  - `lo=29 <= hi=30` → returns `(29, 30)`.
- Writer produces 29-word takeaway. `runtime() = 33.0 + 29/2.5 + 1.0 + 14.30 = 33.0 + 11.6 + 1.0 + 14.30 = 59.9 s`.
- **59.9 < 60.0** → `rt_ok = False` → cheap gate fails.

The budget *should* have returned `None` or a range that guarantees ≥ 60 s. The `LY_AIM_S` check failed (correctly), but the `RUNTIME_S` fallback uses `math.ceil(words_at(a) - 1e-9)` which can round *down* to a word count that lands just below the target. The `-1e-9` epsilon is meant to handle floating-point noise, but here it causes `ceil(29.25 - 1e-9) = 29` when the true minimum to reach 60 s is `ceil(29.25) = 30`.

**Fix:** Use `math.ceil(words_at(a))` without the epsilon subtraction for the lower bound, or verify the resulting runtime after computing `lo`.

**Impact:** A package that should pass the runtime gate fails, wasting a write attempt. Not a security issue, but a correctness bug that can cause unnecessary re-writes or, if the writer is at its last attempt, a failed build.

---

### P0-3: `lineup_for` with `repeat_ok=True` can select two clips from the same channel *and* same video
**File:** `pipeline/package.py`, `lineup_for()` (lines ~378-380 in diff)

**Code:**
```python
if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
    continue
```

**Scenario:**
- `n = 2` (hook + 2 clips = 3 segments).
- `chans = ["A", "A", "B"]` → `len(set(chans)) = 2 ≠ 3`.
- `repeat_ok=True`, `len(set(chans)) == 2 == n` ✓.
- `video_ids = ["v1", "v1", "v2"]` → `len(set) = 2 ≠ 3` → **skipped**. Correct.
- `video_ids = ["v1", "v2", "v2"]` → `len(set) = 2 ≠ 3` → **skipped**. Correct.
- `video_ids = ["v1", "v2", "v3"]` → `len(set) = 3 == n+1` → **allowed**. But `chans = ["A", "A", "B"]` means two clips from channel A, from videos v1 and v2. This is the intended supply exception.

Wait — the condition `len({m["video_id"] for m in (h, *combo)}) == n + 1` requires *all* video IDs to be distinct. With 3 segments, it requires 3 distinct videos. If channel A provides two clips, they must be from two different videos. This is correct per L-y 4.

**Re-examination:** The logic is sound. Downgrading.

---

## P1 Findings

### P1-1: `medley()` prompt includes clip text up to 900 chars, but `CI._q` may truncate mid-word
**File:** `pipeline/package.py`, `medley()` (line ~433 in diff)

**Code:**
```python
clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
                  for lb, m in zip(labs, segs))
```

If `CI._q` truncates at 900 chars without word-boundary awareness, the model sees a 

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the L-y diff (orchestrator 20:30 ET Nov 12): cycle 1 consensus (synthesis by the pp-selectid session, 21:05 ET)

**Run.** Cycle 1 ran on C1_STEP.diff (103,655 bytes; prompt 135,833 bytes). Reviewers, each SHIP verdict and its
time:
- grok-4.20-0309-reasoning (xAI): SHIP yes with conditions, 85 s.
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no, 90 s.
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions, 84 s.

**Spend:** about $0.60 at the config's upper-bound prices; direct HTTP, not on the router's ledger.

**The rule:** consensus (two or more reviewers) is implemented; a unique finding is evaluated on its evidence.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | the takeaway's length vs the runtime gate (qwen P0-2 on the rounding; glm P0-3 on a bridge's seconds) | glm's case IMPLEMENTED. write_takeaway budgeted the takeaway without the bridge, so a flagged join's bridge could push the estimate past 70 s, and the redo prompt kept the same budget. Now: a write offered a bridge budgets with a bridge of LY_BRIDGE_WORDS (12) words; every redo budgets with the bridge actually written; a RUNTIME redo carries the exact word range ("a takeaway of N-M words lands it", or "shorten the bridge"). qwen's case is REFUTED on the numbers: ceil(29.25 - 1e-9) is 30, not 29, and test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps sweeps 30.0-55.9 s in 0.1 s steps, asserting runtime() of both bounds inside 60-70 |
| K2 | test gaps (qwen P2-5: a takeaway over 30 words; glm P2-6: build()'s loop control untested) | IMPLEMENTED: test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins; TestBuildLoop with every model stubbed (nothing written when the clips alone fail; a weak clip dropped and the line-up re-picked; a declined bridge drops the clip after the flagged join; a given bridge sits at the flagged join with its reason and pins; the supply exception recorded). 30 tests in test_medley.py |
| K3 | the inventory's medley / ly_shape rows (grok P2-3; glm P2-8) | REFUTED. ly_shape's row comes from row(), so it has status, by, replayed (False) and n (1). When the clips-alone verdict is not measured, the medley row is NOT RUN and ly_shape is FAIL: both are not PASS, so required_gates refuses the pin (L-m, L-j). build() also never assembles a package after an unmeasured clips-alone verdict |
| K4 | the bridge after the hook (grok P2-2 says line_problems refuses it; glm P1-7 traced it and found it consistent) | REFUTED by a test. For k == 0, assemble_medley puts the bridge in vo.intro and the slot "intro"; bridges = [takeaway] with after [n_clips]. bridge_slots gives ["takeaway"], and line_problems checks the intro separately. Grok's scenario (after_clip [0, 2]) is a shape the code never builds. The test pins a hook-join bridge: edl_vo {"intro": bridge, "bridges": [takeaway after the last clip]} |

## Unique findings, evaluated

| finding | disposition |
|---

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2030/C2_STEP.diff (1734 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 51f24c7d..300d36d1 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -9,29 +9,44 @@ usable()      moments a package may use: on screen eligible (word timing, law L-
   6 |  prescreen()   step A of law L-s on each usable moment's own context, ONCE per moment (package-independent), stored on
   7 |                the moment (`store`: a JSON ledger keyed by moment and the step-A prompt); never recomputed
   8 |  ANGLES        role angle_write: up to MAX_ANGLES one-sentence angles, each backed by 3-8 cleared moments from >= 3
   9 | -              channels (one clip per channel, L-u)
  10 | -lineup_for()  code: hook + 2-3 clips for one angle, every segment from a different channel, at most one price prediction
  11 | -              (L-u), a clip under SHORT_CLIP_S only as the punchline, and the length the runtime (60-70 s, L-o) AND the
  12 | -              factory's EDL rule R4 (VO <= 25 % of runtime, one bridge per channel transition) both allow
  13 | -write_v3()    role angle_write: the PBX MAX VO in the renderer's order (hook -> intro -> clip 1 -> bridge -> ...), in
  14 | -              one of two styles (05:25 item 3): "host" (tease / hedge-matched hand-off of a VERIFIED speaker / the
  15 | -              host's own takeaway after a clip) or "quote" (show + topic, at most four exact words quoted); NEVER a
  16 | -              restatement of a clip's claim; word budgets from R4 and the runtime
  17 | -GATES (hard, every one, recorded in a sealed inventory, package_pin.REQUIRED_GATES):
  18 | -              cheap first (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4;
  19 | +              channels (one clip per channel, L-u), listed in PLAY ORDER (L-y 3)
  20 | +lineup_for()  code: the hook + 2-4 clips for one angle in the proposer's play order, every segment from a different
  21 | +              channel, at most one price prediction (L-u), a clip under SHORT_CLIP_S only as the punchline, and seconds
  22 | +              that let ONE takeaway land the factory's runtime estimate in 60-70 s (L-o, L-y 4)
  23 | +medley()      the blind clips-ALONE verdict (L-y 3): a through-line, a rating per clip, a verdict per join
  24 | +write_takeaway() role angle_write: the ONE takeaway (host commentary), ONE title, ONE caption, and the one bridge only
  25 | +              at a join the clips-alone verdict flagged (L-y 2); NEVER a restatement of a clip's claim
  26 | +GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gates):
  27 | +              the clips-alone verdict first (no writing before it passes);
  28 | +              cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
  29 |                then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
  30 |                integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
  31 | -              start in the background as soon as a line-up is fixed; then COHERENCE (blind, >= 4).
  32 | +              start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
  33 |                Every verdict avoids the vendors and model families of every reply whose text it judges (L-x).
  34 |                A rejected line goes back to the writer with the exact violations; a clip that fails exclusion or L-v 2
  35 | -              is dropped and the angle re-lined; at most WRITES writes per angle and MAX_ANGLES angles; the first
  36 | -              package with coherence >= COHERENCE_MIN wins (05:30).
  37 | +              is dropped and the angle re-lined; at most WRITES writes per line-up, LY_LINEUPS line-ups per angle and
  38 | +              MAX_ANGLES angles; the first package that passes every gate wins (05:30).
  39 |  OUTPUT pp.package/1: segments (moment ids, verbatim text, times), VO, title, caption, the gate inventory, the model per
  40 |                artefact, seconds and dollars.
  41 | +
  42 | +L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12, PBX's verdict on the reviewed video; amends L-q, L-w 1 and
  43 | +R4-moments): build() makes the MEDLEY the default shape. The hook and 2-4 clips play back to back with no narration,
  44 | +then ONE takeaway after the last clip (host commentary, class D, one or two sentences, <= 30 words), then the
  45 | +sign-off. There is no intro after the hook and no bridge.
  46 | +- SELECTION carries the weight: the angle proposer gives the moments in PLAY ORDER, each clip's opening making sense
  47 | +  after the previous clip's ending in the speaker's own words (lineup_for).
  48 | +- The blind coherence verdict is asked on the clips ALONE first (medley(): a through-line a viewer can state, a rating
  49 | +  per clip, and per join whether a viewer can follow the jump). Only then is it asked on the takeaway (coherence()).
  50 | +- A bridge is the EXCEPTION: at most ONE, only at the join the clips-alone verdict flagged, and only when the writer
  51 | +  also judges a viewer cannot follow it. The package records why (ly_shape()). Two or more flagged joins mean the
  52 | +  line-up is wrong: other clips are picked.
  53 | +- 3-5 clips; the factory's runtime estimate stays inside 60-70 s (the measured final is accepted at 58-72 s, ruling 12).
  54 | +- One clip per channel unless the supply forces otherwise, and then the package says so (supply_exception).
  55 |  """
  56 |  import hashlib
  57 |  import itertools
  58 |  import json
  59 | +import math
  60 |  import os
  61 |  import re
  62 |  import time
  63 | @@ -42,11 +57,8 @@ import eligibility as E
  64 |  import vo_fidelity as VF
  65 |  
  66 |  SEG_MAX_S = 20.0                   # L-u: at most 20 s per source video
  67 | -RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the one hard length rule
  68 | -WPS = 2.6                          # PBX MAX VO words per second: an ASSUMPTION until the render measures it
  69 | -SIGNOFF_WORDS = 18                 # the preview's sign-off ("Clips today from A, B, and C. Go follow them ...")
  70 | -FIXED_S = round(E.TAIL_S - SIGNOFF_WORDS / WPS, 2)   # credits card + outro + transitions without VO (~7.4 s)
  71 | -VO_S = (6.0, 22.0)                 # the VO's seconds (intro + bridges), the slack that lands the runtime
  72 | +RUNTIME_S = E.RUNTIME_S            # L-o: 60-70 s, the packaging target the factory's estimate must meet (ruling 12)
  73 | +VO_S = (6.0, 22.0)                 # the PBX MAX v3 VO's seconds (intro + bridges), content_range()'s slack
  74 |  R4_WPS, R4_PREROLL_S, R4_SHARE = 2.5, 1.0, 0.25      # edl_rules.rule_r4's own estimate (the factory's rule)
  75 |  TIME_SENSITIVE_H = 24.0            # L-v 3: 'today' / 'just' / a price level only from a source this fresh
  76 |  PRESCREEN_N = 24                   # moments whose own context is screened (step A) before any writing
  77 | @@ -113,8 +125,8 @@ def runtime(segs, vo_lines):
  78 |      """The FACTORY's own estimate, the one its hard 60-70 s check reads (edl_rules._r4_moments, main a5ec0f17: "hook +
  79 |      clips + VO + FINAL_TAIL_S", each VO line "words / 2.5 + the 1.0 s pre-roll"): segments' word spans + every VO line
  80 |      (intro, bridges) at R4_WPS w/s + R4_PREROLL_S each + FINAL_TAIL_S (the sign-off is inside it). It replaced (07:42)
  81 | -    this module's own estimate (2.6 w/s, no pre-roll, FIXED_S + the sign-off), which ran 3-4 s lower than the factory's
  82 | -    on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  83 | +    this module's own estimate (2.6 w/s, no pre-roll, a fixed tail + the sign-off), which ran 3-4 s lower than the
  84 | +    factory's on three VO lines. Neither is a measurement: the render measures the final (design section 8, open)."""
  85 |      vo = sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in vo_lines if t and t.strip())
  86 |      return round(sum(m["duration_s"] for m in segs) + vo + FINAL_TAIL_S, 2)
  87 |  
  88 | @@ -126,6 +138,41 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
  89 |                                     # clip; 60-70 s stays hard
  90 |  
  91 |  
  92 | +LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
  93 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
  94 | +LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
  95 | +                                   # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
  96 | +LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
  97 | +LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
  98 | +                                   # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
  99 | +LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
 100 | +
 101 | +
 102 | +def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 103 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 104 | +    n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 105 | +    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 106 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 107 | +    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 108 | +    return round(lo, 2), round(hi, 2)
 109 | +
 110 | +
 111 | +def takeaway_budget(content_s, other=()):
 112 | +    """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 113 | +    estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 114 | +    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 115 | +    other = [t for t in other if t and t.strip()]
 116 | +    fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 117 | +    words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 118 | +    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 119 | +              r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 120 | +    for a, b in (LY_AIM_S, RUNTIME_S):
 121 | +        lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 122 | +        if lo <= hi:
 123 | +            return lo, hi
 124 | +    return None
 125 | +
 126 | +
 127 |  def r4_max_vo_words(content_s, n_vo):
 128 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
 129 |      VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
 130 | @@ -179,13 +226,6 @@ def r4(pk):
 131 |                           "R4 (moments-first, 06:00) PASS") + f" | {note}"
 132 |  
 133 |  
 134 | -def budgets(content_s, n_bridges=1):
 135 | -    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
 136 | -    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
 137 | -    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
 138 | -    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
 139 | -
 140 | -
 141 |  def _name(m, ctx):
 142 |      return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
 143 |  
 144 | @@ -197,38 +237,23 @@ def signoff(segs, ctx):
 145 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 146 |  
 147 |  
 148 | -def plain_vo(segs, ctx):
 149 | -    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
 150 | -    last (orchestrator 03:40); the title names whole channels only (U11)."""
 151 | -    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
 152 | -    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
 153 | -    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
 154 | -    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
 155 | -    while len(title) > 70 and len(chans) > 1:
 156 | -        chans = chans[:-1]
 157 | -        title = "Bitcoin: " + ", ".join(chans) + " and others"
 158 | -    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
 159 | -    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}
 160 | +def labels(n):
 161 | +    """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 162 | +    return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 163 |  
 164 |  
 165 | -def assemble(order, by_id, fields, ctx, vo_kind):
 166 | -    segs = [by_id[i] for i in order]
 167 | -    lines = [dict(fields["intro"], slot="intro")] + \
 168 | -        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 169 | -        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 170 | -    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
 171 | +def _package(segs, ctx, fields, vo_kind, vo, lines):
 172 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"] not in ("title", "caption"))
 173 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 174 |            "vo_kind": vo_kind, "style": fields.get("style"),
 175 | -          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
 176 | +          "segments": [{"label": lb, "moment_id": m["moment_id"],
 177 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 178 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 179 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 180 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 181 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 182 | -                       for i, m in enumerate(segs)],
 183 | -          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 184 | -                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
 185 | -                 "signoff": signoff(segs, ctx)},
 186 | +                       for lb, m in zip(labels(len(segs)), segs)],
 187 | +          "vo": dict(vo, signoff=signoff(segs, ctx)),
 188 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
 189 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
 190 |            "lines": lines}
 191 | @@ -240,6 +265,46 @@ def assemble(order, by_id, fields, ctx, vo_kind):
 192 |      return pk
 193 |  
 194 |  
 195 | +def assemble(order, by_id, fields, ctx, vo_kind):
 196 | +    """The PBX MAX v3 shape (an intro after the hook and a line after clips; the orchestrator's given packages of the
 197 | +    night of Nov 11-12). L-y's medley is assemble_medley()."""
 198 | +    segs = [by_id[i] for i in order]
 199 | +    lines = [dict(fields["intro"], slot="intro")] + \
 200 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 201 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 202 | +    vo = {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 203 | +          "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1))}      # the renderer's after_clip
 204 | +    return _package(segs, ctx, fields, vo_kind, vo, lines)
 205 | +
 206 | +
 207 | +def assemble_medley(order, by_id, fields, ctx, vo_kind):
 208 | +    """L-y: the clips back to back, ONE takeaway after the last clip (slot "takeaway", the renderer's after_clip = the
 209 | +    last clip), and at most one bridge: after the hook it is the renderer's intro slot (slot "intro"), after clip k it is
 210 | +    a bridge after_clip k (slot "bridge_1"). fields: takeaway, bridge (None or {"text", "cites", "why"}), bridge_after
 211 | +    (None, 0 = after the hook, or k), title, caption."""
 212 | +    segs = [by_id[i] for i in order]
 213 | +    n_clips = len(segs) - 1
 214 | +    b, k = fields.get("bridge"), fields.get("bridge_after")
 215 | +    if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 216 | +        raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 217 | +    mid = b is not None and k > 0
 218 | +    lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 219 | +        ([dict(b, slot="bridge_1")] if mid else []) + \
 220 | +        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 221 | +         dict(fields["caption"], slot="caption")]
 222 | +    vo = {"intro": b["text"] if b is not None and k == 0 else None,
 223 | +          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 224 | +          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 225 | +    pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 226 | +    pk["shape"] = "medley"
 227 | +    pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 228 | +                                           "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
 229 | +                                           "text": b["text"], "why": b.get("why"),
 230 | +                                           "confirmed_by": fields.get("bridge_confirmed_by")}
 231 | +    pk["supply_exception"] = fields.get("supply_exception")
 232 | +    return pk
 233 | +
 234 | +
 235 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
 236 |  
 237 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
 238 | @@ -309,9 +374,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 239 |      return a_by, fails, vendors, families
 240 |  
 241 |  
 242 | -ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
 243 | -voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
 244 | -checks. The channels were not in one conversation and never answer each other.
 245 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
 246 | +play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
 247 | +clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
 248 | +conversation and never answer each other.
 249 |  
 250 |  {note}
 251 |  {clips}
 252 | @@ -320,52 +386,65 @@ Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repea
 253 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 254 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 255 |  it is today's.
 256 | -The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
 257 | -seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
 258 | -sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
 259 | -from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
 260 | -attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
 261 | +With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
 262 | +clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
 263 | +introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
 264 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
 265 | +each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
 266 | +survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
 267 | +"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
 268 | +words on what it adds and why it follows the clip before it (an internal note).
 269 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 270 |  "support": {{"id": "..."}}}}]}}"""
 271 |  
 272 | -STYLES = {
 273 | -    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
 274 | -            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
 275 | -            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
 276 | -            "clip, as your opinion, never as what the speaker said.",
 277 | -    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
 278 | -             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
 279 | -             "title."}
 280 | +MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
 281 | +Each clip is a person's own words from a show; the shows were not in one conversation.
 282 | +
 283 | +{clips}
 284 |  
 285 | -WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 286 | +1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
 287 | +   "none" if there is none.
 288 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
 289 | +3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
 290 | +   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
 291 | +   words.
 292 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
 293 | +
 294 | +WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 295 |  THE ANGLE (the point this video makes): "{angle}"
 296 | -The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
 297 | +The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
 298 | +in one conversation and never answer each other):
 299 |  
 300 |  {note}
 301 |  {lineup}
 302 |  
 303 | -The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
 304 | -(written by code).
 305 | -Write:
 306 | -- "intro": heard right AFTER the hook: your own take that sets up the angle.
 307 | -- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
 308 | -- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
 309 | -- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
 310 | +After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 311 | +{bridge}Write:
 312 | +- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 313 | +  opinion or conclusion), never a restatement of any clip.
 314 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 315 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 316 | -{style}
 317 |  RULES (a line that breaks one is rejected):
 318 | -- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
 319 | -- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
 320 | -  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
 321 | +- NEVER restate a clip's claim, and never repeat its words: the clip says it, in its own words.
 322 | +- Your OWN commentary must contain no number, price, date, named person or company, must not say or imply what any
 323 | +  speaker thinks, and must not relate speakers.
 324 |  - Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
 325 |    for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
 326 |    ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
 327 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 328 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 329 |    "slams", "exposes", "admits", "confirms", "caught".
 330 | -{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
 331 | +{extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 332 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 333 |  
 334 | +BRIDGE_ASK = """ONE JOIN NEEDS HELP: a blind viewer who watched these clips back to back could not follow the jump from
 335 | +{a} to {b} ("{why}"). Write ONE "bridge", heard between them: as short as it can be (at most {n} words); it only makes
 336 | +the next clip's subject or referent clear (its show and its topic, or a question); it never says what the next speaker
 337 | +thinks. Give "why": one sentence on why a viewer could not follow the jump without it. If you judge a viewer CAN
 338 | +follow this jump without narration, give "bridge": null (these clips then do not sit together, and other clips are
 339 | +picked).
 340 | +"""
 341 | +
 342 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
 343 |  different person's own words).
 344 |  
 345 | @@ -419,36 +498,43 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 346 |      return out
 347 |  
 348 |  
 349 | -def lineup_for(angle, by_id, dropped=frozenset()):
 350 | -    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
 351 | -    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
 352 | -    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
 353 | -    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
 354 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
 355 | +    """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 356 | +    medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 357 | +    angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 358 | +    predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), and the clips' seconds inside crange
 359 | +    (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
 360 | +    earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
 361 | +    seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
 362 | +    ONE channel may give two clips, from two different videos. None if impossible."""
 363 | +    lo, hi = crange or medley_content_range()
 364 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 365 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 366 |      hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 367 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 368 |      for h in hooks:
 369 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 370 | -                and m["channel_id"] != h["channel_id"]]
 371 | +                and (repeat_ok or m["channel_id"] != h["channel_id"])]
 372 |          best = None
 373 | -        for n in (3, 2):
 374 | -            lo, hi = content_range(n)
 375 | +        for n in range(clips[0], clips[1] + 1):
 376 |              for combo in itertools.combinations(pool, n):
 377 | -                if len({m["channel_id"] for m in combo}) != n:
 378 | +                chans = [m["channel_id"] for m in (h, *combo)]
 379 | +                if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
 380 | +                                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
 381 |                      continue
 382 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
 383 |                      continue
 384 | -                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
 385 | +                order = sorted(combo, key=lambda m: pos[m["moment_id"]])
 386 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
 387 |                      continue
 388 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
 389 |                  if not lo <= dur <= hi:
 390 |                      continue
 391 | -                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
 392 | +                key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
 393 |                  if best is None or key > best[0]:
 394 |                      best = (key, [h] + order)
 395 | -            if best:
 396 | -                return best[1]
 397 | +        if best:
 398 | +            return best[1]
 399 |      return None
 400 |  
 401 |  
 402 | @@ -489,9 +575,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 403 |          r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
 404 |                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 405 |          v = json.loads(r.text.strip())
 406 | -        labels = [sg["label"] for sg in pk["segments"]]
 407 | +        labs = [sg["label"] for sg in pk["segments"]]
 408 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 409 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
 410 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 411 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 412 |              raise ValueError("coherence verdict out of contract")
 413 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 414 | @@ -515,39 +601,136 @@ def _lineup_block(segs, ctx, a_by):
 415 |      return "\n".join(out)
 416 |  
 417 |  
 418 | -def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
 419 | +def joins(labs):
 420 | +    """The joins of a medley in play order: "<label> -> <next label>"; join k follows segment k (k = 0 is the hook)."""
 421 | +    return [f"{a} -> {b}" for a, b in zip(labs, labs[1:])]
 422 | +
 423 | +
 424 | +def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 425 | +    """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
 426 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
 427 | +    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
 428 | +    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
 429 | +    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
 430 | +    import providers as P
 431 | +    labs = labels(len(segs))
 432 | +    js = joins(labs)
 433 | +    clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 434 | +                      for lb, m in zip(labs, segs))
 435 | +    r = None
 436 | +    try:
 437 | +        r = router.call("coherence_verdict",
 438 | +                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
 439 | +                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 440 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 441 | +        v = json.loads(r.text.strip())
 442 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 443 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 444 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 445 | +                not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
 446 | +                any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 447 | +                    or not isinstance(x["why"], str) for x in v["joins"].values()):
 448 | +            raise ValueError("clips-alone verdict out of contract")
 449 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 450 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 451 | +            router.reject(r)
 452 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 453 | +    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 454 | +    flagged = [j for j in js if v["joins"][j]["followable"] is False]
 455 | +    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 456 | +        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 457 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 458 | +                    replayed=bool(getattr(r, "replayed", False)))
 459 | +
 460 | +
 461 | +def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 462 | +    """L-y: ONE takeaway (host commentary, class D), ONE title, ONE caption, and a bridge ONLY at `join` (k, why), the
 463 | +    one join the clips-alone verdict flagged (L-y 2): the writer gives it with its reason, or null when it judges a
 464 | +    viewer can follow the jump. The takeaway's word budget lands the factory's estimate (takeaway_budget()) with the
 465 | +    other VO lines' texts `other` (a bridge already written; when a bridge is asked for and none is written yet, one of
 466 | +    LY_BRIDGE_WORDS words). -> (reply, fields) with fields["bridge_after"] = k when a bridge is given."""
 467 |      from select_by_id import UNTRUSTED
 468 |      from story_semantics import quote_data
 469 |      content = sum(m["duration_s"] for m in segs)
 470 | -    nb = len(segs) - 2
 471 | -    iw, bw, (lo, hi) = budgets(content, nb)
 472 | -    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
 473 | +    if join is not None and not other:                # the bridge's seconds come off the takeaway (audit 2030 C1, glm):
 474 | +        other = [" ".join(["word"] * LY_BRIDGE_WORDS)]   # the most it may hold until it is written
 475 | +    budget = takeaway_budget(content, other) or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)
 476 | +    labs = labels(len(segs))
 477 | +    ask, shape = "", "null"
 478 | +    if join is not None:
 479 | +        k, why = join
 480 | +        ask = BRIDGE_ASK.format(a=labs[k].upper().replace("_", " "), b=labs[k + 1].upper().replace("_", " "),
 481 | +                                why=" ".join(quote_data(why, 300).replace('"', "'").split()), n=LY_BRIDGE_WORDS)
 482 | +        shape = '{"text": "...", "cites": ["id"], "why": "..."} or null'
 483 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 484 | -    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 485 | -                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
 486 | -                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
 487 | -                             extra=(extra + "\n") if extra else "")
 488 | +    prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 489 | +                             lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 490 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 491 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 492 |      try:
 493 |          obj = json.loads(r.text.strip())
 494 |          ids = [m["moment_id"] for m in segs]
 495 | -        keys = {"intro", "bridges", "title", "caption"}
 496 | +        keys = {"takeaway", "bridge", "title", "caption"}
 497 |          if not isinstance(obj, dict) or set(obj) != keys:
 498 |              raise ValueError(f"keys must be exactly {sorted(keys)}")
 499 | -        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
 500 | -            raise ValueError(f"'bridges' must hold {nb} lines")
 501 | -        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
 502 | -                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
 503 | -            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 504 | +        lines = [("takeaway", obj["takeaway"], {"text", "cites"}), ("title", obj["title"], {"text", "cites"}),
 505 | +                 ("caption", obj["caption"], {"text", "cites"})]
 506 | +        if obj["bridge"] is not None:
 507 | +            if join is None:
 508 | +                raise ValueError("no join needs a bridge: 'bridge' must be null (L-y 1)")
 509 | +            lines.append(("bridge", obj["bridge"], {"text", "cites", "why"}))
 510 | +        for slot, ln, want in lines:
 511 | +            if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
 512 |                      not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 513 | -                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
 514 | -                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
 515 | +                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
 516 | +                    ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
 517 | +                raise ValueError(f"{slot}: needs text and cites from the line-up's ids" +
 518 | +                                 (" and a reason" if "why" in want else ""))
 519 |          if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
 520 |              raise ValueError("title <= 70 characters, caption <= 220")
 521 |      except (ValueError, TypeError):
 522 |          router.reject(r)
 523 |          raise
 524 | -    return r, dict(obj, type="moments", angle=angle["angle"], style=style)
 525 | +    return r, dict(obj, bridge_after=join[0] if join is not None and obj["bridge"] is not None else None,
 526 | +                   type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
 527 | +
 528 | +
 529 | +def ly_shape(pk):
 530 | +    """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
 531 | +    last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
 532 | +    with its reason recorded, and every flagged join bridged (else these clips do not sit together); a bridge within
 533 | +    config.BRIDGE_WORD_CAP words; one clip per channel unless pk["supply_exception"] says why not (L-y 4)."""
 534 | +    from config import BRIDGE_WORD_CAP
 535 | +    segs, vo = pk["segments"], pk["vo"]
 536 | +    n_clips = len(segs) - 1
 537 | +    fails = []
 538 | +    if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 539 | +        fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 540 | +    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 541 | +    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 542 | +        fails.append("no takeaway after the last clip (L-y 1)")
 543 | +    js = joins([sg["label"] for sg in segs])
 544 | +    bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
 545 | +    texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]
 546 | +    if len(bridged) != len(texts):
 547 | +        fails.append(f"a line after clips {after[:-1]} that is not at a join between two clips")
 548 | +    if len(texts) > LY_MAX_BRIDGES:
 549 | +        fails.append(f"{len(texts)} bridges (L-y 2: at most {LY_MAX_BRIDGES})")
 550 | +    med = pk.get("medley") or {}
 551 | +    if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 552 | +        fails.append("the clips-alone verdict was not measured (L-y 3)")
 553 | +    elif sorted(bridged) != sorted(med["flagged"]):
 554 | +        fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 555 | +                     f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 556 | +    if texts and not ((pk.get("bridge") or {}).get("why") or "").strip():
 557 | +        fails.append("the bridge's reason is not recorded (L-y 2)")
 558 | +    for t in texts:
 559 | +        if len(t.split()) > BRIDGE_WORD_CAP:
 560 | +            fails.append(f"bridge of {len(t.split())} words (max {BRIDGE_WORD_CAP})")
 561 | +    chans = [sg["channel_id"] for sg in segs]
 562 | +    if len(set(chans)) != len(chans) and not (pk.get("supply_exception") or "").strip():
 563 | +        fails.append("two clips from one channel without the supply exception recorded (L-y 4)")
 564 | +    return not fails, fails
 565 |  
 566 |  
 567 |  def fidelity_segments(pk, a_by):
 568 | @@ -563,7 +746,7 @@ def fidelity_segments(pk, a_by):
 569 |  
 570 |  def cheap_checks(pk, a_by, levels, now):
 571 |      """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
 572 | -    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
 573 | +    runtime, R4, and for a medley the L-y shape. -> (violations, det, dup, rt_ok, r4_res)."""
 574 |      segs_v = fidelity_segments(pk, a_by)
 575 |      lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 576 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 577 | @@ -571,10 +754,13 @@ def cheap_checks(pk, a_by, levels, now):
 578 |      dup = duplicates(pk)
 579 |      rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 580 |      r4_res = r4(pk)
 581 | +    what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
 582 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
 583 | -                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
 584 | +                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change {what} "
 585 |                                                        f"length"}]) + \
 586 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 587 | +    if pk.get("shape") == "medley":
 588 | +        v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 589 |      return v, det, dup, rt_ok, r4_res
 590 |  
 591 |  
 592 | @@ -654,16 +840,48 @@ def _writers(router):
 593 |  
 594 |  
 595 |  def _redo(violations):
 596 | -    return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
 597 | -            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 598 | +    """The writer's second try: exactly the failing lines, by the keys the writer returns ("bridge" for the one bridge,
 599 | +    whichever join it sits at)."""
 600 | +    key = {"intro": "bridge", "bridge_1": "bridge"}
 601 | +    return ("Your previous reply was REJECTED. Return the WHOLE JSON object again, every key; rewrite ONLY the lines "
 602 | +            "below and keep the others exactly as they were. The failing lines, with the reason:\n" +
 603 | +            "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 604 | +
 605 | +
 606 | +def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 607 | +    """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
 608 | +    the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
 609 | +    passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict.
 610 | +    context_framing: the context-integrity failures the VO's framing causes (VO_DEPENDENT; per clip, so not attributed
 611 | +    to one line: recorded beside `passed`, never folded into it)."""
 612 | +    line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
 613 | +    rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
 614 | +           "words": len((line.get("text") or "").split()),
 615 | +           "cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") == "takeaway"}),
 616 | +           "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
 617 | +           "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None,
 618 | +           "context_framing": None if cx is None else sorted({v["rule"] for v in cx.get("violations") or []
 619 | +                                                              if v.get("rule") in VO_DEPENDENT})}
 620 | +    if fid is not None:
 621 | +        ver = fid.get("verdict") or {}
 622 | +        if fid.get("measured") and isinstance(ver.get("violations"), list):
 623 | +            rec["verdict_fail"] = sorted({v["rule"] for v in ver["violations"] if v.get("slot") in ("takeaway", "-")})
 624 | +            rec["passed"] = not rec["cheap_fail"] and not rec["verdict_fail"]
 625 | +        else:
 626 | +            rec["verdict_fail"] = ["NOT MEASURED"]
 627 | +            rec["passed"] = False if rec["cheap_fail"] else None
 628 | +    return rec
 629 |  
 630 |  
 631 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 632 | -          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
 633 | -    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
 634 | -    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
 635 | -    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
 636 | -    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
 637 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 638 | +    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 639 | +    item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 640 | +    written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 641 | +    one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 642 | +    work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 643 | +    spend: a callable returning the ledger's USD (dollars per package).
 644 | +    -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 645 |      t0 = time.time()
 646 |      usd0 = spend() if spend else None
 647 |      ms, why = usable(moments, ctx, delivered, optout)
 648 | @@ -671,9 +889,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 649 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 650 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 651 |      levels = current_levels(sources.values(), ctx)
 652 | -    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 653 | +    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 654 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 655 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
 656 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 657 | +           "package": None}
 658 |      log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 659 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 660 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 661 | @@ -685,7 +904,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 662 |      from story_semantics import quote_data
 663 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
 664 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 665 | -    lo, hi = content_range(2)[0], content_range(3)[1]
 666 | +    lo, hi = medley_content_range()
 667 |      angles, angle_reply = None, None
 668 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 669 |          r = None
 670 | @@ -707,25 +926,56 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 671 |      exc, tru = {}, {}
 672 |      with ThreadPoolExecutor(max_workers=8) as pool:
 673 |          for ai, angle in enumerate(angles):
 674 | -            dropped, w_used = set(), 0
 675 | -            while w_used < writes and not out["packages"]:
 676 | -                segs = lineup_for(angle, cleared, frozenset(dropped))
 677 | -                rec = {"angle": ai + 1, "text": angle["angle"],
 678 | -                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
 679 | +            dropped, n_lineup = set(), 0
 680 | +            while n_lineup < lineups and not out["packages"]:
 681 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped)), None
 682 | +                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 683 | +                    segs = lineup_for(angle, cleared, frozenset(dropped), repeat_ok=True)
 684 | +                    if segs is not None:
 685 | +                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 686 | +                               if sum(m["channel_id"] == c for m in segs) > 1]
 687 | +                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 688 | +                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 689 | +                                     f" gives two clips, from two videos (L-y 4)")
 690 | +                rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 691 | +                       "supply_exception": exception, "attempts": []}
 692 |                  out["tried"].append(rec)
 693 |                  if segs is None:
 694 | -                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
 695 | +                    rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 696 |                      break
 697 | +                n_lineup += 1
 698 | +                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 699 | +                rec["medley"], rec["medley_ok"] = med, ok_m
 700 | +                log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 701 | +                    f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 702 | +                    f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 703 | +                labs = labels(len(segs))
 704 | +                if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 705 | +                    by_lab = dict(zip(labs, segs))
 706 | +                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 707 | +                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 708 | +                    if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 709 | +                        weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 710 | +                    if not med.get("measured") or not weak:
 711 | +                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 712 | +                        break
 713 | +                    dropped |= weak
 714 | +                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 715 | +                    continue
 716 | +                join = None
 717 | +                if med["flagged"]:
 718 | +                    k = joins(labs).index(med["flagged"][0])
 719 | +                    join = (k, med["joins"][med["flagged"][0]]["why"])
 720 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 721 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 722 | -                extra, relined = "", False
 723 | +                extra, relined, w_used, written = "", False, 0, ()
 724 |                  while w_used < writes:
 725 | -                    style = styles[min(w_used, len(styles) - 1)]
 726 |                      w_used += 1
 727 |                      try:
 728 | -                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
 729 | +                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 730 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup, other=written)
 731 |                      except Exception as e:
 732 | -                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 733 | +                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 734 |                          continue
 735 |                      writers_v.add(wr.vendor)
 736 |                      writers_f.add(wr.family)
 737 | @@ -740,25 +990,47 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 738 |                              dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 739 |                              relined = True
 740 |                              break
 741 | -                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
 742 | -                                  f"written ({style}), attempt {w_used}")
 743 | +                    if join is not None and fields["bridge"] is None:
 744 | +                        dropped.add(segs[join[0] + 1]["moment_id"])
 745 | +                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 746 | +                                      f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 747 | +                        relined = True
 748 | +                        break
 749 | +                    if fields["bridge"] is not None:
 750 | +                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 751 | +                                                         "backend": med.get("backend")}
 752 | +                    fields["supply_exception"] = exception
 753 | +                    pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 754 | +                                         f"medley (L-y), written, attempt {w_used}")
 755 | +                    pk["medley"] = med
 756 | +                    written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
 757 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 758 | -                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
 759 | +                    att = {"writer": wr.backend, "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 760 | +                           "takeaway_budget": fields.get("takeaway_budget"),
 761 |                             "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 762 |                      rec["attempts"].append(att)
 763 | -                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
 764 | +                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 765 | +                    out["takeaways"].append(take)
 766 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 767 | +                        f"words, {pk['runtime_s_estimate']} s): " +
 768 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 769 |                          + f" ({time.time() - t0:.0f} s)")
 770 |                      if cheap:
 771 |                          att["violations"] = cheap
 772 | -                        extra = _redo(cheap)
 773 | +                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 774 | +                        extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 775 | +                                                                     if b else " (no takeaway length lands it: shorten "
 776 | +                                                                                "the bridge)"))
 777 | +                                       if v["rule"] == "RUNTIME" else v for v in cheap])
 778 |                          continue
 779 |                      fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 780 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 781 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 782 |                      att["violations"] = fid["violations"] + cx["violations"]
 783 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 784 | -                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
 785 | -                        f"({time.time() - t0:.0f} s)")
 786 | +                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 787 | +                        f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 788 | +                        f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 789 |                      if not fid["ok"] or not cx["ok"]:
 790 |                          if fid["ok"] and not framing:
 791 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 792 | @@ -777,22 +1049,34 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 793 |                          rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
 794 |                          relined = True
 795 |                          break
 796 | -                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
 797 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
 798 |                      att["coherence"] = coh
 799 | -                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
 800 | -                        f"({time.time() - t0:.0f} s)")
 801 | +                    log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 802 | +                        f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 803 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 804 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 805 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 806 | -                                            ok_c, coh)
 807 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 808 |                      if not ok_c:
 809 | -                        rec["why"] = "coherence below 4 or no through-line: next angle"
 810 | -                        w_used = writes
 811 | +                        tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 812 | +                        if coh.get("measured") and type(coh.get("vo_point")) is int and \
 813 | +                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 814 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 815 | +                            extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 816 | +                                            f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 817 | +                                            f"being supported by the clips: land the point the clips make together"}])
 818 | +                            continue                          # the clips hold; only the takeaway's point is weak
 819 | +                        weak = {sg["moment_id"] for sg in pk["segments"][1:]
 820 | +                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 821 | +                        dropped |= weak
 822 | +                        relined = bool(weak)
 823 | +                        rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 824 | +                                      (f"dropped {sorted(weak)}, re-lined" if weak else "next angle"))
 825 |                          break
 826 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
 827 | +                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 828 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 829 |                                      "coherence": coh.get("backend")}
 830 | -                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
 831 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 832 |                      pk["seconds"] = round(time.time() - t0, 1)
 833 |                      pk["usd"] = round(spend() - usd0, 4) if spend else None
 834 |                      out["packages"].append(pk)
 835 | @@ -811,9 +1095,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 836 |      return out
 837 |  
 838 |  
 839 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 840 | -    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
 841 | -    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
 842 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 843 | +    """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 844 | +    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 845 | +    A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 846 | +    (shape=(ok, [why]) from ly_shape())."""
 847 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 848 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 849 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 850 | @@ -861,4 +1147,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 851 |                          measured=all("edges" in t for t in truth.values())),
 852 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 853 |                            **votes_of(coh)),
 854 | +        **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 855 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
 856 | +           if medley is not None else {}),
 857 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 858 | +           if shape is not None else {}),
 859 |      }
 860 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 861 | index 3194dcc1..b1da529b 100644
 862 | --- a/pipeline/package_pin.py
 863 | +++ b/pipeline/package_pin.py
 864 | @@ -25,6 +25,13 @@ from datetime import datetime, timezone
 865 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 866 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 867 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 868 | +MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 869 | +
 870 | +
 871 | +def required_gates(pk):
 872 | +    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 873 | +    clips-alone verdict and the L-y shape."""
 874 | +    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 875 |  
 876 |  
 877 |  class PinRefused(Exception):
 878 | @@ -44,12 +51,12 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 879 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 880 |  
 881 |  
 882 | -def gate_problems(gates):
 883 | +def gate_problems(gates, required=REQUIRED_GATES):
 884 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 885 |      if not isinstance(gates, dict):
 886 |          return ["no gate inventory"]
 887 |      out = []
 888 | -    for g in REQUIRED_GATES:
 889 | +    for g in required:
 890 |          row = gates.get(g)
 891 |          if not isinstance(row, dict) or row.get("status") != "PASS":
 892 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
 893 | @@ -58,6 +65,17 @@ def gate_problems(gates):
 894 |      return out
 895 |  
 896 |  
 897 | +def bridge_slots(pk):
 898 | +    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
 899 | +    is the "takeaway" and the one bridge before it is bridge_1."""
 900 | +    vo = pk.get("vo") or {}
 901 | +    after = list(vo.get("bridges_after_clip") or [])
 902 | +    last = len(pk.get("segments") or []) - 1
 903 | +    if pk.get("shape") == "medley":
 904 | +        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
 905 | +    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]
 906 | +
 907 | +
 908 |  def line_problems(pk):
 909 |      """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
 910 |      by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
 911 | @@ -66,8 +84,9 @@ def line_problems(pk):
 912 |      if by.get("intro") != vo.get("intro"):
 913 |          out.append("intro")
 914 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 915 | -    if len(bridges) != len(after) or any(by.get(f"bridge_{i + 1}") != t for i, t in enumerate(bridges)) or \
 916 | -            any(k.startswith("bridge_") and int(k.split("_")[1]) > len(bridges) for k in by if k):
 917 | +    slots = bridge_slots(pk)
 918 | +    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
 919 | +            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
 920 |          out.append("bridges")
 921 |      for k in ("title", "caption"):
 922 |          if by.get(k) != pk.get(k):
 923 | @@ -76,8 +95,8 @@ def line_problems(pk):
 924 |  
 925 |  
 926 |  def to_pin(pk, run_name):
 927 | -    problems = gate_problems(pk.get("gates")) + [f"{x}: the gated line differs from the one shipped"
 928 | -                                                 for x in line_problems(pk)]
 929 | +    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
 930 | +                                                                     for x in line_problems(pk)]
 931 |      if problems:
 932 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
 933 |      segs = []
 934 | @@ -100,8 +119,13 @@ def to_pin(pk, run_name):
 935 |                                  "signoff_expected": pk["vo"]["signoff"],
 936 |                                  "title": pk["title"], "caption": pk["caption"],
 937 |                                  "hook_first_words": pk["hook_first_words"],
 938 | -                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
 939 | -                                                                   for i in range(len(pk["vo"]["bridges"]))}},
 940 | +                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
 941 | +                                               if pk["vo"]["intro"] else {}),
 942 | +                                            **{s: "takeaway" if s == "takeaway" else "connection"
 943 | +                                               for s in bridge_slots(pk)}},
 944 | +                                "shape": pk.get("shape"),
 945 | +                                "bridge": pk.get("bridge"),
 946 | +                                "supply_exception": pk.get("supply_exception"),
 947 |                                  "gates": pk["gates"],
 948 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 949 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
 950 | diff --git a/pipeline/providers.py b/pipeline/providers.py
 951 | index 67dfd391..b0c948d5 100644
 952 | --- a/pipeline/providers.py
 953 | +++ b/pipeline/providers.py
 954 | @@ -221,6 +221,16 @@ class OpenAIBackend(Backend):
 955 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 956 |  
 957 |  
 958 | +def _num(x):
 959 | +    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and x >= 0
 960 | +
 961 | +
 962 | +def _reported(usd):
 963 | +    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
 964 | +    the price-table estimate for it, labelled as an estimate)."""
 965 | +    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}
 966 | +
 967 | +
 968 |  class HeimdallBackend(OpenAIBackend):
 969 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
 970 |      words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
 971 | @@ -246,7 +256,8 @@ class HeimdallBackend(OpenAIBackend):
 972 |              text = j["choices"][0]["message"].get("content") or ""
 973 |          except (KeyError, IndexError, TypeError):
 974 |              raise RequestRejected("heimdall: no choices") from None
 975 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
 976 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
 977 | +                          **_reported(u.get("cost"))), time.time() - t0
 978 |  
 979 |      def credits(self):
 980 |          """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
 981 | @@ -285,8 +296,9 @@ class XAIBackend(Backend):
 982 |              text = j["choices"][0]["message"].get("content") or ""
 983 |          except (KeyError, IndexError, TypeError):
 984 |              raise RequestRejected("xai: no choices") from None
 985 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
 986 | -            time.time() - t0
 987 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
 988 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning},
 989 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
 990 |  
 991 |  
 992 |  class AnthropicBackend(Backend):
 993 | @@ -575,6 +587,13 @@ class Router:
 994 |                  r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
 995 |                  r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
 996 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
 997 | +                if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
 998 | +                    rep = float(usage["usd_reported"])
 999 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
1000 | +                             reported_calls=b.get("reported_calls", 0) + 1)
1001 | +                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
1002 | +                else:                                  # no vendor figure: the estimate stands for this call
1003 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
1004 |              self._save(d)
1005 |  
1006 |      def reject(self, reply, why=""):
1007 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
1008 | index 4535455d..7a41a3a3 100644
1009 | --- a/tests/moments/test_moments.py
1010 | +++ b/tests/moments/test_moments.py
1011 | @@ -129,13 +129,6 @@ class TestPackageUsable(unittest.TestCase):
1012 |          self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
1013 |                                                  "Go follow them for more. Links are below.")
1014 |  
1015 | -    def test_the_plain_title_never_cuts_a_name(self):
1016 | -        ctx = E.Context(NOW, REG)
1017 | -        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
1018 | -                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
1019 | -        title = PK.plain_vo(segs, ctx)[2]["text"]
1020 | -        self.assertLessEqual(len(title), 70)
1021 | -        self.assertTrue(title.endswith(("and others", "Two", "One")), title)
1022 |  
1023 |  
1024 |  if __name__ == "__main__":
1025 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
1026 | new file mode 100644
1027 | index 00000000..3ca40b5a
1028 | --- /dev/null
1029 | +++ b/tests/package/proof_ly.py
1030 | @@ -0,0 +1,211 @@
1031 | +#!/usr/bin/env python3
1032 | +"""ORCHESTRATOR ORDER 20:30 ET Nov 12 (law L-y, VOICEOVER IS MINIMAL): re-run tonight's universe and the saved ones
1033 | +through the packager's new default, the MEDLEY (pipeline/package.py build()). The table goes to the top of STATE:
1034 | +- packages per universe;
1035 | +- how many needed zero bridges and how many needed one;
1036 | +- the gate pass rate on the single takeaway line;
1037 | +- time and dollars per package.
1038 | +The top package of the newest universe becomes a sealed pin (MOMENTS_PIN_LY.json).
1039 | +
1040 | +LEGS (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"). The probe at
1041 | +20:32 ET found Anthropic "credit balance is too low" (HTTP 400) and OpenAI 429 credit_balance_exhausted, so both stay
1042 | +out. Local gemma runs on GPU0, which this builder never uses (L-r, the session's standing order), so every local leg
1043 | +is out too. What is left:
1044 | +- the writer (angle + takeaway) is Heimdall: deepseek-v4.1-flash, then qwen3.8-27b. This is the config's own
1045 | +  angle_write order once the frozen vendors drop out.
1046 | +- every verdict avoids the writer's vendor (L-x), so it runs on xAI grok-4.20.
1047 | +- the second recogniser is ElevenLabs scribe_v1.
1048 | +CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
1049 | +
1050 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
1051 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
1052 | +estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
1053 | +
1054 | +Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
1055 | +"""
1056 | +import argparse
1057 | +import hashlib
1058 | +import json
1059 | +import os
1060 | +import subprocess
1061 | +import sys
1062 | +import time
1063 | +
1064 | +HERE = os.path.dirname(os.path.abspath(__file__))
1065 | +REPO = os.path.dirname(os.path.dirname(HERE))
1066 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1067 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1068 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1069 | +import moments as M  # noqa: E402
1070 | +import package as PK  # noqa: E402
1071 | +import package_pin  # noqa: E402
1072 | +import proof_moments as PM  # noqa: E402
1073 | +import providers as P  # noqa: E402
1074 | +
1075 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
1076 | +OUT = os.path.join(HERE, "proof")
1077 | +SPEND = os.path.join(OUT, "SPEND_LY.json")
1078 | +LY_LIMIT_USD = 40.0                # the price-table estimate (an upper bound): xAI's own figure ran 1/8 of it on
1079 | +                                   # this order's first calls (estimate $0.636 vs reported $0.078 for 3 grok calls),
1080 | +                                   # so about $5 real; each paid call also RESERVES its upper bound (~$0.26-0.96)
1081 | +                                   # while in flight, and three workers run concurrently
1082 | +TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
1083 | +RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
1084 | +        "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
1085 | +        "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
1086 | +NEWEST = RUNS[0]
1087 | +FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
1088 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
1089 | +SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
1090 | +
1091 | +
1092 | +def chains():
1093 | +    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
1094 | +    cfg = json.load(open(P.CONFIG))
1095 | +    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
1096 | +    out["angle_write"] = list(WRITERS)
1097 | +    return out
1098 | +
1099 | +
1100 | +def ledger():
1101 | +    try:
1102 | +        d = json.load(open(SPEND))
1103 | +    except (OSError, ValueError):
1104 | +        d = {}
1105 | +    est = float(d.get("usd_estimate", 0.0))
1106 | +    best = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
1107 | +    return est, best, d
1108 | +
1109 | +
1110 | +def code_sha():
1111 | +    """The code this run used: HEAD plus the working tree's diff of pipeline/ and this driver (the results name it)."""
1112 | +    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
1113 | +    diff = subprocess.run(["git", "-C", REPO, "diff", "HEAD", "--", "pipeline", "tests/package"], capture_output=True).stdout
1114 | +    return f"{head}+{hashlib.sha256(diff).hexdigest()[:12]}" if diff else head
1115 | +
1116 | +
1117 | +def run_one(run, router, work_dir, log):
1118 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
1119 | +    words, captions, ctx, saved = PM.universe_sources(run)
1120 | +    sources = {s.video_id: s for s in words}
1121 | +    e0, b0, _ = ledger()
1122 | +    t0 = time.time()
1123 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
1124 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a.json"), spend=lambda: ledger()[0])
1125 | +    e1, b1, _ = ledger()
1126 | +    res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
1127 | +               usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
1128 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
1129 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
1130 | +    if res["package"]:
1131 | +        pk = res["package"]
1132 | +        pk["usd_best_known"] = res["usd_best_known"]
1133 | +        path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name="MOMENTS_PIN_LY.json")
1134 | +        res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1135 | +                      "package_sha256": pin["moments_package"]["package_sha256"]}
1136 | +        log(f"{run}: PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best known)"
1137 | +            f" pin {path}")
1138 | +    else:
1139 | +        log(f"{run}: no package ({res.get('why_none')}); usable {res['usable']}, cleared "
1140 | +            f"{res['prescreen']['cleared']}")
1141 | +    json.dump(res, open(os.path.join(OUT, run, "package_ly.json"), "w"), indent=1, default=str)
1142 | +    return res
1143 | +
1144 | +
1145 | +def table():
1146 | +    rows = ["| universe | usable / cleared step A | line-ups judged on the clips alone (passed) | package | segments, "
1147 | +            "seconds of clips | bridges | takeaway writes: passed / judged (first write) | runtime estimate | time | "
1148 | +            "$ estimate / $ best known | why none |", "|---|---|---|---|---|---|---|---|---|---|---|"]
1149 | +    tot = {"universes": 0, "packages": 0, "zero": 0, "one": 0, "passed": 0, "judged": 0, "first_passed": 0,
1150 | +           "first_judged": 0, "s": [], "est": [], "best": [], "framing": 0, "flagged_lineups": 0, "lineups": 0}
1151 | +    for run in RUNS:
1152 | +        f = os.path.join(OUT, run, "package_ly.json")
1153 | +        if not os.path.exists(f):
1154 | +            rows.append(f"| {run} | not run | | | | | | | | | |")
1155 | +            continue
1156 | +        r = json.load(open(f))
1157 | +        tot["universes"] += 1
1158 | +        tried = [t for t in r.get("tried") or [] if t.get("medley") is not None]
1159 | +        med_ok = sum(1 for t in tried if t.get("medley_ok") is True)
1160 | +        tot["lineups"] += len(tried)
1161 | +        tot["flagged_lineups"] += sum(1 for t in tried if t.get("medley_ok") and t["medley"].get("flagged"))
1162 | +        takes = r.get("takeaways") or []
1163 | +        tot["framing"] += sum(1 for x in takes if x.get("context_framing"))
1164 | +        judged = [x for x in takes if x.get("passed") is not None]
1165 | +        firsts = [x for x in judged if x.get("write") == 1]
1166 | +        tot["passed"] += sum(1 for x in judged if x["passed"])
1167 | +        tot["judged"] += len(judged)
1168 | +        tot["first_passed"] += sum(1 for x in firsts if x["passed"])
1169 | +        tot["first_judged"] += len(firsts)
1170 | +        pk = r.get("package")
1171 | +        if pk:
1172 | +            nb = 0 if not pk.get("bridge") else 1
1173 | +            tot["packages"] += 1
1174 | +            tot["zero" if nb == 0 else "one"] += 1
1175 | +            tot["s"].append(r["seconds"])
1176 | +            tot["est"].append(r.get("usd_estimate") or 0.0)
1177 | +            tot["best"].append(r.get("usd_best_known") or 0.0)
1178 | +            segs = f"{len(pk['segments'])}, {sum(s['duration_s'] for s in pk['segments']):.1f} s"
1179 | +            bridge = "0" if nb == 0 else f"1 ({pk['bridge']['join']}: {pk['bridge']['why']})".replace("|", "/")
1180 | +            pkg, rt, why = f"YES: \"{pk['title']}\"".replace("|", "/"), f"{pk['runtime_s_estimate']} s", ""
1181 | +        else:
1182 | +            segs = bridge = rt = "-"
1183 | +            pkg = "no"
1184 | +            why = (r.get("why_none") or "; ".join(f"angle {t['angle']}: {t.get('why') or '-'}" for t in r.get("tried") or [])
1185 | +                   )[:240].replace("|", "/")
1186 | +        rows.append(f"| {run} | {r['usable']} / {r['prescreen']['cleared']} | {len(tried)} ({med_ok}) | {pkg} | {segs} | "
1187 | +                    f"{bridge} | {sum(1 for x in judged if x['passed'])} / {len(judged)} "
1188 | +                    f"({sum(1 for x in firsts if x['passed'])} / {len(firsts)}) | {rt} | {r['seconds']} s | "
1189 | +                    f"${r.get('usd_estimate')} / ${r.get('usd_best_known')} | {why} |")
1190 | +    n = tot["packages"]
1191 | +    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
1192 | +    _, _, d = ledger()
1193 | +    summary = (f"\n**Totals:**\n"
1194 | +               f"- {tot['universes']} universes run; {n} packages.\n"
1195 | +               f"- Bridges: {tot['zero']} packages needed none, {tot['one']} needed one.\n"
1196 | +               f"- The takeaway line passed its gates in {tot['passed']} of {tot['judged']} judged writes "
1197 | +               f"({tot['first_passed']} of {tot['first_judged']} on the first write); context-integrity failures "
1198 | +               f"caused by the VO's framing, recorded beside it: {tot['framing']} writes.\n"
1199 | +               f"- Line-ups judged on the clips alone: {tot['lineups']}; of those that passed, {tot['flagged_lineups']} "
1200 | +               f"had one join a viewer could not follow (the bridge offered).\n"
1201 | +               f"- Per package: {mean(tot['s']):.0f} s mean, ${mean(tot['est']):.2f} estimate, "
1202 | +               f"${mean(tot['best']):.2f} best known.\n"
1203 | +               f"- This order's ledger: ${d.get('usd_estimate', 0):.2f} estimate; vendor-reported "
1204 | +               f"${d.get('usd_reported', 0):.4f} + unreported calls' estimate ${d.get('usd_unreported_estimate', 0):.2f}.\n")
1205 | +    text = ("# pp-selectid: the L-y medley re-run (generated by tests/package/proof_ly.py --table)\n\n" +
1206 | +            "\n".join(rows) + "\n" + summary)
1207 | +    open(TABLE, "w").write(text)
1208 | +    return text
1209 | +
1210 | +
1211 | +def main(argv=None):
1212 | +    ap = argparse.ArgumentParser()
1213 | +    ap.add_argument("--runs", nargs="+", default=list(RUNS))
1214 | +    ap.add_argument("--table", action="store_true", help="only (re)write the table from the saved results")
1215 | +    ap.add_argument("--work-dir", default=os.path.join(SCRATCH, "lv2"))
1216 | +    a = ap.parse_args(argv)
1217 | +    if a.table:
1218 | +        print(table())
1219 | +        return 0
1220 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
1221 | +    os.makedirs(a.work_dir, exist_ok=True)
1222 | +    for run in a.runs:
1223 | +        os.makedirs(os.path.join(OUT, run), exist_ok=True)
1224 | +        logf = open(os.path.join(OUT, run, "package_ly.log"), "a")
1225 | +        say = lambda s: (print(f"[{run}] {s}", flush=True), logf.write(s + "\n"), logf.flush())
1226 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} L-y medley build, code {code_sha()}, chains {json.dumps(router.chains)}")
1227 | +        try:
1228 | +            run_one(run, router, a.work_dir, say)
1229 | +        except P.SpendLimit as e:
1230 | +            say(f"STOPPED: {e}")
1231 | +            break
1232 | +        finally:
1233 | +            logf.close()
1234 | +    if router.notices:
1235 | +        print("NOTICES:", router.notices)
1236 | +    print(table())
1237 | +    return 0
1238 | +
1239 | +
1240 | +if __name__ == "__main__":
1241 | +    sys.exit(main())
1242 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1243 | new file mode 100644
1244 | index 00000000..4277b1a1
1245 | --- /dev/null
1246 | +++ b/tests/package/test_medley.py
1247 | @@ -0,0 +1,486 @@
1248 | +#!/usr/bin/env python3
1249 | +"""L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12): the packager's MEDLEY, offline.
1250 | +
1251 | +- The arithmetic: the clips' seconds that let ONE takeaway land the factory's estimate in 60-70 s, and the takeaway's
1252 | +  word budget, which lands it there.
1253 | +- The line-up: the hook + 2-4 clips in the proposer's play order, one per channel (a repeat only as the recorded supply
1254 | +  exception).
1255 | +- The clips-ALONE verdict's contract.
1256 | +- The writer's contract: a bridge only at the flagged join.
1257 | +- ly_shape's must-fail cases.
1258 | +- The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
1259 | +"""
1260 | +import json
1261 | +import os
1262 | +import sys
1263 | +import unittest
1264 | +
1265 | +HERE = os.path.dirname(os.path.abspath(__file__))
1266 | +REPO = os.path.dirname(os.path.dirname(HERE))
1267 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1268 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1269 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1270 | +sys.path.insert(0, HERE)
1271 | +import eligibility as E  # noqa: E402
1272 | +import package as PK  # noqa: E402
1273 | +import package_pin  # noqa: E402
1274 | +from config import BRIDGE_WORD_CAP  # noqa: E402
1275 | +from test_eligibility import NOW, REG  # noqa: E402
1276 | +from test_gates import Canned  # noqa: E402
1277 | +from test_moments import pm  # noqa: E402
1278 | +
1279 | +W = lambda n: " ".join(["word"] * n)
1280 | +
1281 | +
1282 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
1283 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
1284 | +
1285 | +
1286 | +def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
1287 | +    js = PK.joins(labs)
1288 | +    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
1289 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
1290 | +                          if j in flagged else "same subject"} for j in js}}
1291 | +
1292 | +
1293 | +def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
1294 | +    """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
1295 | +    labs = PK.labels(n)
1296 | +    segs = [{"label": lb, "channel_id": (chans or "ABCDEFG")[i], "duration_s": 12.0, "text": f"Bitcoin {lb}."}
1297 | +            for i, lb in enumerate(labs)]
1298 | +    bridges, aft = (["B " + W(5)] if bridge else []) + [W(20)], ([after] if bridge else []) + [n - 1]
1299 | +    return {"shape": "medley", "segments": segs,
1300 | +            "vo": {"intro": intro, "bridges": bridges, "bridges_after_clip": aft, "signoff": "S"},
1301 | +            "medley": {"measured": measured, "flagged": list(flagged)},
1302 | +            "bridge": {"why": bridge} if bridge or intro else None, "supply_exception": supply}
1303 | +
1304 | +
1305 | +class TestMedleyArithmetic(unittest.TestCase):
1306 | +    def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1307 | +        lo, hi = PK.medley_content_range()
1308 | +        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1309 | +        seg = lambda c: [{"duration_s": c}]
1310 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1311 | +        self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1312 | +        lo1, hi1 = PK.medley_content_range(n_bridges=1)
1313 | +        self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1314 | +        self.assertAlmostEqual(hi - hi1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1315 | +
1316 | +    def test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps(self):
1317 | +        aimed = 0
1318 | +        for c10 in range(300, 560):
1319 | +            c = c10 / 10
1320 | +            b = PK.takeaway_budget(c)
1321 | +            if b is None:
1322 | +                self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1323 | +                continue
1324 | +            lo, hi = b
1325 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1326 | +            for w in (lo, hi):
1327 | +                est = PK.runtime([{"duration_s": c}], [W(w)])
1328 | +                self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1329 | +                p = {"segments": [{"duration_s": c, "channel": "A"}, {"duration_s": 0.0, "channel": "B"}],
1330 | +                     "vo": {"intro": None, "bridges": [W(w)], "bridges_after_clip": [1]}, "runtime_s_estimate": est}
1331 | +                self.assertTrue(PK.r4(p)[0], (c, w, PK.r4(p)[1]))
1332 | +            aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1333 | +        self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1334 | +        self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1335 | +        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1336 | +        self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1337 | +
1338 | +
1339 | +class TestMedleyLineup(unittest.TestCase):
1340 | +    def test_the_hook_and_clips_in_the_proposers_order_one_per_channel(self):
1341 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1342 | +                                          pm("z", "D", 12.0), pm("e", "A", 14.0))}
1343 | +        seg = PK.lineup_for(angle(["h", "y", "x", "z", "e"], "h"), by)
1344 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "y", "x"])        # the earliest that fit, in that order
1345 | +        self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1346 | +
1347 | +    def test_more_clips_when_two_do_not_fill_the_medley(self):
1348 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1349 | +        seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1350 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1351 | +        short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1352 | +        self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1353 | +
1354 | +    def test_a_channel_twice_only_as_the_supply_exception_and_from_two_videos(self):
1355 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0),
1356 | +                                          pm("e", "A", 13.0))}
1357 | +        a = angle(["h", "x", "y", "e"], "h")
1358 | +        self.assertIsNone(PK.lineup_for(a, by))                                    # one per channel cannot fill it
1359 | +        seg = PK.lineup_for(a, by, repeat_ok=True)
1360 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "e"])
1361 | +        same_video = dict(by, e=dict(by["e"], video_id=by["h"]["video_id"]))
1362 | +        self.assertIsNone(PK.lineup_for(a, same_video, repeat_ok=True))           # never two clips of one video
1363 | +
1364 | +
1365 | +class TestClipsAloneVerdict(unittest.TestCase):
1366 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1367 | +    LABS = ["hook", "clip_01", "clip_02"]
1368 | +
1369 | +    def run_it(self, reply):
1370 | +        r = Canned(coherence_verdict=[reply])
1371 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1372 | +        return ok, v, r
1373 | +
1374 | +    def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
1375 | +        r = Canned(coherence_verdict=[verdict(self.LABS)])
1376 | +        prompts = []
1377 | +        call = r.call
1378 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1379 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1380 | +        self.assertTrue(ok)
1381 | +        self.assertEqual(v["flagged"], [])
1382 | +        self.assertNotIn("VOICE-OVER", prompts[0])
1383 | +        self.assertNotIn("TITLE", prompts[0])
1384 | +        self.assertIn('"hook -> clip_01"', prompts[0])
1385 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
1386 | +
1387 | +    def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
1388 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
1389 | +        self.assertTrue(ok)
1390 | +        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
1391 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
1392 | +        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
1393 | +
1394 | +    def test_no_through_line_or_a_weak_clip_fails(self):
1395 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
1396 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
1397 | +        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
1398 | +
1399 | +    def test_out_of_contract_is_not_measured_and_rejected(self):
1400 | +        good = verdict(self.LABS)
1401 | +        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
1402 | +                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
1403 | +                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
1404 | +                    dict(good, vo_point=5),
1405 | +                    dict(good, clips={"hook": 5, "clip_01": 5})):
1406 | +            ok, v, r = self.run_it(bad)
1407 | +            self.assertFalse(ok)
1408 | +            self.assertFalse(v["measured"])
1409 | +            self.assertIsNone(v["flagged"])
1410 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1411 | +
1412 | +
1413 | +class TestWriteTakeaway(unittest.TestCase):
1414 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1415 | +
1416 | +    def write(self, reply, join=None):
1417 | +        r = Canned(angle_write=[reply])
1418 | +        return PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {}, join), r
1419 | +
1420 | +    def lines(self, bridge=None):
1421 | +        return {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": bridge,
1422 | +                "title": {"text": "No ruler.", "cites": ["h"]}, "caption": {"text": "three clips", "cites": []}}
1423 | +
1424 | +    def test_no_bridge_unless_a_join_was_flagged(self):
1425 | +        (rep, f), _ = self.write(self.lines())
1426 | +        self.assertIsNone(f["bridge_after"])
1427 | +        with self.assertRaises(ValueError):
1428 | +            self.write(self.lines({"text": "Next, B.", "cites": ["x"], "why": "w"}))
1429 | +
1430 | +    def test_a_bridge_at_the_flagged_join_needs_its_reason_and_may_be_declined(self):
1431 | +        (rep, f), _ = self.write(self.lines({"text": "Next, B's show on keys.", "cites": ["x"], "why": "no referent"}),
1432 | +                                 join=(1, "the next speaker's 'it' has no referent"))
1433 | +        self.assertEqual(f["bridge_after"], 1)
1434 | +        (rep, f), _ = self.write(self.lines(None), join=(1, "w"))
1435 | +        self.assertIsNone(f["bridge_after"])                                       # declined: build re-lines
1436 | +        for bad in ({"text": "Next.", "cites": ["x"]}, {"text": "Next.", "cites": ["x"], "why": " "},
1437 | +                    {"text": "Next.", "cites": ["zz"], "why": "w"}):
1438 | +            with self.assertRaises(ValueError):
1439 | +                self.write(self.lines(bad), join=(1, "w"))
1440 | +
1441 | +    def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1442 | +        r = Canned(angle_write=[self.lines()])
1443 | +        prompts = []
1444 | +        call = r.call
1445 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1446 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1447 | +        lo, hi = PK.takeaway_budget(39.0)
1448 | +        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1449 | +        self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1450 | +        self.assertNotIn('"intro"', prompts[0])
1451 | +
1452 | +
1453 | +class TestLyShape(unittest.TestCase):
1454 | +    def test_a_clean_medley_passes(self):
1455 | +        self.assertEqual(PK.ly_shape(medley_pk()), (True, []))
1456 | +        self.assertTrue(PK.ly_shape(medley_pk(n=5))[0])
1457 | +
1458 | +    def test_a_bridge_only_and_always_at_the_flagged_join_with_its_reason(self):
1459 | +        self.assertTrue(PK.ly_shape(medley_pk(n=4, bridge="no referent", after=2, flagged=["clip_02 -> clip_03"]))[0])
1460 | +        self.assertTrue(PK.ly_shape(medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1461 | +            "bridge": {"why": "no referent"}})[0])
1462 | +        must_fail = {
1463 | +            "bridge at an unflagged join": medley_pk(n=4, bridge="w", after=1, flagged=["clip_02 -> clip_03"]),
1464 | +            "bridge with nothing flagged": medley_pk(n=4, bridge="w", after=1),
1465 | +            "flagged join left unbridged": medley_pk(flagged=["clip_01 -> clip_02"]),
1466 | +            "bridge without its reason": medley_pk(n=4, bridge="", after=2, flagged=["clip_02 -> clip_03"]) | {
1467 | +                "vo": medley_pk(n=4, bridge="w", after=2)["vo"]},
1468 | +            "an intro with nothing flagged": medley_pk(intro="Here's the thing.") | {"bridge": {"why": "w"}},
1469 | +            "two bridges": medley_pk(n=4, intro="Next.", bridge="w", after=2,
1470 | +                                     flagged=["hook -> clip_01", "clip_02 -> clip_03"]),
1471 | +            "verdict not measured": medley_pk(measured=False),
1472 | +            "verdict missing": medley_pk() | {"medley": None},
1473 | +        }
1474 | +        for why, pk in must_fail.items():
1475 | +            self.assertFalse(PK.ly_shape(pk)[0], why)
1476 | +
1477 | +    def test_the_takeaway_is_the_line_after_the_last_clip(self):
1478 | +        pk = medley_pk()
1479 | +        pk["vo"] = dict(pk["vo"], bridges_after_clip=[1])
1480 | +        self.assertFalse(PK.ly_shape(pk)[0])
1481 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1482 | +        self.assertFalse(PK.ly_shape(pk)[0])
1483 | +
1484 | +    def test_three_to_five_segments_and_one_clip_per_channel(self):
1485 | +        self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1486 | +        self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1487 | +        self.assertFalse(PK.ly_shape(medley_pk(chans="ABA"))[0])
1488 | +        self.assertTrue(PK.ly_shape(medley_pk(chans="ABA", supply="A gives two clips (L-y 4)"))[0])
1489 | +
1490 | +    def test_a_bridge_over_the_word_cap_fails(self):
1491 | +        pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
1492 | +        pk["vo"]["bridges"][0] = W(BRIDGE_WORD_CAP + 1)
1493 | +        self.assertFalse(PK.ly_shape(pk)[0])
1494 | +
1495 | +
1496 | +def ctx():
1497 | +    return E.Context(NOW, REG)
1498 | +
1499 | +
1500 | +class TestMedleyPackageAndPin(unittest.TestCase):
1501 | +    def build(self, bridge=None, k=None, n=3, text="No ruler, just rules nobody gets to bend."):
1502 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1503 | +                                          pm("z", "D", 9.0))}
1504 | +        order = ["h", "x", "y", "z"][:n]
1505 | +        fields = {"takeaway": {"text": text, "cites": []}, "bridge": bridge, "bridge_after": k,
1506 | +                  "title": {"text": "No ruler.", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1507 | +        return PK.assemble_medley(order, by, fields, ctx(), "medley (L-y)")
1508 | +
1509 | +    def gates(self, pk, **over):
1510 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
1511 | +        g.update(over)
1512 | +        return g
1513 | +
1514 | +    def test_no_intro_and_one_takeaway_after_the_last_clip(self):
1515 | +        pk = self.build()
1516 | +        self.assertIsNone(pk["vo"]["intro"])
1517 | +        self.assertEqual((pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]),
1518 | +                         (["No ruler, just rules nobody gets to bend."], [2]))
1519 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["takeaway", "title", "caption"])
1520 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1521 | +        self.assertEqual(PK.r4(pk)[0], True)
1522 | +
1523 | +    def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1524 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1525 | +        pk = self.build(bridge=b, k=1, n=4)
1526 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 3])
1527 | +        self.assertEqual([x["slot"] for x in pk["lines"]][:2], ["bridge_1", "takeaway"])
1528 | +        self.assertEqual(pk["bridge"]["join"], "clip_01 -> clip_02")
1529 | +        pk0 = self.build(bridge=b, k=0)
1530 | +        self.assertEqual(pk0["vo"]["intro"], "Next, on keys.")
1531 | +        self.assertEqual(pk0["vo"]["bridges_after_clip"], [2])
1532 | +        with self.assertRaises(ValueError):
1533 | +            self.build(bridge=b, k=2)                     # after the last clip is the takeaway's place
1534 | +
1535 | +    def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1536 | +        pk = self.build()
1537 | +        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1538 | +        pk["gates"] = self.gates(pk)
1539 | +        pin = package_pin.to_pin(pk, "test")
1540 | +        mp = pin["moments_package"]
1541 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1542 | +        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1543 | +        self.assertEqual(mp["shape"], "medley")
1544 | +        for missing in ("medley", "ly_shape"):
1545 | +            g = self.gates(pk)
1546 | +            g.pop(missing)
1547 | +            with self.assertRaises(package_pin.PinRefused):
1548 | +                package_pin.to_pin(dict(pk, gates=g), "test")
1549 | +        with self.assertRaises(package_pin.PinRefused):
1550 | +            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
1551 | +
1552 | +    def test_the_gated_takeaway_must_be_the_spoken_one(self):
1553 | +        pk = self.build()
1554 | +        pk["gates"] = self.gates(pk)
1555 | +        pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
1556 | +        with self.assertRaises(package_pin.PinRefused) as cm:
1557 | +            package_pin.to_pin(pk, "test")
1558 | +        self.assertIn("bridges", str(cm.exception))
1559 | +
1560 | +    def test_the_old_shape_keeps_its_slots(self):
1561 | +        pk = {"vo": {"intro": "I", "bridges": ["B", "T"], "bridges_after_clip": [1, 2]}, "segments": [{}, {}, {}]}
1562 | +        self.assertEqual(package_pin.bridge_slots(pk), ["bridge_1", "bridge_2"])
1563 | +        self.assertEqual(package_pin.bridge_slots(dict(pk, shape="medley")), ["bridge_1", "takeaway"])
1564 | +
1565 | +
1566 | +    def test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins(self):
1567 | +        pk = self.build(text=" ".join(["rules"] * (PK.MOMENTS_TAKEAWAY_WORD_CAP + 1)))
1568 | +        pk["medley"] = {"measured": True, "flagged": []}
1569 | +        cheap = PK.cheap_checks(pk, {}, [], NOW)[0]
1570 | +        self.assertTrue(any(v["rule"] == "R4" and "takeaway 1 31 words (max 30)" in v["detail"] for v in cheap), cheap)
1571 | +        b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
1572 | +        pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
1573 | +        pk0["gates"] = self.gates(pk0)
1574 | +        mp = package_pin.to_pin(pk0, "test")["moments_package"]
1575 | +        self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
1576 | +                                        "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
1577 | +        self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})
1578 | +
1579 | +
1580 | +class Rig:
1581 | +    """build() with every model and the network stubbed: the LOOP CONTROL under test (audit 2030 C1, glm P2-6).
1582 | +    medleys: the clips-alone verdicts in call order, each (ok, flagged, ratings, through_line); writes: the writer's
1583 | +    bridges in call order (None = no bridge / declined)."""
1584 | +
1585 | +    LINE = "Nobody gets to bend these rules, and that is exactly why they hold when it counts."
1586 | +    A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
1587 | +            "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
1588 | +
1589 | +    def __init__(self, moments, angle_moments, medleys, writes):
1590 | +        import providers as P
1591 | +        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
1592 | +        self.medley_calls, self.write_calls = [], []
1593 | +        self.router = Canned(angle_write=[{"angles": [angle(angle_moments, angle_moments[0])]}])
1594 | +        self.router.backends = {"xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}
1595 | +
1596 | +    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
1597 | +        self.medley_calls.append([m["moment_id"] for m in segs])
1598 | +        ok, flagged, ratings, line = self.medleys.pop(0)
1599 | +        labs = PK.labels(len(segs))
1600 | +        v = verdict(labs, flagged, ratings, line)
1601 | +        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False)
1602 | +
1603 | +    def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
1604 | +        self.write_calls.append(([m["moment_id"] for m in segs], join))
1605 | +        b = self.writes.pop(0)
1606 | +        fields = {"takeaway": {"text": self.LINE, "cites": []}, "bridge": b,
1607 | +                  "bridge_after": join[0] if join is not None and b is not None else None,
1608 | +                  "title": {"text": "Nobody bends the rules", "cites": []},
1609 | +                  "caption": {"text": "three voices, one point", "cites": []},
1610 | +                  "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
1611 | +        return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
1612 | +
1613 | +    def run(self):
1614 | +        fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
1615 | +               "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
1616 | +               "verdict": {"ok": True, "violations": [], "classes": {}}}
1617 | +        cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
1618 | +        stubs = {
1619 | +            "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
1620 | +            "prescreen": lambda router, ms, *a, **k: ({m["moment_id"]: dict(self.A_OK) for m in ms},
1621 | +                                                      {m["moment_id"]: [] for m in ms}, set(), set()),
1622 | +            "current_levels": lambda *a, **k: [],
1623 | +            "medley": self.medley, "write_takeaway": self.write,
1624 | +            "paid_gates": lambda *a, **k: (fid, cx),
1625 | +            "exclusion_for": lambda router, m, *a, **k: {"verdict": "keep", "measured": True, "replayed": False,
1626 | +                                                         "backend": "xai:grok"},
1627 | +            "truth_for": lambda router, m, *a, **k: {"ok": True, "edges": {"cuttable": True}, "replayed": False,
1628 | +                                                     "model": "scribe_v1"},
1629 | +            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
1630 | +                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
1631 | +                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
1632 | +                                                             "replayed": False}),
1633 | +        }
1634 | +        saved = {k: getattr(PK, k) for k in stubs}
1635 | +        try:
1636 | +            for k, v in stubs.items():
1637 | +                setattr(PK, k, v)
1638 | +            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent")
1639 | +        finally:
1640 | +            for k, v in saved.items():
1641 | +                setattr(PK, k, v)
1642 | +
1643 | +
1644 | +class TestBuildLoop(unittest.TestCase):
1645 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1646 | +
1647 | +    def test_nothing_is_written_for_clips_that_fail_alone(self):
1648 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], None, "none")], [])
1649 | +        out = rig.run()
1650 | +        self.assertIsNone(out["package"])
1651 | +        self.assertEqual(rig.write_calls, [])
1652 | +        self.assertIn("no through-line", out["tried"][0]["why"])
1653 | +
1654 | +    def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
1655 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
1656 | +                  [None])
1657 | +        out = rig.run()
1658 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
1659 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])           # written only after the clips pass
1660 | +        self.assertIsNotNone(out["package"])
1661 | +        self.assertIsNone(out["package"]["bridge"])
1662 | +
1663 | +    def test_a_declined_bridge_drops_the_clip_after_the_flagged_join(self):
1664 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
1665 | +                                                  (True, [], None, Rig.LINE)], [None, None])
1666 | +        out = rig.run()
1667 | +        self.assertEqual(rig.write_calls[0], (["h", "x", "y"], (1, "the next speaker's 'it' has no referent")))
1668 | +        self.assertIn("followable without a bridge", out["tried"][0]["why"])
1669 | +        self.assertEqual(rig.medley_calls[1], ["h", "x", "z"])                  # y, after the flagged join, dropped
1670 | +        pk = out["package"]
1671 | +        self.assertIsNone(pk["bridge"])
1672 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["ly_shape"]["status"]), ("PASS", "PASS"))
1673 | +
1674 | +    def test_a_given_bridge_sits_at_the_flagged_join_with_its_reason(self):
1675 | +        b = {"text": "Next, a show on keys.", "cites": ["y"], "why": "the next clip's 'it' has no referent"}
1676 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b])
1677 | +        pk = rig.run()["package"]
1678 | +        self.assertEqual((pk["bridge"]["join"], pk["bridge"]["why"]), ("clip_01 -> clip_02", b["why"]))
1679 | +        self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
1680 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
1681 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
1682 | +        package_pin.to_pin(pk, "test")                    # every required row exactly PASS: the pin is allowed
1683 | +
1684 | +    def test_the_supply_exception_is_recorded(self):
1685 | +        ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
1686 | +        rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
1687 | +        pk = rig.run()["package"]
1688 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "e"])
1689 | +        self.assertIn("gives two clips, from two videos (L-y 4)", pk["supply_exception"])
1690 | +        self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")
1691 | +
1692 | +
1693 | +class TestInventoryRows(unittest.TestCase):
1694 | +    def test_the_two_medley_rows(self):
1695 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
1696 | +               "backend": "x", "replayed": False, "measured": True}
1697 | +        coh = {"backend": "x", "replayed": False, "measured": True}
1698 | +        args = (fid, [], True, (True, ""), {"ok": True, "measured": True, "replayed": False, "backends": {}},
1699 | +                {"hook": {"backend": "x", "replayed": False}}, {"h": {"verdict": "keep", "measured": True,
1700 | +                                                                      "replayed": False}},
1701 | +                {"h": {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "s"}}, True, coh)
1702 | +        self.assertNotIn("medley", PK.inventory(*args))
1703 | +        g = PK.inventory(*args, medley=(True, {"backend": "x", "replayed": False, "measured": True, "flagged": []}),
1704 | +                         shape=(True, []))
1705 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("PASS", "PASS"))
1706 | +        g = PK.inventory(*args, medley=(False, {"measured": False, "flagged": None}), shape=(False, ["two bridges"]))
1707 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("NOT RUN", "FAIL"))
1708 | +        self.assertEqual(g["ly_shape"]["why"], ["two bridges"])
1709 | +
1710 | +
1711 | +class TestReportedCost(unittest.TestCase):
1712 | +    def test_the_ledger_keeps_the_vendors_own_figure_beside_the_estimate(self):
1713 | +        import tempfile
1714 | +        import providers as P
1715 | +        with tempfile.TemporaryDirectory() as d:
1716 | +            path = os.path.join(d, "SPEND.json")
1717 | +            r = P.Router(env_path=None, spend_path=path, limit_usd=10.0)
1718 | +            b = r.backends["xai:grok-4.20-0309-reasoning"]
1719 | +            r._settle(None, b, {"in": 1000, "out": 1000, "usd_reported": 0.002}, 0.03, "check")
1720 | +            r._settle(None, b, {"in": 1000, "out": 1000}, 0.03, "check")
1721 | +            led = json.load(open(path))
1722 | +            self.assertAlmostEqual(led["usd_estimate"], 0.06, places=6)
1723 | +            self.assertAlmostEqual(led["usd_reported"], 0.002, places=8)
1724 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.03, places=6)
1725 | +            self.assertEqual(led["by_backend"][b.name]["reported_calls"], 1)
1726 | +        self.assertEqual(P._reported(None), {})
1727 | +        self.assertEqual(P._reported(True), {})
1728 | +        self.assertEqual(P._reported(-1), {})
1729 | +        self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})
1730 | +
1731 | +
1732 | +if __name__ == "__main__":
1733 | +    unittest.main()
1734 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse, moments-first packaging), written 20:30-21:10 ET Nov 12
under the orchestrator's new law L-y. The code gates a video package before a pinned render. Standing laws: nothing
measured is never a pass (L-m); fail closed (L-j); never change what a check accepts in order to make something pass;
every model verdict avoids the vendor and model family of any reply whose text it judges (L-x).

LAW L-y VOICEOVER IS MINIMAL (the order, paraphrased exactly):
 1. DEFAULT SHAPE: hook clip -> clip -> clip (-> clip) back to back as a medley, joined by the approved transition, then
    ONE voiceover line at the END (the takeaway) and the sign-off naming every channel. No VO intro after the hook. No
    bridges between clips.
 2. A bridge between two clips is the EXCEPTION, used only when the packager judges, and the blind coherence check
    confirms, that a viewer could not follow the jump without it (the second clip's subject or referent is unclear
    coming from the first). At most ONE bridge per video, as short as it can be, and the package records why it was
    needed. If two or more bridges would be needed, the line-up is wrong: pick clips that sit together.
 3. SELECTION carries the weight: the packager chooses moments that follow from one another WITHOUT narration - each
    clip's opening must make sense after the previous clip's ending, in the speaker's own words. The coherence verdict
    is asked on the clips ALONE first ("played back to back with no narration, is there a through-line a viewer can
    state?"), and only then on the takeaway.
 4. Runtime: 3 to 5 clips, the measured final 58-72 s accepted, target 60-70 (the packaging estimate stays inside
    60-70). Per-clip duration targets stay targets. One clip per channel still holds unless the supply forces
    otherwise (then say so in the package).
 5. The takeaway is host commentary (class D): one or two sentences; it is still gated (VO fidelity, context
    integrity). The title and caption still carry the angle. The existing caps stay as upper bounds (takeaway 30 words,
    bridge 20 words, VO share <= 45 % of the runtime estimate).
 6. Keep every VO gate.

What changed, and what to check:
1. package.build(): the medley is the default. Per angle up to LY_LINEUPS line-ups; each line-up is judged on the
   clips ALONE first (package.medley) before anything is written; only a passing line-up gets writes
   (write_takeaway); the one bridge is offered to the writer ONLY at the join the clips-alone verdict flagged, and if
   the writer declines it, the line-up is dropped (re-lined); then the cheap gates (incl. ly_shape), the fidelity
   verdict and context integrity, exclusion and the second recognition pass, and last the coherence verdict WITH the
   takeaway. Check the loop control (dropped / relined / next angle), that nothing is written for a line-up whose
   clips alone fail, and that the takeaway's gate results are recorded honestly (_takeaway_record).
2. package.ly_shape(): the code check of L-y on the package. Can a package pass with: an intro when no hook join was
   flagged; a bridge at a join that was not flagged; a flagged join left unbridged; two bridges; no takeaway after the
   last clip; a bridge without its recorded reason; a bridge over 20 words; 2 or 6 segments; two clips of one channel
   without the recorded supply exception; an unmeasured clips-alone verdict?
3. package.medley(): the blind clips-alone verdict. Is its JSON contract strict (exact keys, every consecutive join,
   booleans)? Does the prompt carry NO voice-over and NO title? Is "flagged" right? ok = a stated through-line
   (>= 4 words, not 'none'), every clip >= 4, at most one unfollowable join.
4. package.write_takeaway(): a bridge must be null unless a join was offered; an offered bridge needs text, cites from
   the line-up and a non-empty reason. The takeaway's word budget (takeaway_budget) must land the factory's runtime
   estimate (package.runtime: clips' word spans + each VO line words / 2.5 + 1.0 s + the 14.30 s tail) in 60-70 s and
   respect the 30-word cap and R4's 45 % share. medley_content_range() gives the clips' seconds that allow that.
5. package.lineup_for(): the hook + 2-4 clips in the proposer's play order, one per channel; repeat_ok allows ONE
   channel twice, only from two different videos, and build() uses it only when no one-per-channel line-up exists,
   recording the supply exception.
6. package.assemble_medley() and package_pin.py: intro None (the deployed pinned.py accepts "intro null"); the takeaway
   is the line after the LAST clip (slot "takeaway"); a bridge after the hook is the renderer's intro slot, after clip
   k a bridge after_clip k; required_gates(pk) adds "medley" and "ly_shape" for a medley; line_problems maps the
   slots; the seal is unchanged in form.
7. pipeline/providers.py: the ledger now records the vendor's own cost per call (xAI cost_in_usd_ticks / 1e10,
   Heimdall usage.cost) beside the price-table estimate; the spend guard still reads the estimate. Any way this can
   corrupt the ledger or let spend pass the guard?
8. tests/package/proof_ly.py: the re-run driver. Chains: no local leg (the builder never uses the GPU), no Anthropic /
   OpenAI (out of credit); writer = Heimdall deepseek then qwen; verdicts avoid the writer's vendor, so xAI. Its own
   ledger and cap. The table: packages per universe, zero / one bridge, the takeaway pass rate, time and dollars.
9. Removed: write_v3, STYLES, budgets, plain_vo (intro + bridges shapes, contrary to L-y 1) and plain_vo's title test.
   Does anything still need them?
10. tests/package/test_medley.py: do the must-fail tests prove each rule above?

Output: findings ranked P0 / P1 / P2, each with file:line and a concrete failure scenario (inputs -> wrong result).
Only state what you can verify from the diff provided. If uncertain, say so; do not guess. End with a verdict line:
"SHIP: yes | yes with conditions | no".


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
