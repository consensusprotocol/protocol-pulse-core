# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-20261114_2131
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 20777 / out 786 usd_reported=0.042059 usd~0.124 (upper-bound price)

**CODE AUDIT: pp-selectid-20261114_2131 (parallel reviewer)**

**Summary:** The diff implements the orchestrator's 21:10/21:31 rulings (visual-3 burned-caption handling, 16:9-only "formats" sealing + hold, ROLE claim gate, spotlight_source "format" recording, reseal directive for same-moment story replacement). It stays within "smallest diff / no new renderer / GPU0 only" constraints. Core logic for formats_of/seal, layout_block, clean_visual, vo_fidelity ROLE_RE, and prompt updates is sound and matches the provided tests. New visual sampling (1 s, 40 tiles) and prompt explicitly fix the root cause that let Blockware captions be missed. Release-auth, pin SHA, and selection-lock invariants are preserved (formats omitted when absent; old pins recompute identically).

**Findings:**

[P1] **Breaks LAW 22 (and L-d protected preview).** `layout_block()` and `clean_visual()` now reject any record where `version != "visual-3"` (or missing `burned_in` list). Frozen `references/v2f_2026-11-06` and the 2026-11-11 preview reference use earlier visual records (visual-1/visual-2). These will now fail `clean_visual` / `layout_block` on re-run, preventing byte-identical re-renders. No backward-compatibility exception, cached-record bypass, or reference-visual upgrade path is present. This is a hard regression on a governing law that must be fixed before merge. (The `RENDER_16X9_ONLY` hold compounds the issue for any re-validated old pins.)

[P2] Hard-coded `RENDER_16X9_ONLY = False` (with 15-line comment) plus the temporary hold message in `layout_block` creates a merge-time landmine once the integrator's format-aware render lands. Should be a config constant or feature flag to keep the diff minimal and auditable.

[P2] `tail_variant.py` mutates the caller's `moments` dict in-place when applying a reseal directive (`m["derived_from"] = {...}`). While tests pass and the directive is strict, this side-effect violates the "immutable input" pattern used elsewhere in the pipeline and risks subtle bugs if the same moment object is referenced by multiple pools.

[P3] Vision prompt for captions now requires the model to evaluate sliding 9:16 crops "while speaker's whole face stays inside with a tenth-of-frame margin." This is semantically complex; LLM variance could produce inconsistent "whole"/"cut" verdicts even on identical sheets. (Matches the ruling but increases flakiness of a REQUIRED gate.)

[P3] `vo_fidelity.ROLE_RE` + normalization (`replace("-","").rstrip("s")`) works for the test cases but is a parallel ad-hoc normalizer outside `pipeline/canon.py` (cf. L-k ONE CANONICAL FORM and test_canon.py's "TestSites fails any ad-hoc normaliser"). Minor duplication.

[P3] New test files (`test_formats.py`, `test_role_claims.py`) are thorough and pin the exact behaviors requested in "PLEASE CHECK," but `test_role_claims` is example-driven rather than exhaustive on all role words / slot combinations. Nit.

All other governing laws (SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, M2, M12, fail-closed, canonical-form routing, release_auth exact-byte semantics, etc.) are respected. No criminal, exploit, or guideline violations. No changes to audio cuts, punctuation, edge-word fidelity, sign-off transcription, or model JSON validation.

P1_OR_WORSE: 1

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 23346 / out 1879 usd_reported=0.004424 usd~0.098 (upper-bound price)

I have reviewed the code changes against the Governing Laws and the specific questions posed. Here is the audit.

### Findings

**1. [P1] `formats` Seal Integrity Violation (L-j / LAW 20)**
In `pipeline/package_pin.py`, the `seal` function includes `formats` in the hash body *only* if `formats is not None` (lines 43-44). However, `pin_seal` (lines 48-54) passes `formats=mp.get("formats")`.
*   **The Defect:** If a pin is created with `formats: ["16x9"]`, the seal includes it. If an attacker or a bug strips the `formats` key from the `moments_package` JSON before verification, `mp.get("formats")` returns `None`. The `seal` function then omits `formats` from the hash body. Because the rest of the body (segments, vo, etc.) is identical, the SHA256 hash will **match** the original seal.
*   **Consequence:** A 16:9-only pin can be mutated into a "both formats" pin (by deleting the key) without breaking the cryptographic seal. This violates **L-j** ("all release gates passed... on exactly the bytes that are sent") and **LAW 20** (gate thresholds/integrity). The test `test_formats.py` (line 411-413) claims to test this ("stripping it breaks the seal"), but based on the code logic provided, it would **fail** to detect the mutation because the hash would remain valid.
*   **Fix:** The `seal` function must always include the `formats` key in the hash body, defaulting to `None` or `[]` if absent, so that the presence/absence of the key changes the hash. Alternatively, `pin_seal` must verify that if `formats` is expected (based on segment visuals), it is present, and raise an error if missing, rather than relying on the hash to catch the omission.

**2. [P2] `ROLE_RE` False Positives on Common Verbs**
In `pipeline/vo_fidelity.py`, `ROLE_RE` includes `hosts?` and `anchors?` (line 338).
*   **The Defect:** The regex `\b((?:co-?)?hosts?|...|anchors?|...)\b` will match the verb "hosts" in sentences like "The event **hosts** 500 people" or "Bitcoin **anchors** the economy." It will also match "anchor" in "The **anchor** of the portfolio."
*   **Consequence:** The `ROLE` gate will flag these sentences as violations unless the cited clip explicitly contains the word "host" or "anchor" as a noun referring to a person. This creates a high false-positive rate for common financial/tech vocabulary, potentially blocking valid captions/titles.
*   **Fix:** The regex should be more specific to noun usage or context, or the check should verify that the role word is used as a noun (e.g., preceded by an article or determiner, or not followed by a verb object). Given the "Fail Closed" law, this is a P2 because it blocks valid content, but it doesn't let bad content through.

**3. [P3] `RENDER_16X9_ONLY` Hardcoded Flag**
In `pipeline/visual_pin.py`, `RENDER_16X9_ONLY = False` is a module-level constant (line 166).
*   **The Defect:** This flag controls whether 16:9-only clips are held or allowed. It is not configurable via environment variable or config file.
*   **Consequence:** When the integrator's format-aware release lands, a code change is required to flip this flag. This is acceptable for a "smallest diff" approach but should be documented clearly. The comment says "Flipped on its word... in one audited change," which is compliant.

**4. [P3] `times()` Edge Case**
In `pipeline/visual_pin.py`, `times()` (line 228) uses `while t < last - 0.01`.
*   **The Defect:** If `dur` is very small (e.g., 0.05s), `last` is 0.0. `t` starts at 1.0. The loop doesn't run. `ts` is `[0.0]`. Then `if last > 0` is false. Returns `[0.0]`. This is correct.
*   **Observation:** The change from `last - 0.25` to `last - 0.01` ensures the last frame is included if it's within 10ms of the end. This is correct for the "1 frame a second" requirement.

**5. [P3] `formats_of` Intersection Logic**
In `pipeline/package_pin.py`, `formats_of` (line 24) returns `["16x9"]` if *any* segment has `formats == ["16x9"]`.
*   **Observation:** The docstring says "a medley takes the intersection." If one clip is 16:9-only and another is both, the intersection is 16:9-only. The code returns `["16x9"]` if *any* is 16:9-only. This is correct for the intersection logic (if any clip *cannot* be 9:16, the medley cannot be 9:16).

### Answers to Specific Questions

1.  **Can a 16:9-only clip be sealed while `RENDER_16X9_ONLY` is False?**
    **No.** `layout_block` in `visual_pin.py` (line 307) checks `if formats(rec) and not RENDER_16X9_ONLY:` and returns a block reason. This prevents the clip from being eligible, so it cannot be sealed.

2.  **Can the ROLE rule pass a role no cited clip states, or refuse a sentence with no role word?**
    **No / No.**
    *   If a role is not in the cited clip's words, `bad` will be non-empty, and `V("ROLE", ...)` is called. It fails.
    *   If a sentence has no role word, `ROLE_RE.findall` returns empty, `roles` is empty

## CLAUDE'S CYCLE 1 CONSENSUS
# Cycle 1 consensus: pp-selectid audit 20261114_2131 (the 21:10 fixes, the sealed formats, the re-seal)

Reviewers under ruling 107 (2): qwen3.8-27b (P1_OR_WORSE 1) and glm-5.3-flash. glm hit its 24,000-token cap with no
closing count, so the driver treated it as no answer and asked Grok as the third (P1_OR_WORSE 1). Cost: $0.0501
vendor-reported (qwen $0.0044, glm $0.0036, Grok $0.0421).

REFUTED, with evidence:
- qwen P1, "stripping formats leaves the seal valid". A pin sealed with "formats" has that key in its hashed body.
  pin_seal on a stripped pin hashes a body WITHOUT it, so the digest differs. test_formats asserts exactly this
  ("stripping it breaks the seal"), and mutation F3 (the recompute ignoring formats) is killed.
- Grok P1, "the version guard breaks the protected preview and the v2f references (L-d, LAW 22)". None of the
  reference or render checks calls the builder's visual gate. A grep of pipeline/check_preview_reference.py,
  pipeline/regression.sh, regression_test.sh, release_auth.py, pinned.py and run_fresh.py finds no visual_pin,
  layout_block or clean_visual. The guard runs only at this builder's pin stage, for new pins.
- glm P1-5, "format may seal a stringified dict". spotlight.layout_for's record is {"layout": <one of LAYOUTS, a
  string>, ...}: check_layout returns v["layout"], validated against LAYOUTS. So .upper() is "FIRST_HAND" /
  "CONVERSATION".
