# pp-ingest: ruling 40, how often the hard flags imperative / accusation / single_source_breaking are right

Orchestrator ruling 40 (03:13 ET Nov 13): precision check, cheap, Heimdall only, a second model; confusion table and
5 examples per cell; then propose the fix and wait for the ruling; clear no flag; report the spend.
Measured 03:25-05:25 ET Nov 13. **Nothing was changed:** no flag cleared, no ledger line written, the adapter's
exclusions untouched, and the watcher still mines with mine/2.

## Answer

| flag | the miner flagged | the second model agrees | precision | 95 % CI |
|---|---|---|---|---|
| imperative | 56 | 41 | **73 %** | 60-83 % |
| accusation | 130 | 68 | **52 %** | 44-61 % |
| single_source_breaking | 30 | 20 | **67 %** | 49-81 % |

- **Second model:** z-ai/glm-5.3-flash on Heimdall, at its default reasoning. Before it was used it got 24 of 24
  quotes with a clear answer under your definitions right. 581 of the 600 questions went to it; the other 19 went to
  the role's second back-end, the Meta model muse-spark-open (also 24/24), after GLM timed out at 300 s, returned
  nothing, or replied invalidly twice.
- **What the precision means:** agreement with a calibrated second model, not ground truth. The checker errs both
  ways (below): it is lenient on imperative and literal on accusation.
- **Where the wrong labels come from:**
  - Imperative: predictions, the speaker's own trades, rhetorical "ignore / listen / look", and the stablecoin line
    from your ruling (the checker says no).
  - Accusation: the miner sets it on any negative mention of a named party: a hack's victim, earnings, market
    commentary, criticism with no wrongdoing alleged, even "if we do hit 68K".
  - single_source_breaking: claims the speaker attributes to someone else, history, speculation.
  - Not the cause: the merging of overlapping windows (only 4 of 200 rows were seen twice).
  - Both miners are affected:
    - qwen: 79 % imperative, 53 % accusation, 62 % single_source_breaking
    - Opus, during the outage drill: 38 %, 46 %, 83 % (small samples)
- **Option A (your definitions in the miner's prompt), dry run on the same windows:** it does not raise precision.
  On the same 119 rows:
  - imperative 87 → 89 %
  - accusation 60 → 59 %
  - single_source_breaking flags rise 18 → 26 (precision 61 → 73 %), because your definition is broader
  - A re-run of the unchanged prompt moves only 1-4 labels per flag.
- **Option B (a flag stands only when both models agree), simulated with the adapter's own read:**
  - The builder's 24 h funnel: hard-flag removals 123 → 84, and 25 more rows reach the packager (510 → 535).
  - 72 h: 311 → 237, and 52 more rows reach the packager.
  - About 10 of those 52 rows are, on my reading, insinuations against a party a viewer can identify. Seven are
    one channel's insinuations that CZ or Binance manipulate the market. One is a creator calling a registered
    partner's chairman a gambler.
  - The checker reads "alleges" as stated outright, and "identifiable" as named in the quote.
- **Proposal (below; awaiting your ruling):**
  - **P1:** option B now for imperative and single_source_breaking. Simulated: 24 h removals 123 → 116, 4 rows
    released; 72 h, 9 rows released (the 4 included); all 9 look clean.
  - **P2:** not for accusation as defined. Sharpen its definition first (insinuation; "identifiable" from the clip,
    its title or its channel), re-measure, then rule.
  - **P3:** option A is not the fix.
- **Spend:** $0.226, all Heimdall:
  - $0.043 for the check, its three runs together
  - $0.004 to choose the checker
  - $0.002 for the smokes
  - $0.177 for option A's dry run (253 calls to the miner's own model)

## How it was measured
- **Rows.** The ledger the builder reads (`data/editorial/moments/moment_ledger.jsonl`), one line per moment id (the
  latest wins, as the adapter reads). Every row the miner flagged `imperative`, `accusation` or
  `single_source_breaking` and published in the last 72 h (the adapter's window): 225 rows; the newest 200
  were checked (published 2026-11-10 16:00 to 2026-11-13 02:57 UTC; 178 mined by qwen, 22 by Opus). That
  includes every such row of the builder's 24 h funnel (106 rows); the adapter's own read of the same ledger
  reproduces that funnel: 685 rows, 123 removed by hard flags.
- **The second model.** Role `flagcheck` in `providers.json`: `z-ai/glm-5.3-flash` then
  `meta-models/muse-spark-open-816b-a42b`, both served by Heimdall (the spend freeze leaves only Heimdall).
  Never a model or back-end that mined any line of the row's video (the rows were mined by `qwen/qwen3.8-27b` and,
  during the 08:36 UTC outage drill, `claude-opus-5-5`; neither is in the role).
