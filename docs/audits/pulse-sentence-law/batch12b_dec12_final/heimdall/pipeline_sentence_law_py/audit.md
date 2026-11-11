# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/sentence_law.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0250
## Consensus findings (majority of panel agrees)
- **[critical] pipeline/sentence_law.py:0** edge_word_bounds misidentifies the word boundary when the cut point is already inside a word: the run of frames within 3 dB of the cut point's level extends through the word, so onset/end are set far beyond the actual word. edge_fades then applies a long fade that overlaps the word.
  - evidence: `        lim = float(d[0]) + FLOOR_PLUS_DB
        k = 0
        while k + 1 < len(d) and d[k + 1] <= lim:
            k += 1
        out["onset"], out["lim_in"] = float(t[k]) + HOP_S, round(lim, 2)`
  - fix: Detect when the run reaches the window edge (k == len(d)-1 for onset, k == 0 for end) or when the cut point level is above a room-tone threshold; in that case reject the cut or set the fade to 0 so it cannot cover the word.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[critical] pipeline/sentence_law.py:0** edge_word_fidelity fails open when the word is not above the gap level: if keep is all False, diff is empty, worst is set to 0.0, and ok becomes True. This happens when the cut point is inside the word (lim is word level + 3 dB), so the faded word is never checked.
  - evidence: `        keep = ds > wb["lim_in" if side == "in" else "lim_out"]       # the word, not the gap it sits next to
        ...
            diff = np.abs(dc[:n] - ds[:n])[keep[:n]]
            worst = float`
  - fix: If keep is all False, treat the edge word as not measurable and return ok=False instead of worst=0.0. Alternatively, use a fixed threshold based on room tone rather than the cut point level.
  - raised by deepseek:F2; agree: deepseek, qwen27b
- **[high] pipeline/sentence_law.py:0** edge_fades enforces a minimum fade of 10 ms even when the available gap is smaller, so the fade can still overlap the edge word.
  - evidence: `    fi = VALLEY_FADE_S if wb["onset"] is None else min(VALLEY_FADE_S, max(FADE_MIN_S, wb["onset"] - cut_in))
    fo = VALLEY_FADE_S if wb["end"] is None else min(VALLEY_FADE_S, max(FADE_MIN_S, cut_out`
  - fix: If the available gap is less than FADE_MIN_S, either reject the cut or set the fade to the gap length (which may be 0) so it never overlaps the word.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[high] pipeline/sentence_law.py:0** edge_word_fidelity's window can miss the word because it uses the faulty bounds from edge_word_bounds. If b is set before the actual word end, the window [b-0.3, b] does not cover the faded word, so the check passes despite the fade covering the word.
  - evidence: `        t0, t1 = (a, min(a + 0.3, cut_out)) if side == "in" else (max(b - 0.3, cut_in), b)`
  - fix: Use correct word bounds (see F1) or extend the window to the cut point so the fade region is always included in the comparison.
  - raised by deepseek:F4; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [high] edge_fades defaults to the full 83 ms fade when edge_word_bounds cannot measure the edge word (onset/end is None), so a fade can still cover the word on unmeasurable edges.
- qwen27b: [medium] edge_word_bounds onset uses + HOP_S but end does not, creating a 10 ms asymmetry: the fade-in can start up to 10 ms later than the true word onset (safe), but the fade-out can end up to 10 ms earlier than the true word end (the last 10 ms of the word's decay is excluded from the 'gap' and treated as word, which is conservative for the fade but means G17c's out-side window [b−0.3, b] may start 10 ms late, potentially excluding the first 10 ms of the word's decay from the fidelity check).
