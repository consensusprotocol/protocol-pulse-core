# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/test_g14_sampling.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0115
## Consensus findings (majority of panel agrees)
- **[low] pipeline/test_g14_sampling.py:27** skipUnless guard checks only three files (out/segment.mp4, qa/g14_manifest_16x9.json, cuts_final.json) but setUpClass also reads transcripts/{vid}.json and sources/{vid}.mp4 for every clip in cuts_final.json. If the run directory is partially present (the three NEEDED files exist but transcripts/ or sources/ are missing), the test is NOT skipped and crashes in setUpClass with an unhelpful FileNotFoundError instead of a clean skip.
  - evidence: `NEEDED = ("out/segment.mp4", "qa/g14_manifest_16x9.json", "cuts_final.json")

@unittest.skipUnless(all(os.path.exists(os.path.join(RUN, p)) for p in NEEDED), "Nov 11 replay run not on this machine")`
  - fix: Extend NEEDED (or add a second skipUnless / try-except in setUpClass) to also verify that every transcripts/{vid}.json and sources/{vid}.mp4 referenced by cuts_final.json exists before the test body runs.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [low] aevalsrc=0|0 generates a 2-channel (stereo) silence source. If the audio track in out/segment.mp4 were mono, the concat filter would receive mismatched channel layouts ([a1] mono, [z] stereo, [a2] mono) and ffmpeg would abort, causing the test to error rather than assert. In practice the rendered segment is stereo, so this is latent, but it makes the test fragile if ever pointed at a mono-audio fixture. (agree: 0)

## Added in cross-examination (not voted on)
- none
