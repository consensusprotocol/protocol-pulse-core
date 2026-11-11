# Heimdall audit

**Question:** Batched audit (orchestrator note 05:40 ET) of two commits. (1) Phase 2: the 9:16 is a per-shot speaker-centred reframe measured with SCRFD (vertical_layout.classify; screen / single / stack2 / stack3 / uncertain by fixed face-area rules), safe frame (whole 16:9) only for screen/uncertain and flagged; new gate G4s (labels vs re-measured picture; safe frame iff labelled screen/uncertain, by band correlation); the unchanged gate_g4 applied per shot. (2) Phase 3 + 4a: transitions only between different channels over measured non-speech (xfade offset corrected for ffmpeg 4.4.2), G18 word-for-word (edges vs the selection lock + identity vs the source span, canonicalised), the verification pack, telegram.deliver_run captions, the one-command runner. Verify from the diff: (a) no existing gate changed what it accepts (gate_g4, G14, G12/G15, G16/G17 untouched; G4s and G18 are new and only add failures); (b) the frozen v2f render path is untouched when TRANSITIONS.json is absent and layouts are hand overrides (Law 22); (c) transitions never overlap speech, never occur at the open or into the credits, and picture and sound stay frame-locked; (d) the safe frame appears only for screen/uncertain shots and is always named in the 9:16 caption; (e) the caption says HOLD FOR APPROVAL only when every row of both formats is PASS and the pack is complete, the only send path is the approval chat, and credentials are never printed; (f) the runner holds a lock, logs, and never touches other tmux sessions; (g) tests are meaningful, not vacuous. Only state what you can verify from the diff; if uncertain, say so. (this chunk: pipeline/verify_pack.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0113
## Consensus findings (majority of panel agrees)
- **[high] pipeline/verify_pack.py:55** In the dissolve (overlap) case, the 'last' frame timestamp uses a["end"] - 1/FPS, which is the END of the dissolve region (where segment a is nearly fully faded out). The correct timestamp for the last clean frame of a before the dissolve begins is b["start"] - 1/FPS. As written, the 'last' verification frame captures a blended/near-transparent frame rather than the last fully-opaque frame of segment a, defeating the purpose of the boundary check.
  - evidence: `pts = [("last", b["start"] - 1.0 / FPS if overlap <= 1e-3 else a["end"] - 1.0 / FPS),
       ("first", (b["start"] if overlap <= 1e-3 else a["end"]) + 0.5 / FPS)]`
  - fix: Change the overlap-case 'last' timestamp to b["start"] - 1.0 / FPS so it captures the last frame before the dissolve begins: pts = [("last", b["start"] - 1.0 / FPS), ("first", a["end"] + 0.5 / FPS)] for the overlap branch (the non-overlap branch already correctly uses b["start"] - 1.0 / FPS).
  - raised by qwen27b:F1; agree: deepseek, qwen27b
- **[medium] pipeline/verify_pack.py:19** _frame uses check=True with no exception handling. If ffmpeg fails for any single frame (timestamp beyond actual video duration, corrupt file, I/O error), a CalledProcessError or TimeoutExpired propagates and crashes the entire build() call. No VERIFICATION.json is produced and no partial pack is written. A single bad boundary timestamp kills the whole verification pack.
  - evidence: `subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video, "-frames:v", "1",
                    "-q:v", "3", out], check=True, timeout=60)
    return out if os.path.exis`
  - fix: Wrap the subprocess.run in a try/except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) and return None on failure, so a single bad frame is recorded as missing rather than aborting the entire pack.
  - raised by qwen27b:F2; agree: deepseek, qwen27b
- **[low] pipeline/verify_pack.py:73** The 'complete' flag only verifies G18 words and the existence of sheet image files. It does not check that the G12/G15 credit rows (stored in pack["credits"]["G12"][fmt] and pack["credits"]["G15"][fmt]) are non-None. A pack can be marked complete=True while the credits gate data is absent from GATE_REPORT.json, giving a false sense of verification coverage.
  - evidence: `pack["complete"] = bool(pack["words"]) and all(p and os.path.exists(p) for p in files)`
  - fix: Extend the completeness check to also require that G12 and G15 values are present for both formats, e.g.: and all(pack["credits"]["G12"][f] is not None and pack["credits"]["G15"][f] is not None for f in ("16x9", "9x16")).
  - raised by qwen27b:F3; agree: deepseek, qwen27b

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- deepseek: [medium] The complete flag checks only sheet images, not the individual frame files. A sheet can be created from a subset of frames if some _frame calls return None, so complete can be True while individual verification frames are missing.
