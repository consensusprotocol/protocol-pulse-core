# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/check_preview_reference.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0096
## Consensus findings (majority of panel agrees)
- **[high] pipeline/check_preview_reference.py:34** zip() silently truncates to the shorter of segs and pin['segments']; if PIN.json has fewer segments than the EDL, the extra segments are never checked and the script can return REPRODUCED (exit 0).
  - evidence: `for (label, seg), ps in zip(segs, pin["segments"]):`
  - fix: Assert len(segs) == len(pin['segments']) and fail if they differ.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[medium] pipeline/check_preview_reference.py:56** If VERTICAL_LAYOUT.json is an empty object, the layout loop does nothing and the script reports REPRODUCED without checking any layout.
  - evidence: `ref_plans = json.load(open(os.path.join(REF, "VERTICAL_LAYOUT.json")))`
  - fix: Assert ref_plans is non-empty or compare against expected clip IDs.
  - raised by deepseek:F4; agree: deepseek, qwen27b
- **[high] pipeline/check_preview_reference.py:33** Fail-open via silent zip truncation: if pin['segments'] has fewer entries than segs (e.g. a truncated or corrupted PIN), zip() stops early and the remaining segments are never verified. The script then reports 'REPRODUCED' (exit 0) despite having skipped real segments. There is no length assertion between segs and pin['segments'].
  - evidence: `for (label, seg), ps in zip(segs, pin["segments"]):`
  - fix: Before the loop, add: if len(segs) != len(pin['segments']): bad.append(f'segment count mismatch: edl has {len(segs)}, pin has {len(pin["segments"])}'); and skip the loop (or raise). This ensures a missing PIN segment is a hard failure, not a silent pass.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] pipeline/check_preview_reference.py:53** Layout completeness is not verified: the loop iterates only over keys present in VERTICAL_LAYOUT.json. If the reference file omits a clip (or the EDL gains a clip after the reference was frozen), that clip's layout is never checked and the script still reports REPRODUCED. The set of clips in ref_plans is never cross-checked against the set of clips in the EDL/cuts.
  - evidence: `for cid, rp in ref_plans.items():`
  - fix: After loading ref_plans, verify that the set of clip IDs in ref_plans matches the set of clip labels derived from the EDL (excluding 'hook' if it has no layout). If any expected clip is missing from ref_plans, append to bad and continue; if any unexpected clip is present, also flag it.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F2 [medium] TOL_S = 0.0101 allows cut differences up to 10.1 ms, which is more than the documented one 10 ms hop; a cut changed by 10.1 ms passes. (agree: 1)
- deepseek:F3 [medium] Layout boundaries are rounded to 2 decimal places (10 ms) before comparison, so changes smaller than 5 ms can be hidden and pass. (agree: 1)
- deepseek:F5 [high] Segments are paired by position via zip, not by label/video_id; if pin['segments'] order differs from the EDL order, the script compares the wrong segment's lock and cut, which can produce false passes or false failures. (agree: 1)
- qwen27b:F3 [low] If the selection lock mismatches, the script appends to bad and continues, but it never verifies that the reference cut for that segment is internally consistent (e.g. cut_in < cut_out). More practically: the 'continue' means the cut comparison is skipped, which is correct, but the label is still printed in the final summary as 'CHANGED' without indicating that the cut was not checked, which could mask a secondary cut regression in the same segment. (agree: 0)

## Added in cross-examination (not voted on)
- qwen27b: [low] Unhandled KeyError if a segment label from the EDL has no corresponding entry in cuts_final.json. The script crashes with a traceback instead of reporting a clean 'CHANGED' or 'MISSING' status, which makes it harder to diagnose in CI.
