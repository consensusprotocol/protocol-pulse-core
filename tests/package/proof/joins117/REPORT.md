# RULING 117 (4): THE JOIN TABLE AND THE SEARCH, REPLAYED ON BUILDS 8-12

Measured 2026-11-15T21:48:09+00:00 UTC; the join table asked of Grok (production's package.join_table, cached in JOIN_CACHE.json); the search free. Spent $0.1285 (vendor-reported, SPEND_J117.json).

| build | angle | hook | table pairs | not followable | line-ups found |
|---|---|---|---|---|---|
| 8 | 1 | cca27461 | 49 | 21 | 0 |
| 8 | 2 | 7ef148a1 | 49 | 18 | 0 |
| 9 | 1 | cca27461 | 49 | 31 | 0 |
| 9 | 2 | 7ef148a1 | 49 | 19 | 0 |
| 10 | 1 | cca27461 | 49 | 31 | 0 |
| 10 | 2 | 7ef148a1 | 49 | 19 | 0 |
| 11 | 1 | 9cc94b73 | 49 | 35 | 0 |
| 11 | 2 | 7ef148a1 | 49 | 27 | 0 |
| 12 | 1 | 9cc94b73 | 49 | 35 | 0 |
| 12 | 2 | 7ef148a1 | 49 | 27 | 0 |

## Reading

- ZERO of the 10 angles reached a line-up. The joins are NOT what stops them: for each angle, 129-527 orders keep at most one flagged join by the table, but only 0-4 orders pass the line-up rules at all, and those few carry two or more flagged joins.
- The rules fail on ONE SEGMENT PER CHANNEL (1,052-1,088 of 1,092 orders an angle): the table's 8 moments were the hook, the writer's 3, then the cleared pool BY RANK SCORE, and the pool is 14 moments over 4 channels, 7 of them Simply Bitcoin, the hooks' own channel and video (Scott Melker 4, Digital Asset News 2, Bitcoin Magazine 1). Half the table was moments that can never stand beside their hook. In builds 8-10, angle 1's hook also fails today's calibrated hook bar.
- The fix follows the order's own words ('the moments that can be in a line-up'): never the hook's own video, clip-eligible only, one moment of each channel not yet in the set first, then the rest by rank score. For builds 11-12 that is the hook, Bitcoin Magazine 1, Scott Melker 4, Digital Asset News 2: all 8 usable.
- AGREEMENT (3): on the 32 joins both the table and these builds' verdicts judged, they agree on 22 (68 %).
- Ruling 113 (6)'s 61 failed line-ups: 0 are still inside 12 h (all expired).