- **One narrow question per flag, the definition in the prompt, verbatim from the ruling.**
  `imperative = tells the viewer to buy, sell, hold or act financially`; `accusation = alleges wrongdoing by a
  named or identifiable person or organisation`; `single_source_breaking = a new factual claim about a current
  event resting on this speaker alone`. The checker sees the quote (the moment's exact text) with its channel,
  title and date, inside an untrusted block, and is not told what the miner said. All three questions are asked
  of every sampled row, so each flag gets a full table, including rows the miner did NOT give that flag (those are
  rows flagged with one of the other two: they say nothing about the miner's misses in general).
- **Strict reply (law L-l).** Exactly `{"answer": "yes" | "no" | "unsure", "evidence", "why"}`; a "yes" must quote
  words found in the quote (checked), any other answer has empty evidence; otherwise the reply is rejected and asked
  again. A question no back-end answered is UNMEASURED: it never counts as agreement or disagreement (law L-m).
- **The checker was calibrated before it was used.** 24 quotes whose answer is clear under the definitions
  (4 yes + 4 no per flag; fictional names). The first candidate setting (glm at reasoning effort none, the
  setting the audits used) scored 21/24: it said "yes" to a speaker's own purchase (imperative), a historical fact
  and a price prediction (single_source_breaking), so it would have inflated the precision. At its default
  reasoning it scored 24/24, and that is the setting used (this run: 24/24 for glm and for muse).
- **Option B simulated, not applied.** The adapter's own read (`ledger.best_unused_moments`) runs on a temporary
  copy of the ledger without the flags the checker answered "no" to (unsure and unmeasured keep the flag: fail
  closed), against the same read of the real ledger. The copy is deleted; the ledger is not written.
- **Option A dry-run, not applied.** `tests/ingest/dryrun_definitions.py` re-mines the checked rows' windows with
  the same model twice: the miner's prompt exactly as it ran (rebuilt and matched to the hash the ledger recorded,
  then called again without the reply cache: the noise floor of a re-run) and the same prompt with only the three
  flag lines replaced by the ruling's definitions. Both arms are scored against the same checker answers.


## Results

Checker calibration (24 quotes with a clear answer under the ruling's definitions, 4 yes + 4 no per flag):

| back-end | model | right | imperative | accusation | single_source_breaking | unmeasured |
|---|---|---|---|---|---|---|
| heimdall_glm53flash | z-ai/glm-5.3-flash | 24/24 | 8/8 | 8/8 | 8/8 | 0 |
| heimdall_muse | meta-models/muse-spark-open-816b-a42b | 24/24 | 8/8 | 8/8 | 8/8 | 0 |

CONFUSION TABLES (rows: the miner's label; columns: the checker's answer)

imperative: precision 73 % (95 % CI [0.604, 0.83]; counting unsure as yes 73 %; measured 56)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 41 | 15 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 1 | 143 | 0 | 0 |

accusation: precision 52 % (95 % CI [0.438, 0.607]; counting unsure as yes 52 %; measured 130)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 68 | 62 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 2 | 68 | 0 | 0 |

single_source_breaking: precision 67 % (95 % CI [0.488, 0.808]; counting unsure as yes 67 %; measured 30)

| miner \ checker | yes | no | unsure | unmeasured |
|---|---|---|---|---|
| flagged | 20 | 10 | 0 | 0 |
| not flagged (rows flagged with another of the three) | 64 | 106 | 0 | 0 |

Precision by subset (checker yes / measured, among the rows the miner flagged):

| subset | imperative | accusation | single_source_breaking |
|---|---|---|---|
| miner claude-opus-5-5 | 3/8 (38 %) | 5/11 (46 %) | 5/6 (83 %) |
| miner qwen/qwen3.8-27b | 38/48 (79 %) | 63/119 (53 %) | 15/24 (62 %) |
| seen once | 40/54 (74 %) | 68/129 (53 %) | 19/29 (66 %) |
| seen in two windows | 1/2 (50 %) | 0/1 (0 %) | 1/1 (100 %) |
| the flag is the row's only hard flag | 34/45 (76 %) | 49/105 (47 %) | 12/17 (71 %) |

OPTION B SIMULATED (a flag stands only when both models agree; unsure and unmeasured keep it): the adapter's own read on a copy of the ledger, against the same read of the real ledger. Nothing applied.

| window | rows | removed by hard flags now | if both must agree | returned now | if both must agree |
|---|---|---|---|---|---|
| 24 h | 685 | 123 | 84 | 510 | 535 |
| 72 h | 1550 | 311 | 237 | 1025 | 1077 |


## Reading the cells

**imperative (73 %).**
- **The checker's 15 "no" answers:** none tells the viewer to act financially:
  - predictions ("Bitcoin isn't moving up until these games end")
  - the speaker's own trades ("I literally never use more than 1x leverage")
  - "ignore the panic stack stats", "Listen to this ... I sold Bitcoin for it"
  - an ad's description of its product (the row keeps `ad_read` anyway)
  - your stablecoin line
- **Its "yes" answers are a little lenient.** "I'm very excited to buy these dips", "then I'd immediately sell all
  my Bitcoin and buy gold" (the speaker's own intent) and "Stop reading wicks ..." count as imperatives to it. So
  imperative's precision may be lower than 73 %, never higher.

**accusation (52 %).**
- **Most of the checker's 62 "no" answers are plainly right.** The miner flagged:
  - a hack's victim ("Binance recently saw a record-breaking $6.3 billion hack")
  - a forfeited pay package, a company's quarterly sale of Bitcoin, a fund's returns against its benchmark
  - market talk ("if we do hit 68K"), "super cycle incoming"
  - a list of asset names
  - criticism with no wrongdoing alleged ("All Michael Saylor is doing is he is gambling")
- **About 10 are debatable, and they are the dangerous kind:** insinuations of wrongdoing against a party the
  viewer can identify:
  - `9de59bc10c885e568761`, `53f438f63faff439156e`: CZ "does a bullish tweet and then the price absolutely dumps"
  - `4cbed9594d3579802c7f`: CZ "is going to liquidate the market"
  - `8761e1dc6d45773f2c6d`: "73% of Binance accounts are still long. It looks like the book is being cleared to
    refill the fund"
  - `4b0d74b36a8dc60f539b`: "liquidate as many people as possible ... the Safu fund"
  - `aa0de859851aebbcd0ea`, `a3c34ae1435f0a6b83ca`: "one venue keeps forcing liquidations ... that isn't a normal
    market"; "the venue that's been leaning on price since the hack"
  - `c9adac7e64b60e33cc7e`: "reports of Susie Wiles' children getting very cushy lobbyist jobs"
  - `8270499b0eb329ad29e8`: MCI "picking winners and losers"
- **Why the checker says "no" to these:** it reads "alleges" as stated outright, and treats "one venue", "they"
  or a passive voice as not identifiable.
- **The partner case:** `e904e3a98a765e47f85f` (Bitcoin Mechanic: "All Michael Saylor is doing is he is gambling")
  is criticism, not wrongdoing, so the checker's "no" is right by the definition. But Strategy is a registered
  partner channel, and the miner did not set `partner_attack`. Option B would release it.

**single_source_breaking (67 %).**
- **The checker's 10 "no" answers fit your definition:**
  - 4 claims the speaker attributes to someone else ("a former White House official says ...")
  - history ("18 years ago ... Satoshi registered Bitcoin on SourceForge")
  - a past practice
  - 2 speculations ("I cannot confirm nor deny")
  - a theory relayed from Twitter
  - a sentence with no claim in it
- **Under your broader definition the miner flags too little:** the checker says "yes" on 64 of the 170 checked rows
  the miner did not flag single_source_breaking. All 64 carry accusation and/or imperative (54, 9 and 1), so they
  are excluded anyway. Option A's dry run shows the same thing: 18 → 26 such flags on the same rows.

**What the "not flagged" rows say.** For imperative (1 "yes" in 144) and accusation (2 in 70), the miner almost never
misses within this sample. These rows were chosen for carrying another of the three flags, so this is not an
estimate of misses in general.

## Option A, dry run (your definitions in the miner's prompt; nothing applied)

Re-mined by heimdall_qwen27b: 178 checked rows from 123 windows (not re-mined: {'mined by claude-opus-5-5 (not callable now)': 22}); control prompts rebuilt vs the recorded hash: {'same as recorded': 101}; failed windows: 0; rows returned again: control 146, A 127; scored on the 119 rows both arms returned.

| flag | arm | flagged | checker yes / no / unsure / unmeasured | precision | checker yes, not flagged | differs from the original |
|---|---|---|---|---|---|---|
| imperative | original | 31 | 27 / 4 / 0 / 0 | 87 % | 1 | - |
| imperative | control | 30 | 26 / 4 / 0 / 0 | 87 % | 2 | 1 |
| imperative | A | 28 | 25 / 3 / 0 / 0 | 89 % | 3 | 3 |
| accusation | original | 77 | 46 / 31 / 0 / 0 | 60 % | 1 | - |
| accusation | control | 76 | 45 / 31 / 0 / 0 | 59 % | 2 | 1 |
| accusation | A | 70 | 41 / 29 / 0 / 0 | 59 % | 6 | 11 |
| single_source_breaking | original | 18 | 11 / 7 / 0 / 0 | 61 % | 38 | - |
| single_source_breaking | control | 18 | 12 / 6 / 0 / 0 | 67 % | 37 | 4 |
| single_source_breaking | A | 26 | 19 / 7 / 0 / 0 | 73 % | 30 | 12 |

Every moment the two arms returned from these windows (not only the checked rows):

| arm | moments | imperative | accusation | single_source_breaking | any hard flag |
|---|---|---|---|---|---|
| control | 456 | 42 | 119 | 26 | 190 |
| A | 439 | 42 | 117 | 38 | 192 |

Spend $0.1773 ({'ok': 246, 'invalid': 7}), 607 s.


Two other points:
- **The re-run moves ranges, not just labels.** Even the unchanged prompt returned only 146 of the 178 re-mined rows
  again (82 %), and the definitions only 127. So a prompt change also changes which ranges become moments.
- **Over every moment the two arms returned from these 123 windows:** hard-flagged moments 190 / 456 → 192 / 439.
  Option A does not lower the exclusion rate.

## Option B, simulated (nothing applied)
- **All three flags** (the table above): 24 h removals 123 → 84, and 25 more rows reach the packager. 72 h: 311 →
  237, and 52 more. Some released rows are then excluded by the adapter's other rules: altcoin or not about
  Bitcoin, or a speaker change.
- **imperative and single_source_breaking only, accusation kept as mined (P1):**
  - **24 h:** removals 123 → 116, and 4 more rows reach the packager:
    - "ignore the panic stack stats"
    - "if I had to put one number on it, maybe it's like 20%, 30%"
    - "I'm waiting on this rotation narrative to emerge"
    - "We've seen an almost 20% decline ... de-risking"
  - **72 h:** removals 311 → 295, and 9 more rows reach the packager, including "18 years ago ... Satoshi registered
    Bitcoin on SourceForge", an attributed report about the Strategic Reserve, and two of the speaker's own trading
    descriptions.
  - All 9 (the 24 h four included) look clean on my reading. Evidence: `pp-ingest_audit/flagcheck_20261113/p1_simulation.json`.

## Proposal (step 2). Awaiting your ruling; nothing applied

**P1: imperative and single_source_breaking. A flag stands only when both models agree.**
- **When the flag stands:** the miner's flag is excluded (L-u) unless a second model, never the line's miner, answers
  "no" to the one narrow question, with your definition in the prompt. "unsure", no answer, an invalid reply, a
  frozen or unavailable checker, or a check not yet made all keep the flag (fail closed, L-j). The miner's `risk` is
  never edited.
- **Implementation on your yes:**
  - **When a line is mined:** the watcher asks the checker role (`flagcheck`, two Heimdall back-ends) about each new
    line's imperative / single_source_breaking flags, before that video's ledger append. The answers go into the line
    (`risk_checks`: answer, model, prompt version).
  - **In the adapter:** the hard-flag rule skips one of those two flags only on a recorded "no" from a model that is
    not the line's miner.
  - **The rows already in the 72 h window:** answered by this run; re-appended with their checks (the latest line
    wins).
  - **Tests:** a missing, unsure, same-model, frozen or failed check never releases a row.
  - **Then:** re-measure after 24 h with this tool.
- **Cost:** about 100-150 questions a day, roughly $0.01 a day. A video with such a flag takes about 30-60 s longer
  to mine.

**P2: accusation. Not yet.**
- **Why:** with your definition as worded, the checker's "no" releases insinuations of manipulation or nepotism
  against identifiable parties. Those are exactly what L-u exists to keep out.
- **What I propose:** you rule a sharpened definition for both models, for example: *accusation = alleges or
  insinuates wrongdoing (crime, fraud, market manipulation, corruption, self-dealing, dishonesty or abuse of office)
  by a person or organisation named in the clip or identifiable from its words, its title or its channel; criticism
  of a strategy, an opinion or a policy alleges no wrongdoing.*
- **What I do next:** re-ask the same 130 questions with it (about $0.01, about 30 min), after adding insinuation
  quotes (fictional names) to the calibration. Then you decide whether accusation gets P1's rule.
- **Until then:** accusation stays as mined.

**P3: option A is not the fix.**
- **Why:** measured above, your definitions in the miner's prompt do not raise imperative or accusation precision,
  and they change which ranges become moments.
- **What it would do:** raise single_source_breaking flags by about 40 % at higher precision, a fail-closed move.
  It is worth doing only if you want the miner to label your broader single_source_breaking. That would be its
  own ruling, and mine/3 with an A/B before switching.
- **What stays:** the miner's "When unsure whether a risk flag applies, set it" is the deliberate fail-closed bias.
  P1 handles its cost after the fact without weakening it.

**Also for the record:** `partner_attack` recall. A creator calling a registered partner's chairman a gambler was
flagged accusation, not partner_attack. P1 does not touch it. Under P2, the sharpened accusation question would
clear it, so partner_attack itself may need the same precision-and-recall check.

## Spend (Heimdall only; the frozen vendors were never called)

| what | calls | $ |
|---|---|---|
| the check: 3 runs together (600 questions, 2 x 24 calibration quotes; first two runs stopped for slowness, their answers reused from the cache) | 757 | 0.0435 |
| choosing the checker: 24 quotes x 4 settings | 96 | 0.0037 |
| smokes (the check: 2 rows; option A: 1 window) | 8 | 0.0015 |
| option A dry run (the miner's own model, 123 windows x 2 arms) | 253 | 0.1773 |
| **total** | | **0.226** |

Basis: each reply's `usage.cost`, failed calls included. Evidence:
- `pp-ingest_audit/spend_by_vendor_20261113.json`
- `pp-ingest_audit/flagcheck_20261113/` (flagcheck.json, FLAGCHECK.md, dryrun_definitions.json, DRYRUN.md,
  checker_choice_calibration.json, p1_simulation.json)

Re-run: `python3 tools/ingest_watch.py flagcheck --max-inflight 8 --transport-retries 0` (answers are cached: a
re-run costs only new questions); `python3 tests/ingest/dryrun_definitions.py --check <flagcheck.json>`.

## Examples (up to 5 per cell; seeded pick 20261113; full rows in flagcheck.json)

#### imperative | miner_yes | checker yes
- `4af82d4384d6340670cf` Bankless, 2026-11-11; miner claude-opus-5-5 flags ['imperative', 'price_prediction', 'time_sensitive'] (windows 1): "And so like the way I kind of see it is I will put on these more longer term overarching thesis through options trades, but then on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76. And that's not necessarily a trade that I want to go in and like cross the spread on options as much for. Um, and so I'm always trading in and out of some of the delta that I have from my options um via per. And so I would say most people should combine both of them."  
  checker: **yes** evidence "And so I would say most people should combine both of them."; The speaker gives a directive: most people should combine both trade types (options and perps), telling viewers how to act financially in their trading.
- `04189add8b472f1e8d92` Scott Melker, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So, to me, I don't really see anything to worry about. I'm very excited to buy these dips."  
  checker: **yes** evidence "I'm very excited to buy these dips."; The speaker states they are excited to buy the dips, conveying the financial action of buying, which meets the definition.
- `324aab69fcc061d39247` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['ad_read', 'imperative'] (windows 1): "Everybody else see on Coinbase, be sure to get the cheapest fees through my link and earn win up to $2 million for the trading you're going to do anyway."  
  checker: **yes** evidence "be sure to get the cheapest fees through my link and earn win up to $2 million for the trading you're going to do anyway"; The imperative 'be sure to get' directs viewers to act: use the link for cheaper fees and earn rewards on their trading, a financial action.
- `925bb460680d74aa7fbe` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "You know, crypto has always been a buy and hold approach and I think that remains the right approach. Um and how this going to shake out, I don't know."  
  checker: **yes** evidence "crypto has always been a buy and hold approach and I think that remains the right approach"; The speaker recommends buy and hold as the right approach, advising viewers how to act financially with their crypto.
- `fbc7f51f686ca1601163` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative', 'price_prediction'] (windows 1): "And you know, if you really like Bitcoin so much, you could always buy it back a lot cheaper. You know, you'll have plenty of opportunities to buy your Bitcoin back substantially lower than it is right now."  
  checker: **yes** evidence "you could always buy it back a lot cheaper"; The speaker advises the viewer they could buy Bitcoin back cheaper, pointing to opportunities to buy it substantially lower, which is a financial action (buy).

#### imperative | miner_yes | checker no
- `efccacd8bc42e4daf1f8` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'imperative'] (windows 1): "Quote, markets already move on Truth Social posts, said Kevin McEntee, interim chief executive officer of TMTG. They're now selling an API that allows a quote real-time feed of the platform's most market [music] moving truths. The company is reportedly charging $100,000 a month and has multiple buyers."  
  checker: **no**; The quote only reports facts: markets move on Truth Social posts, TMTG sells an API, and it charges $100,000 a month. No instruction to buy, sell, hold or act financially.
- `0341e73babc1f4e22f8e` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'imperative'] (windows 1): "Dude, half of it's money laundering. Like I'm not I'm being real. So like that becomes a thing where they're like all it is is a greater fool theory."  
  checker: **no**; The quote only describes money laundering and greater fool theory; it gives no instruction to buy, sell, hold or act financially.
- `b5d6556583b814c5a094` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['ad_read', 'imperative'] (windows 1): "They're the only self-custody by default platform in North America. Yeah, North America. And uh that's why Bitcoin Well team is topnotch. Also, they do have their white glove service over there."  
  checker: **no**; The quote only describes Bitcoin Well's features and praises the team; it gives no instruction to buy, sell, hold or act financially.
- `05b8d78e2a92eaf26a68` BTC Sessions, 2026-11-10; miner claude-opus-5-5 flags ['imperative'] (windows 1): "So what I've been telling people is like, if you aren't using this technology, if you aren't using these large language models to attack yourself, then you should expect that they're going to get used against you, and you're going to be at a severe disadvantage if you haven't been making use of the new capabilities."  
  checker: **no**; The quote advises using technology (LLMs) to avoid disadvantage; it mentions no buying, selling, holding or financial action, so it does not meet the imperative definition.
- `bcbdc047b85057d62bbf` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "Listen to this. Let me give you a sort of sales pitch. I did invest in the company very lucky to >> sold Bitcoin for it actually. This is true story. So, it's a first rotation where I was like, "Whoa, I just let go of my prize jewel.""  
  checker: **no**; The speaker only recounts past personal actions (invested, sold Bitcoin, let go of prize jewel); no instruction to the viewer to buy, sell, hold or act financially.

#### imperative | miner_no | checker yes
- `5767ba900538628c293f` CNBC Television, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "LOOK MSCI HAS BEEN ON A MULTIYEAR CAMPAIGN AGAINST DIGITAL ASSETS. AND IT'S INTERESTING BECAUSE THEIR ROLE IS TO BE AN INDEPENDENT ARBITER OF THE MARKETS NOT PICKING WINNERS AND LOSERS. AND THEY'VE CLEARLY DECIDED THAT BITCOIN ISN'T SOMETHING THAT PEOPLE SHOULD BE INVESTING IN."  
  checker: **yes** evidence "THEY'VE CLEARLY DECIDED THAT BITCOIN ISN'T SOMETHING THAT PEOPLE SHOULD BE INVESTING IN."; The quote states people should be investing in Bitcoin, conveying a financial action (investing) to the viewer, meeting the definition.

#### imperative | miner_no | checker no
- `3959d7c70701a3bc6896` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "Are they recovering the losses? This is the big question going on right now. Is Binance liquidating their users to recover those losses?"  
  checker: **no**; The quote only poses questions about Binance recovering losses and liquidating users; it gives no instruction to the viewer to buy, sell, hold, or act financially.
- `22f18e2fa3042ab8da50` BTC Sessions, 2026-11-10; miner claude-opus-5-5 flags ['accusation', 'doom', 'single_source_breaking', 'time_sensitive'] (windows 1): "So Bitcoin infrastructure has been completely ransacked. While a vulnerability is core lightning liquid hack BTC server capped off with the largest exchange Binance, being hit by the largest heist of any kind of all time at 6.3 billion."  
  checker: **no**; The quote only describes hacks and the Binance heist; it gives no instruction to buy, sell, hold or otherwise act financially.
- `bc7bf5e71d9f4554232f` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc'] (windows 1): "What's wild about the PSL or Party for Socialism and Liberation is that it is essentially organized and run by a man based in Shanghai named Neville Singham. He's an avowed Marxist who's funded nonprofits here in the United States that are anti-American and pro-CCP to the tune of $278 million."  
  checker: **no**; The quote only describes the PSL, Neville Singham, and his $278 million in nonprofit funding; it gives no instruction to buy, sell, hold, or act financially.
- `241bfaee53b5bee735a1` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I mean, you've got the same coins I've got. Like you've got BTC Sh, you got XPTt or whatever. But like the the like kind of the ignorance to what's actually happening felt like very gaslighty."  
  checker: **no**; The quote only states that the listener has the same coins as the speaker and comments that the ignorance felt gaslighty; it gives no instruction to buy, sell, hold or act financially.
- `f674e35be2656986ea12` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "They have officially chosen Avalanche Blockchain to settle tokenized stocks. At its core, what the New York Stock Exchange has decided to do is put the Avalanche blockchain at the center of their new infrastructure play for tokenized equities and 24/7 trading."  
  checker: **no**; The quote only reports facts about NYSE choosing Avalanche; it gives no instruction to buy, sell, hold or act financially.

#### accusation | miner_yes | checker yes
- `403f762b59fde51f942e` Bitcoin Mechanic, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I'm not saying we're perfect. I'm saying that the community around Blake2B has the actual integrity and humility to say of course we can screw stuff up. We just need to and having that mentality is just so important. That's why I see the beauty I do see in the in the Blake 2B chain. And I don't and again the the the pathological dishonesty I see back in SHA 256 is it's only getting worse because no one is taking them to task over it."  
  checker: **yes** evidence "the the the pathological dishonesty I see back in SHA 256 is it's only getting worse because no one is taking them to task over it"; The quote attributes 'pathological dishonesty' that is 'only getting worse' to SHA 256, an identifiable entity, alleging wrongdoing, with no one taking 'them to task'.
- `9fcd1656b45fa9a1891d` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "One of these investors in TMTG is Don Wilson, who weeks prior had the SEC enforcement case against his crypto company Cumberland dismissed with prejudice. Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal. TMTG is largely owned by Donald J."  
  checker: **yes** evidence "the SEC enforcement case against his crypto company Cumberland"; An SEC enforcement case against the named company Cumberland implies alleged wrongdoing; the quid pro quo issue is also raised.
- `1de632dab9335c9c100d` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): ">> So, a man that just left the White House is telling us that the last administration sold Bitcoin in ways that looked designed to hurt the price. So, if this has happened before, who would want Bitcoin cheap right now?"  
  checker: **yes** evidence "the last administration sold Bitcoin in ways that looked designed to hurt the price"; The identifiable 'last administration' is alleged to have sold Bitcoin in ways designed to hurt the price, i.e. deliberate conduct amounting to wrongdoing.
