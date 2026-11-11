# Heimdall audit

**Question:** Protocol Pulse news-video pipeline (no publishing). Changes: (1) a replay harness: run_fresh.main's tail (prepare, layout, render, gates, verify, verdict) moved into run_tail(run, cuts, start), and replay.py runs it on a COPY of an existing run dir (sources hard-linked, outputs removed); (2) a stand-alone + topic rule checked at validate for every run and at auto selection on final windows: a hook may not open on a pronoun, conjunction or reply fragment; a clip may open on a conjunction only if the clip scorer affirms it stands alone; every segment names the story subject (Bitcoin for a Bitcoin story) or completes the previous segment's claim with a back-reference and a figure; (3) the word-diff canonicaliser keeps a decimal as ONE token and maps 'one point three' / 'five and a half' to it (before, '5.5' became '5 5' and a repeat-collapser merged it to '5', so 5.5% and 5% compared equal); (4) shot_snap: a hard shot change after the last word (or before the first word) of a prepared clip is replaced by a hold of the speaker's shot, audio copied unchanged, frame count unchanged; (5) the wrapper sends Telegram only when every gate passed. Find real bugs: a check that can pass when it should fail, a replay that differs from production, a snap that moves audio or changes timing, a canonicalisation that hides a real word difference. Only state what you can verify from the diff. (this chunk: pipeline/editorial_select.py)

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0095
## Consensus findings (majority of panel agrees)
- **[low] pipeline/editorial_select.py:1168** The 'no hook' reason string is now inaccurate: hooks can be excluded by the stand-alone filter even when their clip_score meets the threshold, yet the message still claims no hook scored high enough. This misleads debugging of why a run is non-producible.
  - evidence: `"reason": (f"no hook passage scored >= {HOOK_MIN_SCORE}" +`
  - fix: Update the reason to reflect both possible causes, e.g. f"no hook passage scored >= {HOOK_MIN_SCORE} and passed the stand-alone check" or build the message conditionally based on whether any hook met the score but failed stand-alone.
  - raised by qwen27b:F1; agree: deepseek, qwen27b

## Raised but not agreed
- deepseek:F1 [high] The stand-alone opener screen is applied only to hooks. For clips, _stand_alone_ok skips SA.opener entirely and only calls SA.topical, so a clip that opens on a pronoun, conjunction, or reply fragment can pass auto selection even when the clip scorer has not affirmed it stands alone. This violates the rule that a clip may open on a conjunction only if the clip scorer affirms it stands alone, and more generally allows disallowed clip openers. (agree: 1)

## Added in cross-examination (not voted on)
- none
