# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/test_edge_words.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0206
## Consensus findings (majority of panel agrees)
- **[high] pipeline/test_edge_words.py:89** G17c window can miss the edge word: i0/i1 are chosen by word midpoint rather than by overlap with the cut, so a word straddling cut_in or cut_out can be excluded from the plan and never checked.
  - evidence: `i0 = next(i for i, w in enumerate(words) if mid(w) > c["cut_in"])
i1 = max(i for i, w in enumerate(words) if mid(w) < c["cut_out"])`
  - fix: Select the first word whose end is after cut_in and the last word whose start is before cut_out, e.g. i0 = next(i for i,w in enumerate(words) if w["end"] > c["cut_in"]); i1 = max(i for i,w in enumerate(words) if w["start"] < c["cut_out"]).
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[medium] pipeline/test_edge_words.py:94** Fail-open: if det is empty, the loop body never runs, bad stays empty, and assertEqual(bad, []) passes without checking any edge.
  - evidence: `for side, v in det.items():
    if (c["clip_id"], side) in self.RECORDED:
        self.assertFalse(v["ok"], (c["clip_id"], side, v))       # the legacy edge keeps failing
    elif not v["ok"]:
       `
  - fix: Assert that det contains both "in" and "out" keys before iterating, e.g. self.assertEqual(set(det), {"in", "out"}).
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[medium] pipeline/test_edge_words.py:95** Recorded legacy edges are not enforced if det omits that side: the test only asserts failure when the side is present, so a missing recorded edge silently passes.
  - evidence: `if (c["clip_id"], side) in self.RECORDED:
    self.assertFalse(v["ok"], (c["clip_id"], side, v))       # the legacy edge keeps failing`
  - fix: Assert that each recorded (clip_id, side) is present in det before checking its ok value.
  - raised by deepseek:F4; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F2 [high] Fail-open: the overall ok result from edge_word_fidelity is assigned but never checked; the test only inspects det items, so an overall failure not reflected in det can pass. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [high] Fail-open: if the v2f cuts list is empty, the loop never runs, `bad` remains empty, and the test passes without checking any edge.
- deepseek: [medium] The L-b fade test only checks that the fade starts after the word end; it does not verify the fade sits in the run of frames within 3 dB of the cut point's level, so a fade placed in a silent gap after the word would pass.
- qwen27b: [medium] Law 22 risk: the test imports and calls run_isolated.prerender_clips (v2f's isolated rendering path) to produce the QA clip. The audit explicitly flags this path as a risk. If run_isolated has side effects (GPU state, global config, or a different fade implementation than the L-b law specifies), the test may verify against the wrong render, or the import itself may alter the environment for subsequent tests in the same process.
