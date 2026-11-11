# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pulse-sentence-law
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GROK — CYCLE 1 OUTPUT
**Q1: CORRECTNESS**  
The changed functions match their docstrings and the governing laws as shown in the diff. `anchor` (lines 983-1012) locates selected text by token alignment and returns `(i0, i1, ratio)` only when first/last tokens match. `boundary`/`edge_plan` (903-978) enforce both lexical (punctuation or adjudicator) and acoustic (>=80 ms pause) conditions before declaring `cuttable`. `write_lock_cut_table` (1070-1109) and `_accepted_cut_pair` (1050-1067) restrict cuts to the legal pause ranges from the lock; no path allows movement outside those ranges. `gate_g16` (1115-1150) and the G17 gates reject on missing lock, mismatched expected words, or out-of-range cuts. M12 fail-closed behavior is present: missing transcript, failed adjudication, or no valid pause produces errors/rejections (e.g., lines 1131, 1144, 1093). No silent exceptions or state leakage between clips is visible. No off-by-one or unit errors in the arithmetic shown.

**Q2: LAW COMPLIANCE**  
- SENTENCE LAW: Compliant (boundary + acoustic checks in `boundary`, 903-948; constants at 694-697).  
- SELECTION LOCK: Compliant (`make_lock`/`verify_lock` at 1020-1039; `selection_lock` written to EDL at 79, 605; never recomputed).  
- SNAP LIMIT: Compliant (`_accepted_cut_pair` searches only inside `cut_lo`/`cut_hi` from the lock; old ` _snap_candidates` removed at 164-202).  
- ONSET/TAIL: Compliant (`edge_plan` lead/tail rules at 962-977; G17a/b at 1249-1309; declared `lead_in_pad_s` at 1106).  
- CREDITS: No change (unchanged per header).  
- LAW 20/M2, M12, LAW 22: Compliant (hard stops, fail-closed, no threshold loosening, v2f path untouched).  
No path allows a cut outside the locked sentence's silence or recomputation of expected words after selection.

**Q3: TESTS**  
Tests prove the claim. `test_pulse_20261110_mustfail.py` asserts the exact D1/D2/D3 failure reasons and expected words (e.g., lines 1463, 1473, 1482). Controls (D3c, faithful render) assert PASS for the right reason. `test_pinned.py` and `test_fresh.py` confirm the old snap path is unreachable and locks are sealed at selection. No vacuous assertions visible.

**Q4: VERDICT**  
No defects found in the diff.  

READY

## GPT4O — CYCLE 1 OUTPUT
### Q1: CORRECTNESS

1. **Functionality and Docstring Alignment**: 
   - The `validate_schema` function (lines 5-12) ensures that machine-built PINs have approved text for each segment, aligning with the docstring.
   - The `validate_range` function (lines 24-47) correctly updates the range validation to use the `sentence_law.anchor` method, which aligns with the requirement to locate words by text rather than by arithmetic.
   - The `build_edl` function (lines 50-82) constructs the EDL with selection locks, ensuring that the selection lock is created and added to each segment.
   - The `stage_cut` function (lines 204-275) removes snapping and ensures cuts are placed within the locked sentence's silence, aligning with the stated laws.
   - The `stage_sentence_law` function (lines 278-294) implements the G16 gate, ensuring that cuts hold exactly their locked sentences.
   - The `apply_lead_in_pad` function (lines 1204-1228) correctly appends room tone to the start of clips with insufficient lead-in, as per the docstring and laws.

2. **Time and Index Handling**: 
   - The use of seconds and milliseconds appears consistent with the laws. For example, `PAUSE_MIN_S` is consistently used as 80 ms (lines 694-695).

3. **Error Handling and Missing Data**:
   - The `write_lock_cut_table` function (lines 1070-1109) handles errors by marking entries as unverified if locks are not cuttable or if `cut_accept` fails, ensuring no invalid cuts are produced.
   - The `gate_g16` function (lines 1115-1150) ensures that errors are collected and reported, preventing a pass if any errors exist.

### Q2: LAW COMPLIANCE

1. **SENTENCE LAW**: COMPLIANT
   - The changes ensure that clips start and end at sentence boundaries, with cuts placed inside the silence (lines 204-275, 1070-1109).

2. **SELECTION LOCK**: COMPLIANT
   - The selection lock is created during selection and not recomputed (lines 545-606).

3. **SNAP LIMIT**: COMPLIANT
   - Snapping is removed, and cuts are placed strictly within the locked sentence's silence (lines 204-275).

4. **ONSET/TAIL**: COMPLIANT
   - The `apply_lead_in_pad` function ensures a genuine lead-in, and the G17 gate checks for sufficient lead-in and tail (lines 1204-1228, 1231-1309).

5. **CREDITS**: COMPLIANT
   - The tests ensure that only valid avatars are used, complying with the credits law (lines 1543-1553).

6. **LAW 20 / M2**: COMPLIANT
   - Gate thresholds are constants, and failures result in a hard stop (lines 278-294, 1115-1150).

7. **M12 FAIL CLOSED**: COMPLIANT
   - Missing data or model failure results in rejection, not a pass (lines 1070-1109).

8. **LAW 22**: COMPLIANT
   - No changes suggest that the v2f reference path would behave differently.

### Q3: TESTS

1. **Must-Fail Fixtures**:
   - The tests for G16 and G17 gates (lines 1443-1523) correctly identify failures due to insufficient lead-in and incorrect sentence boundaries.
   - The `TestSelectionLockEdges` class verifies that selection locks are correctly applied and not recomputed (lines 1443-1444).

2. **Controls**:
   - The `TestD4Credits` class ensures that valid avatars are accepted, and invalid ones are rejected (lines 1543-1553).

3. **Assertions**:
   - Assertions in tests like `test_faithful_render_passes` ensure that the render passes when it should (lines 1505-1508).

### Q4: VERDICT

1. **SEVERITY: LOW | Line 204-275 | Issue: Redundant import statement in `stage_cut` function | Fix: Remove redundant import of `sentence_law` inside the function.**

2. **SEVERITY: LOW | Line 1543-1553 | Issue: Test setup could be optimized | Fix: Use `setUpClass` and `tearDownClass` for temporary directory management.**

Overall, the code changes align with the laws, and the tests effectively verify compliance. The identified issues are minor and do not affect the overall readiness.

**READY**

## GEMINI — CYCLE 1 OUTPUT
Excellent. This is a substantial and critical feature. I will now perform the requested code audit.

---

### Q1: CORRECTNESS

The changed functions appear to correctly implement their stated logic, with a strong emphasis on "fail closed" principles (Law M12).

*   **`pipeline/sentence_law.py`:** This new module forms the core of the feature and is well-designed.
    *   **Audio Processing (`SourceAudio`)**: The use of `subprocess.run` with `check=True` (L759) ensures that `ffmpeg` failures are not silent. The check for `n == 0` (L764) correctly raises an error if no audio is decoded, preventing downstream failures on empty data.
    *   **Boundary Adjudication**: The `Adjudicator` class (L838) is robust. It uses a content-addressed cache, makes cache writes atomic via `os.replace` (L890), and logs every decision (L892-898). The `allow_model=False` mode (L871) correctly raises a `LawError` for a cache miss, ensuring deterministic replays for gates.
    *   **Failure Propagation**: `boundary()` (L903) and `edge_plan()` (L951) correctly return records with `valid: False` and a reason, rather than raising exceptions for expected failures (like no pause). This descriptive failure is handled gracefully by `write_lock_cut_table()` (L1070) and `gate_g16()` (L1115), which record the reasons and fail the segment. This is excellent adherence to M12.
    *   **Cut Placement (`_accepted_cut_pair`)**: The logic correctly searches *only* within the legal windows (`pi["cut_lo"]`, `pi["cut_hi"]`, etc.) provided by the `edge_plan` (L1062-1063). This prevents cuts from moving outside the allowed silence, a key correctness requirement.
    *   **Units**: Time units appear consistently in seconds (e.g., `PAUSE_MIN_S = 0.080`), and conversions to milliseconds for reporting are explicit (e.g., `int(round((e - s) * 1000))`). No inconsistencies were found.

*   **`pipeline/run_fresh.py`:** The refactoring is a major correctness improvement.
    *   The complete removal of `_recompute_edge_words` and the complex, stateful `_snap_candidates` logic (L106-202, L238-259, L329-368) eliminates the entire class of bugs that caused D2/D3. The new flow is linear and stateless between segments.
    *   The introduction of the pre-render `stage_sentence_law` (L278, L452) is a good "fail fast" design, preventing wasted rendering time.
    *   The logic to handle `lead_in_pad_s` is correctly applied to clip duration checks (`check_clip`, L325) and G14 manifest generation (L390-399), preventing these pads from causing false-positive gate failures.

*   **`pipeline/select_passages.py`:**
    *   The replacement of `_find_word_boundaries` (which used time-based heuristics) with `sentence_law.anchor` and `sentence_law.edge_plan` (L540, L559, L567) is a fundamental fix. It ensures that segment selection is based on the *text* and its acoustic viability from the start, which is the core of the Sentence Law.

Overall, the code is of high quality. It correctly handles error conditions, avoids state leakage, uses consistent units, and the core logic appears sound and free of off-by-one errors.

### Q2: LAW COMPLIANCE

*   **SENTENCE LAW**: **COMPLIANT**. Implemented in `pipeline/sentence_law.py`. The `boundary` function (L903) requires both a lexical condition (`is_terminal` or `Adjudicator`) and an acoustic pause (`find_pause`, L928) of at least `PAUSE_MIN_S` (L694, 80 ms).
*   **SELECTION LOCK**: **COMPLIANT**. `select_passages.py` and `pinned.py` now create a `selection_lock` (L565, L55). This lock is verified against the transcript's SHA256 at cut time (`write_lock_cut_table`, L1082) and during gating (`gate_g16`, L1128). `gate_g16` explicitly fails if the `expected` words in `cuts_final.json` do not match the lock (L1133), preventing re-computation. The old re-computation code is deleted.
*   **SNAP LIMIT**: **COMPLIANT**. The old snapping logic that could search up to 2.0s away is removed from `run_fresh.py`. The new `_accepted_cut_pair` function (L1050) is constrained to search only within the `cut_lo`/`cut_hi` ranges defined by the pause around the locked sentence, as determined by `edge_plan`. This strictly prevents adding or dropping words.
*   **ONSET/TAIL**: **COMPLIANT**. New gates G17a (`gate_g17_prepared`, L1249) and G17b (`gate_g17_output`, L1264) enforce this law. G17a checks for >= 80 ms of genuine lead-in/tail on prepared clips. The lead-in pad logic (`apply_lead_in_pad`, L1204) handles sources without sufficient lead-in. G17b verifies that rendered edge words keep >= 85% of their duration (`WORD_DURATION_RATIO_MIN`, L710).
*   **CREDITS**: **PARTIAL**. The diff does not contain the `shoutout` source code itself. However, the test in `test_pulse_20261110_mustfail.py` (L1545) is updated to assert that `validate_avatar` raises a `ValueError` with the message "square". This provides strong evidence that non-square avatars (like thumbnails) are now rejected, which would prevent warping. Assuming the test is accurate, this change is compli

## CLAUDE'S CYCLE 1 CONSENSUS
# CONSENSUS REPORT — PULSE-SENTENCE-LAW — CYCLE 1
Generated: 2026-11-11 02:42
Models: grok, gpt4o, gemini

---

## SCORES

| Subsystem | Gemini | GPT-4o | Grok | Consensus |
|---|---|---|---|---|
| Correctness | 9.5/10 | 9.0/10 | 9.5/10 | 9.3/10 |
| Law Compliance | 9.5/10 | 9.5/10 | 10/10 | 9.7/10 |
| Test Quality | 9.5/10 | 9.0/10 | 9.5/10 | 9.3/10 |
| Overall Verdict | READY | READY (minor notes) | READY | **READY** |

> **Score methodology**: Extracted from each model's Q4 verdict tone and Q1–Q3 severity language. Gemini provided the most granular analysis; Grok was the most unequivocal; GPT-4o identified the only substantive (if minor) code issues. No model issued a HOLD or requested fundamental rework.

---

## UNANIMOUS FINDINGS (all 3 models agree — implement unconditionally)

**None.** All three models agree the code is correct and law-compliant. No defect was flagged by all three models simultaneously. This is an unusually strong signal of code quality.

---

## MAJORITY FINDINGS (2 of 3 models agree)

**None.** No single issue was flagged independently by two or more models as a defect requiring a fix. The closest candidate is the `redundant import` issue raised by GPT-4o (see Unique Insights), but neither Grok nor Gemini flagged it, so it remains a minority finding.

---

## UNIQUE INSIGHTS (only 1 model caught this — evaluate carefully)

### UI-1 — Redundant `sentence_law` import inside `stage_cut`
**Model**: GPT-4o only
**Location**: `pipeline/run_fresh.py`, lines 204–275
**Observation**: GPT-4o flagged a redundant import of `sentence_law` inside the `stage_cut` function body, where it is presumably already imported at module level.
**Assessment**: **IMPLEMENT** — trivially safe, keeps the module clean, eliminates the runtime overhead of repeated `sys.modules` lookups on every call. Zero risk, positive hygiene.
**Fix**: Remove the in-function `import sentence_law` statement; confirm the module-level import covers all callers.

---

### UI-2 — Test class setup could use `setUpClass` / `tearDownClass` for temp directories
**Model**: GPT-4o only
**Location**: `test_pulse_20261110_mustfail.py`, lines 1543–1553
**Observation**: GPT-4o noted that temporary directory lifecycle management in `TestD4Credits` could be promoted to class-level setup/teardown, reducing per-test overhead and preventing orphaned temp dirs on failure.
**Assessment**: **IMPLEMENT (low priority)** — not a correctness issue, but test isolation hygiene matters for CI speed and artifact cleanliness. Use `setUpClass`/`tearDownClass` or `tempfile.TemporaryDirectory` as a context manager at class scope.
**Fix**: Refactor temp-dir creation to `setUpClass`; ensure `tearDownClass` unconditionally cleans up even on assertion errors.

---

### UI-3 — Credits / `validate_avatar` compliance is inferred, not directly verified in diff
**Model**: Gemini only
**Location**: `test_pulse_20261110_mustfail.py`, line ~1545; `shoutout` module (not in diff)
**Observation**: Gemini noted the

---

## ORIGINAL CODE (same code as Cycle 1)
## THE CODE (every new and modified file)

