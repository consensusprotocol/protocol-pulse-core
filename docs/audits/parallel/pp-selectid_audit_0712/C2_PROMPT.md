# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0712
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 85 s finish=stop usage in 9593 / out 2479 usd~0.066 (upper-bound price)

# Audit: TRIMMED-CLIP SEALING (Ruling 49) — reviewer pass

Scope: I verified only what the diff shows. I did not see `stand_alone_check`, `trim_variant`, `to_pin`'s schema check, `pinned.validate_schema`, or the swap paths' bodies; where that matters I say so.

## P0

None.

## P1

**P1-1 — `package.py:41-44` (lineup_ok) vs. `package_pin.trim_problems` (package_pin.py:89-92): the two "at most one" checks count differently, so a pin can be refused for a line-up the builder already accepted.**
`lineup_ok` counts `bool(m.get("trimmed_leading"))` — a segment with `trimmed_leading` but no `untrimmed_start` (or vice versa) counts as trimmed. `trim_problems` counts `"trimmed_leading" in s or "untrimmed_start" in s` — same. But `trim_problems` also independently requires `scorer_pending is True` on every trimmed segment, while `lineup_ok` never looks at `scorer_pending`. Concrete scenario: a segment carries `trimmed_leading`/`untrimmed_start` but no `scorer_pending` key (e.g. an older moment dict produced before this diff, or a path that builds the row without it — I cannot verify from the diff that every producer of the trimmed row sets it; the only producer shown is the `**{...}` literal at package.py:31-33, which does set it). `lineup_ok` passes it, the pin's `trim_problems` refuses it. That is fail-closed, not a correctness bug — but it means the builder's line-up acceptance and the pin's acceptance can disagree, and the diff's own test (test_medley.py:158) only exercises `lineup_ok`'s message, not the disagreement case. Severity: P1 because the ruling's condition (a) is enforced only at the pin, not where the line-up is chosen; if any other producer of trimmed rows exists outside this diff, it silently breaks.

