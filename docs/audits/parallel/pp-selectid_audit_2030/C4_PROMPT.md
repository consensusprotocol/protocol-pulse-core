# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-2030
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 364 s finish=stop usage in 48914 / out 12304 usd~0.331 (upper-bound price)

# Audit — pp-selectid, L-y medley (cycles 3–4, ROUND 2)

Scope: the diff as given (package.py, package_pin.py, providers.py, proof_ly.py, test_medley.py, pin_and_verify.py). Everything below is verified against the diff text only; where the diff references symbols I cannot see (e.g. `FINAL_TAIL_S`, `MOMENTS_TAKEAWAY_WORD_CAP`, `Canned`, `truth_for`, `config.BRIDGE_WORD_CAP`), I state the assumption.

---

## P0 findings

**P0-1. `assemble_medley` bridge-after-hook: `bridges_after_clip`/`lines` disagree with `ly_shape`'s join mapping — a legal package fails `ly_shape` (or, worse, the wrong join is recorded).**
`pipeline/package.py:219-225` (assemble_medley) vs `pipeline/package.py:554` (ly_shape).

In `assemble_medley`, when the bridge sits after the hook (`k == 0`), the bridge line is emitted with slot `"intro"` and `vo["intro"] = b["text"]`; `vo["bridges"]` then holds only `[takeaway]` and `vo["bridges_after_clip"] = [n_clips]`. In `ly_shape` (line 554):

```python
bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
```

For the after-hook case: `vo["intro"]` is truthy → `bridged = [js[0]]` = `["hook -> clip_01"]`; `after = [n_clips]`, so `after[:-1]` is empty → nothing more. `texts = [vo["intro"]] + bridges[:-1] = [b_text] + []` → length 1. So `bridged == texts` in count — that part is consistent. But now check the *flagged-join* comparison at line 563: `sorted(bridged) != sorted(med["flagged"])`. The flagged join recorded by `medley()` is `"hook -> clip_01"` — matches. So the after-hook case actually lines up. Where it breaks is the **mid-join case combined with the record check**: `rec = pk.get("bridge") or {}`; `rec["text"]` must equal `texts[0]`. For a mid-join bridge, `texts[0] = bridges[0]` = the bridge text — fine. For the after-hook case, `texts[0] = vo["intro"]` = the bridge text — also fine. So the record check passes. The real inconsistency: **`bridge_slots` in package_pin.py:988** — for a medley with a mid-join bridge, `after = [k, n_clips]`, so slots = `["bridge_1", "takeaway"]`; `line_problems` (line 1002) then requires `by["bridge_1"] == bridges[0]` and `by["takeaway"] == bridges[1]`. In `assemble_medley` the lines list for the mid-join case is `[bridge_1, takeaway, title, caption]` — consistent. For the after-hook case, `after = [n_clips]` → slots = `["takeaway"]`, and `line_problems` checks `by["takeaway"] == bridges[0]` — the takeaway. But `vo["intro"]` is set to the bridge text while `by["intro"]` is... **absent** (assemble_medley's lines list for k==0 emits the bridge with slot `"intro"` — wait, line 219: `dict(b, slot="intro")` — so `by["intro"]` IS present and equals the bridge text, and `line_problems` line 996 checks `by.get("intro") != vo.get("intro")` → equal → OK). After tracing all three paths, the slot/record/flagged-join bookkeeping is internally consistent. **Downgrade: this is not a P0.** What remains genuinely fragile: `ly_shape` line 554's guard `type(a) is int and 0 < a < n_clips` silently *drops* an `after` entry that is 0 or ≥ n_clips instead of failing, while `assemble_medley` (line 216) raises on `k >= n_clips`. A package built by any other producer (e.g. the integrator's R11 path, or a hand-edited pin) with `bridges_after_clip = [0, n_clips]` and `intro` set would have `bridged = [js[0]] + []` (a=0 fails `0 < a`), `texts = [intro] + bridges[:-1]` = `[intro, takeaway]` if bridges = [intro_text, takeaway]... wait, for `after=[0, n_clips]`, `bridges` would be `[bridge_text, takeaway]`, `texts = [intro] + [bridge_text]` = 2 entries, `bridged = [js[0]]` = 1 entry → `len(bridged) != len(texts)` → fails with "a line after clips [0] that is not at a join between two clips" — but the package is actually well-formed (bridge after the hook, recorded as intro). Concrete failure: a *valid* medley with a bridge after the hook whose `bridges_after_clip` literally records `0` (which `assemble_medley`'s own `pk["bridge"]["after_clip"] = k` documents as "0 = after the hook", line 211) is rejected by `ly_shape` because `assemble_medley` never writes `0` into `bridges_after_clip` — it folds it into `intro`. Two producers, two conventions, one checker. **P1, not P0.** (I keep it here because the audit question 2 explicitly asks whether a legal package can fail; the answer is yes for the documented `after_clip: 0` convention.)

**P0-2. `write_takeaway`'s "any bridge of 3–12 words" budget (ROUND 2 item 11) does not actually guarantee the 60–70 s landing for all bridge lengths — the intersection can be empty and the code silently falls back to the 12-word budget, which can then fail RUNTIME.**
`pipeline/package.py:480-485`.

```python
if join is not None and not other:
    w = lambda n: [" ".join(["word"] * n)]
    short, long_ = takeaway_budget(content, w(LY_BRIDGE_MIN_WORDS)), takeaway_budget(content, w(LY_BRIDGE_W

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 110 s finish=stop usage in 48072 / out 1088 usd~0.268 (upper-bound price)

**P0: pipeline/package.py:226 (assemble_medley / _package)**
- `assemble_medley` (and `_package`) never writes `"runtime_s_estimate"` into the returned `pk` dict.
- `cheap_checks` (line 597) does `RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]` unconditionally; `ly_shape`, `r4`, logging, and `_takeaway_record` also read it.
- Concrete failure: `medley_pk()` (or any `assemble_medley` call with 39 s clips + 8-word takeaway) → `KeyError` in `cheap_checks` (or `rt_ok=False` / RUNTIME gate FAIL). The new test at `tests/package/test_medley.py:1692` asserts exactly this key with a specific numeric value; it cannot pass against the implementation shown. All medley packages are blocked before any gate inventory is written (violates L-j, LAW 20).

**P1: pipeline/package.py:484 (write_takeaway budget intersection) + 828 (redo message)**
- When a flagged join exists and no bridge has been written yet, `takeaway_budget(..., other=w(LY_BRIDGE_MIN_WORDS))` and `...w(LY_BRIDGE_WORDS)` are computed; their intersection is taken only if both succeed and `both[0] <= both[1]`, else `long_` is used.
- The redo text appended to a RUNTIME violation assumes a `(lo, hi)` pair exists (`if v["rule"] == "RUNTIME" ... (a takeaway of {b[0]}-{b[1]} words ...)`).
- Concrete failure: clip seconds that make the min-bridge budget return `None` while the max-bridge budget succeeds → `budget=None`, fallback to `(LY_TAKEAWAY_MIN_WORDS, CAP)`, then a later RUNTIME violation produces a malformed redo string containing the literal "None" (writer receives garbage extra prompt). Matches the "qwen P1, grok P2" comment but is not guarded; violates "never change what a check accepts to make a render pass" (LAW 20 / M2) and fail-closed (M12).

**P2: pipeline/package_pin.py:1002 (bridge_slots + line_problems) + pipeline/package.py:569 (ly_shape text match)**
- Both perform exact `!=` / `.strip() !=` on VO/bridge lines and `sorted(bridged) != sorted(med["flagged"])`.
- LAW L-k requires *every* text comparison to route through `canon.py` (entities, split tokens, spoken forms, numbers, signs). No `canon.same(...)` or `canon.canon_tokens` call is present.
- Concrete failure: writer returns bridge `"S&P"` while `vo["bridges"]` normalizes to `"S & P"` (or canonical apostrophe / comma variant per L-h/L-g); `line_problems` or `ly_shape` treats them as mismatch → `PinRefused` even though a listener hears identical words and the bytes sent to render are semantically identical. Blocks L-j authorisation on otherwise clean gates. (Exact string is appropriate for "these bytes" but the governing law is violated as written.)

**P2: tests/package/proof_ly.py:1293 (table) + 1302 (firsts)**
- `judged = [x for x in takes if x.get("passed") is not None]`; `firsts = [x for x in judged if x.get("write") == 1]`.
- `_takeaway_record` can leave `"passed": None` when cheap gates stop before the classifying verdict (explicitly documented).
- Concrete failure: a write stopped by LY_SHAPE or R4 before fidelity verdict runs → counted in `tot["judged"]` / `tot["first_judged"]` but its `None` is silently ignored in pass-rate math, under-counting "judged" relative to the gate inventory that actually ran. The table shipped to STATE therefore misreports the takeaway pass rate. (Minor but violates "honest" recording required by L-y 6 and the proof's own comment.)

No other violations of the listed governing laws (L-a through L-l, SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-c dissent-until-disproved on final bytes, L-j exact inventory, L-k canon where semantic, L-l strict JSON contracts, M12 fail-closed, LAW 22 v2f byte-identical) could be verified from the diff alone; early CUTTABLE/L-v 2 filtering, medley contract strictness, `ly_shape` must-fail cases, vendor-reported cost ledger, prompt changes for commentary tests, and loop control (clips-alone first, doomed moments, reline on declined bridge) all match the stated L-y rules and ROUND-2 amendments. The removed `plain_vo` / styles code is correctly dead after L-y.

**Verdict: SHIP: no** (P0 runtime key omission must be fixed before merge; it breaks every medley path and the new test suite).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 127 s finish=stop usage in 54420 / out 5099 usd~0.240 (upper-bound price)

# Code Audit: pp-selectid-2030 (L-y Medley)

## P0 Findings

### P0-1: `ly_shape` allows a bridge at an unflagged join when the verdict is unmeasured
**File:** `pipeline/package.py`, `ly_shape()` (lines ~560-565 in diff)

**Scenario:**
1. `medley()` fails (e.g., provider error), returning `{"measured": False, "flagged": None}`.
2. `build()` correctly refuses to write for this line-up (`if not ok_m: ... break`).
3. **However**, if a package is constructed via `assemble_medley()` with a bridge (e.g., from a retry path or manual construction) and `pk["medley"]` is `{"measured": False, "flagged": None}`:
   - `ly_shape` checks `med.get("measured") is not True` → adds failure `"the clips-alone verdict was not measured (L-y 3)"`.
   - **But** it does NOT check whether the bridge is at a flagged join when `flagged` is `None`. The `elif sorted(bridged) != sorted(med["flagged"])` branch is skipped because `measured` is not `True`.
   - Result: A package with a bridge at an arbitrary join passes the "bridge at flagged join" check (it's not evaluated) but fails on "not measured". This is correct behavior (fail closed), **BUT** the failure message is misleading: it says "not measured" when the real issue is also that the bridge placement is unverifiable. More critically, if `measured` is `True` but `flagged` is an empty list `[]`, and a bridge exists, `sorted(bridged) != sorted([])` correctly fails. **No actual P0 here** — the fail-closed behavior is correct.

**Revised:** This is not a P0. The fail-closed behavior is correct. Downgrading to P2 (misleading error message).

---

### P0-2: `takeaway_budget` can return a budget where the lower bound exceeds the upper bound after R4 cap
**File:** `pipeline/package.py`, `takeaway_budget()` (lines ~112-125 in diff)

**Scenario:**
1. `content_s = 50.0` (clips total 50s).
2. `FINAL_TAIL_S = 14.30`, `R4_WPS = 2.5`, `R4_PREROLL_S = 1.0`.
3. `fixed = 50.0 + 14.30 + 0 = 64.30`.
4. `words_at(61.5) = 2.5 * (61.5 - 64.30 - 1.0) = 2.5 * (-3.8) = -9.5` → `lo = max(8, ceil(-9.5)) = 8`.
5. `words_at(68.5) = 2.5 * (68.5 - 64.30 - 1.0) = 2.5 * 3.2 = 8.0` → `hi = min(cap, floor(8.0))`.
6. `cap = min(30, r4_max_vo_words(50.0, 1) - 0)`.
   - `r4_max_vo_words(50.0, 1)`: The R4 share is 45% of runtime. Runtime estimate = `50.0 + (words/2.5 + 1.0) + 14.30`. R4 requires `VO_seconds <= 0.45 * runtime`. This is a circular dependency resolved by the formula in `r4_max_vo_words`.
   - If `cap < 8`, then `hi = min(cap, 8) < 8 = lo` → `lo > hi` → returns `None`.
7. **But** `write_takeaway` does `budget = budget or (LY_TAKEAWAY_MIN_WORDS, MOMENTS_TAKEAWAY_WORD_CAP)` → falls back to `(8, 30)`.
8. The writer is asked for 8-30 words. If it writes 30 words, `runtime()` = `50.0 + (30/2.5 + 1.0) + 14.30 = 50.0 + 13.0 + 14.30 = 77.3s` → **exceeds 70s**.
9. `cheap_checks` fails on `RUNTIME`. The writer is asked to redo. But the redo uses the same fallback budget `(8, 30)` because `takeaway_budget` still returns `None` for `content_s=50.0`.
10. **Result:** Infinite loop of rewrites, or the angle is abandoned. This is a **fail-closed** behavior (no bad package is produced), but it wastes budget and may prevent a valid package from being produced when a shorter takeaway (e.g., 8 words) would have fit.

**Concrete failure:**
- Input: `content_s = 50.0`, no bridge.
- `takeaway_budget(50.0)` returns `None` (because even 8 words pushes the estimate over 70s? Let's verify: `50.0 + (8/2.5 + 1.0) + 14.30 = 50.0 + 4.2 + 14.30 = 68.5s` → **fits**).
- Wait, `words_at(68.5) = 8.0`, so `hi = 8`. `lo = 8`. `cap >= 8`. So `budget = (8, 8)`. This is valid.
- Let's try `content_s = 52.0`: `fixed = 52.0 + 14.30 = 66.30`. `words_at(61.5) = 2.5*(61.5-66.30-1.0) = 2.5*(-5.8) = -14.5` → `lo = 8`. `words_at(68.5) = 2.5*(68.5-66.30-1.0) = 2.5*1.2 = 3.0` → `hi = min(cap, 3)`. If `cap >= 3`, `hi = 3`. `lo=8 > hi=3` → `None`.
- Fallback: `(8, 30)`. Writer writes 8 words. `runtime = 52.0 + (8/2.5+1.0) + 14.30 = 52.0 + 4.2 + 14.30 = 70.5s` → **fails** (exceeds 70s).
- Writer writes 30 words. `runtime = 52.0 + 13.0 + 14.30 = 79.3s` → **fails**.
- **No takeaway length lands 60-70s.** The angle is correctly abandoned. This is **fail-closed** and correct.

**Revised:** Not a P0. The behavior is correct (fail closed). Downgrading to P2 (could be more efficient, but no incorrect output).

---

### P0-3: `medley_content_range` does not account for the bridge's pre-roll in the lower bound
**File:** `pipeline/package.py`, `medley_content_range()` (lines ~103-109 in diff)

**Scenario:**
1. `n_bridges=1`, `bridge_words=12`.
2. `extra = 1 * (12/2.5 + 1.0) = 5.8`.
3. `lo = 60 - 14.30 - 5.8 - (30/2.5 + 1.0) = 60 - 14.30 - 5.8 - 13.0 = 26.9`.
4. `hi = 70 - 14.30 - 5.8 - (8/2.5 + 1.0) = 70 - 14.30 - 5.8 - 4.2 = 45.7`.
5. A line-up with clips totaling 26.9s and a 12-word bridge and a 30-word takeaway: `runtime = 26.9 + (12/2.5+1.0) + (30/2.5+1.0) + 14.

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit of the L-y diff, ROUND 2: cycle 3 consensus (synthesis by the pp-selectid session, 21:30 ET Nov 12)

**Run.** Cycle 3 is a fresh first review of the final diff, which includes the post-cycle-2 changes, QUESTION items
11-15. C3_STEP.diff is 129,213 bytes; the prompt is 166,034 bytes. Reviewers:
- grok-4.20-0309-reasoning (xAI): SHIP no (one P0, refuted below).
- qwen/qwen3.8-27b (Heimdall, effort none): SHIP no (one P0, refuted below).
- z-ai/glm-5.3-flash (Heimdall, effort none): SHIP yes with conditions.

**Spend:** about $0.84 at the config's upper-bound prices.

## Consensus: implemented

| # | finding (reviewers) | disposition |
|---|---|---|
| K6 | the takeaway budget for a flagged join's FIRST write (glm P0-2 / P1-2; qwen P2-2) | IMPLEMENTED. Two gaps: when the 3-word and 12-word budgets did not overlap, or the 12-word one did not exist, the code fell back to the 12-word budget or to (8, 30), and a legal bridge could then miss 60-70 s. Now package.bridge_budget(content) returns the largest bridge limit n <= 12 for which ANY bridge of 3..n words with the stated takeaway range lands 60-70 s; BRIDGE_ASK tells the writer "at most n words". When no bridge length fits, write_takeaway raises NoBridgeFits BEFORE any model call, and build() drops the clip after the flagged join and re-picks (no write paid). A redo with no landing length raises the same. Tests: test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_it_allows (94 clip lengths: every bridge of 3..n words at both takeaway bounds lands 60-70 s; where none fits, no prompt is sent), test_a_flagged_join_no_bridge_can_fill_drops_the_line_up_before_any_write |
| K7 | the table's takeaway pass rate hides the writes stopped before their verdict (grok P2; glm P1-9 / P2-3) | IMPLEMENTED. The table shows passed / judged / WRITTEN per universe and in total. The summary states that a write stopped first by another gate (runtime, shape, a lost clip) is not judged |

## Refuted with evidence