- `9cdf8b72eb50664c43fa` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Some new data is circulating that is suggesting that the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump. And let's not forget Binance recently saw a recordbreaking $6.3 billion hack."  
  checker: **yes** evidence "the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump"; The quote suggests an identifiable organisation, the world's largest Bitcoin exchange, may be responsible for Bitcoin's recent dump, hedged by 'could be' but still an allegation.
- `edb9fcbe1b3562c5501f` TFTC, 2026-11-11; miner claude-opus-5-5 flags ['accusation', 'politics_non_btc'] (windows 1): "And we were actually very close to a deal like that that would have gotten conservatives more than they ever could have dreamed. Cuz when there was the mass deportation mandate in the beginning of the Trump administration, the left-wing open borders think tanks were ready to make a deal. You know who blew that up? Donald John Trump with his own scaling back of the anti-, you know, illegal immigrant metric."  
  checker: **yes** evidence "You know who blew that up? Donald John Trump with his own scaling back of the anti-, you know, illegal immigrant metric."; The quote attributes fault to a named person: Donald John Trump blew up the near deal by scaling back the metric, which is wrongdoing by an identifiable individual.

#### accusation | miner_yes | checker no
- `00c4fbc5da052487e949` Simply Bitcoin, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "It it's a pretty pretty, you know, I would say lackluster kind of FUD or disagreement with Bitcoin when he is the authorized participant of the Black Rockck ETF, which is the best performing ETF for Black Rockck. Like, he's making a ton of money off Bitcoin and yet he still comes out and says, you know, I don't really like it. It's like, okay, cool, cool story, bro."  
  checker: **no**; The quote merely describes an identifiable person's lackluster disagreement/FUD with Bitcoin despite profiting from it; it criticizes but does not allege wrongdoing.
