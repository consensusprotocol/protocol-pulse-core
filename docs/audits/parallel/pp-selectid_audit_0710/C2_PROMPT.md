# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0710
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 173 s finish=stop usage in 16761 / out 5811 usd~0.137 (upper-bound price)

# AUDIT — pp-selectid: acoustic cut measure for TRIMMED clips (ruling 33 part 2)

Scope: only the diff provided. I verified the copied functions against the render's usage as described in the diff and the background; I could not diff against the render's c6605895 myself (not provided), so "verbatim" is taken from the stated AST comparison.

---

## P0

None found.

---

## P1

**P1-1 — `hook_onset.trim_onset` margin: `on > need + 1e-9` is a strict inequality on a float, and the margin is added to the *render's* threshold, not to the *measured* onset's uncertainty.**
`pipeline/hook_onset.py:38-40` (diff lines 38–44). `need = SL.HOP_S + MARGIN_MS/1000` = 0.020 s; the render's own rule (`sentence_law.trimmed_onset`, diff lines 189) is `onset > HOP_S + 1e-9` = 0.010 s. The pin stage demands the onset lie one more 10 ms hop later than the render's rule. That is the stated intent ("one more 10 ms frame of margin: the slice vs the render's own decode"), and it only makes the pin stage stricter — good. But note the direction of the margin: the pin stage measures the onset on the *window file* (16 kHz, its own decode) while the render measures on its own decode of the same audio. If the window's decode places the onset *earlier* than the render's decode (different `-ss` seeking, resample), the pin stage can fail a cut the render will pass — the pin stage then holds a clip the render would have accepted. That is fail-closed and stricter, so it complies with L-m/L-j; it is a divergence that only makes the pin stage stricter, as permitted. No action required; noted for the record. (If the intent had been the opposite — pin stage more permissive — it would be a defect; it is not.)

