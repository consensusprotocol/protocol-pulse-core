# Heimdall audit

**Question:** Cycle 3 of a release-gate change: verify ONE fix. Cycle 1 found that attest() / authorise() in pipeline/release_auth.py crashed (AttributeError / TypeError) on a malformed but digest-valid GATE_REPORT.json detail: V1[fmt]["boundaries"] or ["letterbox_per_shot"] a truthy non-dict, a model's "rows" a non-dict, G9[fmt] a non-dict; and seg_name() crashed when the EDL's "clips" was not a list. The diff guards each reader with isinstance checks. Intended semantics (unchanged by the fix): V1's credits row ("credits_round_and_match") is HARD (speaker credit, ruling 137 (2)): a V1 that did not pass holds when ANY model did not affirm that row (said no, left it out, or V1 gave no answer); V1's other rows, "boundaries" (next shot before the cut) and "letterbox_per_shot" are SOFT flags; absent "boundaries" / "letterbox_per_shot" means not asked (no flag); anything other than {"ok": True} there is a doubt (a flag).

FACTS (unchanged code): verify_pack writes V1[fmt] = {"ok", "error"?, "per_model": {model: {"rows": {row: {"answer", "why", "ok"}}}}, "boundaries": {"ok", "cuts"}?, "letterbox_per_shot": {"ok", "shots"}?}. _v1_doubts returns None for "no answer" (the caller holds), else the list of doubted names.

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If the fix holds, answer PASS with no findings.

CHECKS:
C1. Can any malformed V1 / G9 / EDL value still raise in _v1_doubts, say(), seg_name() or who()?
C2. Did the fix change a verdict for a WELL-FORMED report: can a credits "no" / missing answer now pass, or a well-formed V1 with all rows ok and boundaries {"ok": True} now flag?
C3. Does anything else change behaviour?

**Panel:** gptoss  |  **Cost:** $0.0026
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