**P1-2 — `package.py:31-33`: `scorer_pending: True` is written unconditionally inside the conditional-spread, but the spread's condition is `m.get("trimmed_leading")` while the pin's "belongs to a trimmed clip" test is presence of `trimmed_leading` OR `untrimmed_start`.**
If a moment dict ever carries `untrimmed_start` without `trimmed_leading` (the diff's own `trim_problems` treats that as malformed, package_pin.py:102-103, so it would be refused — but only at the pin, with a *different* message), the package row would carry `untrimmed_start` with no `scorer_pending`, and the pin's ruling-49(a) check (`s.get("scorer_pending") is not True` fires whenever either key is present, package_pin.py:93-101) would refuse it with the *pending* message rather than the *pairing* message. Fail-closed, but the diagnostic points at the wrong ruling. Minor, diagnostic-only. Could be P2; I list it here because the two presence tests (`m.get("trimmed_leading")` truthiness vs. key presence) are subtly different — a moment with `trimmed_leading: ""` (falsy) would get no `scorer_pending` in the package row yet count as trimmed in `trim_problems`'s `n` count (key presence, not truthiness). That is a real, if unlikely, divergence: **`trimmed_leading: ""`** → package row: no scorer_pending; pin: counted as trimmed, then refused for missing scorer_pending. Fail-closed either way.

## P2

**P2-1 — `package.py:14-21` / `package_pin.py:75`: the two constants are equal only by convention, enforced by a test, not by code.**
`TRIMMED_PER_LINEUP_MAX = 1` (package.py) and `TRIMMED_PER_PIN_MAX = 1` (package_pin.py) are separate literals; the test asserts equality (test_medley.py:152) but nothing in the code does. If one changes, the other drifts. `package_pin` already imports nothing from `package` here — I cannot see whether a circular-import constraint prevents `TRIMMED_PER_PIN_MAX = package.TRIMMED_PER_LINEUP_MAX`. If importable, prefer the single source. (The test at line 152 does catch drift, so this is P2.)

**P2-2 — `package_pin.py:99-101`: the ruling-49(a) check runs before the pairing check, so a segment with `scorer_pending` but neither trim key gets *two* problems appended in some orderings — actually no: it's guarded correctly.** On re-reading: the `scorer_pending`-on-untrimmed case is caught at package_pin.py:96-97 (inside the `not has_w and not has_s` branch) and the missing-`scorer_pending` case at 99-101 (inside the has-either branch). Both are correct; the only residual is that a segment with `trimmed_leading` present but `untrimmed_start` absent *and* `scorer_pending: true` gets the pairing refusal (line 102-103) and correctly no ruling-49(a) refusal — good. No finding; noted for completeness.

**P2-3 — `package.py:55-61` (the no-voice path, build): the added-clip rule is duplicated inline rather than calling `lineup_ok`.**
The no-voice path re-encodes the line-up rules (length, price predictions, now trimmed count, duration window) as an inline `if ... continue`. This is the third copy of the trimmed-count rule (lineup_for's inline, lineup_ok, and here). Any future change to TRIMMED_PER_LINEUP_MAX semantics (e

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 9735 / out 488 usd~0.061 (upper-bound price)

**P2: pipeline/package_pin.py:89** (trim_problems)  
Concrete scenario: segments=[{"trimmed_leading":"But", "untrimmed_start":0.0, "scorer_pending":True}, {"trimmed_leading":"So", "untrimmed_start":0.0, "scorer_pending":True}]. The n>TRIMMED_PER_PIN_MAX check fires first and the per-segment scorer_pending validation also fires; both messages are collected. Matches the ruling-49(b) intent but the diff contains no path that ever raises the limit after a validate affirmation (the "integrator says when" clause is mentioned only in comments).

**P2: pipeline/package.py:31** (the **{... "scorer_pending": True ...} dict in _package)  
Concrete scenario: a trimmed segment is emitted with scorer_pending=True even if TRIM_SCORER_PENDING were later toggled back to False in the same Python process. The constant only controls stand_alone_check behavior; the emitted pin key is hard-coded. (Test temporarily flips the constant and confirms the check side, but the emission side is unconditional after the constant change at line 14.)

No other violations of the requested properties are present in the diff:  
- trim_problems explicitly refuses a trimmed clip lacking scorer_pending: true (lines 99-101) and refuses scorer_pending on any untrimmed clip (lines 96-97).  
- to_pin copies the key only when present (line 110); SEALED_LATER lists it but older pins without the key therefore hash identically.  
- lineup_ok, lineup_for and the build candidate loop all reject > TRIMMED_PER_LINEUP_MAX trimmed clips (lines 41, 50, 59); test_medley.py:158-160 confirms lineup_for never returns two and that the two MAX constants are kept equal.  
- No code path claims the scorer has affirmed anything; the STAND_ALONE row and scorer_pending list explicitly say "PENDING AT THE RENDER".  
- Nothing in the diff touches the renderer, selector, GPU usage outside the stated Ollama path, or any governing law outside ruling 49.

SHIP: yes with conditions (integrator must document how/when the TRIMMED_PER_*_MAX limit is raised post-affirmation; the pending emission should be guarded by the constant rather than hard-coded True).

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 28 s finish=stop usage in 10429 / out 1903 usd~0.060 (upper-bound price)

# Code Audit: pp-selectid-0712 (C1_STEP.diff)

## Findings

### P0: None
No critical defects found. The implementation correctly enforces the "fail closed" principle for the strict mode and properly seals the `scorer_pending` flag.

### P1: None
No high-severity issues identified.

### P2: Observations / Minor

**1. Constant Duplication (Maintainability)**
*   **File:** `pipeline/package.py` (line 19) and `pipeline/package_pin.py` (line 75)
*   **Scenario:** `TRIMMED_PER_LINEUP_MAX` and `TRIMMED_PER_PIN_MAX` are both set to `1`. While the test `test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin` asserts they are equal, they are defined independently. If a future ruling changes the limit for lineups but not for pins (or vice versa), this could lead to subtle inconsistencies if the test is not updated.
*   **Recommendation:** Consider importing one constant into the other module or defining a shared constant in a common config module to ensure they remain synchronized by construction.

**2. Logic Clarity in `trim_problems`**
*   **File:** `pipeline/package_pin.py` (lines 89-101)
*   **Scenario:** The check `if s.get("scorer_pending") is not True` is performed *after* the `has_w != has_s` check in the loop, but the count `n` is calculated before the loop. The logic is correct, but the placement of the `scorer_pending` validation inside the `if has_w or has_s` block (implicitly, because it's after the `continue` for non-trimmed segments) is slightly subtle. Specifically, if a segment has `trimmed_leading` but *not* `untrimmed_start`, it hits `continue` at line 104 *before* checking `scorer_pending` at line 99.
    *   *Wait, let me re-read the diff carefully.*
    *   Line 94: `has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s`
    *   Line 95: `if not has_w and not has_s:` -> checks `scorer_pending` presence (line 96-97) -> `continue`.
    *   Line 99: `if s.get("scorer_pending") is not True:` -> This line is **outside** the `if not has_w and not has_s` block. It executes for **all** segments that are not skipped by the `continue` at line 98.
    *   Line 102: `if has_w != has_s:` -> checks consistency -> `continue`.
    *   **Correction:** The code at line 99 checks `scorer_pending` for **every** segment that has *either* `trimmed_leading` or `untrimmed_start` (or both).
        *   If a segment has `trimmed_leading` but no `untrimmed_start`, `has_w` is True, `has_s` is False. It does not enter the `if not has_w and not has_s` block. It reaches line 99. If `scorer_pending` is not True, it adds an error. Then it reaches line 102, adds another error about missing `untrimmed_start`, and continues. This is correct behavior (fail closed, report all issues).
        *   If a segment has `untrimmed_start` but no `trimmed_leading`, same logic applies.
        *   If a segment has neither, it enters the first block. If it has `scorer_pending`, it reports an error. If it doesn't, it continues.
    *   **Conclusion:** The logic is actually robust. It ensures that *any* segment that looks like it might be trimmed (has one of the keys) must have `scorer_pending: True`. And *any* segment that is not trimmed (has neither key) must *not* have `scorer_pending`. This is a strong invariant. No change needed.

**3. Test Coverage for `lineup_for` with `TRIMMED_PER_LINEUP_MAX`**
*   **File:** `tests/package/test_medley.py` (line 159-160)
*   **Scenario:** The test `test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin` verifies that `lineup_for` returns a lineup with exactly 1 trimmed clip. It does not explicitly test that `lineup_for` *refuses* to build a lineup with 2 trimmed clips if they were the only options (i.e., does it return `None` or an empty list?). The code in `package.py` (line 50-51) uses `continue` to skip invalid combos. If all combos are invalid, `lineup_for` will likely return `None` or an empty list depending on its implementation (not fully shown, but standard pattern). The test asserts `sum(...) == 1`, which implies it found a valid lineup. It doesn't prove it *rejects* a 2-trimmed lineup if that were the only candidate. However, `lineup_ok` is tested to reject 2 trimmed clips (line 158). Since `lineup_for` relies on `lineup_ok` (or similar logic), this is likely sufficient.

## Verification of Specific Checks

1.  **Trimmed clip sealed WITHOUT `scorer_pending: true`?**
    *   **No.** `package_pin.trim_problems` (line 99-101) explicitly checks `if s.get("scorer_pending") is not True` for any segment that has `trimmed_leading` or `untrimmed_start`. If missing or False, it adds an error, causing `PinRefused`.
    *   **No clip says pending when not trimmed?**
    *   **No.** `package_pin.trim_problems` (line 95-97) checks `if not has_w and not has_s:` and then `if "scorer_pending" in s:` adds an error. So untrimmed clips cannot have `scorer_pending`.

2.  **No line-up or pin can carry t

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0712 (RULING 49: a trimmed clip sealed with the clip scorer's verdict pending): cycle 1 consensus

**Run.** Verdicts:
- grok: "yes with conditions" (P2 only);
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0, "yes with conditions" (its P1s are consistency and diagnostics; its conditions are answered below).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | grok P2 (its condition 2), in glm P1-2's spirit: the row's scorer_pending is hard-coded True whatever TRIM_SCORER_PENDING says | The row writes bool(TRIM_SCORER_PENDING). Under the strict switch a trimmed segment would carry False, which trim_problems refuses, so the pin can never claim pending when the switch says strict. |

## Answered (verified from the code; no change)

| # | condition | answer |
|---|---|---|
| A1 | glm condition 1: is the package row the only producer of trimmed_leading / untrimmed_start on a segment? | Yes. They are set only by trim_variant (the moment, always both keys together), the _package row literal (both, with scorer_pending), and to_pin's copy. So the pin's ruling-49 (a) check cannot see a trimmed row without scorer_pending. |
| A2 | glm P1-1: lineup_ok counts trimmed_leading while trim_problems counts either key | Equal on every producer's output, because both keys always come together (A1). trim_problems is the pin's backstop: it also refuses a row with only one key. |
| A3 | glm condition 2: derive TRIMMED_PER_PIN_MAX from package | Kept as two constants plus the equality test (test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin). The integrator's check_pin_only imports this branch's package_pin.py, and package_pin must not pull package.py (and its imports) into the integrator's process. |
| A4 | glm condition 3: a test of the no-voice path's copy of the rule | Not added (one reviewer, P2). The inline rule is the same expression as lineup_for's, which is tested, and a pin with two trimmed clips is refused by trim_problems anyway (tested). |
| A5 | grok condition 1: when is the limit of one raised? | Only when the integrator reports the first trimmed clip affirmed at validate, and on your word. It is stated in the constant's comment and in STATE. |

## Verification

- test_medley 81 OK; every other suite OK.


---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0712/C2_STEP.diff (198 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 4263680..5fce642 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -80,11 +80,14 @@ SEARCH_USD_ESTIMATE = 10.00        # ruling 5's $1.50 / 15 min is per PACKAGE de
   6 |                                     # ceiling keeps ruling 5's ratio ($5.00 : $1.50) for calls whose vendor reports no cost
   7 |  SEARCH_WALL_S = 2400.0             # the build ends cleanly before its driver's timeout (a killed build writes no record)
   8 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33 part 2: the ONE leading word a cut may trim
   9 | -TRIM_SCORER_PENDING = False        # ruling 33 (b): the render's clip scorer must affirm every trimmed segment; it runs on
  10 | -                                   # GPU0, which the pin stage may not use. False (the default): the pin stage judges a
  11 | -                                   # trimmed segment as the render does with no scorer, so it fails closed and is never
  12 | -                                   # sealed. True ONLY on the orchestrator's explicit yes: it is sealed with the verdict
  13 | -                                   # pending at the render, stated in the sealed row (audit 0530: the reviewers split on L-m)
  14 | +TRIM_SCORER_PENDING = True         # ruling 33 (b): the render's clip scorer (gemma3:27b on Ultron's GPU0, which the
  15 | +                                   # pin stage may not use) must affirm every trimmed segment. RULING 49 (07:02 Nov 13):
  16 | +                                   # YES, a trimmed clip is sealed with that verdict PENDING AT THE RENDER (stage_validate
  17 | +                                   # runs before any render; a refusal there costs no GPU), stated in the sealed row and
  18 | +                                   # per clip in the pin (scorer_pending: true). False: the render's check with no scorer
  19 | +TRIMMED_PER_LINEUP_MAX = 1         # ruling 49 (b): at most ONE trimmed clip per line-up until the first trimmed clip has
  20 | +                                   # been affirmed at validate once (the integrator says when): one refusal cannot sink a
  21 | +                                   # line-up twice. package_pin.TRIMMED_PER_PIN_MAX holds the pin to the same number
  22 |  SWAP_TOP = 10                      # candidates read per swapped place, best by score first, after the place's own
  23 |                                     # rules (a short clip only at the last place): audit 0510 C1, glm P1-3
  24 |  NO_VOICE_AFTER = 2                 # ruling 3 (22:40): the takeaway failing its gates this many times ships no VO line
  25 | @@ -306,8 +309,10 @@ def _package(segs, ctx, fields, vo_kind, vo, lines):
  26 |                          "time_sensitive": bool(time_sensitive(m)),          # ruling 1 (22:40): L-v 3 on the render
  27 |                          "source_published_at": utc_z(m.get("published_at")),  # clock, both sealed in the pin
  28 |                          "url_30s_before": f"https://www.youtube.com/watch?v={m['video_id']}&t={max(0, int(m['start']) - 30)}s",
  29 | -                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"]}
  30 | -                           if m.get("trimmed_leading") else {})}                      # ruling 33 part 2, sealed
  31 | +                        **({"trimmed_leading": m["trimmed_leading"], "untrimmed_start": m["untrimmed_start"],
  32 | +                            "scorer_pending": bool(TRIM_SCORER_PENDING)}   # ruling 49 (a): the clip scorer's verdict
  33 | +                           if m.get("trimmed_leading") else {})}   # on the trimmed text is pending at the render
  34 | +                                                                   # (strict: False, which the pin refuses)
  35 |                         for lb, m in zip(labels(len(segs)), segs)],
  36 |            "vo": dict(vo, signoff=signoff(segs, ctx)),
  37 |            "title": fields["title"]["text"], "caption": fields["caption"]["text"],
  38 | @@ -736,6 +741,8 @@ def lineup_ok(segs, crange=None, repeat_ok=False):
  39 |          return False, "one segment per channel"
  40 |      if sum("price_prediction" in m.get("risk", []) for m in segs) > PRICE_PREDICTIONS_MAX:
  41 |          return False, "price predictions"
  42 | +    if sum(bool(m.get("trimmed_leading")) for m in segs) > TRIMMED_PER_LINEUP_MAX:
  43 | +        return False, f"more than {TRIMMED_PER_LINEUP_MAX} trimmed clip (ruling 49 b)"
  44 |      if any(m["duration_s"] < SHORT_CLIP_S for m in clips[:-1]):
  45 |          return False, "a short clip that is not last"
  46 |      dur = sum(m["duration_s"] for m in segs)
  47 | @@ -822,6 +829,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  48 |                      continue
  49 |                  if sum("price_prediction" in m.get("risk", []) for m in (h, *combo)) > PRICE_PREDICTIONS_MAX:
  50 |                      continue
  51 | +                if sum(bool(m.get("trimmed_leading")) for m in (h, *combo)) > TRIMMED_PER_LINEUP_MAX:   # ruling 49 b
  52 | +                    continue
  53 |                  order = sorted(combo, key=lambda m: pos[m["moment_id"]])
  54 |                  if [m for m in order[:-1] if m["duration_s"] < SHORT_CLIP_S]:
  55 |                      continue
  56 | @@ -1405,6 +1414,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  57 |                  cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
  58 |                  if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
  59 |                          sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
  60 | +                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
  61 |                          not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
  62 |                      continue
  63 |                  order, added = cand, mid
  64 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  65 | index c8a76d3..f860174 100644
  66 | --- a/pipeline/package_pin.py
  67 | +++ b/pipeline/package_pin.py
  68 | @@ -67,8 +67,9 @@ def recency_problems(segments):
  69 |  
  70 |  SEALED_LATER = ("time_sensitive", "source_published_at",   # ruling 1 (22:40): the render clock checks L-v 3 on these
  71 |                  "speaker",                                 # the 00:05 ET Nov 13 order, item 3
  72 | -                "trimmed_leading", "untrimmed_start")      # ruling 33 part 2 (render merged 11e361cc): only when a word
  73 | -                                                           # is trimmed, so every other pin seals as before
  74 | +                "trimmed_leading", "untrimmed_start",      # ruling 33 part 2 (render merged 11e361cc): only when a word
  75 | +                "scorer_pending")                          # is trimmed, so every other pin seals as before (ruling 49 a)
  76 | +TRIMMED_PER_PIN_MAX = 1                                    # ruling 49 (b): package.TRIMMED_PER_LINEUP_MAX
  77 |  TRIM_WORDS = ("but", "and", "so", "well", "now", "yeah")   # ruling 33: the ONE leading word a cut may trim
  78 |  
  79 |  
  80 | @@ -99,13 +100,24 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None):
  81 |  def trim_problems(segments):
  82 |      """[why] for segments whose trim does not match the render's contract (ruling 33 part 2; pinned.validate_schema
  83 |      refuses anything else): "trimmed_leading" and "untrimmed_start" both present or both absent; the trimmed word's
  84 | -    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start."""
  85 | +    canonical token one of TRIM_WORDS; 0 <= untrimmed_start < start. RULING 49: (a) every trimmed clip says
  86 | +    scorer_pending: true (the clip scorer's verdict is pending at the render) and no other clip carries the key;
  87 | +    (b) at most TRIMMED_PER_PIN_MAX trimmed clips."""
  88 |      import canon
  89 |      out = []
  90 | +    n = sum("trimmed_leading" in s or "untrimmed_start" in s for s in segments)
  91 | +    if n > TRIMMED_PER_PIN_MAX:
  92 | +        out.append(f"{n} trimmed clips: at most {TRIMMED_PER_PIN_MAX} until the first is affirmed at validate "
  93 | +                   f"(ruling 49 b)")
  94 |      for i, s in enumerate(segments):
  95 |          has_w, has_s = "trimmed_leading" in s, "untrimmed_start" in s
  96 |          if not has_w and not has_s:
  97 | +            if "scorer_pending" in s:
  98 | +                out.append(f"segment {i}: scorer_pending belongs to a trimmed clip only (ruling 49 a)")
  99 |              continue
 100 | +        if s.get("scorer_pending") is not True:
 101 | +            out.append(f"segment {i}: a trimmed clip must say scorer_pending: true (ruling 49 a: the clip scorer's "
 102 | +                       f"verdict on the trimmed text is pending at the render)")
 103 |          if has_w != has_s:
 104 |              out.append(f"segment {i}: trimmed_leading and untrimmed_start come together (ruling 33 part 2)")
 105 |              continue
 106 | @@ -226,7 +238,7 @@ def to_pin(pk, run_name):
 107 |                       "approved_text": s["text"], "transcript_sha256": s.get("transcript_sha256"),
 108 |                       "time_sensitive": s.get("time_sensitive"), "source_published_at": s.get("source_published_at"),
 109 |                       "speaker": s.get("speaker"),                     # 00:05 ET Nov 13 item 3 (sealed)
 110 | -                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start") if k in s},   # ruling 33 part 2
 111 | +                     **{k: s[k] for k in ("trimmed_leading", "untrimmed_start", "scorer_pending") if k in s},
 112 |                       "time_coords": "youtube", "source": {"kind": "youtube"}})
 113 |      edl_vo = {"intro": pk["vo"]["intro"],
 114 |                "bridges": [{"text": t, "after_clip": a} for t, a in zip(pk["vo"]["bridges"], pk["vo"]["bridges_after_clip"])]}
 115 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 116 | index a8d3d92..c68fcc1 100644
 117 | --- a/tests/package/test_medley.py
 118 | +++ b/tests/package/test_medley.py
 119 | @@ -810,24 +810,38 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 120 |          m, srcs = self.moment("But Bitcoin wins now.")                    # 3 kept words: no statement (glm P0-2)
 121 |          self.assertIsNone(PK.trim_variant(m, srcs))
 122 |  
 123 | -    def test_strict_by_default_and_pending_at_the_render_only_on_the_switch(self):
 124 | +    def test_pending_at_the_render_by_ruling_49_and_strict_on_the_switch(self):
 125 |          m, srcs = self.moment("But Bitcoin has rarely seen six negative weeks back to back in its whole history.")
 126 |          v = PK.trim_variant(m, srcs)
 127 |          line = [{"text": "Bitcoin is the hardest money ever made."}, v, {"text": "Bitcoin wins."}]
 128 | -        self.assertFalse(PK.TRIM_SCORER_PENDING)                      # the default: the render's check, no scorer
 129 | +        self.assertTrue(PK.TRIM_SCORER_PENDING)                       # ruling 49 (07:02): YES
 130 |          r = PK.stand_alone_check(line)
 131 | -        self.assertFalse(r["ok"])                                     # a trimmed segment fails closed, never sealed
 132 | -        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 133 | -        self.assertEqual(r["scorer_pending"], [])
 134 | +        self.assertTrue(r["ok"], r["rows"])
 135 | +        self.assertEqual(r["scorer_pending"], ["clip_01"])
 136 | +        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 137 |          saved = PK.TRIM_SCORER_PENDING
 138 | -        try:                                                          # the orchestrator's explicit yes only
 139 | -            PK.TRIM_SCORER_PENDING = True
 140 | +        try:                                                          # the strict switch: the render's check with
 141 | +            PK.TRIM_SCORER_PENDING = False                            # no scorer fails closed, never sealed
 142 |              r = PK.stand_alone_check(line)
 143 |          finally:
 144 |              PK.TRIM_SCORER_PENDING = saved
 145 | -        self.assertTrue(r["ok"], r["rows"])
 146 | -        self.assertEqual(r["scorer_pending"], ["clip_01"])
 147 | -        self.assertIn("PENDING AT THE RENDER", r["rows"][1]["opener"]["why"])      # stated in the sealed row
 148 | +        self.assertFalse(r["ok"])
 149 | +        self.assertIn("no clip-scorer verdict on the trimmed text", r["rows"][1]["opener"]["why"])
 150 | +        self.assertEqual(r["scorer_pending"], [])
 151 | +
 152 | +    def test_ruling_49_one_trimmed_clip_per_line_up_and_per_pin(self):
 153 | +        self.assertEqual(PK.TRIMMED_PER_LINEUP_MAX, package_pin.TRIMMED_PER_PIN_MAX)
 154 | +        ms = [dict(pm("h", "A", 12.0)), dict(pm("x", "B", 14.0), trimmed_leading="But", untrimmed_start=0.0),
 155 | +              dict(pm("y", "C", 13.0), trimmed_leading="So", untrimmed_start=0.0), dict(pm("z", "D", 13.0))]
 156 | +        for m in ms:
 157 | +            m["hook_onset"] = {"pass": True}
 158 | +        by = {m["moment_id"]: m for m in ms}
 159 | +        self.assertEqual(PK.lineup_ok([by["h"], by["x"], by["y"]])[1], "more than 1 trimmed clip (ruling 49 b)")
 160 | +        segs = PK.lineup_for(angle(["h", "x", "y", "z"], "h"), by, need_onset=True)
 161 | +        self.assertEqual(sum(bool(m.get("trimmed_leading")) for m in segs), 1, [m["moment_id"] for m in segs])
 162 | +        two = [{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True},
 163 | +               {"trimmed_leading": "So", "untrimmed_start": 0.0, "start": 1.0, "scorer_pending": True}]
 164 | +        self.assertIn("2 trimmed clips", package_pin.trim_problems(two)[0])
 165 |  
 166 |      def test_the_pin_seals_the_trim_and_refuses_a_malformed_one(self):
 167 |          segs = [dict(pm("h", "A", 12.0), text="Bitcoin is the hardest money ever made."),
 168 | @@ -843,19 +857,27 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 169 |          pk["gates"] = TestMedleyPackageAndPin().gates(pk)
 170 |          pin = package_pin.to_pin(spk(pk), "test")
 171 |          s1 = pin["segments"][1]
 172 | -        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"]), ("But", 0.0))
 173 | +        self.assertEqual((s1["trimmed_leading"], s1["untrimmed_start"], s1["scorer_pending"]), ("But", 0.0, True))
 174 |          self.assertNotIn("trimmed_leading", pin["segments"][0])                   # untrimmed segments: unchanged
 175 | +        self.assertNotIn("scorer_pending", pin["segments"][0])                    # ruling 49 (a): per trimmed clip
 176 |          mp = pin["moments_package"]
 177 |          args = (mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"], mp["gates"], mp["btc_screen"])
 178 |          self.assertEqual(package_pin.seal(pin["segments"], *args), mp["package_sha256"])
 179 |          other = [dict(x) for x in pin["segments"]]
 180 |          other[1]["trimmed_leading"] = "And"                                       # the trim is inside the seal
 181 |          self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 182 | -        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0}):
 183 | +        other[1]["trimmed_leading"], other[1]["scorer_pending"] = "But", False      # and so is scorer_pending
 184 | +        self.assertNotEqual(package_pin.seal(other, *args), mp["package_sha256"])
 185 | +        for bad in ({"trimmed_leading": "Because"}, {"untrimmed_start": 0.5}, {"untrimmed_start": -1.0},
 186 | +                    {"scorer_pending": False}):                                       # ruling 49 (a) in plain words
 187 |              p = spk(pk)
 188 |              p["segments"][1] = dict(p["segments"][1], **bad)
 189 |              with self.assertRaises(package_pin.PinRefused):
 190 |                  package_pin.to_pin(p, "test")
 191 | +        p = spk(pk)
 192 | +        p["segments"][0] = dict(p["segments"][0], scorer_pending=True)                # only on a trimmed clip
 193 | +        with self.assertRaises(package_pin.PinRefused):
 194 | +            package_pin.to_pin(p, "test")
 195 |          self.assertTrue(package_pin.trim_problems([{"trimmed_leading": "But", "untrimmed_start": 0.0, "start": None}]))
 196 |          p = spk(pk)                                                       # ^ refused, never raised (glm P0-8)
 197 |          p["segments"][1] = {k: v for k, v in p["segments"][1].items() if k != "untrimmed_start"}
 198 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips); the integrator renders them. Your role: a
strict reviewer of how TRIMMED clips are sealed.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- Ruling 33 part 2 lets a clip that opens on ONE of but/and/so/well/now/yeah be cut one word in, when (a) the cut opens
  in quiet (measured at the pin stage as the render measures it), (b) the render's STAND_ALONE clip scorer affirms the
  trimmed clip, and (c) step A is re-judged on the trimmed span.
- The render's clip scorer is gemma3:27b through Ollama on Ultron's GPU0 (run_fresh.stage_validate ->
  story_semantics.LocalLLM). The pin-stage builder may not use any GPU. Until now the builder kept (b) STRICT
  (TRIM_SCORER_PENDING = False): a trimmed segment failed the pin stage's STAND_ALONE, so it was never in a line-up.
- A pin's per-segment keys are sealed in package_sha256 (package_pin.seal). SEALED_LATER keys enter the seal only
  when the segment carries them, so older pins recompute their seal unchanged. The integrator's check_pin_only
  imports this branch's package_pin.py. The render's pinned.validate_schema checks named keys and ignores unknown ones.

The order this diff implements (ORCHESTRATOR RULING 49, 07:02 ET Nov 13, verbatim): "ITEM 42, YES: a trimmed clip may be
sealed with the clip scorer's verdict pending at the render, because stage_validate runs before any render and a
refusal there costs no GPU. Two conditions: (a) the pin says so in plain words (scorer_pending: true per trimmed clip);
(b) a line-up carries at most ONE trimmed clip until the first trimmed clip has been affirmed at validate once, so one
refusal cannot sink a line-up twice. If you can call the same scorer with the same prompt and model at the pin stage
inside budget, do that instead and seal its verdict: say which you did."
- Which we did: pending at the render. The same scorer (gemma3:27b, Ollama, GPU0) cannot run at the pin stage, and no
  other box this builder may use serves that model.

The change:
1. pipeline/package.py:
   - TRIM_SCORER_PENDING = True. stand_alone_check then judges a trimmed segment on its trimmed text with no lock
     marker, and records the trimmed labels in scorer_pending; the sealed STAND_ALONE row says "PENDING AT THE RENDER"
     (both unchanged code).
   - TRIMMED_PER_LINEUP_MAX = 1, enforced in lineup_for (its inline rules), lineup_ok (used by ruling 41's swap and
     item 44's swap), and the no-voice path's added clip.
   - The package's trimmed segment rows carry "scorer_pending": True next to trimmed_leading / untrimmed_start.
2. pipeline/package_pin.py:
   - SEALED_LATER gains "scorer_pending" (sealed only when present).
   - TRIMMED_PER_PIN_MAX = 1.
   - to_pin copies scorer_pending.
   - trim_problems refuses: a trimmed segment without scorer_pending: true; scorer_pending on an untrimmed segment;
     more than TRIMMED_PER_PIN_MAX trimmed segments.
3. tests/package/test_medley.py:
   - The default is now pending, and the strict switch still fails closed.
   - One trimmed clip per line-up: lineup_ok refuses two; lineup_for never picks two; the pin refuses two; the two
     constants are equal.
   - The pin seals scorer_pending: true on the trimmed clip only, and it is inside the seal. Refused: scorer_pending
     false, and scorer_pending on an untrimmed clip.
- test_medley 81 OK; every other suite OK.

Check in particular:
- that a trimmed clip can never be sealed WITHOUT "scorer_pending": true in plain words, and that no clip says pending
  when it is not trimmed;
- that no line-up or pin can carry two trimmed clips, through every path that builds or changes a line-up (lineup_for,
  ruling 41's swap, item 44's swap, the no-voice added clip);
- that pins without a trimmed clip seal exactly as before (the SEALED_LATER contract);
- that nothing claims the scorer affirmed anything.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
