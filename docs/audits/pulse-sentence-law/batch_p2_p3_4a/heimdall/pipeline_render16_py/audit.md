# Heimdall audit

**Question:** Batched audit (orchestrator note 05:40 ET) of two commits. (1) Phase 2: the 9:16 is a per-shot speaker-centred reframe measured with SCRFD (vertical_layout.classify; screen / single / stack2 / stack3 / uncertain by fixed face-area rules), safe frame (whole 16:9) only for screen/uncertain and flagged; new gate G4s (labels vs re-measured picture; safe frame iff labelled screen/uncertain, by band correlation); the unchanged gate_g4 applied per shot. (2) Phase 3 + 4a: transitions only between different channels over measured non-speech (xfade offset corrected for ffmpeg 4.4.2), G18 word-for-word (edges vs the selection lock + identity vs the source span, canonicalised), the verification pack, telegram.deliver_run captions, the one-command runner. Verify from the diff: (a) no existing gate changed what it accepts (gate_g4, G14, G12/G15, G16/G17 untouched; G4s and G18 are new and only add failures); (b) the frozen v2f render path is untouched when TRANSITIONS.json is absent and layouts are hand overrides (Law 22); (c) transitions never overlap speech, never occur at the open or into the credits, and picture and sound stay frame-locked; (d) the safe frame appears only for screen/uncertain shots and is always named in the 9:16 caption; (e) the caption says HOLD FOR APPROVAL only when every row of both formats is PASS and the pack is complete, the only send path is the approval chat, and credentials are never printed; (f) the runner holds a lock, logs, and never touches other tmux sessions; (g) tests are meaningful, not vacuous. Only state what you can verify from the diff; if uncertain, say so. (this chunk: pipeline/render16.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0075
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/render16.py:393** The new shoutout_start override uses next() without a default, so it raises StopIteration and crashes the render if the transition timeline contains no segment labelled 'shoutout'. The original code left shoutout_start at its initial value when no shoutout was found, so this is a regression.
  - evidence: `shoutout_start = next(e["start"] for e in timeline if e["label"] == "shoutout")`
  - fix: Use a default: shoutout_start = next((e["start"] for e in timeline if e["label"] == "shoutout"), shoutout_start)
  - raised by deepseek:F1; agree: deepseek, qwen27b
- **[high] pipeline/render16.py:392** StopIteration crash when the transition timeline omits a 'shoutout' entry. The original code iterated segments and simply left shoutout_start at its initial value if 'shoutout' was absent; the new code uses next() on a generator expression with no default, so a timeline that lacks a 'shoutout' label (e.g. a run with no shoutout segment) will raise an unhandled StopIteration and abort the render.
  - evidence: `shoutout_start = next(e["start"] for e in timeline if e["label"] == "shoutout")`
  - fix: Provide a default matching the original no-op behaviour: shoutout_start = next((e["start"] for e in timeline if e["label"] == "shoutout"), 0.0)  (or the same initial value the pre-loop code used when 'shoutout' was not found).
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F2 [low] No structural validation of TRANSITIONS.json before indexing. A file that exists but is missing any of the required keys ('channels', 'lead_tail', 'style') will raise a bare KeyError with no context about which run/segment triggered it, making diagnosis harder in a batch pipeline. (agree: 1)

## Added in cross-examination (not voted on)
- none