- glm P1-33, "formats may never reach the pin". package._package seals each segment's visual as
  visual_pin.sealed(m["visual"]) (package.py:383), and sealed() now carries "formats". The chain is visual_for ->
  m["visual"] -> sealed() -> the segment -> package_pin.formats_of -> moments_package["formats"].
- glm P1-39, "the re-seal's day place is not wired". Both call sites exist in unchanged code:
  spotlight.pool -> day_taken(spotlit, channel, day, m["derived_from"]["alternative_to"]) (spotlight.py:219), and
  at the pin proof_ledger.spot_place reads pk["spotlight"]["derived_from"], which spotlight copies from the moment
  (spotlight.py:1137).

IMPLEMENTED:
- glm P1-17: check() now sorts the blocking items first, then a CUT caption, so the 16:9-only decision survives
  TEXTS_MAX. Test: a cut caption listed after 14 whole ones keeps formats ["16x9"].
- glm P1-34/50 and Grok P3 (L-k): the ROLE comparison now uses canon. Each role noun is its canonical token
  (canon_tokens(...)[-1]), compared with the cited clip's canonical tokens. The hyphen and plural stripping is gone.
  Test: a capitalised, sentence-initial "Analyst here." supports "an ANALYST"; "analysts" is another word.
- glm P1-6/53 (the prompt and the gate disagreed): a role word inside a show or channel name the line credits is
  no claim (manifest_terms). Test: "From Analyst Answers: ..." passes, and "Our guests ..." still fails.
