# Heimdall audit

**Question:** Batch 52 cycle 2 (verification). Cycle 1 C1 implemented: is_fresh mirrors the ledger's _aware ('Z' = UTC, no offset = not measured, TypeError caught); tests added.

Batch 52 = ORCHESTRATOR ORDER '01:55' item 1, on the word-pass worker (pipeline/word_pass_worker.py, merged in batch 51). The order, verbatim: "Make the word-pass worker take rows by published_at newest first inside a 10 hour window before anything older (ranked by score inside that window, L-u exclusions applied before spending GPU time)."
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
FIND: anything still open; an older row before a fresh one; a wrong fresh / stale call; a test that does not test what it claims. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0013
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] Pass 2 (uncapped fresh) can starve other channels: if one channel has ≥ per_cycle fresh rows, they fill the whole cycle and pass 3 never runs, so older rows from other channels are skipped entirely that cycle — arguably intended by the order, but it also means the per_channel cap in pass 1 is pointless when a single channel floods fresh rows. (agree: 1)
- glm:F2 [low] is_fresh treats a published_at exactly equal to now as fresh (inclusive), and a future published_at within the window check is excluded only by pub <= now — consistent with the test, so this is just noting the inclusive boundary is asserted, not a defect. No wrong fresh/stale call found; the no-offset→not-fresh and 'Z'→UTC cases are both tested against the ledger's _aware semantics. (agree: 1)

## Added in cross-examination (not voted on)
- glm: [low] Test 1's fresh rows are ranked LAST by score yet are picked FIRST, but the test never exercises the per-channel cap in pass 1: all 3 fresh rows come from different implied channels, so pass 1's cap (7/channel) is never hit and the pass-1/pass-2 split is untested for the multi-channel case.
