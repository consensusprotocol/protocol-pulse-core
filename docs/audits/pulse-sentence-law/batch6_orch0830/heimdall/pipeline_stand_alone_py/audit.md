# Heimdall audit

**Question:** Protocol Pulse news-video pipeline (no publishing). Changes: (1) a replay harness: run_fresh.main's tail (prepare, layout, render, gates, verify, verdict) moved into run_tail(run, cuts, start), and replay.py runs it on a COPY of an existing run dir (sources hard-linked, outputs removed); (2) a stand-alone + topic rule checked at validate for every run and at auto selection on final windows: a hook may not open on a pronoun, conjunction or reply fragment; a clip may open on a conjunction only if the clip scorer affirms it stands alone; every segment names the story subject (Bitcoin for a Bitcoin story) or completes the previous segment's claim with a back-reference and a figure; (3) the word-diff canonicaliser keeps a decimal as ONE token and maps 'one point three' / 'five and a half' to it (before, '5.5' became '5 5' and a repeat-collapser merged it to '5', so 5.5% and 5% compared equal); (4) shot_snap: a hard shot change after the last word (or before the first word) of a prepared clip is replaced by a hold of the speaker's shot, audio copied unchanged, frame count unchanged; (5) the wrapper sends Telegram only when every gate passed. Find real bugs: a check that can pass when it should fail, a replay that differs from production, a snap that moves audio or changes timing, a canonicalisation that hides a real word difference. Only state what you can verify from the diff. (this chunk: pipeline/stand_alone.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0151
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
