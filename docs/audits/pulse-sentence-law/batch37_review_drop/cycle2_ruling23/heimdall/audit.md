# Heimdall audit

**Question:** Batch 37 cycle 2 = RULING 23 (orchestrator 2026-11-12 '13:18') in the REVIEW DROP (telegram.review_drop: an engineering review of a run that is NOT a pass, labelled 'REVIEW ONLY - NOT A PASS - not for publishing'; the release path is unchanged). V1 (the visual checklist answered by two vision models) used to make a run never droppable. Now a failing V1 row is droppable ONLY when every failing V1 item (checklist rows per model, letterbox shots, boundary pairs, from VERIFY/VERIFICATION.json) is a SPLIT: at least one model 'yes' and every other model an explicit 'no'; both 'no', a missing / other answer, fewer than two models, an unreadable file, or a failing credits_round_and_match while the measured ring geometry row G15_credits is not PASS: refused (nothing sent). A droppable split is quoted in the note: the item, each model's answer and reason. Also: the forbidden-wording check is now case-insensitive (cycle 1 consensus F2).
FIND: any way a V1 failure on which both models said no, or a ring-geometry failure, is dropped; any way a split is dropped without being quoted; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0176
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- qwen27b:F1 [high] A V1 row that is not PASS in GATE_REPORT but has no failing items in VERIFICATION.json (all per-model rows ok=True, no failing letterbox/boundary entries) and visual.ok is True is returned as droppable with an empty description. No split is quoted, violating the ruling that 'A droppable split is quoted in the note: the item, each model's answer and reason.' The guard only refuses when failing is empty AND vis.ok is not True; when vis.ok IS True it falls through to return (True, ''). (agree: 1)
- qwen27b:F2 [medium] Letterbox shots and boundary pairs are stored with ok hardcoded to False for every model, so the split check (which requires at least one model with ok=True) can never recognise a valid split on these items. The ruling explicitly lists 'letterbox shots, boundary pairs' as V1 items eligible for split-dropping. A genuine one-yes-one-no split on a letterbox shot is incorrectly refused, and more critically, the per-model ok status from the verification data is discarded, making the item's answers untrustworthy for any downstream logic. (agree: 1)

## Added in cross-examination (not voted on)
- deepseek: [high] Missing per-item answers are not detected: if one model lacks a row and the other's ok is True, the item is not in failing, so a V1 failure with a missing answer can be dropped.
- deepseek: [high] Split check uses ok boolean for yes instead of verifying answer is 'yes'; a model with ok=True but answer 'no' is counted as yes, allowing a both-no item to be dropped.
- deepseek: [medium] Reason is omitted from the quoted split when empty; ruling requires each model's answer and reason.
