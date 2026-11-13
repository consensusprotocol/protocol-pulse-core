# Heimdall audit

**Question:** Batch 40 cycle 3 = LAW L-y VOICEOVER IS MINIMAL (orchestrator 2026-11-12 '20:30'; PBX: too much voiceover, keep one line at the end unless needed to stick content together). The whole R11 change, reworked after the packager stated its shape. A package of type 'moments' plays hook clip -> clips back to back -> ONE takeaway line after the LAST clip -> sign-off. L-y 2: a bridge between two clips is the exception, at most ONE per video, used only when the packager judges and a blind coherence check confirms a viewer could not follow the jump; the package records why. The renderer's only line between the hook and clip 1 is the EDL 'intro' slot; lines after clip k are vo.bridges[{text, after_clip}]. New edl_rules.rule_r11 (run by validate_edl before any cut): at most one line after the last clip; at most ONE line before the takeaway (intro slot or after clip k < last), and that line passes only if the EDL's moments_bridge (the package's record, copied by pinned.build_edl) has text exactly equal to it (after strip), a non-empty 'why', a non-empty 'confirmed_by' (string, list or dict), and the line is <= 20 words; two or more lines before the takeaway fail even with a record; a record with no bridge line fails; a non-text line, a line whose after_clip is not a clip index, malformed vo / bridges / clip indexes fail. Story-type and untyped EDLs (protected references) are unchanged. Cycle 1 findings (F1 clip indexes, F2 bridges shape / slots, F3 whitespace intro) are in.
FIND: any way a second VO line before the takeaway, an unrecorded or unconfirmed bridge, an old-style intro, or a second takeaway passes for a moments package; a mismatch between what R11 counts and what the renderer / vo.py actually voice (e.g. whitespace, a non-string text); story / untyped regressions; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek, glm  |  **Cost:** $0.0256
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [medium] The fail-closed condition 'a non-text line' is enforced only for lines in the `before` list (intro / bridge before the takeaway) but not for closing (takeaway) lines. A bridge whose `after_clip == max(idx)` and whose `text` is not a string (e.g. None, 123, a list) is counted as a valid closing line with no text-type check, so R11 passes it to the renderer which will attempt to voice a non-string. (agree: 1)
- qwen27b:F2 [low] No test exercises a non-string or whitespace-only `text` on a closing (takeaway) bridge, so the gap in F1 is untested. The `test_a_line_without_a_clip_slot_fails` and `test_an_intro_or_a_bridge_without_the_record_fails` tests cover non-text for before-lines only. (agree: 1)

## Added in cross-examination (not voted on)
- none
