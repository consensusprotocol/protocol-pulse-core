# BACKTEST SUPPLY REPORT: did a line-up that passes our rules exist, and did the selector find it?

Generated 2026-11-12 10:24 UTC by `tools/backtest_oracle.py report` (branch pp-backtest). Order pp-backtest, 2026-11-12 (session pipeline_pp_backtest).

**Sample size: 10 saved runs on 5 UTC dates. This is a small sample: every number below is a count of these runs, stated with its raw count; no rate in this report generalises beyond them, and no confidence interval is claimed.**

## 1. Per run

| run (UTC stamp) | started (ET) | rows shown / exported | oracle | proposed / pass the code checks / pass the blind judge | availability | as-run selector | loss stage as run | cold backtest @394ffe5a | replay at HEAD | layout column |
|---|---|---|---|---|---|---|---|---|---|---|
| 20261106_213852 | Nov 06 16:38 ET | 5263 / 5384 | OK LINEUPS | 2 / 2 / 1 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | COVERAGE | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives |
| 20261107_065702 | Nov 07 01:57 ET | 3657 / 3751 | OK LINEUPS | 2 / 1 / 1 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | WINDOWS | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives |
| 20261107_080503 | Nov 07 03:05 ET | 4978 / 5097 | OK LINEUPS | 3 / 2 / 2 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | COVERAGE | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L2 survives; L3 survives |
| 20261110_093150 | Nov 10 04:31 ET | 2945 / 3018 | OK LINEUPS | 2 / 2 / 2 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | COVERAGE | COVERAGE | NOT_RERUN: no cached gemma reply for thi at clip_quality; loss LABEL | L1 DIES; L2 survives |
| 20261111_190259 | Nov 11 14:03 ET | 3581 / 3670 | OK LINEUPS | 1 / 1 / 1 | AVAILABLE | crashed | NOT_REACHED | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives |
| 20261111_192645 | Nov 11 14:26 ET | 3647 / 3738 | OK LINEUPS | 2 / 2 / 2 | AVAILABLE | stopped at derive | NOT_REACHED | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives; L2 DIES |
| 20261111_213954 | Nov 11 16:39 ET | 3867 / 3964 | OK LINEUPS | 2 / 2 / 2 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | CLUSTER_FORMATION, CURRENTNESS | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives; L2 DIES |
| 20261112_001448 | Nov 11 19:14 ET | 3667 / 3764 | OK LINEUPS | 1 / 1 / 1 | AVAILABLE | stopped at adjudicate | NOT_REACHED | no record | NOT_RERUN: no cached gemma reply for thi at embedded; loss NOT_REACHED | L1 survives |
| 20261112_013452 | Nov 11 20:34 ET | 3664 / 3751 | OK LINEUPS | 2 / 2 / 2 | AVAILABLE | stopped at coverage | NOT_REACHED | NOT_REACHED | NOT_RERUN: no cached gemma reply for thi at word_transcripts_done; loss NOT_REACHED | L1 survives; L2 survives |
| 20261112_050611 | Nov 12 00:06 ET | 3773 / 3862 | OK LINEUPS | 2 / 2 / 2 | AVAILABLE | HOLD: no candidate is producible (see candidates[].decision) | COVERAGE | no record | NOT_RERUN: no cached gemma reply for thi at emergent; loss NOT_REACHED | L1 survives; L2 survives |

## 2. Overall (raw counts beside every rate)

