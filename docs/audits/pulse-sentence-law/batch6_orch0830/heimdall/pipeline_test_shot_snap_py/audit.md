# Heimdall audit

**Question:** Protocol Pulse news-video pipeline (no publishing). Changes: (1) a replay harness: run_fresh.main's tail (prepare, layout, render, gates, verify, verdict) moved into run_tail(run, cuts, start), and replay.py runs it on a COPY of an existing run dir (sources hard-linked, outputs removed); (2) a stand-alone + topic rule checked at validate for every run and at auto selection on final windows: a hook may not open on a pronoun, conjunction or reply fragment; a clip may open on a conjunction only if the clip scorer affirms it stands alone; every segment names the story subject (Bitcoin for a Bitcoin story) or completes the previous segment's claim with a back-reference and a figure; (3) the word-diff canonicaliser keeps a decimal as ONE token and maps 'one point three' / 'five and a half' to it (before, '5.5' became '5 5' and a repeat-collapser merged it to '5', so 5.5% and 5% compared equal); (4) shot_snap: a hard shot change after the last word (or before the first word) of a prepared clip is replaced by a hold of the speaker's shot, audio copied unchanged, frame count unchanged; (5) the wrapper sends Telegram only when every gate passed. Find real bugs: a check that can pass when it should fail, a replay that differs from production, a snap that moves audio or changes timing, a canonicalisation that hides a real word difference. Only state what you can verify from the diff. (this chunk: pipeline/test_shot_snap.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0170
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/test_shot_snap.py:74** The luma check only verifies that all frames have similar brightness, not that the held shot is the speaker's shot. A snap that incorrectly holds the non-speaker shot (blue) uniformly would also pass.
  - evidence: `self.assertLess(float(np.ptp(lum)), 3.0)               # every frame now shows the red (speaker's) shot`
  - fix: Assert the mean luma of the first frame matches the red shot's luma (or check the actual color) to ensure the speaker's shot is held.
  - raised by deepseek:F1; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F2 [high] The audio check compares only raw PCM samples, not their timing relative to the video. A snap that moves the audio (e.g., changes its start offset) without altering the samples would still produce the same PCM hash and pass. (agree: 1)
- deepseek:F3 [medium] The test checks the frame count but not the video frame rate or duration. A snap that changes the frame rate while keeping the same number of frames would alter the video timing and pass. (agree: 1)

## Added in cross-examination (not voted on)
- none
