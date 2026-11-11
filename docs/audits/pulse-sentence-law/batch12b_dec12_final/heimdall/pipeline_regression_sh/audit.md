# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/regression.sh)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0028
## Consensus findings (majority of panel agrees)
- **[high] pipeline/regression.sh:93** Fail-open: the new protected-reference gate only fails when check_preview_reference.py exits exactly 1. Any other non-zero exit (e.g. 2 for a parse/reference error, 127 for missing python3, or 128+ for a signal) is ignored, so the regression can pass even though the preview check did not succeed.
  - evidence: `if [ "$PREVIEW_RC" -eq 1 ]; then`
  - fix: Change the condition to `if [ "$PREVIEW_RC" -ne 0 ]; then` (and optionally treat signal exits as failures) so every non-zero exit from check_preview_reference.py fails the regression.
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/regression.sh:93** Fail-open: the return-code check only catches exit code 1. If check_preview_reference.py exits with any other non-zero code (2 for a different assertion, 127 if python3 is missing, 139 for a segfault, 137 if OOM-killed), the script falls through to 'REGRESSION COMPLETE' and exits 0, silently passing the regression gate.
  - evidence: `if [ "$PREVIEW_RC" -eq 1 ]; then`
  - fix: Change the guard to catch every non-zero exit: `if [ "$PREVIEW_RC" -ne 0 ]; then` (and optionally print the actual code in the message for diagnostics).
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