- Availability (a line-up the oracle proposed, the deterministic checks pass and the blind judge says passes our rules): 10 of 10 (100 %) measured runs; not measured: 0 (none).
- Accepted line-ups in total: 16.
- Selector recall, as_run: 0 of 6 (0 %) available runs whose record completed a selection reached an equivalent line-up (same development by a shared sentence in >= 2 channels' segments); 4 run(s) not measured (the record crashed, stopped or hit NOT_RERUN before selecting).
- Selector recall, cold_backtest_394ffe5a: 0 of 1 (0 %) available runs whose record completed a selection reached an equivalent line-up (same development by a shared sentence in >= 2 channels' segments); 1 run(s) not measured (the record crashed, stopped or hit NOT_RERUN before selecting).
- Selector recall, replay_head: not measured: no record completed a selection; 10 run(s) not measured (the record crashed, stopped or hit NOT_RERUN before selecting).
- Selector precision, as_run: selector-accepted line-ups = 0: not measured (the selector accepted no line-up on any saved run in this record).
- Selector precision, cold_backtest_394ffe5a: selector-accepted line-ups = 0: not measured (the selector accepted no line-up on any saved run in this record).
- Selector precision, replay_head: selector-accepted line-ups = 0: not measured (the selector accepted no line-up on any saved run in this record).
- Layout column: 3 of 16 (19 %) accepted line-ups stop passing our rules once segments from layout-ineligible channels (has_chyron: Bitcoin Magazine, CoinDesk) are removed.

## 3. Where the line-ups that pass our rules were lost (count of accepted line-ups per stage)

| stage | as_run | cold_backtest_394ffe5a | replay_head |
|---|---|---|---|
| CLUSTER_FORMATION | 1 | 0 | 0 |
| LABEL | 0 | 0 | 2 |
| CURRENTNESS | 1 | 0 | 0 |
| COVERAGE | 7 | 2 | 0 |
| WINDOWS | 1 | 0 | 0 |
| NOT_REACHED | 6 | 2 | 14 |

- as_run: 1 of its CLUSTER_FORMATION count: "cluster membership = the label's excerpts only (pre-DEC-13 record)".
- as_run: 3 of its NOT_REACHED count: "no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)".
- as_run: 1 of its NOT_REACHED count: "no clusters in this record (the run crashed or stopped before clustering)".
- as_run: 2 of its NOT_REACHED count: "pre-DEC-13 record, incomplete: cluster membership not recorded and candidates left undecided".
- cold_backtest_394ffe5a: 2 of its NOT_REACHED count: "no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)".
- replay_head: 6 of its NOT_REACHED count: "no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)".

Line-ups whose statements no single cluster held from two of their channels (decided CLUSTER_FORMATION in a complete record, or NOT_REACHED where an incomplete record stopped): how far the furthest one-channel cluster holding some of them got (its own stage):

| furthest one-channel cluster | as_run | cold_backtest_394ffe5a | replay_head |
|---|---|---|---|
| LABEL | 1 | 0 | 1 |
| COVERAGE | 2 | 2 | 1 |
| WINDOWS | 1 | 0 | 0 |
| held one channel's, no decision recorded (NOT_REACHED) | 0 | 0 | 4 |

## 4. Every accepted line-up, its sentences and its trace

### 20261106_213852 L1: Bitcoin was dragged down by the November 5 tech-stock sell-off, falling about 5% to roughly $76,000.
Channels Blockware Solutions, Swan Bitcoin; content 47.49 s (runtime ~61.0 s); blind judge: passes our rules (Swan Bitcoin and Blockware Solutions both state the same fresh development, Bitcoin falling alongside the tech-stock crash, in videos published hours before the cut, and the hook names Bitcoin and what happened without l)
  - hook `w4h9HfP7Gb0:1`..2 Swan Bitcoin: "Tech stocks got crushed yesterday and dragged Bitcoin down with them. The NASDAQ 100 fell 6.4%, its worst day since March 2020, and chip stocks fell 12%."
  - clip_01 `w4h9HfP7Gb0:9`..11 Swan Bitcoin: "Investors are questioning whether future returns can justify all of the money pouring into AI. This week's Democratic victories added fears that political opposition coul..."
  - clip_02 `kUrwpp--Nps:90`..92 Blockware Solutions: "Well, I think Bitcoin is showing incredible strength and resilience, holding the line right here at 76,000. Typically on these bloodbath type days for tech stocks, Bitcoi..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via story_engine coverage 'Bitcoin ETFs Bleed $430 Million as Tech Rout Tests Wall Street Buyers' holding [Blockware Solutions: kUrwpp--Nps:91, kUrwpp--Nps:92; Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2, w4h9HfP7Gb0:9]: the line-up's statements counted as the same event for 0 of its channels (none); candidate: rejected: only 0 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 2
  - one-channel story_engine coverage  'Fed and OCC Quiz U.S. Banks After $6.3 Billion Binance Hack' (cluster channels -) holding [Blockware Solutions: kUrwpp--Nps:90, kUrwpp--Nps:91, kUrwpp--Nps:92]: ASSEMBLY rejected: clip quality: 1 usable clips across 2 channel(s)
  - one-channel story_engine coverage  'Crypto Liquidations Top $1 Billion as Bitcoin Tests 11-Week Low' (cluster channels -) holding [Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2, w4h9HfP7Gb0:9]: LAYOUT_ELIGIBILITY rejected: only 0 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 3
  - one-channel story_engine coverage  'Strive (ASST) Posts $474.8 Million Common Net Income as Bitcoin Yield Hits 63.2%' (cluster channels -) holding [Blockware Solutions: kUrwpp--Nps:90, kUrwpp--Nps:91, kUrwpp--Nps:92]: COVERAGE rejected: coverage 0 < 2 independent channels
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 0 '' (cluster channels Altcoin Daily, BTC Sessions, Bankless, Bitcoin Magazine, Blockware Solutions) holding [Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2, w4h9HfP7Gb0:9]: NOT_REACHED no candidate recorded
  - one-channel cluster 28 '' (cluster channels Blockware Solutions, CoinTelegraph, Stacker News, What Bitcoin Did) holding [Blockware Solutions: kUrwpp--Nps:90, kUrwpp--Nps:91]: NOT_REACHED no candidate recorded
  - one-channel cluster 223 '' (cluster channels Blockware Solutions, Scott Melker) holding [Blockware Solutions: kUrwpp--Nps:91, kUrwpp--Nps:92]: NOT_REACHED no candidate recorded

### 20261107_065702 L1: Bitcoin erased its post-midterm rebound as a global tech-stock sell-off dragged it lower.
Channels Blockware Solutions, Simply Bitcoin, Swan Bitcoin, Yahoo Finance; content 55.65 s (runtime ~69.2 s); blind judge: passes our rules (Four different channels state or directly react to Bitcoin's sell-off in this week's tech rout, published 6-15 hours before the video; the hook names Bitcoin and what happened, every segment is whole sentences ending on )
  - hook `kK4b6PFhLz4:0` Yahoo Finance: "Bitcoin's big rebound after the midterms was entirely erased in the face of a massive tech and market route across the world."
  - clip_01 `w4h9HfP7Gb0:9`..11 Swan Bitcoin: "Investors are questioning whether future returns can justify all of the money pouring into AI. This week's Democratic victories added fears that political opposition coul..."
  - clip_02 `16ojEohQcR8:118`..119 Simply Bitcoin: "Bitcoin Archive flags a move toward the 200 day moving average and reports $265 million in long liquidations over 12 hours got smoked. That's a 12-hour snapshot, not proo..."
  - clip_03 `kUrwpp--Nps:91`..93 Blockware Solutions: "Typically on these bloodbath type days for tech stocks, Bitcoin gets hurt even worse. But Bitcoin's only down about 5% which is par for the course for this volatile orang..."
- layout: every segment's channel is layout-eligible
- as_run: **WINDOWS** via story_engine coverage 'Crypto Liquidations Top $1 Billion as Bitcoin Tests 11-Week Low' holding [Swan Bitcoin: w4h9HfP7Gb0:9, w4h9HfP7Gb0:10, w4h9HfP7Gb0:11; Yahoo Finance: kK4b6PFhLz4:0]: clip-quality windows in the line-up's videos from Yahoo Finance; candidate: rejected: no hook passage scored >= 4.0
  - one-channel story_engine coverage  'Fed and OCC Quiz U.S. Banks After $6.3 Billion Binance Hack' (cluster channels -) holding [Blockware Solutions: kUrwpp--Nps:91, kUrwpp--Nps:92, kUrwpp--Nps:93]: WINDOWS rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'The AI ‘credit card’ is getting costlier as CoreWeave bond yield tops 16%' (cluster channels -) holding [Swan Bitcoin: w4h9HfP7Gb0:11]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'Strive (ASST) Posts $474.8 Million Common Net Income as Bitcoin Yield Hits 63.2%' (cluster channels -) holding [Blockware Solutions: kUrwpp--Nps:91, kUrwpp--Nps:92, kUrwpp--Nps:93]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** via cluster '' holding [Blockware Solutions: kUrwpp--Nps:91, kUrwpp--Nps:92, kUrwpp--Nps:93; Swan Bitcoin: w4h9HfP7Gb0:9, w4h9HfP7Gb0:10, w4h9HfP7Gb0:11]: no candidate recorded
  - one-channel cluster 9 '' (cluster channels Bitcoin Magazine, Blockware Solutions, Stephan Livera, What Bitcoin Did, Yahoo Finance) holding [Blockware Solutions: kUrwpp--Nps:91]: NOT_REACHED no candidate recorded

### 20261107_080503 L2: Bitcoin fell alongside the November 5 tech sell-off and was testing support around $75,000–$76,000.
Channels Blockware Solutions, Swan Bitcoin, Yahoo Finance; content 46.88 s (runtime ~60.4 s); blind judge: passes our rules (Swan Bitcoin and Blockware both state the tech-stock rout pulling Bitcoin down, and the Yahoo Finance clip is a direct reaction on where Bitcoin is holding after it; all videos were published 14-17 hours before. The hook)
  - hook `w4h9HfP7Gb0:1`..2 Swan Bitcoin: "Tech stocks got crushed yesterday and dragged Bitcoin down with them. The NASDAQ 100 fell 6.4%, its worst day since March 2020, and chip stocks fell 12%."
  - clip_01 `kK4b6PFhLz4:83`..84 Yahoo Finance: "Now, for me, the story about Bitcoin, which is what you're obviously here for, is that it's still trading at prices where it had already bottomed last week. It's still tr..."
  - clip_02 `kUrwpp--Nps:95`..97 Blockware Solutions: "Well, I think Bitcoin is showing incredible strength and resilience holding the line right here at 76,000. Typically, on these bloodbath type days for tech stocks, Bitcoi..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via story_engine coverage 'Crypto Liquidations Top $1 Billion as Bitcoin Tests 11-Week Low' holding [Blockware Solutions: kUrwpp--Nps:96, kUrwpp--Nps:97; Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2; Yahoo Finance: kK4b6PFhLz4:83, kK4b6PFhLz4:84]: the line-up's statements counted as the same event for 1 of its channels (Swan Bitcoin); candidate: rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'Fed and OCC Quiz U.S. Banks After $6.3 Billion Binance Hack' (cluster channels -) holding [Blockware Solutions: kUrwpp--Nps:96, kUrwpp--Nps:97]: WINDOWS rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'Bitcoin erases post-election gains as Wall Street selloff triggers over $1 billi' (cluster channels -) holding [Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2]: CURRENTNESS inconclusive: currentness conflict: 1 verified historical-background verdict(s) vs 1 verified current
  - one-channel cluster 0 'US Midterm Elections Result in Democratic Control of Senate and House' (cluster channels UC678LSROK47l__G-pMnOMgA, UC9ijza42jVR3T6b8bColgvg, UCAl9Ld79qaZxp9JzEOwd3aA, UCCatR7nWbYrkVXdxXb4cGXw, UCDo6-SUypaXlTmH6AyrYBZA) holding [Yahoo Finance: kK4b6PFhLz4:83, kK4b6PFhLz4:84]: LABEL no verified current-development evidence
- replay_head: **NOT_REACHED** via cluster '' holding [Blockware Solutions: kUrwpp--Nps:96, kUrwpp--Nps:97; Swan Bitcoin: w4h9HfP7Gb0:1, w4h9HfP7Gb0:2]: no candidate recorded
  - one-channel cluster 0 '' (cluster channels Altcoin Daily, Anthony Pompliano, BTC Sessions, Bankless, Bitcoin Magazine) holding [Yahoo Finance: kK4b6PFhLz4:83, kK4b6PFhLz4:84]: NOT_REACHED no candidate recorded
  - one-channel cluster 37 '' (cluster channels Blockware Solutions, CoinTelegraph, Stacker News, What Bitcoin Did) holding [Blockware Solutions: kUrwpp--Nps:95]: NOT_REACHED no candidate recorded

### 20261107_080503 L3: Bitcoin's November 5 tech-led sell-off erased its post-midterm rebound, prompting assessments of its relative resilience and nearby support.
Channels Blockware Solutions, Scott Melker, Swan Bitcoin, Yahoo Finance; content 55.88 s (runtime ~69.4 s); blind judge: passes our rules (Yahoo Finance and Swan Bitcoin both state Bitcoin's drop in the tech-led market rout, and the Scott Melker and Blockware clips are direct reactions to it, all from videos published 14-18 hours earlier. The hook opens on )
  - hook `kK4b6PFhLz4:0` Yahoo Finance: "Bitcoin's big rebound after the midterms was entirely erased in the face of a massive tech and market route across the world."
  - clip_01 `w4h9HfP7Gb0:2`..3 Swan Bitcoin: "The NASDAQ 100 fell 6.4%, its worst day since March 2020, and chip stocks fell 12%. Bitcoin actually fell less than the NASDAQ 100, down about 5 % over 24 hours and tradi..."
  - clip_02 `y0SjcqQPdpA:119`..120 Scott Melker: "Well, the NASDAQ is down 10% and we're still 17 or $18,000 above Bitcoin's low. So the case that the NASDAQ or the market dropping 20% would send Bitcoin to 10,000 to me ..."
  - clip_03 `kUrwpp--Nps:102`..104 Blockware Solutions: "So everyone who's bought Bitcoin in the past six months, their cost basis is precisely where Bitcoin is at right now. This is support. During uptrends, newer market parti..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via story_engine coverage 'Crypto Liquidations Top $1 Billion as Bitcoin Tests 11-Week Low' holding [Swan Bitcoin: w4h9HfP7Gb0:2, w4h9HfP7Gb0:3; Yahoo Finance: kK4b6PFhLz4:0]: the line-up's statements counted as the same event for 1 of its channels (Swan Bitcoin); candidate: rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'The AI ‘credit card’ is getting costlier as CoreWeave bond yield tops 16%' (cluster channels -) holding [Scott Melker: y0SjcqQPdpA:119]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'Binance Hackers Swap About $50 Million of Stolen XRP Mostly Into Bitcoin, Ellipt' (cluster channels -) holding [Yahoo Finance: kK4b6PFhLz4:0]: CURRENTNESS inconclusive: currentness conflict: 4 verified historical-background verdict(s) vs 1 verified current
  - one-channel transcript_cluster coverage  'Elon Musk's Stock Sell-Off and Market Impact' (cluster channels -) holding [Scott Melker: y0SjcqQPdpA:119]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** via cluster '' holding [Scott Melker: y0SjcqQPdpA:119, y0SjcqQPdpA:120; Swan Bitcoin: w4h9HfP7Gb0:2, w4h9HfP7Gb0:3]: no candidate recorded
  - one-channel cluster 1 '' (cluster channels BTC Sessions, Bankless, Bitcoin Magazine, Bloomberg Television, CNBC Television) holding [Scott Melker: y0SjcqQPdpA:119]: BITCOIN_SCREEN Bitcoin screen: Bitcoin statements from 0 channel(s) in the last 72 h < 2 (no model call)
  - one-channel cluster 0 '' (cluster channels Altcoin Daily, Anthony Pompliano, BTC Sessions, Bankless, Bitcoin Magazine) holding [Blockware Solutions: kUrwpp--Nps:102, kUrwpp--Nps:103, kUrwpp--Nps:104]: NOT_REACHED no candidate recorded

### 20261110_093150 L1: Bitcoin closed the week below its 50-week moving average, ending seven consecutive weekly closes above it.
Channels Bitcoin Magazine, Marty Bent (Rabbit Hole Recap), Simply Bitcoin; content 53.56 s (runtime ~67.1 s); blind judge: passes our rules (Three channels state the same weekly close below the 50-week moving average from about a day and a half earlier, and the last clip is a direct reaction to it. The hook names Bitcoin and the event, timings fit (8.4 s hook)
  - hook `qo8rDU3bbMo:17`..18 Simply Bitcoin: "On Thursday, I said to watch this Sunday's weekly close. Well, Bitcoin closed just under 75K, about $500 below its 50we moving average."
  - clip_01 `jbDqdLytkNM:2`..3 Bitcoin Magazine: "Last night was Bitcoin's first weekly close below the 50we moving average since September. The 50we was around $75,000 and Bitcoin closed around $74.7,000, just 1% below ..."
  - clip_02 `eEB0nt6jvEw:270`..272 Marty Bent (Rabbit Hole Recap): "Bitcoin closed the week just below. It's 50-week moving average after seven straight weekly closes above it. The two prior times that slipped back after a post-bottom rec..."
  - clip_03 `jbDqdLytkNM:45`..47 Bitcoin Magazine: "We want to see Bitcoin reclaim the 50we urgently. It's not good that it was lost, but that doesn't change that the true market bottom is most likely in. The historical ex..."
- layout: without Bitcoin Magazine (not layout-eligible): hook kept, 1 clip(s), 2 channel(s), 21.8 s
- as_run: **COVERAGE** via story_engine coverage 'Bitcoin ETFs shed $1.3B in biggest weekly outflow since late June' holding [Bitcoin Magazine: jbDqdLytkNM:2, jbDqdLytkNM:3; Marty Bent (Rabbit Hole Recap): eEB0nt6jvEw:270, eEB0nt6jvEw:271, eEB0nt6jvEw:272; Simply Bitcoin: qo8rDU3bbMo:17, qo8rDU3bbMo:18]: the line-up's statements counted as the same event for 0 of its channels (none); candidate: rejected: no hook passage scored >= 4.0
  - one-channel story_engine coverage  '‘Connecting the dots’: Michael Saylor’s Strategy buys another 1,036 bitcoin for ' (cluster channels -) holding [Marty Bent (Rabbit Hole Recap): eEB0nt6jvEw:270, eEB0nt6jvEw:271, eEB0nt6jvEw:272]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel transcript_cluster coverage  'Bitcoin Falls Amid Tech Selloff and Global Economic Concerns' (cluster channels -) holding [Marty Bent (Rabbit Hole Recap): eEB0nt6jvEw:270, eEB0nt6jvEw:271, eEB0nt6jvEw:272]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'Binance to Close Accounts in Four EU Countries Dec. 31, Charging Idle Balances F' (cluster channels -) holding [Bitcoin Magazine: jbDqdLytkNM:2, jbDqdLytkNM:3]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- cold_backtest_394ffe5a: **COVERAGE** via story_engine coverage 'Bitcoin ETFs shed $1.3B in biggest weekly outflow since late June' holding [Bitcoin Magazine: jbDqdLytkNM:2, jbDqdLytkNM:3; Marty Bent (Rabbit Hole Recap): eEB0nt6jvEw:270, eEB0nt6jvEw:271, eEB0nt6jvEw:272; Simply Bitcoin: qo8rDU3bbMo:17, qo8rDU3bbMo:18]: the line-up's statements counted as the same event for 0 of its channels (none); candidate: rejected: no hook passage scored >= 4.0
  - one-channel cluster 148 'Bitcoin recently closed below a key moving average, signaling potential market s' (cluster channels Altcoin Daily, Bitcoin Magazine) holding [Bitcoin Magazine: jbDqdLytkNM:2, jbDqdLytkNM:3]: LAYOUT_ELIGIBILITY rejected: only 1 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 2
  - one-channel cluster 111 'Recent elections are being absorbed by the Bitcoin market.' (cluster channels Simply Bitcoin, Yahoo Finance) holding [Simply Bitcoin: qo8rDU3bbMo:17]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'BitGo revenue falls 51% in Q3 as trading slows; net income rises on treasury gai' (cluster channels -) holding [Simply Bitcoin: qo8rDU3bbMo:17, qo8rDU3bbMo:18]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **LABEL** via cluster 'Bitcoin experienced a recent price decline alongside a broader tech sell-off and was impac' holding [Bitcoin Magazine: jbDqdLytkNM:47; Marty Bent (Rabbit Hole Recap): eEB0nt6jvEw:270, eEB0nt6jvEw:271, eEB0nt6jvEw:272]: label: no verified current-development evidence
  - one-channel cluster 148 'Bitcoin recently closed below a key moving average, signaling potential market s' (cluster channels Altcoin Daily, Bitcoin Magazine) holding [Bitcoin Magazine: jbDqdLytkNM:2, jbDqdLytkNM:3]: LAYOUT_ELIGIBILITY rejected: only 1 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 2
  - one-channel cluster 111 'Recent elections are being absorbed by the Bitcoin market.' (cluster channels Simply Bitcoin, Yahoo Finance) holding [Simply Bitcoin: qo8rDU3bbMo:17]: COVERAGE rejected: coverage 1 < 2 independent channels

### 20261110_093150 L2: Bitcoin dropped to around $74,000 over the weekend alongside a technology-stock sell-off.
Channels DataDash, Natalie Brunell, Yahoo Finance; content 55.96 s (runtime ~69.5 s); blind judge: passes our rules (Yahoo Finance, DataDash and Natalie Brunell all state the weekend drop to the mid-$70,000s as current news; the hook names Bitcoin and what happened, and the timings (10.7 s hook, clips of 13.3, 17.1 and 14.9 s, 56.0 s t)
  - hook `_cGepHL1Rf0:9` Yahoo Finance: "Of course, Bitcoin dropped pretty massively over the weekend alongside the tech selloff that we saw, the Democrat blue wave, the Binance hack, but I don't check it on an ..."
  - clip_01 `RXTVaDsN11M:0`..1 DataDash: "Bitcoin has now seen a 16% decline from the overall high from 88,000, touching down towards about 73,400, 500, give or take. Over the weekend here, we had the stock marke..."
  - clip_02 `lusJ1m-J0Mc:18`..20 Natalie Brunell: "It went from above $81,000 after the election to below $75,000 by the weekend. U.S. Bitcoin ETFs had about $1.3 billion in net outflows just last week. And Bitcoin really..."
  - clip_03 `_cGepHL1Rf0:10`..11 Yahoo Finance: "It seemed to have bounced very nicely at a very key level around $74,000, around the 50 weekly MA, which we've talked about many times. I actually take the silver lining ..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via cluster 'Bitcoin Falls Amid Tech Selloff and Global Economic Concerns' holding [DataDash: RXTVaDsN11M:0, RXTVaDsN11M:1; Yahoo Finance: _cGepHL1Rf0:9, _cGepHL1Rf0:10, _cGepHL1Rf0:11]: the line-up's statements counted as the same event for 0 of its channels (none); candidate: rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'HIVE’s Bitcoin output jumps 49%, but mining revenue still falls' (cluster channels -) holding [Yahoo Finance: _cGepHL1Rf0:9, _cGepHL1Rf0:10, _cGepHL1Rf0:11]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'Bitcoin Price Drops Below $74,000 as Nvidia Probe and Regulation Fears Spark $1 ' (cluster channels -) holding [Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'Should you leave Australia to avoid paying 47% tax on crypto gains?' (cluster channels -) holding [Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- cold_backtest_394ffe5a: **COVERAGE** via story_engine coverage 'Bitcoin ETFs shed $1.3B in biggest weekly outflow since late June' holding [DataDash: RXTVaDsN11M:0, RXTVaDsN11M:1; Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: the line-up's statements counted as the same event for 1 of its channels (Natalie Brunell); candidate: rejected: no hook passage scored >= 4.0
  - one-channel story_engine coverage  'TD Cowen Gives Stablecoin Yield Ban 10% Odds as Banks Plan Push in Democrat-Led ' (cluster channels -) holding [Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'HIVE’s Bitcoin output jumps 49%, but mining revenue still falls' (cluster channels -) holding [Yahoo Finance: _cGepHL1Rf0:9, _cGepHL1Rf0:10, _cGepHL1Rf0:11]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'Bitcoin Price Drops Below $74,000 as Nvidia Probe and Regulation Fears Spark $1 ' (cluster channels -) holding [Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **LABEL** via cluster 'Bitcoin experienced a recent price decline alongside a broader tech sell-off and was impac' holding [DataDash: RXTVaDsN11M:0, RXTVaDsN11M:1; Yahoo Finance: _cGepHL1Rf0:9, _cGepHL1Rf0:10, _cGepHL1Rf0:11]: label: no verified current-development evidence
  - one-channel cluster 39 '' (cluster channels Altcoin Daily, Anthony Pompliano, Natalie Brunell) holding [Natalie Brunell: lusJ1m-J0Mc:18, lusJ1m-J0Mc:19, lusJ1m-J0Mc:20]: BITCOIN_SCREEN Bitcoin screen: Bitcoin statements from 1 channel(s) in the last 72 h < 2 (no model call)

### 20261111_190259 L1: Bitcoin fell toward $73,000, testing support at its 200-day moving average.
Channels Altcoin Daily, Coin Bureau, The Bitcoin Layer; content 54.53 s (runtime ~68.0 s); blind judge: passes our rules (Altcoin Daily and Coin Bureau both state the drop to the 200-day average within the last 32 hours, and the hook names Bitcoin and what happened; durations (54.5 s total), sentence boundaries, format limits and the altcoi)
  - hook `R-iKNbc7-zk:5` Altcoin Daily: "Bitcoin dropping to $73,000 yet finding support on the 200day moving average."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `f22H17BKYRw:85` The Bitcoin Layer: "But for those that are sort of focused on the levels, if we break sort of low7s, then we sort of I think we move straight down into the mid60s, which is another key level..."
- layout: every segment's channel is layout-eligible
- as_run: **NOT_REACHED** [no clusters in this record (the run crashed or stopped before clustering)] (no cluster or headline held its statements from >= 2 of its channels; 0 held one channel's)
- replay_head: **NOT_REACHED** via cluster '' holding [Altcoin Daily: R-iKNbc7-zk:5; The Bitcoin Layer: f22H17BKYRw:85]: no candidate recorded
  - one-channel cluster 25 '' (cluster channels Altcoin Daily, Bitcoin Magazine, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: NOT_REACHED no candidate recorded

### 20261111_192645 L1: Bitcoin's drop toward $73,000 is testing support at its 200-day moving average.
Channels Altcoin Daily, Coin Bureau, The Bitcoin Layer; content 54.53 s (runtime ~68.0 s); blind judge: passes our rules (Altcoin Daily and Coin Bureau both state the drop to about $73,000 holding at the 200-day average within the last 32 hours, and The Bitcoin Layer clip reacts with the next levels to watch. The hook opens on Bitcoin and s)
  - hook `R-iKNbc7-zk:5` Altcoin Daily: "Bitcoin dropping to $73,000 yet finding support on the 200day moving average."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `f22H17BKYRw:85` The Bitcoin Layer: "But for those that are sort of focused on the levels, if we break sort of low7s, then we sort of I think we move straight down into the mid60s, which is another key level..."
- layout: every segment's channel is layout-eligible
- as_run: **NOT_REACHED** [pre-DEC-13 record, incomplete: cluster membership not recorded and candidates left undecided] (no cluster or headline held its statements from >= 2 of its channels; 0 held one channel's)
- replay_head: **NOT_REACHED** via cluster '' holding [Altcoin Daily: R-iKNbc7-zk:5; The Bitcoin Layer: f22H17BKYRw:85]: no candidate recorded
  - one-channel cluster 27 '' (cluster channels Altcoin Daily, Bitcoin Magazine, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: NOT_REACHED no candidate recorded

### 20261111_192645 L2: Bitcoin recorded its first weekly close below the 50-week moving average since September.
Channels Bitcoin Magazine, Simply Bitcoin; content 50.76 s (runtime ~64.3 s); blind judge: passes our rules (Simply Bitcoin and Bitcoin Magazine both state that Bitcoin lost its 50-week moving average at Sunday's weekly close (about 67 hours before the video), and the hook names Bitcoin and what happened on its own. Segments ar)
  - hook `qo8rDU3bbMo:18` Simply Bitcoin: "On Thursday, I said to watch this Sunday's weekly close, while Bitcoin closed just under 75K, about $500 below its 50 -week moving average."
  - clip_01 `jbDqdLytkNM:23` Bitcoin Magazine: "Perhaps Bitcoin missed this week only because of, you know, the unwinded in tech, the Nvidia news, something akin to a narrative cross -market sell -off like what happene..."
  - clip_02 `qo8rDU3bbMo:196`..198 Simply Bitcoin: "So the same AI crash that dragged Bitcoin under its 50 -week line is building the pressure that ends at the printer. Bare markets usually end when the sellers run out, ev..."
  - clip_03 `jbDqdLytkNM:44`..46 Bitcoin Magazine: "We want to see Bitcoin reclaim the 50 week urgently. It's not good that it was lost, but that doesn't change that the true market bottom is most likely in. The historical..."
- layout: without Bitcoin Magazine (not layout-eligible): hook kept, 1 clip(s), 1 channel(s), 21.2 s
- as_run: **NOT_REACHED** [pre-DEC-13 record, incomplete: cluster membership not recorded and candidates left undecided] (no cluster or headline held its statements from >= 2 of its channels; 0 held one channel's)
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 0 '' (cluster channels Altcoin Daily, Bankless, Bitcoin Magazine, Coin Bureau, CoinTelegraph) holding [Bitcoin Magazine: jbDqdLytkNM:44, jbDqdLytkNM:45, jbDqdLytkNM:46]: NOT_REACHED no candidate recorded
  - one-channel cluster 62 '' (cluster channels Coin Bureau, DataDash, Simply Bitcoin) holding [Simply Bitcoin: qo8rDU3bbMo:18]: NOT_REACHED no candidate recorded
  - one-channel cluster 134 '' (cluster channels Bitcoin Magazine, Simply Bitcoin) holding [Bitcoin Magazine: jbDqdLytkNM:23]: NOT_REACHED no candidate recorded

### 20261111_213954 L1: Bitcoin's latest sell-off brought it down to test its 200-day moving average near $73,000.
Channels Altcoin Daily, Coin Bureau, The Bitcoin Layer; content 55.76 s (runtime ~69.3 s); blind judge: passes our rules (Coin Bureau and Altcoin Daily both state the drop holding at the 200-day average in videos from the last 34 hours, and The Bitcoin Layer clip is a direct reaction to the same breakdown. The hook opens on Bitcoin and what)
  - hook `UJFQBaMh3yg:0`..1 Coin Bureau: "Bitcoin's recent drop stalled just above the line traders use to separate a pullback from a bare market. And for 4 days running, it closed at almost the same price."
  - clip_01 `R-iKNbc7-zk:4`..5 Altcoin Daily: "The moment of truth for Bitcoin and the crypto market is happening now. Bitcoin dropping to $73,000 yet finding support on the 200day moving average."
  - clip_02 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_03 `f22H17BKYRw:78` The Bitcoin Layer: "On the Bitcoin price, pure price perspective, 75,600 was a key level that once it gave up, I'm looking back down to my ascending trend line, which is around 65 to 67,000,..."
- layout: every segment's channel is layout-eligible
- as_run: **CURRENTNESS** via story_engine coverage 'BitGo revenue falls 51% in Q3 as trading slows; net income rises on treasury gains' holding [Altcoin Daily: R-iKNbc7-zk:4, R-iKNbc7-zk:5; Coin Bureau: UJFQBaMh3yg:0, UJFQBaMh3yg:1]: inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel cluster 5 'US Midterm Elections Impact on Bitcoin' (cluster channels UC43_LTf5Z4lbRjKCq0sIAVg, UCB6Q0S1gUHXMe5-Jjx0_laQ, UCCatR7nWbYrkVXdxXb4cGXw, UCDo6-SUypaXlTmH6AyrYBZA, UCRqBu-grVX1p97WaX4d-OuQ) holding [The Bitcoin Layer: f22H17BKYRw:78]: WINDOWS rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'OKXICE moves ahead with tokenized stocks as blue chips push back' (cluster channels -) holding [Coin Bureau: UJFQBaMh3yg:0, UJFQBaMh3yg:1]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'MARA Sells 13,597 Bitcoin for $1.1 Billion, Says More Sales Are Coming' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:4, R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** via cluster '' holding [Altcoin Daily: R-iKNbc7-zk:4, R-iKNbc7-zk:5; The Bitcoin Layer: f22H17BKYRw:78]: no candidate recorded
  - one-channel cluster 25 '' (cluster channels Altcoin Daily, Bitcoin Magazine, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:0, UJFQBaMh3yg:1, UJFQBaMh3yg:74]: NOT_REACHED no candidate recorded

### 20261111_213954 L2: Bitcoin closed the week below its 50-week moving average, ending seven consecutive weekly closes above it.
Channels Bitcoin Magazine, Simply Bitcoin; content 55.12 s (runtime ~68.6 s); blind judge: passes our rules (Simply Bitcoin and Bitcoin Magazine both state the weekly close below the 50-week average near $75K, which falls inside the 72-hour window, and the other clips are direct reactions to it. The hook names Bitcoin and the e)
  - hook `qo8rDU3bbMo:18` Simply Bitcoin: "On Thursday, I said to watch this Sunday's weekly close, while Bitcoin closed just under 75K, about $500 below its 50 -week moving average."
  - clip_01 `jbDqdLytkNM:24`..25 Bitcoin Magazine: "You know, up until the Nvidia news broke, Bitcoin was holding its 50 -week moving average. It was above that $75,000 threshold and then lost it just moments heading into ..."
  - clip_02 `qo8rDU3bbMo:196`..198 Simply Bitcoin: "So the same AI crash that dragged Bitcoin under its 50 -week line is building the pressure that ends at the printer. Bare markets usually end when the sellers run out, ev..."
  - clip_03 `jbDqdLytkNM:47`..49 Bitcoin Magazine: "So right now, I would say, is an excellent buying opportunity if you're bullish on Bitcoin as a technology as money. and that, you know, we seldom get this many opportuni..."
- layout: without Bitcoin Magazine (not layout-eligible): hook kept, 1 clip(s), 1 channel(s), 21.2 s
- as_run: **CLUSTER_FORMATION** [cluster membership = the label's excerpts only (pre-DEC-13 record)] (no cluster or headline held its statements from >= 2 of its channels; 4 held one channel's)
  - one-channel story_engine coverage  'The Fed Has to Raise Rates. How Fast to Go Has Officials Divided.' (cluster channels -) holding [Simply Bitcoin: qo8rDU3bbMo:18]: WINDOWS rejected: no quote-anchored boundary window in layout-eligible evidence
  - one-channel story_engine coverage  'Canaan’s Q3 revenue plunges 90% to $14.5 million as bitcoin mining hardware sale' (cluster channels -) holding [Bitcoin Magazine: jbDqdLytkNM:24, jbDqdLytkNM:25]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'BitGo revenue falls 51% in Q3 as trading slows; net income rises on treasury gai' (cluster channels -) holding [Simply Bitcoin: qo8rDU3bbMo:18]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 2 '' (cluster channels Altcoin Daily, Bitcoin Magazine, Coin Bureau, CoinTelegraph, DataDash) holding [Bitcoin Magazine: jbDqdLytkNM:47, jbDqdLytkNM:48, jbDqdLytkNM:49]: NOT_REACHED no candidate recorded
  - one-channel cluster 68 '' (cluster channels Coin Bureau, DataDash, Simply Bitcoin) holding [Simply Bitcoin: qo8rDU3bbMo:18]: NOT_REACHED no candidate recorded
  - one-channel cluster 154 '' (cluster channels Bitcoin Magazine, Simply Bitcoin) holding [Bitcoin Magazine: jbDqdLytkNM:24, jbDqdLytkNM:25]: NOT_REACHED no candidate recorded

### 20261112_001448 L1: Bitcoin's latest sell-off pushed it into the low $73,000s, testing support at its 200-day moving average.
Channels Coin Bureau, DataDash, The Bitcoin Layer; content 55.55 s (runtime ~69.0 s); blind judge: passes our rules (DataDash and Coin Bureau both state the same drop to about $73,400 / the lowest level since August, and The Bitcoin Layer reacts with the downside levels; all videos are 5-55 hours old and present it as current. The hook)
  - hook `RXTVaDsN11M:0` DataDash: "Bitcoin has now seen a 16 % decline from the overall high from 88,000, touching down towards about 73,400, 500, give or take."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `f22H17BKYRw:85` The Bitcoin Layer: "But for those that are sort of focused on the levels, if we break sort of low7s, then we sort of I think we move straight down into the mid60s, which is another key level..."
- layout: every segment's channel is layout-eligible
- as_run: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 4 held one channel's)
  - one-channel cluster 145 'Bitcoin's price has recently declined from around $88,000 to approximately $73,4' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'' (cluster channels -) holding [DataDash: RXTVaDsN11M:0]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel cluster 23 'Bitcoin's price has recently experienced a stall or consolidation after a brief ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap), Stephan Livera) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 0 '' (cluster channels Altcoin Daily, BTC Sessions, Bankless, Bitcoin Magazine, Coin Bureau) holding [The Bitcoin Layer: f22H17BKYRw:85]: NOT_REACHED no candidate recorded
  - one-channel cluster 40 '' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: NOT_REACHED no candidate recorded
  - one-channel cluster 136 '' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: NOT_REACHED no candidate recorded

### 20261112_013452 L1: Bitcoin's latest sell-off reached roughly $73,000–$73,500 and tested support near its 200-day moving average.
Channels Coin Bureau, DataDash, The Bitcoin Layer; content 55.55 s (runtime ~69.0 s); blind judge: passes our rules (DataDash and Coin Bureau both state the same drop to about $73,400 within the last 72 hours, and The Bitcoin Layer clip is a direct reaction on the next levels; the hook names Bitcoin and what happened. Timings fit (9.3 )
  - hook `RXTVaDsN11M:0` DataDash: "Bitcoin has now seen a 16 % decline from the overall high from 88,000, touching down towards about 73,400, 500, give or take."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `f22H17BKYRw:85` The Bitcoin Layer: "But for those that are sort of focused on the levels, if we break sort of low7s, then we sort of I think we move straight down into the mid60s, which is another key level..."
- layout: every segment's channel is layout-eligible
- as_run: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 0 'Bitcoin and gold are currently experiencing price declines, coinciding with Bitc' (cluster channels Anthony Pompliano, BTC Sessions, Bankless, Bitcoin Magazine, CoinTelegraph) holding [The Bitcoin Layer: f22H17BKYRw:85]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
  - one-channel cluster 150 '' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: NOT_REACHED no candidate recorded
- cold_backtest_394ffe5a: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 4 held one channel's)
  - one-channel cluster 0 'Bitcoin and gold are currently experiencing price declines, coinciding with Bitc' (cluster channels Anthony Pompliano, BTC Sessions, Bankless, Bitcoin Magazine, CoinTelegraph) holding [The Bitcoin Layer: f22H17BKYRw:85]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel story_engine coverage  'Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'' (cluster channels -) holding [DataDash: RXTVaDsN11M:0]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 0 'Bitcoin and gold are currently experiencing price declines, coinciding with Bitc' (cluster channels Anthony Pompliano, BTC Sessions, Bankless, Bitcoin Magazine, CoinTelegraph) holding [The Bitcoin Layer: f22H17BKYRw:85]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
  - one-channel cluster 150 '' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: NOT_REACHED no candidate recorded

### 20261112_013452 L2: Bitcoin's latest sell-off reached roughly $73,000–$73,500 and tested support near its 200-day moving average.
Channels Altcoin Daily, Coin Bureau, DataDash; content 54.08 s (runtime ~67.6 s); blind judge: passes our rules (DataDash and Coin Bureau both state the same current Bitcoin drop, and Altcoin Daily reacts to it without naming any other coin; the hook names Bitcoin and the move, and each clip follows from what is heard before it. Ti)
  - hook `RXTVaDsN11M:0` DataDash: "Bitcoin has now seen a 16 % decline from the overall high from 88,000, touching down towards about 73,400, 500, give or take."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `R-iKNbc7-zk:99`..100 Altcoin Daily: "But unless you believe that a lower low is coming, and and sure, that is 100% possible, the other alternative is that we're just making a higher low. And the first higher..."
- layout: every segment's channel is layout-eligible
- as_run: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 6 'There is ongoing discussion regarding the potential for a strategic Bitcoin rese' (cluster channels Altcoin Daily, BTC Sessions, Bitcoin Audible, Bitcoin Magazine, Stacker News) holding [Altcoin Daily: R-iKNbc7-zk:99, R-iKNbc7-zk:100]: LABEL label: no verified current-development evidence
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
  - one-channel cluster 150 '' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: NOT_REACHED no candidate recorded
- cold_backtest_394ffe5a: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 4 held one channel's)
  - one-channel story_engine coverage  'Stablecoin Drain, ETF Outflows Leave Bitcoin 'Running on Empty'' (cluster channels -) holding [DataDash: RXTVaDsN11M:0]: COVERAGE rejected: coverage 1 < 2 independent channels
  - one-channel cluster 6 'There is ongoing discussion regarding the potential for a strategic Bitcoin rese' (cluster channels Altcoin Daily, BTC Sessions, Bitcoin Audible, Bitcoin Magazine, Stacker News) holding [Altcoin Daily: R-iKNbc7-zk:99, R-iKNbc7-zk:100]: LABEL label: no verified current-development evidence
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
- replay_head: **NOT_REACHED** [no cluster held its statements from >= 2 of its channels; the run stopped before every pool and headline was evaluated (audit F8: not a decided loss)] (no cluster or headline held its statements from >= 2 of its channels; 3 held one channel's)
  - one-channel cluster 6 'There is ongoing discussion regarding the potential for a strategic Bitcoin rese' (cluster channels Altcoin Daily, BTC Sessions, Bitcoin Audible, Bitcoin Magazine, Stacker News) holding [Altcoin Daily: R-iKNbc7-zk:99, R-iKNbc7-zk:100]: LABEL label: no verified current-development evidence
  - one-channel cluster 49 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence
  - one-channel cluster 150 '' (cluster channels Coin Bureau, DataDash) holding [DataDash: RXTVaDsN11M:0]: NOT_REACHED no candidate recorded

### 20261112_050611 L1: Bitcoin dropped to around $73,000 and found support at its 200-day moving average.
Channels Altcoin Daily, Coin Bureau, The Bitcoin Layer; content 54.53 s (runtime ~68.0 s); blind judge: passes our rules (Altcoin Daily and Coin Bureau both state the drop to about $73,000 holding at the 200-day average, and The Bitcoin Layer clip gives the downside levels as a reaction; all videos are 10-42 hours old. The hook names Bitcoi)
  - hook `R-iKNbc7-zk:5` Altcoin Daily: "Bitcoin dropping to $73,000 yet finding support on the 200day moving average."
  - clip_01 `UJFQBaMh3yg:74`..76 Coin Bureau: "And on the way down, Bitcoin has sliced through everything else. The 50-day, the 100 day, even the 200-day exponential average are all overhead. Now, the 200day simple av..."
  - clip_02 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_03 `f22H17BKYRw:85` The Bitcoin Layer: "But for those that are sort of focused on the levels, if we break sort of low7s, then we sort of I think we move straight down into the mid60s, which is another key level..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via cluster 'Bitcoin and gold are currently experiencing a downturn in price, coinciding with recent ec' holding [Altcoin Daily: R-iKNbc7-zk:5; The Bitcoin Layer: f22H17BKYRw:85]: the line-up's statements counted as the same event for 1 of its channels (Altcoin Daily); candidate: rejected: only 1 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 2
  - one-channel story_engine coverage  'Canaan’s Q3 revenue plunges 90% to $14.5 million as bitcoin mining hardware sale' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'US bit barn boom sees energy needs grow 10x as fast as grid capacity' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'Sam Lyman: “Bitcoin doesn’t need America. America needs Bitcoin.”' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** via cluster 'Bitcoin and gold are currently experiencing a downturn in price, coinciding with recent ec' holding [Altcoin Daily: R-iKNbc7-zk:5; The Bitcoin Layer: f22H17BKYRw:85]: no decision recorded (the run stopped or crashed before this candidate)
  - one-channel cluster 50 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:74, UJFQBaMh3yg:75, UJFQBaMh3yg:76]: LABEL label: no verified current-development evidence

### 20261112_050611 L2: Bitcoin dropped to around $73,000 and found support at its 200-day moving average.
Channels Altcoin Daily, Coin Bureau, The Bitcoin Layer; content 56.1 s (runtime ~69.6 s); blind judge: passes our rules (Altcoin Daily and Coin Bureau both state the drop to the 200-day moving average and the hold, and the other two clips are direct reactions to it, from videos 10-42 hours old. The hook opens on "Bitcoin" and says what hap)
  - hook `R-iKNbc7-zk:5` Altcoin Daily: "Bitcoin dropping to $73,000 yet finding support on the 200day moving average."
  - clip_01 `UJFQBaMh3yg:81`..83 Coin Bureau: "Bitcoin dipped to its lowest level since August within a few hundred of the line and it held. So the rule from here is pretty simple. Daily closes above the 200 day and t..."
  - clip_02 `f22H17BKYRw:78` The Bitcoin Layer: "On the Bitcoin price, pure price perspective, 75,600 was a key level that once it gave up, I'm looking back down to my ascending trend line, which is around 65 to 67,000,..."
  - clip_03 `R-iKNbc7-zk:99`..100 Altcoin Daily: "But unless you believe that a lower low is coming, and and sure, that is 100% possible, the other alternative is that we're just making a higher low. And the first higher..."
- layout: every segment's channel is layout-eligible
- as_run: **COVERAGE** via cluster 'Bitcoin and gold are currently experiencing a downturn in price, coinciding with recent ec' holding [Altcoin Daily: R-iKNbc7-zk:5, R-iKNbc7-zk:99, R-iKNbc7-zk:100; The Bitcoin Layer: f22H17BKYRw:78]: the line-up's statements counted as the same event for 1 of its channels (Altcoin Daily); candidate: rejected: only 1 layout-eligible channel(s) with evidence (clips need >= 2); editorial coverage 2
  - one-channel story_engine coverage  'Canaan’s Q3 revenue plunges 90% to $14.5 million as bitcoin mining hardware sale' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'US bit barn boom sees energy needs grow 10x as fast as grid capacity' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
  - one-channel story_engine coverage  'Sam Lyman: “Bitcoin doesn’t need America. America needs Bitcoin.”' (cluster channels -) holding [Altcoin Daily: R-iKNbc7-zk:5, R-iKNbc7-zk:99, R-iKNbc7-zk:100]: CURRENTNESS inconclusive: currentness missing: no verified transcript evidence of a current development
- replay_head: **NOT_REACHED** via cluster 'Bitcoin and gold are currently experiencing a downturn in price, coinciding with recent ec' holding [Altcoin Daily: R-iKNbc7-zk:5, R-iKNbc7-zk:99, R-iKNbc7-zk:100; The Bitcoin Layer: f22H17BKYRw:78]: no decision recorded (the run stopped or crashed before this candidate)
  - one-channel cluster 50 'Bitcoin's price recently experienced a pullback following a surge after midterm ' (cluster channels Altcoin Daily, Coin Bureau, Marty Bent (Rabbit Hole Recap)) holding [Coin Bureau: UJFQBaMh3yg:81, UJFQBaMh3yg:82, UJFQBaMh3yg:83]: LABEL label: no verified current-development evidence

## 5. Analysis (hand-written, from the tables above)

### 5.1 What the numbers say, and what they cannot

- Supply existed on every saved run measured: on 10 of 10 runs the blind oracle proposed at least one line-up that
  passed the deterministic checks and that the blind judge said passes our rules (16 accepted line-ups; 19 proposed, 2
  failed a deterministic check, the blind judge said 1 fails our rules; every oracle reply valid at its first
  attempt). The selector reached none of them where it could be measured: recall 0 of 6 as run (the 6 runs whose
  record completed a selection; 4 crashed or were stopped: not measured), 0 of 1 in the 394ffe5a cold backtest (the
  other stopped: not measured); the HEAD replay stops (NOT_RERUN: no cached gemma reply) before any selection on every
  run, so recall at HEAD is not measured. Precision is not measured: no record accepted a line-up, so there is
  nothing for the judge to rate.
- Small and correlated sample: 10 runs on 5 ET dates (Nov 6, 7, 10, 11, 12); the six Nov 11 / Nov 12 00:06 runs share
  most of one 72 h universe, and the same few developments recur (Nov 5 tech sell-off; the weekend fall to ~$74K /
  the 50-week close; the test of the 200-day average near $73K). One oracle sample and one judge sample per item. Read
  every count as "on these runs", not as a rate.
- Availability here is TEXT-level. Not measured: the acoustic sentence law at the cut (pauses, edge words: DEC-10 /
  L-b), the render and its gates, the vertical layout. Caption-timed sentences carry estimated times (about +-1 s; the
  hook 8-12 s and clip 12-20 s budgets were applied to those estimates). The PBX-approved preview's own line-up needed
  DEC-10's envelope-minimum cut on Yahoo's abutting 'days.' | 'Of', so a line-up that passes our rules as text can still fail at the cut.
- The oracle's Nov 10 line-up L2 independently rebuilt the protected preview's story and channels (Yahoo Finance hook
  _cGepHL1Rf0:9, DataDash RXTVaDsN11M:0-1, Natalie Brunell lusJ1m-J0Mc:18-20, Yahoo _cGepHL1Rf0:10-11): the instrument
  finds the line-up PBX approved, on the day the go-live bar names.

### 5.2 The three stages that lost the most accepted line-ups (as run: the decisions the selector actually made)

As run, the 16 accepted line-ups were lost at COVERAGE 7, CLUSTER_FORMATION 1, WINDOWS 1, CURRENTNESS 1, and 6 were
never reached: fresh_20261111_190259 crashed before clustering (E-FAIL-030; 1), fresh_20261111_192645 was stopped
before its pre-DEC-13 candidates were decided (2), and on fresh_20261112_001448 and fresh_20261112_013452 the clusters
formed but no single cluster held two of the line-up's channels and the run was stopped before every pool and
headline was evaluated (3). At HEAD (replay, current clustering) 2 stop at LABEL (Nov 10) and 14 are NOT_REACHED: 8
whose statements from >= 2 channels sit in ONE cluster whose label needs a gemma reply that is not cached, and 6 split
across clusters where the replay stopped. DEC-13's >= 2-channel clusters hold more of these line-ups together than
the old 8-widest rule did; where they do not, the development is split (point 2).

**1. COVERAGE: the line-up's statements were adjudicated and not counted (7 of 16 as run).** Two different things
share this stage:
- (a) the only selector object that held the statements was a headline about a DIFFERENT development, and its
  adjudication correctly refused them (2 as run, + the BitGo case at CURRENTNESS, + both Nov 10 line-ups in the cold
  backtest). Nov 6 L1: the wire headline "Bitcoin ETFs Bleed $430 Million as Tech Rout Tests Wall Street Buyers" (derived
  event "Investors sold off shares in Bitcoin ETFs on November 6") held Swan Bitcoin w4h9HfP7Gb0:1-2 and Blockware
  kUrwpp--Nps:91-92; both CURRENT_EVENT, quotes verified, support TOPIC_ONLY. Nov 10 L1 (the 50-week close): only the
  ETF-outflow headline held Simply Bitcoin qo8rDU3bbMo:17-18, Bitcoin Magazine jbDqdLytkNM:2-3 and Marty Bent
  eEB0nt6jvEw:270-272, all TOPIC_ONLY against "investors reduced their holdings in Bitcoin-based products".
  The development the channels shared (a price move to a level) was never a candidate of its own: these runs predate
  DEC-13 and kept only the 8 widest >= 3-channel clusters.
- (b) the candidate WAS the development (or a broader claim containing it) and its adjudication refused the line-up's
  statements (5 as run). Nov 7 03:05 L2 / L3: the liquidation headline's derived event is the AI-led sell-off; Yahoo
  Finance's caption reads "... Wall Street telloff triggers over $1 billion in crypto. liquidations." and the model
  quoted "selloff", so quote_verified False (bible B8); Blockware's quote was a question ("Did the blue wave just burst
  the AI bubble?"), TOPIC_ONLY; one channel counted. Nov 10 L2 as run: the cluster "Bitcoin Falls Amid Tech Selloff
  ..." was derived as "Global financial markets experienced increased volatility and a risk-off sentiment ..." (the
  E-FAIL-038 class law L-i fixed at 394ffe5a) and DataDash's adjudicated quote was "I'm gonna be paying attention for
  the strength weakness in bitcoin" (not RXTVaDsN11M:0's "16 % decline ... towards about 73,400"): TOPIC_ONLY. The one
  channel the candidate counted was Yahoo Finance through a DIFFERENT video (36HPi9UZPOc), not the line-up's
  _cGepHL1Rf0, so none of the line-up's own statements counted. Nov 12 00:06 (live run, f2840fac) L1 / L2: the cluster "Bitcoin and gold are currently experiencing a
  downturn ..." held Altcoin Daily R-iKNbc7-zk:5 and The Bitcoin Layer f22H17BKYRw:85; The Bitcoin Layer's adjudicated
  quote was "Bitcoin delevered first half of this year ..." (TOPIC_ONLY), so one layout-eligible channel.
- What it implies, as trade-offs (no gate loosened): (a) is a candidate-generation question, not an adjudication one:
  the support verifier's same-actor-action-object test is what keeps an ETF-outflow headline from counting a price
  statement (DEC-13's must-not), so the price-move development needs to be a candidate itself. (b) is the free-text
  evidence path: the model chooses which sentence of a 30-60 s excerpt is "the quote" and re-types it; a re-typed quote
  can fail verbatim verification (B8) and a weak sentence can be chosen over the one that states the development.
  Constrained selection (addendum '22:15' item 3: the model returns ids of numbered statements; the quote is the stored
  sentence) removes both without lowering any threshold. Cost: a larger prompt (numbered sentences instead of
  excerpts), and the support verifier then judges exactly the sentence the clip will use, so a vague sentence that passes our rules
  is refused where today a lucky re-typed quote might pass.

**2. Split across clusters: no single cluster held the line-up's statements from two of its channels (1 decided as
run, CLUSTER_FORMATION, from a pre-DEC-13 record whose membership is the label's excerpts only; seen again in 3 more
as run, 2 in the cold backtest and 6 at HEAD in records that stopped before every pool and headline was evaluated:
those are NOT_REACHED, because a later headline's coverage can still gather statements across clusters).** The
pattern is real (DEC-13 cluster membership is complete once clustering ran); whether a later stage would have
recovered these line-ups is not measured. On the DEC-13 days the statements of ONE development sit in several clusters that each hold one
of the line-up's channels. Nov 11 20:34 (fresh_20261112_013452) L1: Coin Bureau UJFQBaMh3yg:74-76 / 81-83 sit in
cluster 49 "Bitcoin's price recently experienced a pullback following a surge after midterm election ..." (Altcoin
Daily, Coin Bureau, Marty Bent); DataDash RXTVaDsN11M:0 sits in cluster 150 "Bitcoin's price has recently declined from
a high of around $88,000 ..." (Coin Bureau, DataDash); The Bitcoin Layer f22H17BKYRw:85 sits in cluster 0 "Bitcoin and
gold are currently experiencing price declines ...". Each one-channel cluster then fails on its own (cluster 0 at
COVERAGE 1 < 2 as run; in the 394ffe5a cold backtest cluster 150 counted DataDash AND Coin Bureau and reached clip
quality with a 5.0 hook RXTVaDsN11M:0 (0.00-9.10 s), then had no Coin Bureau window because the backtest had no word
record for UJFQBaMh3yg: NOT_RERUN, not a decision).
- Why: clusters are formed over 30-60 s chunks (cosine 0.22, average linkage). A chunk carries several statements, so
  where a development's statements land depends on what else each chunk says; the same-event merge (step 5b) links
  candidates only when they COUNT the same statement, which split clusters by construction do not.
- Trade-offs: a looser clustering threshold merges more of one development and also merges different events (the
  DEC-13 must-not: Bloomberg's Fed-hike and Natalie Brunell's ETF-outflow statements). Clustering whole sentences
  (the units this export already has: 892-1,641 Bitcoin sentences per run against ~3,700-5,000 chunks) aligns the
  cluster with the statement the clip will use, at the cost of more, shorter items that embed less reliably; a merge of
  clusters whose labelled claims state the same level / figure would need its own must-not fixtures.

**3. LABEL (HEAD) and WINDOWS (as run): evidence identifiers and window growth.**
- LABEL, Nov 10 at HEAD (and at 394ffe5a: the same cached reply): DEC-13 clustering DOES put the accepted line-up's
  statements together: cluster 0 holds DataDash RXTVaDsN11M:0-1 and Yahoo Finance _cGepHL1Rf0:9-11. Its label quotes
  Yahoo's sentence verbatim ("Bitcoin dropped pretty massively over the weekend alongside the tech selloff ...") but
  returns current_development_chunk_id "_cGepHL1Rf0" (the video id, not an excerpt id), so the quote check fails
  closed: "label: no verified current-development evidence" (bible B7; 1-2 of 31-46 specific-event labels per DEC-13
  record). On the go-live bar's own day, the preview's story is lost to a malformed identifier, not to a missing story.
  Implies: the same constrained-selection change as 1(b) (the label picks a numbered sentence; the code binds its chunk).
- WINDOWS, Nov 7 01:57 L1: the liquidation headline counted Swan Bitcoin and Yahoo Finance; Swan's verified sentence
  w4h9HfP7Gb0:1 "Tech stocks got crushed yesterday and dragged Bitcoin down with them." is 3.86 s (< 8 s hook) and the
  next sentence w4h9HfP7Gb0:2 "The NASDAQ 100 fell 6.4%, its worst day since March 2020, and chip stocks fell 12%." was
  refused by the adjacent-sentence check (TOPIC_ONLY); the oracle's hook is exactly :1-2 (11.2 s). Yahoo's only window
  scored 3.0; "no hook passage scored >= 4.0". Under today's D4 rule the deterministic pre-check would refuse it too (no
  back-reference, shared entity or shared number). Trade-off: D4 is what stops a window drifting into the next topic;
  the cost is a hook whose first sentence states the event and whose second gives its numbers. Not changed here.

### 5.3 Layout eligibility (its own column)

3 of 16 accepted line-ups stop passing our rules without has_chyron channels: Nov 10 L1, Nov 11 14:26 L2 and Nov
11 16:39 L2 each take two clips from Bitcoin Magazine (jbDqdLytkNM), which DEC-12d keeps out of clips because its
burned-in lower third fails G10 in 16:9; without them each keeps a hook and one clip (~21-22 s). The other 13 use only
layout-eligible channels. The decision this belongs to is OD-9 (a 16:9 framing for has_chyron channels), not a gate
change: with it these 3 become candidates; without it they are correctly unproducible.

### 5.4 What the backtest could not decide (NOT_RERUN / NOT_REACHED, said plainly)

- HEAD replay: every run stops at its first gemma call with no cached reply (label_cluster on the Nov 11 / Nov 12
  universes, derive_story_query after the 48 h pool on Nov 10, adjudicate on Nov 11 20:34). Stages after the stop are
  scored from the saved run records instead (columns as_run / cold_backtest), never inferred.
- Where a cluster holding two of the line-up's channels formed at HEAD but its label needs gemma (Nov 11 14:03 L1,
  14:26 L1, 16:39 L1; Nov 12 00:06 L1 / L2), the stage is NOT_REACHED: the current code got further than the run did,
  and how much further is not known without the GPU.
- Word records: the offline backtest has no word transcript for videos the live run would transcribe at clip quality;
  such clip-quality outcomes are NOT_RERUN (e.g. Coin Bureau UJFQBaMh3yg in the cold backtest), not losses.

### 5.5 Story-first with bent clip rules versus moments-first, on the same universes (notes 01:55 and 02:30)

Same 10 exports, same writer (gpt-6.1-sol) and same blind judge (claude-fable-5-2) for every column; counts are per
saved universe (section 7 has every cell). Each writer call asked for as many sentence-disjoint line-ups as exist (up
to 8), except the order's first run (up to 3).

| rule set | runs with a line-up | accepted line-ups (per universe) | sentence-disjoint (per universe) | distinct developments (per universe) |
|---|---|---|---|---|
| story-first, windows HARD, up to 3 asked (the order's run) | 10 of 10 | 16 (1-2) | 13 (1-2) | 13 (1-2) |
| story-first, windows HARD, as many as exist | 10 of 10 | 31 (1-6) | 31 (1-6) | 22 (1-5) |
| (A) story-first, windows as TARGETS (L-o) | 10 of 10 | 41 (2-7) | 41 (2-7) | 22 (1-4) |
| (B) moments-first, windows as targets | 10 of 10 | 48 (3-6) | 48 (3-6) | - (not one development) |
| (B) + all four witness checks | 6 of 10 | 7 (0-2) | 7 (0-2) | - |

- Told the windows are targets, the writer mostly went outside them: 36 of 41 (A) and 43 of 48 (B) accepted line-ups
  miss at least one 8-12 s / 12-20 s window, so the windows-hard numbers measured after the fact on those runs (5
  disjoint line-ups each) are lower bounds; the direct hard-window measurement is the "windows HARD, as many as exist"
  row (its own writer call per universe, told the windows are limits).
- What the windows cost, measured directly: 31 accepted line-ups with the windows as hard limits against 41 with them
  as targets (10 fewer, on the same universes, same writer and judge). Developments per universe sum to 22 either way,
  but per universe the counts move in both directions (hard / targets: Nov 6 5 / 4, Nov 7 01:57 2 / 3, Nov 7 03:05
  3 / 2, Nov 10 2 / 1, Nov 11 14:26 1 / 2, Nov 11 19:14 1 / 2; the other four equal), and whether they are the SAME
  developments was not checked (each run was grouped on its own). So: the hard windows cost about a quarter of the
  line-ups; no loss of stories is shown, and none is ruled out. One writer sample per universe and rule set, so a
  single-universe difference (Nov 10: 3 line-ups hard against 2 as targets; Nov 11 14:26: 1 against 3) is noise-sized.
- The difference between (A) and (B) is the cost of the same-development rule (41 against 48 line-ups); section 8
  gives the cost of each witness check.
- Every accepted line-up of every rule set fits a 60-70 s runtime estimate (content + ~13.5 s of card and outro).
- Distinct developments repeat across universes taken hours apart: on the six Nov 11 / Nov 12 runs (story-first,
  targets) the same three developments recur, two per run (the test of the 200-day average near $73K; the first weekly
  close below the 50-week average; the comparison with the November 2021 peak), so NEW developments per 3-5 h window
  are fewer than developments per universe.
- Judge leniency to watch: story-first acceptances include developments whose Bitcoin focus or currentness is
  arguable (Nov 6 / 7: "Democrats won control of both the House and the Senate"; Nov 12: "Five years after the November
  2021 peak near $69,000 ..."). These are single judge samples; they are counted as the judge ruled.
- Parity note: the witness checks were run on moments line-ups only (as ordered). Applied to story-first, "one excerpt
  per channel" alone would keep 5 of 41 (A) line-ups (3 runs): story-first line-ups typically take two clips from one
  channel. Context-stripping and implied relation were not measured for story-first.

### 5.6 What each witness check costs moments-first (section 8 has every run)

- Base: 48 accepted line-ups on 10 of 10 runs. One excerpt per channel: 24 left (9 runs). Own sincere assertion in the
  original context (90 s before / 60 s after): 17 left (9 runs). No implied relation across videos: 19 left (10 runs;
  the witness found a cross-video relation implied in 29 of 48 line-ups: juxtaposition is what the format does). No
  named accusation / buy-sell imperative / ad read: 44 left. All four: 7 line-ups on 6 of 10 runs.
- Of the 166 segments the witness read, 140 were the speaker's own sincere view; 14 attributed (a host reporting
  someone else's view, e.g. "Liquid is betting that ..." as the set-up to a question), 6 read aloud (headline
  rundowns the host then mocks or qualifies), 3 ad reads, 3 uncertain (speaker not identifiable from captions without
  diarisation). 1 buy / sell imperative, 0 named accusations.
- The witness reads captions without speaker labels: "uncertain" counts as a fail, so supply without diarisation is a
  lower bound for this check, and a diarised transcript is an input the check needs (the reviewers say so too).

### 5.7 Model roles under law L-x: blind A/B on the saved data (section 9)

Every model call now goes through one provider interface (pipeline/oracle/providers.py): each role is a chain of at
least two vendors with the local Ultron model first; a vendor that is down or out of credit moves the role to the next;
a judge-like role never uses the vendor that actually wrote; no model name appears outside the provider config; the
local model becomes a role's default only once its own A/B passes (all tested). The reference in each comparison is
the back-end this report's numbers rest on (claude-fable-5-2 for judge / witness / grouping, gpt-6.1-sol for the
writer). One sample per item unless stated; read every count as "on these items".

- Writer (Nov 10, the smallest universe; every line-up judged by the same blind judge): gpt-6.1-sol 2 line-ups, both
  pass our rules, 2 sentence-disjoint (273 s, $0.34). grok-4.7: 2 pass, 1 disjoint (377 s, $0.42).
  heimdall-deepseek-v4.1-flash: 1 line-up, failed by the judge on rule 1 (its Yahoo Finance clip "shares the price
  topic but neither states the 50-week loss nor reacts to it"), 0 pass (1,812 s on a loaded gateway, $0.009). The
  local model cannot take any universe whole (115,595-219,172 prompt tokens against a 131,072-token context that must
  also hold the reply): a local writer needs a reduction step first (for example one call per development cluster).
- Judge (25 items: the 17 recorded verdicts and 8 development swaps). The swaps calibrate rather than prove: the
  reference itself caught 6 of 8 on rule 1 (it passed one, a "five years after the 2021 peak, up only 6 %" clip inside
  a "drop to $73K stalled above the 200-day average" line-up, and failed one for another reason).
  - heimdall-glm-5.3-flash: it passed all 17 recorded line-ups (its "agreement" there only reflects that the
    reference passed 16 of them) and passed 4 of the 6 swaps it answered (1 caught on rule 1, 1 failed for another
    reason, 2 gateway 503s; 3 swaps sampled twice, one pair disagreeing). It does not discriminate: as a fallback it
    would pass what the reference fails. 14.5 s median, $0.010 for all 25.
  - Local gemma3:27b (the integrator, under the GPU0 lease): 10 of 25 with the reference; passed 6 of 8 swaps and 1
    recorded line-up the reference failed (7 lenient); failed 6 the reference passed, 5 on a false altcoin reading;
    caught 0 swaps on rule 1. 88 s median. Below the bar: the judge stays on the frontier (providers.DECIDED_BY).
  - grok-4.7: failed all 16 recorded line-ups the reference passed and agreed on the one it failed (0 lenient; 222 s
    median; $2.55); its swaps were not run (spend guard). As a fallback it would report zero supply on every run.
- Witness (48 recorded verdicts on moments line-ups in their original context): heimdall-glm-5.3-flash measured 38
  (10 replies refused by the strict parser as internally inconsistent, e.g. a PASS its own fields contradict),
  agreed on 21, passed 10 the reference failed, failed 7 it passed (10.9 s median, $0.008). The local model (the
  integrator's run, still in progress at this commit: 19 of 48 items) agreed on 6 of 15 measured and passed 7 the
  reference failed. Neither is a usable fallback for this check.
- Grouping (16 recorded groupings): heimdall-glm-5.3-flash gave the reference's partition on 16 of 16 (56 s median,
  $0.004 for all 16); deepseek-v4.1-flash 14 of 16, qwen3.8-27b 13 of 16. Every disagreement split a reference group
  (5 developments against 4, 3 against 2): it would inflate the distinct-developments count.
- What this says about L-x, as trade-offs (no gate changed): only grouping has a measured fallback that matches the
  reference (heimdall-glm). For the judge and the witness, every fallback measured either passes what the reference
  fails (glm, local) or fails everything (grok): the first silently lets bad line-ups through, the second silently
  produces nothing. So the order of the judge and witness chains matters: grok-4.7 (fails closed: an outage of the
  reference yields no supply) stays ahead of heimdall-glm (lenient: it would yield wrong supply), and no default moves
  until a back-end catches the swaps. Latency on the shared Heimdall gateway, with several batches in flight, ran from seconds to over 20
  minutes per call (glm judge calls: median 14.5 s, longest 4,698 s; the deepseek writer call 1,812 s), so a Heimdall
  fallback inside a live run needs its own concurrency limit and timeout.

## 6. Method and artefacts

- Export: tools/backtest_oracle.py export; rows = every sentence that names Bitcoin (editorial_select.BITCOIN_TERMS) and its 2 neighbours either side in the same video; text read as spoken (transcript_store.read_text), canon = canon.canon. Three independent exports (2026-11-12 01:03-01:08 ET, session log) were byte-identical; tests/oracle/test_oracle_export.py proves the property on fixtures (sha256 per run below).
- Writer (oracle) and judge: the back-ends named per run in section 7 (pipeline/oracle/providers.py holds every back-end, its settings and price); JSON-schema output, parsed strictly. The writer is shown only the run's statements (rows longer than the 20 s clip budget hidden) and the written rules; up to one retry (schema error, or every line-up failing the deterministic checks). The judge is shown one line-up and the same rules, never who built it, and is never the writer's vendor.
- Available = oracle proposed it AND the deterministic checks pass (ids, consecutive sentences, durations, >= 2 channels, per-video / per-channel limits, >= 46.5 s, altcoin word screen) AND the blind judge says it passes our rules. (In the raw artefacts the judge's verdict field reads LEGAL for passes our rules and ILLEGAL for fails them; the field name is kept so stored prompts stay byte-identical.)

| run | rows sha256 | rows | Bitcoin rows | videos exported / universe |
|---|---|---|---|---|
| 20261106_213852 | `c6987ef50aa6a4c9f03d64432294b6ebb0af5c86055d344e2005f1896cf50c8f` | 5384 | 1641 | 96 / 109 |
| 20261107_065702 | `36f1b96aec11318b1104544a5815188763375cde282292adbdc6d5c4ff7c5a81` | 3751 | 1127 | 102 / 112 |
| 20261107_080503 | `a7600a89478d2b4044310cbba392bf49e747db8cb98cfa2e2e23053c4dd5a369` | 5097 | 1502 | 105 / 115 |
| 20261110_093150 | `8a749e7d5f929048e8c90f6d6dd74b15b07aecd4e6cf29d42079b8083dd81162` | 3018 | 892 | 87 / 95 |
| 20261111_190259 | `dab90477cb1b8a504e9b60d43167b328effdac8a6d0c84e5e99f9d025bb70ec4` | 3670 | 1206 | 96 / 117 |
| 20261111_192645 | `7fb61307511c6122eb61246fcf2d410683ec51e747f2d536af93aeea01c9e19f` | 3738 | 1226 | 96 / 117 |
| 20261111_213954 | `6f81fb00f8fa685824a7b9a2817380c9e67aceba8636146d7b1a82f1eed0d420` | 3964 | 1316 | 98 / 119 |
| 20261112_001448 | `6a0f9820068f581637ca891cfc9927d2253609c1d8e1e7beea184e48f09030f6` | 3764 | 1246 | 97 / 117 |
| 20261112_013452 | `d5cb7c27af4446422331394e2803fba90d40051c29c831dd176f7ce489ee2ea7` | 3751 | 1248 | 95 / 115 |
| 20261112_050611 | `a8b812d21179a6d5a80e63f2183ef4edac6d23102cd0b5a6902566f1412c107d` | 3862 | 1272 | 109 / 121 |

API spend (ledger /home/ultron/heimdall_probe/pp_redteam/oracle/SPEND.jsonl): 57.4 USD over 586 calls; per back-end: claude-fable-5-2 35.01 USD / 321 calls; gpt-6.1-sol 19.08 USD / 42 calls; grok-4.7 3.22 USD / 31 calls; heimdall-qwen3.8-27b 0.03 USD / 17 calls; heimdall-deepseek-v4.1-flash 0.03 USD / 26 calls; heimdall-glm-5.3-flash 0.03 USD / 103 calls; local-gemma3-27b 0.0 USD / 46 calls. The local back-end's calls are the integrator's runs under the GPU0 lease (REQUESTS R5); this session never called it. Of the total, 0.0896 USD is the per-call cost a gateway reported; 4 gateway calls made before per-call pricing was recorded carry no price. Guard: 60 USD (the ledger refuses any call whose worst case would pass it).


## 7. Supply per universe under the 01:55 note: distinct line-ups, PBX's 01:48 moments rule, law L-o

Three rule sets on the same exports (each column says which models produced it):
- **same_dev_hard**: same development; 8-12 s / 12-20 s windows hard; up to 3 line-ups asked.
- **same_dev_hard_max**: same development; windows hard; as many sentence-disjoint line-ups as exist.
- **same_dev**: same development; windows as targets (L-o); as many sentence-disjoint line-ups as exist.
- **moments**: moments first (PBX 01:48); windows as targets (L-o); as many sentence-disjoint line-ups.

Per cell: accepted line-ups / sentence-disjoint line-ups / distinct developments (the accepted line-ups grouped blind by development; '-' = no grouping: moments line-ups need not share one); then, in brackets, the same with the 8-12 s / 12-20 s windows applied as HARD limits after the fact (a target-mode line-up outside them does not count; a lower bound, since that oracle was told the windows are targets).

| run | same_dev_hard | same_dev_hard_max | same_dev | moments |
|---|---|---|---|---|
| 20261106_213852 | 1 / 1 / 1 (1 / 1) | 6 / 6 / 5 (6 / 6) | 7 / 7 / 4 (3 / 3) | 6 / 6 / - (1 / 1) |
| 20261107_065702 | 1 / 1 / 1 (1 / 1) | 3 / 3 / 2 (3 / 3) | 5 / 5 / 3 (1 / 1) | 5 / 5 / - (0 / 0) |
| 20261107_080503 | 2 / 1 / 1 (2 / 1) | 5 / 5 / 3 (5 / 5) | 5 / 5 / 2 (0 / 0) | 4 / 4 / - (1 / 1) |
| 20261110_093150 | 2 / 2 / 2 (2 / 2) | 3 / 3 / 2 (3 / 3) | 2 / 2 / 1 (0 / 0) | 4 / 4 / - (0 / 0) |
| 20261111_190259 | 1 / 1 / 1 (1 / 1) | 4 / 4 / 2 (4 / 4) | 5 / 5 / 2 (0 / 0) | 5 / 5 / - (0 / 0) |
| 20261111_192645 | 2 / 2 / 2 (2 / 2) | 1 / 1 / 1 (1 / 1) | 3 / 3 / 2 (0 / 0) | 5 / 5 / - (0 / 0) |
| 20261111_213954 | 2 / 2 / 2 (2 / 2) | 3 / 3 / 2 (3 / 3) | 5 / 5 / 2 (0 / 0) | 3 / 3 / - (0 / 0) |
| 20261112_001448 | 1 / 1 / 1 (1 / 1) | 1 / 1 / 1 (1 / 1) | 4 / 4 / 2 (1 / 1) | 6 / 6 / - (1 / 1) |
| 20261112_013452 | 2 / 1 / 1 (2 / 1) | 3 / 3 / 2 (3 / 3) | 3 / 3 / 2 (0 / 0) | 6 / 6 / - (2 / 2) |
| 20261112_050611 | 2 / 1 / 1 (2 / 1) | 2 / 2 / 2 (2 / 2) | 2 / 2 / 2 (0 / 0) | 4 / 4 / - (0 / 0) |

| rule set | models | runs with an accepted line-up (windows targets / hard / runtime <= 70 s) | accepted line-ups (all / runtime <= 70 s) | sentence-disjoint line-ups (targets / hard / <= 70 s) | distinct developments |
|---|---|---|---|---|---|
| same_dev_hard | oracle gpt-6.1-sol, judge claude-fable-5-2 | 10 of 10 / 10 of 10 / 10 of 10 | 16 / 16 | 13 / 13 / 13 | 13 over 10 grouped runs |
| same_dev_hard_max | oracle gpt-6.1-sol, judge claude-fable-5-2 | 10 of 10 / 10 of 10 / 10 of 10 | 31 / 31 | 31 / 31 / 31 | 22 over 10 grouped runs |
| same_dev | oracle gpt-6.1-sol, judge claude-fable-5-2 | 10 of 10 / 3 of 10 / 10 of 10 | 41 / 41 | 41 / 5 / 41 | 22 over 10 grouped runs |
| moments | oracle gpt-6.1-sol, judge claude-fable-5-2 | 10 of 10 / 4 of 10 / 10 of 10 | 48 / 48 | 48 / 5 / 48 | - |

Runtime = hook + clips + ~13.5 s of credits card and outro (an estimate); the floor of 60 s is enforced for every rule set, the 70 s ceiling only counted here (the approved preview ran 71.08 s).

Every rule set hid from the writer the sentences longer than the 20 s clip ceiling (73-121 per universe, 957 in all; mostly unpunctuated caption stretches, bible B6). Under the rule sets that treat the windows as targets (same_dev, moments) such a sentence could have been a clip, so those columns are lower bounds for this reason as well.

## 8. Moments-first with the reviewers' witness checks (orchestrator note 02:30)

Each accepted moments line-up was re-read by claude-fable-5-2 (never the writer's vendor) with every clip inside its ORIGINAL context (the same transcript, 90 s before to 60 s after); one excerpt per channel is checked in code. Any 'uncertain' is a fail; a witness reply that is not whole and consistent fails the checks (WITNESS_FAILED line-ups: 0). Cells: line-ups passing / of those, sentence-disjoint.

| run | base (blind judge: passes our rules) | + one excerpt per channel | + own sincere assertion in original context | + no implied relation across videos | + no named accusation / buy-sell imperative / ad read | all four witness checks |
|---|---|---|---|---|---|---|
| 20261106_213852 | 6 / 6 | 3 / 3 | 4 / 4 | 3 / 3 | 6 / 6 | 1 / 1 |
| 20261107_065702 | 5 / 5 | 2 / 2 | 2 / 2 | 2 / 2 | 4 / 4 | 1 / 1 |
| 20261107_080503 | 4 / 4 | 2 / 2 | 0 / 0 | 2 / 2 | 4 / 4 | 0 / 0 |
| 20261110_093150 | 4 / 4 | 2 / 2 | 1 / 1 | 2 / 2 | 4 / 4 | 0 / 0 |
| 20261111_190259 | 5 / 5 | 4 / 4 | 3 / 3 | 2 / 2 | 4 / 4 | 1 / 1 |
| 20261111_192645 | 5 / 5 | 3 / 3 | 2 / 2 | 1 / 1 | 5 / 5 | 0 / 0 |
| 20261111_213954 | 3 / 3 | 2 / 2 | 1 / 1 | 1 / 1 | 2 / 2 | 1 / 1 |
| 20261112_001448 | 6 / 6 | 0 / 0 | 1 / 1 | 2 / 2 | 5 / 5 | 0 / 0 |
| 20261112_013452 | 6 / 6 | 4 / 4 | 2 / 2 | 3 / 3 | 6 / 6 | 2 / 2 |
| 20261112_050611 | 4 / 4 | 2 / 2 | 1 / 1 | 1 / 1 | 4 / 4 | 1 / 1 |

| checks required | runs with a line-up left | line-ups left | sentence-disjoint line-ups left |
|---|---|---|---|
| base (blind judge: passes our rules) | 10 of 10 | 48 | 48 |
| + one excerpt per channel | 9 of 10 | 24 | 24 |
| + own sincere assertion in original context | 9 of 10 | 17 | 17 |
| + no implied relation across videos | 10 of 10 | 19 | 19 |
| + no named accusation / buy-sell imperative / ad read | 10 of 10 | 44 | 44 |
| all four witness checks | 6 of 10 | 7 | 7 |

## 9. Model roles: one provider interface, blind A/B on saved data (law L-x, note 02:45)

Every model call of this instrument goes through pipeline/oracle/providers.py (the only place a vendor or a model name appears). Role chains, first available back-end answers, a vendor-side failure moves to the next, the judge-like roles never use the writer's vendor:

- **writer**: local-gemma3-27b -> gpt-6.1-sol -> grok-4.7 -> heimdall-deepseek-v4.1-flash (default decided by: measured by size, 2026-11-12: every saved universe's writer prompt is 115,595-219,172 tokens and the local context holds 131,072 including the reply budget, so the context guard skips the local writer on all 10 (a cut prompt is never sent); the frontier writes until a reduction step exists. Quality A/B of the alternatives: BACKTEST_SUPPLY_REPORT.md section 9)
- **judge**: local-gemma3-27b -> claude-fable-5-2 -> grok-4.7 -> heimdall-glm-5.3-flash (default decided by: measured 2026-11-12 (integrator, GPU0 lease, REQUESTS R5): the local model agreed with the reference on 10 of 25 items, passed 6 of 8 development swaps and 1 line-up the reference failed, and failed 6 the reference passed (5 on a false altcoin reading): below the bar, so the judge's default stays the frontier back-end (ab/local/AB_judge.json))
- **grouping**: local-gemma3-27b -> claude-fable-5-2 -> grok-4.7 -> heimdall-glm-5.3-flash (default decided by: pending: the local A/B runs under the GPU0 lease (integrator); see BACKTEST_SUPPLY_REPORT.md section 9)
- **witness**: local-gemma3-27b -> claude-fable-5-2 -> grok-4.7 -> heimdall-glm-5.3-flash (default decided by: pending: the local A/B runs under the GPU0 lease (integrator); see BACKTEST_SUPPLY_REPORT.md section 9)

Judge / witness / grouping: the exact stored prompts replayed on each back-end and compared with the recorded reference verdicts (judge: plus must-fail swaps whose only right verdict is 'fails our rules'). Writer: the saved day re-run per back-end with the judge fixed. The local back-end, local-gemma3-27b (gemma3:27b), runs only inside the integrator's GPU0 lease (this session never calls it): its rows below are the integrator's runs (REQUESTS R5; they are that back-end's calls in the spend ledger); a role it has not run yet reads PENDING. 'items run / planned' shows what was never run. Dollars per call: frontier from the provider config's price table, a gateway's as it reports each call, local 0.

Items the spend guard stopped before they were sent are NOT MEASURED (own column), never failures and never agreement; a batch re-run for them is merged per item (every paid call is counted in the dollars). The reference judge's own row holds only its result on the development swaps (its recorded verdicts are the reference and are not re-asked).

| role | back-end | items run / planned | measured / not sent (spend guard) / failed (no usable reply) | agreement with the reference (of measured) | passes what the reference fails | fails what the reference passes | must-fail caught (of measured) | median s per call | USD |
|---|---|---|---|---|---|---|---|---|---|
| writer | grok-4.7 (20261110_093150) | 1 call(s) | 1 / 0 / 0 | AVAILABLE (OK): 2 line-ups, check-fail 0, judge says fails our rules 0, accepted 2, disjoint 1 (judge claude-fable-5-2) | - | - | - | 377.4 | 0.4214 (price table) |
| writer | heimdall-deepseek-v4.1-flash (20261110_093150) | 1 call(s) | 1 / 0 / 0 | NOT_AVAILABLE (the blind judge said every checked line-up fails our rules) (OK): 1 line-ups, check-fail 0, judge says fails our rules 1, accepted 0, disjoint 0 (judge claude-fable-5-2) | - | - | - | 1812.1 | 0.009009 (gateway-reported) |
| writer | local-gemma3-27b | 10 universes | - | not run: the stored writer prompt fits its context on 0 of 10 universes (context guard; a cut prompt is never sent) | - | - | - | - | - |
| judge | grok-4.7 | 17 / 25 | 17 / 0 / 0 | 1 of 17 | 0 | 16 | 0 of 0 (10 rows of the 9 withdrawn first swaps not counted) | 221.7 | 2.5487 (price table) |
| judge | claude-fable-5-2 | 8 / 8 | 8 / 0 / 0 | 6 of 8 | 1 | 0 | 6 of 8 (18 rows of the 9 withdrawn first swaps not counted) | 21.9 | 1.8912 (price table) |
| judge | heimdall-glm-5.3-flash | 25 / 25 | 23 / 0 / 2 | 17 of 23 | 5 | 0 | 1 of 6 (9 rows of the 9 withdrawn first swaps not counted) | 14.5 | 0.010442 (gateway-reported) |
| judge | local-gemma3-27b | 25 / 25 | 25 / 0 / 0 | 10 of 25 | 7 | 6 | 0 of 8 | 88.1 | 0.0 (local) |
| witness | heimdall-glm-5.3-flash | 48 / 48 | 38 / 0 / 10 | 21 of 38 | 10 | 7 | - | 10.9 | 0.008362 (gateway-reported) |
| witness | local-gemma3-27b (batch still running or stopped early: counts are of the items it finished) | 21 / 48 | 16 / 0 / 5 | 7 of 16 | 7 | 2 | - | 172.9 | 0.0 (local) |
| grouping | heimdall-deepseek-v4.1-flash | 16 / 16 | 16 / 0 / 0 | 14 of 16 | - | - | - | 99.2 | 0.013939 (gateway-reported) |
| grouping | heimdall-glm-5.3-flash | 16 / 16 | 16 / 0 / 0 | 16 of 16 | - | - | - | 55.8 | 0.003868 (gateway-reported) |
| grouping | heimdall-qwen3.8-27b | 16 / 16 | 16 / 0 / 0 | 13 of 16 | - | - | - | 18.4 | 0.034073 (gateway-reported) |
| grouping | local-gemma3-27b | - | - | PENDING: integrator, GPU0 lease | - | - | - | - | - |
