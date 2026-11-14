# Heimdall audit

**Question:** Batch 52 = ORCHESTRATOR ORDER '01:55' item 1, on the word-pass worker (pipeline/word_pass_worker.py, merged in batch 51). The order, verbatim: "Make the word-pass worker take rows by published_at newest first inside a 10 hour window before anything older (ranked by score inside that window, L-u exclusions applied before spending GPU time)."
The change:
- is_fresh(row, now) is true when published_at is an ISO time with an offset inside [now - 10 h, now].
- pick() fills up to 40 in three passes, each in the adapter's rank order (score):
  (1) fresh rows, at most 7 per channel;
  (2) the remaining fresh rows, uncapped, so a capped channel's fresh rows still come before any older row;
  (3) older rows, capped.
- Done moments and videos with a full-video record are skipped in every pass.
- The cycle report adds fresh_h, fresh_rows, fresh_picked and fresh_channels.
- The L-u exclusions are the adapter's own (best_unused_moments drops hard flags, altcoin and speaker changes before the worker sees a row, so before any GPU time).
Measured now: the adapter returns 1340 rows, 78 of them fresh (10 h) from 7 videos. A cycle now picks 40 fresh from 7 channels.
FIND:
- an older row picked while a fresh row remains;
- a fresh row skipped or picked twice;
- a time-zone or parse error making a row fresh or stale wrongly (no offset, future times);
- the report counts wrong;
- tests that do not test what they claim.
Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0009
## Consensus findings (majority of panel agrees)
- **[low] pipeline/word_pass_worker.py:118** is_fresh treats a naive published_at as stale even when it is the store's default ISO format, so rows written without an offset are never fresh and lose the 10 h priority; the test only asserts the behavior, it does not catch a wrong classification
  - evidence: `return pub.tzinfo is not None and now - dt.timedelta(hours=hours) <= pub <= now`
  - fix: If the ledger can emit naive timestamps, assume UTC (pub = pub.replace(tzinfo=dt.timezone.utc)) or document the invariant; otherwise keep as is.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- glm: [low] is_fresh catches only ValueError, not TypeError; if published_at is None, str(None)='None' raises ValueError (ok), but if row.get returns a non-ISO type the fromisoformat may raise other errors in some Python versions — minor. More concrete: the second test's fresh rows all share one channel, so pass 1 caps at 7 and pass 2 adds 3; but pass 2 (uncapped) also increments per, so pass 3's cap counting is consistent — no bug. However the first test's expected picks include 'm000' (older) while fresh rows remain? No: only 3 fresh + edge fresh m200 = 4 fresh, per_cycle=5, so 5th pick is older m000 — correct. Real missed item: fresh_picked counts picks that are fresh, but pass 3 could pick a row whose published_at equals now boundary... none. Actual missed: report's fresh_rows/fresh_channels computed from all rows, not from non-done/non-full rows, so counts include rows that will never be picked — report slightly overstated.