- `aa0de859851aebbcd0ea` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I can't tell you why, but when one venue keeps forcing liquidations while spot demand keeps getting stronger, that isn't a normal market. And once that pressure stops, spot usually shows you where price wanted to go all along."  
  checker: **no**; The quote attributes the behaviour only to 'one venue', unnamed and unidentified; no specific person or organisation is named, so it does not meet the definition of an accusation.
- `bb072f70e2ae0ffcbece` The Bitcoin Layer, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "We know that the ECB president, Christine Lagarde, just left the institution very recently. Maybe she wanted to get out ahead of some more dangerous events going on in the European financial system."  
  checker: **no**; The quote only notes Lagarde's departure and speculates ('Maybe she wanted...') about her motive; no fault or misconduct by any named party is alleged.
- `c62c26c16bf870c757a1` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "We're from Wall Street. We wear the suits. We're way more trustworthy."  
  checker: **no**; The quote only makes positive self-claims ('way more trustworthy'); it states no wrongdoing by any named or identifiable person or organisation.
- `e704e4b545366868f2b8` Bitcoin Audible, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc'] (windows 1): "I think it's spooky and you see the lengths that like governments and stuff are going to get hold of people's Bitcoin. wouldn't surprise me if I'm not saying the government themselves are doing it necessarily, but like if they have someone's back and say like, "Look, we're going to turn a blind eye to this because like we're broke and we need some Bitcoin.""  
  checker: **no**; The quote only speculates: 'wouldn't surprise me if' and 'not saying the government themselves are doing it necessarily' — no wrongdoing is asserted, and 'governments' is generic, not named.

