# Heimdall audit

**Question:** Batch 73 CYCLE 2 = LAW L-ab SPOTLIGHT, the render side (cycle 1: no consensus findings; the diff is unchanged; read cycle 1's question for the ruling and the agreed contract). Verify these specific points on the diff, each with the quoted code:
(1) MEDLEY / STORY UNCHANGED: every new branch is guarded by package_type == 'moments' AND package_shape == 'spotlight' (EDL) or moments_package.shape == 'spotlight' (pin); build_edl adds package_shape / first_comment ONLY for a spotlight; signoff.MEDLEY_REGISTERS is the old three register lines character for character, so a medley's prompt is byte-identical; vo.py's fallback keeps the old list for 2+ channels; telegram keeps HOLD_OK, the credits line and the 60-70 / 8-12 / 12-20 deviations for non-spotlights; G5 keeps 58-72 / 60-70 when the EDL is missing, unreadable or not a spotlight.
(2) THE SPOTLIGHT CANNOT PASS WITH: two segments (validate_schema), any clip (moments_vo, R5, R11), a bridge (moments_vo, R11), a non-null intro in the pin's edl_vo, a closing line > 12 words (moments_vo, R4's intro cap, R11) or without closing_value / closing_fidelity / closing_context exactly PASS and replayed False, a missing / FAIL / replayed required row, an empty first_comment, or a moments_bridge record.
(3) NO FAIL-OPEN: a rule or gate that passes a spotlight because nothing was measured; note editorial LAW 1 and LAW 4 are passed for a spotlight BY DESIGN (the ruling: 'only the taste rules that assume a medley change'), while L0, LAW 2 (a closing line needs a job) and LAW 3 (a concrete takeaway) still bind.
(4) Any crash path: an EDL without package_shape, a hook without duration, a non-dict gates row.
Only state what you can verify from the diff. Reply with the JSON verdict; at most 3 findings; if nothing, say so.

**Panel:** qwen27b, glm  |  **Cost:** $0.0007
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
