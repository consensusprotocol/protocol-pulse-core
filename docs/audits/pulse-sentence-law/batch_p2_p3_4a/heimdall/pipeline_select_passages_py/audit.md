# Heimdall audit

**Question:** Batched audit (orchestrator note 05:40 ET) of two commits. (1) Phase 2: the 9:16 is a per-shot speaker-centred reframe measured with SCRFD (vertical_layout.classify; screen / single / stack2 / stack3 / uncertain by fixed face-area rules), safe frame (whole 16:9) only for screen/uncertain and flagged; new gate G4s (labels vs re-measured picture; safe frame iff labelled screen/uncertain, by band correlation); the unchanged gate_g4 applied per shot. (2) Phase 3 + 4a: transitions only between different channels over measured non-speech (xfade offset corrected for ffmpeg 4.4.2), G18 word-for-word (edges vs the selection lock + identity vs the source span, canonicalised), the verification pack, telegram.deliver_run captions, the one-command runner. Verify from the diff: (a) no existing gate changed what it accepts (gate_g4, G14, G12/G15, G16/G17 untouched; G4s and G18 are new and only add failures); (b) the frozen v2f render path is untouched when TRANSITIONS.json is absent and layouts are hand overrides (Law 22); (c) transitions never overlap speech, never occur at the open or into the credits, and picture and sound stay frame-locked; (d) the safe frame appears only for screen/uncertain shots and is always named in the 9:16 caption; (e) the caption says HOLD FOR APPROVAL only when every row of both formats is PASS and the pack is complete, the only send path is the approval chat, and credentials are never printed; (f) the runner holds a lock, logs, and never touches other tmux sessions; (g) tests are meaningful, not vacuous. Only state what you can verify from the diff; if uncertain, say so. (this chunk: pipeline/select_passages.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0056
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- deepseek:F1 [high] build_vertical_overrides now unconditionally sets layout 'auto' for every segment, ignoring the registry and approved hand layouts. Previously approved channels received 'crop' from their hand table; now they get 'auto', so the frozen v2f render path is altered when TRANSITIONS.json is absent and hand overrides exist (Law 22). (agree: 1)
- qwen27b:F1 [low] The `registry` parameter is accepted but never read; the old code that loaded `channels.json` and built `approved_channels` is removed. This is explicitly documented as intentional ('kept for call compatibility'), so it is not a bug, but any caller that previously relied on passing a custom `registry` to influence layout selection will now silently get 'auto' for every segment with no warning or deprecation notice. (agree: 0)

## Added in cross-examination (not voted on)
- none