#### accusation | miner_no | checker yes
- `fb5462ac859350a4890d` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "One, obviously, don't keep your Bitcoin on exchanges. And two, if you are trading on these exchanges, you should at the very least expect that these exchanges are counterrading you and they are trying to liquidate you because they want your Bitcoin."  
  checker: **yes** evidence "these exchanges are counterrading you and they are trying to liquidate you because they want your Bitcoin"; Exchanges are identifiable organisations; the quote alleges they countertrade and liquidate users because they want their Bitcoin, i.e. they act against users' interests.
- `a5e9ed4abfc5bcbcee5c` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking', 'time_sensitive'] (windows 1): ">> You know what? I I actually I it I will agree with you even though we're talking strategy. I will I will agree with you because I had a conversation today for a podcast coming out next week with someone. I'll just leave it at that. Um, and he actually shared some things he's never shared publicly before, but it was specifically referring to Al Salvador um, with regards to pressure to prevent Bitcoin from being in these positions."  
  checker: **yes** evidence "it was specifically referring to Al Salvador um, with regards to pressure to prevent Bitcoin from being in these positions."; The quote says there was pressure on El Salvador to prevent Bitcoin, alleging improper pressure by an identifiable party in that context.

#### accusation | miner_no | checker no
- `90e7bbb3468bfdcf3cbc` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "Um and thirdly, it has a fixed supply of 21 million which gives it this um you know hedge against long-term debasement trade. Um and if any of those three things are ever called into question then I'd immediately sell all my Bitcoin and buy gold."  
  checker: **no**; The quote only describes Bitcoin's fixed supply and the speaker's selling condition; no wrongdoing by any named or identifiable party is alleged.
