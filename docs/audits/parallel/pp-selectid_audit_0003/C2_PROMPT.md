# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0003
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 156 s finish=stop usage in 17251 / out 3582 usd~0.105 (upper-bound price)

<medium> **visual_pin.py:224–226 (flags()) — a ruling-93 burned_in flag is emitted for items that are actually blocking, depending on call order; and the flag's `item` key is dropped by `sealed()`'s downstream consumers inconsistently.** Actually the concrete, verifiable defect: `flags()` adds a `burned_in` flag for every item where `not burned_block(x)` — i.e. only *eligible* items — but `spotlight.clean_visual` (spotlight.py:90–91) treats *any* flag other than `kind == "burned_in"` as unclean, while `package.build`'s hook path (package.py:48) uses `hook_block(v) or layout_block(v)` and never consults `flags` at all. So the same underlying record is judged by two different predicates in the two builds; that is by design per the ruling, but note the *asymmetry*: a clip with a ticker (layout_block → "ruling 93: a ticker…") is dropped in package.build, yet in spotlight.build the same record fails `clean_visual` only because `layout_block(v)` is truthy — the `not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]` clause then never runs, so a record with BOTH a ticker (blocking) and a ruling-70 flag reports only the layout reason in spotlight's `stop()` message at spotlight.py:118–120, where the `VP.layout_block(v) or` inserted at line 119 sits *after* the "not clean" branch, meaning a record that is measured, has a ruling-70 flag AND a ticker prints the flag kinds, not the ruling-93 reason. Cosmetic, but the precedence is: `not measured` → `layout_block` → `not clean (flags)`. Wait — reading line 118–120: the ternary picks `not measured` if `v.get("measured") is not True`, else `VP.layout_block(v) or f"not clean (...)"`. Since `layout_block` returns None for a clean record, the `or` falls through to the flags message. Correct. Withdrawn as a defect; noting precedence is right.

<medium> **visual_pin.py:213–215 (check()) — burned_in list is silently truncated to TEXTS_MAX=12 with no `burned_in_truncated` marker, unlike on_screen_text which gets `on_screen_text_truncated`.** Concrete scenario: a busy news frame (CoinDesk) with a ticker, a crawl, a lower third, a bug and several headline straps — the model returns 14 items; `check()` keeps the first 12. If the 13th/14th are the ticker/crawl, `layout_block` passes the clip as eligible while a ticker is actually on screen — the ruling-93 rule "a ticker or crawl = not eligible" silently fails open. Contrast: the on_screen_text truncation at line 210 is *marked* (`on_screen_text_truncated`), so the precedent in the same function is that truncation must be reported. This is a fail-open path in a law (L-m / M12) that says missing data never produces a pass. Concrete input: `burned_in` = 13 items, the ticker last → `VP.layout_block` returns None, clip reaches the pin with an unmeasured ticker.

<medium> **visual_pin.py:249–252 (layout_block()) — the 300-char truncation of the joined reasons can cut mid-reason, and more importantly `layout_block` returns a *string* while `hook_block` (line 255, unchanged) returns... (unverifiable from diff, its body is not shown).** What *is* verifiable: `package.py:48` does `why_v = VP.hook_block(m["visual"]) or VP.layout_block(m["visual"])`. If `hook_block` returns a non-string truthy (e.g. a dict) the f-string at package.py:50 still works, but the medley test at test_medley.py:366 asserts `self.assertIn("ruling 93: a ticker", out["hook_pool"]["visual_blocked"]["h"])` — this only passes because `hook_block` returned None for that record. For a record that is BOTH hook-blocked (third_person) and ticker-blocked, only the hook reason survives (`or` short-circuits); the ruling-93 reason is invisible in the hook pool. Not a correctness break (the clip is held either way, fail-closed holds), but the orchestrator's sheet loses the ruling-93 evidence for that clip.

<medium> **package.py:59–61 vs 71–72 — the two "not measured / not eligible" sweeps use different predicates, so a clip can pass one and be dropped by the other.** Line 59: `vbad = [m["moment_id"] for m in order if VP.layout_block(m.get("visual"))]` — this *replaces* the old "not measured" check, and since `layout_block` itself returns "its visual check is not measured (law L-m)" for an unmeasured record, the ruling-70 "not measured" case is still covered. But line 71–72: `vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") or VP.layout_block(m.get("visual")) for m in segs if VP.layout_block(m.get("visual"))}` — here the *dict value* prefers the record's stored `why` (the ruling-70 reason) over the ruling-93 reason, while the *filter* uses only `layout_block`. Concrete scenario: a record with `measured: True, why: "backend timeout"`, `burned_in: []` → filter: `layout_block` returns None → not in `vbad` → the clip proceeds even though its record carries a `why` (a prior failure note). Under the old code the same record also proceeded (old filter was 

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 46 s finish=stop usage in 17102 / out 530 usd~0.099 (upper-bound price)

**Findings**

No <critical> findings. All paths in the diff were examined line-by-line against the exact text of RULING 93, L-m, L-j, L-d, M12 and the supplied test fixtures.

No <high> findings. Every layout_block call (eligibility.py:32, package.py:48/59/71, spotlight.py:115/119, visual_pin.py:247) treats unmeasured, missing burned_in list, ticker, crawl, cut, covers_speaker or non-whole_16x9 as a blocking string; clean_visual and layout_ok never treat these as eligible. Old visual-1 records (no "burned_in" key) are rejected by layout_block:247 and force recompute (VERSION bumped to visual-2 at visual_pin.py:144, cache key changes). Sealed records from before the change omit the new key (sealed:260 uses "if k in rec") so pre-ruling-93 pins remain byte-identical until cache miss.

<medium> spotlight.py:89 (clean_visual): local `import visual_pin as VP` is inside the function while the module already binds VP at module level (evidenced by pre-existing `VP.hook_block(v)` at the updated line 114 and continued use at line 119). Harmless on every concrete visual dict in test_spotlight.py:433-447 and test_medley.py:372-391, but style deviates from smallest-diff intent (M1) and is redundant.

All other paths match the ruling verbatim:
- No channel-name hold remains (eligibility.py:21-24, layout_ok:25 returns only on channel_id; test_eligibility.py:289-296, test_select_by_id.py:505-520 now assert Bitcoin Magazine layout_eligible=True and only not_sentence_ready).
- Ticker (test_medley.py:369 TICKER dict) produces "ruling 93: a ticker" block before any pin or write (package.py:59, spotlight.py:118).
- Whole static lower_third/bug produces burned_in FLAG only, stays clean, reaches package (test_medley.py:384, clean_visual:90, flags:224).
- Protected preview outcome unchanged (Bitcoin Magazine clip still excluded, now solely by not_sentence_ready; selection locks/cut points for used clips untouched).
- G3/G10/G17c/L-b/L-c/L-g/L-k paths, canon, sentence_law, release_auth, visual-1 backward seals, and must-fail fixtures untouched by this diff.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 43 s finish=stop usage in 18942 / out 2572 usd~0.095 (upper-bound price)

I’ll audit the diff strictly against the stated RULING 93 and the governing laws, focusing on the specific invariants you listed.

## Findings

