# Heimdall audit

**Question:** Batched audit (orchestrator note 05:40 ET) of two commits. (1) Phase 2: the 9:16 is a per-shot speaker-centred reframe measured with SCRFD (vertical_layout.classify; screen / single / stack2 / stack3 / uncertain by fixed face-area rules), safe frame (whole 16:9) only for screen/uncertain and flagged; new gate G4s (labels vs re-measured picture; safe frame iff labelled screen/uncertain, by band correlation); the unchanged gate_g4 applied per shot. (2) Phase 3 + 4a: transitions only between different channels over measured non-speech (xfade offset corrected for ffmpeg 4.4.2), G18 word-for-word (edges vs the selection lock + identity vs the source span, canonicalised), the verification pack, telegram.deliver_run captions, the one-command runner. Verify from the diff: (a) no existing gate changed what it accepts (gate_g4, G14, G12/G15, G16/G17 untouched; G4s and G18 are new and only add failures); (b) the frozen v2f render path is untouched when TRANSITIONS.json is absent and layouts are hand overrides (Law 22); (c) transitions never overlap speech, never occur at the open or into the credits, and picture and sound stay frame-locked; (d) the safe frame appears only for screen/uncertain shots and is always named in the 9:16 caption; (e) the caption says HOLD FOR APPROVAL only when every row of both formats is PASS and the pack is complete, the only send path is the approval chat, and credentials are never printed; (f) the runner holds a lock, logs, and never touches other tmux sessions; (g) tests are meaningful, not vacuous. Only state what you can verify from the diff; if uncertain, say so. (this chunk: pipeline/render_vertical.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0161
## Consensus findings (majority of panel agrees)
- **[high] pipeline/render_vertical.py:939** StopIteration crash when no 'shoutout' segment exists and timeline is not None. The original loop left shoutout_start at its initial value if no 'shoutout' was found, but the new code unconditionally calls next() on a generator that may yield nothing.
  - evidence: `if timeline is not None:
        shoutout_start = next(e["start"] for e in timeline if e["label"] == "shoutout")`
  - fix: Replace with a safe lookup: shoutout_start = next((e["start"] for e in timeline if e["label"] == "shoutout"), shoutout_start) so it falls back to the value set by the preceding loop (or its initial default) when no shoutout entry exists.
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] pipeline/render_vertical.py:779** The fail-closed RuntimeError now applies to ALL reframe layouts (grid, single, letterbox, fixed_crop), not just the new 'auto' path. Previously a reframe failure logged a warning and fell back to the 16:9 source clip; now any single-shot reframe failure aborts the entire vertical render. This changes the acceptance behaviour of the existing render path.
  - evidence: `if not ok:
            # M12 fail closed (2026-11-11): never drop a 16:9 clip into the 9:16 timeline
            raise RuntimeError(f"STOP: vertical reframe failed for {clip_id} (layout {crop_rect})")`
  - fix: If the intent is to fail-closed only for the new 'auto' layout, scope the raise to that branch (e.g., check layout == 'auto' before raising) and retain the warning+fallback for the pre-existing layouts. If the policy change is intentional for all layouts, document it as a Law 22 / v2f exception in the commit message so auditors can confirm it is a deliberate gate change.
  - raised by qwen27b:F2; agree: deepseek, qwen27b

## Raised but not agreed
- qwen27b:F3 [medium] The trim frame boundaries are computed with plan['fps'] but the output is forced to the module constant FPS via '-r str(FPS)'. Audio is copied without re-timing ('-c:a copy'). If plan['fps'] != FPS (e.g. 29.97 source vs 30 target), the video is resampled to a different duration while the audio stream retains its original length, causing progressive A/V drift across the segment. (agree: 1)

## Added in cross-examination (not voted on)
- none