- `1d98b77703b3c5fb6651` Simply Bitcoin, 2026-11-10; miner claude-opus-5-5 flags ['imperative', 'time_sensitive'] (windows 1): "Mark Harvey put Bitcoin on the power law curve, a model which is fitted to Bitcoin's entire price history. And on this model, Bitcoin below 76,839 is below its lower level on the power band, which historically has been a great time to buy. It's been when the FTX collapse happened, during the COVID crash, major shocks, and every single time Bitcoin has rebounded powerfully."  
  checker: **no**; The quote only describes Mark Harvey's price model and past market events (FTX collapse, COVID crash) as timing context; it states no wrongdoing by any named person or organisation.
- `ee62d106350a67cc428a` Bitcoin Magazine, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative', 'time_sensitive'] (windows 1): ">> Yeah, I would say that Bitcoin life insurance is 40% on sale. Uh, so they should go and they should go and buy a life insurance policy with us."  
  checker: **no**; The quote only promotes a product, saying Bitcoin life insurance is 40% on sale and urging people to buy a policy; it alleges no wrongdoing by any named or identifiable person or organisation.
- `c9fe4a64430c294a05f0` DataDash, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "We've seen an almost 20% decline. And so, we're at, you know, obviously when we're looking for more de-risking and a little bit of more scale out into strength type of situation."  
  checker: **no**; The quote only reports a ~20% decline and the speaker's own de-risking/scale-out strategy; no wrongdoing by any named or identifiable person or organisation is alleged.