- Grok P2: the re-seal no longer mutates the caller's moment. for_pool returns a marked COPY in its place
  (replaced + variants, as a directive variant does). Test: the caller's rec

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_20261114_2131/C2_STEP.diff (712 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 28bcc89..967f665 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -943,6 +943,9 @@ RULES (a line that breaks one is rejected):
   6 |  - No price level; no advice to buy, sell or use leverage; no quotes except a clip's exact words; no "destroys",
   7 |    "slams", "exposes", "admits", "confirms", "caught".
   8 |  - A line that names a show, a person or Bitcoin's price cites the clips it comes from.
   9 | +- Never give anyone a ROLE the clips' own words do not state: no "guest", "host", "co-host", "analyst", "expert",
  10 | +  "economist", "strategist", "interviewer", "presenter", "anchor", "panelist" or "commentator". A role is a claim
  11 | +  (law L-v): say "he", "she" or "the speaker", or credit the show.
  12 |  {style}
  13 |  {extra}Return ONLY this JSON object: {{"takeaway": {{"text": "...", "cites": []}}, "bridge": {bridge_shape},
  14 |  "title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}}}}"""
  15 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
  16 | index bfbed07..1f409cf 100644
  17 | --- a/pipeline/package_pin.py
  18 | +++ b/pipeline/package_pin.py
  19 | @@ -187,7 +187,18 @@ def window_problems(segments, now=None):
  20 |      return out
  21 |  
  22 |  
  23 | -def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None):
  24 | +def formats_of(segments):
  25 | +    """RULING 93 AMENDED (orchestrator 21:10 ET Nov 14; the integrator's spelling, 21:31): the formats a pin may be
  26 | +    rendered in. ["16x9"] when ANY segment's sealed visual record says so (a source caption the 9:16 crop cuts: a
  27 | +    medley takes the intersection), else None: absent means both formats, as every pin before it."""
  28 | +    for s in segments or []:
  29 | +        if ((s or {}).get("visual") or {}).get("formats") == ["16x9"]:
  30 | +            return ["16x9"]
  31 | +    return None
  32 | +
  33 | +
  34 | +def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shape=None, first_comment=None,
  35 | +         formats=None):
  36 |      """sha256 over the gated bytes, in a canonical form both sides compute: the segments (video, start, end, the exact
  37 |      words, the transcript sha, and each SEALED_LATER field the segment carries), the VO the renderer will speak (intro,
  38 |      bridges with after_clip), the sign-off, the ONE title and caption (law L-t), and the gate inventory.
  39 | @@ -214,6 +225,8 @@ def seal(segments, edl_vo, signoff, title, caption, gates, btc_screen=None, shap
  40 |      if shape == "spotlight":                               # ruling 90: the closing line, the kind and the comment,
  41 |          body["vo"]["closing"] = edl_vo.get("closing")      # sealed; keyed on the kind alone, so no medley's body
  42 |          body["shape"], body["first_comment"] = shape, first_comment   # can change (audit 2322 C1, glm)
  43 | +    if formats is not None:                                # ruling 93 amended: "formats", only when present, so every
  44 | +        body["formats"] = formats                          # pin before it recomputes to its own sha
  45 |      return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
  46 |  
  47 |  
  48 | @@ -225,7 +238,8 @@ def pin_seal(pin):
  49 |      shape = mp.get("shape")
  50 |      return seal(pin["segments"], mp["edl_vo"], mp["signoff_expected"], mp["title"], mp["caption"], mp["gates"],
  51 |                  mp.get("btc_screen"), shape="spotlight" if shape == "spotlight" else None,
  52 | -                first_comment=mp.get("first_comment") if shape == "spotlight" else None)
  53 | +                first_comment=mp.get("first_comment") if shape == "spotlight" else None,
  54 | +                formats=mp.get("formats"))
  55 |  
  56 |  
  57 |  def affirmed_verdict(s):
  58 | @@ -451,8 +465,9 @@ def to_pin(pk, run_name):
  59 |      spot = pk.get("shape") == "spotlight"                 # ruling 90: the agreed contract
  60 |      if spot:
  61 |          edl_vo["closing"] = pk["vo"].get("closing")
  62 | +    fmts = formats_of(segs)                               # ruling 93 amended: sealed, only when 16:9-only
  63 |      sha = seal(segs, edl_vo, pk["vo"]["signoff"], pk["title"], pk["caption"], pk["gates"], pk.get("btc_screen"),
  64 | -               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None)
  65 | +               shape="spotlight" if spot else None, first_comment=pk["first_comment"] if spot else None, formats=fmts)
  66 |      return {"schema": SCHEMA, "story_id": f"moments-{run_name}-{sha[:8]}",
  67 |              "label": "bitcoin", "headline": pk["title"],
  68 |              "approved_by": "machine:pp-selectid moments-first (REVIEW ONLY, not approved by a human)",
  69 | @@ -481,6 +496,7 @@ def to_pin(pk, run_name):
  70 |                                     if spot else {}),
  71 |                                  "gates": pk["gates"],
  72 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
  73 | +                                **({"formats": fmts} if fmts is not None else {}),   # ruling 93 amended (sealed)
  74 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
  75 |                                             "derived_from": "gates (every required row exactly PASS, checked above)",
  76 |                                             "models": pk.get("models")},
  77 | diff --git a/pipeline/spotlight.py b/pipeline/spotlight.py
  78 | index 5f7daa3..6011dcf 100644
  79 | --- a/pipeline/spotlight.py
  80 | +++ b/pipeline/spotlight.py
  81 | @@ -474,11 +474,12 @@ def layout_for(router, m, vrec, cache_path=None, seed=7, evidence=None):
  82 |  def clean_visual(v):
  83 |      """RULING 90's "visual check clean" with RULING 93: measured, no ruling-70 flag (a third person shown as a still
  84 |      with a negative claim, on-screen text that asserts beyond the words), not blocked as a hook, and eligible on its
  85 | -    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) is
  86 | -    eligible and flagged for the orchestrator, so it does not make the clip unclean."""
  87 | +    own frames (visual_pin.layout_block). A ruling-93 "burned_in" flag (a lower third or bug that sits whole) and a
  88 | +    "burned_caption" flag (ruling 93 amended, 21:10 Nov 14: the source's own captions never make a clip ineligible)
  89 | +    are flagged for the orchestrator, so they do not make the clip unclean."""
  90 |      import visual_pin as VP
  91 |      return (v or {}).get("measured") is True and not VP.hook_block(v) and not VP.layout_block(v) and \
  92 | -        not [f for f in v.get("flags") or [] if f.get("kind") != "burned_in"]
  93 | +        not [f for f in v.get("flags") or [] if f.get("kind") not in ("burned_in", "burned_caption")]
  94 |  
  95 |  
  96 |  def alone_score(m):
  97 | @@ -531,6 +532,9 @@ RULES (a line that breaks one is rejected):
  98 |  - No price level; no advice to buy, sell or use leverage; no quotes except the clip's exact words; no "destroys",
  99 |    "slams", "exposes", "admits", "confirms", "caught".
 100 |  - A line that names a show, a person or Bitcoin's price cites the clip.
 101 | +- Never give anyone a ROLE the clip's own words do not state: no "guest", "host", "co-host", "analyst", "expert",
 102 | +  "economist", "strategist", "interviewer", "presenter", "anchor", "panelist" or "commentator". A role is a claim
 103 | +  (law L-v): say "he", "she" or "the speaker", or credit the show.
 104 |  {style}
 105 |  {extra}Return ONLY this JSON object: {{"title": {{"text": "...", "cites": []}}, "caption": {{"text": "...", "cites": []}},
 106 |  "comment": {{"text": "...", "cites": []}}, "closing": {{"text": "...", "cites": []}} or null}}"""
 107 | @@ -753,6 +757,8 @@ def inventory(pk, m, fid, dup, rt_ok, style, cx, a_off, a_two, exc, truth, pre,
 108 |                                      bool((src_rec.get("layout") or {}).get("replayed", False)),
 109 |                                      measured=(src_rec.get("layout") or {}).get("measured") is True,
 110 |                                      why=src_rec.get("why"), evidence=src_rec.get("evidence"), layout=src_rec.get("layout"),
 111 | +                                    format=str((src_rec.get("layout") or {}).get("layout") or "").upper() or None,  # 21:10
 112 | +                                    #   Nov 14: WHICH of CONVERSATION / FIRST_HAND passed, on the pin's sealed row
 113 |                                      rule="ruling 92 amended (09:03 Nov 14): the layout decides (conversation or "
 114 |                                           "first-hand); the captions are evidence, refusing alone only with zero "
 115 |                                           "speaker changes in the 10 minutes around the clip")
 116 | diff --git a/pipeline/tail_variant.py b/pipeline/tail_variant.py
 117 | index 36973ce..88854f8 100644
 118 | --- a/pipeline/tail_variant.py
 119 | +++ b/pipeline/tail_variant.py
 120 | @@ -125,6 +125,14 @@ def for_pool(moments, sources, ctx, results_dir, ceil_s, directives=None):
 121 |                  notes[mid] = "the directive: no variant, the parent is one sentence (no earlier boundary)"
 122 |              continue                                     # one sentence: no earlier boundary
 123 |          wanted = []
 124 | +        if (directives or {}).get(mid, {}).get("reseal") is True:   # RULING 93 AMENDED + 106 (21:31 Nov 14): the SAME
 125 | +            d = directives[mid]                                    # moment sealed again (16:9-only) in the place of
 126 | +            out.append(dict(m, derived_from={"ruling": "93 amended", "reseal_of": d["alternative_to"],   # its own
 127 | +                                             "alternative_to": d["alternative_to"], "directive": d.get("by"),  # earlier
 128 | +                                             "why": d.get("why") or ""}))     # story, never a second spotlight: a
 129 | +            replaced.add(mid)                            # marked COPY in its place, the caller's record untouched
 130 | +            notes[mid] = f"the directive: re-sealed in the place of {d['alternative_to']}"   # (audit 2131 C1, grok)
 131 | +            continue
 132 |          if mid in (directives or {}):                    # the orchestrator's directive: this variant, in its place
 133 |              try:
 134 |                  src = CI.source_for(m, sources)
 135 | diff --git a/pipeline/visual_pin.py b/pipeline/visual_pin.py
 136 | index ef4a557..844a320 100644
 137 | --- a/pipeline/visual_pin.py
 138 | +++ b/pipeline/visual_pin.py
 139 | @@ -21,6 +21,11 @@ Per clip (a moment's [start, end]):
 140 |    not wholly in the 16:9, that the 9:16 edge would cut mid-word, or that covers the speaker, makes the clip NOT
 141 |    eligible in any role (per clip, never by channel name); one that sits whole in the 16:9 and wholly in or out of the
 142 |    9:16 is eligible and sealed as a "burned_in" FLAG for the orchestrator.
 143 | +- RULING 93 AMENDED (orchestrator 21:10 ET Nov 14), visual-3: the source's own BURNED CAPTIONS of the spoken words are
 144 | +  asked for explicitly (question 4's kind "caption", with the frame times each shows in), on a sheet of one frame a
 145 | +  second (TILES 36, the 35 s ceiling). Visual-2 asked to leave "subtitles of the spoken words" out, twice, and missed
 146 | +  Blockware's. A caption never makes a clip ineligible: one the 9:16 crop cuts mid-word makes it 16:9-ONLY (formats():
 147 | +  "formats": ["16x9"], sealed in the visual record), and each caption is flagged ("burned_caption").
 148 |  - hook_block(): why the clip may not be the HOOK, or None. Step A passes only a clip whose view is "own_sincere" (the
 149 |    speaker's own assertion: context_integrity.a_failures), so no step-A verdict confirms a claim as REPORTED fact; a
 150 |    third_person finding therefore blocks the hook (fail closed) until step A is asked that.
 151 | @@ -32,11 +37,18 @@ import os
 152 |  import subprocess
 153 |  import threading
 154 |  
 155 | -VERSION = "visual-2"                     # RULING 93 (23:58 ET Nov 13): question 4, burned-in text and the 9:16
 156 | -ROLE = "visual_check"
 157 | -TILES, EVERY_S, TILE_W = 8, 2.0, 480
 158 | +VERSION = "visual-3"                     # RULING 93 AMENDED (21:10 ET Nov 14): the source's burned captions asked for
 159 | +ROLE = "visual_check"                    #   explicitly, one frame a second (visual-2: ruling 93, 23:58 ET Nov 13)
 160 | +TILES, EVERY_S, TILE_W, COLS = 40, 1.0, 320, 6   # 21:10 Nov 14: "at least one frame a second across the span" (the
 161 | +#   35 s ceiling takes 36; 40 leaves room); 6 x 320 px across keeps the sheet 1920 px wide (visual-2 sampled 8 at 480 px:
 162 | +#   one every 3.27 s on Blockware's 22.94 s, and its question excluded the captions it showed)
 163 |  HOW = ("still", "photo", "graphic", "none")
 164 | -BURNED = ("ticker", "crawl", "lower_third", "bug")      # ruling 93: question 4's kinds
 165 | +BURNED = ("ticker", "crawl", "lower_third", "bug", "caption")   # ruling 93: question 4's kinds; "caption" (ruling 93
 166 | +CAPTION = "caption"                                    # amended): the source's own burned subtitles of the words
 167 | +RENDER_16X9_ONLY = False      # the integrator's render cannot yet pass a 16:9-only pin (its message 21:2x Nov 14: its
 168 | +#   release_auth needs the 9:16 rows; it builds the format-aware path, audited): until it says so, a clip that is
 169 | +#   16:9-only is HELD here (layout_block), and no 16:9-only pin is sealed. Flipped on its word, with the package-level
 170 | +#   "formats" (package_pin), in one audited change.
 171 |  RUNNING = ("ticker", "crawl")                          # ruling 93: "a ticker or crawl = not eligible"
 172 |  IN_9X16 = ("whole", "out", "cut")
 173 |  FORMAT = "bv*[height<=480][ext=mp4]/bv*[height<=480]/b[height<=480]"
 174 | @@ -53,25 +65,33 @@ Answer four questions from the frames only:
 175 |     person taking part in the show) while the clip's words make a NEGATIVE claim (a mistake, an accusation, a scandal,
 176 |     a crime, a failure)? Report any NAME the screen shows as TEXT with that person. Never name anyone from a face: only
 177 |     text on the screen names a person.
 178 | -2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not subtitles of the spoken
 179 | -   words, not the channel's logo), copied exactly, each with whether it ASSERTS something the clip's words do not.
 180 | +2. on_screen_text: every headline graphic, chyron, banner or title card the SOURCE shows (not its captions of the
 181 | +   spoken words, which are question 4's; not the channel's logo), copied exactly, each with whether it ASSERTS
 182 | +   something the clip's words do not.
 183 |  3. lower_third: the on-screen name strap (lower third) of the person speaking, copied exactly, or null.
 184 | -4. burned_in: every piece of text or graphic burned into the SOURCE picture that stays on screen: a ticker or a crawl
 185 | -   (text that runs or scrolls across the frame), a lower third (a name or headline strap), or a channel bug (a logo or
 186 | -   watermark). Not subtitles of the spoken words. For each say whether it sits WHOLLY inside the frame, and how the
 187 | +4. burned_in: every piece of text or graphic burned into the SOURCE picture: a ticker or a crawl (text that runs or
 188 | +   scrolls across the frame), a lower third (a name or headline strap), a channel bug (a logo or watermark), AND THE
 189 | +   SOURCE'S OWN BURNED-IN CAPTIONS OR SUBTITLES of the spoken words (kind "caption": styled words that show what is
 190 | +   being said, often large and animated, word by word or phrase by phrase). Look at EVERY frame: list each distinct
 191 | +   caption text you can read as its own item, copied exactly, with "at": the frame times (seconds) it shows in.
 192 | +   For each item say whether it sits WHOLLY inside the frame, and how the
 193 |     VERTICAL 9:16 version would treat it. The 9:16 version shows, for ONE speaker, a full-height strip about one third
 194 |     of the frame's width, centred on the speaker's face; for two or three people, a band around each face, stacked; for
 195 |     a shared screen (a chart, a slide, b-roll), the whole frame. "in_9x16" is "whole" (wholly inside the 9:16 picture),
 196 | -   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). "covers_speaker": does it cover
 197 | -   the speaking person's face or mouth?
 198 | +   "out" (wholly outside it) or "cut" (the 9:16 edge would cut through it mid-word). FOR A CAPTION the strip may slide
 199 | +   left or right, but only so far that the speaker's WHOLE face stays inside it with a margin (a tenth of the frame's
 200 | +   width from either edge): "whole" if ONE such position shows the caption whole, "cut" if every such position cuts it
 201 | +   mid-word, "out" if it lies outside every such position. "covers_speaker": does it cover the speaking person's face
 202 | +   or mouth? An empty list means you read NO text at all burned into any frame.
 203 |  
 204 |  Return ONLY this JSON object:
 205 |  {{"third_person": {{"shown": true or false, "how": "still|photo|graphic|none", "words_negative": true or false,
 206 |    "name_on_screen": "<the on-screen text naming them> or null", "finding": "<one sentence>"}},
 207 |   "on_screen_text": [{{"text": "...", "asserts_beyond_words": true or false, "why": "..."}}],
 208 |   "lower_third": {{"name": "<the name on the strap> or null", "text": "<the strap's full text> or null"}},
 209 | - "burned_in": [{{"kind": "ticker|crawl|lower_third|bug", "text": "<its text, copied>", "whole_in_16x9": true or false,
 210 | -   "in_9x16": "whole|out|cut", "covers_speaker": true or false}}]}}"""
 211 | + "burned_in": [{{"kind": "ticker|crawl|lower_third|bug|caption", "text": "<its text, copied>",
 212 | +   "whole_in_16x9": true or false, "in_9x16": "whole|out|cut", "covers_speaker": true or false,
 213 | +   "at": [<the frame times it shows in, seconds>]}}]}}"""
 214 |  
 215 |  
 216 |  def load_cache(path):
 217 | @@ -95,7 +115,7 @@ def save_cache(path, cache):
 218 |  def key(m):
 219 |      """The cache key: the moment and span, VERSION, and a digest of everything else the verdict reads (the clip's
 220 |      words, the prompt, the sheet's parameters; audit 1541 C1). A hit is used only on the same sheet bytes."""
 221 | -    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, FORMAT, str(m.get("text") or "")])
 222 | +    inputs = json.dumps([PROMPT, TILES, EVERY_S, TILE_W, COLS, FORMAT, str(m.get("text") or "")])
 223 |      return (f"{m['moment_id']}:{float(m['start']):.3f}-{float(m['end']):.3f}:{VERSION}:"
 224 |              f"{hashlib.sha256(inputs.encode()).hexdigest()[:16]}")
 225 |  
 226 | @@ -109,12 +129,12 @@ def _sha_of(path):
 227 |  
 228 |  
 229 |  def times(dur, every=EVERY_S, tiles=TILES):
 230 | -    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame; at most `tiles`,
 231 | -    the first and the last always kept."""
 232 | +    """The stills' offsets in the clip: the cut-in frame, one every `every` seconds, the last frame (so no gap is ever
 233 | +    longer than `every`); at most `tiles`, the first and the last always kept."""
 234 |      last = max(0.0, dur - 0.05)
 235 |      ts = [0.0]
 236 |      t = every
 237 | -    while t < last - 0.25:
 238 | +    while t < last - 0.01:
 239 |          ts.append(round(t, 2))
 240 |          t += every
 241 |      if last > 0:
 242 | @@ -156,7 +176,7 @@ def sheet(video, start, end, work_dir):
 243 |          with Image.open(out) as im:
 244 |              tiles.append(im.convert("RGB").copy())
 245 |          os.remove(out)
 246 | -    cols = min(4, len(tiles))
 247 | +    cols = min(COLS, len(tiles))
 248 |      rows = (len(tiles) + cols - 1) // cols
 249 |      w, h = tiles[0].size
 250 |      canvas = Image.new("RGB", (cols * w, rows * h), (0, 0, 0))
 251 | @@ -196,12 +216,18 @@ def check(v):
 252 |      if not isinstance(bi, list) or any(
 253 |              not isinstance(x, dict) or x.get("kind") not in BURNED or not isinstance(x.get("text"), (str, type(None)))
 254 |              or type(x.get("whole_in_16x9")) is not bool or x.get("in_9x16") not in IN_9X16 or
 255 | -            type(x.get("covers_speaker")) is not bool for x in bi):        # a wordless bug may carry no text
 256 | -        raise ValueError("burned_in out of contract (ruling 93)")
 257 | +            type(x.get("covers_speaker")) is not bool or
 258 | +            (x["kind"] == CAPTION and not (x.get("text") or "").strip()) or
 259 | +            not isinstance(x.get("at", []), list) or
 260 | +            any(type(a) not in (int, float) for a in x.get("at") or []) for x in bi):   # a wordless bug may carry
 261 | +        raise ValueError("burned_in out of contract (ruling 93)")                          # no text; a caption must
 262 |      items = [{"kind": x["kind"], "text": (x.get("text") or "").strip()[:TEXT_CHARS],
 263 | -              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"]}
 264 | +              "whole_in_16x9": x["whole_in_16x9"], "in_9x16": x["in_9x16"], "covers_speaker": x["covers_speaker"],
 265 | +              **({"at": sorted({round(float(a), 2) for a in x["at"]})[:TILES]} if x.get("at") else {})}
 266 |               for x in bi]
 267 | -    items = sorted(items, key=lambda x: burned_block(x) is None)   # the blocking ones first, so a cut never hides
 268 | +    items = sorted(items, key=lambda x: (burned_block(x) is None,              # the blocking ones first, then a
 269 | +                                         not (x["kind"] == CAPTION and x["in_9x16"] == "cut")))   # cut caption (audit
 270 | +    #   2131 C1, glm: the 16:9-only decision must survive TEXTS_MAX), so a cut never hides
 271 |      #   one (audit 0003 C1, glm: a ticker listed 13th would otherwise pass)
 272 |      if not isinstance(tp, dict) or type(tp.get("shown")) is not bool or tp.get("how") not in HOW or \
 273 |              type(tp.get("words_negative")) is not bool or not isinstance(tp.get("finding"), str):
 274 | @@ -233,14 +259,30 @@ def flags(v):
 275 |      out += [{"kind": "on_screen_text", "text": x["text"], "why": x["why"]} for x in v["on_screen_text"]
 276 |              if x["asserts_beyond_words"]]
 277 |      out += [{"kind": "burned_in", "text": x["text"], "item": x["kind"], "in_9x16": x["in_9x16"]}   # ruling 93: an
 278 | -            for x in v.get("burned_in") or [] if not burned_block(x)]            # eligible lower third or bug,
 279 | +            for x in v.get("burned_in") or [] if not burned_block(x) and x["kind"] != CAPTION]   # eligible lower
 280 | +    out += [{"kind": "burned_caption", "text": x["text"], "in_9x16": x["in_9x16"],              # third or bug, and
 281 | +             **({"at": x["at"]} if x.get("at") else {})}                                          # (ruling 93 amended)
 282 | +            for x in v.get("burned_in") or [] if x["kind"] == CAPTION]                            # each burned caption,
 283 |      return out                                                                   # flagged for the orchestrator
 284 |  
 285 |  
 286 | +def formats(rec):
 287 | +    """RULING 93 AMENDED (orchestrator 21:10 ET Nov 14): "source-burned captions that the 9:16 crop cuts mid-word make the
 288 | +    clip 16:9-ONLY (sealed as formats: ['16x9'], the integrator renders and delivers that format alone) unless a crop
 289 | +    exists that shows them whole; they do not make the clip ineligible." -> ["16x9"] when any burned caption of a
 290 | +    measured record is "cut" in the 9:16, else None (both formats, as before)."""
 291 | +    if not (rec or {}).get("measured"):
 292 | +        return None
 293 | +    cut = [x for x in rec.get("burned_in") or [] if x.get("kind") == CAPTION and x.get("in_9x16") == "cut"]
 294 | +    return ["16x9"] if cut else None
 295 | +
 296 | +
 297 |  def burned_block(x):
 298 |      """RULING 93 on one burned-in item -> why it makes the clip NOT eligible, or None (eligible, flagged): a ticker or
 299 |      a crawl; a lower third or bug that is not wholly inside the 16:9, that the 9:16 edge would cut through mid-word, or
 300 |      that covers the speaker."""
 301 | +    if x["kind"] == CAPTION:                     # ruling 93 amended: a burned caption never makes a clip ineligible;
 302 | +        return None                              # cut by the 9:16 it makes it 16:9-only (formats())
 303 |      if x["kind"] in RUNNING:
 304 |          return f"a {x['kind']} ({x['text'][:80]!r}): not eligible"
 305 |      if not x["whole_in_16x9"]:
 306 | @@ -259,7 +301,12 @@ def layout_block(rec):
 307 |          return "its visual check is not measured (law L-m)"
 308 |      if not isinstance(rec.get("burned_in"), list):
 309 |          return "ruling 93: the burned-in text question was not asked (an earlier visual record)"
 310 | +    if rec.get("version") != VERSION:            # 21:10 Nov 14: visual-2 never asked for the source's captions
 311 | +        return f"its visual record is {rec.get('version')!r}, which never asked for the source's burned captions"
 312 |      why = [w for w in (burned_block(x) for x in rec["burned_in"]) if w]
 313 | +    if formats(rec) and not RENDER_16X9_ONLY:    # ruling 93 amended: 16:9-only, which the render cannot pass yet
 314 | +        why.append("16:9-only (a burned caption the 9:16 crop cuts mid-word, ruling 93 amended), and the integrator's "
 315 | +                   "render cannot pass a 16:9-only pin until its format-aware release lands: held")
 316 |      return (f"ruling 93 ({len(why)} item(s)): " + "; ".join(why))[:600] if why else None   # (audit 0003 C2)
 317 |  
 318 |  
 319 | @@ -280,7 +327,7 @@ def sealed(rec):
 320 |      """The part of a visual record a pin seals (package_pin.SEALED_LATER "visual"): the findings, the flags, the sheet's
 321 |      name, sha256 and times (the sheet itself is copied beside the pin), the back-end. Never a scratch path or a cost."""
 322 |      out = {k: rec[k] for k in ("version", "measured", "flags", "third_person", "on_screen_text", "lower_third",
 323 | -                               "burned_in", "burned_in_truncated", "backend", "replayed", "why") if k in rec}
 324 | +                               "burned_in", "burned_in_truncated", "formats", "backend", "replayed", "why") if k in rec}
 325 |      if isinstance(rec.get("sheet"), dict):
 326 |          out["sheet"] = {k: rec["sheet"][k] for k in ("name", "sha256", "times") if k in rec["sheet"]}
 327 |      return out
 328 | @@ -327,6 +374,7 @@ def visual_for(router, m, work_dir, cache, seed=7, log=print):
 329 |              r = router.call(ROLE, prompt, 1500, sd)
 330 |              v = check(_json(r.text))
 331 |              rec = {"version": VERSION, "measured": True, **v, "flags": flags(v),
 332 | +                   **({"formats": formats(dict(v, measured=True))} if formats(dict(v, measured=True)) else {}),
 333 |                     "sheet": {"name": os.path.basename(path), "sha256": sha, "times": ts, "path": path},
 334 |                     "backend": r.backend, "replayed": bool(getattr(r, "replayed", False)),
 335 |                     **cost(r),
 336 | diff --git a/pipeline/vo_fidelity.py b/pipeline/vo_fidelity.py
 337 | index 010a13e..968f02a 100644
 338 | --- a/pipeline/vo_fidelity.py
 339 | +++ b/pipeline/vo_fidelity.py
 340 | @@ -45,6 +45,9 @@ ATTRIB_VERBS = SPEECH_S                                        # (kept for calle
 341 |  PRONOUN_SUBJECTS = ("he", "she", "they", "his guest", "her guest", "their guest", "the guest", "the host",
 342 |                      "this guest", "this host", "the speaker", "this speaker", "the analyst", "this analyst",
 343 |                      "the author", "experts", "analysts", "critics", "many", "some", "others", "people", "everyone")
 344 | +ROLE_RE = re.compile(r"\b((?:co-?)?hosts?|guests?|analysts?|experts?|economists?|strategists?|interviewers?|"
 345 | +                     r"presenters?|anchors?|panelists?|commentators?)\b", re.I)   # orchestrator 21:10 Nov 14: a role
 346 | +#   ("a guest", "the host", "an analyst") is a claim under L-v; a line may give one only when a cited clip's words do
 347 |  VO_SELF = ("i", "we")                                          # PBX MAX itself: its claims are the verdict's to judge
 348 |  RELATION = re.compile(
 349 |      r"\b(agree[sd]?|agreeing|disagree[sd]?|disagreeing|respond(s|ed|ing)? to|repl(y|ies|ied|ying) to|"
 350 | @@ -477,6 +480,12 @@ def check_deterministic(segments, lines, manifest=None, current_levels=None):
 351 |          if (fact_numbers(without_manifest_date(text, manifest), meta_nums) or names or quotes or atts or times) \
 352 |                  and not cited:                                       # the 10:48 ruling (3): the show date needs none
 353 |              V("NEEDS_SOURCE", "a line with a number, name, quote, attribution or time word cites no segment")
 354 | +        roles = sorted({canon.canon_tokens(w)[-1] for w in ROLE_RE.findall(text) if canon.canon_tokens(w)})  # 21:10
 355 | +        if roles:                                    # Nov 14 (Blockware's caption: "a guest"); the role noun's canonical
 356 | +            shows = {t for n in meta for t in canon.canon_tokens(n)}       # token (L-k), as the cited clip says it; a
 357 | +            bad = [w for w in roles if w not in set(pool) and w not in shows]   # show or channel NAMED with it is no
 358 | +            if bad:                                                        # claim (audit 2131 C1, glm)
 359 | +                V("ROLE", f"gives someone a role the cited clips' own words do not state (law L-v): {bad}")
 360 |          pools = []                                                   # per attribution: the governing segments
 361 |          for subj0, form, _ in atts:
 362 |              subj = _clean_subject(subj0)
 363 | diff --git a/tests/package/proof_ledger.py b/tests/package/proof_ledger.py
 364 | index 9eeb541..8e556dd 100644
 365 | --- a/tests/package/proof_ledger.py
 366 | +++ b/tests/package/proof_ledger.py
 367 | @@ -147,8 +147,10 @@ def directives(path=None):
 368 |      import re
 369 |      story = re.compile(r"moments-[A-Za-z0-9_]+-[0-9a-f]{8}")         # the pins' own story id form (package_pin.to_pin)
 370 |      return {d["parent"]: d for d in rows if isinstance(d, dict) and isinstance(d.get("parent"), str) and
 371 | -            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and isinstance(d.get("ends"), str) and d["ends"].strip() and
 372 | -            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and
 373 | +            re.fullmatch(r"[0-9a-f]{20}", d["parent"]) and
 374 | +            ((isinstance(d.get("ends"), str) and d["ends"].strip() and "reseal" not in d) or   # a variant, or the SAME
 375 | +             (d.get("reseal") is True and "ends" not in d)) and                             # moment re-sealed (93
 376 | +            isinstance(d.get("alternative_to"), str) and story.fullmatch(d["alternative_to"]) and   # amended + 106)
 377 |              isinstance(d.get("by"), str) and d["by"].strip()}
 378 |  
 379 |  
 380 | diff --git a/tests/package/test_formats.py b/tests/package/test_formats.py
 381 | new file mode 100644
 382 | index 0000000..9cbee31
 383 | --- /dev/null
 384 | +++ b/tests/package/test_formats.py
 385 | @@ -0,0 +1,48 @@
 386 | +#!/usr/bin/env python3
 387 | +"""RULING 93 AMENDED (orchestrator 21:10 ET Nov 14; the integrator's spelling, 21:31): a pin whose clip carries a
 388 | +source caption the 9:16 crop cuts is sealed 16:9-ONLY, moments_package["formats"] = ["16x9"], inside the seal; absent
 389 | +means both formats, and every pin sealed before it recomputes to its own sha. A medley takes the intersection."""
 390 | +import copy
 391 | +import json
 392 | +import os
 393 | +import sys
 394 | +import unittest
 395 | +
 396 | +HERE = os.path.dirname(os.path.abspath(__file__))
 397 | +REPO = os.path.dirname(os.path.dirname(HERE))
 398 | +for _p in ("pipeline", "tests/package"):
 399 | +    sys.path.insert(0, os.path.join(REPO, _p))
 400 | +import package_pin as PP  # noqa: E402
 401 | +import test_angles as TA  # noqa: E402
 402 | +
 403 | +
 404 | +class TestFormats(unittest.TestCase):
 405 | +    def test_a_16x9_only_clip_seals_its_format_and_a_pin_without_one_as_before(self):
 406 | +        base = TA.TestPinAndTruth.pk(None)
 407 | +        plain = PP.to_pin(copy.deepcopy(base), "r")
 408 | +        self.assertNotIn("formats", plain["moments_package"])
 409 | +        self.assertEqual(PP.pin_seal(plain), plain["moments_package"]["package_sha256"])
 410 | +        only = copy.deepcopy(base)
 411 | +        only["segments"][1]["visual"] = dict(only["segments"][1].get("visual") or {}, formats=["16x9"])
 412 | +        pin = PP.to_pin(only, "r")                                        # ONE clip of the medley: the intersection
 413 | +        mp = pin["moments_package"]
 414 | +        self.assertEqual(mp["formats"], ["16x9"])
 415 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])          # the integrator's recompute
 416 | +        self.assertNotEqual(mp["package_sha256"], plain["moments_package"]["package_sha256"])
 417 | +        dropped = copy.deepcopy(pin)
 418 | +        del dropped["moments_package"]["formats"]                         # stripping it breaks the seal
 419 | +        self.assertNotEqual(PP.pin_seal(dropped), mp["package_sha256"])
 420 | +
 421 | +    def test_formats_of(self):
 422 | +        self.assertIsNone(PP.formats_of([]))
 423 | +        self.assertIsNone(PP.formats_of([{"visual": {"formats": None}}, {}]))
 424 | +        self.assertEqual(PP.formats_of([{}, {"visual": {"formats": ["16x9"]}}]), ["16x9"])
 425 | +
 426 | +    def test_the_spotlight_now_held_still_recomputes(self):
 427 | +        p = os.path.join(REPO, "tests", "package", "proof", "ledger_20261114_230148", "SPOTLIGHT_PIN.json")
 428 | +        pin = json.load(open(p))
 429 | +        self.assertEqual(PP.pin_seal(pin), pin["moments_package"]["package_sha256"])
 430 | +
 431 | +
 432 | +if __name__ == "__main__":
 433 | +    unittest.main()
 434 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 435 | index 9d8e2ca..af68ac8 100644
 436 | --- a/tests/package/test_medley.py
 437 | +++ b/tests/package/test_medley.py
 438 | @@ -33,6 +33,7 @@ from test_eligibility import NOW, REG, source  # noqa: E402
 439 |  from test_gates import Canned  # noqa: E402
 440 |  from test_moments import pm  # noqa: E402
 441 |  import house_style as HS  # noqa: E402
 442 | +import visual_pin as VP  # noqa: E402
 443 |  
 444 |  W = lambda n: " ".join(["word"] * n)
 445 |  
 446 | @@ -648,7 +649,7 @@ class Rig:
 447 |      def visual(self, router, m, work_dir, cache, seed=7, log=print):
 448 |          """visual_pin.visual_for as the build calls it: a measured clean record unless self.visuals says otherwise."""
 449 |          self.visual_calls.append(m["moment_id"])
 450 | -        base = {"version": "visual-2", "measured": True, "flags": [],
 451 | +        base = {"version": VP.VERSION, "measured": True, "flags": [],
 452 |                  "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 453 |                                   "finding": "no third person"},
 454 |                  "on_screen_text": [], "lower_third": {"name": None, "text": None}, "burned_in": [],   # ruling 93
 455 | diff --git a/tests/package/test_role_claims.py b/tests/package/test_role_claims.py
 456 | new file mode 100644
 457 | index 0000000..c8e491f
 458 | --- /dev/null
 459 | +++ b/tests/package/test_role_claims.py
 460 | @@ -0,0 +1,72 @@
 461 | +#!/usr/bin/env python3
 462 | +"""The orchestrator, 21:10 ET Nov 14: Blockware's spotlight caption called the channel's own presenter "a guest". "A
 463 | +caption may not assign a role the evidence does not show: 'a guest', 'the host', 'an analyst' are claims under L-v. Fix
 464 | +the writer's instructions and add it to the fidelity gate's checks." Offline."""
 465 | +import os
 466 | +import sys
 467 | +import unittest
 468 | +
 469 | +HERE = os.path.dirname(os.path.abspath(__file__))
 470 | +REPO = os.path.dirname(os.path.dirname(HERE))
 471 | +sys.path.insert(0, os.path.join(REPO, "pipeline"))
 472 | +import package as PK  # noqa: E402
 473 | +import spotlight as SPOT  # noqa: E402
 474 | +import vo_fidelity as VF  # noqa: E402
 475 | +
 476 | +BLOCKWARE = {"m1": {"show": "Blockware Solutions", "speaker": None, "names": [], "video_id": "7BqLu-wzbU0",
 477 | +                    "text": "On my 20th birthday, I sold every stock in my Roth IRA and put it all into Bitcoin."}}
 478 | +MAN = {"channels": ["Blockware Solutions"], "date": "2026-11-14"}
 479 | +
 480 | +
 481 | +def rules(text, slot="caption", segs=BLOCKWARE, cites=("m1",)):
 482 | +    out = VF.check_deterministic(segs, [{"slot": slot, "text": text, "cites": list(cites)}], MAN)
 483 | +    return [x["rule"] for x in out["violations"]]
 484 | +
 485 | +
 486 | +class TestTheFidelityGate(unittest.TestCase):
 487 | +    def test_blockwares_caption_fails_and_the_same_line_without_the_role_passes(self):
 488 | +        self.assertIn("ROLE", rules("a guest sold his retirement stocks for bitcoin and skipped the usual path."))
 489 | +        self.assertNotIn("ROLE", rules("he sold his retirement stocks for bitcoin and skipped the usual path."))
 490 | +
 491 | +    def test_every_role_word_in_every_slot_needs_the_clips_own_words(self):
 492 | +        for line in ("The host sold everything.", "an analyst sold his stocks", "Our guest went all in",
 493 | +                     "A Wall Street strategist sold his IRA", "the co-host bought bitcoin", "Two experts disagree"):
 494 | +            for slot in ("caption", "title", "comment", "closing"):
 495 | +                self.assertIn("ROLE", rules(line, slot), (line, slot))
 496 | +
 497 | +    def test_a_role_the_clip_states_is_no_claim_of_ours(self):
 498 | +        segs = {"m1": {"show": "X", "speaker": None, "names": [], "video_id": "v",
 499 | +                       "text": "I'm an analyst at a big bank and I think bitcoin wins."}}
 500 | +        self.assertNotIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs))
 501 | +        self.assertIn("ROLE", rules("an analyst thinks bitcoin wins", segs=segs, cites=()))   # not cited: no source
 502 | +        self.assertIn("ROLE", rules("a guest thinks bitcoin wins", segs=segs))                # another role
 503 | +
 504 | +    def test_a_show_or_channel_named_with_a_role_word_is_no_claim(self):     # audit 2131 C1 (glm)
 505 | +        segs = {"m1": {"show": "Analyst Answers", "speaker": None, "names": [], "video_id": "v",
 506 | +                       "text": "Bitcoin is a bearer asset."}}
 507 | +        out = VF.check_deterministic(segs, [{"slot": "caption", "text": "From Analyst Answers: bitcoin as a bearer asset.",
 508 | +                                             "cites": ["m1"]}], {"channels": ["Analyst Answers"], "date": "2026-11-14"})
 509 | +        self.assertNotIn("ROLE", [x["rule"] for x in out["violations"]])
 510 | +        self.assertIn("ROLE", rules("Our guests sold everything."))        # still a claim elsewhere
 511 | +
 512 | +    def test_the_comparison_is_canonical(self):
 513 | +        segs = {"m1": {"show": "X", "speaker": None, "names": [], "video_id": "v",
 514 | +                       "text": "Analyst here. I think bitcoin wins."}}            # sentence-initial, capitalised
 515 | +        self.assertNotIn("ROLE", rules("an ANALYST thinks bitcoin wins", segs=segs))
 516 | +        self.assertIn("ROLE", rules("analysts think bitcoin wins", segs=segs))   # another word: a claim of ours
 517 | +
 518 | +    def test_words_that_only_contain_a_role_are_not_roles(self):
 519 | +        for line in ("He is hosting nothing.", "Ghosts of the old system.", "Anchoring on old prices fails."):
 520 | +            self.assertNotIn("ROLE", rules(line), line)
 521 | +
 522 | +
 523 | +class TestTheWriters(unittest.TestCase):
 524 | +    def test_both_writers_are_told_never_to_give_a_role(self):
 525 | +        for name, prompt in (("spotlight", SPOT.WRITE_SPOT), ("medley", PK.WRITE_LY)):
 526 | +            self.assertIn("Never give anyone a ROLE", prompt, name)
 527 | +            for word in ('"guest"', '"host"', '"analyst"'):
 528 | +                self.assertIn(word, prompt, (name, word))
 529 | +
 530 | +
 531 | +if __name__ == "__main__":
 532 | +    unittest.main()
 533 | diff --git a/tests/package/test_ruling_104.py b/tests/package/test_ruling_104.py
 534 | index 585955a..88ca6c3 100644
 535 | --- a/tests/package/test_ruling_104.py
 536 | +++ b/tests/package/test_ruling_104.py
 537 | @@ -378,3 +378,41 @@ class TestTheDirective(unittest.TestCase):
 538 |          no_id = [{"channel_id": "A", "day_et": SPOT.et_day(NOW)}]                 # a record without a story id
 539 |          got, _ = SPOT.pool([a, alt, b], {}, ctx, spotlit=no_id, captions_for=caps)
 540 |          self.assertEqual([m["moment_id"] for m in got], ["b"])                   # admits no one
 541 | +
 542 | +
 543 | +RESEAL = {"parent": None, "reseal": True, "alternative_to": "moments-ledger_20261114_230148-3f481f5a",
 544 | +          "by": "orchestrator default 21:4x ET Nov 14 (ruling 106 (a))", "why": "16:9-only under ruling 93 amended"}
 545 | +
 546 | +
 547 | +class TestTheReseal(unittest.TestCase):
 548 | +    """RULING 93 AMENDED with 106 (21:31 Nov 14): the SAME moment sealed again (16:9-only) in the place of its own
 549 | +    earlier story, never as a second spotlight of the channel's day, only on a written directive."""
 550 | +
 551 | +    def setUp(self):
 552 | +        self.d = tempfile.TemporaryDirectory()
 553 | +        self.addCleanup(self.d.cleanup)
 554 | +
 555 | +    def test_the_moment_itself_takes_its_earlier_storys_place(self):
 556 | +        src, m = blockware()
 557 | +        vs, notes, replaced = TV.for_pool([m], {"7BqLu-wzbU0": src}, CTX, self.d.name, 35.0,
 558 | +                                          directives={m["moment_id"]: dict(RESEAL, parent=m["moment_id"])})
 559 | +        self.assertNotIn("derived_from", m)                                   # the caller's record untouched
 560 | +        self.assertEqual(([v["moment_id"] for v in vs], replaced), ([m["moment_id"]], {m["moment_id"]}))  # the SAME
 561 | +        m = vs[0]                                                             # moment, marked, in its own place
 562 | +        self.assertEqual((m["derived_from"]["reseal_of"], m["derived_from"]["alternative_to"]),
 563 | +                         (RESEAL["alternative_to"],) * 2)
 564 | +        self.assertEqual(m["text"], blockware()[1]["text"])                   # its words unchanged
 565 | +        self.assertIn("re-sealed in the place of", notes[m["moment_id"]])
 566 | +        rec = [{"channel_id": "c", "day_et": "2026-11-14", "story_id": RESEAL["alternative_to"]}]
 567 | +        self.assertFalse(SPOT.day_taken(rec, "c", "2026-11-14", m["derived_from"]["alternative_to"]))   # its place
 568 | +        self.assertTrue(SPOT.day_taken(rec + [{"channel_id": "c", "day_et": "2026-11-14", "story_id": "other"}],
 569 | +                                       "c", "2026-11-14", m["derived_from"]["alternative_to"]))   # never a second
 570 | +
 571 | +    def test_the_reseal_directive_is_read_strictly(self):
 572 | +        p = os.path.join(self.d.name, "D.json")
 573 | +        good = dict(RESEAL, parent="06d34e155feae654ee56")
 574 | +        with open(p, "w") as f:
 575 | +            json.dump({"directives": [good, dict(good, parent="1" * 20, reseal="yes"),
 576 | +                                      dict(good, parent="2" * 20, ends="...Roth IRA."),      # both: never guessed
 577 | +                                      dict(good, parent="3" * 20, alternative_to="not-a-story")]}, f)
 578 | +        self.assertEqual(PLG.directives(p), {"06d34e155feae654ee56": good})
 579 | diff --git a/tests/package/test_spotlight.py b/tests/package/test_spotlight.py
 580 | index a678b34..e6b4035 100644
 581 | --- a/tests/package/test_spotlight.py
 582 | +++ b/tests/package/test_spotlight.py
 583 | @@ -66,7 +66,7 @@ def moment(text=TEXT, dur=20.0, mid="m1", channel="DataDash", **kw):
 584 |               hook_onset={"pass": True, "measured": True, "lead_ms": 120, "cut_in": 1.0, "why": "quiet"},
 585 |               hook_rating={"scroll": 5, "alone": 4, "setup": 3, "rating": 4, "why": "a complete claim",
 586 |                            "backend": "fake:xai", "replayed": False},
 587 | -             visual={"version": "visual-1", "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 588 | +             visual={"version": VP.VERSION, "measured": True, "flags": [], "backend": "fake:vis", "replayed": False,
 589 |                       "third_person": {"shown": False, "how": "none", "words_negative": False, "name_on_screen": None,
 590 |                                        "finding": "none"}, "on_screen_text": [],
 591 |                       "lower_third": {"name": None, "text": None}, "burned_in": []},
 592 | @@ -181,7 +181,8 @@ class TestPinContract(unittest.TestCase):
 593 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [], "closing": GOOD["closing"]["text"]})
 594 |          self.assertEqual(mp["vo_jobs"], {"closing": "closing"})
 595 |          self.assertEqual(mp["first_comment"], pk["first_comment"])
 596 | -        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])
 597 | +        self.assertEqual(mp["gates"]["spotlight_source"]["format"], "CONVERSATION")   # 21:10 Nov 14: WHICH passed,
 598 | +        self.assertEqual(PP.pin_seal(pin), mp["package_sha256"])                      # inside the seal
 599 |          integrator = PP.seal(pin["segments"], mp["edl_vo"], mp.get("signoff_expected"), mp["title"], mp["caption"],
 600 |                               mp["gates"], mp.get("btc_screen"),
 601 |                               **({"shape": mp["shape"], "first_comment": mp["first_comment"]}
 602 | @@ -686,7 +687,7 @@ class TestBuild(unittest.TestCase):
 603 |                   (SPOT.P, "truth_for", lambda r, m, w, c: {"ok": True, "edges": {"cuttable": True}}),
 604 |                   (SPOT.P, "hook_onset_for", lambda m, s, w, c: onset or {"pass": True, "measured": True}),
 605 |                   (SPOT.P, "scorer_verdicts", verdicts), (SPOT.P, "render_scorer_sha", lambda *a: "s" * 64),
 606 | -                 (VP, "visual_for", lambda r, m, w, c: dict({"measured": True, "flags": [], "burned_in": [],
 607 | +                 (VP, "visual_for", lambda r, m, w, c: dict({"version": VP.VERSION, "measured": True, "flags": [], "burned_in": [],
 608 |                                                                "backend": "fake:vis"}, **(visual or {}))),
 609 |                   (SPOT, "layout_for", lambda r, m, v, c, **k: (calls.setdefault("layout", []).append(
 610 |                       (m["moment_id"], k.get("evidence"))), {"measured": True, "layout": layout, "why": "w"})[1]),
 611 | @@ -773,9 +774,13 @@ class TestBuild(unittest.TestCase):
 612 |          out, calls = self.run_build(ms, {"a": 5}, visual={"burned_in": [strap], "flags": [
 613 |              {"kind": "burned_in", "text": "BILL MILLER IV", "item": "lower_third", "in_9x16": "out"}]})
 614 |          self.assertEqual(calls["package_for"], ["a"])                   # eligible, flagged, still clean
 615 | -        self.assertTrue(SPOT.clean_visual({"measured": True, "burned_in": [strap], "flags": [
 616 | +        cap = {"kind": "caption", "text": "SOLD MY ROTH IRA", "whole_in_16x9": True, "in_9x16": "whole",
 617 | +               "covers_speaker": False, "at": [3.27]}                       # ruling 93 amended: a source caption is
 618 | +        self.assertTrue(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [cap], "flags": [
 619 | +            {"kind": "burned_caption", "text": "SOLD MY ROTH IRA", "in_9x16": "whole", "at": [3.27]}]}))   # flagged, clean
 620 | +        self.assertTrue(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [strap], "flags": [
 621 |              {"kind": "burned_in", "text": "BILL MILLER IV"}]}))
 622 | -        self.assertFalse(SPOT.clean_visual({"measured": True, "burned_in": [], "flags": [
 623 | +        self.assertFalse(SPOT.clean_visual({"version": VP.VERSION, "measured": True, "burned_in": [], "flags": [
 624 |              {"kind": "on_screen_text", "text": "SCANDAL"}]}))           # a ruling-70 flag is not clean
 625 |          self.assertFalse(SPOT.clean_visual({"measured": True, "flags": []}))       # no question 4: never
 626 |  
 627 | diff --git a/tests/package/test_visual_pin.py b/tests/package/test_visual_pin.py
 628 | index 82c682c..326fb65 100644
 629 | --- a/tests/package/test_visual_pin.py
 630 | +++ b/tests/package/test_visual_pin.py
 631 | @@ -7,6 +7,7 @@ import os
 632 |  import sys
 633 |  import tempfile
 634 |  import unittest
 635 | +from unittest import mock
 636 |  
 637 |  HERE = os.path.dirname(os.path.abspath(__file__))
 638 |  REPO = os.path.dirname(os.path.dirname(HERE))
 639 | @@ -33,9 +34,13 @@ class VFake(Fake):
 640 |  
 641 |  
 642 |  class TestContract(unittest.TestCase):
 643 | -    def test_the_stills_are_the_cut_in_one_every_two_seconds_and_the_last(self):
 644 | -        self.assertEqual(VP.times(16.62), [0.0, 2.37, 4.73, 7.1, 9.47, 11.84, 14.2, 16.57])   # evenly spaced
 645 | -        self.assertEqual(VP.times(5.0), [0.0, 2.0, 4.0, 4.95])
 646 | +    def test_the_stills_are_the_cut_in_one_every_second_and_the_last(self):    # 21:10 Nov 14: >= 1 frame a second
 647 | +        self.assertEqual(VP.times(5.0), [0.0, 1.0, 2.0, 3.0, 4.0, 4.95])
 648 | +        for dur in (5.0, 12.3, 16.62, 22.94, 35.0):                       # every span up to the 35 s ceiling
 649 | +            ts = VP.times(dur)
 650 | +            self.assertEqual((ts[0], ts[-1]), (0.0, round(dur - 0.05, 2)), dur)
 651 | +            self.assertLessEqual(max(b - a for a, b in zip(ts, ts[1:])), 1.0 + 1e-9, dur)
 652 | +        self.assertEqual(len(VP.times(22.94)), 24)                        # Blockware: 24 frames, not 8
 653 |          self.assertEqual(len(VP.times(60.0)), VP.TILES)
 654 |  
 655 |      def test_a_reply_in_contract_and_out_of_it(self):
 656 | @@ -67,7 +72,7 @@ class TestContract(unittest.TestCase):
 657 |      def test_ruling_93_burned_in_text_per_clip(self):
 658 |          item = lambda kind, **k: dict({"kind": kind, "text": "BITCOIN 74,512 | ETH 2,410", "whole_in_16x9": True,
 659 |                                         "in_9x16": "out", "covers_speaker": False}, **k)
 660 | -        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True)
 661 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
 662 |          self.assertIsNone(VP.layout_block(rec()))                                       # nothing burned in
 663 |          for kind in ("ticker", "crawl"):                                                # a ticker or crawl: never
 664 |              self.assertIn(f"a {kind}", VP.layout_block(rec(item(kind))))
 665 | @@ -90,8 +95,44 @@ class TestContract(unittest.TestCase):
 666 |          many = [dict(strap, text=f"strap {i}", in_9x16="out") for i in range(VP.TEXTS_MAX + 3)] + [item("ticker")]
 667 |          v = VP.check(dict(CLEAN, burned_in=many))                                       # the ticker listed last
 668 |          self.assertEqual((len(v["burned_in"]), v["burned_in_truncated"]), (VP.TEXTS_MAX, 4))
 669 | -        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True)))            # is never cut away
 670 | -        self.assertEqual(VP.VERSION, "visual-2")                                        # every clip asked again
 671 | +        self.assertIn("a ticker", VP.layout_block(dict(v, measured=True, version=VP.VERSION)))   # never cut away
 672 | +        self.assertEqual(VP.VERSION, "visual-3")                                        # every clip asked again
 673 | +
 674 | +    def test_ruling_93_amended_the_sources_burned_captions(self):
 675 | +        """21:10 Nov 14: Blockware's captions ('SOLD MY ROTH IRA', '26 NO ROTH IRA NO 401K') were on the sheet, and
 676 | +        visual-2's question told the model to leave subtitles out. A caption never makes a clip ineligible; cut by the
 677 | +        9:16 it makes the clip 16:9-ONLY, held until the integrator's render can pass a 16:9-only pin."""
 678 | +        q4 = VP.PROMPT.split("4. burned_in:")[1]
 679 | +        self.assertNotIn("Not subtitles of the spoken words", q4)            # the cause, gone
 680 | +        for words in ("BURNED-IN CAPTIONS", '"caption"', "EVERY frame", "face"):
 681 | +            self.assertIn(words, q4)
 682 | +        cap = lambda text, cut, at=(16.35, 19.62): {"kind": "caption", "text": text, "whole_in_16x9": True,
 683 | +                                                   "in_9x16": cut, "covers_speaker": False, "at": list(at)}
 684 | +        rec = lambda *items: dict(VP.check(dict(CLEAN, burned_in=list(items))), measured=True, version=VP.VERSION)
 685 | +        blockware = rec(cap("SOLD MY ROTH IRA", "cut", (3.27,)), cap("26 NO ROTH IRA NO 401K", "cut"))
 686 | +        self.assertEqual(VP.formats(blockware), ["16x9"])
 687 | +        self.assertEqual([f["kind"] for f in VP.flags(blockware)], ["burned_caption", "burned_caption"])
 688 | +        self.assertEqual(VP.flags(blockware)[1]["at"], [16.35, 19.62])
 689 | +        self.assertIn("16:9-only", VP.layout_block(blockware))               # held while the render cannot pass it
 690 | +        self.assertNotIn("ticker", VP.layout_block(blockware))
 691 | +        with mock.patch.object(VP, "RENDER_16X9_ONLY", True):
 692 | +            self.assertIsNone(VP.layout_block(blockware))                    # then eligible, 16:9 only
 693 | +            self.assertEqual(VP.formats(blockware), ["16x9"])
 694 | +        whole = rec(cap("FINANCIALLY INDEPENDENT BY 45", "whole"))
 695 | +        self.assertIsNone(VP.formats(whole))                                 # a crop shows it whole: both formats
 696 | +        self.assertIsNone(VP.layout_block(whole))
 697 | +        self.assertIsNone(VP.formats(dict(blockware, measured=False)))
 698 | +        self.assertEqual(VP.sealed(dict(blockware, formats=VP.formats(blockware)))["formats"], ["16x9"])
 699 | +        for bad in ([dict(cap("x", "cut"), text="")], [dict(cap("x", "cut"), at="16.35")],
 700 | +                    [dict(cap("x", "cut"), at=["16.35"])]):
 701 | +            with self.assertRaises(ValueError):                             # a caption with no words, or bad times
 702 | +                VP.check(dict(CLEAN, burned_in=bad))
 703 | +        many = [cap(f"WHOLE CAPTION {i}", "whole") for i in range(VP.TEXTS_MAX + 2)] + [cap("CUT LAST", "cut")]
 704 | +        kept = rec(*many)                                                    # audit 2131 C1 (glm): the cut caption
 705 | +        self.assertEqual(VP.formats(kept), ["16x9"])                         # listed last survives TEXTS_MAX
 706 | +        self.assertEqual(kept["burned_in"][0]["text"], "CUT LAST")
 707 | +        old = dict(blockware, version="visual-2")
 708 | +        self.assertIn("never asked for the source's burned captions", VP.layout_block(old))
 709 |  
 710 |      def test_the_cost_is_the_vendors_figure_and_an_estimate_is_labelled(self):
 711 |          class R:
 712 | 
```

---

pp-selectid: THE ORCHESTRATOR'S THREE FIXES OF 21:10 ET Nov 14, plus the sealed "formats" and the re-seal directive.

THE ORCHESTRATOR (21:10): "1. THE VISUAL CHECK MISSED BURNED-IN CAPTIONS ... sample at least one frame a second across
the span, and ask explicitly for burned-in captions / subtitles. RULING 93 AMENDED: source-burned captions that the 9:16
crop cuts mid-word make the clip 16:9-ONLY (sealed as formats: ['16x9'], the integrator renders and delivers that format
alone) unless a crop exists that shows them whole; they do not make the clip ineligible. 2. THE CAPTION SAYS 'a guest'
... A caption may not assign a role the evidence does not show: 'a guest', 'the host', 'an analyst' are claims under
L-v. Fix the writer's instructions and add it to the fidelity gate's checks. 3. ... record on the pin WHICH of
CONVERSATION / FIRST_HAND passed."
THE INTEGRATOR (21:2x and 21:31):
- Its render cannot yet pass a 16:9-only pin, so none is sealed until its format-aware release lands.
- Its crop slides only while the speaker's face stays inside.
- The spelling: moments_package["formats"] = ["16x9"], inside the seal; absent means both.

ROOT CAUSE of the miss: the sheet's 8 frames DID show Blockware's captions. Visual-2's question told the model, twice,
to leave out "subtitles of the spoken words", so it reported none.

THE CHANGE:
- pipeline/visual_pin.py, VERSION "visual-3":
  - frames: TILES 40, EVERY_S 1.0, 6 columns of 320 px, so no gap exceeds a second (times() also keeps the last
    frame within a second);
  - question 4 asks for the source's own burned CAPTIONS (kind "caption", with "at" frame times), with the face-safe
    crop rule;
  - burned_block: a caption never makes a clip ineligible;
  - formats(): ["16x9"] when a caption is "cut";
  - layout_block: holds a 16:9-only clip while RENDER_16X9_ONLY is False, and holds a record of another VERSION;
  - flags: "burned_caption"; sealed() carries "formats".
- pipeline/spotlight.py:
  - clean_visual ignores "burned_caption" flags;
  - the spotlight_source gate row carries "format": "CONVERSATION" | "FIRST_HAND" (sealed in the gates);
  - WRITE_SPOT's RULES gain the role rule.
- pipeline/package.py: WRITE_LY's RULES gain the role rule.
- pipeline/vo_fidelity.py: check_deterministic gains rule "ROLE". A line naming a role (guest, host, co-host,
  analyst, expert, economist, strategist, interviewer, presenter, anchor, panelist, commentator) fails unless a CITED
  clip's own words state that role.
- pipeline/package_pin.py:
  - formats_of(segments) (the intersection);
  - seal(..., formats=None) puts it in the body only when present;
  - pin_seal passes it;
  - to_pin seals moments_package["formats"].
- pipeline/tail_variant.py + tests/package/proof_ledger.py: a directive {"parent", "reseal": true,
  "alternative_to", "by", "why"} marks the SAME moment (no variant) as re-sealed in the place of its own earlier
  story. spotlight.day_taken then lets it take that story's place for the day, and only that one. A row with both
  "ends" and "reseal", or a reseal that is not exactly true, is dropped.
- Tests: test_visual_pin, test_spotlight, test_role_claims (new), test_formats (new), test_ruling_104, test_medley
  (fixture version).

UNCHANGED GUARDS: spotlight.day_taken excludes only the named story's own record. Every other record of the
channel's day still takes the place. The visual cache key includes VERSION and the sheet's parameters, so visual-2
verdicts are never reused. check_pin_only (the integrator's) recomputes through pin_seal.

PLEASE CHECK:
(1) Can a 16:9-only clip be sealed while RENDER_16X9_ONLY is False?
(2) Can the ROLE rule pass a role no cited clip states, or refuse a sentence with no role word?
(3) Does "formats" change any existing pin's recompute?
(4) Can a reseal directive create a second spotlight for a channel's day?
(5) Do the tests pin each piece? The mutation results are in the consensus file.


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