| finding | evidence |
|---|---|
| grok P0: "_package never writes runtime_s_estimate" | package._package sets `pk["runtime_s_estimate"] = runtime(segs, vo_lines)`. test_no_intro_and_one_takeaway_after_the_last_clip asserts its value (39.0 + 8 / 2.5 + 1.0 + 14.30), and 145 tests pass |
| grok P1: a RUNTIME redo can print "None" | the redo's detail branches on the budget: "(a takeaway of N-M words lands it)" or "(no takeaway length lands it: shorten the bridge)". Since K6, a redo with no landing length is refused before the call (NoBridgeFits) |
| grok P2: L-k says the text comparisons must go through canon | the comparisons are between two copies of the package's OWN bytes: the bridge record's text vs the VO line, and the gated line vs the shipped line. L-j wants these exact; canon is for transcripts against locked text |
| qwen P0-6: the ledger's read-modify-write races | Router._lock() opens a new descriptor and takes fcntl.flock(LOCK_EX) for every _reserve / _settle, so threads an

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_2030/C4_STEP.diff (1995 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 51f24c7d..0a2078a2 100644
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
  88 | @@ -126,6 +138,58 @@ R4_MOMENTS_SHARE = 0.45            # orchestrator 08:29 ruling 9: moments-first
  89 |                                     # clip; 60-70 s stays hard
  90 |  
  91 |  
  92 | +LY_CLIPS = (2, 4)                  # L-y 4: 3 to 5 clips = the hook + 2-4 clips, back to back (the medley)
  93 | +LY_TAKEAWAY_MIN_WORDS = 8          # L-y 5: one or two sentences; the cap is ruling 10's MOMENTS_TAKEAWAY_WORD_CAP
  94 | +LY_BRIDGE_WORDS = 12               # L-y 2: the one exceptional bridge, "as short as it can be" (asked of the writer;
  95 | +                                   # config.BRIDGE_WORD_CAP 20 stays the hard bound, ly_shape)
  96 | +LY_BRIDGE_MIN_WORDS = 3            # the shortest bridge a first write budgets for ("Next, on keys.")
  97 | +LY_MAX_BRIDGES = 1                 # L-y 2: at most ONE bridge per video
  98 | +LY_AIM_S = (61.5, 68.5)            # the takeaway's length aims the factory's estimate here when the clips allow it
  99 | +                                   # (inside 60-70 s with margin: the voice measured 2.91 w/s vs R4's 2.5, ruling 12)
 100 | +LY_LINEUPS = 2                     # line-ups tried per angle (a clips-alone failure drops its weak clips once)
 101 | +
 102 | +
 103 | +def medley_content_range(n_bridges=0, bridge_words=LY_BRIDGE_WORDS):
 104 | +    """Seconds the clips may fill so that ONE takeaway of LY_TAKEAWAY_MIN_WORDS..MOMENTS_TAKEAWAY_WORD_CAP words (and
 105 | +    n_bridges bridges of bridge_words) lands the factory's estimate (runtime()) inside 60-70 s (L-y 4)."""
 106 | +    extra = n_bridges * (bridge_words / R4_WPS + R4_PREROLL_S)
 107 | +    lo = RUNTIME_S[0] - FINAL_TAIL_S - extra - (MOMENTS_TAKEAWAY_WORD_CAP / R4_WPS + R4_PREROLL_S)
 108 | +    hi = RUNTIME_S[1] - FINAL_TAIL_S - extra - (LY_TAKEAWAY_MIN_WORDS / R4_WPS + R4_PREROLL_S)
 109 | +    return round(lo, 2), round(hi, 2)
 110 | +
 111 | +
 112 | +def bridge_budget(content_s):
 113 | +    """For a line-up that must carry one bridge (L-y 2), before the bridge is written: (n, (lo, hi)), the largest bridge
 114 | +    limit n <= LY_BRIDGE_WORDS words such that ANY bridge of LY_BRIDGE_MIN_WORDS..n words with a takeaway of lo..hi
 115 | +    words lands the factory's estimate in 60-70 s (the two budgets overlap), or None when no bridge fits these clips
 116 | +    (audit 2030 C3: the writer is never handed a range that a legal bridge can push outside 60-70 s)."""
 117 | +    w = lambda n: [" ".join(["word"] * n)]
 118 | +    short = takeaway_budget(content_s, w(LY_BRIDGE_MIN_WORDS))
 119 | +    if short is None:
 120 | +        return None
 121 | +    for n in range(LY_BRIDGE_WORDS, LY_BRIDGE_MIN_WORDS - 1, -1):
 122 | +        long_ = takeaway_budget(content_s, w(n))
 123 | +        if long_ is not None and max(short[0], long_[0]) <= min(short[1], long_[1]):
 124 | +            return n, (max(short[0], long_[0]), min(short[1], long_[1]))
 125 | +    return None
 126 | +
 127 | +
 128 | +def takeaway_budget(content_s, other=()):
 129 | +    """(lo, hi) words for the takeaway, given the clips' seconds and the other VO lines' texts (a bridge): the factory's
 130 | +    estimate (runtime()) inside LY_AIM_S when the clips allow it, else inside 60-70 s; never under
 131 | +    LY_TAKEAWAY_MIN_WORDS, above the cap of 30 or past R4's share. None when no length lands 60-70 s."""
 132 | +    other = [t for t in other if t and t.strip()]
 133 | +    fixed = content_s + FINAL_TAIL_S + sum(len(t.split()) / R4_WPS + R4_PREROLL_S for t in other)
 134 | +    words_at = lambda s: R4_WPS * (s - fixed - R4_PREROLL_S)     # the takeaway's words that land the estimate at s
 135 | +    cap = min(MOMENTS_TAKEAWAY_WORD_CAP,
 136 | +              r4_max_vo_words(content_s, 1 + len(other)) - sum(len(t.split()) for t in other))
 137 | +    for a, b in (LY_AIM_S, RUNTIME_S):
 138 | +        lo, hi = max(LY_TAKEAWAY_MIN_WORDS, math.ceil(words_at(a) - 1e-9)), min(cap, math.floor(words_at(b) + 1e-9))
 139 | +        if lo <= hi:
 140 | +            return lo, hi
 141 | +    return None
 142 | +
 143 | +
 144 |  def r4_max_vo_words(content_s, n_vo):
 145 |      """The most VO words (intro + bridges) the moments-first R4 allows: edl_rules' own estimate (words / 2.5 + 1 s per
 146 |      VO line) <= R4_MOMENTS_SHARE of the runtime estimate (runtime(): content + that VO + FINAL_TAIL_S)."""
 147 | @@ -179,13 +243,6 @@ def r4(pk):
 148 |                           "R4 (moments-first, 06:00) PASS") + f" | {note}"
 149 |  
 150 |  
 151 | -def budgets(content_s, n_bridges=1):
 152 | -    """Word budgets (intro, each bridge, (min, max) total) that land 60-70 s and fit R4; 40 % to the intro."""
 153 | -    hi = min(r4_max_vo_words(content_s, 1 + n_bridges), int(VO_S[1] * WPS))
 154 | -    lo = min(min_vo_words(content_s, 1 + n_bridges), hi)
 155 | -    return max(6, int(hi * 0.4)), max(4, int(hi * 0.6 / max(1, n_bridges))), (lo, hi)
 156 | -
 157 | -
 158 |  def _name(m, ctx):
 159 |      return (ctx.channel(m["channel_id"]) or {}).get("display_name") or m["channel_name"]
 160 |  
 161 | @@ -197,38 +254,23 @@ def signoff(segs, ctx):
 162 |      return f"Clips today from {who}. Go follow them for more. Links are below."
 163 |  
 164 |  
 165 | -def plain_vo(segs, ctx):
 166 | -    """L-w 2: the plain factual fallback VO ("Next, <show> on <topic>."): it claims nothing beyond who speaks. Ranked
 167 | -    last (orchestrator 03:40); the title names whole channels only (U11)."""
 168 | -    intro = {"text": f"Here's {_name(segs[0], ctx)} on Bitcoin.", "cites": []}
 169 | -    bridges = [{"text": f"Next, {_name(m, ctx)} on Bitcoin.", "cites": []} for m in segs[2:]]
 170 | -    chans = list(dict.fromkeys(_name(m, ctx) for m in segs))
 171 | -    title = "Bitcoin: " + ", ".join(chans[:-1]) + f" and {chans[-1]}"
 172 | -    while len(title) > 70 and len(chans) > 1:
 173 | -        chans = chans[:-1]
 174 | -        title = "Bitcoin: " + ", ".join(chans) + " and others"
 175 | -    caption = f"Clips from {', '.join(dict.fromkeys(_name(m, ctx) for m in segs))}. Links to every source below."
 176 | -    return intro, bridges, {"text": title[:70], "cites": []}, {"text": caption, "cites": []}
 177 | +def labels(n):
 178 | +    """The segments' labels in play order: the hook, then clip_01 ... (the renderer's clip index = the position)."""
 179 | +    return ["hook" if i == 0 else f"clip_{i:02d}" for i in range(n)]
 180 |  
 181 |  
 182 | -def assemble(order, by_id, fields, ctx, vo_kind):
 183 | -    segs = [by_id[i] for i in order]
 184 | -    lines = [dict(fields["intro"], slot="intro")] + \
 185 | -        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 186 | -        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 187 | -    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"].startswith(("intro", "bridge")))
 188 | +def _package(segs, ctx, fields, vo_kind, vo, lines):
 189 | +    vo_words = sum(len(x["text"].split()) for x in lines if x["slot"] not in ("title", "caption"))
 190 |      pk = {"schema": "pp.package/1", "type": fields.get("type", "moments"), "angle": fields.get("angle", ""),
 191 |            "vo_kind": vo_kind, "style": fields.get("style"),
 192 | -          "segments": [{"label": "hook" if i == 0 else f"clip_{i:02d}", "moment_id": m["moment_id"],
 193 | +          "segments": [{"label": lb, "moment_id": m["moment_id"],
 194 |                          "video_id": m["video_id"], "channel_id": m["channel_id"], "channel": _name(m, ctx),
 195 |                          "k0": m["sentences"][0], "k1": m["sentences"][1], "words": m["words"],
 196 |                          "start": m["start"], "end": m["end"], "duration_s": m["duration_s"], "text": m["text"],
 197 |                          "published_at": m["published_at"], "transcript_sha256": m["transcript_sha256"],
 198 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s"}
 199 | -                       for i, m in enumerate(segs)],
 200 | -          "vo": {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 201 | -                 "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1)),     # the renderer's after_clip
 202 | -                 "signoff": signoff(segs, ctx)},
 203 | +                       for lb, m in zip(labels(len(segs)), segs)],
 204 | +          "vo": dict(vo, signoff=signoff(segs, ctx)),
 205 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
 206 |            "hook_first_words": " ".join(segs[0]["text"].split()[:8]),
 207 |            "lines": lines}
 208 | @@ -240,6 +282,46 @@ def assemble(order, by_id, fields, ctx, vo_kind):
 209 |      return pk
 210 |  
 211 |  
 212 | +def assemble(order, by_id, fields, ctx, vo_kind):
 213 | +    """The PBX MAX v3 shape (an intro after the hook and a line after clips; the orchestrator's given packages of the
 214 | +    night of Nov 11-12). L-y's medley is assemble_medley()."""
 215 | +    segs = [by_id[i] for i in order]
 216 | +    lines = [dict(fields["intro"], slot="intro")] + \
 217 | +        [dict(b, slot=f"bridge_{i + 1}") for i, b in enumerate(fields["bridges"])] + \
 218 | +        [dict(fields["title"], slot="title"), dict(fields["caption"], slot="caption")]
 219 | +    vo = {"intro": fields["intro"]["text"], "bridges": [b["text"] for b in fields["bridges"]],
 220 | +          "bridges_after_clip": list(range(1, len(fields["bridges"]) + 1))}      # the renderer's after_clip
 221 | +    return _package(segs, ctx, fields, vo_kind, vo, lines)
 222 | +
 223 | +
 224 | +def assemble_medley(order, by_id, fields, ctx, vo_kind):
 225 | +    """L-y: the clips back to back, ONE takeaway after the last clip (slot "takeaway", the renderer's after_clip = the
 226 | +    last clip), and at most one bridge: after the hook it is the renderer's intro slot (slot "intro"), after clip k it is
 227 | +    a bridge after_clip k (slot "bridge_1"). fields: takeaway, bridge (None or {"text", "cites", "why"}), bridge_after
 228 | +    (None, 0 = after the hook, or k), title, caption."""
 229 | +    segs = [by_id[i] for i in order]
 230 | +    n_clips = len(segs) - 1
 231 | +    b, k = fields.get("bridge"), fields.get("bridge_after")
 232 | +    if b is not None and (type(k) is not int or not 0 <= k < n_clips):
 233 | +        raise ValueError(f"a bridge sits at a join between two clips: after 0..{n_clips - 1}, not {k!r}")
 234 | +    mid = b is not None and k > 0
 235 | +    lines = ([dict(b, slot="intro")] if b is not None and k == 0 else []) + \
 236 | +        ([dict(b, slot="bridge_1")] if mid else []) + \
 237 | +        [dict(fields["takeaway"], slot="takeaway"), dict(fields["title"], slot="title"),
 238 | +         dict(fields["caption"], slot="caption")]
 239 | +    vo = {"intro": b["text"] if b is not None and k == 0 else None,
 240 | +          "bridges": ([b["text"]] if mid else []) + [fields["takeaway"]["text"]],
 241 | +          "bridges_after_clip": ([k] if mid else []) + [n_clips]}
 242 | +    pk = _package(segs, ctx, fields, vo_kind, vo, lines)
 243 | +    pk["shape"] = "medley"
 244 | +    pk["bridge"] = None if b is None else {"after": pk["segments"][k]["label"], "after_clip": k,
 245 | +                                           "join": f"{pk['segments'][k]['label']} -> {pk['segments'][k + 1]['label']}",
 246 | +                                           "text": b["text"], "why": b.get("why"),
 247 | +                                           "confirmed_by": fields.get("bridge_confirmed_by")}
 248 | +    pk["supply_exception"] = fields.get("supply_exception")
 249 | +    return pk
 250 | +
 251 | +
 252 |  # ── step A once per moment (orchestrator 05:25 item 5) ──
 253 |  
 254 |  STEP_A_VERSION = hashlib.sha256(CI.STEP_A.encode()).hexdigest()[:12]
 255 | @@ -309,9 +391,10 @@ def prescreen(router, ms, sources, ctx, writer_vendor, writer_family=None, n=PRE
 256 |      return a_by, fails, vendors, families
 257 |  
 258 |  
 259 | -ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words, with a
 260 | -voice-over that makes a point. Below are clips (verbatim quotes, each with its channel and length) that passed our
 261 | -checks. The channels were not in one conversation and never answer each other.
 262 | +ANGLE_PROMPT = """You are the editor of PBX MAX: 60-second Bitcoin videos made of other channels' own words. The clips
 263 | +play BACK TO BACK as a medley, with NO narration between them; the host speaks ONE closing line at the end. Below are
 264 | +clips (verbatim quotes, each with its channel and length) that passed our checks. The channels were not in one
 265 | +conversation and never answer each other.
 266 |  
 267 |  {note}
 268 |  {clips}
 269 | @@ -320,52 +403,68 @@ Find up to {k} ANGLES, best first. An angle is ONE sentence a viewer could repea
 270 |  GENUINELY support together (each clip adds a different reason, fact or voice to the same point). Do not make a point
 271 |  the clips do not state. Do not build an angle on a price level or move as if it were today's news unless a clip says
 272 |  it is today's.
 273 | -The video uses ONE clip per channel: a hook and 2-3 clips, from 3-4 DIFFERENT channels, together {lo:.0f}-{hi:.0f}
 274 | -seconds of clips. Give as many good angles as the clips allow (aim for {k}); for each angle give: "angle" (the
 275 | -sentence); "moments": the ids of 5 to 8 clips that support it (more choice survives a clip that later fails a check),
 276 | -from at least 3 different channels, with enough seconds among them; "hook": one of those ids whose FIRST WORDS grab
 277 | -attention AND set up the angle; "support": for each of those ids, a few words on what it adds (an internal note).
 278 | +With no narration the ORDER carries the video: list each angle's clips in the order they should PLAY, so that every
 279 | +clip's opening makes sense right after the previous clip's ending, in the speakers' own words (no clip may need an
 280 | +introduction to be understood). The video plays the hook and 2-4 more clips, ONE per channel, from 3-5 DIFFERENT
 281 | +channels, together {lo:.0f}-{hi:.0f} seconds of clips. Give as many good angles as the clips allow (aim for {k}); for
 282 | +each angle give: "angle" (the sentence); "moments": the ids of 4 to 8 clips IN PLAY ORDER, the hook first (more choice
 283 | +survives a clip that later fails a check), from at least 3 different channels, with enough seconds among them;
 284 | +"hook": the first id, whose FIRST WORDS grab attention AND set up the angle; "support": for each of those ids, a few
 285 | +words on what it adds and why it follows the clip before it (an internal note).
 286 |  Return ONLY this JSON object: {{"angles": [{{"angle": "...", "moments": ["id", "id", "id"], "hook": "id",
 287 |  "support": {{"id": "..."}}}}]}}"""
 288 |  
 289 | -STYLES = {
 290 | -    "host": "HOST STYLE: you have a point of view. A bridge may (a) tease the next clip with a question or a topic, never "
 291 | -            "saying what its speaker thinks; (b) hand off with an attribution ONLY for a clip whose speaker is marked "
 292 | -            "VERIFIED, with the clip's own hedge (\"Stephan Livera thinks so.\"); (c) land your own takeaway AFTER a "
 293 | -            "clip, as your opinion, never as what the speaker said.",
 294 | -    "quote": "QUOTE-LED STYLE: introduce each clip by its show and its topic in a few words; you may quote AT MOST FOUR "
 295 | -             "exact words of that clip in quotation marks; the point is carried by the sequence of clips and the ONE "
 296 | -             "title."}
 297 | +MEDLEY_PROMPT = """You watch a short video made ONLY of these clips, played back to back with NO narration between them.
 298 | +Each clip is a person's own words from a show; the shows were not in one conversation.
 299 |  
 300 | -WRITE_V3 = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 301 | +{clips}
 302 | +
 303 | +1) Played back to back with no narration, is there a through-line a viewer can state? State it in ONE sentence, or
 304 | +   "none" if there is none.
 305 | +2) For each clip, rate 1-5 how much it advances that through-line (5 = essential, 1 = off topic).
 306 | +3) For each JOIN between two consecutive clips: could a viewer follow the jump with no narration, i.e. is the next
 307 | +   clip's subject or referent clear coming from the previous clip's ending? Answer true or false, and why in a few
 308 | +   words.
 309 | +Return ONLY this JSON object: {{"through_line": "...", "clips": {{"<label>": 1}}, "joins": {{{joins}}}}}"""
 310 | +
 311 | +WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
 312 |  THE ANGLE (the point this video makes): "{angle}"
 313 | -The clips, in play order (verbatim; the channels were not in one conversation and never answer each other):
 314 | +The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
 315 | +in one conversation and never answer each other):
 316 |  
 317 |  {note}
 318 |  {lineup}
 319 |  
 320 | -The video plays: the HOOK clip, then your INTRO, then clip 1, then {slots}, then a sign-off that credits every channel
 321 | -(written by code).
 322 | -Write:
 323 | -- "intro": heard right AFTER the hook: your own take that sets up the angle.
 324 | -- "bridges": exactly {n_bridges} line(s), one after each clip but the last.
 325 | -- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters.
 326 | -- LENGTH: intro + bridges together {lo}-{hi} words; the intro at most {intro_words}, each bridge at most {bridge_words}.
 327 | +After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off credits every channel (written by code).
 328 | +{bridge}Write:
 329 | +- "takeaway": one or two sentences, {lo}-{hi} words: the point the medley adds up to, as YOUR OWN commentary (your
 330 | +  opinion or conclusion), never a restatement of any clip.
 331 | +- "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
 332 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
 333 | -{style}
 334 |  RULES (a line that breaks one is rejected):
 335 | -- NEVER restate a clip's claim before or after it, and never repeat its words: the clip says it, in its own words.
 336 | -- Your OWN commentary (an opinion, framing, a question, a tease, a takeaway) is welcome, but it must contain no number,
 337 | -  price, date, named person or company, must not say or imply what any speaker thinks, and must not relate speakers.
 338 | +- NEVER restate a clip's claim, and never repeat its words: the clip says it, in its own words.
 339 | +- Your OWN commentary is an opinion or a conclusion, nothing else: no checkable fact, number, price, date, named person
 340 | +  or company; never what a speaker thinks or how speakers relate; no prediction of what will happen; no advice or
 341 | +  instruction to the viewer (no "you should", "your job", "must"); no accusation; nothing that sounds like a quote.
 342 |  - Say what a speaker says or thinks ONLY for a clip marked VERIFIED, by that name, with the clip's own hedge: "thinks"
 343 |    for "I think", "feels" for "I feel like", "says" only for a flat statement. For any other clip credit the SHOW only
 344 | -  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says".
 345 | +  ("on Coin Bureau", "from What Bitcoin Did's show"), never "<name> says" or "<name> discusses".
 346 |  - Never say or imply that channels agree, answer, rebut or react to each other.
 347 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
 348 |    "slams", "exposes", "admits", "confirms", "caught".
 349 | -{extra}Return ONLY this JSON object: {{"intro": {{"text": "...", "cites": []}}, "bridges": [{{"text": "...", "cites": ["id"]}}],
 350 | +- Write the title and caption in sentence case: capitalise only the first word and real names. A line that names a
 351 | +  show, a person or Bitcoin's price cites the clips it comes from.
 352 | +{extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
 353 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
 354 |  
 355 | +BRIDGE_ASK = """ONE JOIN NEEDS HELP: a blind viewer who watched these clips back to back could not follow the jump from
 356 | +{a} to {b} ("{why}"). Write ONE "bridge", heard between them: as short as it can be (at most {n} words); it only makes
 357 | +the next clip's subject or referent clear (its show and its topic, or a question); it never says what the next speaker
 358 | +thinks. Give "why": one sentence on why a viewer could not follow the jump without it. If you judge a viewer CAN
 359 | +follow this jump without narration, give "bridge": null (these clips then do not sit together, and other clips are
 360 | +picked).
 361 | +"""
 362 | +
 363 |  COHERENCE_PROMPT = """You watch a 60-second video. Here is everything it says and shows, in order (each clip is a
 364 |  different person's own words).
 365 |  
 366 | @@ -419,36 +518,43 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
 367 |      return out
 368 |  
 369 |  
 370 | -def lineup_for(angle, by_id, dropped=frozenset()):
 371 | -    """Hook + 2-3 clips for one angle: the proposer's hook (else the angle's best hook-eligible moment by its first
 372 | -    2 s), clips from the angle's other moments, every segment from a different channel (L-u), at most
 373 | -    PRICE_PREDICTIONS_MAX price predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), the
 374 | -    length the runtime AND R4 allow. Best by the proposer's order. None if impossible."""
 375 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False):
 376 | +    """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
 377 | +    medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
 378 | +    angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
 379 | +    predictions (L-u), a clip under SHORT_CLIP_S only as the last (the punchline), and the clips' seconds inside crange
 380 | +    (default medley_content_range(): one takeaway lands the factory's estimate in 60-70 s). Best = the proposer's
 381 | +    earliest moments (the lowest sum of play positions, so the default hook -> clip -> clip when it fits), then the
 382 | +    seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
 383 | +    ONE channel may give two clips, from two different videos. None if impossible."""
 384 | +    lo, hi = crange or medley_content_range()
 385 | +    pos = {m: i for i, m in enumerate(angle["moments"])}
 386 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
 387 |      hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok")]
 388 |      hooks.sort(key=lambda m: (m["moment_id"] != angle["hook"], -m["scores"]["hook_first_2s"]))
 389 |      for h in hooks:
 390 |          pool = [m for m in ms if m is not h and (m.get("eligibility") or {}).get("clip", {}).get("ok")
 391 | -                and m["channel_id"] != h["channel_id"]]
 392 | +                and (repeat_ok or m["channel_id"] != h["channel_id"])]
 393 |          best = None
 394 | -        for n in (3, 2):
 395 | -            lo, hi = content_range(n)
 396 | +        for n in range(clips[0], clips[1] + 1):
 397 |              for combo in itertools.combinations(pool, n):
 398 | -                if len({m["channel_id"] for m in combo}) != n:
 399 | +                chans = [m["channel_id"] for m in (h, *combo)]
 400 | +                if len(set(chans)) != n + 1 and not (repeat_ok and len(set(chans)) == n and
 401 | +                                                     len({m["video_id"] for m in (h, *combo)}) == n + 1):
 402 |                      continue
 403 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
 404 |                      continue
 405 | -                order = sorted(combo, key=lambda m: angle["moments"].index(m["moment_id"]))
 406 | +                order = sorted(combo, key=lambda m: pos[m["moment_id"]])
 407 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
 408 |                      continue
 409 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
 410 |                  if not lo <= dur <= hi:
 411 |                      continue
 412 | -                key = (n, -sum(angle["moments"].index(m["moment_id"]) for m in order))
 413 | +                key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
 414 |                  if best is None or key > best[0]:
 415 |                      best = (key, [h] + order)
 416 | -            if best:
 417 | -                return best[1]
 418 | +        if best:
 419 | +            return best[1]
 420 |      return None
 421 |  
 422 |  
 423 | @@ -489,9 +595,9 @@ def coherence(router, pk, writer_vendor, seed=7, writer_family=None):
 424 |          r = router.call("coherence_verdict", COHERENCE_PROMPT.format(package=CI.package_view(pk)), 1200, seed,
 425 |                          avoid_vendor=writer_vendor, avoid_family=writer_family)
 426 |          v = json.loads(r.text.strip())
 427 | -        labels = [sg["label"] for sg in pk["segments"]]
 428 | +        labs = [sg["label"] for sg in pk["segments"]]
 429 |          if not isinstance(v, dict) or set(v) != {"through_line", "clips", "vo_point"} or \
 430 | -                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labels) or \
 431 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 432 |                  any(type(x) is not int or not 1 <= x <= 5 for x in list(v["clips"].values()) + [v["vo_point"]]):
 433 |              raise ValueError("coherence verdict out of contract")
 434 |      except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 435 | @@ -515,39 +621,156 @@ def _lineup_block(segs, ctx, a_by):
 436 |      return "\n".join(out)
 437 |  
 438 |  
 439 | -def write_v3(router, angle, segs, ctx, a_by, style="host", extra="", seed=7, avoid_vendor=None):
 440 | +def joins(labs):
 441 | +    """The joins of a medley in play order: "<label> -> <next label>"; join k follows segment k (k = 0 is the hook)."""
 442 | +    return [f"{a} -> {b}" for a, b in zip(labs, labs[1:])]
 443 | +
 444 | +
 445 | +def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
 446 | +    """L-y 3: the blind coherence verdict on the clips ALONE (no VO, no title), asked FIRST: "played back to back with
 447 | +    no narration, is there a through-line a viewer can state?", a 1-5 rating per clip, and per join whether a viewer
 448 | +    can follow the jump. Never the vendor / family of the writer. -> (ok, verdict): ok when the through-line is stated
 449 | +    (>= 4 words, not 'none'), every clip rates >= COHERENCE_MIN and at most LY_MAX_BRIDGES joins are not followable;
 450 | +    verdict["flagged"] = the joins a viewer could not follow (a bridge may go only there, L-y 2)."""
 451 | +    import providers as P
 452 | +    labs = labels(len(segs))
 453 | +    js = joins(labs)
 454 | +    clips = "\n".join(f'CLIP label="{lb}" (on screen: {CI._q(_name(m, ctx), 80)}): "{CI._q(m["text"], 900)}"'
 455 | +                      for lb, m in zip(labs, segs))
 456 | +    r = None
 457 | +    try:
 458 | +        r = router.call("coherence_verdict",
 459 | +                        MEDLEY_PROMPT.format(clips=clips, joins=", ".join(
 460 | +                            f'"{j}": {{"followable": true, "why": "..."}}' for j in js)),
 461 | +                        1200, seed, avoid_vendor=writer_vendor, avoid_family=writer_family)
 462 | +        v = json.loads(r.text.strip())
 463 | +        if not isinstance(v, dict) or set(v) != {"through_line", "clips", "joins"} or \
 464 | +                not isinstance(v["clips"], dict) or set(v["clips"]) != set(labs) or \
 465 | +                any(type(x) is not int or not 1 <= x <= 5 for x in v["clips"].values()) or \
 466 | +                not isinstance(v["joins"], dict) or set(v["joins"]) != set(js) or \
 467 | +                any(not isinstance(x, dict) or set(x) != {"followable", "why"} or type(x["followable"]) is not bool
 468 | +                    or not isinstance(x["why"], str) for x in v["joins"].values()):
 469 | +            raise ValueError("clips-alone verdict out of contract")
 470 | +    except (P.ProviderError, P.SpendLimit, ValueError, TypeError) as e:
 471 | +        if r is not None and isinstance(e, (ValueError, TypeError)):
 472 | +            router.reject(r)
 473 | +        return False, {"error": f"{type(e).__name__}: {str(e)[:200]}", "measured": False, "flagged": None}
 474 | +    tl = v["through_line"] if isinstance(v["through_line"], str) else ""
 475 | +    flagged = [j for j in js if v["joins"][j]["followable"] is False]
 476 | +    ok = bool(tl.strip()) and not NO_LINE.search(tl) and len(tl.split()) >= 4 and \
 477 | +        min(v["clips"].values()) >= COHERENCE_MIN and len(flagged) <= LY_MAX_BRIDGES
 478 | +    return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
 479 | +                    replayed=bool(getattr(r, "replayed", False)))
 480 | +
 481 | +
 482 | +class NoBridgeFits(ValueError):
 483 | +    """These clips leave no takeaway length (and, for a flagged join, no bridge length) that lands 60-70 s."""
 484 | +
 485 | +
 486 | +def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 487 | +    """L-y: ONE takeaway (host commentary, class D), ONE title, ONE caption, and a bridge ONLY at `join` (k, why), the
 488 | +    one join the clips-alone verdict flagged (L-y 2): the writer gives it with its reason, or null when it judges a
 489 | +    viewer can follow the jump. The takeaway's word budget lands the factory's estimate (takeaway_budget()) with the
 490 | +    other VO lines' texts `other` (a bridge already written; when a bridge is asked for and none is written yet, the
 491 | +    budget and the bridge limit come from bridge_budget(): any bridge the writer may write lands). Raises NoBridgeFits,
 492 | +    before any model call, when no length lands 60-70 s. -> (reply, fields) with fields["bridge_after"] = k when a
 493 | +    bridge is given."""
 494 |      from select_by_id import UNTRUSTED
 495 |      from story_semantics import quote_data
 496 |      content = sum(m["duration_s"] for m in segs)
 497 | -    nb = len(segs) - 2
 498 | -    iw, bw, (lo, hi) = budgets(content, nb)
 499 | -    slots = ", then ".join(f"your bridge, then clip {i + 2}" for i in range(nb)) or "nothing"
 500 | +    budget, n_bridge = takeaway_budget(content, other), LY_BRIDGE_WORDS
 501 | +    if join is not None and not other:                # until the bridge is written, a budget that holds for ANY bridge
 502 | +        bb = bridge_budget(content)                     # of 3..n words (audit 2030 C1 glm; C2 qwen, grok; C3 glm, qwen)
 503 | +        if bb is None:
 504 | +            raise NoBridgeFits(f"no bridge of {LY_BRIDGE_MIN_WORDS}-{LY_BRIDGE_WORDS} words and takeaway land 60-70 s "
 505 | +                               f"with {content:.1f} s of clips")
 506 | +        n_bridge, budget = bb
 507 | +    if budget is None:
 508 | +        raise NoBridgeFits(f"no takeaway length lands 60-70 s with {content:.1f} s of clips and the lines {list(other)}")
 509 | +    labs = labels(len(segs))
 510 | +    ask, shape = "", "null"
 511 | +    if join is not None:
 512 | +        k, why = join
 513 | +        ask = BRIDGE_ASK.format(a=labs[k].upper().replace("_", " "), b=labs[k + 1].upper().replace("_", " "),
 514 | +                                why=" ".join(quote_data(why, 300).replace('"', "'").split()), n=n_bridge)
 515 | +        shape = '{"text": "...", "cites": ["id"], "why": "..."} or null'
 516 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
 517 | -    prompt = WRITE_V3.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 518 | -                             lineup=_lineup_block(segs, ctx, a_by), slots=slots, n_bridges=nb, lo=lo, hi=hi,
 519 | -                             intro_words=min(iw, 30), bridge_words=min(bw, 20), style=STYLES[style],
 520 | -                             extra=(extra + "\n") if extra else "")
 521 | +    prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
 522 | +                             lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
 523 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape)
 524 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor)
 525 |      try:
 526 |          obj = json.loads(r.text.strip())
 527 |          ids = [m["moment_id"] for m in segs]
 528 | -        keys = {"intro", "bridges", "title", "caption"}
 529 | +        keys = {"takeaway", "bridge", "title", "caption"}
 530 |          if not isinstance(obj, dict) or set(obj) != keys:
 531 |              raise ValueError(f"keys must be exactly {sorted(keys)}")
 532 | -        if not isinstance(obj["bridges"], list) or len(obj["bridges"]) != nb:
 533 | -            raise ValueError(f"'bridges' must hold {nb} lines")
 534 | -        for slot, ln in [("intro", obj["intro"]), ("title", obj["title"]), ("caption", obj["caption"])] + \
 535 | -                [(f"bridge_{i + 1}", b) for i, b in enumerate(obj["bridges"])]:
 536 | -            if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
 537 | +        lines = [("takeaway", obj["takeaway"], {"text", "cites"}), ("title", obj["title"], {"text", "cites"}),
 538 | +                 ("caption", obj["caption"], {"text", "cites"})]
 539 | +        if obj["bridge"] is not None:
 540 | +            if join is None:
 541 | +                raise ValueError("no join needs a bridge: 'bridge' must be null (L-y 1)")
 542 | +            lines.append(("bridge", obj["bridge"], {"text", "cites", "why"}))
 543 | +        for slot, ln, want in lines:
 544 | +            if not isinstance(ln, dict) or set(ln) != want or not isinstance(ln["text"], str) or \
 545 |                      not ln["text"].strip() or not isinstance(ln["cites"], list) or \
 546 | -                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]):
 547 | -                raise ValueError(f"{slot}: needs text and cites from the line-up's ids")
 548 | +                    any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
 549 | +                    ("why" in want and (not isinstance(ln["why"], str) or not ln["why"].strip())):
 550 | +                raise ValueError(f"{slot}: needs text and cites from the line-up's ids" +
 551 | +                                 (" and a reason" if "why" in want else ""))
 552 |          if len(obj["title"]["text"]) > 70 or len(obj["caption"]["text"]) > 220:
 553 |              raise ValueError("title <= 70 characters, caption <= 220")
 554 |      except (ValueError, TypeError):
 555 |          router.reject(r)
 556 |          raise
 557 | -    return r, dict(obj, type="moments", angle=angle["angle"], style=style)
 558 | +    return r, dict(obj, bridge_after=join[0] if join is not None and obj["bridge"] is not None else None,
 559 | +                   type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
 560 | +
 561 | +
 562 | +def ly_shape(pk):
 563 | +    """L-y (orchestrator 20:30), checked by code on the package -> (ok, [why]): 3-5 segments; ONE takeaway, after the
 564 | +    last clip; at most LY_MAX_BRIDGES bridge(s), each at a join the clips-alone verdict flagged (pk["medley"], measured)
 565 | +    with its reason recorded, and every flagged join bridged (else these clips do not sit together); a bridge within
 566 | +    config.BRIDGE_WORD_CAP words; one clip per channel unless pk["supply_exception"] says why not (L-y 4)."""
 567 | +    from config import BRIDGE_WORD_CAP
 568 | +    segs, vo = pk["segments"], pk["vo"]
 569 | +    n_clips = len(segs) - 1
 570 | +    fails = []
 571 | +    if not LY_CLIPS[0] <= n_clips <= LY_CLIPS[1]:
 572 | +        fails.append(f"{len(segs)} segments: a medley plays 3-5 (the hook + {LY_CLIPS[0]}-{LY_CLIPS[1]} clips)")
 573 | +    bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
 574 | +    if not bridges or len(after) != len(bridges) or after[-1] != n_clips or not (bridges[-1] or "").strip():
 575 | +        fails.append("no takeaway after the last clip (L-y 1)")
 576 | +    js = joins([sg["label"] for sg in segs])
 577 | +    bridged = ([js[0]] if vo.get("intro") else []) + [js[a] for a in after[:-1] if type(a) is int and 0 < a < n_clips]
 578 | +    texts = ([vo["intro"]] if vo.get("intro") else []) + bridges[:-1]
 579 | +    if len(bridged) != len(texts):
 580 | +        fails.append(f"a line after clips {after[:-1]} that is not at a join between two clips")
 581 | +    if len(texts) > LY_MAX_BRIDGES:
 582 | +        fails.append(f"{len(texts)} bridges (L-y 2: at most {LY_MAX_BRIDGES})")
 583 | +    med = pk.get("medley") or {}
 584 | +    if med.get("measured") is not True or not isinstance(med.get("flagged"), list):
 585 | +        fails.append("the clips-alone verdict was not measured (L-y 3)")
 586 | +    elif sorted(bridged) != sorted(med["flagged"]):
 587 | +        fails.append(f"bridges at {bridged or 'no join'}, the clips-alone verdict flagged {med['flagged'] or 'no join'}"
 588 | +                     f": a bridge goes only, and always, where a viewer could not follow the jump (L-y 2)")
 589 | +    rec = pk.get("bridge") or {}
 590 | +    if texts and not (rec.get("why") or "").strip():
 591 | +        fails.append("the bridge's reason is not recorded (L-y 2)")
 592 | +    if texts and (not isinstance(rec.get("text"), str) or rec["text"].strip() != texts[0].strip()):
 593 | +        fails.append("the bridge record's text is not the bridge line (the factory's R11 binds them)")
 594 | +    cb = rec.get("confirmed_by")
 595 | +    if texts and not ((isinstance(cb, str) and cb.strip()) or (isinstance(cb, (list, dict)) and cb)):
 596 | +        fails.append("the bridge's confirmation by the clips-alone verdict is not recorded (L-y 2, R11)")
 597 | +    if not texts and pk.get("bridge"):
 598 | +        fails.append("a bridge record with no bridge line")
 599 | +    for t in texts:
 600 | +        if len(t.split()) > BRIDGE_WORD_CAP:
 601 | +            fails.append(f"bridge of {len(t.split())} words (max {BRIDGE_WORD_CAP})")
 602 | +    chans = [sg["channel_id"] for sg in segs]
 603 | +    if len(set(chans)) != len(chans) and not (pk.get("supply_exception") or "").strip():
 604 | +        fails.append("two clips from one channel without the supply exception recorded (L-y 4)")
 605 | +    return not fails, fails
 606 |  
 607 |  
 608 |  def fidelity_segments(pk, a_by):
 609 | @@ -563,7 +786,7 @@ def fidelity_segments(pk, a_by):
 610 |  
 611 |  def cheap_checks(pk, a_by, levels, now):
 612 |      """The gates that cost nothing, run before any paid verdict: VO fidelity's deterministic rules, DUPLICATE,
 613 | -    runtime, R4. -> (violations, det, dup, rt_ok, r4_res)."""
 614 | +    runtime, R4, and for a medley the L-y shape. -> (violations, det, dup, rt_ok, r4_res)."""
 615 |      segs_v = fidelity_segments(pk, a_by)
 616 |      lines = [{"slot": x["slot"], "text": x["text"], "cites": x["cites"]} for x in pk["lines"]]
 617 |      man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 618 | @@ -571,10 +794,13 @@ def cheap_checks(pk, a_by, levels, now):
 619 |      dup = duplicates(pk)
 620 |      rt_ok = RUNTIME_S[0] <= pk["runtime_s_estimate"] <= RUNTIME_S[1]
 621 |      r4_res = r4(pk)
 622 | +    what = "the takeaway's" if pk.get("shape") == "medley" else "the VO's"
 623 |      v = det["violations"] + dup + ([] if rt_ok else [{"slot": "-", "rule": "RUNTIME", "detail":
 624 | -                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change the VO's "
 625 | +                                                      f"{pk['runtime_s_estimate']} s outside 60-70 s: change {what} "
 626 |                                                        f"length"}]) + \
 627 |          ([] if r4_res[0] else [{"slot": "-", "rule": "R4", "detail": r4_res[1]}])
 628 | +    if pk.get("shape") == "medley":
 629 | +        v += [{"slot": "-", "rule": "LY_SHAPE", "detail": why} for why in ly_shape(pk)[1]]
 630 |      return v, det, dup, rt_ok, r4_res
 631 |  
 632 |  
 633 | @@ -654,16 +880,48 @@ def _writers(router):
 634 |  
 635 |  
 636 |  def _redo(violations):
 637 | -    return ("Your previous script was REJECTED. Exactly these lines failed, with the reason; rewrite ONLY them:\n" +
 638 | -            "\n".join(f"- {v['slot']}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 639 | +    """The writer's second try: exactly the failing lines, by the keys the writer returns ("bridge" for the one bridge,
 640 | +    whichever join it sits at)."""
 641 | +    key = {"intro": "bridge", "bridge_1": "bridge"}
 642 | +    return ("Your previous reply was REJECTED. Return the WHOLE JSON object again, every key; rewrite ONLY the lines "
 643 | +            "below and keep the others exactly as they were. The failing lines, with the reason:\n" +
 644 | +            "\n".join(f"- {key.get(v['slot'], v['slot'])}: {v['rule']}: {v['detail']}" for v in violations)[:1800])
 645 | +
 646 | +
 647 | +def _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid=None, cx=None):
 648 | +    """One written takeaway and the gates on ITS line (L-y 6: "one free-text line to judge per video ... measure it"):
 649 | +    the deterministic fidelity rules and DUPLICATE on the takeaway slot, then the classifying verdict's violations on it.
 650 | +    passed: True / False once the verdict judged it, None when other gates stopped the write before the verdict.
 651 | +    context_framing: the context-integrity failures the VO's framing causes (VO_DEPENDENT; per clip, so not attributed
 652 | +    to one line: recorded beside `passed`, never folded into it)."""
 653 | +    line = next((x for x in pk["lines"] if x["slot"] == "takeaway"), {})
 654 | +    rec = {"angle": ai + 1, "lineup": n_lineup, "write": w_used, "text": line.get("text"),
 655 | +           "words": len((line.get("text") or "").split()),
 656 | +           "cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") == "takeaway"}),
 657 | +           "other_cheap_fail": sorted({v["rule"] for v in cheap if v.get("slot") != "takeaway"}), "verdict_fail": None,
 658 | +           "passed": False if any(v.get("slot") == "takeaway" for v in cheap) else None,
 659 | +           "context_framing": None if cx is None else sorted({v["rule"] for v in cx.get("violations") or []
 660 | +                                                              if v.get("rule") in VO_DEPENDENT})}
 661 | +    if fid is not None:
 662 | +        ver = fid.get("verdict") or {}
 663 | +        if fid.get("measured") and isinstance(ver.get("violations"), list):
 664 | +            rec["verdict_fail"] = sorted({v["rule"] for v in ver["violations"] if v.get("slot") in ("takeaway", "-")})
 665 | +            rec["passed"] = not rec["cheap_fail"] and not rec["verdict_fail"]
 666 | +        else:
 667 | +            rec["verdict_fail"] = ["NOT MEASURED"]
 668 | +            rec["passed"] = False if rec["cheap_fail"] else None
 669 | +    return rec
 670 |  
 671 |  
 672 |  def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=print, max_angles=MAX_ANGLES,
 673 | -          writes=WRITES, work_dir=None, store=None, styles=("host", "quote"), spend=None):
 674 | -    """Angle first, inside the orchestrator's budgets (05:25 item 5, 05:30): at most max_angles angles x `writes`
 675 | -    writes, stopped at the first package that passes every hard gate with coherence >= COHERENCE_MIN. work_dir: where
 676 | -    law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger. spend: a
 677 | -    callable returning the ledger's USD (dollars per package). -> {"package", "packages", "tried", "angles", ...}."""
 678 | +          writes=WRITES, work_dir=None, store=None, spend=None, lineups=LY_LINEUPS):
 679 | +    """L-y MEDLEY (the default since orchestrator 20:30 Nov 12), angle first, inside the orchestrator's budgets (05:25
 680 | +    item 5, 05:30): per angle at most `lineups` line-ups, each judged on the clips ALONE first (medley(); nothing is
 681 | +    written for a line-up that fails it); a line-up that passes gets at most `writes` writes of the takeaway (and of the
 682 | +    one bridge, only at the join the clips-alone verdict flagged); the first package that passes every hard gate wins.
 683 | +    work_dir: where law L-v 2's audio windows go (required: without it no package can pass). store: the step-A ledger.
 684 | +    spend: a callable returning the ledger's USD (dollars per package).
 685 | +    -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 686 |      t0 = time.time()
 687 |      usd0 = spend() if spend else None
 688 |      ms, why = usable(moments, ctx, delivered, optout)
 689 | @@ -671,9 +929,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 690 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
 691 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
 692 |      levels = current_levels(sources.values(), ctx)
 693 | -    out = {"packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 694 | +    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
 695 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
 696 | -                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "package": None}
 697 | +                         "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 698 | +           "package": None}
 699 |      log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 700 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 701 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 702 | @@ -683,9 +942,25 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 703 |          return out
 704 |      from select_by_id import UNTRUSTED
 705 |      from story_semantics import quote_data
 706 | +    exc, tru = {}, {}
 707 | +    with ThreadPoolExecutor(max_workers=8) as pre:     # L-v 2 + CUTTABLE per moment, before the angles (L-y 3)
 708 | +        futs = {mid: pre.submit(truth_for, router, m, work_dir, tru) for mid, m in cleared.items()}
 709 | +        tru.update({mid: f.result() for mid, f in futs.items()})
 710 | +    cut_ok = lambda t: bool(t.get("ok")) and (t.get("edges") or {}).get("cuttable") is True
 711 | +    out["prescreen"]["second_pass"] = {
 712 | +        mid: "PASS" if cut_ok(t) else ("NOT MEASURED: " + t["error"] if t.get("error") else
 713 | +                                       "L-v 2 FAIL" if not t.get("ok") else "not cuttable at an edge (ruling C / 7)")
 714 | +        for mid, t in tru.items()}
 715 | +    cleared = {mid: m for mid, m in cleared.items() if cut_ok(tru.get(mid) or {})}
 716 | +    out["prescreen"]["cuttable"] = len(cleared)
 717 | +    log(f"  {len(cleared)} of them pass the second recognition pass and CUTTABLE ({time.time() - t0:.0f} s)")
 718 | +    if len({m["channel_id"] for m in cleared.values()}) < 3:
 719 | +        out["why_none"] = (f"{len(cleared)} cleared moments pass the second pass and CUTTABLE, from fewer than 3 "
 720 | +                           f"channels")
 721 | +        return out
 722 |      clips = "\n".join(f'id={m["moment_id"]} | {_name(m, ctx)} | {m["duration_s"]:.1f} s | "{quote_data(m["text"], 600)}"'
 723 |                        for m in sorted(cleared.values(), key=lambda m: (-m["rank_score"], m["moment_id"])))
 724 | -    lo, hi = content_range(2)[0], content_range(3)[1]
 725 | +    lo, hi = medley_content_range()
 726 |      angles, angle_reply = None, None
 727 |      for seed in (7, 8):                               # one re-ask on an out-of-contract reply (never served again)
 728 |          r = None
 729 | @@ -704,28 +979,65 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 730 |      out["angles"] = [{"angle": a["angle"], "moments": a["moments"], "hook": a["hook"]} for a in angles]
 731 |      writers_v, writers_f = {angle_reply.vendor}, {angle_reply.family}
 732 |      log(f"  {len(angles)} angles from {angle_reply.backend} ({time.time() - t0:.0f} s)")
 733 | -    exc, tru = {}, {}
 734 | +    doomed = set()                                         # moments a per-moment gate dropped: out of every angle
 735 |      with ThreadPoolExecutor(max_workers=8) as pool:
 736 |          for ai, angle in enumerate(angles):
 737 | -            dropped, w_used = set(), 0
 738 | -            while w_used < writes and not out["packages"]:
 739 | -                segs = lineup_for(angle, cleared, frozenset(dropped))
 740 | -                rec = {"angle": ai + 1, "text": angle["angle"],
 741 | -                       "lineup": [m["moment_id"] for m in segs] if segs else None, "attempts": []}
 742 | +            dropped, n_lineup = set(), 0
 743 | +            while n_lineup < lineups and not out["packages"]:
 744 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed)), None
 745 | +                if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 746 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True)
 747 | +                    if segs is not None:
 748 | +                        rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 749 | +                               if sum(m["channel_id"] == c for m in segs) > 1]
 750 | +                        exception = (f"one clip per channel cannot fill the medley's seconds from this angle's moments: "
 751 | +                                     f"{', '.join(_name(next(m for m in segs if m['channel_id'] == c), ctx) for c in rep)}"
 752 | +                                     f" gives two clips, from two videos (L-y 4)")
 753 | +                rec = {"angle": ai + 1, "text": angle["angle"], "lineup": [m["moment_id"] for m in segs] if segs else None,
 754 | +                       "supply_exception": exception, "attempts": []}
 755 |                  out["tried"].append(rec)
 756 |                  if segs is None:
 757 | -                    rec["why"] = "no line-up: fewer than a hook + 2 clips from distinct channels in the length rules"
 758 | +                    rec["why"] = "no line-up: the hook + 2-4 clips inside the medley's seconds and the channel rules"
 759 |                      break
 760 | +                n_lineup += 1
 761 | +                ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai, writer_family=writers_f)
 762 | +                rec["medley"], rec["medley_ok"] = med, ok_m
 763 | +                log(f"  angle {ai + 1} line-up {n_lineup} ({len(segs)} clips, "
 764 | +                    f"{sum(m['duration_s'] for m in segs):.1f} s): clips alone {'PASS' if ok_m else 'FAIL'} "
 765 | +                    f"{med.get('clips')} flagged {med.get('flagged')} ({time.time() - t0:.0f} s)")
 766 | +                labs = labels(len(segs))
 767 | +                if not ok_m:                              # L-y 2 / 3: pick clips that sit together
 768 | +                    by_lab = dict(zip(labs, segs))
 769 | +                    weak = {by_lab[lb]["moment_id"] for lb, x in (med.get("clips") or {}).items()
 770 | +                            if lb in by_lab and lb != "hook" and x < COHERENCE_MIN}
 771 | +                    if len(med.get("flagged") or []) > LY_MAX_BRIDGES:
 772 | +                        weak |= {by_lab[j.split(" -> ")[1]]["moment_id"] for j in med["flagged"][1:]}
 773 | +                    if not med.get("measured") or not weak:
 774 | +                        rec["why"] = "the clips alone have no through-line a viewer can state (or it was not measured)"
 775 | +                        break
 776 | +                    dropped |= weak
 777 | +                    rec["why"] = f"the clips alone fail (ratings / joins): dropped {sorted(weak)}, re-lined"
 778 | +                    continue
 779 | +                join = None
 780 | +                if med["flagged"]:
 781 | +                    k = joins(labs).index(med["flagged"][0])
 782 | +                    join = (k, med["joins"][med["flagged"][0]]["why"])
 783 |                  bg = {m["moment_id"]: (pool.submit(exclusion_for, router, m, sources, exc),
 784 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
 785 | -                extra, relined = "", False
 786 | +                extra, relined, w_used, written = "", False, 0, ()
 787 |                  while w_used < writes:
 788 | -                    style = styles[min(w_used, len(styles) - 1)]
 789 |                      w_used += 1
 790 |                      try:
 791 | -                        wr, fields = write_v3(router, angle, segs, ctx, a_by, style, extra, seed=7 + w_used + 10 * ai)
 792 | +                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 793 | +                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup, other=written)
 794 | +                    except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 795 | +                        if join is not None:
 796 | +                            dropped.add(segs[join[0] + 1]["moment_id"])
 797 | +                        rec["why"] = f"{e}: re-lined"
 798 | +                        relined = join is not None
 799 | +                        break
 800 |                      except Exception as e:
 801 | -                        rec["attempts"].append({"style": style, "writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 802 | +                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 803 |                          continue
 804 |                      writers_v.add(wr.vendor)
 805 |                      writers_f.add(wr.family)
 806 | @@ -740,25 +1052,61 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 807 |                              dropped |= {m["moment_id"] for m in stale if CI.a_failures(a_by.get(m["moment_id"], {}))}
 808 |                              relined = True
 809 |                              break
 810 | -                    pk = assemble([m["moment_id"] for m in segs], cleared, fields, ctx,
 811 | -                                  f"written ({style}), attempt {w_used}")
 812 | +                    if join is not None and fields["bridge"] is None:
 813 | +                        dropped.add(segs[join[0] + 1]["moment_id"])
 814 | +                        rec["why"] = (f"the clips-alone verdict flagged {med['flagged'][0]}; the writer judged it "
 815 | +                                      f"followable without a bridge: these clips do not sit together (L-y 2): re-lined")
 816 | +                        relined = True
 817 | +                        break
 818 | +                    if fields["bridge"] is not None:
 819 | +                        fields["bridge_confirmed_by"] = {"join": med["flagged"][0], "why": join[1],
 820 | +                                                         "backend": med.get("backend")}
 821 | +                    fields["supply_exception"] = exception
 822 | +                    pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 823 | +                                         f"medley (L-y), written, attempt {w_used}")
 824 | +                    pk["medley"] = med
 825 | +                    written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
 826 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 827 | -                    att = {"style": style, "writer": wr.backend, "runtime": pk["runtime_s_estimate"],
 828 | +                    att = {"writer": wr.backend, "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 829 | +                           "takeaway_budget": fields.get("takeaway_budget"),
 830 |                             "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 831 |                      rec["attempts"].append(att)
 832 | -                    log(f"  angle {ai + 1} write {w_used} ({style}, {wr.backend}): " +
 833 | +                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 834 | +                    out["takeaways"].append(take)
 835 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 836 | +                        f"words, {pk['runtime_s_estimate']} s): " +
 837 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 838 |                          + f" ({time.time() - t0:.0f} s)")
 839 | +                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}   # the clips' own gates first
 840 | +                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")
 841 | +                            or (t.get("edges") or {}).get("cuttable") is not True}   # CUTTABLE is a required gate
 842 | +                    if lost:
 843 | +                        rec["lost_why"] = {mid: ("exclusion" if e.get("verdict") != "keep" else
 844 | +                                                 "second pass (L-v 2)" if not t.get("ok") else
 845 | +                                                 "not cuttable at an edge (ruling C / 7)")
 846 | +                                           for mid, (e, t) in got.items() if mid in lost}
 847 | +                        att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 848 | +                        dropped |= lost
 849 | +                        doomed |= lost                         # per-moment verdicts: no angle may use them again
 850 | +                        rec["why"] = f"exclusion / L-v 2 / CUTTABLE dropped {rec['lost_why']}: re-lined"
 851 | +                        relined = True
 852 | +                        break
 853 |                      if cheap:
 854 |                          att["violations"] = cheap
 855 | -                        extra = _redo(cheap)
 856 | +                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 857 | +                        extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 858 | +                                                                     if b else " (no takeaway length lands it: shorten "
 859 | +                                                                                "the bridge)"))
 860 | +                                       if v["rule"] == "RUNTIME" else v for v in cheap])
 861 |                          continue
 862 |                      fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 863 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 864 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 865 |                      att["violations"] = fid["violations"] + cx["violations"]
 866 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 867 | -                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'}, context {'PASS' if cx['ok'] else 'FAIL'} "
 868 | -                        f"({time.time() - t0:.0f} s)")
 869 | +                    log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 870 | +                        f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 871 | +                        f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 872 |                      if not fid["ok"] or not cx["ok"]:
 873 |                          if fid["ok"] and not framing:
 874 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 875 | @@ -768,31 +1116,42 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 876 |                                                              "detail": VO_FIX.get(v["rule"], v["detail"])}
 877 |                                                             for v in framing])
 878 |                          continue
 879 | -                    got = {mid: (f[0].result(), f[1].result()) for mid, f in bg.items()}
 880 | -                    lost = {mid for mid, (e, t) in got.items() if e.get("verdict") != "keep" or not t.get("ok")}
 881 |                      att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 882 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 883 | -                    if lost:
 884 | -                        dropped |= lost
 885 | -                        rec["why"] = f"exclusion / L-v 2 dropped {sorted(lost)}: re-lined"
 886 | -                        relined = True
 887 | -                        break
 888 | -                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)
 889 | +                    ok_c, coh = coherence(router, pk, writers_v, writer_family=writers_f)    # then on the takeaway
 890 |                      att["coherence"] = coh
 891 | -                    log(f"    coherence {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo {coh.get('vo_point')} "
 892 | -                        f"({time.time() - t0:.0f} s)")
 893 | +                    log(f"    coherence with the takeaway {'PASS' if ok_c else 'FAIL'} {coh.get('clips')} vo "
 894 | +                        f"{coh.get('vo_point')} ({time.time() - t0:.0f} s)")
 895 |                      a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 896 |                      pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
 897 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 898 | -                                            ok_c, coh)
 899 | +                                            ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk))
 900 |                      if not ok_c:
 901 | -                        rec["why"] = "coherence below 4 or no through-line: next angle"
 902 | +                        tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 903 | +                        if coh.get("measured") and type(coh.get("vo_point")) is int and \
 904 | +                                coh["vo_point"] < COHERENCE_MIN and min(coh["clips"].values()) >= COHERENCE_MIN and \
 905 | +                                len(tl.split()) >= 4 and not NO_LINE.search(tl):
 906 | +                            extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 907 | +                                            f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 908 | +                                            f"being supported by the clips: land the point the clips make together"}])
 909 | +                            continue                          # the clips hold; only the takeaway's point is weak
 910 | +                        weak = {sg["moment_id"] for sg in pk["segments"][1:]
 911 | +                                if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 912 | +                        dropped |= weak
 913 | +                        relined = bool(weak)
 914 | +                        rec["why"] = ("coherence with the takeaway below 4 or no through-line: " +
 915 | +                                      (f"dropped {sorted(weak)}, re-lined" if weak else "next angle"))
 916 | +                        break
 917 | +                    import package_pin
 918 | +                    problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
 919 | +                    if problems:                              # never return a package its pin would refuse (L-j)
 920 | +                        rec["why"] = f"a required gate is not exactly PASS: {problems}: next angle"
 921 |                          w_used = writes
 922 |                          break
 923 | -                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend,
 924 | +                    pk["models"] = {"angle": angle_reply.backend, "writer": wr.backend, "medley": med.get("backend"),
 925 |                                      "fidelity_verdict": fid.get("backend"), "context": cx.get("backends"),
 926 |                                      "coherence": coh.get("backend")}
 927 | -                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh}
 928 | +                    pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": med}
 929 |                      pk["seconds"] = round(time.time() - t0, 1)
 930 |                      pk["usd"] = round(spend() - usd0, 4) if spend else None
 931 |                      out["packages"].append(pk)
 932 | @@ -802,8 +1161,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 933 |                      break
 934 |              if out["packages"]:
 935 |                  break
 936 | -            if time.time() - t0 > BUDGET_S * 2 or (spend and spend() - usd0 > BUDGET_USD * 2):
 937 | -                out["why_none"] = "twice the per-package time / spend budget is used: stopped"
 938 | +            used_s, used_usd = time.time() - t0, (spend() - usd0) if spend else 0.0
 939 | +            if used_s > BUDGET_S * 2 or used_usd > BUDGET_USD * 2:
 940 | +                out["why_none"] = (f"stopped after angle {ai + 1} of {len(angles)}: {used_s:.0f} s of the "
 941 | +                                   f"{BUDGET_S * 2:.0f} s / ${used_usd:.2f} of the ${BUDGET_USD * 2:.2f} (estimate) "
 942 | +                                   f"per-package budget (05:25 item 5, twice)")
 943 | +                out["budget_stop"] = {"seconds": round(used_s, 1), "usd_estimate": round(used_usd, 4),
 944 | +                                      "angles_tried": ai + 1, "angles": len(angles)}
 945 |                  break
 946 |      out["package"] = out["packages"][0] if out["packages"] else None
 947 |      out["seconds"] = round(time.time() - t0, 1)
 948 | @@ -811,9 +1175,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 949 |      return out
 950 |  
 951 |  
 952 | -def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 953 | -    """The sealed GATE INVENTORY (audit p2 C1; package_pin.REQUIRED_GATES): one row per hard gate, each
 954 | -    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m)."""
 955 | +def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None):
 956 | +    """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 957 | +    {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 958 | +    A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 959 | +    (shape=(ok, [why]) from ly_shape())."""
 960 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 961 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 962 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 963 | @@ -861,4 +1227,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh):
 964 |                          measured=all("edges" in t for t in truth.values())),
 965 |          "coherence": dict(row(bool(coh_ok), coh.get("backend"), coh.get("replayed"), measured=bool(coh.get("measured"))),
 966 |                            **votes_of(coh)),
 967 | +        **({"medley": dict(row(bool(medley[0]), medley[1].get("backend"), medley[1].get("replayed"),
 968 | +                               measured=bool(medley[1].get("measured"))), flagged=medley[1].get("flagged"))}
 969 | +           if medley is not None else {}),
 970 | +        **({"ly_shape": dict(row(bool(shape[0]), "code (package.ly_shape, L-y)"), why=list(shape[1]))}
 971 | +           if shape is not None else {}),
 972 |      }
 973 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 974 | index 3194dcc1..b1da529b 100644
 975 | --- a/pipeline/package_pin.py
 976 | +++ b/pipeline/package_pin.py
 977 | @@ -25,6 +25,13 @@ from datetime import datetime, timezone
 978 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 979 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 980 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 981 | +MEDLEY_GATES = ("medley", "ly_shape")      # L-y (orchestrator 20:30): the clips-alone verdict and the medley's shape
 982 | +
 983 | +
 984 | +def required_gates(pk):
 985 | +    """The rows a package's inventory must hold, each exactly PASS: REQUIRED_GATES, and for a medley (L-y) also the
 986 | +    clips-alone verdict and the L-y shape."""
 987 | +    return REQUIRED_GATES + (MEDLEY_GATES if (pk or {}).get("shape") == "medley" else ())
 988 |  
 989 |  
 990 |  class PinRefused(Exception):
 991 | @@ -44,12 +51,12 @@ def seal(segments, edl_vo, signoff, title, caption, gates):
 992 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
 993 |  
 994 |  
 995 | -def gate_problems(gates):
 996 | +def gate_problems(gates, required=REQUIRED_GATES):
 997 |      """[why] for an inventory that does not authorise a pin (empty = every required gate exactly PASS, measured live)."""
 998 |      if not isinstance(gates, dict):
 999 |          return ["no gate inventory"]
1000 |      out = []
1001 | -    for g in REQUIRED_GATES:
1002 | +    for g in required:
1003 |          row = gates.get(g)
1004 |          if not isinstance(row, dict) or row.get("status") != "PASS":
1005 |              out.append(f"{g}: {(row or {}).get('status') if isinstance(row, dict) else 'missing'}")
1006 | @@ -58,6 +65,17 @@ def gate_problems(gates):
1007 |      return out
1008 |  
1009 |  
1010 | +def bridge_slots(pk):
1011 | +    """The line slot of each VO bridge, in order: bridge_1, bridge_2 ...; in a medley (L-y) the line after the LAST clip
1012 | +    is the "takeaway" and the one bridge before it is bridge_1."""
1013 | +    vo = pk.get("vo") or {}
1014 | +    after = list(vo.get("bridges_after_clip") or [])
1015 | +    last = len(pk.get("segments") or []) - 1
1016 | +    if pk.get("shape") == "medley":
1017 | +        return ["takeaway" if a == last else f"bridge_{i + 1}" for i, a in enumerate(after)]
1018 | +    return [f"bridge_{i + 1}" for i in range(len(vo.get("bridges") or []))]
1019 | +
1020 | +
1021 |  def line_problems(pk):
1022 |      """The gated lines must BE the VO, title and caption that will be spoken and shown (audit C2 K3)."""
1023 |      by = {x.get("slot"): x.get("text") for x in pk.get("lines") or []}
1024 | @@ -66,8 +84,9 @@ def line_problems(pk):
1025 |      if by.get("intro") != vo.get("intro"):
1026 |          out.append("intro")
1027 |      bridges, after = list(vo.get("bridges") or []), list(vo.get("bridges_after_clip") or [])
1028 | -    if len(bridges) != len(after) or any(by.get(f"bridge_{i + 1}") != t for i, t in enumerate(bridges)) or \
1029 | -            any(k.startswith("bridge_") and int(k.split("_")[1]) > len(bridges) for k in by if k):
1030 | +    slots = bridge_slots(pk)
1031 | +    if len(bridges) != len(after) or any(by.get(s) != t for s, t in zip(slots, bridges)) or \
1032 | +            any(k not in slots and (k.startswith("bridge_") or k == "takeaway") for k in by if k):
1033 |          out.append("bridges")
1034 |      for k in ("title", "caption"):
1035 |          if by.get(k) != pk.get(k):
1036 | @@ -76,8 +95,8 @@ def line_problems(pk):
1037 |  
1038 |  
1039 |  def to_pin(pk, run_name):
1040 | -    problems = gate_problems(pk.get("gates")) + [f"{x}: the gated line differs from the one shipped"
1041 | -                                                 for x in line_problems(pk)]
1042 | +    problems = gate_problems(pk.get("gates"), required_gates(pk)) + [f"{x}: the gated line differs from the one shipped"
1043 | +                                                                     for x in line_problems(pk)]
1044 |      if problems:
1045 |          raise PinRefused("the package's gates do not authorise a pin: " + "; ".join(problems))
1046 |      segs = []
1047 | @@ -100,8 +119,13 @@ def to_pin(pk, run_name):
1048 |                                  "signoff_expected": pk["vo"]["signoff"],
1049 |                                  "title": pk["title"], "caption": pk["caption"],
1050 |                                  "hook_first_words": pk["hook_first_words"],
1051 | -                                "vo_jobs": {"intro": "context", **{f"bridge_{i + 1}": "connection"
1052 | -                                                                   for i in range(len(pk["vo"]["bridges"]))}},
1053 | +                                "vo_jobs": {**({"intro": "context" if pk.get("shape") != "medley" else "connection"}
1054 | +                                               if pk["vo"]["intro"] else {}),
1055 | +                                            **{s: "takeaway" if s == "takeaway" else "connection"
1056 | +                                               for s in bridge_slots(pk)}},
1057 | +                                "shape": pk.get("shape"),
1058 | +                                "bridge": pk.get("bridge"),
1059 | +                                "supply_exception": pk.get("supply_exception"),
1060 |                                  "gates": pk["gates"],
1061 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
1062 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
1063 | diff --git a/pipeline/providers.py b/pipeline/providers.py
1064 | index 67dfd391..6e8220ca 100644
1065 | --- a/pipeline/providers.py
1066 | +++ b/pipeline/providers.py
1067 | @@ -221,6 +221,17 @@ class OpenAIBackend(Backend):
1068 |          return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1069 |  
1070 |  
1071 | +def _num(x):
1072 | +    import math
1073 | +    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and x >= 0
1074 | +
1075 | +
1076 | +def _reported(usd):
1077 | +    """{"usd_reported": the vendor's own figure for this call} when the reply carries one, else {} (the ledger then keeps
1078 | +    the price-table estimate for it, labelled as an estimate)."""
1079 | +    return {"usd_reported": round(float(usd), 8)} if _num(usd) else {}
1080 | +
1081 | +
1082 |  class HeimdallBackend(OpenAIBackend):
1083 |      """Heimdall: an OpenAI-compatible multi-model API (HEIMDALL_API_KEY) at the config's base_url. JSON is asked for in
1084 |      words only (its models differ in json_object support); its /credits endpoint feeds the 90% tripwire."""
1085 | @@ -246,7 +257,8 @@ class HeimdallBackend(OpenAIBackend):
1086 |              text = j["choices"][0]["message"].get("content") or ""
1087 |          except (KeyError, IndexError, TypeError):
1088 |              raise RequestRejected("heimdall: no choices") from None
1089 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)}, time.time() - t0
1090 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0)},
1091 | +                          **_reported(u.get("cost"))), time.time() - t0
1092 |  
1093 |      def credits(self):
1094 |          """(total_usage, total_credits) in USD from GET /credits, or None when it cannot be read."""
1095 | @@ -285,8 +297,9 @@ class XAIBackend(Backend):
1096 |              text = j["choices"][0]["message"].get("content") or ""
1097 |          except (KeyError, IndexError, TypeError):
1098 |              raise RequestRejected("xai: no choices") from None
1099 | -        return text, {"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning}, \
1100 | -            time.time() - t0
1101 | +        ticks = u.get("cost_in_usd_ticks")                    # the vendor's own cost: 1 USD = 1e10 ticks
1102 | +        return text, dict({"in": int(u.get("prompt_tokens") or 0), "out": int(u.get("completion_tokens") or 0) + reasoning},
1103 | +                          **_reported(ticks / 1e10 if _num(ticks) else None)), time.time() - t0
1104 |  
1105 |  
1106 |  class AnthropicBackend(Backend):
1107 | @@ -575,6 +588,13 @@ class Router:
1108 |                  r = d["by_role"].setdefault(role, {"calls": 0, "usd_estimate": 0.0})
1109 |                  r.update(calls=r["calls"] + 1, usd_estimate=round(r["usd_estimate"] + usd, 6))
1110 |                  d.update(calls=d["calls"] + 1, usd_estimate=round(d["usd_estimate"] + usd, 6))
1111 | +                if _num(usage.get("usd_reported")):    # the vendor's own figure (xAI ticks, Heimdall usage.cost)
1112 | +                    rep = float(usage["usd_reported"])
1113 | +                    b.update(usd_reported=round(b.get("usd_reported", 0.0) + rep, 8),
1114 | +                             reported_calls=b.get("reported_calls", 0) + 1)
1115 | +                    d["usd_reported"] = round(d.get("usd_reported", 0.0) + rep, 8)
1116 | +                else:                                  # no vendor figure: the estimate stands for this call
1117 | +                    d["usd_unreported_estimate"] = round(d.get("usd_unreported_estimate", 0.0) + usd, 6)
1118 |              self._save(d)
1119 |  
1120 |      def reject(self, reply, why=""):
1121 | diff --git a/tests/moments/test_moments.py b/tests/moments/test_moments.py
1122 | index 4535455d..7a41a3a3 100644
1123 | --- a/tests/moments/test_moments.py
1124 | +++ b/tests/moments/test_moments.py
1125 | @@ -129,13 +129,6 @@ class TestPackageUsable(unittest.TestCase):
1126 |          self.assertEqual(PK.signoff(segs, ctx), "Clips today from DataDash, Natalie Brunell, and Yahoo Finance. "
1127 |                                                  "Go follow them for more. Links are below.")
1128 |  
1129 | -    def test_the_plain_title_never_cuts_a_name(self):
1130 | -        ctx = E.Context(NOW, REG)
1131 | -        segs = [pm("h", "Averyveryverylongchannelname One", 10.0), pm("c1", "Averyveryverylongchannelname Two", 15.0),
1132 | -                pm("c2", "Averyveryverylongchannelname Three", 15.0)]
1133 | -        title = PK.plain_vo(segs, ctx)[2]["text"]
1134 | -        self.assertLessEqual(len(title), 70)
1135 | -        self.assertTrue(title.endswith(("and others", "Two", "One")), title)
1136 |  
1137 |  
1138 |  if __name__ == "__main__":
1139 | diff --git a/tests/package/pin_and_verify.py b/tests/package/pin_and_verify.py
1140 | index 4a478de9..37f12287 100644
1141 | --- a/tests/package/pin_and_verify.py
1142 | +++ b/tests/package/pin_and_verify.py
1143 | @@ -7,7 +7,9 @@ Checks on the REAL pin: package_pin.to_pin authorises it (every required gate ex
1144 |  equal the VO / title / caption); pinned.validate_schema accepts it; pinned.build_edl (moments_vo) carries the VO
1145 |  (a line after every clip, the last included), the ONE title and caption and the seal; edl_rules.rule_r4 (R4 for
1146 |  moments) passes on the pin's own segment durations.
1147 | -Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]"""
1148 | +Where the factory copy has edl_rules.rule_r11 (law L-y's VO shape), it runs too.
1149 | +Usage: python3 tests/package/pin_and_verify.py PACKAGE.json RUN_NAME OUT_DIR [MAIN_TREE]
1150 | +(MAIN_TREE: any directory holding pipeline/{pinned,edl_rules,config}.py, e.g. a `git show` export of a branch)"""
1151 |  import json
1152 |  import os
1153 |  import shutil
1154 | @@ -61,7 +63,11 @@ def main(argv=None):
1155 |          ok, why = edl_rules.rule_r4(edl)
1156 |          print(f"PIN {path}\n  story_id {pin['story_id']} seal {mp['package_sha256']}")
1157 |          print(f"  pinned.validate_schema: OK; build_edl (moments_vo): VO, title, caption, seal carried")
1158 | -        print(f"  edl_rules.rule_r4 (deployed): {'PASS' if ok else 'FAIL'}: {why}")
1159 | +        print(f"  edl_rules.rule_r4 ({main_tree}): {'PASS' if ok else 'FAIL'}: {why}")
1160 | +        if hasattr(edl_rules, "rule_r11"):                  # law L-y's VO shape, where that factory has it
1161 | +            ok11, why11 = edl_rules.rule_r11(edl)
1162 | +            print(f"  edl_rules.rule_r11 ({main_tree}): {'PASS' if ok11 else 'FAIL'}: {why11}")
1163 | +            ok = ok and ok11
1164 |          return 0 if ok else 1
1165 |      finally:
1166 |          shutil.rmtree(tmp, ignore_errors=True)
1167 | diff --git a/tests/package/proof_ly.py b/tests/package/proof_ly.py
1168 | new file mode 100644
1169 | index 00000000..a18caa32
1170 | --- /dev/null
1171 | +++ b/tests/package/proof_ly.py
1172 | @@ -0,0 +1,245 @@
1173 | +#!/usr/bin/env python3
1174 | +"""ORCHESTRATOR ORDER 20:30 ET Nov 12 (law L-y, VOICEOVER IS MINIMAL): re-run tonight's universe and the saved ones
1175 | +through the packager's new default, the MEDLEY (pipeline/package.py build()). The table goes to the top of STATE:
1176 | +- packages per universe;
1177 | +- how many needed zero bridges and how many needed one;
1178 | +- the gate pass rate on the single takeaway line;
1179 | +- time and dollars per package.
1180 | +The top package of the newest universe becomes a sealed pin (MOMENTS_PIN_LY.json).
1181 | +
1182 | +LEGS (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"). The probe at
1183 | +20:32 ET found Anthropic "credit balance is too low" (HTTP 400) and OpenAI 429 credit_balance_exhausted, so both stay
1184 | +out. Local gemma runs on GPU0, which this builder never uses (L-r, the session's standing order), so every local leg
1185 | +is out too. What is left:
1186 | +- the writer (angle + takeaway) is Heimdall: deepseek-v4.1-flash, then qwen3.8-27b. This is the config's own
1187 | +  angle_write order once the frozen vendors drop out.
1188 | +- every verdict avoids the writer's vendor (L-x), so it runs on xAI grok-4.20.
1189 | +- the second recogniser is ElevenLabs scribe_v1.
1190 | +CPU and network only. The inputs are read-only: the saved runs and the main store's transcripts.
1191 | +
1192 | +SPEND: a ledger of this order's own (tests/package/proof/SPEND_LY.json) holds the price-table estimate beside the
1193 | +vendors' own figures (xAI cost_in_usd_ticks, Heimdall usage.cost; providers.py). Its guard is LY_LIMIT_USD by the
1194 | +estimate (an upper bound). No budget was stated at 20:30; the cap is the builder's, and STATE says so.
1195 | +
1196 | +Usage: python3 tests/package/proof_ly.py --runs fresh_20261112_050611 ... [--table]
1197 | +"""
1198 | +import argparse
1199 | +import hashlib
1200 | +import json
1201 | +import os
1202 | +import subprocess
1203 | +import sys
1204 | +import time
1205 | +
1206 | +HERE = os.path.dirname(os.path.abspath(__file__))
1207 | +REPO = os.path.dirname(os.path.dirname(HERE))
1208 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1209 | +sys.path.insert(0, os.path.join(REPO, "tests", "select_by_id"))
1210 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1211 | +import moments as M  # noqa: E402
1212 | +import package as PK  # noqa: E402
1213 | +import package_pin  # noqa: E402
1214 | +import proof_moments as PM  # noqa: E402
1215 | +import providers as P  # noqa: E402
1216 | +
1217 | +REPLIES = os.path.join(HERE, "fixtures", "replies")
1218 | +OUT = os.path.join(HERE, "proof")
1219 | +SPEND = os.path.join(OUT, "SPEND_LY.json")
1220 | +LY_LIMIT_USD = 40.0                # the price-table estimate (an upper bound): xAI's own figure ran 1/8 of it on
1221 | +                                   # this order's first calls (estimate $0.636 vs reported $0.078 for 3 grok calls),
1222 | +                                   # so about $5 real; each paid call also RESERVES its upper bound (~$0.26-0.96)
1223 | +                                   # while in flight, and three workers run concurrently
1224 | +TABLE = os.path.join(REPO, "docs", "audits", "parallel", "pp-selectid_LY_RERUN.md")
1225 | +RUNS = ("fresh_20261112_050611", "fresh_20261112_013452", "fresh_20261112_001448", "fresh_20261111_213954",
1226 | +        "fresh_20261111_192645", "fresh_20261111_190259", "fresh_20261110_093150", "fresh_20261107_080503",
1227 | +        "fresh_20261107_065702", "fresh_20261106_213852")           # newest first: the first is tonight's
1228 | +NEWEST = RUNS[0]
1229 | +FROZEN = ("local:", "anthropic:", "openai:", "openai_stt:")         # GPU0 (never this builder's); out of credit 20:32
1230 | +WRITERS = ["heimdall:deepseek/deepseek-v4.1-flash", "heimdall:qwen/qwen3.8-27b"]
1231 | +SCRATCH = "/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad"
1232 | +
1233 | +
1234 | +def chains():
1235 | +    """Every role's configured chain without the frozen legs; the writer = two Heimdall families."""
1236 | +    cfg = json.load(open(P.CONFIG))
1237 | +    out = {r: [b for b in v["chain"] if not b.startswith(FROZEN)] for r, v in cfg["roles"].items()}
1238 | +    out["angle_write"] = list(WRITERS)
1239 | +    return out
1240 | +
1241 | +
1242 | +def ledger():
1243 | +    try:
1244 | +        d = json.load(open(SPEND))
1245 | +    except (OSError, ValueError):
1246 | +        d = {}
1247 | +    est = float(d.get("usd_estimate", 0.0))
1248 | +    best = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
1249 | +    return est, best, d
1250 | +
1251 | +
1252 | +def meter(router):
1253 | +    """THIS process's own spend, from every call the router accounts (Router._settle). The shared ledger's total moves
1254 | +    with the other workers too, so a per-package budget read from it would charge one universe for another's calls.
1255 | +    -> {"est": price-table estimate, "best": the vendor's own figure where reported, else the estimate}."""
1256 | +    import threading
1257 | +    tot, lock, settle = {"est": 0.0, "best": 0.0}, threading.Lock(), router._settle
1258 | +
1259 | +    def _settle(key, backend=None, usage=None, usd=0.0, role=""):
1260 | +        settle(key, backend, usage, usd, role)
1261 | +        if backend is not None:
1262 | +            rep = (usage or {}).get("usd_reported")
1263 | +            with lock:
1264 | +                tot["est"] += float(usd or 0.0)
1265 | +                tot["best"] += float(rep) if P._num(rep) else float(usd or 0.0)
1266 | +    router._settle = _settle
1267 | +    return tot
1268 | +
1269 | +
1270 | +def code_sha():
1271 | +    """The code this run used: HEAD plus the working tree's diff of pipeline/ and this driver (the results name it)."""
1272 | +    head = subprocess.run(["git", "-C", REPO, "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
1273 | +    diff = subprocess.run(["git", "-C", REPO, "diff", "HEAD", "--", "pipeline", "tests/package"], capture_output=True).stdout
1274 | +    return f"{head}+{hashlib.sha256(diff).hexdigest()[:12]}" if diff else head
1275 | +
1276 | +
1277 | +def run_one(run, router, work_dir, log, own):
1278 | +    rec_m = json.load(open(os.path.join(PM.OUT, run, "moments.json")))
1279 | +    words, captions, ctx, saved = PM.universe_sources(run)
1280 | +    sources = {s.video_id: s for s in words}
1281 | +    e0, b0 = own["est"], own["best"]
1282 | +    t0 = time.time()
1283 | +    res = PK.build(router, rec_m["moments"], sources, ctx, delivered=(), optout=M.optout_ids(), log=log,
1284 | +                   work_dir=work_dir, store=os.path.join(OUT, run, "step_a.json"), spend=lambda: own["est"])
1285 | +    e1, b1 = own["est"], own["best"]
1286 | +    res.update(run=run, seconds=round(time.time() - t0, 1), usd_estimate=round(e1 - e0, 4),
1287 | +               usd_best_known=round(b1 - b0, 4), code=code_sha(), chains=router.chains,
1288 | +               at=time.strftime("%Y-%m-%d %H:%M:%S %Z"))
1289 | +    os.makedirs(os.path.join(OUT, run), exist_ok=True)
1290 | +    if res["package"]:
1291 | +        pk = res["package"]
1292 | +        pk["usd_best_known"] = res["usd_best_known"]
1293 | +        try:
1294 | +            path, pin = package_pin.write_pin(pk, run, os.path.join(OUT, run), name="MOMENTS_PIN_LY.json")
1295 | +            res["pin"] = {"path": os.path.relpath(path, REPO), "story_id": pin["story_id"],
1296 | +                          "package_sha256": pin["moments_package"]["package_sha256"]}
1297 | +            log(f"{run}: PACKAGE ({res['seconds']} s, ${res['usd_estimate']} estimate, ${res['usd_best_known']} best "
1298 | +                f"known) pin {path}")
1299 | +        except package_pin.PinRefused as e:                # recorded, never a pass; the next universe still runs
1300 | +            res["pin_refused"] = str(e)
1301 | +            log(f"{run}: PIN REFUSED: {e}")
1302 | +    else:
1303 | +        log(f"{run}: no package ({res.get('why_none')}); usable {res['usable']}, cleared "
1304 | +            f"{res['prescreen']['cleared']}")
1305 | +    json.dump(res, open(os.path.join(OUT, run, "package_ly.json"), "w"), indent=1, default=str)
1306 | +    return res
1307 | +
1308 | +
1309 | +def table():
1310 | +    rows = ["| universe | usable / cleared step A | line-ups judged on the clips alone (passed) | package | segments, "
1311 | +            "seconds of clips | bridges | takeaways: passed / judged / written (first write: passed / judged) | runtime estimate | time | "
1312 | +            "$ estimate / $ best known (*) | why none |", "|---|---|---|---|---|---|---|---|---|---|---|"]
1313 | +    tot = {"universes": 0, "packages": 0, "zero": 0, "one": 0, "passed": 0, "judged": 0, "first_passed": 0,
1314 | +           "first_judged": 0, "s": [], "est": [], "best": [], "framing": 0, "flagged_lineups": 0, "lineups": 0,
1315 | +           "budget_stops": []}
1316 | +    for run in RUNS:
1317 | +        f = os.path.join(OUT, run, "package_ly.json")
1318 | +        if not os.path.exists(f):
1319 | +            rows.append(f"| {run} | not run | | | | | | | | | |")
1320 | +            continue
1321 | +        r = json.load(open(f))
1322 | +        tot["universes"] += 1
1323 | +        tried = [t for t in r.get("tried") or [] if t.get("medley") is not None]
1324 | +        med_ok = sum(1 for t in tried if t.get("medley_ok") is True)
1325 | +        if not r.get("package") and (r.get("budget_stop") or "budget" in (r.get("why_none") or "")):
1326 | +            tot["budget_stops"].append(run)
1327 | +        tot["lineups"] += len(tried)
1328 | +        tot["flagged_lineups"] += sum(1 for t in tried if t.get("medley_ok") and t["medley"].get("flagged"))
1329 | +        takes = r.get("takeaways") or []
1330 | +        tot["framing"] += sum(1 for x in takes if x.get("context_framing"))
1331 | +        judged = [x for x in takes if x.get("passed") is not None]
1332 | +        firsts = [x for x in judged if x.get("write") == 1]
1333 | +        tot["passed"] += sum(1 for x in judged if x["passed"])
1334 | +        tot["judged"] += len(judged)
1335 | +        tot["written"] = tot.get("written", 0) + len(takes)
1336 | +        tot["first_passed"] += sum(1 for x in firsts if x["passed"])
1337 | +        tot["first_judged"] += len(firsts)
1338 | +        pk = r.get("package")
1339 | +        if pk:
1340 | +            nb = 0 if not pk.get("bridge") else 1
1341 | +            tot["packages"] += 1
1342 | +            tot["zero" if nb == 0 else "one"] += 1
1343 | +            tot["s"].append(r["seconds"])
1344 | +            tot["est"].append(r.get("usd_estimate") or 0.0)
1345 | +            tot["best"].append(r.get("usd_best_known") or 0.0)
1346 | +            segs = f"{len(pk['segments'])}, {sum(s['duration_s'] for s in pk['segments']):.1f} s"
1347 | +            bridge = "0" if nb == 0 else f"1 ({pk['bridge']['join']}: {pk['bridge']['why']})".replace("|", "/")
1348 | +            pkg, rt, why = f"YES: \"{pk['title']}\"".replace("|", "/"), f"{pk['runtime_s_estimate']} s", ""
1349 | +        else:
1350 | +            segs = bridge = rt = "-"
1351 | +            pkg = "no"
1352 | +            why = (r.get("why_none") or "; ".join(f"angle {t['angle']}: {t.get('why') or '-'}" for t in r.get("tried") or [])
1353 | +                   )[:240].replace("|", "/")
1354 | +        rows.append(f"| {run} | {r['usable']} / {r['prescreen']['cleared']} | {len(tried)} ({med_ok}) | {pkg} | {segs} | "
1355 | +                    f"{bridge} | {sum(1 for x in judged if x['passed'])} / {len(judged)} / {len(takes)} "
1356 | +                    f"({sum(1 for x in firsts if x['passed'])} / {len(firsts)}) | {rt} | {r['seconds']} s | "
1357 | +                    f"${r.get('usd_estimate')} / ${r.get('usd_best_known')} | {why} |")
1358 | +    n = tot["packages"]
1359 | +    mean = lambda xs: (sum(xs) / len(xs)) if xs else 0.0
1360 | +    _, _, d = ledger()
1361 | +    summary = (f"\n**Totals:**\n"
1362 | +               f"- {tot['universes']} universes run; {n} packages.\n"
1363 | +               f"- Bridges: {tot['zero']} packages needed none, {tot['one']} needed one.\n"
1364 | +               f"- Takeaways written: {tot.get('written', 0)}; judged by their own gates: {tot['judged']} (a write "
1365 | +               f"stopped first by another gate, the runtime, the shape or a lost clip, is not judged).\n"
1366 | +               f"- The takeaway line passed its gates in {tot['passed']} of {tot['judged']} judged writes "
1367 | +               f"({tot['first_passed']} of {tot['first_judged']} on the first write); context-integrity failures "
1368 | +               f"caused by the VO's framing, recorded beside it: {tot['framing']} writes.\n"
1369 | +               f"- Line-ups judged on the clips alone: {tot['lineups']}; of those that passed, {tot['flagged_lineups']} "
1370 | +               f"had one join a viewer could not follow (the bridge offered).\n"
1371 | +               f"- Universes without a package because the per-package budget (05:25 item 5, twice) stopped the "
1372 | +               f"search before every angle was tried: {len(tot['budget_stops'])} {tot['budget_stops'] or ''}.\n"
1373 | +               f"- Per package: {mean(tot['s']):.0f} s mean, ${mean(tot['est']):.2f} estimate, "
1374 | +               f"${mean(tot['best']):.2f} best known.\n"
1375 | +               f"- This order's ledger: ${d.get('usd_estimate', 0):.2f} estimate; vendor-reported "
1376 | +               f"${d.get('usd_reported', 0):.4f} + unreported calls' estimate ${d.get('usd_unreported_estimate', 0):.2f}.\n")
1377 | +    note = ("\n(*) $ estimate: the price table's upper bound (the spend guard reads it). $ best known: the vendor's own "
1378 | +            "figure where the reply carries one (xAI cost_in_usd_ticks, Heimdall usage.cost), else that call's estimate "
1379 | +            "(ElevenLabs STT reports none).\n")
1380 | +    text = ("# pp-selectid: the L-y medley re-run (generated by tests/package/proof_ly.py --table)\n\n" +
1381 | +            "\n".join(rows) + "\n" + note + summary)
1382 | +    open(TABLE, "w").write(text)
1383 | +    return text
1384 | +
1385 | +
1386 | +def main(argv=None):
1387 | +    ap = argparse.ArgumentParser()
1388 | +    ap.add_argument("--runs", nargs="+", default=list(RUNS))
1389 | +    ap.add_argument("--table", action="store_true", help="only (re)write the table from the saved results")
1390 | +    ap.add_argument("--work-dir", default=os.path.join(SCRATCH, "lv2"))
1391 | +    a = ap.parse_args(argv)
1392 | +    if a.table:
1393 | +        print(table())
1394 | +        return 0
1395 | +    router = P.Router(env_path=PM.PS.ENV, record_dir=REPLIES, spend_path=SPEND, limit_usd=LY_LIMIT_USD, chains=chains())
1396 | +    own = meter(router)
1397 | +    os.makedirs(a.work_dir, exist_ok=True)
1398 | +    for run in a.runs:
1399 | +        os.makedirs(os.path.join(OUT, run), exist_ok=True)
1400 | +        logf = open(os.path.join(OUT, run, "package_ly.log"), "a")
1401 | +        say = lambda s: (print(f"[{run}] {s}", flush=True), logf.write(s + "\n"), logf.flush())
1402 | +        say(f"=== {time.strftime('%H:%M:%S %Z')} L-y medley build, code {code_sha()}, chains {json.dumps(router.chains)}")
1403 | +        try:
1404 | +            run_one(run, router, a.work_dir, say, own)
1405 | +        except P.SpendLimit as e:
1406 | +            say(f"STOPPED: {e}")
1407 | +            break
1408 | +        finally:
1409 | +            logf.close()
1410 | +    if router.notices:
1411 | +        print("NOTICES:", router.notices)
1412 | +    print(table())
1413 | +    return 0
1414 | +
1415 | +
1416 | +if __name__ == "__main__":
1417 | +    sys.exit(main())
1418 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
1419 | new file mode 100644
1420 | index 00000000..88eda054
1421 | --- /dev/null
1422 | +++ b/tests/package/test_medley.py
1423 | @@ -0,0 +1,571 @@
1424 | +#!/usr/bin/env python3
1425 | +"""L-y VOICEOVER IS MINIMAL (orchestrator 20:30 ET Nov 12): the packager's MEDLEY, offline.
1426 | +
1427 | +- The arithmetic: the clips' seconds that let ONE takeaway land the factory's estimate in 60-70 s, and the takeaway's
1428 | +  word budget, which lands it there.
1429 | +- The line-up: the hook + 2-4 clips in the proposer's play order, one per channel (a repeat only as the recorded supply
1430 | +  exception).
1431 | +- The clips-ALONE verdict's contract.
1432 | +- The writer's contract: a bridge only at the flagged join.
1433 | +- ly_shape's must-fail cases.
1434 | +- The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
1435 | +"""
1436 | +import json
1437 | +import os
1438 | +import sys
1439 | +import unittest
1440 | +
1441 | +HERE = os.path.dirname(os.path.abspath(__file__))
1442 | +REPO = os.path.dirname(os.path.dirname(HERE))
1443 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
1444 | +sys.path.insert(0, os.path.join(REPO, "tests", "eligibility"))
1445 | +sys.path.insert(0, os.path.join(REPO, "tests", "moments"))
1446 | +sys.path.insert(0, HERE)
1447 | +import eligibility as E  # noqa: E402
1448 | +import package as PK  # noqa: E402
1449 | +import package_pin  # noqa: E402
1450 | +from config import BRIDGE_WORD_CAP  # noqa: E402
1451 | +from test_eligibility import NOW, REG  # noqa: E402
1452 | +from test_gates import Canned  # noqa: E402
1453 | +from test_moments import pm  # noqa: E402
1454 | +
1455 | +W = lambda n: " ".join(["word"] * n)
1456 | +
1457 | +
1458 | +def angle(ms, hook, text="Nobody controls Bitcoin."):
1459 | +    return {"angle": text, "moments": ms, "hook": hook, "support": {m: "x" for m in ms}}
1460 | +
1461 | +
1462 | +def verdict(labs, flagged=(), ratings=None, line="Nobody can change the rules of Bitcoin."):
1463 | +    js = PK.joins(labs)
1464 | +    return {"through_line": line, "clips": {lb: (ratings or {}).get(lb, 5) for lb in labs},
1465 | +            "joins": {j: {"followable": j not in flagged, "why": "the next speaker's 'it' has no referent"
1466 | +                          if j in flagged else "same subject"} for j in js}}
1467 | +
1468 | +
1469 | +def medley_pk(n=3, bridge=None, after=None, flagged=(), measured=True, chans=None, supply=None, intro=None):
1470 | +    """A medley package the shape check reads: n segments; the takeaway after the last clip; an optional bridge."""
1471 | +    labs = PK.labels(n)
1472 | +    segs = [{"label": lb, "channel_id": (chans or "ABCDEFG")[i], "duration_s": 12.0, "text": f"Bitcoin {lb}."}
1473 | +            for i, lb in enumerate(labs)]
1474 | +    bridges, aft = (["B " + W(5)] if bridge else []) + [W(20)], ([after] if bridge else []) + [n - 1]
1475 | +    return {"shape": "medley", "segments": segs,
1476 | +            "vo": {"intro": intro, "bridges": bridges, "bridges_after_clip": aft, "signoff": "S"},
1477 | +            "medley": {"measured": measured, "flagged": list(flagged)},
1478 | +            "bridge": {"why": bridge, "text": intro or (bridges[0] if bridge else None),
1479 | +                       "confirmed_by": {"join": "x", "why": "y"}} if bridge or intro else None,
1480 | +            "supply_exception": supply}
1481 | +
1482 | +
1483 | +class TestMedleyArithmetic(unittest.TestCase):
1484 | +    def test_the_medley_seconds_let_one_takeaway_land_60_to_70(self):
1485 | +        lo, hi = PK.medley_content_range()
1486 | +        self.assertEqual((lo, hi), (32.7, 51.5))          # 60 - 14.30 - (30 / 2.5 + 1); 70 - 14.30 - (8 / 2.5 + 1)
1487 | +        seg = lambda c: [{"duration_s": c}]
1488 | +        self.assertAlmostEqual(PK.runtime(seg(lo), [W(PK.MOMENTS_TAKEAWAY_WORD_CAP)]), 60.0, places=2)
1489 | +        self.assertAlmostEqual(PK.runtime(seg(hi), [W(PK.LY_TAKEAWAY_MIN_WORDS)]), 70.0, places=2)
1490 | +        lo1, hi1 = PK.medley_content_range(n_bridges=1)
1491 | +        self.assertAlmostEqual(lo - lo1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1492 | +        self.assertAlmostEqual(hi - hi1, PK.LY_BRIDGE_WORDS / 2.5 + 1.0, places=2)
1493 | +
1494 | +    def test_the_takeaway_budget_lands_the_estimate_and_never_passes_the_caps(self):
1495 | +        aimed = 0
1496 | +        for c10 in range(300, 560):
1497 | +            c = c10 / 10
1498 | +            b = PK.takeaway_budget(c)
1499 | +            if b is None:
1500 | +                self.assertTrue(c > PK.medley_content_range()[1] or c < PK.medley_content_range()[0], c)
1501 | +                continue
1502 | +            lo, hi = b
1503 | +            self.assertTrue(PK.LY_TAKEAWAY_MIN_WORDS <= lo <= hi <= PK.MOMENTS_TAKEAWAY_WORD_CAP, (c, b))
1504 | +            for w in (lo, hi):
1505 | +                est = PK.runtime([{"duration_s": c}], [W(w)])
1506 | +                self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, w, est))
1507 | +                p = {"segments": [{"duration_s": c, "channel": "A"}, {"duration_s": 0.0, "channel": "B"}],
1508 | +                     "vo": {"intro": None, "bridges": [W(w)], "bridges_after_clip": [1]}, "runtime_s_estimate": est}
1509 | +                self.assertTrue(PK.r4(p)[0], (c, w, PK.r4(p)[1]))
1510 | +            aimed += all(PK.LY_AIM_S[0] <= PK.runtime([{"duration_s": c}], [W(w)]) <= PK.LY_AIM_S[1] for w in (lo, hi))
1511 | +        self.assertGreater(aimed, 100)                    # most clip lengths land the aim (61.5-68.5 s)
1512 | +        self.assertIsNone(PK.takeaway_budget(60.0))       # too many seconds of clips: no takeaway lands 70 s
1513 | +        b0, b1 = PK.takeaway_budget(40.0), PK.takeaway_budget(40.0, other=[W(10)])
1514 | +        self.assertLess(b1[1], b0[1])                     # a bridge's seconds come off the takeaway
1515 | +
1516 | +
1517 | +class TestMedleyLineup(unittest.TestCase):
1518 | +    def test_the_hook_and_clips_in_the_proposers_order_one_per_channel(self):
1519 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1520 | +                                          pm("z", "D", 12.0), pm("e", "A", 14.0))}
1521 | +        seg = PK.lineup_for(angle(["h", "y", "x", "z", "e"], "h"), by)
1522 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "y", "x"])        # the earliest that fit, in that order
1523 | +        self.assertTrue(PK.medley_content_range()[0] <= sum(m["duration_s"] for m in seg) <= PK.medley_content_range()[1])
1524 | +
1525 | +    def test_more_clips_when_two_do_not_fill_the_medley(self):
1526 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 9.0), pm("x", "B", 9.0), pm("y", "C", 9.0), pm("z", "D", 9.0))}
1527 | +        seg = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by)
1528 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "y", "z"])   # 36 s: the hook + 3 clips
1529 | +        short = {k: dict(v, duration_s=6.0) for k, v in by.items()}
1530 | +        self.assertIsNone(PK.lineup_for(angle(["h", "x", "y", "z"], "h"), short))   # 24 s: no medley fits
1531 | +
1532 | +    def test_a_channel_twice_only_as_the_supply_exception_and_from_two_videos(self):
1533 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0),
1534 | +                                          pm("e", "A", 13.0))}
1535 | +        a = angle(["h", "x", "y", "e"], "h")
1536 | +        self.assertIsNone(PK.lineup_for(a, by))                                    # one per channel cannot fill it
1537 | +        seg = PK.lineup_for(a, by, repeat_ok=True)
1538 | +        self.assertEqual([m["moment_id"] for m in seg], ["h", "x", "e"])
1539 | +        same_video = dict(by, e=dict(by["e"], video_id=by["h"]["video_id"]))
1540 | +        self.assertIsNone(PK.lineup_for(a, same_video, repeat_ok=True))           # never two clips of one video
1541 | +
1542 | +
1543 | +class TestClipsAloneVerdict(unittest.TestCase):
1544 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1545 | +    LABS = ["hook", "clip_01", "clip_02"]
1546 | +
1547 | +    def run_it(self, reply):
1548 | +        r = Canned(coherence_verdict=[reply])
1549 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1550 | +        return ok, v, r
1551 | +
1552 | +    def test_no_narration_in_the_prompt_and_the_writers_vendor_avoided(self):
1553 | +        r = Canned(coherence_verdict=[verdict(self.LABS)])
1554 | +        prompts = []
1555 | +        call = r.call
1556 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1557 | +        ok, v = PK.medley(r, self.SEGS, E.Context(NOW, REG), {"heimdall"}, writer_family={"deepseek"})
1558 | +        self.assertTrue(ok)
1559 | +        self.assertEqual(v["flagged"], [])
1560 | +        self.assertNotIn("VOICE-OVER", prompts[0])
1561 | +        self.assertNotIn("TITLE", prompts[0])
1562 | +        self.assertIn('"hook -> clip_01"', prompts[0])
1563 | +        self.assertEqual(r.calls[0], ("coherence_verdict", {"heimdall"}, {"deepseek"}))
1564 | +
1565 | +    def test_one_unfollowable_join_passes_flagged_and_two_fail(self):
1566 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["clip_01 -> clip_02"]))
1567 | +        self.assertTrue(ok)
1568 | +        self.assertEqual(v["flagged"], ["clip_01 -> clip_02"])
1569 | +        ok, v, _ = self.run_it(verdict(self.LABS, flagged=["hook -> clip_01", "clip_01 -> clip_02"]))
1570 | +        self.assertFalse(ok)                              # two bridges would be needed: the line-up is wrong (L-y 2)
1571 | +
1572 | +    def test_no_through_line_or_a_weak_clip_fails(self):
1573 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="none"))[0])
1574 | +        self.assertFalse(self.run_it(verdict(self.LABS, line="Bitcoin."))[0])
1575 | +        self.assertFalse(self.run_it(verdict(self.LABS, ratings={"clip_02": 3}))[0])
1576 | +
1577 | +    def test_out_of_contract_is_not_measured_and_rejected(self):
1578 | +        good = verdict(self.LABS)
1579 | +        for bad in (dict(good, joins={"hook -> clip_01": good["joins"]["hook -> clip_01"]}),      # a join missing
1580 | +                    dict(good, joins=dict(good["joins"], **{"clip_02 -> hook": {"followable": True, "why": ""}})),
1581 | +                    dict(good, joins={j: {"followable": "yes", "why": ""} for j in good["joins"]}),
1582 | +                    dict(good, vo_point=5),
1583 | +                    dict(good, clips={"hook": 5, "clip_01": 5})):
1584 | +            ok, v, r = self.run_it(bad)
1585 | +            self.assertFalse(ok)
1586 | +            self.assertFalse(v["measured"])
1587 | +            self.assertIsNone(v["flagged"])
1588 | +            self.assertEqual(r.rejected, ["fake:coherence_verdict"])
1589 | +
1590 | +
1591 | +class TestWriteTakeaway(unittest.TestCase):
1592 | +    SEGS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
1593 | +
1594 | +    def write(self, reply, join=None):
1595 | +        r = Canned(angle_write=[reply])
1596 | +        return PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {}, join), r
1597 | +
1598 | +    def lines(self, bridge=None):
1599 | +        return {"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": bridge,
1600 | +                "title": {"text": "No ruler.", "cites": ["h"]}, "caption": {"text": "three clips", "cites": []}}
1601 | +
1602 | +    def test_no_bridge_unless_a_join_was_flagged(self):
1603 | +        (rep, f), _ = self.write(self.lines())
1604 | +        self.assertIsNone(f["bridge_after"])
1605 | +        with self.assertRaises(ValueError):
1606 | +            self.write(self.lines({"text": "Next, B.", "cites": ["x"], "why": "w"}))
1607 | +
1608 | +    def test_a_bridge_at_the_flagged_join_needs_its_reason_and_may_be_declined(self):
1609 | +        (rep, f), _ = self.write(self.lines({"text": "Next, B's show on keys.", "cites": ["x"], "why": "no referent"}),
1610 | +                                 join=(1, "the next speaker's 'it' has no referent"))
1611 | +        self.assertEqual(f["bridge_after"], 1)
1612 | +        (rep, f), _ = self.write(self.lines(None), join=(1, "w"))
1613 | +        self.assertIsNone(f["bridge_after"])                                       # declined: build re-lines
1614 | +        for bad in ({"text": "Next.", "cites": ["x"]}, {"text": "Next.", "cites": ["x"], "why": " "},
1615 | +                    {"text": "Next.", "cites": ["zz"], "why": "w"}):
1616 | +            with self.assertRaises(ValueError):
1617 | +                self.write(self.lines(bad), join=(1, "w"))
1618 | +
1619 | +    def test_an_offered_bridge_leaves_a_budget_that_holds_for_any_bridge_it_allows(self):
1620 | +        import re
1621 | +        fits = none = 0
1622 | +        for c10 in range(240, 520, 3):                     # audit 2030 C2 (qwen P1, grok P2), C3 (glm P0-2, qwen P2-2)
1623 | +            c = c10 / 10
1624 | +            segs = [dict(m, duration_s=c / 3) for m in self.SEGS]
1625 | +            r = Canned(angle_write=[self.lines()])
1626 | +            prompts = []
1627 | +            call = r.call
1628 | +            r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1629 | +            bb = PK.bridge_budget(c)
1630 | +            if bb is None:                                  # no bridge length fits: refused before any model call
1631 | +                with self.assertRaises(PK.NoBridgeFits):
1632 | +                    PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
1633 | +                self.assertEqual(prompts, [])
1634 | +                none += 1
1635 | +                continue
1636 | +            fits += 1
1637 | +            PK.write_takeaway(r, angle(["h", "x", "y"], "h"), segs, E.Context(NOW, REG), {}, join=(1, "w"))
1638 | +            lo, hi = map(int, re.search(r"one or two sentences, (\d+)-(\d+) words", prompts[0]).groups())
1639 | +            n = int(re.search(r"as short as it can be \(at most (\d+) words\)", prompts[0]).group(1))
1640 | +            self.assertEqual((n, (lo, hi)), bb)
1641 | +            self.assertTrue(PK.LY_BRIDGE_MIN_WORDS <= n <= PK.LY_BRIDGE_WORDS)
1642 | +            for t in (lo, hi):                              # EVERY bridge the writer may write lands 60-70 s
1643 | +                for bw in range(PK.LY_BRIDGE_MIN_WORDS, n + 1):
1644 | +                    est = PK.runtime([{"duration_s": c}], [W(t), W(bw)])
1645 | +                    self.assertTrue(PK.RUNTIME_S[0] <= est <= PK.RUNTIME_S[1], (c, t, bw, est))
1646 | +        self.assertGreater(fits, 50)
1647 | +        self.assertGreater(none, 0)                         # at the top of the medley's seconds no bridge fits
1648 | +
1649 | +    def test_the_prompt_asks_for_one_takeaway_inside_the_budget(self):
1650 | +        r = Canned(angle_write=[self.lines()])
1651 | +        prompts = []
1652 | +        call = r.call
1653 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), call(role, prompt, *a, **k))[1]
1654 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), self.SEGS, E.Context(NOW, REG), {})
1655 | +        lo, hi = PK.takeaway_budget(39.0)
1656 | +        self.assertIn(f"one or two sentences, {lo}-{hi} words", prompts[0])
1657 | +        self.assertNotIn("ONE JOIN NEEDS HELP", prompts[0])
1658 | +        self.assertNotIn('"intro"', prompts[0])
1659 | +
1660 | +
1661 | +class TestLyShape(unittest.TestCase):
1662 | +    def test_a_clean_medley_passes(self):
1663 | +        self.assertEqual(PK.ly_shape(medley_pk()), (True, []))
1664 | +        self.assertTrue(PK.ly_shape(medley_pk(n=5))[0])
1665 | +
1666 | +    def test_a_bridge_only_and_always_at_the_flagged_join_with_its_reason(self):
1667 | +        self.assertTrue(PK.ly_shape(medley_pk(n=4, bridge="no referent", after=2, flagged=["clip_02 -> clip_03"]))[0])
1668 | +        rec = {"why": "no referent", "text": "Next, B.", "confirmed_by": {"join": "hook -> clip_01"}}
1669 | +        self.assertTrue(PK.ly_shape(medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {"bridge": rec})[0])
1670 | +        must_fail = {
1671 | +            "bridge at an unflagged join": medley_pk(n=4, bridge="w", after=1, flagged=["clip_02 -> clip_03"]),
1672 | +            "bridge with nothing flagged": medley_pk(n=4, bridge="w", after=1),
1673 | +            "flagged join left unbridged": medley_pk(flagged=["clip_01 -> clip_02"]),
1674 | +            "bridge without its reason": medley_pk(n=4, bridge="", after=2, flagged=["clip_02 -> clip_03"]) | {
1675 | +                "vo": medley_pk(n=4, bridge="w", after=2)["vo"]},
1676 | +            "an intro with nothing flagged": medley_pk(intro="Here's the thing.") | {"bridge": {"why": "w"}},
1677 | +            "two bridges": medley_pk(n=4, intro="Next.", bridge="w", after=2,
1678 | +                                     flagged=["hook -> clip_01", "clip_02 -> clip_03"]),
1679 | +            "verdict not measured": medley_pk(measured=False),
1680 | +            "verdict missing": medley_pk() | {"medley": None},
1681 | +            # the factory's R11 (integrator, branch ly-shape): the record binds the line and carries its confirmation
1682 | +            "record text is not the line": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1683 | +                "bridge": dict(rec, text="Next, C.")},
1684 | +            "confirmation missing": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1685 | +                "bridge": dict(rec, confirmed_by=None)},
1686 | +            "confirmation a bool": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1687 | +                "bridge": dict(rec, confirmed_by=True)},
1688 | +            "confirmation empty": medley_pk(intro="Next, B.", flagged=["hook -> clip_01"]) | {
1689 | +                "bridge": dict(rec, confirmed_by={})},
1690 | +            "a record with no bridge line": medley_pk() | {"bridge": rec},
1691 | +        }
1692 | +        for why, pk in must_fail.items():
1693 | +            self.assertFalse(PK.ly_shape(pk)[0], why)
1694 | +
1695 | +    def test_the_takeaway_is_the_line_after_the_last_clip(self):
1696 | +        pk = medley_pk()
1697 | +        pk["vo"] = dict(pk["vo"], bridges_after_clip=[1])
1698 | +        self.assertFalse(PK.ly_shape(pk)[0])
1699 | +        pk["vo"] = dict(pk["vo"], bridges=[], bridges_after_clip=[])
1700 | +        self.assertFalse(PK.ly_shape(pk)[0])
1701 | +
1702 | +    def test_three_to_five_segments_and_one_clip_per_channel(self):
1703 | +        self.assertFalse(PK.ly_shape(medley_pk(n=2))[0])
1704 | +        self.assertFalse(PK.ly_shape(medley_pk(n=6))[0])
1705 | +        self.assertFalse(PK.ly_shape(medley_pk(chans="ABA"))[0])
1706 | +        self.assertTrue(PK.ly_shape(medley_pk(chans="ABA", supply="A gives two clips (L-y 4)"))[0])
1707 | +
1708 | +    def test_a_bridge_over_the_word_cap_fails(self):
1709 | +        pk = medley_pk(n=4, bridge="w", after=2, flagged=["clip_02 -> clip_03"])
1710 | +        pk["vo"]["bridges"][0] = W(BRIDGE_WORD_CAP + 1)
1711 | +        self.assertFalse(PK.ly_shape(pk)[0])
1712 | +
1713 | +
1714 | +def ctx():
1715 | +    return E.Context(NOW, REG)
1716 | +
1717 | +
1718 | +class TestMedleyPackageAndPin(unittest.TestCase):
1719 | +    def build(self, bridge=None, k=None, n=3, text="No ruler, just rules nobody gets to bend."):
1720 | +        by = {m["moment_id"]: m for m in (pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0),
1721 | +                                          pm("z", "D", 9.0))}
1722 | +        order = ["h", "x", "y", "z"][:n]
1723 | +        fields = {"takeaway": {"text": text, "cites": []}, "bridge": bridge, "bridge_after": k,
1724 | +                  "title": {"text": "No ruler.", "cites": []}, "caption": {"text": "three clips", "cites": []}}
1725 | +        return PK.assemble_medley(order, by, fields, ctx(), "medley (L-y)")
1726 | +
1727 | +    def gates(self, pk, **over):
1728 | +        g = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
1729 | +        g.update(over)
1730 | +        return g
1731 | +
1732 | +    def test_no_intro_and_one_takeaway_after_the_last_clip(self):
1733 | +        pk = self.build()
1734 | +        self.assertIsNone(pk["vo"]["intro"])
1735 | +        self.assertEqual((pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"]),
1736 | +                         (["No ruler, just rules nobody gets to bend."], [2]))
1737 | +        self.assertEqual([x["slot"] for x in pk["lines"]], ["takeaway", "title", "caption"])
1738 | +        self.assertAlmostEqual(pk["runtime_s_estimate"], 39.0 + 8 / 2.5 + 1.0 + PK.FINAL_TAIL_S, places=2)
1739 | +        self.assertEqual(PK.r4(pk)[0], True)
1740 | +
1741 | +    def test_the_one_bridge_after_a_clip_or_after_the_hook(self):
1742 | +        b = {"text": "Next, on keys.", "cites": ["y"], "why": "no referent"}
1743 | +        pk = self.build(bridge=b, k=1, n=4)
1744 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 3])
1745 | +        self.assertEqual([x["slot"] for x in pk["lines"]][:2], ["bridge_1", "takeaway"])
1746 | +        self.assertEqual(pk["bridge"]["join"], "clip_01 -> clip_02")
1747 | +        pk0 = self.build(bridge=b, k=0)
1748 | +        self.assertEqual(pk0["vo"]["intro"], "Next, on keys.")
1749 | +        self.assertEqual(pk0["vo"]["bridges_after_clip"], [2])
1750 | +        with self.assertRaises(ValueError):
1751 | +            self.build(bridge=b, k=2)                     # after the last clip is the takeaway's place
1752 | +
1753 | +    def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
1754 | +        pk = self.build()
1755 | +        self.assertEqual(package_pin.required_gates(pk)[-2:], ("medley", "ly_shape"))
1756 | +        pk["gates"] = self.gates(pk)
1757 | +        pin = package_pin.to_pin(pk, "test")
1758 | +        mp = pin["moments_package"]
1759 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
1760 | +        self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
1761 | +        self.assertEqual(mp["shape"], "medley")
1762 | +        for missing in ("medley", "ly_shape"):
1763 | +            g = self.gates(pk)
1764 | +            g.pop(missing)
1765 | +            with self.assertRaises(package_pin.PinRefused):
1766 | +                package_pin.to_pin(dict(pk, gates=g), "test")
1767 | +        with self.assertRaises(package_pin.PinRefused):
1768 | +            package_pin.to_pin(dict(pk, gates=self.gates(pk, ly_shape={"status": "FAIL", "replayed": False})), "test")
1769 | +
1770 | +    def test_the_gated_takeaway_must_be_the_spoken_one(self):
1771 | +        pk = self.build()
1772 | +        pk["gates"] = self.gates(pk)
1773 | +        pk["vo"] = dict(pk["vo"], bridges=["A different closing line."])
1774 | +        with self.assertRaises(package_pin.PinRefused) as cm:
1775 | +            package_pin.to_pin(pk, "test")
1776 | +        self.assertIn("bridges", str(cm.exception))
1777 | +
1778 | +    def test_the_old_shape_keeps_its_slots(self):
1779 | +        pk = {"vo": {"intro": "I", "bridges": ["B", "T"], "bridges_after_clip": [1, 2]}, "segments": [{}, {}, {}]}
1780 | +        self.assertEqual(package_pin.bridge_slots(pk), ["bridge_1", "bridge_2"])
1781 | +        self.assertEqual(package_pin.bridge_slots(dict(pk, shape="medley")), ["bridge_1", "takeaway"])
1782 | +
1783 | +
1784 | +    def test_a_takeaway_over_30_words_fails_r4_and_a_hook_join_bridge_pins(self):
1785 | +        pk = self.build(text=" ".join(["rules"] * (PK.MOMENTS_TAKEAWAY_WORD_CAP + 1)))
1786 | +        pk["medley"] = {"measured": True, "flagged": []}
1787 | +        cheap = PK.cheap_checks(pk, {}, [], NOW)[0]
1788 | +        self.assertTrue(any(v["rule"] == "R4" and "takeaway 1 31 words (max 30)" in v["detail"] for v in cheap), cheap)
1789 | +        b = {"text": "Next, on keys.", "cites": ["x"], "why": "no referent"}
1790 | +        pk0 = self.build(bridge=b, k=0)                   # audit 2030 C1 (grok P2-2): the intro slot pins as intro
1791 | +        pk0["gates"] = self.gates(pk0)
1792 | +        mp = package_pin.to_pin(pk0, "test")["moments_package"]
1793 | +        self.assertEqual(mp["edl_vo"], {"intro": "Next, on keys.",
1794 | +                                        "bridges": [{"text": pk0["vo"]["bridges"][0], "after_clip": 2}]})
1795 | +        self.assertEqual(mp["vo_jobs"], {"intro": "connection", "takeaway": "takeaway"})
1796 | +
1797 | +
1798 | +class Rig:
1799 | +    """build() with every model and the network stubbed: the LOOP CONTROL under test (audit 2030 C1, glm P2-6).
1800 | +    medleys: the clips-alone verdicts in call order, each (ok, flagged, ratings, through_line); writes: the writer's
1801 | +    bridges in call order (None = no bridge / declined)."""
1802 | +
1803 | +    LINE = "Nobody gets to bend these rules, and that is exactly why they hold when it counts."
1804 | +    A_OK = {"backend": "xai:grok", "replayed": False, "speaker_changes_inside": "no", "view": "own_sincere",
1805 | +            "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
1806 | +
1807 | +    def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=()):
1808 | +        import providers as P
1809 | +        self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
1810 | +        self.uncuttable, self.excluded = set(uncuttable), set(excluded)
1811 | +        self.medley_calls, self.write_calls, self.prompts = [], [], []
1812 | +        many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
1813 | +        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
1814 | +        call = self.router.call
1815 | +        self.router.call = lambda role, prompt, *a, **k: (self.prompts.append((role, prompt)),
1816 | +                                                          call(role, prompt, *a, **k))[1]
1817 | +        self.router.backends = {"xai:grok": type("B", (), {"vendor": "xai", "family": "grok"})()}
1818 | +
1819 | +    def medley(self, router, segs, ctx_, wv, seed=7, writer_family=None):
1820 | +        self.medley_calls.append([m["moment_id"] for m in segs])
1821 | +        ok, flagged, ratings, line = self.medleys.pop(0)
1822 | +        labs = PK.labels(len(segs))
1823 | +        v = verdict(labs, flagged, ratings, line)
1824 | +        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False)
1825 | +
1826 | +    def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
1827 | +        if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
1828 | +            raise PK.NoBridgeFits("no bridge of 3-12 words fits (the real write_takeaway's precondition)")
1829 | +        self.write_calls.append(([m["moment_id"] for m in segs], join))
1830 | +        b = self.writes.pop(0)
1831 | +        fields = {"takeaway": {"text": self.LINE, "cites": []}, "bridge": b,
1832 | +                  "bridge_after": join[0] if join is not None and b is not None else None,
1833 | +                  "title": {"text": "Nobody bends the rules", "cites": []},
1834 | +                  "caption": {"text": "three voices, one point", "cites": []},
1835 | +                  "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
1836 | +        return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
1837 | +
1838 | +    def run(self):
1839 | +        fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
1840 | +               "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
1841 | +               "verdict": {"ok": True, "violations": [], "classes": {}}}
1842 | +        cx = {"ok": True, "violations": [], "measured": True, "replayed": False, "backends": {"B": "xai", "C": "xai"}}
1843 | +        stubs = {
1844 | +            "_writers": lambda router: ({"heimdall"}, {"deepseek"}),
1845 | +            "prescreen": lambda router, ms, *a, **k: ({m["moment_id"]: dict(self.A_OK) for m in ms},
1846 | +                                                      {m["moment_id"]: [] for m in ms}, set(), set()),
1847 | +            "current_levels": lambda *a, **k: [],
1848 | +            "medley": self.medley, "write_takeaway": self.write,
1849 | +            "paid_gates": lambda *a, **k: (fid, cx),
1850 | +            "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
1851 | +                                                         "keep", "measured": True, "replayed": False,
1852 | +                                                         "backend": "xai:grok"},
1853 | +            "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
1854 | +                                                     "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
1855 | +            "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
1856 | +                                                             "clips": {sg["label"]: 5 for sg in pk["segments"]},
1857 | +                                                             "vo_point": 5, "backend": "xai:grok", "measured": True,
1858 | +                                                             "replayed": False}),
1859 | +        }
1860 | +        saved = {k: getattr(PK, k) for k in stubs}
1861 | +        try:
1862 | +            for k, v in stubs.items():
1863 | +                setattr(PK, k, v)
1864 | +            return PK.build(self.router, self.moments, {}, ctx(), log=lambda s: None, work_dir="/nonexistent")
1865 | +        finally:
1866 | +            for k, v in saved.items():
1867 | +                setattr(PK, k, v)
1868 | +
1869 | +
1870 | +class TestBuildLoop(unittest.TestCase):
1871 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
1872 | +
1873 | +    def test_nothing_is_written_for_clips_that_fail_alone(self):
1874 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], None, "none")], [])
1875 | +        out = rig.run()
1876 | +        self.assertIsNone(out["package"])
1877 | +        self.assertEqual(rig.write_calls, [])
1878 | +        self.assertIn("no through-line", out["tried"][0]["why"])
1879 | +
1880 | +    def test_a_weak_clip_alone_is_dropped_and_the_line_up_re_picked(self):
1881 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(False, [], {"clip_02": 2}, Rig.LINE), (True, [], None, Rig.LINE)],
1882 | +                  [None])
1883 | +        out = rig.run()
1884 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])
1885 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])           # written only after the clips pass
1886 | +        self.assertIsNotNone(out["package"])
1887 | +        self.assertIsNone(out["package"]["bridge"])
1888 | +
1889 | +    def test_a_declined_bridge_drops_the_clip_after_the_flagged_join(self):
1890 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
1891 | +                                                  (True, [], None, Rig.LINE)], [None, None])
1892 | +        out = rig.run()
1893 | +        self.assertEqual(rig.write_calls[0], (["h", "x", "y"], (1, "the next speaker's 'it' has no referent")))
1894 | +        self.assertIn("followable without a bridge", out["tried"][0]["why"])
1895 | +        self.assertEqual(rig.medley_calls[1], ["h", "x", "z"])                  # y, after the flagged join, dropped
1896 | +        pk = out["package"]
1897 | +        self.assertIsNone(pk["bridge"])
1898 | +        self.assertEqual((pk["gates"]["medley"]["status"], pk["gates"]["ly_shape"]["status"]), ("PASS", "PASS"))
1899 | +
1900 | +    def test_a_flagged_join_no_bridge_can_fill_drops_the_line_up_before_any_write(self):
1901 | +        long_ms = [pm("h", "A", 17.0), pm("x", "B", 17.0), pm("y", "C", 17.0), pm("z", "D", 13.0), pm("w", "E", 13.0)]
1902 | +        rig = Rig(long_ms, ["h", "x", "y", "z", "w"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE),
1903 | +                                                       (True, [], None, Rig.LINE)], [None])
1904 | +        self.assertIsNone(PK.bridge_budget(51.0))           # 51 s of clips: a bridge leaves no takeaway inside 70 s
1905 | +        out = rig.run()
1906 | +        self.assertIn("no bridge of 3-12 words", out["tried"][0]["why"])
1907 | +        self.assertEqual(rig.write_calls[0][0], [m for m in rig.medley_calls[1]])   # the first write is the 2nd line-up
1908 | +        self.assertNotIn("y", rig.medley_calls[1])           # the clip after the flagged join was dropped
1909 | +
1910 | +    def test_a_given_bridge_sits_at_the_flagged_join_with_its_reason(self):
1911 | +        b = {"text": "Next, a show on keys.", "cites": ["y"], "why": "the next clip's 'it' has no referent"}
1912 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, ["clip_01 -> clip_02"], None, Rig.LINE)], [b])
1913 | +        pk = rig.run()["package"]
1914 | +        self.assertEqual((pk["bridge"]["join"], pk["bridge"]["why"]), ("clip_01 -> clip_02", b["why"]))
1915 | +        self.assertEqual(pk["bridge"]["confirmed_by"]["join"], "clip_01 -> clip_02")
1916 | +        self.assertEqual(pk["vo"]["bridges_after_clip"], [1, 2])
1917 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
1918 | +        package_pin.to_pin(pk, "test")                    # every required row exactly PASS: the pin is allowed
1919 | +
1920 | +    def test_a_clip_the_second_recogniser_cannot_cut_is_never_offered_to_the_angles(self):
1921 | +        rig = Rig(self.MS, ["h", "x", "z"], [(True, [], None, Rig.LINE)], [None], uncuttable={"y"})
1922 | +        out = rig.run()
1923 | +        angle_prompt = next(p for r, p in rig.prompts if r == "angle_write")
1924 | +        self.assertNotIn("id=y ", angle_prompt)          # measured once per moment, before the angles (L-y 3)
1925 | +        self.assertIn("id=x ", angle_prompt)
1926 | +        self.assertEqual(out["prescreen"]["second_pass"]["y"], "not cuttable at an edge (ruling C / 7)")
1927 | +        self.assertEqual(out["prescreen"]["cuttable"], 3)
1928 | +        self.assertEqual(rig.medley_calls, [["h", "x", "z"]])
1929 | +        pk = out["package"]
1930 | +        self.assertEqual(pk["gates"]["cuttable"]["status"], "PASS")
1931 | +        package_pin.to_pin(pk, "test")                    # build() returns only a package its pin accepts
1932 | +
1933 | +    def test_an_excluded_moment_stays_out_of_every_later_angle(self):
1934 | +        ms = self.MS + [pm("w", "E", 14.0)]
1935 | +        rig = Rig(ms, [["h", "x", "y"], ["h", "x", "z", "w"]], [(True, [], None, Rig.LINE)] * 2, [None, None],
1936 | +                  excluded={"x"})
1937 | +        out = rig.run()
1938 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "z", "w"]])   # angle 2 never offers x again
1939 | +        self.assertIn("'x': 'exclusion'", out["tried"][0]["why"])
1940 | +        self.assertEqual(len(rig.write_calls), 2)          # the paid verdicts never ran on the doomed line-up
1941 | +        self.assertEqual([s["moment_id"] for s in out["package"]["segments"]], ["h", "z", "w"])
1942 | +
1943 | +    def test_the_supply_exception_is_recorded(self):
1944 | +        ms = [pm("h", "A", 14.0), pm("x", "B", 13.0), pm("y", "C", 3.0), pm("e", "A", 13.0)]
1945 | +        rig = Rig(ms, ["h", "x", "y", "e"], [(True, [], None, Rig.LINE)], [None])
1946 | +        pk = rig.run()["package"]
1947 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "e"])
1948 | +        self.assertIn("gives two clips, from two videos (L-y 4)", pk["supply_exception"])
1949 | +        self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")
1950 | +
1951 | +
1952 | +class TestInventoryRows(unittest.TestCase):
1953 | +    def test_the_two_medley_rows(self):
1954 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
1955 | +               "backend": "x", "replayed": False, "measured": True}
1956 | +        coh = {"backend": "x", "replayed": False, "measured": True}
1957 | +        args = (fid, [], True, (True, ""), {"ok": True, "measured": True, "replayed": False, "backends": {}},
1958 | +                {"hook": {"backend": "x", "replayed": False}}, {"h": {"verdict": "keep", "measured": True,
1959 | +                                                                      "replayed": False}},
1960 | +                {"h": {"ok": True, "edges": {"cuttable": True}, "replayed": False, "model": "s"}}, True, coh)
1961 | +        self.assertNotIn("medley", PK.inventory(*args))
1962 | +        g = PK.inventory(*args, medley=(True, {"backend": "x", "replayed": False, "measured": True, "flagged": []}),
1963 | +                         shape=(True, []))
1964 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("PASS", "PASS"))
1965 | +        g = PK.inventory(*args, medley=(False, {"measured": False, "flagged": None}), shape=(False, ["two bridges"]))
1966 | +        self.assertEqual((g["medley"]["status"], g["ly_shape"]["status"]), ("NOT RUN", "FAIL"))
1967 | +        self.assertEqual(g["ly_shape"]["why"], ["two bridges"])
1968 | +
1969 | +
1970 | +class TestReportedCost(unittest.TestCase):
1971 | +    def test_the_ledger_keeps_the_vendors_own_figure_beside_the_estimate(self):
1972 | +        import tempfile
1973 | +        import providers as P
1974 | +        with tempfile.TemporaryDirectory() as d:
1975 | +            path = os.path.join(d, "SPEND.json")
1976 | +            r = P.Router(env_path=None, spend_path=path, limit_usd=10.0)
1977 | +            b = r.backends["xai:grok-4.20-0309-reasoning"]
1978 | +            r._settle(None, b, {"in": 1000, "out": 1000, "usd_reported": 0.002}, 0.03, "check")
1979 | +            r._settle(None, b, {"in": 1000, "out": 1000}, 0.03, "check")
1980 | +            led = json.load(open(path))
1981 | +            self.assertAlmostEqual(led["usd_estimate"], 0.06, places=6)
1982 | +            self.assertAlmostEqual(led["usd_reported"], 0.002, places=8)
1983 | +            self.assertAlmostEqual(led["usd_unreported_estimate"], 0.03, places=6)
1984 | +            self.assertEqual(led["by_backend"][b.name]["reported_calls"], 1)
1985 | +        self.assertEqual(P._reported(None), {})
1986 | +        self.assertEqual(P._reported(True), {})
1987 | +        self.assertEqual(P._reported(-1), {})
1988 | +        self.assertEqual(P._reported(float("inf")), {})      # audit 2030 C3 (glm P2-1): a finite figure only
1989 | +        self.assertEqual(P._reported(float("nan")), {})
1990 | +        self.assertEqual(P._reported(0.5), {"usd_reported": 0.5})
1991 | +
1992 | +
1993 | +if __name__ == "__main__":
1994 | +    unittest.main()
1995 | 
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