- `a25c69cf74aa3d0111cc` Bitcoin Magazine, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So that's good news. You can sell your Bitcoin and at least you can buy the dip in gold."  
  checker: **no**; The quote only gives advice about selling Bitcoin and buying gold; it names no person or organisation and alleges no wrongdoing.

#### single_source_breaking | miner_yes | checker yes
- `962102c4a2b80420b390` DataDash, 2026-11-11; miner claude-opus-5-5 flags ['single_source_breaking'] (windows 1): "Bitcoin staking on Stacks began its initial institutional rollout in September 2026, and the first bond attracted approximately 230 Bitcoin. The second bond expanded to roughly 505 Bitcoin. And among the early institutional participants were 21 Shares, HashKey Cloud, UTXO Management, and Cipher Capital. And the second bond required approximately 6.75 million Stacks to be paired with the Bitcoin positions."  
  checker: **yes** evidence "Bitcoin staking on Stacks began its initial institutional rollout in September 2026, and the first bond attracted approximately 230 Bitcoin. The second bond expanded to roughly 505 Bitcoin. And among the early institutional participants were 21 Shares, HashKey Cloud, UTXO Management, and Cipher Capital. And the second bond required approximately 6.75 million Stacks to be paired with the Bitcoin positions."; Speaker reports specific new facts—dates, BTC amounts, named participants—about the recent Stacks institutional rollout, with no cited source, so it rests on this speaker alone.
- `4bac36830b753fb0a66e` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'politics_non_btc', 'single_source_breaking'] (windows 1): "Uh, it would appear that uh our our everybody's current favorite uh CEO um of Nvidia uh he had another affair. >> No."  
  checker: **yes** evidence "it would appear that uh our our everybody's current favorite uh CEO um of Nvidia uh he had another affair"; Speaker reports Nvidia's CEO had another affair, a current-event claim with no cited source, so it rests on this speaker alone.
- `64ab8aa47797d93e6a93` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Binance has been liquidating everyone over and over since the hack. Open interest rate builds and a wick takes the book out."  
  checker: **yes** evidence "Binance has been liquidating everyone over and over since the hack."; The speaker, citing no other source, asserts as fact that Binance has repeatedly liquidated traders since the hack — a current-event claim resting on this speaker alone.
- `44918e1456e858d64101` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "And like in like when the red team were doing their thing, they obviously scanned every repo on Bitcoin, found no critical vulnerabilities. Like I think Rob came out and said libec what P or whatever that that repos."  
  checker: **yes** evidence "when the red team were doing their thing, they obviously scanned every repo on Bitcoin, found no critical vulnerabilities"; Reports a current event: a red team scanned all Bitcoin repos and found no critical vulnerabilities, sourced only to this speaker.
- `9fcd1656b45fa9a1891d` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "One of these investors in TMTG is Don Wilson, who weeks prior had the SEC enforcement case against his crypto company Cumberland dismissed with prejudice. Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal. TMTG is largely owned by Donald J."  
  checker: **yes** evidence "Now in response to my request for comment, Cumberland denied any quid pro quo and connection between the Trump Media investment and the SEC's dismissal."; Coffeezilla reports his own finding: Cumberland told him directly it denied quid pro quo, a new factual claim about the recent SEC dismissal resting on his sole reporting.

#### single_source_breaking | miner_yes | checker no
- `c1f47e2329192118b0bd` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "And uh, and this can include your Bitcoin wallets, your keys. So, uh, we'll talk about what is affected and what you should do."  
  checker: **no**; The quote only says wallets and keys can be included and promises to discuss what is affected; it states no specific new factual claim about a current event.
- `b7ae3de139f9e3db388b` Yahoo Finance, 2026-11-11; miner claude-opus-5-5 flags ['single_source_breaking', 'time_sensitive'] (windows 1): "And it has been reported by uh ex White House advisor Patrick Whit that Trump remains interested in buying Bitcoin for US Strategic Reserve, but legal and custody issues stall process progress."  
  checker: **no**; The claim is attributed to another source, not this speaker alone: 'it has been reported by uh ex White House advisor Patrick Whit', so it fails the resting-on-this-speaker-alone test.
- `9cdf8b72eb50664c43fa` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'single_source_breaking'] (windows 1): "Some new data is circulating that is suggesting that the world's largest Bitcoin exchange could be responsible for Bitcoin's recent dump. And let's not forget Binance recently saw a recordbreaking $6.3 billion hack."  
  checker: **no**; Quote attributes claim to circulating data, not speaker alone; second sentence is background, not new breaking claim.
- `d3579c7d953ba27163f1` CoinDesk, 2026-11-12; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "I'm waiting on this rotation narrative to emerge and I've been hearing it in various corners that you know after the anthropic IPO, there's not many huge AI related IPOs uh waiting to to happen, right? At some point, uh, AI kind of ends its Cambrian explosion phase, just like we saw with the ICO era and altcoins and memecoins and Bitcoin. Um, and then capital rotates to back to fundamentals or back where uh taking on that risk yields the highest reward, which we all hope will be Bitcoin."  
  checker: **no**; The quote offers speculation about a future rotation narrative, not a new factual claim about a current event; it's the speaker's opinion and prediction.