**P1-2 — `trim_onset`'s "no cut" branch reports `measured: True` with no onset, and `measure`'s wrapper then synthesises a *different* record.**
`pipeline/hook_onset.py:33-34` (diff lines 33–34): when `accepted_cut` returns `None`, `trim_onset` returns `{"pass": False, "measured": True, "why": ...}` — no `onset_s`, no `cut_in`. That is correct (the render's `accepted_cut` finding no cut is a measured property of the audio, not missing data). But in `measure` (diff lines 54–57), the wrapper only adds a synthesised `trim` when `"trim" not in rec`; the synthesised record copies `rec.get("measured")` and `rec.get("why")` from the *hook-lead* failure, not a trimmed-cut reason. Scenario: `edge_plan` raises (diff line 72–73, "no cut plan") for a trimmed moment → `_measure` returns early with `measured: False` and a plan-level `why` → wrapper sets `rec["trim"] = {"pass": False, "measured": False, "why": "no cut plan: ..."}`. That is fail-closed and `trim` is present — the law is met. But the `why` names the *hook-lead* planning failure, not the trimmed-cut one; the funnel's `trim_cut` report (package.py, diff lines 129–132) will show a reason that is not about the trim. Cosmetic-to-moderate: the gate verdict is right, the evidence string can mislead a human reading the prescreen. P1 because the prescreen report is what PBX reads to overturn a HOLD.

**P1-3 — `package.build`'s new exclusion reads `m["hook_onset"].get("trim")` but the synthesised-`trim` guarantee lives in `hook_onset.measure`; the rig stub in test_medley must now also carry it, and the funnel's `mom()` can still produce a record without `trim`.**
`pipeline/package.py:129-131` (diff lines 129–132): the comprehension uses `m["hook_onset"].get("trim") or {"measured": False, "why": "no trimmed-cut record"}` — good, it fails closed when `trim` is absent. But `hook_onset_for` (diff lines 102–111) catches *all* exceptions from `HO.measure` and stores `{"pass": False, "measured": False, "why": ...}` — no `trim` key. Then `build`'s comprehension: `t = m["hook_onset"].get("trim") or {...}` → the fallback fires, the moment is excluded with "no trimmed-cut record", `measured` never consulted. Correct (fail closed), but note the *old* code excluded on `hook_onset.pass is not True` — the same moment was already excluded by the old rule too, so no behaviour change; the new fallback's `why` is the only difference. Verified: no path lets a trimmed moment through with a missing/failed `trim`. The funnel's `mom()` (tests/package/funnel.py, diff lines 265–274) returns a *display* record only; it does not feed `build`. Confirmed: funnel changes are report-only.

**P1-4 — `edge_plan`'s trimmed `cut_hi` uses `q["end"] - LEAD_MIN_S` but the untrimmed branch's `cuttable`/`reason` comparison changed from `hi >= g["start"]` to `hi >= lo`.**
`pipeline/sentence_law.py:205-215` (diff lines 205–215). Untrimmed path: previously `hi = round(g["end"] - LEAD_MIN_S, 3)`, `cuttable = hi >= g["start"] - 1e-9`, `cut = clamp(target, g["start"], hi)`. Now: `lo = g["start]`... wait, `lo, hi = g["start"], round(g["end"] - LEAD_MIN_S, 3)`; then for trimmed, `lo, hi = max(lo, q["start"]), min(hi, round(q["end"] - LEAD_M

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 48 s finish=stop usage in 16590 / out 610 usd~0.098 (upper-bound price)

**P2: pipeline/sentence_law.py:196** (edge_plan) and **hook_onset.py:71**: when trimmed={"word": ...} is supplied, edge_plan routes to trimmed_boundary (lines 164-181) then trims the quiet_run interval (lines 206-208); trim_onset:31 then calls the render's accepted_cut + trimmed_onset (lines 35, 188) on the identical plan dict shape. Matches render usage exactly; the extra HO.MARGIN_MS frame (line 38) only makes the pin-stage onset test stricter.

**P2: pipeline/hook_onset.py:54-57, 92-96**: every trimmed path writes a "trim" dict; any exception, planning failure, or trim_onset failure forces measured=False or pass=False (never a pass, satisfying L-m / L-j / ruling 33(a)). Untrimmed call sites (trimmed=None or absent) execute the pre-existing boundary + lead-only path unchanged (lines 69, 85).

**P2: pipeline/package.py:129-133**: trim_cut only collects trimmed moments whose trim["pass"] is not True and removes them from cleared (out at any place); hook lead still gates "can open a medley". Matches ruling 33(a) exactly; non-trimmed moments and the old hook_onset["pass"] logic are untouched. The STAND_ALONE log line is only textual.

**P2: tests/package/test_hook_onset.py:397-420** (TestTrimmedCut): synthetic 16 kHz WAVs exercise trimmed_boundary (pause vs co-articulated), the k<0 / lexical / sentence-start guards, envelope "not measured" case, and confirm untrimmed path is identical. All four tests verify the render's own onset rule (with pin-stage margin) on the bytes that would be cut.

**P2: tests/package/test_medley.py:477-489** (TestRuling33TrimAtThePinStage): Rig.onset stub supplies realistic "trim" records; trimmed-cut failure excludes from angle_write (never offered); clean-trim + bad-lead stays as non-hook clip. Funnel.py:268-274 only affects reporting (mom() aliasing, no build logic change).

**P2: sentence_law.py:168** (trimmed_boundary k<0 case): returns valid=False ("not the word before the lock"). K1 assumption cannot be verified from this diff alone (no full-transcript eligibility code); render copy is byte-identical per audit note, so behavior is as-shipped by integrator at c6605895. No other divergence found.

No P0 or P1 findings; all required gates (plan, accepted_cut, onset on final cut audio, fail-closed paths, untrimmed invariance) are exercised by the diff and tests. The 05:48 build's two real trimmed moments are now measurable exactly as described.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 38 s finish=stop usage in 18385 / out 2284 usd~0.089 (upper-bound price)

# Code Audit: pp-selectid-0710 (C1_STEP.diff)

## P0 Findings

**1. `pipeline/sentence_law.py` (lines 223-251): `_cut_head` and `hook_lead_at` are not verbatim copies of the render's `c6605895`**
The diff claims these functions are "copied VERBATIM from the render's c6605895 (verified byte-identical by an AST source comparison)." However, `_cut_head` (line 223) and `hook_lead_at` (line 248) are **new** functions introduced in this diff. The render's `c6605895` does not contain these helpers; they are part of the pin stage's own measurement infrastructure. The claim of verbatim copying is false for these three functions. This is not a functional defect per se, but it misrepresents the provenance of the code and could mislead future auditors into assuming these functions have been validated against the render's behavior. The actual verbatim copies are `TRIMMABLE_LEADING`, `trimmed_boundary`, `trimmed_onset`, and the modified `edge_plan`.

**2. `pipeline/hook_onset.py` (lines 38-44): `trim_onset` margin calculation may be inconsistent with the render's rule**
The pin stage adds `MARGIN_MS / 1000` to the onset threshold: `need = SL.HOP_S + MARGIN_MS / 1000`. The render's `trimmed_onset` (line 189) uses `onset > HOP_S + 1e-9` with no additional margin. The diff states this is "one more 10 ms frame after the cut than the render's rule asks (the slice vs the render's own decode)." However, the render's `hook_lead_at` (line 248) measures the lead on the **cut audio** (after `_cut_head` applies the fade), while the pin stage's `trim_onset` (line 35) calls `SL.trimmed_onset(sa.path, pick["cut_in"], pick["fade_in_ms"])` on the **source window** (`sa.path`), not on the cut audio. This means the pin stage is measuring the onset on the uncut source, which is a different signal than what the render measures. The margin may not compensate for this difference. **Scenario:** A trimmed word ends at 1.95 s, the next word starts at 2.40 s. The render cuts at 2.10 s with an 83 ms fade, so the cut audio starts at 2.10 s and the first onset is at 2.40 s (300 ms lead). The pin stage measures the onset on the source window, where the first onset after 2.10 s is also at 2.40 s (300 ms lead). In this case, the margin is irrelevant. But if the fade is longer or the cut is earlier, the difference between measuring on the source vs. the cut audio could matter. **Verdict:** This is a P1, not a P0, because the pin stage is intended to be stricter, and the margin is a conservative adjustment. But the provenance claim is misleading.

## P1 Findings

**3. `pipeline/package.py` (lines 129-133): The `trim_cut` logic is correct but the comment is misleading**
The new logic (lines 129-133) correctly implements ruling 33 (a): a trimmed moment is left out at any place only when its "trim" record is not a pass. The old logic (lines 126-128) left it out whenever its hook lead failed. The new logic is correct. However, the comment on line 133 says "the hook lead decides only the hook," which is true but could be misread as implying that the hook lead is irrelevant to trimmed moments. In fact, the hook lead still matters for whether a trimmed moment can **open** a medley (line 96: `rec["pass"] = False` if the trim fails, but the hook lead is also checked on line 85). The comment should clarify that the hook lead still gates the "open" decision, but the trim cut gates the "any place" decision.

**4. `tests/package/funnel.py` (lines 265-274): The `mom` function assumes the trimmed word is the first word of the text**
The `mom` function (line 273) extracts the first word of the text and marks it as trimmed: `w, _, rest = (o.get("text") or "").partition(" ")`. This assumes that the trimmed word is always the first word of the moment's text. This is true for the current implementation (the trimmed word is the leading discourse conjunction), but it is a fragile assumption. If a future change allows trimming a non-leading word, this function will produce incorrect output. **Scenario:** A moment with text "So Bitcoin rises." where "So" is trimmed. The `mom` function correctly produces "[So trimmed] Bitcoin rises." But if a future change allows trimming "Bitcoin" (which is not in `TRIMMABLE_LEADING`), the function would still mark the first word as trimmed, which would be incorrect. **Verdict:** This is a P2, not a P1, because the current implementation is correct and the assumption is reasonable.

**5. `pipeline/hook_onset.py` (lines 55-56): The "trim" record is added on every path, but the `measured` field may be inconsistent**
When `trimmed` is provided and no plan is reached (line 55), the "trim" record is added with `"measured": rec.get("measured", False)`. If the original `rec` has `"measured": True` (e.g., the hook lead was measured but the trim cut failed), the "trim" record will have `"measured": True`. This is correct. But if the original `rec` h

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0710 (item 42's gap: the trimmed cut measured as the render measures it): cycle 1 consensus

Synthesis by the pp-selectid session, written before cycle 2.

**Run.** C1_STEP.diff covers sentence_law.py, hook_onset.py, package.py, funnel.py, test_hook_onset.py and
test_medley.py. Verdicts:
- grok: no P0, no P1, "SHIP: yes";
- glm: no P0, "SHIP: yes" (its P1s are notes it verifies as fail-closed itself);
- qwen: "SHIP: yes with conditions", with two "P0"s, both misreadings (K1, K2).

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | qwen P1-3 (its condition 2): the trim_cut comment "the hook lead decides only the hook" can be misread | it now says that the hook lead decides only whether a trimmed clip may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip. |
| F2 | qwen P2-6 (its condition 3): the passing test does not check the fade | the test asserts that the fade accepted_cut picked lies in law L-b's bounds (FADE_MIN_S 10 ms .. VALLEY_FADE_S 83 ms). |

## Misreadings (verified from the code)

| # | claim | the code |
|---|---|---|
| K1 | qwen "P0-1" (its condition 1): _cut_head, _head_tail_of and hook_lead_at are new, not the render's | They ARE the render's. `git show c6605895:pipeline/sentence_law.py` (the integrator's branch, combo-letterbox-quoteonly-v2) defines them at lines 718 (_cut_head), 730 (_head_tail_of) and 743 (hook_lead_at). The render's trimmed_onset calls hook_lead_at. An AST source comparison (ast.get_source_segment of each top-level def) found all seven names byte-identical to that file: TRIMMABLE_LEADING, trimmed_boundary, trimmed_onset, edge_plan, _cut_head, _head_tail_of, hook_lead_at. |
| K2 | qwen "P0-2": the pin stage measures the onset on the UNCUT source window, not on the audio as cut | trim_onset calls SL.trimmed_onset(sa.path, cut_in, fade_in_ms). Through hook_lead_at, that calls _cut_head(src, c, fade_ms): ffmpeg `-ss c` decodes FROM the cut, and the clip's linear fade-in is applied to the first fade_ms. The measure is the audio AS CUT, exactly the render's function. Only the file differs: the render's source mp4, the pin stage's L-v 2 window of the same video. Hence the one-frame margin. |
| K3 | qwen P1-5 / glm P1-2: when the trimmed plan is not reached, the synthesised "trim" record copies a "why" that is not about the trimmed cut | Every early return of _measure is ON the trimmed cut's path: "no source audio" / "the clip's words are not inside its audio window" (NOT MEASURED), "no cut plan: <exception>" (edge_plan with the trimmed word raised), and "no cut after the trimmed word 'So': <trimmed_boundary's reason>" (FAIL). Each names why the trimmed cut has no measure or no plan. No change. |
| K4 | glm P2-7: `trims` in the log line is not shown | build() defines it (item 42's change, 1d928276): `trims = {m["moment_id"]: v for m in ms if m["moment_id"] in no_role for v in [trim_variant(m, sources)] if v}`, the variants that JOIN. |
| K5 | glm P1-5's

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0710/C2_STEP.diff (496 lines)
```
   1 | diff --git a/pipeline/hook_onset.py b/pipeline/hook_onset.py
   2 | index b5cc7c4..2faa5d1 100644
   3 | --- a/pipeline/hook_onset.py
   4 | +++ b/pipeline/hook_onset.py
   5 | @@ -20,6 +20,14 @@ applied, which can only make this check stricter.
   6 |  
   7 |  measure(...) -> {"pass", "measured", "lead_ms", "cut_in", "pad_s", "why"}. Not measured (no audio, no plan) is never
   8 |  a pass (law L-m).
   9 | +
  10 | +RULING 33 PART 2 (a trimmed moment: ONE leading but/and/so/well/now/yeah left out; item 42): the render plans the IN
  11 | +edge at the measured pause AFTER the trimmed word (sentence_law.trimmed_boundary, edge_plan(trimmed=...)), takes
  12 | +accepted_cut's cut and fade, and holds the clip unless the audio as cut opens in quiet (sentence_law.trimmed_onset:
  13 | +the first onset after the first 10 ms hop). measure(..., trimmed=word) plans and measures exactly that on the L-v 2
  14 | +window, with this slice's one-frame margin, in "trim" ({"pass", "measured", "why", ...}): ruling 33 (a), at any
  15 | +place. "pass" (may it OPEN a medley?) then also needs "trim". The render's functions are copied verbatim from its
  16 | +sentence_law.py at c6605895.
  17 |  """
  18 |  import sentence_law as SL
  19 |  import transcript_truth as TT
  20 | @@ -35,10 +43,41 @@ class _Slice(SL.SourceAudio):
  21 |          self.path, self.t, self.db, self.dur = sa.path, sa.t[m] - t0, sa.db[m], max(0.0, t1 - t0)
  22 |  
  23 |  
  24 | -def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  25 | +def trim_onset(sa, plan, a):
  26 | +    """Ruling 33 (a) as the render measures it at its cut table (write_lock_cut_table): accepted_cut's cut and fade,
  27 | +    then trimmed_onset on the audio as cut. Here on the L-v 2 window (sa.path), so the onset must lie one more 10 ms
  28 | +    frame after the cut than the render's rule asks (the slice vs the render's own decode, as for the hook's lead).
  29 | +    a: the window's start (video seconds). -> {"pass", "measured", "why", "onset_s", "cut_in", "fade_in_ms"}."""
  30 | +    try:
  31 | +        pick = SL.accepted_cut(sa.path, plan, sa=sa)
  32 | +        if pick is None:
  33 | +            return {"pass": False, "measured": True, "why": "no cut keeps the neighbour words inaudible (the render's "
  34 | +                                                                "accepted_cut finds none: it holds the clip)"}
  35 | +        _, r = SL.trimmed_onset(sa.path, pick["cut_in"], pick["fade_in_ms"])
  36 | +    except Exception as e:                               # no audio, no plan for an edge: never a pass (law L-m)
  37 | +        return {"pass": False, "measured": False, "why": f"not measured: {type(e).__name__}: {str(e)[:120]}"}
  38 | +    need = SL.HOP_S + MARGIN_MS / 1000
  39 | +    on = r.get("onset_s")
  40 | +    ok = on is not None and on > need + 1e-9
  41 | +    return {"pass": ok, "measured": True, "onset_s": on, "lead_ms": r.get("lead_ms"),
  42 | +            "cut_in": round(a + pick["cut_in"], 3), "fade_in_ms": pick["fade_in_ms"],
  43 | +            "why": "ok" if ok else f"the audio as cut opens on sound: first onset {on} s, not after {need:.2f} s (the "
  44 | +                                   f"render's first 10 ms hop + one {MARGIN_MS} ms frame)"}
  45 | +
  46 | +
  47 | +def measure(src, w0, w1, video_id, start, end, work_dir, audio=None, trimmed=None):
  48 |      """The hook moment's planned prepared clip: does it keep >= HEAD_LEAD_MIN_S of genuine quiet before its first
  49 |      onset? src: the moment's eligibility Source; w0 / w1: its first / last word indices in src.tokens; start / end:
  50 | -    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window."""
  51 | +    the clip's times (video seconds). audio: (SourceAudio, window start s) to reuse (tests); else the L-v 2 window.
  52 | +    trimmed: the moment's trimmed_leading (ruling 33 part 2): the IN edge is planned after that word, and ruling
  53 | +    33 (a) is measured in "trim"; the record then carries "trim" on every path."""
  54 | +    rec = _measure(src, w0, w1, video_id, start, end, work_dir, audio, trimmed)
  55 | +    if trimmed and "trim" not in rec:                   # no plan was reached: the trimmed cut is not measured either
  56 | +        rec["trim"] = {"pass": False, "measured": rec.get("measured", False), "why": rec.get("why")}
  57 | +    return rec
  58 | +
  59 | +
  60 | +def _measure(src, w0, w1, video_id, start, end, work_dir, audio, trimmed):
  61 |      need = SL.HEAD_LEAD_MIN_S * 1000 + MARGIN_MS
  62 |      try:
  63 |          if audio is None:
  64 | @@ -56,13 +95,14 @@ def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  65 |      words = [{"word": toks[i]["word"], "start": float(toks[i]["start"]) - a, "end": float(toks[i]["end"]) - a}
  66 |               for i in idx]
  67 |      i0, i1 = idx.index(w0), idx.index(w1)
  68 | -    try:
  69 | -        plan = SL.edge_plan(sa, words, i0, i1)
  70 | +    try:                                                 # ruling 33 part 2: the render's planning of a trimmed IN edge
  71 | +        plan = SL.edge_plan(sa, words, i0, i1, trimmed={"word": trimmed} if trimmed else None)
  72 |      except Exception as e:                               # LawError: no audio to read levels from, and the like
  73 |          return {"pass": False, "measured": False, "why": f"no cut plan: {type(e).__name__}: {str(e)[:120]}"}
  74 |      cin = plan.get("in") or {}
  75 |      if not cin.get("cuttable"):
  76 | -        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut before the hook: "
  77 | +        return {"pass": False, "measured": True, "lead_ms": 0, "why": f"no cut "
  78 | +                f"{'after the trimmed word ' + repr(trimmed) if trimmed else 'before the hook'}: "
  79 |                  f"{cin.get('reason') or 'not cuttable'}"}
  80 |      cut_in = float(cin["cut"])
  81 |      out = plan.get("out") or {}
  82 | @@ -74,6 +114,12 @@ def measure(src, w0, w1, video_id, start, end, work_dir, audio=None):
  83 |      pad = float(cin.get("lead_in_pad_s") or 0.0)         # a room-tone pad: edge_plan allows one only at a file head
  84 |      lead = int(round(ht["lead_ms"] + pad * 1000))
  85 |      ok = lead >= need
  86 | -    return {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  87 | -            "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
  88 | -                                    f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
  89 | +    rec = {"pass": ok, "measured": True, "lead_ms": lead, "cut_in": round(a + cut_in, 3), "pad_s": pad,
  90 | +           "why": "ok" if ok else f"{lead} ms of genuine quiet before the hook's first onset < {need:.0f} ms "
  91 | +                                   f"(G17a's {SL.HEAD_LEAD_MIN_S * 1000:.0f} ms + one {MARGIN_MS} ms frame)"}
  92 | +    if trimmed:                                          # ruling 33 (a): the trimmed cut opens in quiet, any place
  93 | +        rec["trim"] = trim_onset(sa, plan, a)
  94 | +        if rec["trim"]["pass"] is not True:
  95 | +            rec.update(passed_lead=ok, why=f"the trimmed cut: {rec['trim']['why']}")
  96 | +            rec["pass"] = False
  97 | +    return rec
  98 | diff --git a/pipeline/package.py b/pipeline/package.py
  99 | index d266dbe..eb534da 100644
 100 | --- a/pipeline/package.py
 101 | +++ b/pipeline/package.py
 102 | @@ -1137,7 +1137,8 @@ def hook_onset_for(m, sources, work_dir, cache):
 103 |          import hook_onset as HO
 104 |          try:
 105 |              cache[m["moment_id"]] = HO.measure(src_of(m, sources), m["words"][0], m["words"][1], m["video_id"],
 106 | -                                               float(m["start"]), float(m["end"]), work_dir)
 107 | +                                               float(m["start"]), float(m["end"]), work_dir,
 108 | +                                               trimmed=m.get("trimmed_leading"))     # ruling 33 part 2 (item 42)
 109 |          except Exception as e:
 110 |              cache[m["moment_id"]] = {"pass": False, "measured": False, "why": f"{type(e).__name__}: {str(e)[:200]}"}
 111 |      return cache[m["moment_id"]]
 112 | @@ -1216,7 +1217,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 113 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
 114 |             "package": None}
 115 |      log(f"  {n_usable} usable, {len(no_role)} of them left out by the render's STAND_ALONE (an opener the clip scorer "
 116 | -        f"would have to affirm, or no place under the topic rule with the pin's screen), {len(ad_read)} on an ad-read "
 117 | +        f"would have to affirm, or no place under the topic rule with the pin's screen; {len(trims)} of them back as "
 118 | +        f"variants with ONE leading word trimmed, ruling 33 part 2), {len(ad_read)} on an ad-read "
 119 |          f"marker (the exclusion screen's deterministic part), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
 120 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
 121 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
 122 | @@ -1245,9 +1247,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 123 |      out["prescreen"]["hook_onset"] = {mid: "PASS" if m["hook_onset"].get("pass") is True else
 124 |                                        ("NOT MEASURED: " if not m["hook_onset"].get("measured") else "FAIL: ") +
 125 |                                        str(m["hook_onset"].get("why")) for mid, m in cleared.items()}
 126 | -    trim_cut = {mid: out["prescreen"]["hook_onset"][mid] for mid, m in cleared.items()     # ruling 33 (a): the
 127 | -                if m.get("trimmed_leading") and m["hook_onset"].get("pass") is not True}    # acoustic onset rule on the
 128 | -    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}                 # trimmed cut, any place
 129 | +    trim_cut = {mid: ("NOT MEASURED: " if not t.get("measured") else "FAIL: ") + str(t.get("why"))   # ruling 33 (a):
 130 | +                for mid, m in cleared.items() if m.get("trimmed_leading")        # the trimmed cut as the render plans
 131 | +                for t in [m["hook_onset"].get("trim") or {"measured": False, "why": "no trimmed-cut record"}]   # it
 132 | +                if t.get("pass") is not True}                                    # opens in quiet, at ANY place. Its
 133 | +    cleared = {mid: m for mid, m in cleared.items() if mid not in trim_cut}     # hook lead decides only whether it
 134 | +    # may OPEN the medley (hook_onset "pass", need_onset), never whether it may play as a clip (audit 0710 C1, qwen)
 135 |      out["prescreen"]["trim_cut"] = trim_cut
 136 |      log(f"  {sum(m['hook_onset'].get('pass') is True for m in cleared.values())} of them can open a medley "
 137 |          f"(G17a at the pin stage: genuine quiet before the first onset)")
 138 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 139 | index b283500..708c64a 100644
 140 | --- a/pipeline/sentence_law.py
 141 | +++ b/pipeline/sentence_law.py
 142 | @@ -79,6 +79,7 @@ PUNCT_WINDOW_WORDS = 60
 143 |  WORD_DURATION_RATIO_MIN = 0.85  # G17: rendered edge word keeps >= 85 % of its duration
 144 |  _TERMINAL = (".", "!", "?")
 145 |  _ABBREV = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "jr", "sr", "inc", "ltd", "corp", "prof", "approx"}
 146 | +TRIMMABLE_LEADING = frozenset({"but", "and", "so", "well", "now", "yeah"})   # ruling 33 part 2 (orchestrator '03:42')
 147 |  
 148 |  
 149 |  class LawError(Exception):
 150 | @@ -287,9 +288,47 @@ def boundary(sa, words, k):
 151 |      return {**rec, "valid": True}
 152 |  
 153 |  
 154 | -def edge_plan(sa, words, i0, i1):
 155 | -    """Boundaries around words[i0..i1] and the legal cut ranges they allow."""
 156 | -    bin_ = boundary(sa, words, i0 - 1)
 157 | +def trimmed_boundary(sa, words, i0, trimmed):
 158 | +    """Ruling 33 part 2 (orchestrator 2026-11-13 '03:42'): a lock may leave out ONE leading word (TRIMMABLE_LEADING) of a
 159 | +    whole sentence, recorded as lock['trimmed_leading']. Its IN edge is then the MEASURED PAUSE after that word, not a
 160 | +    sentence boundary: (1) words[i0 - 1] is the trimmed word; (2) the untrimmed sentence starts a sentence (the word
 161 | +    before it ends one in a punctuated stretch, or it is the transcript's first word): everything else about whole
 162 | +    sentences is unchanged; (3) a quiet run lies between the trimmed word and the first kept word, with a heard gap.
 163 | +    Otherwise invalid: the word cannot be cut cleanly (no pause, co-articulated) and the clip is held."""
 164 | +    import canon
 165 | +    k, word = i0 - 1, str((trimmed or {}).get("word") or "")
 166 | +    rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>", "before_word": words[i0]["word"],
 167 | +           "trimmed_leading": word, "lexical": "trimmed leading word (ruling 33 part 2)"}
 168 | +    tok = canon.canon_tokens(word)
 169 | +    if k < 0 or len(tok) != 1 or tok[0] not in TRIMMABLE_LEADING or canon.canon_tokens(words[k]["word"]) != tok:
 170 | +        return {**rec, "valid": False, "reason": f"the trimmed word {word!r} is not one of "
 171 | +                f"{'/'.join(sorted(TRIMMABLE_LEADING))} or not the word before the lock ({rec['after_word']!r})"}
 172 | +    if k > 0 and not (is_punctuated(words, k - 1) and is_terminal(words[k - 1]["word"])):
 173 | +        return {**rec, "valid": False, "reason": f"the untrimmed sentence does not start a sentence: "
 174 | +                f"{words[k - 1]['word']!r} before {word!r} does not end one"}
 175 | +    mid = lambda w: (w["start"] + w["end"]) / 2
 176 | +    quiet, lv = find_pause(sa, mid(words[k]), mid(words[i0]))
 177 | +    point, gap, pause = boundary_geometry(sa, words, k, lv, quiet)
 178 | +    rec.update(levels=lv, pause=pause, quiet_run=quiet, point=point, word_gap=gap)
 179 | +    if quiet is None or gap["end"] <= gap["start"]:
 180 | +        return {**rec, "valid": False, "reason": f"the trimmed word {word!r} cannot be cut cleanly: no measured pause "
 181 | +                f"between it and {words[i0]['word']!r} (co-articulated)"}
 182 | +    return {**rec, "valid": True}
 183 | +
 184 | +
 185 | +def trimmed_onset(src, cut_in, fade_in_ms):
 186 | +    """Ruling 33 part 2, the onset rule on the audio as cut: G17a's own measure (head_tail on the cut audio with the
 187 | +    clip's fade-in, hook_lead_at) finds quiet before the first sound (the first onset after the first 10 ms hop, the
 188 | +    criterion ruling 28 uses for 'quiet after the cut'): nothing of the trimmed word opens the clip. (ok, record)."""
 189 | +    lead, onset = hook_lead_at(src, cut_in, fade_in_ms)
 190 | +    ok = onset is not None and onset > HOP_S + 1e-9
 191 | +    return ok, {"cut_in": cut_in, "fade_in_ms": fade_in_ms, "onset_s": onset, "lead_ms": lead, "ok": ok}
 192 | +
 193 | +
 194 | +def edge_plan(sa, words, i0, i1, trimmed=None):
 195 | +    """Boundaries around words[i0..i1] and the legal cut ranges they allow. trimmed: the lock's trimmed_leading
 196 | +    (ruling 33 part 2): the IN edge is the measured pause after that word, and the cut must SIT in its quiet run."""
 197 | +    bin_ = trimmed_boundary(sa, words, i0, trimmed) if trimmed else boundary(sa, words, i0 - 1)
 198 |      bout = boundary(sa, words, i1)
 199 |      plan = {"in": bin_, "out": bout}
 200 |      if bin_["valid"]:
 201 | @@ -301,11 +340,14 @@ def edge_plan(sa, words, i0, i1):
 202 |              bin_.update(cut_lo=0.0, cut_hi=p["start"], cut=p["start"], lead_in_pad_s=pad, cuttable=True)
 203 |          else:                                             # DEC-10: anywhere in the heard gap; aim at the pause
 204 |              g = bin_.get("word_gap") or {"start": p["start"], "end": p["end"]}
 205 | -            hi = round(g["end"] - LEAD_MIN_S, 3)
 206 | +            lo, hi = g["start"], round(g["end"] - LEAD_MIN_S, 3)
 207 | +            if trimmed:                                   # ruling 33 part 2: inside the measured quiet run as well
 208 | +                q = bin_["quiet_run"]
 209 | +                lo, hi = max(lo, q["start"]), min(hi, round(q["end"] - LEAD_MIN_S, 3))
 210 |              target = max(p["start"], p["end"] - LEAD_TARGET_S) if p.get("ms", 0) > 0 else bin_.get("point", p["start"])
 211 | -            bin_.update(cut_lo=g["start"], cut_hi=hi, cuttable=hi >= g["start"] - 1e-9,
 212 | -                        cut=round(min(max(target, g["start"]), hi), 3), lead_in_pad_s=0.0,
 213 | -                        reason=None if hi >= g["start"] - 1e-9 else "no room before the first word")
 214 | +            bin_.update(cut_lo=lo, cut_hi=hi, cuttable=hi >= lo - 1e-9,
 215 | +                        cut=round(min(max(target, lo), hi), 3), lead_in_pad_s=0.0,
 216 | +                        reason=None if hi >= lo - 1e-9 else "no room before the first word")
 217 |      if bout["valid"]:
 218 |          p = bout["pause"]
 219 |          guard = 0.0 if bout.get("file_end") else GUARD_S
 220 | @@ -667,6 +709,37 @@ def _accepted_cut_pair(src, plan, step=HOP_S):
 221 |      return (c["cut_in"], c["cut_out"]) if c else None
 222 |  
 223 |  
 224 | +def _cut_head(src, c, fade_ms):
 225 | +    """LEVEL_WINDOW_S of `src` from `c`, stereo 48 kHz float, with the clip's own linear fade-in of `fade_ms` applied
 226 | +    as prepare applies it (audit batch 56 C1, qwen: measure what the prepared clip will hold)."""
 227 | +    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{c:.3f}", "-i", src, "-t", f"{LEVEL_WINDOW_S}", "-vn", "-ac",
 228 | +                        "2", "-ar", "48000", "-f", "f32le", "-"], capture_output=True, check=True, timeout=60)
 229 | +    x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64).copy()
 230 | +    k = min(len(x), int(round(fade_ms / 1000 * 48000)))
 231 | +    if k > 0:
 232 | +        x[:k] *= np.linspace(0.0, 1.0, k)[:, None]
 233 | +    return x
 234 | +
 235 | +
 236 | +def _head_tail_of(x):
 237 | +    import tempfile
 238 | +    import wave
 239 | +    with tempfile.TemporaryDirectory() as d:
 240 | +        w = os.path.join(d, "head.wav")
 241 | +        with wave.open(w, "wb") as f:
 242 | +            f.setnchannels(2)
 243 | +            f.setsampwidth(2)
 244 | +            f.setframerate(48000)
 245 | +            f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
 246 | +        return head_tail(SourceAudio(w))
 247 | +
 248 | +
 249 | +def hook_lead_at(src, c, fade_ms=0):
 250 | +    """(genuine lead ms, onset s) of the audio as cut at `c` with its fade-in: G17a's own measure (head_tail)."""
 251 | +    ht = _head_tail_of(_cut_head(src, c, fade_ms))
 252 | +    return ht["lead_ms"], ht["onset"]
 253 | +
 254 | +
 255 |  def write_lock_cut_table(run_dir):
 256 |      """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
 257 |      the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
 258 | diff --git a/tests/package/funnel.py b/tests/package/funnel.py
 259 | index 45ccfe8..5e25d43 100644
 260 | --- a/tests/package/funnel.py
 261 | +++ b/tests/package/funnel.py
 262 | @@ -39,8 +39,20 @@ def q(t, n=140):
 263 |      return t if len(t) <= n else t[:n - 1] + "…"
 264 |  
 265 |  
 266 | +def mom(mid):
 267 | +    """The moment's record; a trimmed variant ("<id>~trim", ruling 33 part 2) is named by its original, with the
 268 | +    trimmed word marked (the record keeps the variant's id only)."""
 269 | +    if mid in by:
 270 | +        return by[mid]
 271 | +    o = by.get(str(mid).removesuffix("~trim"))
 272 | +    if o is None:
 273 | +        return {}
 274 | +    w, _, rest = (o.get("text") or "").partition(" ")
 275 | +    return dict(o, moment_id=mid, text=f"[{w} trimmed] {rest}", duration_s=f"under {o.get('duration_s')}")
 276 | +
 277 | +
 278 |  def tx(mid):
 279 | -    return by.get(mid, {}).get("text") or texts.get(mid) or ""
 280 | +    return mom(mid).get("text") or texts.get(mid) or ""
 281 |  
 282 |  
 283 |  def emit(title, rows, head=("lost", "exact reason", "one example (moment text)")):
 284 | @@ -189,7 +201,7 @@ try:
 285 |      import transcript_truth as TT
 286 |      rt = P.Router(record_dir=REPLIES, replay=True)
 287 |      for mid in lost3:
 288 | -        m = by[mid]
 289 | +        m = mom(mid)
 290 |          try:
 291 |              t = TT.verify_segment(rt, m["video_id"], float(m["start"]), float(m["end"]), m["text"], LV2)
 292 |              e = t.get("edges") or {}
 293 | @@ -219,25 +231,36 @@ if len(lost3) > 1:
 294 |      print("\nEvery stage-3 loss, exactly:")
 295 |      for mid in lost3:
 296 |          k, d = detail.get(mid, (sp[mid], ""))
 297 | -        print(f"- {by[mid].get('channel_name')}: {k}: {q(d, 260)}")
 298 | +        print(f"- {mom(mid).get('channel_name')}: {k}: {q(d, 260)}")
 299 |  
 300 |  # ---- stage 4: cuttable -> can open
 301 |  ho = pre.get("hook_onset") or {}
 302 |  lost4 = [(v, mid) for mid, v in ho.items() if v != "PASS"]
 303 |  emit(f"Stage 4: {pre.get('cuttable')} cuttable -> {sum(v == 'PASS' for v in ho.values())} can open a medley (G17a; "
 304 |       f"the others stay in play as non-hook clips)", grouped(lost4) or [[0, "-", "-"]])
 305 | +tc, sv = pre.get("trim_cut") or {}, pre.get("second_vendor") or {}
 306 | +if pk.get("trimmed") is not None:
 307 | +    print(f"\nTrimmed variants (ruling 33 part 2): {len(pk['trimmed'])} of the {len(pk.get('no_role') or {})} left "
 308 | +          f"out by STAND_ALONE joined the usable moments; {len(tc)} cleared to here and failed the trimmed cut (a), at "
 309 | +          f"any place:")
 310 | +    for mid, why in tc.items():
 311 | +        print(f"- {mom(mid).get('channel_name')}: {q(why, 200)}: \"{q(tx(mid), 120)}\"")
 312 | +sv_lost = [(v, mid) for mid, v in sv.items() if not str(v).startswith("PASS")]
 313 | +if sv:
 314 | +    emit(f"Stage 4b: step A from the second vendor (order 06:22 item 45): {len(sv) - len(sv_lost)} of {len(sv)} pass",
 315 | +         grouped(sv_lost) or [[0, "-", "-"]])
 316 |  
 317 |  # ---- stage 5: -> angle -> line-ups
 318 |  print(f"\n**Stage 5: the angle step and the line-ups.** why_none: {pk.get('why_none')!r}; angles: "
 319 |        f"{len(pk.get('angles') or [])} from {pk.get('angle_backend')}")
 320 | -cl = [mid for mid, v in sp.items() if v == "PASS"]
 321 | +cl = [mid for mid, v in sp.items() if v == "PASS" and mid not in tc and not str(sv.get(mid, "PASS")).startswith("FAIL")]
 322 |  print("\nThe moments offered to the angle step:")
 323 |  for mid in cl:
 324 | -    m = by.get(mid, {})
 325 | +    m = mom(mid)
 326 |      print(f"- {m.get('channel_name')} ({m.get('video_id')}), {m.get('duration_s')} s, can open: "
 327 |            f"{ho.get(mid) == 'PASS'}: \"{q(m.get('text'), 150)}\"")
 328 |  print(f"\nTogether {round(sum(float(by[m]['duration_s']) for m in cl if m in by), 2)} s from "
 329 | -      f"{len({by[m]['channel_id'] for m in cl if m in by})} channels.")
 330 | +      f"{len({mom(m)['channel_id'] for m in cl if mom(m)})} channels (a trimmed variant's seconds not counted).")
 331 |  for a in pk.get("angles") or []:
 332 |      print(f"- angle: \"{q(a.get('angle'), 200)}\" moments {len(a.get('moments') or [])}")
 333 |  log = open(os.path.join(D, "package.log")).read().splitlines()
 334 | diff --git a/tests/package/test_hook_onset.py b/tests/package/test_hook_onset.py
 335 | index 536bcd7..6b01bd6 100644
 336 | --- a/tests/package/test_hook_onset.py
 337 | +++ b/tests/package/test_hook_onset.py
 338 | @@ -4,8 +4,11 @@ kept 30 ms of genuine quiet before its first onset. The word record showed a 400
 339 |  then DIGITAL ZEROS (a hard edit), then speech. Offline: synthetic 10 ms envelopes, built to the render's own level
 340 |  rules (sentence_law: speech near -20 dBFS, room tone near -55, digital zeros below DIGITAL_FLOOR_DBFS)."""
 341 |  import os
 342 | +import shutil
 343 |  import sys
 344 | +import tempfile
 345 |  import unittest
 346 | +import wave
 347 |  
 348 |  import numpy as np
 349 |  
 350 | @@ -89,5 +92,77 @@ class TestHookOnset(unittest.TestCase):
 351 |          self.assertIn("not inside its audio window", r["why"])
 352 |  
 353 |  
 354 | +TRIM_WORDS = [("Before", 0.20, 0.60), ("this", 0.60, 0.95), ("markets.", 0.95, 1.35),   # the previous sentence
 355 | +              ("So", 1.75, 1.95),                                                       # the trimmed word
 356 | +              ("Bitcoin", 2.40, 2.80), ("rises.", 2.80, 3.30),                          # the clip: words 4..5
 357 | +              ("Next", 3.70, 4.10), ("words", 4.10, 4.50), ("follow.", 4.50, 5.10)]
 358 | +TRIM_SPEECH = [(0.20, 1.35, -20.0), (2.40, 3.30, -20.0), (3.70, 5.10, -20.0)]
 359 | +
 360 | +
 361 | +def wav(path, spans, dur=6.0, bed=-55.0, sr=16000):
 362 | +    """A real 16 kHz file: white noise at `bed` dBFS RMS (room tone), louder noise over `spans` [(t0, t1, dBFS)]."""
 363 | +    lv = np.full(int(dur * sr), 10 ** (bed / 20))
 364 | +    for a, b, v in spans:
 365 | +        lv[int(a * sr):int(b * sr)] = 10 ** (v / 20)
 366 | +    x = np.clip(np.random.default_rng(7).standard_normal(len(lv)) * lv, -1, 1)
 367 | +    with wave.open(path, "wb") as f:
 368 | +        f.setnchannels(1)
 369 | +        f.setsampwidth(2)
 370 | +        f.setframerate(sr)
 371 | +        f.writeframes((x * 32767).astype(np.int16).tobytes())
 372 | +    return path
 373 | +
 374 | +
 375 | +def trim_src():
 376 | +    toks = tuple({"word": w, "start": a, "end": b} for w, a, b in TRIM_WORDS)
 377 | +    return E.Source("vidT", "UCx", "X", "2026-11-12T00:00:00+00:00", "sha", "whisper_words_punct", toks,
 378 | +                    timing="word", file_head=False, vod=True)
 379 | +
 380 | +
 381 | +class TestTrimmedCut(unittest.TestCase):
 382 | +    """Ruling 33 part 2 (item 42): a trimmed moment's IN edge is planned AFTER the trimmed word, as the render plans it
 383 | +    (sentence_law.trimmed_boundary / edge_plan(trimmed=...), verbatim from its c6605895), and ruling 33 (a) is the
 384 | +    render's own onset rule on the audio as cut (accepted_cut's cut and fade, then trimmed_onset), with one more 10 ms
 385 | +    frame here. On a generated audio file: the render's rule decodes the file. The 05:48 build's two cleared trims
 386 | +    failed the old measure, which only cut after a sentence end ("'So' does not end a sentence")."""
 387 | +
 388 | +    def setUp(self):
 389 | +        self.d = tempfile.mkdtemp()
 390 | +
 391 | +    def tearDown(self):
 392 | +        shutil.rmtree(self.d, ignore_errors=True)
 393 | +
 394 | +    def measure(self, spans, trimmed="So"):
 395 | +        sa = SL.SourceAudio(wav(os.path.join(self.d, "t.wav"), spans))
 396 | +        return HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(sa, 0.0), trimmed=trimmed)
 397 | +
 398 | +    def test_a_measured_pause_after_the_trimmed_word_passes(self):
 399 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                 # "So", 450 ms of room tone, "Bitcoin"
 400 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"]), (True, True), r)
 401 | +        self.assertGreater(r["trim"]["onset_s"], SL.HOP_S + HO.MARGIN_MS / 1000)
 402 | +        self.assertTrue(1.95 <= r["trim"]["cut_in"] < 2.40, r["trim"])        # the cut sits in the pause
 403 | +        self.assertTrue(SL.FADE_MIN_S * 1000 - 1e-6 <= r["trim"]["fade_in_ms"] <= SL.VALLEY_FADE_S * 1000 + 1,
 404 | +                        r["trim"])                                            # with law L-b's fade (accepted_cut)
 405 | +        self.assertTrue(r["pass"], r)                                         # and its lead lets it open a medley
 406 | +
 407 | +    def test_a_trimmed_word_run_into_the_next_cannot_be_cut(self):
 408 | +        r = self.measure([(0.20, 1.35, -20.0), (1.75, 3.30, -20.0), (3.70, 5.10, -20.0)])   # no pause after "So"
 409 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, True, False), r)
 410 | +        self.assertIn("cannot be cut cleanly", r["trim"]["why"])
 411 | +
 412 | +    def test_the_trimmed_word_must_be_the_word_heard_before_the_clip(self):
 413 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed="But")
 414 | +        self.assertEqual((r["trim"]["pass"], r["pass"]), (False, False), r)
 415 | +        self.assertIn("not the word before the lock", r["trim"]["why"])
 416 | +
 417 | +    def test_untrimmed_is_unchanged_and_no_audio_file_is_never_a_pass(self):
 418 | +        r = self.measure(TRIM_SPEECH + [(1.75, 1.95, -20.0)], trimmed=None)   # the old rule: a sentence end first
 419 | +        self.assertEqual((r["pass"], "trim" in r), (False, False), r)
 420 | +        self.assertIn("does not end a sentence", r["why"])
 421 | +        env = Env(TRIM_SPEECH + [(1.75, 1.95, -20.0)])                        # an envelope, no file to cut (law L-m)
 422 | +        r = HO.measure(trim_src(), 4, 5, "vidT", 2.40, 3.30, self.d, audio=(env, 0.0), trimmed="So")
 423 | +        self.assertEqual((r["trim"]["pass"], r["trim"]["measured"], r["pass"]), (False, False, False), r)
 424 | +
 425 | +
 426 |  if __name__ == "__main__":
 427 |      unittest.main()
 428 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 429 | index 3cb6fa9..89f8ad6 100644
 430 | --- a/tests/package/test_medley.py
 431 | +++ b/tests/package/test_medley.py
 432 | @@ -425,11 +425,12 @@ class Rig:
 433 |              "referents": [], "conditions": [], "retraction": "none", "time_ok": "yes", "certainty": "certain"}
 434 |  
 435 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 436 | -                 spend=None, no_hook=()):
 437 | +                 spend=None, no_hook=(), trim_fail=()):
 438 |          import providers as P
 439 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 440 |          self.takeaways, self.spend = list(takeaways or []), spend
 441 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 442 | +        self.trim_fail = set(trim_fail)                    # trimmed moments whose trimmed cut fails ruling 33 (a)
 443 |          self.medley_calls, self.write_calls, self.prompts = [], [], []
 444 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 445 |          self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}])
 446 | @@ -462,6 +463,17 @@ class Rig:
 447 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 448 |          return self.P.Reply("{}", "heimdall:deepseek", "heimdall", family="deepseek"), fields
 449 |  
 450 | +    def onset(self, m, *a, **k):
 451 | +        """hook_onset.measure's record: the hook lead, and for a trimmed moment its trimmed cut ("trim")."""
 452 | +        r = ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"} if m["moment_id"] in self.no_hook
 453 | +             else {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"})
 454 | +        if m.get("trimmed_leading"):
 455 | +            ok = m["moment_id"] not in self.trim_fail
 456 | +            r["trim"] = {"pass": ok, "measured": True, "why": "ok" if ok else "the trimmed word 'But' cannot be cut "
 457 | +                                                                              "cleanly: no measured pause (co-articulated)"}
 458 | +            r["pass"] = r["pass"] and ok
 459 | +        return r
 460 | +
 461 |      def run(self):
 462 |          fid = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
 463 |                 "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 464 | @@ -479,9 +491,7 @@ class Rig:
 465 |                                                           "backend": "xai:grok"},
 466 |              "truth_for": lambda router, m, *a, **k: {"ok": True, "replayed": False, "model": "scribe_v1",
 467 |                                                       "edges": {"cuttable": m["moment_id"] not in self.uncuttable}},
 468 | -            "hook_onset_for": lambda m, *a, **k: ({"pass": False, "measured": True, "lead_ms": 20, "why": "20 ms < 80"}
 469 | -                                                  if m["moment_id"] in self.no_hook else
 470 | -                                                  {"pass": True, "measured": True, "lead_ms": 200, "why": "ok"}),
 471 | +            "hook_onset_for": self.onset,
 472 |              "coherence": lambda router, pk, *a, **k: (True, {"through_line": "Nobody gets to bend the rules.",
 473 |                                                               "clips": {sg["label"]: 5 for sg in pk["segments"]},
 474 |                                                               "vo_point": 5, "backend": "xai:grok", "measured": True,
 475 | @@ -828,13 +838,18 @@ class TestRuling33TrimAtThePinStage(unittest.TestCase):
 476 |          saved = PK.trim_variant
 477 |          try:
 478 |              PK.trim_variant = lambda m, sources: v if m["moment_id"] == "b" else None
 479 | -            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 480 | +            rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], trim_fail={"b~trim"})
 481 |              out = rig.run()
 482 | +            rig2 = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None], no_hook={"b~trim"})
 483 | +            out2 = rig2.run()
 484 |          finally:
 485 |              PK.trim_variant = saved
 486 |          self.assertEqual(out["trimmed"], {"b": "b~trim"})
 487 | -        self.assertIn("b~trim", out["prescreen"]["trim_cut"])                     # ruling 33 (a): out, any place
 488 | +        self.assertTrue(out["prescreen"]["trim_cut"]["b~trim"].startswith("FAIL: the trimmed word"))   # (a): out
 489 | +        self.assertNotIn("id=b~trim ", next(p for r, p in rig.prompts if r == "angle_write"))         # at any place
 490 |          self.assertIsNotNone(out["package"])
 491 | +        self.assertEqual(out2["prescreen"]["trim_cut"], {})        # its cut is clean, only its hook lead fails: it
 492 | +        self.assertIn("id=b~trim ", next(p for r, p in rig2.prompts if r == "angle_write"))   # stays as a clip
 493 |  
 494 |  
 495 |  class TestRuling41Search(unittest.TestCase):
 496 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips).
