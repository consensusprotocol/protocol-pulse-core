# Heimdall audit

**Question:** Batch 49 = THE SPEAKERS IN THE DELIVERY TEXTS (orchestrator order 2026-11-13 '00:05' item 3: "Every pin carries, per segment, the SPEAKER'S NAME where the source's title/description names the guest ... with its evidence ... PBX wants to tag the right people when he posts ... Unknown speaker = say unknown, never guess.").
The builder seals a per-segment record in the pin: speaker = {name or "unknown", role, line, basis, why, people: [{name, role, line}], measured}. The pin rides into the run's PINNED_DECISION.json.
telegram.speaker_lines(run_dir) renders, per segment:
- "speaker <name>" with its role and evidence line, or "speaker unknown" with its why;
- then each person the source names, with its line, or "the source names nobody";
- each quoted line is cut to 140 characters with '...', each why to 120;
- the whole block is capped at SPEAKERS_MAX = 1200 characters, ending "- (truncated)";
- it returns [] for a pin without records.

review_texts (the review drop note) and publish_kit (the pass path's kit, before FIRST COMMENT) add the block under SPEAKERS_HEAD. Nothing else changes: no gate, no authorisation, no send logic.
FIND:
- any way the block invents or upgrades a speaker, e.g. prints a name for an unknown record, or turns 'people' into the speaker;
- a record that crashes the note or the kit and so blocks a delivery;
- a note pushed past TEXT_MAX;
- a mis-numbered segment;
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0008
## Consensus findings (majority of panel agrees)
- **[low] pipeline/telegram.py:361** Known-speaker line indexes sp['role'] and sp['line'] directly; a record with name but no 'role'/'line' keys (only missing via .get elsewhere) would KeyError — but the guard uses sp.get('role')/sp.get('line') so it's actually safe; the real nit: a known speaker whose 'line' key exists but is non-str (e.g. number) is coerced by _cut(str), fine. No crash found; noting only that the truncated block's final line '- (truncated)' is not itself counted precisely, but the 14-char reserve covers it.
  - evidence: `text = text[:SPEAKERS_MAX - 14].rsplit("\n", 1)[0] + "\n- (truncated)"`
  - fix: None needed; reserve covers the suffix.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- glm: [low] A known speaker whose 'line' key exists but is non-str (e.g. a number) is coerced by _cut(str), fine — but a known speaker with role/line keys present yet falsy (empty string) silently drops the parenthetical, which is cosmetic only. More substantively: the 'people' list is rendered even for a known speaker, so a source that names the speaker in people[] prints the same name twice (once as speaker, once as 'named by the source') — this is faithful to the pin, not an invention, so it is not a defect. No real defect found beyond the noted cosmetic duplication.
