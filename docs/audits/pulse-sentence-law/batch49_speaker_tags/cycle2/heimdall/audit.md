# Heimdall audit

**Question:** Batch 49 cycle 2 (verification). Cycle 1: no consensus defect (one nit, no fix needed).

Batch 49 = THE SPEAKERS IN THE DELIVERY TEXTS (orchestrator order 2026-11-13 '00:05' item 3: "Every pin carries, per segment, the SPEAKER'S NAME where the source's title/description names the guest ... with its evidence ... PBX wants to tag the right people when he posts ... Unknown speaker = say unknown, never guess.").
The builder seals a per-segment record in the pin: speaker = {name or "unknown", role, line, basis, why, people: [{name, role, line}], measured}. The pin rides into the run's PINNED_DECISION.json.
telegram.speaker_lines(run_dir) renders, per segment:
- "speaker <name>" with its role and evidence line, or "speaker unknown" with its why;
- then each person the source names, with its line, or "the source names nobody";
- each quoted line is cut to 140 characters with '...', each why to 120;
- the whole block is capped at SPEAKERS_MAX = 1200 characters, ending "- (truncated)";
- it returns [] for a pin without records.

review_texts (the review drop note) and publish_kit (the pass path's kit, before FIRST COMMENT) add the block under SPEAKERS_HEAD. Nothing else changes: no gate, no authorisation, no send logic.
FIND: anything a delivery could crash on, a speaker invented or upgraded, a note past TEXT_MAX, a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0006
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] A speaker record with a non-string 'why' (e.g. a number or list) crashes the note build; the builder's contract says why is a string, but the reader otherwise tolerates junk (isinstance checks on seg/people, str() on name). (agree: 1)

## Added in cross-examination (not voted on)
- none
