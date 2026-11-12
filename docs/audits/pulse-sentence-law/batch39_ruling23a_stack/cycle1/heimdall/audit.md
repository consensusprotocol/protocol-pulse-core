# Heimdall audit

**Question:** Batch 39 = RULING 23 (a) (orchestrator 2026-11-12 '13:18'): V1 (two vision models answer a checklist about a video's contact sheet; any 'no' fails the row) asked 'every talking-head segment shows its speaker centred in the frame' of a 9:16 segment laid out as a STACK (two speakers in two panels, one above the other), and one model answered no ('framed off-centre'). Now: verify_pack.stack_note names every 9:16 segment whose vertical-layout shots are a stack ('9:16 STACK clip_02 (Natalie Brunell): stack2: two speakers in two panels, one above the other; each face is centred in its own panel') in the layout note the vision prompt already carries; the checklist item vertical_speaker_centred adds: for a segment the layout note names as a STACK, answer about EACH face: each face centred in ITS OWN panel and no panel edge cutting through a face; the single-speaker question applies only to single-speaker layouts. Tests (both Heimdall vision models, the Nov 12 re-run's 9:16 frames): the untouched stack frame passes; the stack with its top face pushed into the panel edge fails; a single-speaker frame shifted off-centre fails.
FIND: any way a cropped face or an off-centre single speaker now passes; a non-stack segment getting the stack wording; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, deepseek  |  **Cost:** $0.0099
## Consensus findings (majority of panel agrees)
- **[high] pipeline/verify_pack.py:125** stack_note labels a segment as STACK if ANY vertical-layout shot class starts with 'stack', so a mixed segment containing both stack and single-speaker shots gets the stack wording. The checklist then says the single-speaker question applies only to single-speaker layouts, so an off-centre single speaker in that mixed segment can pass.
  - evidence: `kinds = sorted({sh.get("class") for sh in ((seg.get("vertical_layout") or {}).get("shots") or []) if str(sh.get("class", "")).startswith("stack")})`
  - fix: Require every vertical-layout shot in the segment to be a stack before naming the segment as STACK, or emit per-shot notes so single-speaker shots are still checked.
  - raised by deepseek:F1; agree: qwen27b, deepseek
- **[high] pipeline/verify_pack.py:129** stack_note asserts 'each face is centred in its own panel' as a fact in the layout note, pre-answering the checklist item that is supposed to verify centring and edge cutting. A cropped or off-centre face can pass because the note already claims it is centred.
  - evidence: `f"one above the other; each face is centred in its own panel")`
  - fix: Remove the assertion from stack_note; only describe the layout (two panels, one above the other) and let the checklist ask the model to verify centring and edge cutting.
  - raised by deepseek:F2; agree: qwen27b, deepseek

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
