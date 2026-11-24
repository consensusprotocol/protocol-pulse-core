# Heimdall audit

**Question:** pp-selectid (Protocol Pulse clip-video builder), RULINGS 152 (1) and 154 (2), uncommitted (diff below). THE RULINGS: "the writer chain: every answering Heimdall family (qwen, deepseek, gpt-oss, gemma, minimax; glm only if probed), 120 s each, then Grok. Probe before the build." and "In the never-empty pass the hook bar is soft; an unrated opener opens flagged." THE CODE: proof_ly.WRITERS (the writer chain), package.WRITER_DEADLINE_S = 120 (every writer call passes it as deadline_s), proof_ledger.writer_probe (probes every Heimdall writer at once, marks the ones that do not answer down for the run; Grok never probed; a replayed run probes nothing). package.hook_unrated (line 1898): the plain reason a hook has no rating ON the calibrated bar (no valid calibration, no rating, or a rating by another back-end than the bar's rater); hook_own (line 1917) lets such a hook pass, flagged and marked "unrated", ONLY when the never-empty pass marked it (hook_bar_soft); the stage 2b block marks at most HOOK_SOFT_MAX (2, line 1111) openers: first those its own rater rated under the bar (hook_bar_under, line 1883, unchanged), then unrated ones. _can_open (line 1989, unchanged) reads hook_own's "passes"; _live_bar (line 1809) is the calibration.
CHECK, quoting the code: can an unrated or off-bar hook open in the CLEAN pass or without its flag; can more than HOOK_SOFT_MAX hooks be marked; can a hook that cannot open for another reason (G17a onset, the STAND_ALONE hook rule, its frames) open now; can hook_own's new branch break a caller that reads its "rating" as an int; can the probe mark a family down that answered, keep one up that did not, run against recordings, or block the build past its timeout; does every writer call keep the 120 s deadline. Report only what the code shows.

**Panel:** qwen27b, gptoss, gemma  |  **Cost:** $0.0477
## Consensus findings (majority of panel agrees)
- **[high] pipeline/package.py:1917** A hook that stage 2b marks soft because hook_unrated() is truthy can still open unflagged when its cached rating passes the bar (ok true), because hook_own only computes un when not ok; the code's own comment/log says such openers open flagged.
  - evidence: `    under = (hook_order([m for mid, m in openers.items() if mid in rated and hook_bar_under(m)]) +    # RULING 137
             hook_order([m for mid, m in openers.items() if hook_unrated(m)]))[:HOOK_`
  - fix: In hook_own, compute the unrated reason whenever the moment is marked soft and no under-bar flag applies, not only when ok is false; e.g. `un = hook_unrated(m) if m.get("hook_bar_soft") and flag is None else None`, and set `flagged`/`unrated` when `un` is not None even if `ok` is true.
  - raised by qwen27b:F1; agree: qwen27b, gemma

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- qwen27b: [medium] hooks_txt assumes m['hook_rating'] exists, but RULING 154 (2) can offer an opener with no hook_rating; hook_unrated and hook_own defensively use (m or {}).get('hook_rating') or {}, so formatting such an offered hook can raise KeyError or AttributeError.