### <critical>
**1. `spotlight.clean_visual` fails closed on pre-RULING-93 records, breaking the "still recompute" invariant for existing pins.**
*   **File:** `pipeline/spotlight.py` (lines 84-91 in diff)
*   **Scenario:** A pin sealed before this change has a `visual` record with `measured: True` but **no** `burned_in` key (since `VERSION` was `visual-1`).
    *   `clean_visual` calls `VP.layout_block(v)`.
    *   `layout_block` (in `visual_pin.py`) checks: `if not isinstance(rec.get("burned_in"), list): return "ruling 93: the burned-in text question was not asked..."`.
    *   Therefore, `layout_block` returns a string (truthy).
    *   `clean_visual` returns `False`.
    *   **Consequence:** Any existing "clean" pin that is re-evaluated by the spotlight logic (e.g., during a re-render or regression check of a previously approved package) will now be flagged as "not clean" and potentially dropped or held, even though it was valid under the previous rules. The prompt states: *"medley pins sealed before the change still recompute... the seal reads the visual record only through sealed()... whose new key appears only on new records."* However, `clean_visual` is used in `spotlight.build` to determine if a moment is "clean" for the inventory. If a pin is re-processed, it will fail this check.
    *   **Law Violation:** This contradicts the requirement that pre-existing valid pins should not be invalidated by the new check unless they are actually re-measured. The `layout_block` function is too strict for *existing* records that simply lack the new field. It should likely treat a missing `burned_in` field as "not applicable" (pass) for records with `version == "visual-1"`, or the spotlight logic needs to distinguish between "unmeasured" and "measured but old version". Currently, `layout_block` conflates "not measured" and "measured but old version" into a block.

**2. `package.build` drops clips based on `layout_block` which blocks old records, causing data loss for existing pins.**
*   **File:** `pipeline/package.py` (lines 59-61, 71-72 in diff)
*   **Scenario:** Similar to above. If a line-up contains a clip with a `visual-1` record (measured, clean), `VP.layout_block(m.get("visual"))` will return a string because `burned_in` is missing.
    *   In `package.build`, `vbad` will include this moment.
    *   The code then executes `dropped |= set(vbad)` and returns `None` (or re-lines).
    *   **Consequence:** Valid, previously approved clips are dropped from the package because their visual records predate RULING 93. This violates the "smallest diff" and "no new renderer" spirit, but more importantly, it breaks the pipeline for any content that hasn't been re-measured with `visual-2`. The prompt implies that *new* checks are added, but existing valid pins should remain valid unless re-measured. The current implementation forces a re-measure or a drop.

### <high>
**3. `eligibility.layout_ok` no longer checks `has_chyron`, but `layout_ineligible` reason is only for "no registry id".**
*   **File:** `pipeline/eligibility.py` (lines 18-25, 33-35 in diff)
*   **Scenario:** The RULING 93 states: *"The has_chyron flag stays in the registry as a hint that orders the check, nothing more."*
    *   The code change removes `has_chyron` from `layout_ok`. This is correct per the ruling.
    *   However, the `layout_ineligible` reason in `_source` is now hardcoded to `"no registry channel id"`.
    *   **Issue:** If a channel *has* a registry id but its clip is blocked by `visual_pin.layout_block` (e.g., due to a ticker), the `eligibility` module does *not* report `layout_ineligible`. It reports `ok` (assuming other checks pass). The blocking happens later in `package.build` or `spotlight.build`.
    *   **Consequence:** The `eligibility` facts (`layout_eligible`) will be `True` for a clip that is actually ineligible due to visual content. This creates a mismatch between the "eligibility" stage and the "package/spotlight" stage. The RULING says *"eligibility drops the channel-name hold and reads the visual verdict."* But `eligibility.py` does **not** read the visual verdict. It only checks the registry ID. The visual verdict is read in `package.py` and `spotlight.py`.
    *   **Law Violation:** The prompt says *"YOUR SIDE: eligibility drops the channel-name hold and reads the visual verdict."* The code does **not** make `eligibility` read the visual verdict. It only drops the channel-name hold. The visual verdict is read downstream. This might be acceptable if "reads the visual verdict" was interpreted loosely, but strictly, `eligibility` should probably reflect the final layout eligibility. Currently, `facts["layout_eligible"]` is `True` even if the clip has a ticker. This c

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0003 (ruling 93), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes; qwen3.8-27b SHIP no (a critical and a high, refuted below); glm-5.3-flash SHIP yes
with conditions.

## Implemented

1. glm (its strongest point, a fail-open): check() cut burned_in to TEXTS_MAX items without a marker, so a ticker
   listed 13th would pass. FIXED: the items are sorted blocking-first before the cut, and burned_in_truncated counts
   what was cut (sealed). A ticker listed after 15 eligible straps still blocks (tested).
2. glm: a wordless channel bug (a logo) may come back with "text": null; the contract refused it, so the clip went
   unmeasured. FIXED: text may be null and is stored as "" (tested).
3. glm: a hook blocked both as a hook (third person) and by ruling 93 reported only the first reason. FIXED: both
   reasons are reported. A measured line-up clip blocked by ruling 93 now reports ruling 93's reason, not the
   record's stale "why"; an unmeasured clip still reports its own why (the existing test holds).

## Refuted, with evidence

- qwen <critical> 1 and 2 ("pre-ruling-93 records are blocked; existing pins are invalidated"):
  - layout_block() is called only on records in a build's pool. visual_pin.key() holds VERSION, so after
    visual-2 every clip is asked again: a visual-1 record is never served to a build.
  - Sealed pins are never re-judged by it. package_pin.to_pin / seal / pin_seal and the integrator's readiness check
    read the sealed visual record through sealed() only, which copies "burned_in" only when present, so a pin sealed
    before keeps its digest.
  - A record without question 4 that did reach a build would be one that never answered ruling 93's question. It
    fails closed (law L-m); that is intended.
- qwen <high> 3 ("eligibility does not read the visual verdict"): the ruling puts the per-clip judgement in "the
  pin-stage visual check (ruling 70)", which needs the clip's frames, fetched only at the pin stage.
  eligibility.layout_ok runs when the ledger is read (no frames). It drops the channel-name hold. The pin-stage
  verdict (layout_block) gates every on-screen role in both builds: a hook may not open; a line-up clip is dropped
  before any write; a spotlight is not clean.
- grok <medium> (a redundant local import in clean_visual): spotlight.py binds visual_pin only inside build(). The
  module has no global VP, so clean_visual's local import is needed.
