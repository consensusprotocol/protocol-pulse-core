# Heimdall audit

**Question:** ONE batch for orchestrator DEC-12 + the 15:30 order + PBX laws (2026-11-11). Kept from the audited pre-B/C diff: (a) G9 floor = v2f measured tail luma minus the MEASURED re-encode spread (14.2857 / 14.7315), (d) has_chyron channels never supply a clip, (e) G14 speech sampling with retake and >= 3 conclusive samples, (f) G3b three readings with 1.5 s context. NEW: (B / law L-a) the sign-off generator gets the credits card's channel list (hook first, then clips; it used to omit the hook's channel), VO stems keyed by hash(text, voice id, model), the voice id is no longer printed, stage_voice HOLDs before render unless the script names exactly the credited channels, gate G20 SIGNOFF_NAMES_ALL transcribes the rendered sign-off (credited names may match fuzzily, other registry names only exactly and outside credited spans). (C / laws L-b, L-c; DEC-12b AMENDED) accepted_cut's fades come from edge_fades: a fade never overlaps an edge word, it sits in the run of frames within 3 dB of the cut point's level next to the cut, 83 ms when that fits, down to 10 ms; G17c edge_word_fidelity compares each edge word (+ decay) of the prepared clip with the unfaded source (<= 1 dB per 10 ms frame, +-2 hop alignment) and is part of the G17 row; L-c in stage_gates: a dissenting G3b reading needs G17c + G16 to pass for that edge (else HOLD), a G3c head / tail failure is overruled only when G17c + G16 prove that edge. (L-d) pipeline/check_preview_reference.py + regression.sh step 6 re-derive the protected preview's locks, cuts and layout. Must-fails: the preview's sign-off (DataDash missing) and its Natalie tail ('rally' under the 83 ms fade). Find real defects only: fail-open paths, a fade that can still cover a word, a G17c window that can miss the word, L-c overruling something it should not, G20 false matches, Law 22 risk (v2f's run_isolated path). (this chunk: pipeline/run_fresh.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0208
## Consensus findings (majority of panel agrees)
- **[high] pipeline/run_fresh.py:0** L-c ignores G3b dissents when last_found is false, so a dissenting reading without last_found does not trigger the required HOLD.
  - evidence: `dissent = [e["segment"] for e in g3b if isinstance(e, dict) and e.get("dissent") and e.get("last_found")]`
  - fix: Remove the last_found condition or handle such dissents separately so any dissent requires G17c+G16 proof.
  - raised by deepseek:F3; agree: deepseek, qwen27b
- **[medium] pipeline/run_fresh.py:962** L-c G3c overruling sets the entire G3c_acoustic_tail row to PASS when all captured head/tail failures are proved, but the `failed` list only collects entries where `tail_ok is False` or `head_ok is False`. If G3c's overall FAIL verdict is caused by any additional criterion beyond those two fields (e.g. a global level/duration check, a `None`-inconclusive that the gate treats as fail), the row is still unconditionally upgraded to PASS, silently discarding the non-head/tail failure. The law states only 'a G3c head / tail failure is overruled'—not the whole gate.
  - evidence: `failed = [(e["segment"], side) for e in g3c if isinstance(e, dict)
              for side, key in (("out", "tail_ok"), ("in", "head_ok")) if e.get(key) is False]
    if rows[fmt].get("G3c_acoustic_tai`
  - fix: Before overruling, verify that the G3c FAIL is attributable solely to the head/tail entries in `failed`. For example, re-derive the G3c verdict from the table excluding the proved edges and confirm it would be PASS; only then upgrade the row. Alternatively, set the row to a qualified status (e.g. 'PASS(L-c: edges proved; other checks: <status>)') that preserves visibility of any residual non-head/tail failure.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [high] L-c overrule uses the global g16_ok flag instead of a per-edge G16 proof, so a G3c edge failure can be overruled even when G16 did not prove that specific edge. (agree: 1)
- deepseek:F2 [medium] Law L-a check compares only sets, ignoring the required order (hook first, then clips). A sign-off script naming the same channels in a different order passes. (agree: 0)
- qwen27b:F2 [low] _edge_proved uses the global boolean g16_ok rather than a per-edge G16 result. The law requires 'G16 to pass for that edge'. A G16 failure on any unrelated edge makes _edge_proved return False for every edge, producing spurious HOLDs on G3b dissents and blocking valid G3c overrulings. This is fail-closed (safe direction) but can stall the pipeline indefinitely on a single bad edge. (agree: 1)

## Added in cross-examination (not voted on)
- none
