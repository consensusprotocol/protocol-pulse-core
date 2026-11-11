# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/vo.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0087
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/vo.py:63** Fail-open reuse: any file larger than 44 bytes is treated as a valid cached stem, so a truncated or corrupted WAV (e.g., from an interrupted write) will be reused, producing bad audio. The hash key only ensures the filename matches the intended text/voice/model, not that the file is complete or valid.
  - evidence: `if os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:`
  - fix: Validate the cached WAV (e.g., parse header, check duration, or write to a temp file and atomically rename only on success) before reusing; do not rely on file size alone.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[medium] pipeline/vo.py:125** Sign-off fallback crashes with IndexError when channels_list is empty. The new code path calls credit_channels(edl) which may return an empty list (e.g., EDL with no hook and no clips, or a malformed EDL). The fallback then evaluates channels_list[0] in the else-branch, raising an unhandled IndexError that aborts the entire VO generation.
  - evidence: `names = (f"{', '.join(channels_list[:-1])}, and {channels_list[-1]}" if len(channels_list) > 1
             else channels_list[0])`
  - fix: Guard against an empty list before building the names string, e.g.:
if not channels_list:
    signoff_text = "Clips today. Go follow them for more. Links are below."
else:
    names = (f"{', '.join(channels_list[:-1])}, and {channels_list[-1]}" if len(channels_list) > 1
             else channels_list[0])
    signoff_text = [...][int(hashlib.sha256(segment_id.encode()).hexdigest(), 16) % 3]
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[low] pipeline/vo.py:63** The reuse guard only checks file size > 44 bytes (minimum WAV header). A truncated or corrupt file of 45+ bytes (e.g., a partial write from a prior crash) will be silently reused as a valid stem, producing silent or garbage audio in the final mix with no error surfaced.
  - evidence: `if os.path.exists(wav_path) and os.path.getsize(wav_path) > 44:
            print(f"  Reusing: {stem_name} (same text, voice and model)")
            return {"stem_wav": os.path.basename(wav_path), "v`
  - fix: Validate the WAV header (RIFF/WAVE magic, non-zero data chunk size) before reusing, or at minimum check that the file size exceeds 44 + a small minimum payload (e.g., > 100 bytes) to reject header-only files.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
