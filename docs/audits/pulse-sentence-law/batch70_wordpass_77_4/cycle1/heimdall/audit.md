# Heimdall audit

**Question:** Batch 70 = RULING 77.4 (orchestrator 2026-11-13 '18:40'), verbatim: "the word-pass worker's tiers become 'last 6 h, then 6-12 h', nothing older (ruling 77.4)". Context: rulings 76 / 77, a clip is usable only while its source is within 12 h of the render clock.
Before: pipeline/word_pass_worker.py read the ingest ledger 72 h back (HORIZON_H 72) and picked in tiers: the last 10 h (FRESH_H), then the last 24 h (DAY_H), each tier first capped (PER_CHANNEL a channel) and then uncapped; and then OLDER rows, capped.
The change:
- FRESH_H, DAY_H = 6, 12; HORIZON_H = 12 (the ledger is read 12 h back);
- pick(): the 'older' pass is removed, so a row older than 12 h is never picked. The two tiers keep their capped-then-uncapped passes, and is_fresh is unchanged ([now - hours, now], inclusive, 'Z' = UTC, no offset never fresh).
- Tests (test_word_pass_worker.py, 27 passed):
  - two ruling-77.4 tier tests: 6 h then 6-12 h; 12 h and 6 h inclusive; 12 h + 1 s, 18 h and 48 h never. Both FAIL on the old worker.
  - The fixture's default published_at moves from > 24 h old to 3 h before the fixed NOW.
  - The cycle tests stamp their rows 1 h before the wall clock: W.cycle() runs on it.
  - The five-channel cap test now states the tier behaviour: 35 capped + 5 of the rest = 40, and a 6th channel's rows come before any uncapped row.
FIND: a path where a row older than 12 h (by published_at, the render-clock rule) is still picked or decoded; a fresh row now wrongly excluded (the boundaries); a change to anything but the tiers and the horizon; a test that does not test what it claims. Only state what you can verify from the diff. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0012
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- glm:F1 [low] The docstring still cites orders '01:55'/'02:46' as the tier source while the tiers now come from ruling 77.4; the comment block above the constants already attributes the change to ruling 77.4, so the docstring's provenance is stale, not the behaviour. (agree: 1)

## Added in cross-examination (not voted on)
- none