- glm (hook_block's body on a record with no third_person): hook_block reads rec.get("measured") and rec.get("flags")
  only. The tests pass such records.
- glm ("story_layout_channels counts Bitcoin Magazine although its preview clip is not sentence-ready"): this is the
  fact's definition (channels that may be on screen by layout). Readiness is a separate, named reason.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0003/C2_STEP.diff (536 lines)
```
   1 | diff --git a/pipeline/eligibility.py b/pipeline/eligibility.py
   2 | index adb3d40..65c73c4 100644
   3 | --- a/pipeline/eligibility.py
   4 | +++ b/pipeline/eligibility.py
   5 | @@ -20,7 +20,8 @@ Result           ok; reasons (EVERY blocking reason, named, with its detail); fa
   6 |                   layout_eligible, age_h, tier, duration_s, ...); parts (a Lineup's per-span results)
   7 |  
   8 |  Layout eligibility is measured for every item and reported as the fact `layout_eligible`; for an on-screen role it is
   9 | -also the blocking reason 'layout_ineligible', so the supply DEC-12d removes can be counted.
  10 | +also the blocking reason 'layout_ineligible' (since RULING 93, 23:58 ET Nov 13: only a channel with no registry id; the
  11 | +frames of each clip are judged at the pin stage, visual_pin.layout_block).
  12 |  """
  13 |  import math
  14 |  import re
  15 | @@ -329,8 +330,11 @@ def age_hours(published_at, now):
  16 |  
  17 |  
  18 |  def layout_ok(reg):
  19 | -    """Rule S6 (editorial_select.layout_eligible, DEC-12d): a registry channel with an id and no burned-in chyron."""
  20 | -    return bool(reg and reg.get("channel_id") and not reg.get("has_chyron"))
  21 | +    """Rule S6: a registry channel with an id. RULING 93 (orchestrator 23:58 ET Nov 13): DEC-12d is measured per CLIP,
  22 | +    not per channel. No channel is layout_ineligible by name: every clip, any channel, is judged on its own frames by
  23 | +    the pin-stage visual check (visual_pin.layout_block: a ticker or crawl, or a lower third the 9:16 crop would cut
  24 | +    mid-word or that covers the speaker). The registry's has_chyron is a hint that orders that check, nothing more."""
  25 | +    return bool(reg and reg.get("channel_id"))
  26 |  
  27 |  
  28 |  # ── the predicate ──
  29 | @@ -380,8 +384,7 @@ def _source(src, ctx, role):
  30 |          R("no_transcript", "no transcript words")
  31 |      if role in ON_SCREEN:
  32 |          if not facts["layout_eligible"]:
  33 | -            R("layout_ineligible", f"{facts['channel']}: " + ("burned-in chyron (has_chyron, DEC-12d)"
  34 | -                                                             if reg and reg.get("has_chyron") else "no registry channel id"))
  35 | +            R("layout_ineligible", f"{facts['channel']}: no registry channel id")   # ruling 93: never by name
  36 |          if not sentence_ready(src):
  37 |              R("not_sentence_ready", "no sentence-ready word record (law L-e): " +
  38 |                ("segment timing only" if src.timing != "word" else "a stretch reads unpunctuated"))
  39 | diff --git a/pipeline/package.py b/pipeline/package.py
  40 | index 8972b95..806e93e 100644
  41 | --- a/pipeline/package.py
  42 | +++ b/pipeline/package.py
  43 | @@ -2336,7 +2336,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  44 |      see(rated_open)                                                          # seen before any angle is asked
  45 |      blocked = {}
  46 |      for m in rated_open:
  47 | -        why_v = VP.hook_block(m["visual"])
  48 | +        why_v = "; ".join(w for w in (VP.hook_block(m["visual"]), VP.layout_block(m["visual"])) if w) or None
  49 | +        #   ruling 93: its own frames, per clip; both reasons when both hold (audit 0003 C1, glm)
  50 |          if why_v:
  51 |              m["visual_hook_block"] = blocked[m["moment_id"]] = why_v
  52 |      out["visual"] = out_visual
  53 | @@ -2553,9 +2554,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  54 |                                        "back to back with the sign-off only", "added_clip": added,
  55 |                                 "lineup_before": [m["moment_id"] for m in segs]}}
  56 |          see(order)                                        # RULING 70: the added clip is seen too
  57 | -        vbad = [m["moment_id"] for m in order if not (m.get("visual") or {}).get("measured")]
  58 | -        if vbad:
  59 | -            note["why_not"] = f"ruling 70: the visual check is not measured for {vbad}"
  60 | +        vbad = [m["moment_id"] for m in order if VP.layout_block(m.get("visual"))]   # ruling 93 (not measured
  61 | +        if vbad:                                                                    # included, law L-m)
  62 | +            note["why_not"] = f"rulings 70 / 93: not measured, or not eligible on its frames: {vbad}"
  63 |              return None
  64 |          nv_pre = None
  65 |          if lock_check is not None:                         # RULINGS 68 / 72: its own line-up
  66 | @@ -2741,8 +2742,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  67 |                                         pool.submit(truth_for, router, m, work_dir, tru)) for m in segs}
  68 |                  extra, relined, w_used, written = "", False, 0, ()
  69 |                  see(segs)                                   # RULING 70: every clip seen before any write is paid
  70 | -                vbad = {m["moment_id"]: (m.get("visual") or {}).get("why") for m in segs
  71 | -                        if not (m.get("visual") or {}).get("measured")}
  72 | +                vbad = {m["moment_id"]: ((m.get("visual") or {}).get("why") if not (m.get("visual") or {}).get(
  73 | +                            "measured") else None) or VP.layout_block(m.get("visual"))     # ruling 93: per clip (L-m
  74 | +                        for m in segs if VP.layout_block(m.get("visual"))}                 # included); the cause named
  75 |                  if vbad or segs[0].get("visual_hook_block"):
  76 |                      vbad = vbad or {segs[0]["moment_id"]: segs[0]["visual_hook_block"]}
  77 |                      dropped |= set(vbad)
  78 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  79 | index b4ee879..effb73e 100644
  80 | --- a/pipeline/spotlight.py
  81 | +++ b/pipeline/spotlight.py
  82 | @@ -350,6 +350,16 @@ def layout_for(router, m, vrec, cache_path=None, seed=7):
  83 |      return rec
  84 |  
  85 |  
  86 | +def clean_visual(v):
  87 | +    """RULING 90's "visual check clean" with RULING 93: measured, no ruling-70 flag (a third person shown as a still
  88 | +    with a negative claim, on-screen text that asserts beyond the words), not blocked as a hook, and eligible on its
  89 | +    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) is
  90 | +    eligible and flagged for the orchestrator, so it does not make the clip unclean."""
  91 | +    import visual_pin as VP
  92 | +    return (v or {}).get("measured") is True and not VP.hook_block(v) and not VP.layout_block(v) and \
  93 | +        not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]
  94 | +
  95 | +
  96 |  def alone_score(m):
  97 |      """The ALONE scorer's rating of the moment's CURRENT text (package.verdict_of: the integrator's verdicts of the
  98 |      render's own scorer, rulings 56 / 60), or None when it has none yet."""
  99 | @@ -595,9 +605,10 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 100 |      rows.pop("r4", None)
 101 |      rows.pop("coherence", None)
 102 |      v = m.get("visual") or {}
 103 | -    rows["visual"] = _row(v.get("measured") is True and not v.get("flags"), v.get("backend"), v.get("replayed"),
 104 | +    rows["visual"] = _row(clean_visual(v), v.get("backend"), v.get("replayed"),
 105 |                            measured=v.get("measured") is True, flags=list(v.get("flags") or []),
 106 | -                          by_rule="ruling 90: the visual check clean (no flag; ruling 70's sheet)")
 107 | +                          by_rule="ruling 90: the visual check clean (no ruling-70 flag, not blocked as a hook, and "
 108 | +                                  "eligible on its frames under ruling 93; a ruling-93 burned_in flag is listed)")
 109 |      own, hr = P.hook_own(m), m.get("hook_rating") or {}
 110 |      rows["hook_own"] = _row(own is not None and own["rating"] >= HOOK_MIN, hr.get("backend"),
 111 |                              bool(hr.get("replayed", False)), measured=own is not None,
 112 | @@ -767,10 +778,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 113 |      clean = {}
 114 |      for mid, m in strong.items():
 115 |          v = m.get("visual") or {}
 116 | -        if v.get("measured") is True and not v.get("flags") and not VP.hook_block(v):
 117 | +        if clean_visual(v):
 118 |              clean[mid] = m
 119 |          else:
 120 |              stop(mid, "the visual check: " + (f"not measured ({v.get('why')})" if v.get("measured") is not True else
 121 | +                                              VP.layout_block(v) or
 122 |                                                f"not clean ({[f.get('kind') for f in v.get('flags') or []]})"))
 123 |      passed(clean, 5)
 124 |      two, off_fail = P.second_screen(router, clean, a_by, sources, ctx, log=log, cache=step_a_cache) if clean else \
 125 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 126 | index 4cecca8..a2bde93 100644
 127 | --- a/pipeline/visual_pin.py
 128 | +++ b/pipeline/visual_pin.py
 129 | @@ -16,6 +16,11 @@ Per clip (a moment's [start, end]):
 130 |    it cannot be sealed (law L-m).
 131 |  - flags(): a third_person finding (a person other than the speaker shown as a still, photo or graphic while the words
 132 |    make a negative claim) and every on-screen text that asserts more than the words. They are sealed, never a reject.
 133 | +- RULING 93 (23:58 ET Nov 13): question 4 (burned_in): every ticker, crawl, lower third or channel bug burned into
 134 | +  the source, and how the 9:16 version treats it. layout_block(): a ticker or crawl, or a lower third or bug that is
 135 | +  not wholly in the 16:9, that the 9:16 edge would cut mid-word, or that covers the speaker, makes the clip NOT
 136 | +  eligible in any role (per clip, never by channel name); one that sits whole in the 16:9 and wholly in or out of the
 137 | +  9:16 is eligible and sealed as a "burned_in" FLAG for the orchestrator.
 138 |  - hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 139 |    speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 140 |    third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 141 | @@ -27,10 +32,13 @@ import os
 142 |  import subprocess
 143 |  import threading
 144 |  
 145 | -VERSION = "visual-1"
 146 | +VERSION = "visual-2"                     # RULING 93 (23:58 ET Nov 13): question 4, burned-in text and the 9:16
 147 |  ROLE = "visual_check"
 148 |  TILES, EVERY_S, TILE_W = 8, 2.0, 480
 149 |  HOW = ("still", "photo", "graphic", "none")
 150 | +BURNED = ("ticker", "crawl", "lower_third", "bug")      # ruling 93: question 4's kinds
 151 | +RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
 152 | +IN_9X16 = ("whole", "out", "cut")
 153 |  FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 154 |  CACHE_LOCK = threading.Lock()
 155 |  TEXTS_MAX, TEXT_CHARS = 12, 200          # audit 1541 C2: a verbose reply never bloats the sealed pin
 156 | @@ -40,7 +48,7 @@ The image is a contact sheet of {n} frames of the clip, left to right and top to
 157 |  the source video (seconds). The clip's words, as spoken:
 158 |  "{text}"
 159 |  
 160 | -Answer three questions from the frames only:
 161 | +Answer four questions from the frames only:
 162 |  1. third_person: is a person who is NOT the one speaking shown as a STILL, a PHOTO or a GRAPHIC (not live video of a
 163 |     person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 164 |     a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 165 | @@ -48,12 +56,22 @@ Answer three questions from the frames only:
 166 |  2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 167 |     words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 168 |  3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 169 | +4. burned_in: every piece of text or graphic burned into the SOURCE picture that stays on screen: a ticker or a crawl
 170 | +   (text that runs or scrolls across the frame), a lower third (a name or headline strap), or a channel bug (a logo or
 171 | +   watermark). Not subtitles of the spoken words. For each say whether it sits WHOLLY inside the frame, and how the
 172 | +   VERTICAL 9:16 version would treat it. The 9:16 version shows, for ONE speaker, a full-height strip about one third
 173 | +   of the frame's width, centred on the speaker's face; for two or three people, a band around each face, stacked; for
 174 | +   a shared screen (a chart, a slide, b-roll), the whole frame. "in_9x16" is "whole" (wholly inside the 9:16 picture),
 175 | +   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). "covers_speaker": does it cover
 176 | +   the speaking person's face or mouth?
 177 |  
 178 |  Return ONLY this JSON object:
 179 |  {{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 180 |    "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 181 |   "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 182 | - "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}}}}"""
 183 | + "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}},
 184 | + "burned_in": [{{"kind": "ticker|crawl|lower_third|bug", "text": "<its text, copied>", "whole_in_16x9": true or false,
 185 | +   "in_9x16": "whole|out|cut", "covers_speaker": true or false}}]}}"""
 186 |  
 187 |  
 188 |  def load_cache(path):
 189 | @@ -171,10 +189,20 @@ def _opt_str(x):
 190 |  
 191 |  
 192 |  def check(v):
 193 | -    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third"}."""
 194 | -    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third"}:
 195 | -        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third")
 196 | -    tp, ost, lt = v["third_person"], v["on_screen_text"], v["lower_third"]
 197 | +    """The verdict, in contract or ValueError -> {"third_person", "on_screen_text", "lower_third", "burned_in"}."""
 198 | +    if not isinstance(v, dict) or set(v) != {"third_person", "on_screen_text", "lower_third", "burned_in"}:
 199 | +        raise ValueError("keys must be exactly third_person, on_screen_text, lower_third, burned_in")
 200 | +    tp, ost, lt, bi = v["third_person"], v["on_screen_text"], v["lower_third"], v["burned_in"]
 201 | +    if not isinstance(bi, list) or any(
 202 | +            not isinstance(x, dict) or x.get("kind") not in BURNED or not isinstance(x.get("text"), (str, type(None)))
 203 | +            or type(x.get("whole_in_16x9")) is not bool or x.get("in_9x16") not in IN_9X16 or
 204 | +            type(x.get("covers_speaker")) is not bool for x in bi):        # a wordless bug may carry no text
 205 | +        raise ValueError("burned_in out of contract (ruling 93)")
 206 | +    items = [{"kind": x["kind"], "text": (x.get("text") or "").strip()[:TEXT_CHARS],
 207 | +              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"]}
 208 | +             for x in bi]
 209 | +    items = sorted(items, key=lambda x: burned_block(x) is None)   # the blocking ones first, so a cut never hides
 210 | +    #   one (audit 0003 C1, glm: a ticker listed 13th would otherwise pass)
 211 |      if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
 212 |              type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
 213 |          raise ValueError("third_person out of contract")
 214 | @@ -191,7 +219,9 @@ def check(v):
 215 |              "on_screen_text": [{"text": x["text"].strip()[:TEXT_CHARS], "asserts_beyond_words": x["asserts_beyond_words"],
 216 |                                  "why": str(x.get("why") or "").strip()[:TEXT_CHARS]} for x in keep],
 217 |              **({"on_screen_text_truncated": len(texts) - len(keep)} if len(texts) > len(keep) else {}),
 218 | -            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))}}
 219 | +            "lower_third": {"name": _opt_str(lt.get("name")), "text": _opt_str(lt.get("text"))},
 220 | +            "burned_in": items[:TEXTS_MAX],
 221 | +            **({"burned_in_truncated": len(items) - TEXTS_MAX} if len(items) > TEXTS_MAX else {})}
 222 |  
 223 |  
 224 |  def flags(v):
 225 | @@ -202,7 +232,35 @@ def flags(v):
 226 |          out.append({"kind": "third_person", "text": tp["finding"], "name_on_screen": tp["name_on_screen"]})
 227 |      out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 228 |              if x["asserts_beyond_words"]]
 229 | -    return out
 230 | +    out += [{"kind": "burned_in", "text": x["text"], "item": x["kind"], "in_9x16": x["in_9x16"]}   # ruling 93: an
 231 | +            for x in v.get("burned_in") or [] if not burned_block(x)]            # eligible lower third or bug,
 232 | +    return out                                                                   # flagged for the orchestrator
 233 | +
 234 | +
 235 | +def burned_block(x):
 236 | +    """RULING 93 on one burned-in item -> why it makes the clip NOT eligible, or None (eligible, flagged): a ticker or
 237 | +    a crawl; a lower third or bug that is not wholly inside the 16:9, that the 9:16 edge would cut through mid-word, or
 238 | +    that covers the speaker."""
 239 | +    if x["kind"] in RUNNING:
 240 | +        return f"a {x['kind']} ({x['text'][:80]!r}): not eligible"
 241 | +    if not x["whole_in_16x9"]:
 242 | +        return f"a {x['kind']} not wholly inside the 16:9 ({x['text'][:80]!r})"
 243 | +    if x["in_9x16"] == "cut":
 244 | +        return f"a {x['kind']} the 9:16 crop would cut through mid-word ({x['text'][:80]!r})"
 245 | +    if x["covers_speaker"]:
 246 | +        return f"a {x['kind']} that covers the speaker ({x['text'][:80]!r})"
 247 | +    return None
 248 | +
 249 | +
 250 | +def layout_block(rec):
 251 | +    """RULING 93 (23:58 ET Nov 13): why the clip may not be on screen in ANY role, or None. Not measured, or a record
 252 | +    without question 4 (an earlier version), is never a pass (law L-m); otherwise burned_block() on every item."""
 253 | +    if not (rec or {}).get("measured"):
 254 | +        return "its visual check is not measured (law L-m)"
 255 | +    if not isinstance(rec.get("burned_in"), list):
 256 | +        return "ruling 93: the burned-in text question was not asked (an earlier visual record)"
 257 | +    why = [w for w in (burned_block(x) for x in rec["burned_in"]) if w]
 258 | +    return ("ruling 93: " + "; ".join(why))[:300] if why else None
 259 |  
 260 |  
 261 |  def hook_block(rec):
 262 | @@ -222,7 +280,7 @@ def sealed(rec):
 263 |      """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 264 |      name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 265 |      out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 266 | -                               "backend", "replayed", "why") if k in rec}
 267 | +                               "burned_in", "burned_in_truncated", "backend", "replayed", "why") if k in rec}
 268 |      if isinstance(rec.get("sheet"), dict):
 269 |          out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 270 |      return out
 271 | diff --git a/tests/eligibility/test_eligibility.py b/tests/eligibility/test_eligibility.py
 272 | index 17896e4..cd89e2d 100644
 273 | --- a/tests/eligibility/test_eligibility.py
 274 | +++ b/tests/eligibility/test_eligibility.py
 275 | @@ -6,8 +6,8 @@ pinned     every law constant equals the module it lives in today (editorial_sel
 276 |  parity     the ported helpers answer as today's (backward_reference, _same_statement, _word_sentences, _ends_statement)
 277 |  must-fail  one fixture per named reason (synthetic, plus real: Altcoin Daily's unpunctuated record, E-FAIL-033)
 278 |  must-pass  the PBX-approved preview's hook and two clips (references/pulse_preview_2026-11-11, frozen word
 279 | -           transcripts); its Bitcoin Magazine clip fails on layout_ineligible (has_chyron, DEC-12d came after) and on
 280 | -           its record's whole-record L-e readiness (one word 570 s away reads unpunctuated), on nothing in its text
 281 | +           transcripts); its Bitcoin Magazine clip fails on its record's whole-record L-e readiness (one word 570 s
 282 | +           away reads unpunctuated), on nothing in its text (ruling 93 retired DEC-12d's channel hold)
 283 |  Run: cd <repo> && python3 -m pytest -q tests/eligibility"""
 284 |  import json
 285 |  import os
 286 | @@ -185,11 +185,14 @@ class TestSource(unittest.TestCase):
 287 |          self.assertIn("not_current", E.eligible(naive, ctx()).names())
 288 |  
 289 |      def test_layout_is_a_fact_always_and_a_reason_on_screen(self):
 290 | -        bm = source([HOOK_TXT], channel="Bitcoin Magazine")    # has_chyron (DEC-12d)
 291 | -        ev = E.eligible(bm, ctx("evidence"))
 292 | -        self.assertTrue(ev.ok)
 293 | -        self.assertIs(ev.facts["layout_eligible"], False)
 294 | -        self.assertIn("layout_ineligible", E.eligible(bm, ctx("clip")).names())
 295 | +        bm = source([HOOK_TXT], channel="Bitcoin Magazine")    # has_chyron: RULING 93 (23:58 ET Nov 13) holds no
 296 | +        ev = E.eligible(bm, ctx("evidence"))                    # channel by name; its frames are judged per clip
 297 | +        self.assertTrue(ev.ok)                                  # (visual_pin.layout_block)
 298 | +        self.assertIs(ev.facts["layout_eligible"], True)
 299 | +        self.assertNotIn("layout_ineligible", E.eligible(bm, ctx("clip")).names())
 300 | +        nobody = source([HOOK_TXT], channel="No Such Channel")  # a channel with no registry id is still held
 301 | +        self.assertIs(E.eligible(nobody, ctx("evidence")).facts["layout_eligible"], False)
 302 | +        self.assertIn("layout_ineligible", E.eligible(nobody, ctx("clip")).names())
 303 |  
 304 |      def test_on_screen_needs_a_sentence_ready_word_record(self):
 305 |          seg = source([HOOK_TXT], timing="segment", method="yt_auto:en")
 306 | @@ -398,8 +401,8 @@ class TestSpan(unittest.TestCase):
 307 |          self.assertIn("no_story_statement", r.names())
 308 |  
 309 |      def test_every_reason_is_reported_not_only_the_first(self):
 310 | -        src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="Bitcoin Magazine",
 311 | -                     age_h=100)
 312 | +        src = source(["so " + ("bitcoin went sideways " * 2) + "today?"], timing="segment", channel="No Such Channel",
 313 | +                     age_h=100)                                      # no registry id: layout_ineligible (ruling 93)
 314 |          r = E.eligible(E.Span(src, 0, 0), ctx("hook", story=statements(E.Span(src, 0, 0))))
 315 |          for n in ("not_current", "layout_ineligible", "not_sentence_ready", "start_case", "duration"):
 316 |              self.assertIn(n, r.names())
 317 | @@ -454,7 +457,7 @@ class TestLineup(unittest.TestCase):
 318 |          r = self.lineup(story=s2, claim=s2[0], hook=None, clips=())
 319 |          self.assertIn("story_bitcoin_screen", r.names())
 320 |          self.assertIn("claim_no_bitcoin", r.names())
 321 | -        bm = source([CLIP_TXT], channel="Bitcoin Magazine", vid="M")
 322 | +        bm = source([CLIP_TXT], channel="No Such Channel", vid="M")   # no registry id (ruling 93: never by name)
 323 |          s3 = (E.Span(self.a, 0, 0), E.Span(bm, 0, 0))
 324 |          self.assertIn("story_layout_channels", self.lineup(story=s3, claim=s3[0], hook=None, clips=()).names())
 325 |          stale = source([CLIP2_TXT], channel="Natalie Brunell", vid="S", age_h=90)
 326 | @@ -548,10 +551,10 @@ class TestRealPreview(unittest.TestCase):
 327 |          for kind, sp, s in spans:
 328 |              r = E.eligible(sp, E.Context(self.now, REG, role=kind, story=story))
 329 |              if s["channel"] == "Bitcoin Magazine":
 330 | -                # DEC-12d (has_chyron) came after the approval; and its ~10-min frozen window transcript has one word
 331 | -                # (598.3 s, 570 s after this clip) in an unpunctuated stretch, which today's whole-record L-e rule
 332 | -                # (transcript_store.sentence_ready) rejects. Both are today's laws, measured, not this passage's text.
 333 | -                self.assertEqual(sorted(r.names()), ["layout_ineligible", "not_sentence_ready"], r.why())
 334 | +                # its ~10-min frozen window transcript has one word (598.3 s, 570 s after this clip) in an
 335 | +                # unpunctuated stretch, which today's whole-record L-e rule (transcript_store.sentence_ready) rejects:
 336 | +                # today's law, measured, not this passage's text. DEC-12d's channel hold is gone (ruling 93).
 337 | +                self.assertEqual(sorted(r.names()), ["not_sentence_ready"], r.why())
 338 |              else:
 339 |                  self.assertTrue(r.ok, f"{s['channel']}: {r.why()}")
 340 |  
 341 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 342 | index 5e25d43..044385c 100644
 343 | --- a/tests/package/funnel.py
 344 | +++ b/tests/package/funnel.py
 345 | @@ -125,7 +125,7 @@ DESC = {"opener": "opens on a pronoun or reply word that needs what came before
 346 |          "no_bitcoin": "does not name Bitcoin: regex `\\b(bitcoins?|btcs?)\\b` (T11, the old story selector's subject "
 347 |                        "screen; 'Bitcoiners', 'sats', 'Satoshi' do not count)",
 348 |          "too_many_sentences": "more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES = 3)",
 349 | -        "layout_ineligible": "the channel has a burned-in chyron (registry has_chyron, DEC-12d)",
 350 | +        "layout_ineligible": "the channel has no registry id (ruling 93: never a hold by channel name)",
 351 |          "not_statement": "ends on a question",
 352 |          "hook_lead": "hook only: transcript gap before the first word < 80 ms",
 353 |          "start_case": "starts lower-case", "fragment": "not a sentence start / end", "too_short": "< 5 words",
 354 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 355 | index 1e3d997..dc22632 100644
 356 | --- a/tests/package/test_medley.py
 357 | +++ b/tests/package/test_medley.py
 358 | @@ -623,10 +623,10 @@ class Rig:
 359 |      def visual(self, router, m, work_dir, cache, seed=7, log=print):
 360 |          """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 361 |          self.visual_calls.append(m["moment_id"])
 362 | -        base = {"version": "visual-1", "measured": True, "flags": [],
 363 | +        base = {"version": "visual-2", "measured": True, "flags": [],
 364 |                  "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 365 |                                   "finding": "no third person"},
 366 | -                "on_screen_text": [], "lower_third": {"name": None, "text": None},
 367 | +                "on_screen_text": [], "lower_third": {"name": None, "text": None}, "burned_in": [],   # ruling 93
 368 |                  "sheet": {"name": f"visual_{m['moment_id']}.jpg", "sha256": "0" * 64, "times": [0.0], "path": "/x"},
 369 |                  "backend": "xai_vision:grok-4.7", "replayed": False, "usd": 0.002, "usd_basis": "reported",
 370 |                  "cached": False}
 371 | @@ -1678,6 +1678,30 @@ class TestRuling70Visual(unittest.TestCase):
 372 |          self.assertIn("not measured", out["hook_pool"]["visual_blocked"]["h"])
 373 |          self.assertIsNone(out["package"])
 374 |  
 375 | +    TICKER = {"burned_in": [{"kind": "ticker", "text": "BTC 74,512 | ETH 2,410", "whole_in_16x9": True,
 376 | +                             "in_9x16": "cut", "covers_speaker": False}]}
 377 | +
 378 | +    def test_ruling_93_a_ticker_holds_the_clip_in_any_role_by_its_own_frames(self):
 379 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [], [], visuals={"h": self.TICKER}).run()
 380 | +        self.assertIn("ruling 93: a ticker", out["hook_pool"]["visual_blocked"]["h"])     # it may not open
 381 | +        self.assertIsNone(out["package"])
 382 | +        rig = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)], [None],
 383 | +                  visuals={"y": self.TICKER})
 384 | +        out = rig.run()
 385 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"], ["h", "x", "z"]])          # dropped and re-lined
 386 | +        self.assertIn("ruling 93: a ticker", out["tried"][0]["why"])
 387 | +        self.assertEqual(rig.write_calls, [(["h", "x", "z"], None)])                   # no write for it
 388 | +        self.assertIsNotNone(out["package"])
 389 | +
 390 | +    def test_ruling_93_a_whole_lower_third_is_eligible_and_flagged(self):
 391 | +        strap = {"kind": "lower_third", "text": "JOE CARLASARE", "whole_in_16x9": True, "in_9x16": "out",
 392 | +                 "covers_speaker": False}
 393 | +        flag = {"kind": "burned_in", "text": "JOE CARLASARE", "item": "lower_third", "in_9x16": "out"}
 394 | +        out = Rig(self.MS, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None],
 395 | +                  visuals={"x": {"burned_in": [strap], "flags": [flag]}}).run()
 396 | +        self.assertIsNotNone(out["package"])
 397 | +        self.assertEqual(out["package"]["gates"]["visual"]["flags"], [dict(flag, segment=1)])
 398 | +
 399 |  
 400 |  class TestRuling66Candidate(unittest.TestCase):
 401 |      """RULING 66 (13:18): A PASSED LINE-UP IS KEPT. A line-up that passed the clips-alone verdict is a candidate. A build
 402 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 403 | index 0e62176..779e766 100644
 404 | --- a/tests/package/test_spotlight.py
 405 | +++ b/tests/package/test_spotlight.py
 406 | @@ -69,7 +69,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
 407 |               visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 408 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 409 |                                        "finding": "none"}, "on_screen_text": [],
 410 | -                     "lower_third": {"name": None, "text": None}},
 411 | +                     "lower_third": {"name": None, "text": None}, "burned_in": []},
 412 |               scorer_verdict=sv(text, 4.0),
 413 |               spotlight_source={"ok": True, "why": "layout 'conversation'", "turns": {"measured": False},
 414 |                                 "layout": {"measured": True, "layout": "conversation", "backend": "fake:vis",
 415 | @@ -495,7 +495,7 @@ class TestPackageFor(unittest.TestCase):
 416 |  class TestBuild(unittest.TestCase):
 417 |      """The stages in order on stubs: each stage's failure is recorded with how far the moment got."""
 418 |  
 419 | -    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None):
 420 | +    def run_build(self, ms, ratings, alone=None, layout="conversation", poll=None, lock=None, visual=None):
 421 |          ctx = E.Context(NOW, REG)
 422 |          calls = {}
 423 |  
 424 | @@ -523,7 +523,8 @@ class TestBuild(unittest.TestCase):
 425 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 426 |                   (SPOT.P, "hook_onset_for", lambda m, s, w, c: {"pass": True, "measured": True}),
 427 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 428 | -                 (VP, "visual_for", lambda r, m, w, c: {"measured": True, "flags": [], "backend": "fake:vis"}),
 429 | +                 (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 430 | +                                                              "backend": "fake:vis"}, **(visual or {}))),
 431 |                   (SPOT, "layout_for", lambda r, m, v, c: {"measured": True, "layout": layout, "why": "w"}),
 432 |                   (SPOT, "episode_turns", lambda vid, c=None: {"measured": False, "unmarked": True}),
 433 |                   (SPOT.P, "exclusion_for", lambda r, m, s, c: {"verdict": "keep"}),
 434 | @@ -578,6 +579,23 @@ class TestBuild(unittest.TestCase):
 435 |              out, calls = self.run_build(ms, {"a": 5})
 436 |          self.assertIs(calls["facts"][0]["never_delivered"], False)
 437 |  
 438 | +    def test_ruling_93_a_ticker_holds_a_clip_and_a_whole_strap_is_flagged_and_clean(self):
 439 | +        ms = [moment(mid="a", channel="A")]
 440 | +        tick = {"kind": "ticker", "text": "BTC 74,512", "whole_in_16x9": True, "in_9x16": "cut",
 441 | +                "covers_speaker": False}
 442 | +        out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [tick]})
 443 | +        self.assertNotIn("package_for", calls)
 444 | +        self.assertIn("ruling 93: a ticker", out["moments"]["a"]["out"])
 445 | +        strap = dict(tick, kind="lower_third", text="BILL MILLER IV", in_9x16="out")
 446 | +        out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [strap], "flags": [
 447 | +            {"kind": "burned_in", "text": "BILL MILLER IV", "item": "lower_third", "in_9x16": "out"}]})
 448 | +        self.assertEqual(calls["package_for"], ["a"])                   # eligible, flagged, still clean
 449 | +        self.assertTrue(SPOT.clean_visual({"measured": True, "burned_in": [strap], "flags": [
 450 | +            {"kind": "burned_in", "text": "BILL MILLER IV"}]}))
 451 | +        self.assertFalse(SPOT.clean_visual({"measured": True, "burned_in": [], "flags": [
 452 | +            {"kind": "on_screen_text", "text": "SCANDAL"}]}))           # a ruling-70 flag is not clean
 453 | +        self.assertFalse(SPOT.clean_visual({"measured": True, "flags": []}))       # no question 4: never
 454 | +
 455 |      def test_ruling_92_and_a_lock_with_no_verdict_stops(self):
 456 |          ms = [moment(mid="a", channel="A")]
 457 |          out, calls = self.run_build(ms, {"a": 5}, layout="reaction")
 458 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 459 | index 22f9647..82c682c 100644
 460 | --- a/tests/package/test_visual_pin.py
 461 | +++ b/tests/package/test_visual_pin.py
 462 | @@ -19,7 +19,8 @@ from test_providers import Fake, router  # noqa: E402
 463 |  CLEAN = {"third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 464 |                            "finding": "only the host on camera"},
 465 |           "on_screen_text": [{"text": "SIMPLY BITCOIN", "asserts_beyond_words": False, "why": "the show's name"}],
 466 | -         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"}}
 467 | +         "lower_third": {"name": "Mark W. Yusko", "text": "Mark W. Yusko, Morgan Creek Capital"},
 468 | +         "burned_in": []}                                                        # ruling 93: question 4
 469 |  STILL = dict(CLEAN, third_person={"shown": True, "how": "photo", "words_negative": True, "name_on_screen": "null",
 470 |                                    "finding": "a photo of a man beside the host while he says a CEO made a mistake"},
 471 |               on_screen_text=[{"text": "NVIDIA CEO SCANDAL", "asserts_beyond_words": True,
 472 | @@ -63,6 +64,35 @@ class TestContract(unittest.TestCase):
 473 |          self.assertIn("not measured", VP.hook_block({"measured": False}))
 474 |          self.assertIn("not measured", VP.hook_block(None))
 475 |  
 476 | +    def test_ruling_93_burned_in_text_per_clip(self):
 477 | +        item = lambda kind, **k: dict({"kind": kind, "text": "BITCOIN 74,512 | ETH 2,410", "whole_in_16x9": True,
 478 | +                                       "in_9x16": "out", "covers_speaker": False}, **k)
 479 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True)
 480 | +        self.assertIsNone(VP.layout_block(rec()))                                       # nothing burned in
 481 | +        for kind in ("ticker", "crawl"):                                                # a ticker or crawl: never
 482 | +            self.assertIn(f"a {kind}", VP.layout_block(rec(item(kind))))
 483 | +        strap = item("lower_third", text="BILL MILLER IV | CIO, MILLER VALUE")
 484 | +        for ok in (dict(strap, in_9x16="whole"), dict(strap, in_9x16="out"), dict(strap, kind="bug", in_9x16="whole")):
 485 | +            self.assertIsNone(VP.layout_block(rec(ok)))                                 # eligible, and flagged
 486 | +            self.assertEqual([f["kind"] for f in VP.flags(VP.check(dict(CLEAN, burned_in=[ok])))], ["burned_in"])
 487 | +        for bad, word in ((dict(strap, in_9x16="cut"), "mid-word"), (dict(strap, covers_speaker=True), "covers"),
 488 | +                          (dict(strap, whole_in_16x9=False), "not wholly inside")):
 489 | +            self.assertIn(word, VP.layout_block(rec(bad)))                              # ... unless cut, covering,
 490 | +        self.assertIn("not measured", VP.layout_block({"measured": False}))             # or not whole in the 16:9
 491 | +        self.assertIn("not asked", VP.layout_block({"measured": True, "flags": []}))    # an earlier record: never
 492 | +        for bad in ([{"kind": "banner", "text": "x", "whole_in_16x9": True, "in_9x16": "out", "covers_speaker": False}],
 493 | +                    [dict(strap, in_9x16="partly")], [dict(strap, covers_speaker="no")], "none"):
 494 | +            with self.assertRaises(ValueError):
 495 | +                VP.check(dict(CLEAN, burned_in=bad))
 496 | +        self.assertIn("burned_in", VP.sealed(rec(strap)))
 497 | +        bug = VP.check(dict(CLEAN, burned_in=[dict(strap, kind="bug", text=None, in_9x16="whole")]))
 498 | +        self.assertEqual(bug["burned_in"][0]["text"], "")                              # a wordless bug (C1, glm)
 499 | +        many = [dict(strap, text=f"strap {i}", in_9x16="out") for i in range(VP.TEXTS_MAX + 3)] + [item("ticker")]
 500 | +        v = VP.check(dict(CLEAN, burned_in=many))                                       # the ticker listed last
 501 | +        self.assertEqual((len(v["burned_in"]), v["burned_in_truncated"]), (VP.TEXTS_MAX, 4))
 502 | +        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True)))            # is never cut away
 503 | +        self.assertEqual(VP.VERSION, "visual-2")                                        # every clip asked again
 504 | +
 505 |      def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 506 |          class R:
 507 |              cached, usd = False, 0.37
 508 | diff --git a/tests/select_by_id/test_select_by_id.py b/tests/select_by_id/test_select_by_id.py
 509 | index eafecb0..51d8333 100644
 510 | --- a/tests/select_by_id/test_select_by_id.py
 511 | +++ b/tests/select_by_id/test_select_by_id.py
 512 | @@ -86,7 +86,9 @@ class TestMustPassPreview(Preview):
 513 |          Yahoo's 'Bitcoin slips below ...'); whether the format allows a tolerance is PBX's call (L-o; audit C2 L-2).
 514 |          The story marks every sentence that states the development: Natalie's three (the drop, the ETF outflows,
 515 |          no part in the Monday rally) and Yahoo's two statements; Yahoo's 'But I don't check it on an hourly basis.'
 516 | -        sits between them. Bitcoin Magazine's sentence counts as evidence (has_chyron) and never goes on screen.
 517 | +        sits between them. Bitcoin Magazine's sentence never goes on screen: since RULING 93 (23:58 ET Nov 13) no
 518 | +        channel is held by name (it now counts as a fourth layout channel), and its record fails the whole-record L-e
 519 | +        readiness (not_sentence_ready), as test_eligibility's preview test measures.
 520 |          With only Natalie's first sentence marked, D4 (a) rejects her next two (no back-reference): the same reason
 521 |          today's auto path stopped her window at 7.15 s (DoD 17:34)."""
 522 |          nat_rows, yah_rows = self.rows(self.table, "Natalie Brunell"), self.rows(self.table, "Yahoo Finance")
 523 | @@ -96,9 +98,10 @@ class TestMustPassPreview(Preview):
 524 |          st = S.choose_story(Scripted(reply(story=ids, claim=ids[0])), self.table, self.ctx)
 525 |          self.assertEqual(st.status, "accepted", st.attempts)
 526 |          self.assertEqual(st.claim.text, st.story[0].text)
 527 | -        self.assertEqual(st.eligibility.facts["story_layout_channels"], 3)
 528 | +        self.assertEqual(st.eligibility.facts["story_layout_channels"], 4)   # ruling 93: no channel by name
 529 |          lt, skipped = S.lineup_table(list(self.src.values()), st.story, self.ctx)
 530 | -        self.assertIn("layout_ineligible", skipped["jbDqdLytkNM"])   # never offered for the screen (DEC-12d)
 531 | +        self.assertNotIn("layout_ineligible", skipped["jbDqdLytkNM"])
 532 | +        self.assertIn("not_sentence_ready", skipped["jbDqdLytkNM"])   # never offered for the screen: its record
 533 |          self.assertFalse(any(r.source.video_id == "jbDqdLytkNM" for r in lt.rows))
 534 |          hook = self.rows(lt, "DataDash")
 535 |          nat, yah = self.rows(lt, "Natalie Brunell"), self.rows(lt, "Yahoo Finance")
 536 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the builder of sealed "moments" pins that
another session renders into short Bitcoin videos). Only state what you can verify from the diff; if uncertain, say
so; do not guess. Be specific: file:line and a concrete input that breaks it.

Background (static):
- DEC-12d (Nov 11) held every clip of a channel the registry marks has_chyron (Bitcoin Magazine, CoinDesk) out of any
  on-screen role, by name: eligibility.layout_ok. The render's G10 TEXT CROP gate measured only those channels.
- RULING 70: the pin-stage VISUAL check (visual_pin): one contact sheet per clip, judged by a vision model; findings
  are sealed as FLAGS, never a reject by themselves, except that a third_person finding may not be the HOOK. A clip
  whose check is not measured is never a pass (law L-m).
- The medley build (package.build) sees every hook before any angle and every clip of a line-up before any write;
  the spotlight (spotlight.build, committed earlier tonight) needs "the visual check clean".

The order (verbatim): "RULING 93: DEC-12d IS MEASURED PER CLIP, NOT PER CHANNEL. ... THE RULE NOW: no channel is
layout_ineligible by name. Every clip, any channel, is judged on its own frames by the pin-stage visual check (ruling
70), which gains one question: 'is there burned-in running text (a ticker, a crawl) or a lower third that the 9:16
crop would cut through mid-word, or that covers the speaker?' A ticker or crawl = not eligible. A static lower third or
channel bug that sits whole in the 16:9 and is either wholly in or wholly out of the 9:16 crop = eligible, flagged for
me. The render's G10 stays as it is and runs on EVERY clip (not only has_chyron channels), still monitoring. The
has_chyron flag stays in the registry as a hint that orders the check, nothing more. YOUR SIDE: eligibility drops the
channel-name hold and reads the visual verdict."
The render's 9:16 (vertical_layout): one speaker = a fixed full-height strip centred on the face, about one third of
the width; two or three people = stacked bands; a shared screen = the whole frame, letterboxed.

The change:
1. eligibility.layout_ok: a registry channel with an id (has_chyron no longer holds); layout_ineligible only for a
   channel with no registry id.
2. visual_pin: VERSION visual-2 (every clip is asked again: the cache key holds the version); question 4 "burned_in"
   (kind ticker / crawl / lower_third / bug, text, whole_in_16x9, in_9x16 whole / out / cut, covers_speaker) in the
   prompt and in check(); burned_block() per item; layout_block(rec): not measured, a record without question 4, a
   ticker or crawl, or a lower third / bug that is not whole in the 16:9, that the 9:16 would cut mid-word, or that
   covers the speaker -> not eligible; otherwise eligible, and each item is a "burned_in" FLAG (flags()); sealed()
   keeps burned_in.
3. package.build: a hook's visual block is hook_block OR layout_block; a line-up clip (and the no-voice line-up's
   clips) blocked by layout_block is dropped and re-lined before any write, as an unmeasured one was.
4. spotlight.clean_visual: measured, not hook-blocked, not layout-blocked, no ruling-70 flag; a ruling-93 burned_in
   flag keeps it clean (eligible, flagged). The spotlight's visual gate row uses it.
5. Tests: the medley rig's records are visual-2; new cases (a ticker holds a hook and a line-up clip; a whole strap is
   eligible and flagged; the contract and each block reason); the eligibility and select_by_id tests that asserted the
   channel hold now assert ruling 93 (Bitcoin Magazine no longer held by name; a channel with no registry id still
   is; the preview's Bitcoin Magazine clip is still never on screen, now on its record's sentence readiness).

Check: that no channel is held by name anywhere in this path; that a ticker / crawl / cut / covering item can never
reach a pin; that an unmeasured or pre-ruling-93 record is never a pass; that a whole, static item is eligible and
flagged, never dropped; that medley pins sealed before the change still recompute (the seal reads the visual record
only through sealed(), whose new key appears only on new records). Answer with findings tagged <critical>, <high>,
<medium> (file:line, a concrete scenario), then "SHIP: yes / no / yes with conditions".


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