This branch builds sealed pins of short video medleys (a hook + 2-4 clips from other channels); the integrator
renders them. Your role: a strict reviewer of the pin stage's acoustic cut measure for TRIMMED clips.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Background (static):
- ORCHESTRATOR RULING 33 (03:12 ET Nov 13): "A clip that opens on a discourse conjunction or reply word (but, and,
  so, well, now, yeah) may have that ONE leading word trimmed at the cut when (a) the acoustic onset rule is met on
  the trimmed cut, and (b) the pipeline's STAND_ALONE scorer affirms the trimmed clip at its unchanged threshold, and
  (c) L-s step A is re-judged on the trimmed span. The locked text is the trimmed text. If any of the three fails, the
  clip is out." ORDER 04:58 item 42: use it now (the render merged it).
- The RENDER (the integrator's branch, pipeline/sentence_law.py at c6605895, unchanged since) cuts a trimmed clip so:
  edge_plan(sa, words, i0, i1, trimmed=lock["trimmed_leading"]) plans the IN edge with trimmed_boundary (the
  word before the lock is the trimmed word; the untrimmed sentence starts a sentence; a quiet run with a heard gap
  lies between the trimmed word and the first kept word), and the cut must sit inside that quiet run; then
  accepted_cut picks the cut and its fade; then trimmed_onset(src, cut_in, fade_in_ms) holds the clip unless the
  audio as cut opens in quiet (the first onset after the first 10 ms hop).
- The pin stage (this branch) measures each cuttable moment on its law-L-v-2 audio window (a 16 kHz WAV of
  [start - 4 s, end + 1.5 s], fetched once) with hook_onset.measure: a planned cut, then G17a's genuine lead before
  the first onset, with ONE extra 10 ms frame of margin (the slice vs the render's own decode).
- THE DEFECT this diff fixes: hook_onset.measure planned every IN edge with the OLD edge_plan, which only cuts after a
  sentence end. A trimmed clip's IN edge sits after the trimmed word, which never ends a sentence. So both trimmed
  variants that cleared step A and L-v 2 in the 05:48 build failed with "no cut before the hook: 'So' does not end a
  sentence": a gap in the pin stage, not a property of the moments.
- Ruling 33 (b) is NOT in this diff: the pin stage keeps (b) strict (TRIM_SCORER_PENDING = False), so a line-up with
  a trimmed clip still fails STAND_ALONE until the orchestrator rules. This diff only makes (a) measurable as the
  render measures it.
- Laws: nothing measured is never a pass (L-m); fail closed (L-j); never change what a check accepts to make
  something pass.

The change:
1. pipeline/sentence_law.py: copied VERBATIM from the render's c6605895 (verified byte-identical by an AST source
   comparison): TRIMMABLE_LEADING, trimmed_boundary, trimmed_onset, edge_plan(trimmed=None) (identical to the old
   edge_plan when trimmed is None), and the three helpers trimmed_onset needs (_cut_head, _head_tail_of,
   hook_lead_at). Nothing else of the render's newer law is taken. No function is removed.
2. pipeline/hook_onset.py:
   - measure(..., trimmed=None): with a trimmed word, the plan is edge_plan(..., trimmed={"word": trimmed}), the
     render's own shape (its lock carries {"word": ...}).
   - trim_onset(sa, plan, a): accepted_cut on the window file, then trimmed_onset, then the pin stage's one-frame
     margin: the onset must lie after 10 ms + 10 ms. Any exception: "not measured", never a pass.
   - The record carries "trim" on every path for a trimmed moment; "pass" (may it OPEN a medley) also needs it.
3. pipeline/package.py:
   - hook_onset_for passes trimmed=m.get("trimmed_leading").
   - build(): a trimmed moment is left out at ANY place when its "trim" record is not a pass (ruling 33 (a)). Before,
     it was left out whenever its HOOK lead failed, which is a different rule (G17a applies to the hook only).
   - The STAND_ALONE log line counts the trimmed variants (order 06:22 item 47).
4. tests/package/funnel.py (the build-record report): a "<id>~trim" variant is named by its original moment instead
   of a blank row or a KeyError; the variants are counted; the moments offered to the angle step exclude the
   trimmed-cut failures (and, when the record has it, the second vendor's step-A failures of the other change).
5. Tests:
   - test_hook_onset: four tests on a GENERATED 16 kHz audio file (the render's rule decodes the file): a measured
     pause after "So" passes (the cut inside the pause, the onset after 20 ms, and the hook lead too); "So" run into
     the next word cannot be cut cleanly; a trimmed word that is not the word before the clip fails; the untrimmed
     rule is unchanged and an envelope with no file is "not measured", never a pass.
   - test_medley: the build rig's onset stub carries the "trim" record. A trimmed moment whose trimmed cut fails is
     out at any place, never offered to the angles; one whose cut is clean but whose hook lead fails stays as a clip.
- Measured on the real data (the 05:48 build's two cleared trims, their own L-v 2 windows), before this audit:
  "So MSCI didn't force any Bitcoin selling this week..." passes (cut in the pause after "So", first onset 130 ms,
  83 ms fade); "So if you look at the average income..." fails ("So" runs into "if": no measured pause).

Stated assumption (K1): the render's trimmed_boundary treats a trimmed word that is the transcript's FIRST word as a
file head. On the pin stage's window the first word is only the window's first word, so that sentence-start check can
pass without its evidence there. The untrimmed sentence's start is ALREADY verified on the full word record by
eligibility (the original moment's IN rule: the word before it ends a sentence, or the file head), and a trimmed
variant inherits that verdict. Say so if you think that is not enough.

Check in particular:
- that the copied functions are used exactly as the render uses them (the trimmed dict shape, the plan, accepted_cut,
  then trimmed_onset), and that any divergence only makes the pin stage stricter;
- that every failure to plan, cut or decode is never a pass, and that "trim" is present on every path for a trimmed
  moment;
- that untrimmed moments are judged exactly as before (the hook lead rule and the old IN boundary);
- that the build's new rule (out at any place only when the trimmed cut fails) is right under ruling 33 (a), and
  that the hook still needs both;
- the funnel changes: nothing in them changes a build.

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
