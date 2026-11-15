# RULING 117 (4), AGAIN: THE JOIN TABLE ON ITS FIXED SET, REPLAYED ON BUILDS 8-12

Measured 2026-11-15T22:13:51+00:00 UTC on code 6195a712 (audit 20261115_1700): each angle's table asked of production's
package.join_moments (the moments that CAN be in its line-up: never the hook's own video, clip-eligible, a new
channel first) and package.join_table (Grok, cached in JOIN_CACHE.json); the search free. Spent $0.0248 (vendor-
reported; SPEND_J117.json now $0.1533). "Orders" = the hook, then 2-4 of the table's other moments, every order;
"pass the rules" = lineup_ok with L-y 4's supply exception (the search's second pass).

| build | angle | hook | table moments | pairs | not followable | orders | pass the rules | fewest flagged | line-ups found |
|---|---|---|---|---|---|---|---|---|---|
| 8 | 1 | cca27461 | 6 | 25 | 7 | 200 | 0 (the hook cannot open) | - | 0 |
| 8 | 2 | 7ef148a1 | 6 | 25 | 9 | 200 | 2 | 2 | 0 |
| 9 | 1 | cca27461 | 6 | 25 | 7 | 200 | 0 (the hook cannot open) | - | 0 |
| 9 | 2 | 7ef148a1 | 6 | 25 | 9 | 200 | 2 | 2 | 0 |
| 10 | 1 | cca27461 | 6 | 25 | 7 | 200 | 0 (the hook cannot open) | - | 0 |
| 10 | 2 | 7ef148a1 | 6 | 25 | 9 | 200 | 2 | 2 | 0 |
| 11 | 1 | 9cc94b73 | 8 | 49 | 23 | 1092 | 4 | 2 | 0 |
| 11 | 2 | 7ef148a1 | 8 | 49 | 24 | 1092 | 14 | 1 | 1 |
| 12 | 1 | 9cc94b73 | 8 | 49 | 23 | 1092 | 4 | 2 | 0 |
| 12 | 2 | 7ef148a1 | 8 | 49 | 24 | 1092 | 14 | 1 | 1 |

## Reading

- The fixed set holds only moments that can stand beside the hook: 6 moments in builds 8-10, 8 in builds 11-12. The
  supply is still small. Scott Melker's 4 moments are ONE video (vQ3c_lU4NZ4), and Digital Asset News's 2 are ONE
  video (Sps9le2Z5RI), both clips under 8 s. So any line-up is the hook plus at most one clip each of Bitcoin
  Magazine, Scott Melker and Digital Asset News, with DAN's clip last. Most orders (1,016 of 1,092) still fail ONE
  SEGMENT PER CHANNEL, because they put two moments of one video together. CORRECTION to the 16:54 STATE line and
  joins117/REPORT.md ("all 8 usable"): all 8 pass the filter, but at most 4 of them (the hook and 3 clips) fit in one line-up.
- ONE line-up in 10 angles passes by the table: builds 11 and 12, angle 2, 7ef148a1 > 9a3597d4 > b6be0c41 >
  6df120f5, with one flagged join (the hook > 9a3597d4, "abrupt market condition shift": the law's one bridge).
- Neither build judged that line-up. Build 12's own clips-alone verdict flagged one of its joins that the table
  passes (9a3597d4 > b6be0c41). By those verdicts it carries two flagged joins, so: by the table 1, by the builds'
  own verdicts 0.
- Builds 8-10: angle 1's hook (cca27461) fails today's calibrated hook bar. Angle 2's two orders that pass the rules
  carry 2 flagged joins each.
- AGREEMENT (3): 28 of the 38 joins the table and these builds' verdicts both judged (74 %; counted once per build and
  angle, so a pair repeats). The 10 disagreements are 4 distinct pairs. In 3 of them the table says followable and a
  verdict said not (9cc94b73 > 9a3597d4, 3233deb3 > 9a3597d4, 9a3597d4 > b6be0c41). In 1 it is the other way
  (3233deb3 > 94a613f3). The table asks each pair alone; the verdict reads the whole line-up.
- Ruling 113 (6)'s 61 failed line-ups: 0 are still inside 12 h.
