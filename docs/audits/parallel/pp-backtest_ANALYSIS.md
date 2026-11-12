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