ROUND 2 (cycles 3 and 4, 21:20 ET): the same diff plus these changes made after cycle 2. Review them first.
11. The first write for a flagged join budgets the takeaway so that ANY bridge of 3-12 words lands 60-70 s, the
    intersection of both budgets (package.write_takeaway). Every redo budgets with the bridge as written.
12. package.ly_shape also fails a bridge record whose text differs from the bridge line, a record whose confirmed_by
    is missing, a bool or empty, and a record with no bridge line. This mirrors the integrator's render-side R11.
13. CUTTABLE (the independent recogniser's sentence boundary at both edges, a REQUIRED gate) was never a drop reason
    in build(); the live run found a package with CUTTABLE FAIL, which the pin refused. Now:
    - L-v 2's second pass and CUTTABLE run ONCE PER CLEARED MOMENT BEFORE the angle call, and the angle proposer
      only sees moments that pass both (out["prescreen"]["second_pass"]);
    - a moment lost to exclusion is "doomed": no later angle may use it;
    - the per-clip results (exclusion, L-v 2, CUTTABLE) are read BEFORE the paid fidelity / context verdicts, so no
      verdict is paid on a line-up that is already lost;
    - build() returns a package only when package_pin.gate_problems(required_gates) is empty.
    Check that filtering early can never let through a moment the later gates would refuse, and never refuse one
    they would pass.
14. The writer prompt's rules now name the fidelity verdict's commentary tests (no checkable fact, no speaker view,
    no prediction, no advice or instruction to the viewer, no accusation, nothing that sounds like a quote) and ask
    for sentence-case titles and captions (title-case words were read as names by the deterministic NAME rule).
    Only the prompt changed; no gate changed.
15. tests/package/proof_ly.py: each worker meters its OWN spend at Router._settle, because the shared ledger moves
    with every worker. The per-package budget stop names which limit stopped it (out["budget_stop"]). A refused pin
    is recorded and the next universe still runs. tests/package/pin_and_verify.py also runs rule_r11 where the
    factory copy has it.


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