### File: docs/audits/pulse-sentence-law/CURRENT.diff (1558 lines)
```
   1 | diff --git a/pipeline/pinned.py b/pipeline/pinned.py
   2 | index 7f585fe3..658f2667 100644
   3 | --- a/pipeline/pinned.py
   4 | +++ b/pipeline/pinned.py
   5 | @@ -115,6 +115,10 @@ def validate_schema(pin, registry=None):
   6 |          errs.append("at least one clip required")
   7 |      if roles and roles[0] != "hook":
   8 |          errs.append("the hook must be the first segment")
   9 | +    if pin.get("machine_cuts") and not all(str(s.get("approved_text") or "").strip() for s in segs):
  10 | +        # sentence law: a machine-built PIN carries the editor's selected sentences; the words are
  11 | +        # located by text in the acquired transcript, never by window-offset arithmetic
  12 | +        errs.append("machine_cuts PIN: every segment needs approved_text (the selected sentences)")
  13 |      recs = []
  14 |      for i, s in enumerate(segs):
  15 |          tag = f"segment {i} ({s.get('role')} {s.get('video_id')})"
  16 | @@ -204,6 +208,7 @@ def acquire(pin, run_dir, log=print):
  17 |              out[vid] = {"path": path, "offset": float(offset), "transcript": tr,
  18 |                          "provenance": {"kind": "youtube_window", "window_offset_s": offset}}
  19 |          out[vid]["provenance"]["source_file_sha256"] = _sha256(out[vid]["path"])
  20 | +        out[vid]["transcript_path"] = os.path.join(run_dir, "transcripts", f"{vid}.json")
  21 |          log(f"  {vid}: acquired ({out[vid]['provenance']['kind']})")
  22 |      return out
  23 |  
  24 | @@ -230,6 +235,7 @@ def validate_range(seg, acq):
  25 |      out = {"start_file": round(start, 3), "end_file": round(end, 3), "source_duration": round(dur, 3),
  26 |             "words": inside, "text": " ".join(w["word"].strip() for w in inside),
  27 |             "first_word": inside[0]["word"].strip(), "last_word": inside[-1]["word"].strip(),
  28 | +           "i0": words.index(inside[0]), "i1": words.index(inside[-1]),
  29 |             "transcript_word_straddles_boundary": [w["word"].strip() for w in straddle],
  30 |             "edge_words_from": "transcript words entirely inside the range"}
  31 |      approved = str(seg.get("approved_text") or "").strip()
  32 | @@ -242,9 +248,14 @@ def validate_range(seg, acq):
  33 |          if ratio < APPROVED_TEXT_MIN_RATIO:
  34 |              raise PinError(f"{tag}: approved_text does not correspond to the transcript in this range "
  35 |                             f"(token similarity {ratio:.2f} < {APPROVED_TEXT_MIN_RATIO})")
  36 | -        toks = approved.split()
  37 | -        out.update(text=approved, first_word=toks[0], last_word=toks[-1], approved_text_similarity=round(ratio, 3),
  38 | -                   edge_words_from="approved_text (verified against the transcript)")
  39 | +        import sentence_law as L
  40 | +        a = L.anchor(words, approved, t0=start - 3.0, t1=end + 3.0)
  41 | +        if a is None:
  42 | +            raise PinError(f"{tag}: approved_text edges not found as words in the transcript near the range")
  43 | +        i0, i1, _ = a
  44 | +        out.update(text=approved, first_word=words[i0]["word"].strip(), last_word=words[i1]["word"].strip(),
  45 | +                   i0=i0, i1=i1, approved_text_similarity=round(ratio, 3),
  46 | +                   edge_words_from="approved_text located by text in the transcript (sentence_law.anchor)")
  47 |      return out
  48 |  
  49 |  
  50 | @@ -261,6 +272,11 @@ def build_edl(pin, acq, registry=None, log=print):
  51 |          a = acq[s["video_id"]]
  52 |          v = validate_range(s, a)
  53 |          ch = by_name[s["channel"]]
  54 | +        import sentence_law as L
  55 | +        lock = L.make_lock(s["video_id"], a["transcript"]["words"], v["i0"], v["i1"],
  56 | +                           L.sha256_file(a["transcript_path"]), v["text"], [s["start"], s["end"]],
  57 | +                           v.get("approved_text_similarity"),
  58 | +                           "pinned approved_text" if s.get("approved_text") else "pinned exact range")
  59 |          seg = {
  60 |              "video_id": s["video_id"],
  61 |              "channel": s["channel"],
  62 | @@ -269,9 +285,9 @@ def build_edl(pin, acq, registry=None, log=print):
  63 |              "text": v["text"],
  64 |              "first_word": v["first_word"],
  65 |              "last_word": v["last_word"],
  66 | -            "word_start": round(v["words"][0]["start"], 3),
  67 | -            "word_end": round(v["words"][-1]["end"], 3),
  68 | -            "duration": round(v["words"][-1]["end"] - v["words"][0]["start"], 2),
  69 | +            "word_start": round(a["transcript"]["words"][v["i0"]]["start"], 3),
  70 | +            "word_end": round(a["transcript"]["words"][v["i1"]]["end"], 3),
  71 | +            "duration": round(a["transcript"]["words"][v["i1"]]["end"] - a["transcript"]["words"][v["i0"]]["start"], 2),
  72 |              "time_coords": "source_file",
  73 |              "source_window_offset_s": round(a["offset"], 3),
  74 |              # the human decision, exact; the cut table is taken from here, never recomputed
  75 | @@ -279,6 +295,7 @@ def build_edl(pin, acq, registry=None, log=print):
  76 |                         "input_end": s["end"], "input_time_coords": s["time_coords"]},
  77 |              "cut_out": v["end_file"],
  78 |              "fade_out_ms": FADE_OUT_MS,
  79 | +            "selection_lock": lock,
  80 |          }
  81 |          segs.append(seg)
  82 |          report.append({"role": s["role"], "video_id": s["video_id"], "channel": s["channel"],
  83 | diff --git a/pipeline/run_fresh.py b/pipeline/run_fresh.py
  84 | index 4bc7f7de..74bbbcd2 100644
  85 | --- a/pipeline/run_fresh.py
  86 | +++ b/pipeline/run_fresh.py
  87 | @@ -14,9 +14,12 @@ Stages (any failure = HOLD; nothing is ever published; telegram is never importe
  88 |                 writes TOPIC_SELECTION.json + passages.json (the select stage's input contract)
  89 |    2 select     existing select_passages.select_and_build_edl            (unchanged from here on)
  90 |    3 validate   existing edl_rules.validate_edl + layout compatibility (all channels approved, all 'crop')
  91 | -  4 cut        existing cut.compute_all_cuts, then cut acceptance (cut_accept.py)
  92 | +  4 cut        cuts placed inside the pauses bounding each LOCKED sentence (sentence_law.py; human
  93 | +               PINs: the exact pinned table), then cut acceptance (cut_accept.py); no snapping
  94 | +  4b sentence_law  G16 SENTENCE_BOUNDARY before rendering (hard stop)
  95 |    5 voice      existing vo.generate_vo (same voice/model as v2f, asserted)
  96 |    6 prepare    run_isolated.prerender_clips, clip contract (clip_contract.py), Law 14c edge words
  97 | +               (expected words = the selection lock, never recomputed)
  98 |    7 render     shout-out 16x9+9x16, preflight, render 16:9, postflight, render 9:16, postflight,
  99 |                 vertical silent-fallback detection
 100 |    8 gates      run_gates both formats exactly as v2f, plus G11 (real), G14 both, G14c, G15 both,
 101 | @@ -362,121 +365,28 @@ def stage_validate(run):
 102 |              raise Hold(f"{l} EDL times not in source-file coordinates")
 103 |  
 104 |  
 105 | -# ── helpers: edge-word recomputation from word-timestamp transcript ──
 106 | -
 107 | -def _recompute_edge_words(transcript_path, cut_in, cut_out):
 108 | -    """Look up first/last words from a word-timestamp transcript at given cut times.
 109 | -
 110 | -    Returns (first_word, last_word). If no transcript or no words found,
 111 | -    returns ("", "") and logs a warning.
 112 | -    """
 113 | -    if not os.path.isfile(transcript_path):
 114 | -        print(f"    WARN: no transcript at {transcript_path} — edge words unavailable")
 115 | -        return "", ""
 116 | -    with open(transcript_path) as f:
 117 | -        t = json.load(f)
 118 | -    words = t.get("words", [])
 119 | -    if not words:
 120 | -        print(f"    WARN: empty word list in {transcript_path} — edge words unavailable")
 121 | -        return "", ""
 122 | -    first, last = "", ""
 123 | -    for w in words:
 124 | -        if w["end"] > cut_in + 0.05:
 125 | -            first = w["word"]
 126 | -            break
 127 | -    for w in words:
 128 | -        # Last word = latest word fully contained in the cut window.
 129 | -        # Whisper on the rendered clip reports the last COMPLETE word it can
 130 | -        # recognise; partially cut words are often dropped or garbled.
 131 | -        # Use end <= cut_out (the word finishes before the cut point).
 132 | -        if w["start"] >= cut_in - 0.5 and w["end"] <= cut_out:
 133 | -            last = w["word"]
 134 | -    return first, last
 135 | -
 136 | -
 137 | -def _sync_edl_edge_words(run_dir, cuts):
 138 | -    """Update edl.json first_word/last_word to match cuts_final after snapping."""
 139 | -    edl_path = os.path.join(run_dir, "edl.json")
 140 | -    if not os.path.isfile(edl_path):
 141 | -        return
 142 | -    with open(edl_path) as f:
 143 | -        edl = json.load(f)
 144 | -    lookup = {c["clip_id"]: c for c in cuts}
 145 | -    # Update hook
 146 | -    if "hook" in lookup and "hook" in edl:
 147 | -        edl["hook"]["first_word"] = lookup["hook"].get("first_word_expected", edl["hook"].get("first_word", ""))
 148 | -        edl["hook"]["last_word"] = lookup["hook"].get("last_word_expected", edl["hook"].get("last_word", ""))
 149 | -    # Update clips
 150 | -    synced = 0
 151 | -    for i, clip in enumerate(edl.get("clips", [])):
 152 | -        cid = f"clip_{i + 1:02d}"
 153 | -        if cid in lookup:
 154 | -            clip["first_word"] = lookup[cid].get("first_word_expected", clip.get("first_word", ""))
 155 | -            clip["last_word"] = lookup[cid].get("last_word_expected", clip.get("last_word", ""))
 156 | -            synced += 1
 157 | -        else:
 158 | -            print(f"    WARN: EDL clip index {i} ({cid}) not in cuts_final — edge words not synced")
 159 | -    jdump(edl_path, edl)
 160 | -
 161 | -
 162 |  # ── stage 6: cut + acceptance ──
 163 |  
 164 | -def _snap_candidates(src, cut_in, cut_out, dur, check_fn, max_shift=2.0, step=0.02):
 165 | -    """Yield ALL (cut_in, cut_out, details) tuples that pass check_fn.
 166 | -
 167 | -    Phase 1: collect all cut_out positions that pass the OUT check (bidirectional,
 168 | -    nearest-first).  Phase 2: for each accepted OUT, find a cut_in that passes IN.
 169 | -    Yields results nearest-first so the caller can stop at the first that also
 170 | -    satisfies the clip contract.
 171 | -    """
 172 | -    n = int(max_shift / step)
 173 | -    offsets = [0]
 174 | -    for i in range(1, n + 1):
 175 | -        offsets.append(-i * step)
 176 | -        offsets.append(i * step)
 177 | -    # Phase 1: collect all OUT-passing positions (nearest-first order preserved)
 178 | -    accepted_outs = []
 179 | -    for delta_out in offsets:
 180 | -        trial_out = round(cut_out + delta_out, 3)
 181 | -        if trial_out <= cut_in + 1.0 or trial_out > dur:
 182 | -            continue
 183 | -        ok, d = check_fn(src, cut_in, trial_out)
 184 | -        if d.get("out", {}).get("pass"):
 185 | -            accepted_outs.append((trial_out, delta_out, ok, d))
 186 | -    # Phase 2: for each accepted OUT, fix cut_in and yield
 187 | -    for trial_out, delta_out, full_ok, d_out in accepted_outs:
 188 | -        if full_ok:
 189 | -            yield (cut_in, trial_out,
 190 | -                   {**d_out, "snapped_out_by": round(delta_out, 3)})
 191 | -        else:
 192 | -            for delta_in in offsets:
 193 | -                trial_in = round(cut_in + delta_in, 3)
 194 | -                if trial_in < 0 or trial_in >= trial_out - 1.0:
 195 | -                    continue
 196 | -                ok, d = check_fn(src, trial_in, trial_out)
 197 | -                if ok:
 198 | -                    yield (trial_in, trial_out,
 199 | -                           {**d, "snapped_in_by": round(delta_in, 3),
 200 | -                            "snapped_out_by": round(delta_out, 3)})
 201 | -                    break  # one IN solution per OUT is enough
 202 | -
 203 | -
 204 |  def stage_cut(run):
 205 | -    import itertools
 206 | -    from cut import compute_all_cuts
 207 | +    """Human PINs: the exact pinned table. Everything else: cuts placed inside the pauses that bound
 208 | +    each LOCKED sentence (sentence_law.write_lock_cut_table) -- a cut never moves outside that
 209 | +    silence and never adds or drops a word (2026-11-11: the +-2 s snap and the edge-word recompute of
 210 | +    ad7295ea/4cf5a31a are gone). The SAME acceptance check runs on every cut; a rejection HOLDs."""
 211 |      from cut_accept import check_cut_acoustics
 212 | -    # Human-approved PINs use exact pinned ranges (no acoustic cutter, no snapping).
 213 | -    # Machine-built PINs (machine_cuts=true) use the acoustic cutter + snapping.
 214 |      use_pinned_table = (run.mode == "pinned" and not run.machine_cuts)
 215 |      if use_pinned_table:
 216 |          from pinned import write_pinned_cut_table
 217 |          write_pinned_cut_table(run.dir)
 218 | -    elif compute_all_cuts(run.dir) is not True:
 219 | -        raise Hold("compute_all_cuts did not succeed")
 220 | +    else:
 221 | +        import sentence_law as L
 222 | +        adj = L.Adjudicator()
 223 | +        try:
 224 | +            L.write_lock_cut_table(run.dir, adj)
 225 | +        finally:
 226 | +            adj.close()
 227 |      with open(os.path.join(run.dir, "cuts_final.json")) as f:
 228 |          cuts = json.load(f)
 229 |      report, fails = [], []
 230 | -    snap_alternatives = {}  # clip_id -> list of remaining (in, out, d) candidates
 231 |      for c in cuts:
 232 |          src = os.path.join(run.dir, "sources", f"{c['video_id']}.mp4")
 233 |          rec = {"clip_id": c["clip_id"], "video_id": c["video_id"], "cut_in": c.get("cut_in"),
 234 | @@ -492,28 +402,6 @@ def stage_cut(run):
 235 |                  rec["reason"] = f"cut range outside source file (duration {dur:.2f})"
 236 |              else:
 237 |                  ok, d = check_cut_acoustics(src, c["cut_in"], c["cut_out"])
 238 | -                if not ok and not use_pinned_table:
 239 | -                    it = _snap_candidates(
 240 | -                        src, c["cut_in"], c["cut_out"], dur, check_cut_acoustics)
 241 | -                    first = next(it, None)
 242 | -                    if first:
 243 | -                        new_in, new_out, d2 = first
 244 | -                        print(f"    snap: {c['cut_in']:.3f}-{c['cut_out']:.3f} -> "
 245 | -                              f"{new_in:.3f}-{new_out:.3f}")
 246 | -                        c["cut_in"], c["cut_out"] = new_in, new_out
 247 | -                        c["cut_duration"] = round(new_out - new_in, 3)
 248 | -                        c["snapped"] = True
 249 | -                        ok, d = True, d2
 250 | -                        # Store up to 20 remaining candidates for contract retry
 251 | -                        remaining = list(itertools.islice(it, 20))
 252 | -                        if remaining:
 253 | -                            snap_alternatives[c["clip_id"]] = remaining
 254 | -                        # Recompute edge words from word-timestamp transcript
 255 | -                        tx = os.path.join(run.dir, "transcripts", f"{c['video_id']}.json")
 256 | -                        fw, lw = _recompute_edge_words(tx, new_in, new_out)
 257 | -                        c["first_word_expected"] = fw
 258 | -                        c["last_word_expected"] = lw
 259 | -                        print(f"    edge words recomputed: first='{fw}' last='{lw}'")
 260 |                  rec.update(pass_=ok, **d)
 261 |                  rec["pass"] = rec.pop("pass_")
 262 |          if not rec["pass"]:
 263 | @@ -521,14 +409,30 @@ def stage_cut(run):
 264 |          report.append(rec)
 265 |          print(f"  {c['clip_id']}: in={c.get('cut_in')} out={c.get('cut_out')} "
 266 |                f"[{'ACCEPT' if rec['pass'] else 'REJECT'}] {rec.get('reason', '')}")
 267 | -    # Write the (possibly snapped) cuts back
 268 | -    jdump(os.path.join(run.dir, "cuts_final.json"), cuts)
 269 | -    _sync_edl_edge_words(run.dir, cuts)
 270 |      run.prov["cut_acceptance"] = report
 271 |      jdump(os.path.join(run.dir, "CUT_ACCEPTANCE.json"), report)
 272 |      if fails:
 273 |          raise Hold(f"cut acceptance rejected {fails} (see CUT_ACCEPTANCE.json)")
 274 | -    return cuts, snap_alternatives
 275 | +    return cuts
 276 | +
 277 | +
 278 | +def stage_sentence_law(run):
 279 | +    """G16 SENTENCE_BOUNDARY before anything is rendered: every cut holds exactly its locked
 280 | +    sentence(s), both edges are legal sentence boundaries and the cuts sit inside those pauses."""
 281 | +    import sentence_law as L
 282 | +    adj = L.Adjudicator()
 283 | +    try:
 284 | +        ok, table = L.gate_g16(run.dir, adj)
 285 | +    finally:
 286 | +        adj.close()
 287 | +    run.prov["G16_pre_render"] = table
 288 | +    jdump(os.path.join(run.dir, "SENTENCE_LAW.json"), {"pass": ok, "segments": table})
 289 | +    for r in table:
 290 | +        print(f"  {r['segment']}: {r.get('locked', '')} [{'PASS' if r['pass'] else 'FAIL'}] "
 291 | +              + "; ".join(r["errors"]))
 292 | +    if not ok:
 293 | +        raise Hold("G16 sentence law: " + "; ".join(
 294 | +            f"{r['segment']}: {', '.join(r['errors'])}" for r in table if not r["pass"]))
 295 |  
 296 |  
 297 |  # ── stage 7: voice ──
 298 | @@ -563,61 +467,30 @@ def stage_voice(run):
 299 |  
 300 |  # ── stage 8: prepare clips + contract + edge words ──
 301 |  
 302 | -def stage_prepare(run, cuts, snap_alternatives=None):
 303 | +def stage_prepare(run, cuts):
 304 |      from run_isolated import prerender_clips
 305 |      from clip_contract import check_clip
 306 |      from cut_accept import check_edge_words
 307 | -    snap_alternatives = snap_alternatives or {}
 308 | +    import sentence_law as L
 309 | +    from config import FPS, NVENC_QP_INTERMEDIATE
 310 |      prerender_clips(run.dir, cuts)
 311 | +    pads = {}
 312 | +    for c in cuts:
 313 | +        if float(c.get("lead_in_pad_s") or 0) > 0:
 314 | +            # D1: a file-head sentence without 80 ms of genuine lead-in gets the declared room-tone pad
 315 | +            pads[c["clip_id"]] = L.apply_lead_in_pad(run.dir, c, FPS, NVENC_QP_INTERMEDIATE)
 316 | +            print(f"  {c['clip_id']}: lead-in pad {pads[c['clip_id']]}")
 317 | +    run.prov["lead_in_pads"] = pads
 318 |      qa = os.path.join(run.dir, "qa")
 319 |      work = os.path.join(qa, "edge_words")
 320 |      os.makedirs(work, exist_ok=True)
 321 |      report, fails = [], []
 322 |      for c in cuts:
 323 |          clip = os.path.join(qa, f"final_{c['clip_id']}.mp4")
 324 | -        ok1, d1 = check_clip(clip, c["cut_duration"])
 325 | +        ok1, d1 = check_clip(clip, c["cut_duration"] + float(c.get("lead_in_pad_s") or 0))
 326 | +        # expected words come from the selection lock (cuts_final), never from the cut position
 327 |          ok2, d2 = check_edge_words(clip, c.get("first_word_expected", ""),
 328 |                                     c.get("last_word_expected", ""), work, c["clip_id"])
 329 | -        # If contract fails on a snapped clip, try alternative snap candidates
 330 | -        if not ok1 and c.get("snapped") and c["clip_id"] in snap_alternatives:
 331 | -            alts = snap_alternatives[c["clip_id"]]
 332 | -            # Save original values to restore on total failure
 333 | -            orig_in, orig_out = c["cut_in"], c["cut_out"]
 334 | -            orig_dur = c["cut_duration"]
 335 | -            orig_fw = c.get("first_word_expected", "")
 336 | -            orig_lw = c.get("last_word_expected", "")
 337 | -            print(f"  {c['clip_id']}: contract FAIL at {c['cut_in']:.3f}-{c['cut_out']:.3f}, "
 338 | -                  f"trying {len(alts)} alternative snap positions...")
 339 | -            found = False
 340 | -            for alt_in, alt_out, alt_d in alts:
 341 | -                c["cut_in"], c["cut_out"] = alt_in, alt_out
 342 | -                c["cut_duration"] = round(alt_out - alt_in, 3)
 343 | -                tx = os.path.join(run.dir, "transcripts", f"{c['video_id']}.json")
 344 | -                fw, lw = _recompute_edge_words(tx, alt_in, alt_out)
 345 | -                c["first_word_expected"], c["last_word_expected"] = fw, lw
 346 | -                prerender_clips(run.dir, [c])
 347 | -                ok1, d1 = check_clip(clip, c["cut_duration"])
 348 | -                ok2, d2 = check_edge_words(clip, fw, lw, work, c["clip_id"])
 349 | -                print(f"    retry snap {alt_in:.3f}-{alt_out:.3f}: "
 350 | -                      f"contract {'PASS' if ok1 else 'FAIL'} edges {'PASS' if ok2 else 'FAIL'}")
 351 | -                if ok1 and ok2:
 352 | -                    print(f"    snap: -> {alt_in:.3f}-{alt_out:.3f} "
 353 | -                          f"(edge words: '{fw}'/'{lw}')")
 354 | -                    found = True
 355 | -                    break
 356 | -            if found:
 357 | -                jdump(os.path.join(run.dir, "cuts_final.json"), cuts)
 358 | -                _sync_edl_edge_words(run.dir, cuts)
 359 | -            else:
 360 | -                # Restore original values — no alternative passed
 361 | -                c["cut_in"], c["cut_out"] = orig_in, orig_out
 362 | -                c["cut_duration"] = orig_dur
 363 | -                c["first_word_expected"] = orig_fw
 364 | -                c["last_word_expected"] = orig_lw
 365 | -                # Re-render at original position for consistent state
 366 | -                prerender_clips(run.dir, [c])
 367 | -                ok1, d1 = check_clip(clip, c["cut_duration"])
 368 | -                ok2, d2 = check_edge_words(clip, orig_fw, orig_lw, work, c["clip_id"])
 369 |          rec = {"clip_id": c["clip_id"], "sha256": sha256(clip), "contract": d1,
 370 |                 "contract_pass": ok1, "edge_words": d2, "edge_words_pass": ok2}
 371 |          report.append(rec)
 372 | @@ -625,8 +498,7 @@ def stage_prepare(run, cuts, snap_alternatives=None):
 373 |              fails.append(c["clip_id"])
 374 |          print(f"  {c['clip_id']}: contract {'PASS' if ok1 else 'FAIL'} {d1.get('errors')} | "
 375 |                f"edges first '{d2['heard_first']}'/'{d2['expected_first']}' "
 376 | -              f"last '{d2['heard_last']}'/'{d2['expected_last']}' "
 377 | -              f"{'PASS' if ok2 else 'FAIL'}{' (snapped)' if c.get('snapped') else ''}")
 378 | +              f"last '{d2['heard_last']}'/'{d2['expected_last']}' {'PASS' if ok2 else 'FAIL'}")
 379 |      run.prov["prepared_clips"] = report
 380 |      jdump(os.path.join(run.dir, "CLIP_CONTRACT.json"), report)
 381 |      if fails:
 382 | @@ -742,14 +614,27 @@ def stage_gates(run, final16, man16, final9, man9):
 383 |      g14dir9 = os.path.join(qa, "g14_9x16")
 384 |      os.makedirs(g14dir16, exist_ok=True)
 385 |      os.makedirs(g14dir9, exist_ok=True)
 386 | -    g14_16_ok, g14_16 = G.gate_g14(final16, man16, source_clips=src_clips, qa_dir=g14dir16)
 387 | +    # a declared lead-in pad is room tone, not source material: G14 measures from the pad's end
 388 | +    pads = {c["clip_id"]: float(c.get("lead_in_pad_s") or 0) for c in cuts}
 389 | +
 390 | +    def _g14_manifest(man, tag):
 391 | +        with open(man) as f:
 392 | +            m = json.load(f)
 393 | +        for sg in m["segments"]:
 394 | +            if sg.get("type") == "talking_head" and pads.get(sg["label"]):
 395 | +                sg["start"] = round(sg["start"] + pads[sg["label"]], 3)
 396 | +        path = os.path.join(qa, f"g14_manifest_{tag}.json")
 397 | +        jdump(path, m)
 398 | +        return path
 399 | +    man16_g14, man9_g14 = _g14_manifest(man16, "16x9"), _g14_manifest(man9, "9x16")
 400 | +    g14_16_ok, g14_16 = G.gate_g14(final16, man16_g14, source_clips=src_clips, qa_dir=g14dir16)
 401 |      fails16 = [d for d in g14_16 if d.get("status") == "FAIL"]
 402 |      rows["16x9"]["G14_av_alignment"] = ("PASS" if g14_16_ok else
 403 |                                          "FAIL" if fails16 else "HOLD(inconclusive)")
 404 |      limits["16x9"].append("G14: static talking-head temporal slips can pass frame_sim "
 405 |                            "(v2e 18.0-24.0 s precedent); VO sections are auto-PASS (pre-roll "
 406 |                            "declared), plate correctness not verified")
 407 | -    g14_9_ok, g14_9 = G.gate_g14(final9, man9, source_clips=src_clips, qa_dir=g14dir9)
 408 | +    g14_9_ok, g14_9 = G.gate_g14(final9, man9_g14, source_clips=src_clips, qa_dir=g14dir9)
 409 |      # audio part: the gate's own conclusive xcorr measurement (peak >= 0.3) and 40 ms tolerance
 410 |      audio_bad = [d for d in g14_9 if d.get("delta_ms") is not None and d["delta_ms"] > 40]
 411 |      inconclusive9 = [d for d in g14_9 if d.get("status") == "HOLD" and d.get("delta_ms") is None]
 412 | @@ -813,13 +698,32 @@ def stage_gates(run, final16, man16, final9, man9):
 413 |          else:
 414 |              rows[fmt]["G9_tail"] = "FAIL"
 415 |  
 416 | +    # G16 SENTENCE_BOUNDARY: re-run on the final cut state (format-independent; same row in both)
 417 | +    import sentence_law as L
 418 | +    adj = L.Adjudicator()
 419 | +    try:
 420 | +        g16_ok, g16 = L.gate_g16(run.dir, adj)
 421 | +    finally:
 422 | +        adj.close()
 423 | +    for fmt in ("16x9", "9x16"):
 424 | +        rows[fmt]["G16_sentence_boundary"] = _status(g16_ok)
 425 | +
 426 | +    # G17 ONSET/TAIL: prepared clips (>= 80 ms genuine lead-in/tail) + each final (edge words >= 85 %)
 427 | +    g17a_ok, g17a = L.gate_g17_prepared({c["clip_id"]: os.path.join(qa, f"final_{c['clip_id']}.mp4")
 428 | +                                          for c in cuts})
 429 | +    g17b16_ok, g17b16 = L.gate_g17_output(final16, segs16, cuts, run.dir)
 430 | +    g17b9_ok, g17b9 = L.gate_g17_output(final9, segs9, cuts, run.dir)
 431 | +    rows["16x9"]["G17_onset_tail"] = _status(g17a_ok and g17b16_ok)
 432 | +    rows["9x16"]["G17_onset_tail"] = _status(g17a_ok and g17b9_ok)
 433 | +
 434 |      fb = run.prov["vertical_fallback_check"]
 435 |      rows["9x16"]["vertical_silent_fallback"] = "FAIL (fallback occurred)" if fb["fallback_occurred"] \
 436 |          else "PASS (no fallback)"
 437 |  
 438 |      gates_out = {"rows": rows, "flags": flags, "limitations": limits,
 439 |                   "G11": g11, "G14_16x9": g14_16, "G14_9x16": g14_9, "G14c": g14c,
 440 | -                 "G15_16x9": g15_16, "G15_9x16": g15_9, "G8": g8_report, "G9": g9_report,
 441 | +                 "G15_16x9": g15_16, "G15_9x16": g15_9, "G8": g8_report, "G9": g9_report, "G16": g16,
 442 | +                 "G17": {"prepared": g17a, "16x9": g17b16, "9x16": g17b9},
 443 |                   "run_gates_overall": {"16x9": ok16, "9x16": ok9}}
 444 |      jdump(os.path.join(run.dir, "GATE_REPORT.json"), gates_out)
 445 |      run.prov["gates"] = {"rows": rows, "flags": flags, "limitations": limits}
 446 | @@ -1002,9 +906,10 @@ def main():
 447 |              run.stage("select", lambda: stage_select(run, keyword))
 448 |          run.stage("review", lambda: stage_review(run))
 449 |          run.stage("validate", lambda: stage_validate(run))
 450 | -        cuts, snap_alts = run.stage("cut", lambda: stage_cut(run))
 451 | +        cuts = run.stage("cut", lambda: stage_cut(run))
 452 | +        run.stage("sentence_law", lambda: stage_sentence_law(run))
 453 |          run.stage("voice", lambda: stage_voice(run))
 454 | -        run.stage("prepare", lambda: stage_prepare(run, cuts, snap_alts))
 455 | +        run.stage("prepare", lambda: stage_prepare(run, cuts))
 456 |          final16, man16, final9, man9 = run.stage("render", lambda: stage_render(run))
 457 |          rows, flags, limits = run.stage("gates", lambda: stage_gates(run, final16, man16,
 458 |                                                                        final9, man9))
 459 | diff --git a/pipeline/select_passages.py b/pipeline/select_passages.py
 460 | index 730a46e1..752a8032 100644
 461 | --- a/pipeline/select_passages.py
 462 | +++ b/pipeline/select_passages.py
 463 | @@ -31,7 +31,11 @@ def _download_window(video_id, start_s, end_s, run_dir, pad=15.0):
 464 |      os.makedirs(sources_dir, exist_ok=True)
 465 |  
 466 |      out_path = os.path.join(sources_dir, f"{video_id}.mp4")
 467 | -    dl_start = max(0, start_s - pad)
 468 | +    # The section start actually requested from yt-dlp (whole seconds) IS the recorded offset
 469 | +    # (2026-11-11: '*54-100' was requested while 53.57 was recorded). Keyframe/priming can still
 470 | +    # move the file start by ~0.1 s, so cut words are located by text (sentence_law.anchor), never
 471 | +    # by offset arithmetic; the offset is provenance only.
 472 | +    dl_start = float(round(max(0, start_s - pad)))
 473 |  
 474 |      if os.path.exists(out_path) and os.path.getsize(out_path) > 100_000:
 475 |          return out_path, dl_start  # Cache hit
 476 | @@ -105,55 +109,6 @@ def _whisper_transcribe(source_path, video_id, run_dir):
 477 |          return None
 478 |  
 479 |  
 480 | -def _find_word_boundaries(words, start_s, end_s, text_hint=None, min_dur=8.0):
 481 | -    """Find the best first_word and last_word within a passage time range.
 482 | -
 483 | -    Widens the search window to ensure clips meet min_dur.
 484 | -    Returns (first_word, last_word, word_start, word_end) or None.
 485 | -    """
 486 | -    # Widen search window: use a generous margin around the passage
 487 | -    margin = 3.0
 488 | -    window_words = [w for w in words
 489 | -                    if w["start"] >= start_s - margin and w["end"] <= end_s + margin]
 490 | -    if not window_words:
 491 | -        # Try even wider — use ALL words
 492 | -        window_words = words
 493 | -    if not window_words:
 494 | -        return None
 495 | -
 496 | -    # First word: closest to start_s, but must be a sentence start if possible
 497 | -    # Look for words near start_s that begin a sentence (after a period)
 498 | -    first = min(window_words, key=lambda w: abs(w["start"] - start_s))
 499 | -
 500 | -    # Last word: find sentence-ending word that gives us >= min_dur
 501 | -    min_end_time = first["start"] + min_dur
 502 | -    sentence_enders = [w for w in window_words
 503 | -                       if w["word"].rstrip().endswith((".", "!", "?"))
 504 | -                       and w["end"] >= min_end_time
 505 | -                       and w["end"] <= end_s + margin]
 506 | -    if sentence_enders:
 507 | -        # Pick the one closest to end_s
 508 | -        last = min(sentence_enders, key=lambda w: abs(w["end"] - end_s))
 509 | -    else:
 510 | -        # No sentence ender meeting min_dur: pick the latest word in range
 511 | -        candidates = [w for w in window_words if w["end"] >= min_end_time]
 512 | -        if candidates:
 513 | -            last = max(candidates, key=lambda w: w["end"])
 514 | -        else:
 515 | -            last = max(window_words, key=lambda w: w["end"])
 516 | -
 517 | -    # Verify minimum duration
 518 | -    dur = last["end"] - first["start"]
 519 | -    if dur < min_dur and len(window_words) > 5:
 520 | -        # Expand: take first word and the last sentence ender that gives >= min_dur
 521 | -        all_enders = [w for w in words if w["word"].rstrip().endswith((".", "!", "?"))
 522 | -                      and w["end"] >= first["start"] + min_dur]
 523 | -        if all_enders:
 524 | -            last = min(all_enders, key=lambda w: w["end"])
 525 | -
 526 | -    return first["word"], last["word"], first["start"], last["end"]
 527 | -
 528 | -
 529 |  def _generate_vo_script(keyword, hook_text, clips, channels):
 530 |      """Generate the default body-VO shape under M20 / Editorial Law 2.
 531 |  
 532 | @@ -259,57 +214,79 @@ def select_and_build_edl(keyword, niche, run_dir):
 533 |      hook = max(hook_candidates, key=lambda p: p["score"]) if hook_candidates else valid[0]
 534 |      clips = [p for p in valid if p is not hook][:5]  # Max 5 clips
 535 |  
 536 | -    # Build word boundaries from transcripts
 537 | +    # SENTENCE LAW (sentence_law.py): the editor's chosen sentences are located in the downloaded
 538 | +    # file's own transcript by TEXT, sealed in a selection lock, and both edges must be legal,
 539 | +    # cuttable sentence boundaries in this file's audio. Nothing is ever picked by nearest word.
 540 | +    import sentence_law as L
 541 |      channels_used = set()
 542 | +    boundary_report = []
 543 | +    adj = L.Adjudicator()
 544 |  
 545 |      def _build_segment(passage, label):
 546 |          vid = passage["video_id"]
 547 |          words = transcripts[vid].get("words", [])
 548 |          offset = offsets.get(vid, 0)
 549 | -        # Passage times are in full-video coords; whisper times are in local (downloaded) coords
 550 | -        # local_time = full_video_time - offset
 551 | -        local_start = passage["start"] - offset
 552 | -        local_end = passage["end"] - offset
 553 | -        bounds = _find_word_boundaries(words, local_start, local_end)
 554 | -        if bounds is None:
 555 | +        tpath = os.path.join(run_dir, "transcripts", f"{vid}.json")
 556 | +        rec = {"segment": label, "video_id": vid, "channel": passage["channel"],
 557 | +               "window_full_video_s": [passage["start"], passage["end"]], "selected_text": passage["text"]}
 558 | +        boundary_report.append(rec)
 559 | +        a = L.anchor(words, passage["text"], t0=passage["start"] - offset - 5.0,
 560 | +                     t1=passage["end"] - offset + 5.0)
 561 | +        if a is None:
 562 | +            rec["result"] = "rejected: selected text not found in this file's transcript"
 563 | +            return None
 564 | +        i0, i1, ratio = a
 565 | +        lock = L.make_lock(vid, words, i0, i1, L.sha256_file(tpath), passage["text"],
 566 | +                           [passage["start"], passage["end"]], ratio, "select_passages")
 567 | +        plan = L.edge_plan(L.SourceAudio(sources[vid]), words, i0, i1, adj, context=f"select {label}")
 568 | +        rec.update(locked=f"'{lock['first_word']}' ... '{lock['last_word']}'", align_ratio=ratio,
 569 | +                   **{f"{s}_edge": {k: plan[s].get(k) for k in ("valid", "cuttable", "pause", "lexical", "reason",
 570 | +                                                                 "cut_lo", "cut_hi", "lead_in_pad_s")}
 571 | +                      for s in ("in", "out")})
 572 | +        if not plan["ok"]:
 573 | +            rec["result"] = "rejected: " + "; ".join(
 574 | +                f"{s.upper()} {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
 575 | +                if not plan[s].get("cuttable"))
 576 |              return None
 577 | -        first_word, last_word, word_start, word_end = bounds
 578 | -        # EDL times stay in SOURCE-FILE coordinates (the downloaded window):
 579 | -        # cut.py and the clip pre-render seek into sources/<vid>.mp4, and the
 580 | -        # whisper words are measured on that same file. The window offset is
 581 | -        # recorded for provenance only (fresh-topic generalization B).
 582 | -        word_start_abs = word_start
 583 | -        word_end_abs = word_end
 584 | +        rec["result"] = "accepted"
 585 |          channels_used.add(passage["channel"])
 586 | +        # EDL times are SOURCE-FILE coordinates (sources/<vid>.mp4); the offset is provenance only.
 587 |          return {
 588 |              "video_id": vid,
 589 |              "channel": passage["channel"],
 590 |              "handle": passage.get("handle", ""),
 591 |              "video_title": passage.get("title", ""),
 592 |              "text": passage["text"],
 593 | -            "first_word": first_word,
 594 | -            "last_word": last_word,
 595 | -            "word_start": round(word_start_abs, 3),
 596 | -            "word_end": round(word_end_abs, 3),
 597 | -            "duration": round(word_end - word_start, 2),
 598 | +            "first_word": lock["first_word"],
 599 | +            "last_word": lock["last_word"],
 600 | +            "word_start": round(words[i0]["start"], 3),
 601 | +            "word_end": round(words[i1]["end"], 3),
 602 | +            "duration": round(words[i1]["end"] - words[i0]["start"], 2),
 603 |              "time_coords": "source_file",
 604 |              "source_window_offset_s": round(offset, 3),
 605 | +            "selection_lock": lock,
 606 |          }
 607 |  
 608 | -    hook_seg = _build_segment(hook, "hook")
 609 | +    try:
 610 | +        hook_seg = _build_segment(hook, "hook")
 611 | +        clip_segs = []
 612 | +        if hook_seg is not None:
 613 | +            for i, clip in enumerate(clips):
 614 | +                seg = _build_segment(clip, f"clip_{i+1:02d}")
 615 | +                if seg:
 616 | +                    seg["index"] = len(clip_segs) + 1
 617 | +                    clip_segs.append(seg)
 618 | +    finally:
 619 | +        adj.close()
 620 | +        with open(os.path.join(run_dir, "SELECT_BOUNDARIES.json"), "w") as f:
 621 | +            json.dump(boundary_report, f, indent=2)
 622 | +    for r in boundary_report:
 623 | +        print(f"    {r['segment']} {r['channel']}: {r['result']}")
 624 |      if hook_seg is None:
 625 | -        print("  Cannot build hook segment — STOP")
 626 | +        print("  Cannot build hook segment (sentence law) — STOP")
 627 |          return False
 628 | -
 629 | -    clip_segs = []
 630 | -    for i, clip in enumerate(clips):
 631 | -        seg = _build_segment(clip, f"clip_{i+1:02d}")
 632 | -        if seg:
 633 | -            seg["index"] = i + 1
 634 | -            clip_segs.append(seg)
 635 | -
 636 |      if len(clip_segs) < 1:
 637 | -        print("  No valid clip segments — STOP")
 638 | +        print("  No valid clip segments (sentence law) — STOP")
 639 |          return False
 640 |  
 641 |      # Generate VO script (M20 rules)
 642 | diff --git a/pipeline/sentence_law.py b/pipeline/sentence_law.py
 643 | new file mode 100644
 644 | index 00000000..755dee49
 645 | --- /dev/null
 646 | +++ b/pipeline/sentence_law.py
 647 | @@ -0,0 +1,662 @@
 648 | +#!/usr/bin/env python3
 649 | +"""pipeline/sentence_law.py — PBX SENTENCE-BOUNDARY LAW (Nov 5 2026; hardened Nov 11 2026, D1-D3).
 650 | +
 651 | +A clip starts on the first word of a sentence and ends on the last word of a sentence, and both
 652 | +cut points sit in the silence between that sentence and its neighbour. The words a clip must
 653 | +contain are fixed at SELECTION time (the "selection lock") and are never recomputed from a moved
 654 | +cut (the D2 tautology of ad7295ea/4cf5a31a).
 655 | +
 656 | +BOUNDARY RULE (law constants, stated once, used by selection, cutting and gate G16):
 657 | +  A sentence boundary exists between transcript word k and word k+1 iff BOTH
 658 | +  (L) LEXICAL   punctuated transcript: word k ends in '.', '!' or '?' and is not an abbreviation
 659 | +                (U.S., Mr., a.m., ...) or a trailing '...';
 660 | +                unpunctuated transcript (fewer than 1 terminal mark per 60 words within +-60 words):
 661 | +                a local-model adjudication says the sentence ends after word k (content-addressed
 662 | +                cache data/editorial/sentence_adjudication.json, every decision logged).
 663 | +  (A) ACOUSTIC  the source audio holds a PAUSE between them: a run of >= PAUSE_MIN_S (80 ms, Law
 664 | +                14c) of 10 ms RMS frames below the QUIET LINE, inside [start(k), end(k+1)] (whisper
 665 | +                word edges are estimates and collapse at sentence boundaries, Law 14/14c, so the
 666 | +                search spans both words; the longest run wins).
 667 | +                QUIET LINE = min(speech - 12 dB (M19a), max(speech - 25 dB (cut_accept), bed + 6 dB
 668 | +                (M19/G3c))); speech = median of frames above the 30th percentile, bed = 10th
 669 | +                percentile (noise-floor estimate) of non-digital-silence frames, both over
 670 | +                [start(k) - 3 s, end(k+1) + 3 s]. Every cut must ALSO pass cut_accept unchanged.
 671 | +CUTTABLE EDGES (G17 + M19):
 672 | +  IN   cut_in inside the pause before the first word with >= LEAD_MIN_S (80 ms) of it kept.
 673 | +       File head (first transcript word): the lead-in is the GENUINE quiet audio before the first
 674 | +       onset; frames below DIGITAL_FLOOR_DBFS (-100 dBFS: encoder priming, file-head padding) are
 675 | +       not room tone. If it is < 80 ms the render must add a LEAD_PAD_S room-tone pad (D1).
 676 | +  OUT  cut_out inside the pause after the last word with >= TAIL_MIN_S (80 ms) of it kept and
 677 | +       >= GUARD_S (60 ms, M19) before the next onset -> the pause must be >= 140 ms.
 678 | +"""
 679 | +import hashlib
 680 | +import json
 681 | +import os
 682 | +import re
 683 | +import subprocess
 684 | +import time
 685 | +from difflib import SequenceMatcher
 686 | +
 687 | +import numpy as np
 688 | +
 689 | +PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
 690 | +REPO = os.path.dirname(PIPELINE_DIR)
 691 | +
 692 | +HOP_S = 0.010
 693 | +SR = 16000
 694 | +PAUSE_MIN_S = 0.080
 695 | +LEAD_MIN_S = 0.080
 696 | +TAIL_MIN_S = 0.080
 697 | +GUARD_S = 0.060
 698 | +LEAD_TARGET_S = 0.250       # preferred lead-in kept before the first onset (Law 14: breath kept)
 699 | +TAIL_TARGET_S = 0.300       # M19: cut_out = min(offset + 0.30, onset - 0.06)
 700 | +LEAD_PAD_S = 0.250          # D1 room-tone pad (6 frames at 24 fps)
 701 | +QUIET_BELOW_SPEECH_DB = 25.0
 702 | +VALLEY_BELOW_SPEECH_DB = 12.0
 703 | +BED_PLUS_DB = 6.0
 704 | +DIGITAL_FLOOR_DBFS = -100.0
 705 | +LEVEL_WINDOW_S = 3.0
 706 | +ONSET_SUSTAIN_S = 0.030
 707 | +EDGE_EPS_S = 0.011          # one 10 ms hop of measurement slack
 708 | +ANCHOR_MIN_RATIO = 0.80
 709 | +PUNCT_WINDOW_WORDS = 60
 710 | +WORD_DURATION_RATIO_MIN = 0.85  # G17: rendered edge word keeps >= 85 % of its duration
 711 | +_TERMINAL = (".", "!", "?")
 712 | +_ABBREV = {"mr", "mrs", "ms", "dr", "st", "vs", "etc", "jr", "sr", "inc", "ltd", "corp", "prof", "approx"}
 713 | +ADJ_CACHE = os.path.join(REPO, "data", "editorial", "sentence_adjudication.json")
 714 | +ADJ_LOG = os.path.join(REPO, "data", "editorial", "sentence_adjudication_log.jsonl")
 715 | +
 716 | +
 717 | +class LawError(Exception):
 718 | +    """A clip cannot be made sentence-complete (window must be rejected)."""
 719 | +
 720 | +
 721 | +# ── text ──
 722 | +
 723 | +def tokens(text):
 724 | +    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower().replace("’", "'").replace("'", "")) if t]
 725 | +
 726 | +
 727 | +def is_terminal(word):
 728 | +    w = (word or "").strip().rstrip("\"')]”’")
 729 | +    if not w.endswith(_TERMINAL) or w.endswith(".."):
 730 | +        return False
 731 | +    if re.fullmatch(r"\.(?:[A-Za-z]\.)+|(?:[A-Za-z]\.){2,}", w):
 732 | +        return False                      # U.S. / .S. / a.m. / e.g.
 733 | +    if w.endswith(".") and w[:-1].lower() in _ABBREV:
 734 | +        return False
 735 | +    return True
 736 | +
 737 | +
 738 | +def is_punctuated(words, k):
 739 | +    lo, hi = max(0, k - PUNCT_WINDOW_WORDS), min(len(words), k + PUNCT_WINDOW_WORDS + 1)
 740 | +    win = words[lo:hi]
 741 | +    marks = sum(1 for w in win if is_terminal(w["word"]))
 742 | +    return marks * PUNCT_WINDOW_WORDS >= len(win)
 743 | +
 744 | +
 745 | +def sha256_file(path):
 746 | +    h = hashlib.sha256()
 747 | +    with open(path, "rb") as f:
 748 | +        for chunk in iter(lambda: f.read(1 << 20), b""):
 749 | +            h.update(chunk)
 750 | +    return h.hexdigest()
 751 | +
 752 | +
 753 | +# ── audio ──
 754 | +
 755 | +class SourceAudio:
 756 | +    """10 ms RMS envelope (dBFS) of a whole media file, mono 16 kHz, decoded once."""
 757 | +
 758 | +    def __init__(self, path):
 759 | +        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
 760 | +                            "-f", "f32le", "-"], capture_output=True, check=True, timeout=300)
 761 | +        x = np.frombuffer(r.stdout, np.float32)
 762 | +        h = int(SR * HOP_S)
 763 | +        n = len(x) // h
 764 | +        if n == 0:
 765 | +            raise RuntimeError(f"no audio decoded from {path}")
 766 | +        self.path = path
 767 | +        self.dur = len(x) / SR
 768 | +        self.t = np.arange(n) * HOP_S
 769 | +        self.db = 20 * np.log10(np.sqrt(np.mean(x[:n * h].reshape(n, h).astype(np.float64) ** 2, axis=1)) + 1e-9)
 770 | +
 771 | +    def sl(self, t0, t1):
 772 | +        m = (self.t >= t0 - 1e-9) & (self.t < t1 - 1e-9)
 773 | +        return self.t[m], self.db[m]
 774 | +
 775 | +    def levels(self, t0, t1):
 776 | +        _, d = self.sl(max(0.0, t0), min(self.dur, t1))
 777 | +        live = d[d > DIGITAL_FLOOR_DBFS]
 778 | +        if len(live) < 10:
 779 | +            raise LawError(f"no audio in [{t0:.2f}, {t1:.2f}]")
 780 | +        speech = float(np.median(live[live > np.percentile(live, 30)]))
 781 | +        bed = float(np.percentile(live, 10))
 782 | +        quiet = min(speech - VALLEY_BELOW_SPEECH_DB, max(speech - QUIET_BELOW_SPEECH_DB, bed + BED_PLUS_DB))
 783 | +        return {"speech_db": round(speech, 1), "bed_db": round(bed, 1), "quiet_db": round(quiet, 1),
 784 | +                "loud_db": round(speech - VALLEY_BELOW_SPEECH_DB, 1)}
 785 | +
 786 | +
 787 | +def quiet_runs(t, db, quiet_db, genuine=False):
 788 | +    """Contiguous runs of frames below quiet_db as (start, end); end = first non-quiet frame time.
 789 | +    genuine=True also excludes digital silence (< DIGITAL_FLOOR_DBFS) from a run."""
 790 | +    mask = db < quiet_db
 791 | +    if genuine:
 792 | +        mask &= db > DIGITAL_FLOOR_DBFS
 793 | +    runs, i, n = [], 0, len(mask)
 794 | +    while i < n:
 795 | +        if mask[i]:
 796 | +            j = i
 797 | +            while j < n and mask[j]:
 798 | +                j += 1
 799 | +            runs.append((float(t[i]), float(t[j]) if j < n else float(t[-1]) + HOP_S))
 800 | +            i = j
 801 | +        else:
 802 | +            i += 1
 803 | +    return runs
 804 | +
 805 | +
 806 | +def first_onset(t, db, loud_db, start=None):
 807 | +    """First frame >= loud_db sustained ONSET_SUSTAIN_S, at or after `start`."""
 808 | +    k = int(round(ONSET_SUSTAIN_S / HOP_S))
 809 | +    for i in range(len(db)):
 810 | +        if (start is None or t[i] >= start - 1e-9) and i + k <= len(db) and np.all(db[i:i + k] >= loud_db):
 811 | +            return float(t[i])
 812 | +    return None
 813 | +
 814 | +
 815 | +def last_offset(t, db, loud_db, end=None):
 816 | +    """End time of the last frame >= loud_db (sustained), at or before `end`."""
 817 | +    k = int(round(ONSET_SUSTAIN_S / HOP_S))
 818 | +    for i in range(len(db) - 1, -1, -1):
 819 | +        if (end is None or t[i] <= end + 1e-9) and i - k + 1 >= 0 and np.all(db[i - k + 1:i + 1] >= loud_db):
 820 | +            return float(t[i]) + HOP_S
 821 | +    return None
 822 | +
 823 | +
 824 | +def find_pause(sa, a, b):
 825 | +    """Longest pause (>= PAUSE_MIN_S) overlapping [a, b]. Returns dict or None."""
 826 | +    lv = sa.levels(a - LEVEL_WINDOW_S, b + LEVEL_WINDOW_S)
 827 | +    t, d = sa.sl(max(0.0, a - 0.5), min(sa.dur, b + 0.5))
 828 | +    runs = [(s, e) for s, e in quiet_runs(t, d, lv["quiet_db"])
 829 | +            if e - s >= PAUSE_MIN_S - 1e-9 and e > a and s < b]
 830 | +    if not runs:
 831 | +        return None, lv
 832 | +    s, e = max(runs, key=lambda r: r[1] - r[0])
 833 | +    return {"start": round(s, 3), "end": round(e, 3), "ms": int(round((e - s) * 1000))}, lv
 834 | +
 835 | +
 836 | +# ── lexical adjudication for unpunctuated transcripts ──
 837 | +
 838 | +class Adjudicator:
 839 | +    """'Does a sentence end after word k?' for unpunctuated transcripts. Content-addressed cache,
 840 | +    every decision (cached or fresh) logged. allow_model=False = cache only (tests, gates replay)."""
 841 | +
 842 | +    def __init__(self, cache_path=ADJ_CACHE, log_path=ADJ_LOG, allow_model=True, model=None):
 843 | +        self.cache_path, self.log_path, self.allow_model = cache_path, log_path, allow_model
 844 | +        self.model = model
 845 | +        self._llm = None
 846 | +        try:
 847 | +            with open(cache_path) as f:
 848 | +                self.cache = json.load(f)
 849 | +        except (FileNotFoundError, json.JSONDecodeError):
 850 | +            self.cache = {}
 851 | +
 852 | +    def _llm_start(self):
 853 | +        if self._llm is None:
 854 | +            import story_semantics as sm
 855 | +            self._llm = sm.LocalLLM(model=self.model or sm.LLM_MODEL).start()
 856 | +        return self._llm
 857 | +
 858 | +    def close(self):
 859 | +        if self._llm is not None:
 860 | +            self._llm.stop()
 861 | +            self._llm = None
 862 | +
 863 | +    def decide(self, words, k, context=""):
 864 | +        left = " ".join(w["word"].strip() for w in words[max(0, k - 39):k + 1])
 865 | +        right = " ".join(w["word"].strip() for w in words[k + 1:k + 21])
 866 | +        model = self.model or "gemma3:27b"
 867 | +        key = hashlib.sha256(f"{model}|{left}|<GAP>|{right}".encode()).hexdigest()[:24]
 868 | +        rec = self.cache.get(key)
 869 | +        fresh = False
 870 | +        if rec is None:
 871 | +            if not self.allow_model:
 872 | +                raise LawError(f"sentence adjudication not cached for gap after '{words[k]['word']}' "
 873 | +                               f"(cache-only mode)")
 874 | +            prompt = (
 875 | +                "A speech transcript has no punctuation. Decide whether a sentence ENDS exactly at the "
 876 | +                "marker <GAP> (the next word begins a new sentence), judging grammar and meaning only.\n"
 877 | +                f"TEXT: ...{left} <GAP> {right}...\n"
 878 | +                'Answer JSON only: {"sentence_end": true or false, "reason": "<= 20 words"}')
 879 | +            out = self._llm_start().chat_json(
 880 | +                prompt, max_tokens=120,
 881 | +                validate=lambda o: isinstance(o, dict) and isinstance(o.get("sentence_end"), bool))
 882 | +            rec = {"sentence_end": bool(out["sentence_end"]), "reason": str(out.get("reason", ""))[:160],
 883 | +                   "left_tail": left[-80:], "right_head": right[:60], "model": model,
 884 | +                   "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
 885 | +            self.cache[key] = rec
 886 | +            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
 887 | +            tmp = self.cache_path + ".tmp"
 888 | +            with open(tmp, "w") as f:
 889 | +                json.dump(self.cache, f, indent=1, sort_keys=True)
 890 | +            os.replace(tmp, self.cache_path)
 891 | +            fresh = True
 892 | +        if self.log_path:
 893 | +            os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
 894 | +            with open(self.log_path, "a") as f:
 895 | +                f.write(json.dumps({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "key": key,
 896 | +                                    "fresh": fresh, "context": context, "after_word": words[k]["word"],
 897 | +                                    "sentence_end": rec["sentence_end"], "reason": rec["reason"]}) + "\n")
 898 | +        return rec["sentence_end"], f"model:{rec['model']} ({'fresh' if fresh else 'cached'} {key}): {rec['reason']}"
 899 | +
 900 | +
 901 | +# ── boundaries ──
 902 | +
 903 | +def boundary(sa, words, k, adj=None, context=""):
 904 | +    """Sentence boundary between word k and k+1 (k = -1: file head; k = len-1: file end)."""
 905 | +    n = len(words)
 906 | +    rec = {"after_word": words[k]["word"] if k >= 0 else "<file head>",
 907 | +           "before_word": words[k + 1]["word"] if k + 1 < n else "<file end>"}
 908 | +    if k < 0:                                            # file head: lexical start by definition
 909 | +        lv = sa.levels(max(0.0, words[0]["start"] - LEVEL_WINDOW_S), min(sa.dur, words[0]["end"] + LEVEL_WINDOW_S))
 910 | +        t, d = sa.sl(0.0, min(sa.dur, words[0]["end"] + 0.5))
 911 | +        onset = first_onset(t, d, lv["quiet_db"])
 912 | +        if onset is None:
 913 | +            return {**rec, "valid": False, "reason": "no onset found at file head", "levels": lv}
 914 | +        runs = [r for r in quiet_runs(t, d, lv["quiet_db"], genuine=True) if abs(r[1] - onset) < 1e-6]
 915 | +        lead = runs[0][1] - runs[0][0] if runs else 0.0
 916 | +        return {**rec, "valid": True, "lexical": "file head", "file_head": True, "levels": lv,
 917 | +                "onset": round(onset, 3), "genuine_lead_ms": int(round(lead * 1000)),
 918 | +                "pause": {"start": round(onset - lead, 3), "end": round(onset, 3), "ms": int(round(lead * 1000))}}
 919 | +    if k + 1 >= n:                                       # file end
 920 | +        lv = sa.levels(max(0.0, words[k]["start"] - LEVEL_WINDOW_S), min(sa.dur, words[k]["end"] + LEVEL_WINDOW_S))
 921 | +        t, d = sa.sl(max(0.0, words[k]["start"]), sa.dur)
 922 | +        off = last_offset(t, d, lv["quiet_db"])
 923 | +        if off is None:
 924 | +            return {**rec, "valid": False, "reason": "no offset found at file end", "levels": lv}
 925 | +        return {**rec, "valid": is_terminal(words[k]["word"]), "lexical": "punctuation", "file_end": True,
 926 | +                "levels": lv, "pause": {"start": round(off, 3), "end": round(sa.dur, 3),
 927 | +                                        "ms": int(round((sa.dur - off) * 1000))}}
 928 | +    pause, lv = find_pause(sa, words[k]["start"], words[k + 1]["end"])
 929 | +    rec.update(levels=lv, pause=pause)
 930 | +    if pause is None:
 931 | +        return {**rec, "valid": False, "reason": f"no pause >= {int(PAUSE_MIN_S * 1000)} ms between the words"}
 932 | +    if is_punctuated(words, k):
 933 | +        lex = is_terminal(words[k]["word"])
 934 | +        rec["lexical"] = "punctuation"
 935 | +        if not lex:
 936 | +            return {**rec, "valid": False, "reason": f"'{words[k]['word']}' does not end a sentence"}
 937 | +    else:
 938 | +        if adj is None:
 939 | +            return {**rec, "valid": False, "lexical": "unpunctuated",
 940 | +                    "reason": "unpunctuated transcript and no adjudicator"}
 941 | +        try:
 942 | +            lex, why = adj.decide(words, k, context=context)
 943 | +        except LawError as e:
 944 | +            return {**rec, "valid": False, "lexical": "unpunctuated", "reason": str(e)}
 945 | +        rec["lexical"] = why
 946 | +        if not lex:
 947 | +            return {**rec, "valid": False, "reason": f"adjudicated: no sentence end after '{words[k]['word']}'"}
 948 | +    return {**rec, "valid": True}
 949 | +
 950 | +
 951 | +def edge_plan(sa, words, i0, i1, adj=None, context=""):
 952 | +    """Boundaries around words[i0..i1] and the legal cut ranges they allow."""
 953 | +    bin_ = boundary(sa, words, i0 - 1, adj, context=f"{context} in")
 954 | +    bout = boundary(sa, words, i1, adj, context=f"{context} out")
 955 | +    plan = {"in": bin_, "out": bout}
 956 | +    if bin_["valid"]:
 957 | +        p = bin_["pause"]
 958 | +        if bin_.get("file_head"):
 959 | +            # keep every genuine sample before the onset; codec zeros before it are not room tone
 960 | +            # (the cut drops them and the declared pad replaces them when the lead is < 80 ms)
 961 | +            pad = 0.0 if bin_["genuine_lead_ms"] >= LEAD_MIN_S * 1000 else LEAD_PAD_S
 962 | +            bin_.update(cut_lo=0.0, cut_hi=p["start"], cut=p["start"], lead_in_pad_s=pad, cuttable=True)
 963 | +        elif p["end"] - p["start"] >= LEAD_MIN_S - 1e-9:
 964 | +            bin_.update(cut_lo=p["start"], cut_hi=round(p["end"] - LEAD_MIN_S, 3), cuttable=True,
 965 | +                        cut=round(max(p["start"], p["end"] - LEAD_TARGET_S), 3), lead_in_pad_s=0.0)
 966 | +        else:
 967 | +            bin_.update(cuttable=False, reason=f"pause {p['ms']} ms < lead-in {int(LEAD_MIN_S * 1000)} ms")
 968 | +    if bout["valid"]:
 969 | +        p = bout["pause"]
 970 | +        guard = 0.0 if bout.get("file_end") else GUARD_S
 971 | +        if p["end"] - p["start"] >= TAIL_MIN_S + guard - 1e-9:
 972 | +            bout.update(cut_lo=round(p["start"] + TAIL_MIN_S, 3), cut_hi=round(p["end"] - guard, 3),
 973 | +                        cut=round(min(p["start"] + TAIL_TARGET_S, p["end"] - guard), 3), cuttable=True)
 974 | +        else:
 975 | +            bout.update(cuttable=False, reason=f"pause {p['ms']} ms < tail {int(TAIL_MIN_S * 1000)} ms + "
 976 | +                                               f"guard {int(guard * 1000)} ms")
 977 | +    plan["ok"] = bool(bin_.get("cuttable") and bout.get("cuttable"))
 978 | +    return plan
 979 | +
 980 | +
 981 | +# ── selection lock ──
 982 | +
 983 | +def anchor(words, text, min_ratio=ANCHOR_MIN_RATIO, t0=None, t1=None):
 984 | +    """Locate the editor's selected text in a word-timestamp transcript (text alignment, never time
 985 | +    arithmetic; [t0, t1] only narrows the search). The span's first and last tokens must equal the
 986 | +    selection's. Returns (i0, i1, ratio) or None."""
 987 | +    qt = tokens(text)
 988 | +    toks = [(t, wi) for wi, w in enumerate(words)
 989 | +            if (t0 is None or w["start"] >= t0) and (t1 is None or w["start"] <= t1) for t in tokens(w["word"])]
 990 | +    seq = [t for t, _ in toks]
 991 | +    if len(qt) < 3 or not seq:
 992 | +        return None
 993 | +    blk = max(SequenceMatcher(None, qt, seq, autojunk=False).get_matching_blocks(), key=lambda b: b.size)
 994 | +    if blk.size < 3:
 995 | +        return None
 996 | +    base, best = blk.b - blk.a, None
 997 | +    for s in range(max(0, base - 8), min(len(seq), base + 9)):
 998 | +        if seq[s] != qt[0]:
 999 | +            continue
1000 | +        for e in range(s + max(1, len(qt) - 9), min(len(seq), s + len(qt) + 9)):
1001 | +            if seq[e] != qt[-1]:
1002 | +                continue
1003 | +            r = SequenceMatcher(None, qt, seq[s:e + 1], autojunk=False).ratio()
1004 | +            if best is None or r > best[0] + 1e-9:
1005 | +                best = (r, s, e)
1006 | +    if best is None or best[0] < min_ratio:
1007 | +        return None
1008 | +    r, s, e = best
1009 | +    i0, i1 = toks[s][1], toks[e][1]
1010 | +    if tokens(words[i0]["word"])[0] != qt[0] or tokens(words[i1]["word"])[-1] != qt[-1]:
1011 | +        return None
1012 | +    return i0, i1, round(r, 3)
1013 | +
1014 | +
1015 | +def _lock_digest(lock):
1016 | +    body = {k: v for k, v in lock.items() if k != "sha256"}
1017 | +    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
1018 | +
1019 | +
1020 | +def make_lock(video_id, words, i0, i1, transcript_sha256, selected_text, selected_window=None,
1021 | +              align_ratio=None, created_by=""):
1022 | +    lock = {"schema": "pulse.selection_lock.v1", "video_id": video_id, "transcript_sha256": transcript_sha256,
1023 | +            "i0": i0, "i1": i1, "first_word": words[i0]["word"].strip(), "last_word": words[i1]["word"].strip(),
1024 | +            "text": " ".join(w["word"].strip() for w in words[i0:i1 + 1]), "n_words": i1 - i0 + 1,
1025 | +            "selected_text": selected_text, "selected_window": selected_window, "align_ratio": align_ratio,
1026 | +            "created_by": created_by}
1027 | +    lock["sha256"] = _lock_digest(lock)
1028 | +    return lock
1029 | +
1030 | +
1031 | +def verify_lock(lock, transcript_path=None):
1032 | +    errs = []
1033 | +    if not lock or lock.get("schema") != "pulse.selection_lock.v1":
1034 | +        return ["no selection lock"]
1035 | +    if _lock_digest(lock) != lock.get("sha256"):
1036 | +        errs.append("selection lock modified after selection (sha256 mismatch)")
1037 | +    if transcript_path is not None and sha256_file(transcript_path) != lock["transcript_sha256"]:
1038 | +        errs.append("transcript changed since selection (sha256 mismatch)")
1039 | +    return errs
1040 | +
1041 | +
1042 | +# ── cut placement from the locks (replaces the +-2 s snap search) ──
1043 | +
1044 | +def _segments(edl):
1045 | +    yield "hook", edl["hook"]
1046 | +    for c in edl.get("clips", []):
1047 | +        yield f"clip_{c['index']:02d}", c
1048 | +
1049 | +
1050 | +def _accepted_cut_pair(src, plan, step=HOP_S):
1051 | +    """The cut pair nearest the plan's targets, searched ONLY inside the legal (locked-pause) ranges,
1052 | +    that also passes cut_accept's unchanged OUT-pause and IN-speech checks. None if no pair does."""
1053 | +    from cut_accept import envelope, speech_median_db, check_cut_out, check_cut_in
1054 | +    pi, po = plan["in"], plan["out"]
1055 | +
1056 | +    def grid(lo, hi, target):
1057 | +        n = int(round((hi - lo) / step))
1058 | +        pts = sorted({round(min(hi, lo + i * step), 3) for i in range(n + 1)} | {round(target, 3)})
1059 | +        return sorted(pts, key=lambda x: (abs(x - target), x))
1060 | +    t, db = envelope(src, pi["cut_lo"] - 1.0, po["cut_hi"] + 1.0)
1061 | +    med = speech_median_db(t, db, pi["cut"], po["cut"])
1062 | +    out_ok = next((x for x in grid(po["cut_lo"], po["cut_hi"], po["cut"]) if check_cut_out(t, db, x, med)[0]), None)
1063 | +    in_ok = next((x for x in grid(pi["cut_lo"], pi["cut_hi"], pi["cut"]) if check_cut_in(t, db, x, med)[0]), None)
1064 | +    if out_ok is None or in_ok is None:
1065 | +        return None
1066 | +    from cut_accept import check_cut_acoustics
1067 | +    return (in_ok, out_ok) if check_cut_acoustics(src, in_ok, out_ok)[0] else None
1068 | +
1069 | +
1070 | +def write_lock_cut_table(run_dir, adj=None):
1071 | +    """cuts_final.json with every cut placed inside the pause that bounds its LOCKED sentence(s):
1072 | +    the cut can never add or drop a word. A segment whose locked edges are not cuttable is written
1073 | +    verified=false with the reason (acceptance then HOLDs; no search outside the pause)."""
1074 | +    with open(os.path.join(run_dir, "edl.json")) as f:
1075 | +        edl = json.load(f)
1076 | +    cuts = []
1077 | +    for label, seg in _segments(edl):
1078 | +        lock = seg.get("selection_lock")
1079 | +        entry = {"clip_id": label, "video_id": seg["video_id"], "channel": seg.get("channel", ""),
1080 | +                 "fade_out_ms": 30, "fade_in_ms": 20, "verified": False}
1081 | +        tpath = os.path.join(run_dir, "transcripts", f"{seg['video_id']}.json")
1082 | +        errs = verify_lock(lock, tpath if os.path.exists(tpath) else None)
1083 | +        if errs:
1084 | +            cuts.append({**entry, "error": "; ".join(errs)})
1085 | +            continue
1086 | +        with open(tpath) as f:
1087 | +            words = json.load(f)["words"]
1088 | +        plan = edge_plan(SourceAudio(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4")), words,
1089 | +                         lock["i0"], lock["i1"], adj, context=f"cut {label}")
1090 | +        entry.update(first_word_expected=lock["first_word"], last_word_expected=lock["last_word"],
1091 | +                     selection_lock_sha256=lock["sha256"],
1092 | +                     pause_in=plan["in"].get("pause"), pause_out=plan["out"].get("pause"))
1093 | +        if not plan["ok"]:
1094 | +            why = [f"{s.upper()}: {plan[s].get('reason') or 'not cuttable'}" for s in ("in", "out")
1095 | +                   if not plan[s].get("cuttable")]
1096 | +            cuts.append({**entry, "error": "locked sentence edges not cuttable: " + "; ".join(why)})
1097 | +            continue
1098 | +        pick = _accepted_cut_pair(os.path.join(run_dir, "sources", f"{seg['video_id']}.mp4"), plan)
1099 | +        if pick is None:
1100 | +            cuts.append({**entry, "error": (
1101 | +                f"no point inside the locked pauses passes cut_accept (IN {plan['in']['cut_lo']}-"
1102 | +                f"{plan['in']['cut_hi']}, OUT {plan['out']['cut_lo']}-{plan['out']['cut_hi']})")})
1103 | +            continue
1104 | +        cut_in, cut_out = pick
1105 | +        cuts.append({**entry, "cut_in": cut_in, "cut_out": cut_out, "cut_duration": round(cut_out - cut_in, 3),
1106 | +                     "lead_in_pad_s": plan["in"]["lead_in_pad_s"], "verified": True})
1107 | +    with open(os.path.join(run_dir, "cuts_final.json"), "w") as f:
1108 | +        json.dump(cuts, f, indent=2)
1109 | +    return cuts
1110 | +
1111 | +
1112 | +# ── G16 SENTENCE_BOUNDARY (pre-render and final gate) ──
1113 | +
1114 | +
1115 | +def gate_g16(run_dir, adj=None, source_path_fn=None):
1116 | +    """Every clip's cut must hold exactly its locked sentence(s): lock intact, expected words equal the
1117 | +    lock (never recomputed), both edges legal sentence boundaries, cut points inside those pauses
1118 | +    (or a declared room-tone pad at a file head without lead-in). Returns (ok, table)."""
1119 | +    with open(os.path.join(run_dir, "edl.json")) as f:
1120 | +        edl = json.load(f)
1121 | +    with open(os.path.join(run_dir, "cuts_final.json")) as f:
1122 | +        cuts = {c["clip_id"]: c for c in json.load(f)}
1123 | +    table, ok_all = [], True
1124 | +    for label, seg in _segments(edl):
1125 | +        row = {"segment": label, "video_id": seg.get("video_id"), "errors": []}
1126 | +        lock = seg.get("selection_lock")
1127 | +        tpath = os.path.join(run_dir, "transcripts", f"{seg.get('video_id')}.json")
1128 | +        row["errors"] += verify_lock(lock, tpath if os.path.exists(tpath) else None)
1129 | +        cut = cuts.get(label)
1130 | +        if cut is None:
1131 | +            row["errors"].append("no cut in cuts_final.json")
1132 | +        if not row["errors"]:
1133 | +            if (cut.get("first_word_expected"), cut.get("last_word_expected")) != (lock["first_word"], lock["last_word"]):
1134 | +                row["errors"].append(
1135 | +                    f"expected words '{cut.get('first_word_expected')}'/'{cut.get('last_word_expected')}' differ from "
1136 | +                    f"the selection lock '{lock['first_word']}'/'{lock['last_word']}' (recomputed after selection)")
1137 | +            with open(tpath) as f:
1138 | +                words = json.load(f)["words"]
1139 | +            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(seg["video_id"])
1140 | +            sa = SourceAudio(src)
1141 | +            plan = edge_plan(sa, words, lock["i0"], lock["i1"], adj, context=f"G16 {label}")
1142 | +            row["in"] = _edge_row(plan["in"], cut["cut_in"], "in", cut)
1143 | +            row["out"] = _edge_row(plan["out"], cut["cut_out"], "out", cut)
1144 | +            row["errors"] += [f"IN: {row['in']['why']}"] if not row["in"]["pass"] else []
1145 | +            row["errors"] += [f"OUT: {row['out']['why']}"] if not row["out"]["pass"] else []
1146 | +            row["locked"] = f"'{lock['first_word']}' ... '{lock['last_word']}' ({lock['n_words']} words)"
1147 | +        row["pass"] = not row["errors"]
1148 | +        ok_all &= row["pass"]
1149 | +        table.append(row)
1150 | +    return ok_all, table
1151 | +
1152 | +
1153 | +def _edge_row(b, cut_t, side, cut):
1154 | +    r = {"cut": cut_t, "boundary_valid": b.get("valid"), "pause": b.get("pause"), "lexical": b.get("lexical"),
1155 | +         "after_word": b.get("after_word"), "before_word": b.get("before_word")}
1156 | +    if not b.get("valid"):
1157 | +        return {**r, "pass": False, "why": f"no sentence boundary: {b.get('reason')}"}
1158 | +    if not b.get("cuttable"):
1159 | +        return {**r, "pass": False, "why": f"boundary not cuttable: {b.get('reason')}"}
1160 | +    r.update(cut_lo=b["cut_lo"], cut_hi=b["cut_hi"])
1161 | +    if side == "in" and b.get("file_head"):
1162 | +        need = b["lead_in_pad_s"]
1163 | +        have = float(cut.get("lead_in_pad_s") or 0.0)
1164 | +        in_range = b["cut_lo"] - EDGE_EPS_S <= cut_t <= b["cut_hi"] + EDGE_EPS_S
1165 | +        ok = in_range and have + 1e-9 >= need
1166 | +        return {**r, "pass": ok, "genuine_lead_ms": b["genuine_lead_ms"], "pad_needed_s": need, "pad_declared_s": have,
1167 | +                "why": "ok" if ok else (f"source starts speaking {b['genuine_lead_ms']} ms after its genuine audio "
1168 | +                                        f"begins (< {int(LEAD_MIN_S * 1000)} ms) and no {need:.2f} s lead-in pad is declared"
1169 | +                                        if in_range else f"cut_in {cut_t:.3f} cuts into the source's first words")}
1170 | +    ok = b["cut_lo"] - EDGE_EPS_S <= cut_t <= b["cut_hi"] + EDGE_EPS_S
1171 | +    return {**r, "pass": ok, "why": "ok" if ok else
1172 | +            f"cut_{side} {cut_t:.3f} outside the legal range {b['cut_lo']:.3f}-{b['cut_hi']:.3f} "
1173 | +            f"(pause {b['pause']['start']:.3f}-{b['pause']['end']:.3f} between '{b['after_word']}' and '{b['before_word']}')"}
1174 | +
1175 | +
1176 | +# ── D1 lead-in pad: room tone + held first frame before a file-head sentence ──
1177 | +
1178 | +def room_tone(src_path, t0, t1, seconds, sr=48000):
1179 | +    """`seconds` of the source's own quietest genuine room tone found in [t0, t1] (>= 40 ms run),
1180 | +    looped with 10 ms crossfades. Raises LawError if the source has none (fail closed)."""
1181 | +    sa = SourceAudio(src_path)
1182 | +    lv = sa.levels(t0, t1)
1183 | +    t, d = sa.sl(t0, t1)
1184 | +    runs = [(s, e) for s, e in quiet_runs(t, d, lv["quiet_db"], genuine=True) if e - s >= 0.040 - 1e-9]
1185 | +    if not runs:
1186 | +        raise LawError("no genuine room tone in the segment to build a lead-in pad")
1187 | +    s, e = min(runs, key=lambda r: float(np.median(d[(t >= r[0] - 1e-9) & (t < r[1] - 1e-9)])))
1188 | +    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{s:.3f}", "-i", src_path, "-t", f"{e - s:.3f}", "-vn",
1189 | +                        "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True, check=True, timeout=60)
1190 | +    x = np.frombuffer(r.stdout, np.float32).reshape(-1, 2).astype(np.float64)
1191 | +    m, n = int(0.010 * sr), int(round(seconds * sr))
1192 | +    if len(x) <= 2 * m:
1193 | +        raise LawError("room-tone run too short to loop")
1194 | +    out = x.copy()
1195 | +    ramp = np.linspace(0.0, 1.0, m)[:, None]
1196 | +    while len(out) < n:
1197 | +        out = np.concatenate([out[:-m], out[-m:] * (1 - ramp) + x[:m] * ramp, x[m:]])
1198 | +    out = out[:n]
1199 | +    k = int(0.020 * sr)
1200 | +    out[:k] *= np.linspace(0.0, 1.0, k)[:, None]           # M19 20 ms fade-in at the new head
1201 | +    return out.astype(np.float32), {"from_s": round(s, 3), "to_s": round(e, 3)}
1202 | +
1203 | +
1204 | +def apply_lead_in_pad(run_dir, cut, fps, qp):
1205 | +    """Prepend cut['lead_in_pad_s'] of room tone + the held first frame to qa/final_<clip>.mp4
1206 | +    (atomic replace). The pad is declared in cuts_final.json, so every gate knows it is there."""
1207 | +    import wave
1208 | +    pad = float(cut["lead_in_pad_s"])
1209 | +    clip = os.path.join(run_dir, "qa", f"final_{cut['clip_id']}.mp4")
1210 | +    src = os.path.join(run_dir, "sources", f"{cut['video_id']}.mp4")
1211 | +    tone, info = room_tone(src, cut["cut_in"], cut["cut_out"], pad)
1212 | +    wav = os.path.join(run_dir, "qa", f"leadpad_{cut['clip_id']}.wav")
1213 | +    with wave.open(wav, "wb") as f:
1214 | +        f.setnchannels(2)
1215 | +        f.setsampwidth(2)
1216 | +        f.setframerate(48000)
1217 | +        f.writeframes((np.clip(tone, -1, 1) * 32767).astype(np.int16).tobytes())
1218 | +    part = clip + ".pad.mp4"
1219 | +    fmt = "aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo"
1220 | +    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", clip, "-i", wav, "-filter_complex",
1221 | +                    f"[0:v]tpad=start_duration={pad:.3f}:start_mode=clone,setpts=PTS-STARTPTS[v];"
1222 | +                    f"[1:a]{fmt}[p];[0:a]{fmt}[c];[p][c]concat=n=2:v=0:a=1[a]",
1223 | +                    "-map", "[v]", "-map", "[a]", "-r", str(fps), "-c:v", "h264_nvenc", "-preset", "p4",
1224 | +                    "-rc", "constqp", "-qp", str(qp), "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
1225 | +                    "-ar", "48000", "-ac", "2", "-movflags", "+faststart", part],
1226 | +                   check=True, capture_output=True, timeout=300)
1227 | +    os.replace(part, clip)
1228 | +    return {"pad_s": pad, "room_tone_source_s": info, "wav": os.path.basename(wav)}
1229 | +
1230 | +
1231 | +# ── G17 ONSET/TAIL INTEGRITY (rendered audio) ──
1232 | +
1233 | +def head_tail(sa):
1234 | +    """Genuine lead-in before the first onset and genuine tail after the last offset of a rendered
1235 | +    segment, each measured with levels LOCAL to that edge (first / last LEVEL_WINDOW_S seconds)."""
1236 | +    w = min(sa.dur, LEVEL_WINDOW_S)
1237 | +    lh, lt = sa.levels(0.0, w), sa.levels(sa.dur - w, sa.dur)
1238 | +    th, dh = sa.sl(0.0, w)
1239 | +    tt, dt = sa.sl(sa.dur - w, sa.dur)
1240 | +    onset, off = first_onset(th, dh, lh["quiet_db"]), last_offset(tt, dt, lt["quiet_db"])
1241 | +    lead = next((e - s for s, e in quiet_runs(th, dh, lh["quiet_db"], genuine=True)
1242 | +                 if onset is not None and abs(e - onset) < 1e-6), 0.0)
1243 | +    tail = next((e - s for s, e in quiet_runs(tt, dt, lt["quiet_db"], genuine=True)
1244 | +                 if off is not None and abs(s - off) < 1e-6), 0.0)
1245 | +    return {"onset": onset, "offset": off, "lead_ms": int(round(lead * 1000)), "tail_ms": int(round(tail * 1000)),
1246 | +            "levels": {"head": lh, "tail": lt}}
1247 | +
1248 | +
1249 | +def gate_g17_prepared(clip_paths):
1250 | +    """G17a on each prepared clip {clip_id: path} (qa/final_<clip>.mp4: the rendered segment audio
1251 | +    before the music bed): >= 80 ms genuine quiet before the first onset and after the last offset."""
1252 | +    table, ok_all = [], True
1253 | +    for cid, p in clip_paths.items():
1254 | +        ht = head_tail(SourceAudio(p))
1255 | +        lead_ok, tail_ok = ht["lead_ms"] >= LEAD_MIN_S * 1000, ht["tail_ms"] >= TAIL_MIN_S * 1000
1256 | +        row = {"segment": cid, **{k: ht[k] for k in ("onset", "offset", "lead_ms", "tail_ms")},
1257 | +               "quiet_db": {k: v["quiet_db"] for k, v in ht["levels"].items()},
1258 | +               "lead_ok": lead_ok, "tail_ok": tail_ok, "pass": lead_ok and tail_ok}
1259 | +        ok_all &= row["pass"]
1260 | +        table.append(row)
1261 | +    return ok_all, table
1262 | +
1263 | +
1264 | +def gate_g17_output(final_path, segments, cuts, run_dir, source_path_fn=None):
1265 | +    """G17b on a final output: the first and last word of every clip keep >= 85 % of their duration.
1266 | +    The render may only add silence around a word: the speech onset (offset) measured in the output
1267 | +    must not come later (earlier) than in the source, relative to the clip start, by more than 15 % of
1268 | +    the locked edge word's transcript duration (clamped 0.10-1.00 s). Returns (ok, table)."""
1269 | +    with open(os.path.join(run_dir, "edl.json")) as f:
1270 | +        locks = {label: seg.get("selection_lock") for label, seg in _segments(json.load(f))}
1271 | +    by = {c["clip_id"]: c for c in cuts}
1272 | +    out = SourceAudio(final_path)
1273 | +    table, ok_all = [], True
1274 | +    for seg in segments:
1275 | +        if seg.get("type") != "talking_head":
1276 | +            continue
1277 | +        label, c, lock = seg["label"], by.get(seg["label"]), locks.get(seg["label"])
1278 | +        row = {"segment": label}
1279 | +        if c is None or not lock:
1280 | +            row.update(pass_=False, why="no cut or no selection lock")
1281 | +        else:
1282 | +            pad = float(c.get("lead_in_pad_s") or 0.0)
1283 | +            src = (source_path_fn or (lambda v: os.path.join(run_dir, "sources", f"{v}.mp4")))(c["video_id"])
1284 | +            sa = SourceAudio(src)
1285 | +            ls = sa.levels(c["cut_in"], c["cut_out"])
1286 | +            ts, ds = sa.sl(c["cut_in"], c["cut_out"])
1287 | +            lo = out.levels(seg["start"], seg["end"])
1288 | +            to, do = out.sl(seg["start"] + pad, seg["end"])
1289 | +            s_on, s_off = first_onset(ts, ds, ls["loud_db"]), last_offset(ts, ds, ls["loud_db"])
1290 | +            o_on, o_off = first_onset(to, do, lo["loud_db"]), last_offset(to, do, lo["loud_db"])
1291 | +            with open(os.path.join(run_dir, "transcripts", f"{c['video_id']}.json")) as f:
1292 | +                words = json.load(f)["words"]
1293 | +            dur = lambda w: min(1.0, max(0.10, w["end"] - w["start"]))
1294 | +            d0, d1 = dur(words[lock["i0"]]), dur(words[lock["i1"]])
1295 | +            if None in (s_on, s_off, o_on, o_off):
1296 | +                row.update(pass_=False, why="speech onset/offset not measurable")
1297 | +            else:
1298 | +                late = (o_on - seg["start"] - pad) - (s_on - c["cut_in"])
1299 | +                early = (s_off - c["cut_in"]) - (o_off - seg["start"] - pad)
1300 | +                head_ok = late <= (1 - WORD_DURATION_RATIO_MIN) * d0 + HOP_S
1301 | +                tail_ok = early <= (1 - WORD_DURATION_RATIO_MIN) * d1 + HOP_S
1302 | +                row.update(onset_late_ms=int(round(late * 1000)), offset_early_ms=int(round(early * 1000)),
1303 | +                           first_word_ratio=round(max(0.0, 1 - max(0.0, late) / d0), 3),
1304 | +                           last_word_ratio=round(max(0.0, 1 - max(0.0, early) / d1), 3),
1305 | +                           head_ok=head_ok, tail_ok=tail_ok, pass_=head_ok and tail_ok)
1306 | +        row["pass"] = row.pop("pass_")
1307 | +        ok_all &= row["pass"]
1308 | +        table.append(row)
1309 | +    return ok_all, table
1310 | diff --git a/pipeline/test_fresh.py b/pipeline/test_fresh.py
1311 | index 98a895cf..a3f019c5 100644
1312 | --- a/pipeline/test_fresh.py
1313 | +++ b/pipeline/test_fresh.py
1314 | @@ -28,29 +28,61 @@ def _sha(p):
1315 |  
1316 |  # ── B: select_passages keeps EDL times in source-file coordinates ──
1317 |  
1318 | +def _synth_window(path, words, dur=45.0, sr=16000):
1319 | +    """WAV with a 300 Hz tone (~-23 dBFS) under every word and -69 dBFS noise elsewhere, so sentence
1320 | +    gaps are real pauses and word gaps (50 ms) are not."""
1321 | +    import numpy as np
1322 | +    import wave
1323 | +    rng = np.random.default_rng(7)
1324 | +    x = rng.normal(0, 0.0005, int(dur * sr))
1325 | +    for w in words:
1326 | +        i0, i1 = int(w["start"] * sr), int(w["end"] * sr)
1327 | +        x[i0:i1] += 0.1 * np.sin(2 * np.pi * 300 * np.arange(i1 - i0) / sr)
1328 | +    with wave.open(path, "wb") as f:
1329 | +        f.setnchannels(1)
1330 | +        f.setsampwidth(2)
1331 | +        f.setframerate(sr)
1332 | +        f.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
1333 | +
1334 | +
1335 | +def _sentences(tag, t, n_sent=8, per=6):
1336 | +    """Sentence-structured word timestamps: 0.30 s words, 0.05 s word gaps, 0.50 s sentence gaps."""
1337 | +    ws = []
1338 | +    for si in range(n_sent):
1339 | +        for wi in range(per):
1340 | +            ws.append({"word": f"{tag}s{si}w{wi}" + ("." if wi == per - 1 else ""),
1341 | +                       "start": round(t, 2), "end": round(t + 0.30, 2)})
1342 | +            t += 0.35
1343 | +        t += 0.45
1344 | +    return ws
1345 | +
1346 | +
1347 |  class TestSelectCoords(unittest.TestCase):
1348 |      def test_edl_times_are_source_file_coords(self):
1349 |          import select_passages as sp
1350 | +        words = {"AAA": _sentences("a", 2.0), "BBB": _sentences("b", 2.0)}
1351 | +
1352 | +        def text(vid, s0, s1):  # sentences s0..s1 as the editor selected them
1353 | +            return " ".join(w["word"] for w in words[vid] if s0 <= int(w["word"][1:].split("s")[1].split("w")[0]) <= s1)
1354 |          with tempfile.TemporaryDirectory() as rd:
1355 | +            os.makedirs(os.path.join(rd, "sources"))
1356 | +            os.makedirs(os.path.join(rd, "transcripts"))
1357 |              passages = {"chosen": [
1358 |                  {"video_id": "AAA", "channel": "The Bitcoin Layer", "start": 110.0, "end": 121.0,
1359 | -                 "duration": 11.0, "score": 9, "text": "Statement one."},
1360 | +                 "duration": 11.0, "score": 9, "text": text("AAA", 5, 6)},
1361 |                  {"video_id": "BBB", "channel": "BTC Sessions", "start": 510.0, "end": 524.0,
1362 | -                 "duration": 14.0, "score": 5, "text": "Statement two."}]}
1363 | +                 "duration": 14.0, "score": 5, "text": text("BBB", 5, 7)}]}
1364 |              json.dump(passages, open(os.path.join(rd, "passages.json"), "w"))
1365 |  
1366 |              def fake_dl(vid, start, end, run_dir, pad=15.0):
1367 | -                return (os.path.join(run_dir, "sources", f"{vid}.mp4"), start - pad)
1368 | +                path = os.path.join(run_dir, "sources", f"{vid}.wav")
1369 | +                _synth_window(path, words[vid])
1370 | +                return (path, start - pad)
1371 |  
1372 |              def fake_tx(path, vid, run_dir):
1373 | -                # whisper words in LOCAL (downloaded file) seconds: both windows start
1374 | -                # 15 s before the passage, so the passage begins near local t=15
1375 | -                ws, t = [], 14.0
1376 | -                for i in range(60):
1377 | -                    w = "word." if i % 6 == 5 else "word"
1378 | -                    ws.append({"word": w, "start": round(t, 2), "end": round(t + 0.3, 2)})
1379 | -                    t += 0.35
1380 | -                return {"words": ws}
1381 | +                rec = {"words": words[vid]}
1382 | +                json.dump(rec, open(os.path.join(run_dir, "transcripts", f"{vid}.json"), "w"))
1383 | +                return rec
1384 |  
1385 |              orig = (sp._download_window, sp._whisper_transcribe)
1386 |              sp._download_window, sp._whisper_transcribe = fake_dl, fake_tx
1387 | @@ -66,6 +98,10 @@ class TestSelectCoords(unittest.TestCase):
1388 |                  # source-file coords: well inside the ~40 s downloaded window, never full-video
1389 |                  self.assertLess(seg["word_start"], 60.0, seg)
1390 |                  self.assertLess(seg["word_end"], 60.0, seg)
1391 | +                # the editor's sentences, sealed at selection (sentence law)
1392 | +                lock = seg["selection_lock"]
1393 | +                self.assertEqual((lock["first_word"], lock["last_word"]), (seg["first_word"], seg["last_word"]))
1394 | +                self.assertTrue(lock["first_word"].endswith("s5w0") and lock["last_word"].endswith("w5."), lock)
1395 |  
1396 |  
1397 |  # ── intro-optional renderer support (shared helper) ──
1398 | diff --git a/pipeline/test_pinned.py b/pipeline/test_pinned.py
1399 | index 9a067353..9c88166f 100644
1400 | --- a/pipeline/test_pinned.py
1401 | +++ b/pipeline/test_pinned.py
1402 | @@ -221,7 +221,7 @@ class TestRunFreshUsesSharedCutAcceptance(Fixture):
1403 |          try:
1404 |              run = rf.Run(self.run_dir)
1405 |              run.mode = "pinned"
1406 | -            cuts, _snap_alts = rf.stage_cut(run)
1407 | +            cuts = rf.stage_cut(run)
1408 |              self.assertEqual(calls, [(f"{s['video_id']}.mp4", s["start"], s["end"]) for s in p["segments"]])
1409 |              self.assertEqual([(c["cut_in"], c["cut_out"]) for c in cuts], [(s["start"], s["end"]) for s in p["segments"]])
1410 |              # acceptance rejection still holds the run (no auto-widen)
1411 | @@ -232,18 +232,22 @@ class TestRunFreshUsesSharedCutAcceptance(Fixture):
1412 |          finally:
1413 |              cut.compute_all_cuts, cut_accept.check_cut_acoustics = orig_cut, orig_acc
1414 |  
1415 | -    def test_auto_mode_still_uses_the_acoustic_cutter(self):
1416 | +    def test_auto_mode_places_cuts_from_the_selection_locks(self):
1417 | +        # 2026-11-11 sentence law: AUTO cuts come from the locked sentences' pauses
1418 | +        # (sentence_law.write_lock_cut_table); the free acoustic cutter is never used by run_fresh.
1419 |          import run_fresh as rf
1420 |          import cut
1421 | -        orig = cut.compute_all_cuts
1422 | -        cut.compute_all_cuts = lambda run_dir: (_ for _ in ()).throw(RuntimeError("cutter called"))
1423 | +        import sentence_law
1424 | +        orig_cut, orig_lock = cut.compute_all_cuts, sentence_law.write_lock_cut_table
1425 | +        cut.compute_all_cuts = lambda *a, **k: (_ for _ in ()).throw(AssertionError("free acoustic cutter used"))
1426 | +        sentence_law.write_lock_cut_table = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("lock placement"))
1427 |          try:
1428 |              run = rf.Run(self.run_dir)
1429 |              self.assertEqual(run.mode, "auto")
1430 | -            with self.assertRaises(RuntimeError):
1431 | +            with self.assertRaisesRegex(RuntimeError, "lock placement"):
1432 |                  rf.stage_cut(run)
1433 |          finally:
1434 | -            cut.compute_all_cuts = orig
1435 | +            cut.compute_all_cuts, sentence_law.write_lock_cut_table = orig_cut, orig_lock
1436 |  
1437 |      def test_v2f_material_guard_only_lifted_by_explicit_pin_flag(self):
1438 |          import run_fresh as rf
1439 | diff --git a/pipeline/test_pulse_20261110_mustfail.py b/pipeline/test_pulse_20261110_mustfail.py
1440 | index 38f64690..4fe1dfd8 100644
1441 | --- a/pipeline/test_pulse_20261110_mustfail.py
1442 | +++ b/pipeline/test_pulse_20261110_mustfail.py
1443 | @@ -93,30 +93,72 @@ class TestSelectionLockEdges(_G16Fixture):
1444 |  class TestD1HookOnset(_G16Fixture):
1445 |      def test_g16_in_fails_without_lead_in_pad(self):
1446 |          r = self.rows["hook"]["in"]
1447 | -        self.assertFalse(r["pass"], r)
1448 | -        self.assertLess(r["genuine_lead_ms"], 80)
1449 | +        self.assertFalse(r["pass"], f"D1: G16 must reject a file-head hook with <80 ms genuine lead-in and no pad: {r}")
1450 | +        self.assertLess(r["genuine_lead_ms"], 80, r)
1451 |  
1452 |      def test_g17a_head_fails(self):
1453 | -        self.assertFalse(self.g17["hook"]["lead_ok"], self.g17["hook"])
1454 | +        self.assertFalse(self.g17["hook"]["lead_ok"], f"D1: G17a must see <80 ms genuine lead-in: {self.g17['hook']}")
1455 |  
1456 |  
1457 |  class TestD2Clip01Out(_G16Fixture):
1458 |      def test_g16_out_fails(self):
1459 | -        self.assertFalse(self.rows["clip_01"]["out"]["pass"], self.rows["clip_01"]["out"])
1460 | +        r = self.rows["clip_01"]["out"]
1461 | +        self.assertFalse(r["pass"], f"D2: clip_01 out 33.71 runs into the next sentence: {r}")
1462 | +        # for the right reason: the locked sentence ends at 'week.' and that edge is not a legal cut there
1463 | +        self.assertEqual(r["after_word"], "week.", r)
1464 | +        self.assertIn("not cuttable", r["why"], r)
1465 |  
1466 |  
1467 |  class TestD3Edges(_G16Fixture):
1468 |      def test_d3a_clip01_in_fails(self):
1469 | -        self.assertFalse(self.rows["clip_01"]["in"]["pass"], self.rows["clip_01"]["in"])
1470 | -        self.assertFalse(self.g17["clip_01"]["lead_ok"], self.g17["clip_01"])
1471 | +        r = self.rows["clip_01"]["in"]
1472 | +        self.assertFalse(r["pass"], f"D3a: clip_01 in 15.13 starts on '81', not 'It': {r}")
1473 | +        self.assertEqual(r["before_word"], "It", r)
1474 | +        self.assertIn("outside the legal range", r["why"], r)
1475 | +        self.assertFalse(self.g17["clip_01"]["lead_ok"], f"D3a: G17a lead-in: {self.g17['clip_01']}")
1476 |  
1477 |      def test_d3b_clip02_in_fails(self):
1478 | -        self.assertFalse(self.rows["clip_02"]["in"]["pass"], self.rows["clip_02"]["in"])
1479 | -        self.assertFalse(self.g17["clip_02"]["lead_ok"], self.g17["clip_02"])
1480 | +        r = self.rows["clip_02"]["in"]
1481 | +        self.assertFalse(r["pass"], f"D3b: clip_02 in 14.93 lands inside 'days': {r}")
1482 | +        self.assertIn("outside the legal range", r["why"], r)
1483 | +        self.assertFalse(self.g17["clip_02"]["lead_ok"], f"D3b: G17a lead-in: {self.g17['clip_02']}")
1484 |  
1485 |      def test_d3c_clip02_out_control_passes(self):
1486 | -        self.assertTrue(self.rows["clip_02"]["out"]["pass"], self.rows["clip_02"]["out"])
1487 | -        self.assertTrue(self.g17["clip_02"]["tail_ok"], self.g17["clip_02"])
1488 | +        self.assertTrue(self.rows["clip_02"]["out"]["pass"], f"CONTROL D3c: clean out edge must pass G16: {self.rows['clip_02']['out']}")
1489 | +        self.assertTrue(self.g17["clip_02"]["tail_ok"], f"CONTROL D3c: clean tail must pass G17a: {self.g17['clip_02']}")
1490 | +
1491 | +
1492 | +class TestG17bRenderedEdges(_G16Fixture):
1493 | +    """G17b: the render may add silence but must not eat a word. Yesterday's render was faithful to its
1494 | +    (wrong) cuts, so G17b PASSES on it (D1 is a source lead-in problem: G16 + G17a). A render whose
1495 | +    fade eats the hook's opening word must FAIL."""
1496 | +
1497 | +    def _run(self, audio):
1498 | +        L = _law()
1499 | +        segs = json.load(open(os.path.join(FIX, "run", "concat_manifest_16x9.json")))["segments"]
1500 | +        cuts = json.load(open(os.path.join(FIX, "run", "cuts_final.json")))
1501 | +        ok, table = L.gate_g17_output(audio, segs, cuts, self.tmp,
1502 | +                                      source_path_fn=lambda v: os.path.join(FIX, "audio", f"src_{v}.flac"))
1503 | +        return ok, {r["segment"]: r for r in table}
1504 | +
1505 | +    def test_faithful_render_passes(self):
1506 | +        ok, rows = self._run(os.path.join(FIX, "audio", "out_16x9.flac"))
1507 | +        self.assertTrue(rows["hook"]["head_ok"], rows["hook"])
1508 | +
1509 | +    def _variant(self, name, af):
1510 | +        out = os.path.join(self.tmp, name)
1511 | +        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(FIX, "audio", "out_16x9.flac"),
1512 | +                        "-af", af, out], check=True)
1513 | +        return self._run(out)[1]["hook"]
1514 | +
1515 | +    def test_render_that_eats_the_opening_word_fails(self):
1516 | +        # the first 160 ms muted: ~70 ms of 'Bitcoin' (onset ~0.09 s) lost, < 85 % of the word left
1517 | +        row = self._variant("eaten.flac", "volume=enable='between(t,0,0.16)':volume=0")
1518 | +        self.assertFalse(row["head_ok"], row)
1519 | +
1520 | +    def test_standard_20ms_fade_passes(self):
1521 | +        row = self._variant("fade20.flac", "afade=t=in:st=0:d=0.02")
1522 | +        self.assertTrue(row["head_ok"], row)
1523 |  
1524 |  
1525 |  class TestTautology(_G16Fixture):
1526 | @@ -162,7 +204,13 @@ class TestWindowOffset(unittest.TestCase):
1527 |  
1528 |  
1529 |  class TestD4Credits(unittest.TestCase):
1530 | -    S = tempfile.mkdtemp(prefix="g15_")
1531 | +    @classmethod
1532 | +    def setUpClass(cls):
1533 | +        cls.S = tempfile.mkdtemp(prefix="g15_")
1534 | +
1535 | +    @classmethod
1536 | +    def tearDownClass(cls):
1537 | +        shutil.rmtree(cls.S, ignore_errors=True)
1538 |  
1539 |      def _gates(self, mp4, segs):
1540 |          import gates as G
1541 | @@ -186,9 +234,15 @@ class TestD4Credits(unittest.TestCase):
1542 |  
1543 |      def test_shoutout_refuses_a_thumbnail_avatar(self):
1544 |          import shoutout
1545 | -        with self.assertRaises(ValueError):
1546 | +        with self.assertRaisesRegex(ValueError, "square"):
1547 |              shoutout.validate_avatar(os.path.join(FIX, "video", "natalie_brunell.jpg"))
1548 |  
1549 | +    def test_shoutout_accepts_a_registered_square_avatar(self):
1550 | +        # positive control: the v2f BTC Sessions avatar (approved, square) must be accepted
1551 | +        import shoutout
1552 | +        reg = {c["display_name"]: c for c in json.load(open(os.path.join(PIPELINE_DIR, "channels.json")))}
1553 | +        shoutout.validate_avatar(reg["BTC Sessions"]["avatar_path"])
1554 | +
1555 |      def test_no_thumbnail_or_placeholder_fallback(self):
1556 |          import shoutout
1557 |          src = inspect.getsource(shoutout)
1558 | 
```

---



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
