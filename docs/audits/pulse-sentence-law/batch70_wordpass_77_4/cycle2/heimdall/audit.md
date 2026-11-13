# Heimdall audit

**Question:** Batch 70 CYCLE 2 (cycle 1: no consensus findings; the diff is unchanged) = RULING 77.4 (orchestrator 2026-11-13 '18:40'), verbatim: "the word-pass worker's tiers become 'last 6 h, then 6-12 h', nothing older (ruling 77.4)". Context: rulings 76 / 77, a clip is usable only while its source is within 12 h of the render clock.
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

**Panel:** qwen27b, glm  |  **Cost:** $0.0039
## Consensus findings (majority of panel agrees)
- **[low] pipeline/word_pass_worker.py:158** Docstring says 'FRESH_H-DAY_H (6-12) hours' but the second tier is rows where not is_fresh(r,now,FRESH_H) and is_fresh(r,now,DAY_H), i.e. (6,12] hours old — the 12 h boundary is inclusive in the second tier, so '6-12' is accurate; no defect, noted only as verified. The 12 h+1 s row (m203, 2026-11-12T17:59:59) and 18 h/48 h rows are excluded by the removed third pass, and the 12 h inclusive row (m202, 18:00:00) is kept — matching ruling 77.4. The five-channel test's uncapped pass (ids[35:] = m007,m008,m009,m017,m018) confirms capped-then-uncapped within a tier is retained, and the 6th channel's rows (m100-m102) land at ids[35:38] before any uncapped row, as claimed. is_fresh is untouched: future (07:00), offset-less ('2026-11-13T01:00:00') and 'Z' cases still behave as before. The cycle-test stamp (now-1h) keeps cycle rows in the 6 h tier under the wall clock. No path picks a >12 h row: the only rows taken are t10 (is_fresh 6 h) and t24 (not 6 h, is_fresh 12 h), and the older capped pass (take([...not is_fresh(r,now,DAY_H)], True)) is deleted. No change outside tiers/horizon: PER_CYCLE, MIN_CHANNELS, PAD_S, BATCH, FETCH_WORKERS, PER_CHANNEL, OWNER, window(), and the take() mechanics are untouched in the diff.
  - evidence: `t24 = [r for r in rows if not is_fresh(r, now, FRESH_H) and is_fresh(r, now, DAY_H)]; take(t24, True); take(t24, False); return out, len(per)  # ruling 77.4: a row older than DAY_H (12 h) is never wor`
  - fix: none required
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