- `88deba3b23f5f865cfc3` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['single_source_breaking'] (windows 1): "18 years ago on November 9th, Satoshi registered Bitcoin on SourceForge. Now, look at that date. I saw the tweet that day and thought, "Oh, that's interesting.""  
  checker: **no**; The quote recounts a historical fact from 18 years ago (Satoshi registering Bitcoin on SourceForge) and the speaker's past reaction, not a new factual claim about a current event.

#### single_source_breaking | miner_no | checker yes
- `bbd396e76827e34df5c9` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "So, Binance is in a very tricky position right now where they've been around for the longest, but a new upstart, someone that literally worked at Binance started a new exchange, Hyperliquid, and everyone is starting to use Hyperlid because they don't trust Binance. So, Binance is in a strange position right now."  
  checker: **yes** evidence "someone that literally worked at Binance started a new exchange, Hyperliquid, and everyone is starting to use Hyperlid because they don't trust Binance"; The speaker alone asserts the current facts that a former Binance employee launched Hyperliquid and users are shifting to it, citing no other source.
- `224912640684b56b0bb9` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I'm talking about all the the other ones where they basically done pipe investments to pump their stocks. Now they're down in the dirt really bad, but they're also now very humbled because they're like, "Okay, I thought we had it all sorted out."  
  checker: **yes** evidence "they basically done pipe investments to pump their stocks. Now they're down in the dirt really bad"; Speaker alone asserts unnamed companies did PIPE investments to pump stocks and are now down badly; a current-state factual claim with no cited source, resting on him alone.
- `e5085743fab00640c4e8` BTC Sessions, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "So again things are looking a little bit worse there getting a little bit bubbly but also on top of that wanted to throw in there we had the Binance hack from not that long ago and it turns out that the Binance CFO apparently has resigned. So another interesting kind of apparently I was finding that there was some information they had planned to resign for a while but again a little suspicious exit."  
  checker: **yes** evidence "it turns out that the Binance CFO apparently has resigned"; The speaker reports the Binance CFO's resignation as recent news without naming any other source, so the new factual claim about a current event rests on him alone.
- `e2168822533fa0b919b3` Bankless, 2026-11-11; miner claude-opus-5-5 flags ['imperative', 'time_sensitive'] (windows 1): "And so like the way I kind of see it is I will put on these more longer term overarching thesis through options trades, but then on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76. And that's not necessarily a trade that I want to go in and like cross the spread on options as much for. Um, and so I'm always trading in and out of some of the delta that I have from my options um via per."  
  checker: **yes** evidence "on a day like you know yesterday for example, you know, Bitcoin at 70, you know, 52 might have been a really interesting per long just for a quick scalp up to back up to like 76"; Speaker cites yesterday's Bitcoin price (~70,52) as a scalp opportunity to ~76, a new factual claim about a current event resting on this speaker alone.
- `c9adac7e64b60e33cc7e` TFTC, 2026-11-11; miner qwen/qwen3.8-27b flags ['accusation', 'time_sensitive'] (windows 1): "I mean, my world, Bitcoin, crypto. The fact that he launched the Trump coin uh the night before the inauguration was completely insane to me, but obviously the reports of Susie Wild's children getting very cushy lobbyist jobs um very close to the administration, it's I mean, they just created such easy soft targets on their backs for when the blue Nami eventually hit."  
  checker: **yes** evidence "The fact that he launched the Trump coin uh the night before the inauguration"; Speaker asserts as fact that the Trump coin launched the night before the inauguration, a current-event claim presented on this speaker's own authority.

#### single_source_breaking | miner_no | checker no
- `a185e29f61267d834b5c` Simply Bitcoin, 2026-11-11; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "And of course, keep buying that Bitcoin, keep hodling that Bitcoin, keep storing that Bitcoin. This is how we win."  
  checker: **no**; The quote is a motivational call to action (keep buying, hodling, storing), not a new factual claim about a current event, so it rests on no factual assertion at all.
- `8dfa9df7dbfcb31507b1` CoinTelegraph, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): "So if you think about it, stablecoins are going to continue growing regardless of what happens in crypto or even in AI. Stablecoins are just one of these omnipresent trends. Doesn't really matter."  
  checker: **no**; The quote offers a general opinion/prediction that stablecoins will keep growing, not a new factual claim about a current event, so it does not meet the definition.
- `241bfaee53b5bee735a1` What Bitcoin Did, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "I mean, you've got the same coins I've got. Like you've got BTC Sh, you got XPTt or whatever. But like the the like kind of the ignorance to what's actually happening felt like very gaslighty."  
  checker: **no**; The quote only offers opinions about shared coins and a feeling that things are 'very gaslighty' - subjective commentary, not a new factual claim about a current event.
- `4fd92203561233275a66` Coffeezilla, 2026-11-12; miner qwen/qwen3.8-27b flags ['accusation'] (windows 1): "And one [music] of them is the crypto stuff. The crypto stuff's nuts."  
  checker: **no**; Only a vague opinion, 'The crypto stuff's nuts'; no specific factual claim about a current event, so it does not meet the definition.
- `4f74babec484b3b240f0` Altcoin Daily, 2026-11-12; miner qwen/qwen3.8-27b flags ['imperative'] (windows 1): ">> Uh yeah, I I would just say look, I mean, I I've said this many times like have a plan stick to it. You know, some people will use this analysis and then go panic sell their Bitcoin and then they get mad when it rallies back up, you know, a few thousand dollars. It's happened several times over the last two, you know, month and a half or whatever."  
  checker: **no**; General advice ('have a plan stick to it') and a repeated pattern ('happened several times over the last... month and a half'), not a new factual claim about a specific current event.
