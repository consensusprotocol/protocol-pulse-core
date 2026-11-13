SPEND (ruling 48): $5.85 of $12.00 vendor-reported after the 07:14 build (+ the estimate where a vendor reports none; no build starts at $10). 07:37 ET: no pin yet. The 07:14 build gave NO LINE-UP (cause below). The next build carries ruling 49 (6a36025a) and the one-token fix (60f2eaed). Two proposals for you below.

## 07:37 ET: the 07:14 build (code e8c622b8): no line-up; the measured cause, and two proposals

Record: tests/package/proof/ledger_20261113_121442. It ran 45 + 44 + item 42's cut fix + ruling 48 (not yet 49).
- **The funnel:**
  - 173 usable; 113 left out by STAND_ALONE (34 back as trimmed variants);
  - 13 cleared step A (90 s): ruling 48's guard works, with no SpendLimit;
  - 9 pass L-v 2 + CUTTABLE; 6 can open;
  - **7 clear step A from BOTH vendors (45)**: Heimdall refused 1 (NOT_OWN_SINCERE), and 1 trim failed its cut
    ("So if": co-articulated).
- **The angle step took until 1277 s:** deepseek and qwen both missed 300 s, then Grok answered (item 46 again).
  The second-vendor screen took about 8 min for one 8-excerpt Heimdall call.
- **NO LINE-UP in any of the 3 angles, so nothing was judged ($0.58 reported for the whole build).** Measured:
  - Grok built all 3 angles from the SAME 4 of the 7 clips. The Bitcoin Layer (4.8 s), What Bitcoin Did ("I will bet
    you one Bitcoin that RSA...", 9.46 s) and Bitcoin Mechanic (7.26 s) were offered and never used.
  - Two of those 4 are the SAME SPEECH on two channels: CNBC Television (13.94 s) and Strategy (MicroStrategy), which
    re-posted the CNBC interview (13.82 s): "I don't really think Bitcoin and crypto are partisan issues...".
  - The 4 cannot form a line-up:
    - hook 8.76 s + the two copies = 36.52 s, short of the 36.7 s floor (and the same speech twice);
    - the 6.93 s clip may only play LAST, but the proposer placed it mid-order.
  - Ruling 41's search swaps only after a JUDGED line-up fails, so a "no line-up" angle never reaches it.
- **The trim "So MSCI didn't force..." failed step A this time (REFERENT_OUTSIDE)** after clearing it at 05:48. Its
  batch differed, and the fresh verdict differed.
- **Proposal 1 (yours to rule):** when an angle's own moments cannot form any line-up, complete it from the WHOLE
  cleared pool by score. That is ruling 41's swap applied to the missing places, with the angle's hook and play order
  kept and every line-up rule unchanged. Here, adding any of the three unused clips would have reached the seconds.
- **Proposal 1, measured on the 07:14 pool (prepared and tested in a scratch copy, NOT committed or used):** all 3
  angles get a line-up (36.89 s, 43.78 s, 36.77 s). Each adds Bitcoin Mechanic (7.26 s) as the HOOK: the angle's own
  hook ("My biggest fear is that I go to the bank...") does not name Bitcoin, so it cannot open (the hook's topic
  rule), and the next opener by its first 2 s comes from the pool, as ruling 41's hook swap would choose it. Scope: an
  angle's FIRST line-up only; a re-line after a drop moves on to the next angle, as now. Two of the 3 still pair the
  CNBC / Strategy copies, hence Proposal 2.
- **Proposal 2 (yours to rule):** the same speech re-posted by a second channel (equal text, different channel)
  counts as ONE moment before the angle step, keeping the original publisher's. Without it, the angle writer keeps
  building on the pair.


## 07:19 ET: rulings 48 and 49 are committed (audits 0707 and 0712, 2 cycles each); the chain builds

- **48 (e8c622b8):** this order's ledger is capped at $12.00 vendor-reported. The estimate counts only for a call
  whose vendor reports none (providers.Router limit_basis="reported"). At $10 a build refuses to start (exit 3) and
  the chain stops; I tell you here. Each build records spend_ruling_48 {before, after} in its package.json.
  - The running total by your rule was $5.26 at 07:02, not $3.46. The $1.81 difference is the estimate for calls with
    no vendor figure: speech-to-text, and Heimdall calls abandoned at the 300 s deadline (booked at their upper bound).
  - A build that starts below $10 can still spend up to its own $3 reported search budget (ruling 41). The $12 cap is
    the hard stop.
- **49 (6a36025a), which I did: PENDING AT THE RENDER.** The render's clip scorer is gemma3:27b through Ollama on
  Ultron's GPU0 (run_fresh.stage_validate -> story_semantics.LocalLLM, temperature 0). This builder may use no GPU,
  and no other box I may use serves that model, so the same scorer cannot run here.
  - (a) Every trimmed clip says "scorer_pending": true in the pin. It is sealed, and refused on any other clip.
  - (b) A line-up and a pin carry at most ONE trimmed clip (lineup_for, both swaps, the no-voice added clip, the pin).
    The limit is raised only when the integrator reports the first trimmed clip affirmed at validate, and on your
    word.
- **The integrator is told** (07:20): the scorer_pending key; their scorer judges every trimmed segment at validate;
  please report the first affirmation.
- **The chain (chain4):** the first build started 07:14:42 on e8c622b8. Later builds run on 6a36025a. It stops on a
  pin, or at the $10 line.


## 07:10 ET: what dropped step A from 13 to 4 (your 07:12 question): the OLD cap, nothing cached

- **The 07:02 build was not under ruling 48.** It was the old chain's automatic build on the committed code
  (8355bbd5), whose guard was still the $40 price-table cap. Ruling 48's guard was written and in audit (0707), not
  committed. I have stopped that chain, so no build runs on the old cap again.
- **Measured on its record (ledger_20261113_120240):**
  - 16 of the 24 screened moments: "STEP_A_UNAVAILABLE: SpendLimit". The reservation was refused before any call was
    made, which is why step A took seconds.
  - The other 8 were real verdicts (4 cleared, 4 REFERENT_OUTSIDE), from one batch whose identical prompt the reply
    cache served.
- **Nothing was cached as a verdict, so there was nothing to purge.**
  - The record's step_a.json holds exactly those 8 verdicts.
  - No file in the reply cache carries a failure.
  - The code stores answers only. providers.Router.call records a reply only after a back-end returned non-empty text.
    prescreen stores only parsed verdicts (`db[...] = a` for `got`), and an exception lands only in that build's
    `fails`.
- **The same 13 -> 4 at 06:31, 06:41 and 06:47:** also 16 SpendLimit each. In addition, the 24 h window moved (176 -> 173
  usable, 115 -> 113 left out), as its oldest rows aged out.



## 06:25 ET: order 06:22: the answers owed (42, 43, 46) and the plan for 45 / 44

### Item 42 (ruling 33 part 2): 36 of the 115 come back as trimmed variants; 0 reached a line-up, because of a gap on MY side

Record: tests/package/proof/ledger_20261113_104817 (05:48, code 1d928276). The 06:18 build
(ledger_20261113_111825) gives the same counts.
- **Why every log still says "115 left out":** the original moments stay out by design. A trimmed variant joins the
  usable moments as a NEW candidate (id "<id>~trim"), so that log line does not show the comeback. The next audited
  change adds the count to it.
- **36 of the 115 come back with trimmed_leading:** 15 "so", 14 "and", 6 "but", 1 "now".
- **The other 79 cannot:**
  - 48: left out by the topic rule alone, with no trimmable opener;
  - 25: an opener AND the topic rule, and the trimmed text still fails the topic rule;
  - 4: an opener outside the six words ("because" x3, "then" x1);
  - 2: "And so ...": the trimmed text opens on "so", and the ruling trims ONE word.
- **Of the 36:**
  - 8 were among the 24 moments step A screens (PRESCREEN_N, by rank score); the other 28 were never screened;
  - 6 of the 8 failed step A (5 REFERENT_OUTSIDE, 1 NOT_OWN_SINCERE);
  - 2 cleared, and both passed L-v 2 with the trimmed word heard before the clip;
  - **both then failed my trimmed-cut measure: "no cut before the hook: 'So' does not end a sentence".**
- **That failure is my gap, not the moments'.**
  - My pin-stage onset measure still plans the IN edge with the old whole-sentence rule.
  - The render's sentence law (c6605895; unchanged on the integrator's branch since) does two things the pin stage
    lacks: it plans a trimmed cut at the measured pause after the trimmed word (trimmed_boundary), and it checks the
    onset on the audio as cut (trimmed_onset).
  - The fix mirrors those functions verbatim at the pin stage. It is being built now, and no build uses it before its
    2-cycle audit.
- **The fix, measured (06:42 ET, before its audit):** the render's functions, copied verbatim, on the two cleared
  variants' own L-v 2 windows:
  - "So MSCI didn't force any Bitcoin selling this week..." (Coin Bureau): PASSES (a). The cut sits in the measured
    pause after "So"; the audio as cut opens in quiet (first onset 130 ms, 83 ms fade). It could even open the medley.
  - "So if you look at the average income..." (What Bitcoin Did): stays out. "So" runs straight into "if" (60 ms, no
    measured pause): the render's own rule says it cannot be cut cleanly.
- **Correction to the line above: even with the fix, no trimmed clip can be sealed yet.** Ruling 33 (b), the render's
  clip scorer, runs only on GPU0, which this stage may not use. So the pin stage keeps (b) STRICT
  (TRIM_SCORER_PENDING = False, as committed at 1d928276): a line-up with a trimmed clip fails STAND_ALONE and is
  never built. **Your yes/no on my 05:44 question decides it:** may a trimmed clip be sealed with the scorer's
  verdict PENDING AT THE RENDER (which holds the pin at validate, before any cut, if the scorer refuses)?
- **One flag (K2), nothing changed:**
  - One of the 36 ("Now, this has been the major target zone...") was left out by the TOPIC rule only, not by its
    opener.
  - Trimming "Now," lets the render's topical() accept it as completing the previous claim ("this" + a figure).
  - "now" is one of the six words, so this is inside the ruling's literal terms. Say so if trims should apply only to
    moments the OPENER rule left out.

### Item 43 (measured on the 04:41 record): angle 2's "no line-up" is NOT a channel shortage (moved up from below)

- **The supply:** the 11 cuttable moments sit on **9 channels**: What Bitcoin Did, CNBC Television, Altcoin Daily,
  Bitcoin Mechanic, Strategy, Coin Bureau x3, Scott Melker, Simply Bitcoin and The Bitcoin Layer. Together they hold
  116.9 s. Widening the window is not needed for channels.
- **Angle 2 offered 4 of them:**
  - The Bitcoin Layer, 4.8 s (the hook);
  - Coin Bureau, 19.5 s (cannot open, G17a);
  - Altcoin Daily, 6.9 s (cannot open);
  - What Bitcoin Did, 9.5 s.
- **Why no line-up:** lineup_for keeps the proposer's PLAY ORDER (L-y 3), and a clip under 8 s may play only LAST
  (SHORT_CLIP_S). In that order, the 6.9 s clip sits mid-line-up; without it, the other clips total 33.8 s (< 36.7 s);
  with What Bitcoin Did as the hook instead, the clips total 35.9 s (< 36.7 s). The binding rules are the seconds
  range, the short-clip position and the fixed play order, on only the 4 moments the angle offered. Over every
  permutation of those 4, 2 orders would fit (a short clip moved last), but neither is the proposer's order.
- **For 41:** the line-up step only sees each angle's 4 moments, not the 11. The search swaps a below-bar segment for
  the next by score from the whole cleared pool.

### Item 46: why Grok wrote the angles in the 05:48 build

- **The code already does what you order.** angle_write is Heimdall deepseek, then Heimdall qwen, then xai Grok. The
  router gives EACH back-end 300 s, Grok included (providers.Router.call applies deadline_s to every back-end).
- **05:48:** both Heimdall writers missed the deadline, so Grok was used:
  - deepseek gave no answer within 300 s and was abandoned;
  - qwen gave no answer within 300 s and was abandoned;
  - Grok answered in 166 s.
- **The angle step took about 766 s (300 + 300 + 166), not 1058 s.** The "1058 s" in the log is the build's own
  clock when the step ended; the step started at about 290 s.
- **The cause is deepseek's reasoning length.** Its answers on this prompt (reply capped at 3,000 tokens):
  | build | seconds | output tokens (mostly reasoning) |
  |---|---|---|
  | 03:39 | 219 | 9,155 |
  | 04:41 | 293 | 12,806 |
  | 05:26 | 285 | 12,229 |
  | 05:48 | over 300 (abandoned) | not returned |
  | 06:18 | 240 | 9,462 |
  - It writes about 42 tokens/s, so any answer over about 12,600 tokens misses 300 s.
  - In the 06:18 build it answered in time, and the angles came from Heimdall.

### Items 45 and 44: for the next build

- **45 (first):**
  - After L-v 2 + CUTTABLE and before the angle step, every cuttable clip gets step A from BOTH vendors.
  - The chains hold only two vendors: step A (context_verdict) is xai Grok, then Heimdall deepseek; angle_write is
    Heimdall first, Grok last.
  - A clip that fails either screen is out before any angle, with its reason.
  - Whichever vendor then writes, every clip already has a passing verdict from the other one.
  - In the 05:48 build, every verdict came from xai; Grok then wrote, so the only passing line-up had to be
    re-screened on Heimdall after its write, and one clip failed.
- **44 (the safety net):**
  - If a re-screen after a write still fails a clip, only that clip goes, for good and with its reason.
  - The next-best cuttable clip is swapped into its place (ruling 41's swap).
  - The clips-alone verdict re-judges the new line-up, then the build goes on to the writer.
  - A passing line-up is never discarded for one replaceable clip.
- Each gets its 2-cycle audit, then the chain rebuilds.

### The 06:18 build (code 1d928276): no package

- Same supply as 05:48: 13 cleared step A, 10 cuttable, 6 can open. The angles came from deepseek, in time.
- Both line-ups judged were the same 3 clips (angles 1 and 3). Both failed on the HOOK, rated 3, with the clips rated
  5 and 5: item 3 again. After that, no swap and no line-up fit the rules.
- A small defect, flagged (K2) and not yet changed: the same line-up was judged twice, because "dropped" is kept per
  angle. A cache keyed on the exact line-up saves that call (about $0.01).

## 06:36 ET: BLOCKED ON SPEND: the 06:31 build failed step A on the builder's own cap; your ruling is needed

- **What happened:** the 06:31 build (ledger_20261113_113101, code 1d928276) screened 24 moments at step A. 16 got
  "STEP_A_UNAVAILABLE: SpendLimit" and 4 failed REFERENT_OUTSIDE. 4 cleared; 2 of them passed L-v 2 + CUTTABLE, from
  fewer than 3 channels: no package.
- **The guard:** tests/package/proof_ly.py LY_LIMIT_USD = 40.0, by the price-table ESTIMATE (an upper bound). I set
  it at 20:30 Nov 12 because no budget was stated (STATE said so then). Every paid call also reserves its upper bound
  while in flight.
- **This order's ledger (tests/package/proof/SPEND_LY.json), by back-end:**
  | back-end | calls | estimate | vendor-reported |
  |---|---|---|---|
  | xai grok-4.20 | 228 | $30.11 | $3.34 |
  | heimdall deepseek | 70 | $7.87 | $0.09 |
  | heimdall qwen | 6 | $1.23 | $0.03 |
  | elevenlabs scribe (STT) | 98 | $0.29 | none (estimate only) |
  | **total** | 402 | **$39.49** | **$3.46** (+ $0.29 STT estimate) |
- **Your budgets since then are per build and per package, in vendor-reported dollars:** ruling 41, $3.00 reported
  per build ($10 estimate ceiling); ruling 5, $1.50 per package ($5 estimate). build() enforces both. No running total
  was ever ordered; mine is the only one, and it binds now.
- **Proposal (yours to rule):** raise this order's cap to $60 by the estimate (about $2 more vendor-reported, at the
  measured ratio of about 1/11), or name a running total in vendor-reported dollars and I re-base the guard on it.
  Until you rule, no build can pass step A, and I change nothing about the cap.

## 06:56 ET: item 42's cut fix is committed (audit 0710, 2 cycles); one trimmed clip now passes (a)

- **What changed:**
  - The pin stage now plans a trimmed clip's IN cut the way the render does: after the trimmed word, inside its
    measured pause. It then applies the render's own onset rule to the audio as cut, with one extra 10 ms frame.
  - The functions are copied verbatim from the integrator's sentence_law.py at c6605895: trimmed_boundary,
    trimmed_onset, edge_plan(trimmed=...) and three helpers. Untrimmed moments are judged exactly as before.
  - A trimmed moment is out at any place when its trimmed cut fails (ruling 33 (a)). Its hook lead decides only
    whether it may OPEN the medley.
- **Measured on the 05:48 build's two cleared trims:**
  - "So MSCI didn't force any Bitcoin selling this week..." (Coin Bureau) passes (a): cut in the pause after "So",
    83 ms fade, first onset 130 ms. It could also open the medley.
  - "So if you look at the average income..." (What Bitcoin Did) stays out: "So" runs into "if".
- **What still blocks a trimmed clip:** (b). The pin stage keeps the clip scorer's verdict strict, because the scorer
  runs only on GPU0. Your yes/no from 05:44 decides.
- The funnel table now names the trimmed variants (FUNNEL.md: "[So trimmed] ...") and lists the moments actually
  offered to the angle step.

## 06:50 ET: ORDER 06:22 items 45 and 44 are committed (audit 0640, 2 cycles)

- **45:** after L-v 2 + CUTTABLE and before the angle step, every cuttable clip is screened by step A on the second
  vendor too (the batches run in parallel: about 3 min on Heimdall). A clip that fails either vendor, gets no verdict,
  or gets one from the first's vendor is out before any angle, with its reason (package.json:
  prescreen.second_vendor). After the angle call, each clip's verdict is the one off the writer's vendor. In the
  05:48 situation (Grok writes), the Heimdall verdicts already exist, so there is no re-screen after the write.
- **44 (the safety net):** a re-screen after a write that fails a clip, or gives no verdict, removes only that clip,
  for good, with its reason (prescreen.rescreen_failed). Ruling 41's swap puts the next-best cuttable clip in its
  place, the clips-alone verdict re-judges, and the build goes on to the writer. With the two configured vendors this
  path cannot trigger: every write stays on the angle's vendor.
- **Fixed on the way (K2, flagged by me, confirmed by the audit):** the old re-screen kept a clip's STALE verdict
  from the writer's vendor when the re-screen call returned nothing for it. No verdict is now never a pass.
- **The trade-off, your order's own design:** when Heimdall's step A disagrees with xai's, or Heimdall is down at
  that moment, a clip leaves BEFORE the angle step. The angle writer sees fewer clips, and a Heimdall step-A outage
  ends the build early.
- **Item 46, one option (yours to rule, nothing changed):** deepseek writes 9-13k reasoning tokens per angle call at
  about 42 tokens/s, so it lands at 219-293 s or misses 300 s. A lower reasoning effort on the angle call would keep
  the angles on Heimdall in time.

## 03:16 ET: the 03:12 rulings, status (one audited change each; the integrator's render must change for 33, 34 and 37)

| ruling | my side (the pin stage) | render side (the integrator, main tree) |
|---|---|---|
| 33, part 1: run stage_validate's STAND_ALONE at the pin stage | DONE: change A (audit 0310, 2 cycles). The check is stand_alone.check_edl, byte-identical to main's, with no scorer. | none |
| 33, part 2: trim ONE leading but/and/so/well/now/yeah | NOT STARTED: it cannot render yet. | BLOCKED. G16 / write_lock_cut_table lock WHOLE sentences, so a trimmed clip is held. Their STAND_ALONE scorer must also be asked about trimmed clips. The integrator agrees with the shape (pin carries trimmed_leading and the untrimmed sentence start; the IN cut sits in the measured pause), but builds it only on YOUR order. |
| 34: no_bitcoin regex retired for clips; the medley names Bitcoin once | DONE on both sides. The render merged at 55315124; the pin side is audit 0426 (2 cycles, all three SHIP yes). The pin seals the miner's screen (moments_package.btc_screen, mine.py@8e6afb61); the line-up runs the render's check_edl with it, and the medley must say bitcoin/btc once. | BLOCKED: their stand_alone.topical requires EVERY segment to name Bitcoin. The integrator needs your order. |
| 35: too_many_sentences retired | DONE (audit 0335, 2 cycles, all three reviewers SHIP yes): recorded only, never rejects. | none: no sentence cap in run_fresh, pinned, sentence_law, editorial_gate or edl_rules. |
| 36: layout_ineligible stays | no change | none |
| 37: a question ending allowed in the HOOK role only | DONE on my side (audit 0500, 2 cycles): a hook may end on '?', a clip may not; the join after a question hook must be followable (no bridge), or the line-up is re-lined. The integrator's R1 is in audit; until it merges, a question-hook pin holds at validate. | BLOCKED: their edl_rules R1 NO_QUESTION_HOOK refuses a hook that ends on "?", the exact opposite. The integrator needs your order. |
| 38: IN edge, a 4 s pad before; a sentence end OR a measured pause >= 700 ms; a file-head start counts | DONE (audit 0338, 2 cycles). The pause is measured on the independent recogniser's word timing, as the ruling words it; the acoustic check of the cut stays the render's (check_cut_acoustics / G16). Want an acoustic confirmation at the pin stage too? Say so. | none (mine) |
| 39: OUT edge, the L-v 2 number canonicaliser | DONE (audit 0338). Both edges also read the occurrence nearest the clip's own time, not an earlier or later same word. That closes a fail-open the audit's test exposed. | none (mine) |
| 32: snap outward to whole sentences, <= 20 s, one speaker | DONE (audit 0332, 2 cycles). SNAP_GUARD retired: the exclusion verdict, step A and L-v 2 judge the added words. A snapped moment's price prediction is counted. A caption speaker marker inside the span keeps it out. Measured on today's 510 rows: 12 come back (4 eligible on screen), 23 stay out over 20 s, 1 for a marker, 35 do not anchor. | none (mine) |
| 40: the miner's "imperative" label | yours to pp-ingest | - |

- **Order.** You ordered 33, 34, 35, then a rebuild. 33's trim and 34 cannot produce a renderable pin until the
  integrator has your order. So I rebuild after change A + 35, then do 38, 39 and 32 (all mine, all effective at once),
  and do 33's trim, 34 and 37 when the render side is ordered. Say so if you want otherwise.
- **Speaker credits:** the integrator's delivery texts already credit the channel name and never guess a person
  (merged at 785c374a, per the integrator).

### 05:44 ET: ITEM 42 (the trim) is built and in audit; ONE QUESTION for you before it can seal anything

The pin side of ruling 33 part 2 is built and tested, with the render's contract as merged at c6605895:
- trimmed_leading and untrimmed_start, sealed only when present;
- variants of the opener-left-out moments;
- (c) step A on the trimmed span;
- L-v 2 with the trimmed word heard before the clip;
- (a) the acoustic onset at the trimmed cut, at any place.

Audit 0530, cycle 1: four real defects found and fixed; cycle 2 running.

**The question (the reviewers split on a standing law):**
- (b) needs the render's clip scorer. It runs on GPU0; this session may not use any GPU. So at the pin stage, the
  scorer's verdict on a trimmed segment cannot be measured.
- The build seals the segment with that verdict listed as PENDING in the sealed stand_alone row ("scorer_pending").
  The render asks its scorer at validate, fails it closed without a verdict, and holds the pin before any cut (the
  integrator: "a run slot, not a bad video").
- grok calls this indefensible under L-m ("nothing measured is never a pass"); qwen says the pin must be sealable this
  way.
- **Do you rule YES: a trimmed segment may be sealed with the scorer's verdict pending at the render?**
  - If yes: I commit 42, rebuild, and report how many of the left-out openers come back.
  - If no: trims cannot be sealed at the pin stage at all, and item 42 waits for a scorer the pin stage may use.

### 05:35 ET: the first build with ruling 41's search (05:26, code bfac353e): every HOOK rated 3. The bar decides

Record: tests/package/proof/ledger_20261113_102658, with FUNNEL.md. Funnel and search:
- 313 moments -> 176 usable -> 16 cleared step A -> 11 L-v 2 + CUTTABLE -> 7 can open -> 3 angles (heimdall
  deepseek, in time);
- the SEARCH judged 4 line-ups of 8 and spent $0.06 reported ($0.71 estimate);
- **every one failed the clips-alone verdict on its HOOK, rated 3, with the clips rated 4-5**:
  | angle | hook (channel: first words) | ratings | through-line the verdict stated |
  |---|---|---|---|
  | 2 | Coin Bureau: "Michael Saylor just had a pretty rough day..." | hook 3, 4, 5 | "Setbacks and risks in traditional finance ... demonstrate Bitcoin's resilience" |
  | 2 | Coin Bureau: "The funds are selling strategies stock..." (swapped in) | hook 3, 5, 4 | "Bitcoin is a resilient alternative to traditional finance..." |
  | 3 | The Bitcoin Layer: "Bitcoin started turning though before liquidity turned red..." | hook 3, 4, 5 | "Bitcoin shows resilience amid liquidity shifts..." |
  | 3 | Bitcoin Mechanic: "Bitcoin on the Blake 2B chain is incredible..." (swapped in) | hook 3, 4, 5 | "Perspectives on Bitcoin's value, market movements..." |
- The search ended at 4: once the clips rated 4-5 were kept in place, no further hook swap fit the line-up rules
  (seconds, channels, onset), and each angle's re-line found no line-up in its own moments.
- **Finding for your ruling (item 3 again):** the clips-alone verdict (MEDLEY_PROMPT) rates the HOOK on "how much it
  advances that through-line", like a clip, with the same bar of 4. A hook is a setup line: four different hooks scored
  3 while their clips scored 4-5. The bar is unchanged per your order. Whether the hook should be rated on its own job
  ("grabs attention and sets up the medley") is yours to rule.
- Next: ruling 42 (the trim) is in audit, then a rebuild. YouTube is clear since 05:25.

### 04:54 ET: the 04:41 build, ruling 34 in: no package; the binding gate is now the clips-alone verdict

Record: tests/package/proof/ledger_20261113_094156 (code 56582b6b), with FUNNEL.md. Funnel:
- 313 moments -> **171 usable** (95 before ruling 34);
- 113 left out by the render's STAND_ALONE: 64 openers, 49 with no place under the topic rule with the screen;
- 2 ad-read early -> 16 cleared step A (24 screened) -> 11 L-v 2 + CUTTABLE -> 8 can open;
- 3 angles from heimdall deepseek, in time.
Both line-ups tried failed the CLIPS-ALONE verdict (MEDLEY_PROMPT):
- angle 1: "no through-line a viewer can state" (the hook rated 3);
- angle 3: the ratings failed (hook 3, a clip 2), re-lined, then no line-up.
**This is item 3 of your 02:45 order: the verdict demands one through-line with every clip rated at least 4 on how
much it advances it. That is the old shared-story strategy, and now the binding gate.** Your ruling decides it.
The stage-1 losses now:
- layout_ineligible: 52 (36 alone; DEC-12d, it stays);
- not_statement: 35 (26 alone; ruling 37 brings back question-ending HOOKS);
- opener: 22 (11 alone).

Ruling 33 part 2 is merged at the render (11e361cc). My pin side is blocked: the render's scorer must affirm every
trimmed segment, and the pin stage has no GPU (see above).

### 04:42 ET: the 04:22 build (code a3e8bd65): a line-up passed the clips-alone verdict, then the WALL BUDGET cut it

Record: tests/package/proof/ledger_20261113_092234, with FUNNEL.md. Funnel:
- 510 rows -> 313 moments -> 95 usable (39 opener, 2 ad-read early) -> 17 cleared step A -> 12 L-v 2 + CUTTABLE ->
  8 can open.
- The angle step took until 671 s: both Heimdall writers were abandoned at 300 s each, then xai grok answered.
- Angle 1, line-up 1: the clips-alone verdict failed (one clip rated 1).
- Angle 3, line-up 1 (3 clips, 41.8 s): the clips-alone verdict PASSED at 888 s.
- Its write ran past the 900 s wall: "stopped in angle 3 of 3: 1133 s of 900 s wall / $0.42 of $1.50 reported".
- **This is the second build in a row lost to writer latency, not to any integrity gate.** The 03:39 build's
  deepseek angle took 224 s, close to the 300 s deadline, and 2 of the last 3 builds' angle calls timed out on both
  Heimdall writers. Your ruling on ruling 5's wall budget (asked at 03:41) is now the binding decision.
- The next build (04:41, code 56582b6b) adds ruling 34's wider supply.

### 03:48 ET: the 03:39 build, every effective ruling (A, 35, 38, 39, 32): no package; the bottleneck moved

Record: tests/package/proof/ledger_20261113_083956 (code 2564f64e), with FUNNEL.md. Funnel:
- 510 rows -> 262 moments (13 of them snapped by ruling 32) -> 76 usable;
- 32 "But"-type openers left out (change A);
- 24 screened at step A (PRESCREEN_N) -> 17 cleared -> **12 pass L-v 2 + CUTTABLE** (8 before 38/39; the 5 lost are 4
  two-speaker L-v 2 fails and 1 yt-dlp fetch error, NOT MEASURED) -> 9 can open;
- 3 angles from heimdall deepseek (in time).

What happened next:
1. Angle 1, line-up 1 (4 clips, 37.6 s) passed the clips-alone verdict, and write 1 passed the cheap checks.
2. The exclusion screen then refused its hook. The deterministic ad-read screen found "link in the description" in
   the sentence right before the hook.
3. The angle was re-lined, and none of the 3 angles could form a line-up inside the medley's seconds and channel rules.
   No package.

Two defects found, flagged (K2) and not yet changed:
- **Reporting:** when every angle ends with "no line-up", build() leaves why_none = None (the log reads "no package
  (None)"). It should name the reason. A small change; it goes in the next audited change.
- **Order:** the deterministic ad-read screen (free, no vendor call) runs only at the package stage, after the angle was
  built around the moment. Running it with step A would keep doomed moments out of the angles.

The chain was restarted at 03:47 ET: it builds after each worker cycle, on committed code only.

### 03:41 ET: the 03:21 build (change A + ruling 35), and three findings for your ruling

Record: tests/package/proof/ledger_20261113_082157 (code e29a958f). Funnel:
- 510 rows -> 178 moments -> 57 usable;
- 19 left out as "But"-type openers (change A);
- 24 screened at step A -> 17 cleared -> 8 L-v 2 + CUTTABLE (old 1.5 s windows) -> 6 can open -> 3 angles.
- NO PACKAGE: "stopped in angle 1 of 3: 907 s of 900 s wall" (ruling 5's per-package wall budget).

1. **WRITER LATENCY ATE THE WALL BUDGET (not integrity).**
   - The angle call went to heimdall:deepseek-v4.1-flash and was abandoned at the 300 s deadline.
   - Then heimdall:qwen3.8-27b was abandoned at 300 s.
   - Then xai:grok answered. Step A + L-v 2 had used 204 s, so 907 s were gone before a line-up was tried.
   - At 03:39 ET a 1-line probe of deepseek answered in 1.8 s, so the gateway is up and the full angle prompt hung.
   - Options for your ruling (budget policy is yours, ruling 5):
     - (a) the wall budget counts from the angle step, or excludes calls abandoned at the deadline;
     - (b) a timed-out writer is skipped for the rest of the run;
     - (c) a shorter angle deadline. The 02:37 deepseek angle took 164 s, so I would not go below 240 s.
2. **STEP A SCREENS AT MOST PRESCREEN_N = 24 MOMENTS (not integrity).** 38 moments were eligible and 24 were screened,
   so 14 usable moments were never judged. Step A costs about $0.01-0.02 per batch of 8. Raise the cap?
3. **no_bitcoin is now the biggest stage-1 loss: 57 moments, 45 for that reason alone (ruling 34's case).** It stays
   blocked until the render's STAND_ALONE topical rule changes, because that rule needs every segment to name Bitcoin.

The 03:39 build has every effective ruling (A, 35, 38, 39, 32).

### Change A (ruling 33 part 1, audit 0310)

- package.stand_alone_check runs check_edl(rate=None) with subject bitcoin/btc on every candidate line-up
  (lineup_for(need_stand_alone=True)).
- A sealed "stand_alone" gate row is required for a medley (package_pin.MEDLEY_GATES).
- A moment that opens on a conjunction or reply fragment can be neither a clip (no scorer here: fail closed) nor a
  hook. It is left out before any vendor call (out["no_role"]).
- On the held pin's texts it gives the render's own verdicts: hook PASS, clip_01 FAIL, clip_02 FAIL.
- d2657bbe cannot be re-sealed: without its two "But" clips, 16.4 s from 2 channels remain.

(The status line before this was "FRESH PIN READY: d2657bbe", 02:54-03:00 ET.)

## 02:56 ET: FUNNEL TABLE (orchestrator 02:45 item 1)

**Record.** The table is taken from the 02:37 build, tests/package/proof/ledger_20261113_073738 (code 2cc6c0a3, render
clock 07:37:38 UTC). That build ended in the pin above. It was read from the record only, with no vendor spend:
inputs.json, package.json, step_a.json and package.log. Two things were recomputed offline:
- the stage-3 edge reasons, from the RECORDED scribe replies (Router replay=True; a miss raises, nothing is fetched);
- the pause levels, from the cached L-v 2 WAVs (CPU).

The full output is in the record as FUNNEL.md and FUNNEL_pre_edge.txt. The two scripts that made them (funnel.py, pre_edge.py) are committed with the ruling-32 change, under its audit.

**Upstream: pp-ingest's adapter excluded 175 rows before the 507.** My recount of the adapter's own rule on the ledger
(same since, now and 24 h horizon) gives the same 123 hard-flag rows. A row can carry several flags; "alone" counts
the rows that flag alone excludes.

| lost | alone | exact reason | one example |
|---|---|---|---|
| 73 | 59 | hard flag `accusation` (L-u, the miner's risk label) | "Some of my experiences, even in just the Bitcoin community of interacting with economic hitmen, whether that be at the B…" |
| 28 | 21 | hard flag `imperative` (L-u) | "So if you think about it, stablecoins are going to continue growing regardless of what happens in crypto or even in AI." |
| 13 | 8 | hard flag `single_source_breaking` (L-u) | "And I think where this is particularly timely is I think we have just witnessed in 2026 an operation Ajax 2.0 in Iran, y…" |
| 9 | 3 | hard flag `partner_attack` (L-u) | "Uh like this Sailor fanboyism where uh in chapter eight of the Bitcoin Sanders, it says there's only one way to own Bitc…" |
| 7 | 4 | hard flag `ad_read` (L-u) | "Your Bitcoin secured across five keys three on hardware from different vendors, one on your phone and one held by Casa." |
| 6 | 5 | hard flag `guaranteed_return` (L-u) | "I mean, look, when I came into crypto, Bitcoin was on the order of a thousand, a couple thousand dollars. So since then,…" |
| 6 | 5 | hard flag `third_party_media` (L-u) | ">> You know, it's not that important to us. It's a fairly dimminimous amount of capital that they control. We think we t…" |
| 30 | - | altcoin or not about Bitcoin (the miner's flags) | n/a (the adapter keeps no example) |
| 22 | - | speaker change inside (caption marker, L-v 1) | n/a |

**Stage 0: 507 ledger rows -> 70 moments (437 not moments)**

| lost | exact reason | one example |
|---|---|---|
| 332 | SUPPLY: waits for its OWN window record (the word-pass worker has not reached the row) | n/a |
| 71 | SUPPLY: no word record yet (none in the store, no sentence-ready window record) | n/a |
| 15 | duplicate: the same speech as a kept moment (time overlap in one video, L-p) | "The number one way to compromise anything is through social engineering. And so what that means is Bitcoin has the software…" |
| 12 | not whole sentences of the word record: more than SNAP_WORDS = 3 words of its edge sentences fall outside it (RULING 32'S CASE) | "But you talk to someone in Venezuela and they're like, wait, oh, you're like, oh, it's volatile. It's like, what do you mean…" |
| 7 | the row's text does not anchor in the word record (sentence_law.anchor) | "Um, but we're willing to underwrite Bitcoin going down 80%. We put cash on the balance sheet. So it's kind of like you mix…" |

The 12 ruling-32 rows, as words of their edge sentences outside the anchored text (before / after):
- 0/6, 0/9, 9/0, 0/11, 0/11, 2/12, 16/0, 0/32, 0/39, 0/47, 0/47, 0/57.
- This is not "0 before / 6 to 12 after" for 11 rows: 2 rows snap backward, and 5 rows need 32-57 more words.
- Each snapped span must be measured against the 20 s clip limit before it is used (see ruling 32 below).

**Stage 1: 70 moments -> 23 usable (47 lost).**
- A moment is out on screen only when it fails BOTH as hook and as clip, so the CLIP role's flags are the binding
  reasons.
- "alone" = the moments that this flag alone keeps out (lifting only it brings them back).

| moments | alone | exact reason (clip role) | one example |
|---|---|---|---|
| 17 | 11 | `no_bitcoin`: the words do not match the regex `\b(bitcoins?\|btcs?)\b` (T11, the old story selector's subject screen) | "There's eight and a half billion people. We all have a money problem. It's not like we sort of maybe have a money problem." |
| 17 | 7 | `too_many_sentences`: more than 3 sentences (T9, the old selector's MAX_WINDOW_SENTENCES) | "Like, you know, I've run a Bitcoin meetup for 10 years now. And I've interacted with thousands of Bitcoiners, as I'm sure you have, Giacomo…" |
| 16 | 7 | `layout_ineligible`: the channel has a burned-in chyron (registry has_chyron, DEC-12d) | "But the headline sounds far, far, far worse than what's actually happening, right? The cycle ran on time and the calendar split it…" |
| 7 | 3 | `not_statement`: ends on a question | "I believe open source will win, and I believe Bitcoin will win too. Will that help us find our way back to each other, to nature, and to God?" |
| 4 | 1 | `opener`: opens on a pronoun or reply word (stand_alone.opener) | "Well, every time Nvidia has taken a hit over the last month, Bitcoin has gone down with it. It doesn't match point for point…" |
| 3 | 3 | over the 20 s per source video (L-u) | "Can Bitcoin front run it perhaps? But I believe Bitcoin does need the dollar to come back down…" |

**Stage 2: 23 usable -> 9 cleared step A (14 lost; L-s on each moment's own context)**

| moments | alone | exact reason | one example |
|---|---|---|---|
| 9 | 9 | `REFERENT_OUTSIDE`: a word refers outside the clip AND resolving it changes the assertion. All 9 were judged "changes: yes"; none failed on an uncertain answer. | "Now if a board can take a founder's company from him in four days, it's worth asking who c…" ('him' -> 'Jensen Huang') |
| 5 | 5 | `NOT_OWN_SINCERE`: 4 ad reads and 1 hypothetical | "In the world of Bitcoin, security isn't just a feature. It's the entire foundation." (view: ad_read) |

**Stage 3: 9 cleared -> 4 pass L-v 2 + CUTTABLE (5 lost)**

| lost | exact reason | one example, measured |
|---|---|---|
| 3 | CUTTABLE IN edge: "the window starts at the clip: no word before it" | "I don't really think Bitcoin and crypto are partisan issues, right?…" The L-v 2 window starts 1.5 s before the clip (PAD_S). The audio there is the tail of a word, then ~1.0 s at -54 to -59 dBFS (a pause). The recogniser heard no word in the pad. |
| 1 | CUTTABLE OUT edge: "the recogniser has no '68000' within 0.8 s of the clip's end" | "…down around 67 to 68,000." The recogniser wrote "sixty-eight thousand." ending at 9.48 s; the clip ends at 9.44 s; its next word is "James". L-v 2 itself passed this clip. |
| 1 | L-v 2 FAIL: two speakers measured inside ("Mm-hmm" by a second speaker) | "Bitcoin is like a place where you come. Like, you know, the Bitcoin, everyone gets Bitcoin at the price they deserve…" |

The 3 IN-edge losses, exactly:
- **CNBC Television GXWj2JO9bz8 and Strategy xfLi0cH_VqM.** Both carry the same speech, "I don't really think
  Bitcoin and crypto are partisan issues". Both have a measured ~1.0 s pause before the clip.
- **What Bitcoin Did acxge3Orsv8, clip at 2.35 s.** These are the episode's first words. Nothing is spoken before them
  in the file. The window starts at 0.85 s, so it does not reach the file head.

**Stage 4: 4 cuttable -> 3 can open (G17a at the pin stage).** One moment did not pass: "0 ms of genuine quiet before
the hook's first onset < 90 ms" ("But we have very rarely in Bitcoin's history seen six negative weeks…"). It stayed in
play as a non-hook clip and is clip 1 of the pin.

**Stage 5: the angle step.** 4 moments were offered (42.34 s, 3 channels), and the step gave 3 angles from
heimdall:deepseek-v4.1-flash. Then:
- angle 1, line-up 1 (3 clips, 37.5 s): clips alone PASS 5/4/5, with one flagged join;
- write 1: fidelity FAIL (the takeaway was COMMENTARY);
- write 2: fidelity, context and coherence PASS -> PIN.

**What rejects moments for reasons that are not integrity.** This is my reading of the table; you rule. Integrity rules
stay hard, and nothing below is changed without a ruling.
1. **Stage 1 `no_bitcoin` (17 moments, 11 alone).** It is a literal regex from the old story selector. Every one of
   these rows already passed the miner's about_bitcoin screen at the adapter. That screen is pp-ingest's BTC_SCREEN,
   which also counts sats, Satoshi, halving, hash rate and self-custody. The regex misses words such as "Bitcoiners".
2. **Stage 1 `too_many_sentences` (17, 7 alone).** It is the old selector's 3-sentence cap. The hard limit is 20 s per
   clip (L-u), and usable() checks that separately.
3. **Stage 1 `layout_ineligible` (16, 7 alone).** It is a presentation decision (DEC-12d, burned-in chyron), not
   integrity. It is a standing PBX decision, so it is yours to rule.
4. **Stage 1 `not_statement` (7, 3 alone): ends on a question.** A question can be a hook.
5. **Stage 3 IN edge "no word before it" (3).** The rule itself is integrity: the independent recogniser must show a
   sentence end before the clip. The loss comes from the measurement window (PAD_S = 1.5 s), which ends inside a
   measured pause. Measuring a longer window before the clip is a measurement change, not an acceptance change.
   - The third case is an episode's first words. The window would have to reach the file head, and you would rule
     whether a clip that starts at the first word of the file counts as a sentence start.
6. **Stage 3 OUT edge "no '68000'" (1).** The edge matcher compares raw word prefixes, so "sixty-eight thousand." does
   not match "68,000.". L-v 2's own comparison canonicalises numbers and passed this clip. This is a matching defect,
   flagged (K2) and not changed.
7. **Upstream `imperative` (28, 21 alone) and `accusation` (73, 59 alone).** These are the miner's labels, and they are
   L-u hard laws at pp-ingest's adapter. The imperative example above ("So if you think about it, stablecoins are going
   to continue growing…") is not an imperative. The label quality belongs to pp-ingest; I only report it.

**The integrity losses (they stay):**
- REFERENT_OUTSIDE 9, NOT_OWN_SINCERE 5, the L-v 2 two-speaker fail 1;
- "does not anchor" 7, duplicates 15 (L-p), over 20 s 3 (L-u);
- the upstream caption-marker speaker changes 22.

## 02:56 ET: THE ANGLE STEP (orchestrator 02:45 item 3)

**What it demands.** These come from ANGLE_PROMPT (pipeline/package.py:429) and check_angles (:531):
1. **A SHARED POINT:** "An angle is ONE sentence a viewer could repeat: a point that several of these clips GENUINELY
   support together (each clip adds a different reason, fact or voice to the same point)." **This is the old strategy
   leaking in.** L-y asks for one takeaway that is true of every clip, not a point that every clip argues.
   - The same demand recurs in two more places. The clips-alone verdict (MEDLEY_PROMPT) passes only with "a
     through-line a viewer can state" and every clip rated >= 4 on "how much it advances that through-line (5 =
     essential, 1 = off topic)". The writer (WRITE_LY) gets "THE ANGLE (the point this video makes)".
2. **"moments: the ids of 4 to 8 clips".** The prompt asks for 4 to 8, but check_angles accepts 3-8.
3. **">= 3 different channels".** The prompt also says "ONE per channel, from 3-5 DIFFERENT channels".
4. **"together 36.7-51.5 seconds of clips".** This is medley_content_range: one takeaway lands the factory's estimate
   in 60-70 s (L-o, hard). lineup_for enforces it again.
5. **The hook:** the first id, "whose FIRST WORDS grab attention AND set up the angle". Each clip also needs a "support"
   note.

**The 02:21 build's 3 moments.** They were Pompliano 16.23 s, Simply Bitcoin 11.58 s and The Bitcoin Layer 4.80 s:
32.61 s from 3 channels.
- **Demand 2 failed (3 offered, 4-8 asked).** Every reply was impossible.
- **Demand 4 failed (32.61 s < 36.7 s).** This one is binding by itself: lineup_for refuses any line-up of these
  three, so no angle, shared or not, could have made a 60-70 s video. The supply was short of seconds; the angle was
  not the bottleneck.
- **Demand 3 was met** (exactly 3 channels).
- **Whether demand 1 also refused is NOT RECORDED.** Both replies (seeds 7 and 8) were out of contract ("exactly
  {'angles': [1-3 items]}": an empty list or more than 3). The router deletes an out-of-contract reply by design, so it
  is asked again instead of served, and the text is not on disk. I did not spend to re-ask, because the seconds
  already decide the outcome.

**The 02:37 build, 4 moments.** The step answered with 3 angles. Each angle is a forced single argument through all 4
clips, for example: "Bitcoin's unstoppable open-source design doesn't prevent rare six-week losing streaks or early
turns before liquidity, so even institutions keep allocations small." Its first line-up passed and became the pin.

**For your ruling (not done; it changes what a check accepts):**
- ANGLE_PROMPT would ask for a hook, a play order and one takeaway that is true of every clip (L-q: not every clip on
  one topic), and for "3 to 8" ids to match check_angles.
- MEDLEY_PROMPT would rate each clip on whether the takeaway is true of it, and on whether the viewer can follow the
  join, not on how much it "advances a through-line".

## 02:56 ET: RULING 32 (orchestrator 02:45 item 2): in progress

The plan:
- implement it in ledger_build.reanchor;
- add tests;
- run a 2-cycle audit before it is used;
- then rebuild.

The facts that shape it:
- **The clip length limit:** the hard limit is SEG_MAX_S = 20 s per clip (L-u). CLIP_S 12-20 and HOOK_S 8-12 only rank
  (L-o).
- **The speaker condition, with a CORRECTION.** Caption records DO carry speaker markers. They are stored HTML-escaped
  as "&gt;&gt;": 454 of 811 records in main's store, 170 of 239 in pp-ingest's store. My earlier "0 of 638" searched for
  the raw ">>" only, so it was wrong.
  - pp-ingest's adapter reads these markers (contract.turn_change_inside). A marker after the span's first token is a
    measured change. No marker is "not measured".
  - Ruling 32 applies the same rule on the snapped span: a marker inside it is a measured speaker change, and the row
    stays out.
  - With no marker, nothing is measured at the snap. Then L-v 2 decides (scribe diarisation: "exactly one speaker
    measured inside"), together with step A's speaker_changes_inside. Both are hard on the snapped span.

(The status line before this was "NO PIN READY", 02:28-02:53 ET.)

## 02:28 ET: FRESH, the 24 h window (in scope: the integrator's reading of the 01:55 order, item 2)

- **02:21 build** (code 6c6e4926: one window per moment, audited; ledger_20261113_072138):
  - 507 adapter rows gave 62 moments on 14 videos (91 windows, every caption record found). 308 rows still wait for
    their own window, and 108 for any word record.
  - 20 usable, 8 cleared step A, 3 passed L-v 2 + CUTTABLE, 3 can open (G17a).
  - Then "no readable angles": 3 moments cannot make a medley angle. No package.
- **Now:** a chain re-runs the same 24 h build after each worker cycle (up to 4), and stops on the first sealed pin.
- **Not changed tonight:** "prefer the newest moments when several line-ups pass" (the integrator, for PBX). The build
  returns the FIRST package that passes every gate, and recency as a tie-break needs its own audited change.
- **Spend:** $1.95 best known of the batch's $6 (SPEND_BATCH $1.113 + the ledger builds since 23:05, $0.839).

## 02:18 ET: the FRESH medley (ruling 2 + the 01:55 order: the last 10 h first). No package yet; supply is the bottleneck

- **The word-pass worker** (the integrator's, GPU1):
  - cycle 1 (01:45): 40 windows from 13 channels, 33 sentence-ready;
  - the 10 h cycle (01:56): 40 windows from 6 channels, 37 ready. Its newest ready source was published 02:57Z.
  - 33 fresh rows still wait for their own window (the next cycle).
- **01:56 build:** no package; it exposed two defects of mine. Both are fixed in 307e2ca7, audited:
  - one window moment without its caption record poisoned its whole step-A batch;
  - 8 of 16 caption records live only in the ledger's own store (pp-ingest's).
- **02:01 build:** no package. Only ONE window per video was used, so 63 of 74 rows could not re-anchor.
- **02:08 build, one window per moment** (in audit 0208): 74 rows gave 32 moments on 6 videos (41 window records,
  every caption record found).
  - 11 usable, 5 cleared step A, 4 passed L-v 2 + CUTTABLE, 3 can open (G17a at the pin stage).
  - The 4 come from 3 channels: Pompliano 16.2 s and 14.1 s (ONE video), Simply Bitcoin 11.6 s, The Bitcoin Layer
    4.8 s.
  - The best one-per-channel line-up is 32.6 s, under the medley's 36.7 s content floor, and Pompliano's two cannot
    pair (the supply exception needs two videos). So there is no line-up, and nothing is paid past the angles.
- **Next:** re-run after the worker's next cycle (the 33 waiting rows, and any new videos). Every gate stays as it is.

## After the 01:39 ET render hold: pin #1 HELD; the hook-onset root cause, measured on the source audio

- **The integrator, 01:39 ET:** run pinned_20261113_054035 HELD, not sent.
  - Held by G17_onset_tail (both formats; the content-integrity row, so the review drop was refused): the prepared
    hook Sjb6lUiL0m4 has 30 ms of quiet lead before its first word, against the 80 ms hook rule (D1).
  - Also failed: G5 (-15.2 LUFS), G9 (BT.601 source) and G18 9:16 (the hook's decode inserts 'when').
  - G20 passed in both formats.
- **Packaging root cause:**
  - T12 (eligibility hook_lead) measured the WORD RECORD's gap before the hook: "markets." ends 3090.35 s, "When"
    starts 3090.75 s, so 400 ms, which passed.
  - The source audio (the L-v 2 window Sjb6lUiL0m4_3089250_3111370.wav, 10 ms RMS frames, acoustic.rms_envelope)
    shows what that gap really holds: breath at about -27 dBFS (3090.41-3090.57), then a run of exact DIGITAL ZEROS
    (-200 dB, 3090.65-3090.77: a hard edit in the source), then speech from 3090.81.
  - Zeros are not room tone (sentence_law: "codec zeros ... are not room tone"), so the genuine quiet before the
    onset is about 20-30 ms, which is what the render measured.
  - The word record's timestamps cannot see an edit like that. Only the audio can.
- **Fix in progress:** a pin-stage HOOK ONSET check with the render's own functions (sentence_law.edge_plan on the
  L-v 2 source audio, then head_tail on the planned cut: G17a's measurement). It is to be sealed and required, so a
  hook like this never reaches a render again. The integrator suggested it in their hold message.

## 00:53 ET: the batch is ONE pin. No second medley passes every gate from the remaining supply

- **Pin #1 is RENDERING** at the integrator: run pinned_20261113_054035, started 00:40:35 ET from main HEAD
  0a645ab4, the pin frozen as data/moments_pins/MOMENTS_PIN_BATCH_B1.json (file sha256 53cb1eff, = ours).
- **Pins #2 / #3: none.** The rebuilds after pin #1 pass every delivered span AND pin #1's spans as delivered, on the
  render clock:
  - fresh_20261112_050611 (b3): 6 pass L-v 2 + CUTTABLE; both line-ups FAIL the clips-alone verdict (a clip rated 2;
    all rated 1).
  - fresh_20261111_190259 (b3): 4 pass; all three line-ups FAIL clips-alone.
  - fresh_20261112_013452 (b3): 4 pass; no line-up fits the medley's seconds and the channel rules.
  - The ingest ledger, run twice (tests/package/proof/ledger_20261113_052637 and _054549; since now - 72 h; the
    three pins as delivered): 6 pass.
    - Line-up 2 (Saifedean Ammous debate, Simply Bitcoin Noq6txZU91c, Stephan Livera) passes clips-alone (5/5/4).
    - First run: the write fails fidelity (COMMENTARY on takeaway, title and caption: "fails speaker_view"), then
      ruling 5's wall budget stops the build (1060 s of 900 s; the angle step alone took 724 s, with one re-ask).
    - Second run: replayed step A and the second pass. The new write passes fidelity and context, then FAILS
      coherence with the takeaway (clip_01 rated 3), as in the 23:05 build. The re-picked line-ups fail clips-alone.
  - The four oldest universes are not built: on their own clocks they already failed on supply (< 3 channels), and
    on the render clock they hold 4-6 usable moments on 2-3 videos.
- **Why:** after novelty (both delivered pins and pin #1) and render-clock recency, every universe keeps 4-7 moments
  that pass L-v 2 + CUTTABLE, from the same few videos, and their line-ups do not hold together. More supply means
  new videos: the integrator's word-pass worker, then the ledger path (ruling 2).
- **Spend:** $1.55 best known of the order's $6 vendor-reported. That is SPEND_BATCH.json $1.113 (estimate $8.67) plus
  the two ledger builds, $0.355 and $0.081 (SPEND_LY.json).
- **Noted, not fixed tonight:** build() leaves why_none empty when every tried line-up fails (192645 b1, the second
  ledger run). The log and the tried list say why; a code change waits for its own audit.

## 00:21 ET: the 00:05 batch (PBX: "new batch!"): pin #1 SEALED and sent to the integrator; #2 and #3 building

**Why every package is a rebuild.** The four named L-y packages reuse delivered moments, so the order's item 2 ("no
moment reused") rules all four out as they are:
- each opens on wdk5JZ9hPzs 3218.1-3221.6, the hook of both 37c5b5f5 and 41f29b1f;
- each carries c1JGheQBPH4 2403.2-2422.1, from 41f29b1f;
- fresh_20261112_001448 is 41f29b1f clip for clip.
They were built with delivered=(). The rebuilds (tests/package/proof_batch.py) run the packager as it stands, so house
style comes in the writer's prompt and the STYLE lint (item 1). Each build:
- uses the RENDER clock (ruling 1);
- passes every clip span of both delivered pins and of the batch's kept packages as delivered (package.usable drops
  any overlap);
- avoids the kept packages' videos where possible;
- stays within ruling 5's budget.

**Results:**
- fresh_20261112_001448: no package. 17 cleared step A, but only 3 passed L-v 2 + CUTTABLE, from < 3 channels.
- fresh_20261111_192645: no package. None of the 3 angles had a line-up that fits the medley's seconds and the
  channel rules (why_none was not filled in; a reporting gap in build(), noted).
- fresh_20261111_190259: no package. The clips-alone check passed, but two writes failed fidelity on a non-takeaway
  line, and ruling 5's wall budget stopped the build at 990 s of 900 s.
- **fresh_20261111_213954: PACKAGE -> pin #1** (814 s; $1.88 estimate, $0.18 best known).
- fresh_20261112_050611 avoiding pin #1's videos: no package (2 moments pass L-v 2 + CUTTABLE, < 3 channels).
  Avoiding videos is therefore not possible on this supply, so videos may repeat across the batch; moments never do.
  050611 is building again with only pin #1's spans out.

**Speakers (item 3; pipeline/speakers.py, audit docs/audits/parallel/pp-selectid_audit_0007/, 2 cycles, no P0/P1):**
- A clip's speaker is named only when the clip or the transcript around it shows who speaks, in a quote checked word
  for word. A title or description naming a guest never names a clip's speaker by itself.
- Everyone the source's lines name is listed with that line, for tags.
- On pin #1 all three speakers are "unknown". Each was measured, and nothing in or around the clips shows who speaks.
  The people named for tagging: Stephan Livera and Joe Burnett; Saifedean Ammous, Jason Hickel and Pavlina Tcherneva
  (a Doha Debates debate); Coin Bureau's description names nobody.

**Seal compatibility (sent to the integrator):** their check_pin_only recomputes seal() from this worktree's
package_pin.py. Every pin sealed before ruling 1 failed that recompute; 6 of 6 recompute again now (SEALED_LATER).

**Spend (SPEND_BATCH.json):** $0.700 best known so far, of the order's $6 vendor-reported ($6.68 by the price-table
estimate).


### #1: tests/package/proof/fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json
- story moments-batch_b1_fresh_20261111_213954-1b4a63d0; package_sha256 1b4a63d0c78005dc768a245959025feaf9636c08746f7711fd8654197cbd9c86; runtime estimate 65.74 s; shape medley
- title: "The crowd feels. The structure holds."
- caption: "the crowd trades feeling. the structure keeps its value."
- takeaway: "The structure does not move with the mood. Most people still price it by the mood."
- bridge after clip 1: "Coin Bureau, on rates and how markets treat Bitcoin." (why: The first clip is about supply and purchasing power, while the next shifts to macro rates and risk sentiment, so the referent is unclear without a bridge.; confirmed by xai:grok-4.20-0309-reasoning)
- sign-off: "Clips today from Stephan Livera, Saifedean Ammous, and Coin Bureau. Go follow them for more. Links are below."
- hook 0: Stephan Livera https://youtu.be/Sjb6lUiL0m4 3090.75-3109.87 s (published 2026-11-11T18:03:23Z; time_sensitive False)
  - verbatim: "When Bitcoin and an asset is going up and the bull market is super hot, everyone loves it. When the bear market is happening and Bitcoin is going down, everyone hates it. And like, that's why the price got high and that's why the price got low, because everyone loved it at the top and everyone wanted exposure and everyone hated it and didn't want exposure at the bottom."
  - speaker: **unknown**: both the host and the guest speak in this episode, and nothing in or around the clip shows which one this is. The source names: Stephan Livera (host): "channel: Stephan Livera"; Joe Burnett (guest): "title: Joe Burnett: Your Wealth Is Melting in the Age of AI | SLP788"
- clip 1: Saifedean Ammous https://youtu.be/vgsSZ4mAHfQ 4664.57-4673.21 s (published 2026-11-10T08:21:50Z; time_sensitive False)
  - verbatim: "Bitcoin shows you that you can just increase the purchasing power. So the value of Bitcoin goes up without the supply of Bitcoin going up. So the people who hold Bitcoin don't get robbed."
  - speaker: **unknown**: multiple people speak in this episode, and nothing in or around the clip shows which one this is. The source names: Saifedean Ammous (host): "channel: Saifedean Ammous"; Jason Hickel (guest): "The Doha Debates hosts Saifedean to debate the nature of money with two MMT economists, Jason Hickel and Pavli"; Pavlina Tcherneva (guest): "The Doha Debates hosts Saifedean to debate the nature of money with two MMT economists, Jason Hickel and Pavli"
- clip 2: Coin Bureau https://youtu.be/UJFQBaMh3yg 191.38-203.06 s (published 2026-11-10T11:33:20Z; time_sensitive False)
  - verbatim: "Now, higher rates make cash more attractive and borrowed money more expensive, which is very much the wrong combo for anything risky, and the market definitely sees Bitcoin as risky."
  - speaker: **unknown**: the transcript does not address anyone by name, the clip has no first-person tie to own work/role/company, and nothing shows which person is speaking. The source names nobody.

**Earlier line 1 (ruling 1 (a), 22:40):** DELIVERING, not a new READY (ruling 1 (a), 22:40): the integrator delivers the 41f29b1f medley REVIEW ONLY, as it is; you tell PBX that clip_02 was 33 h old at delivery. The NEXT READY pin will be the first FRESH medley, built from the ingest ledger once the integrator's word-pass worker (GPU1) marks moments sentence-ready (ruling 2). Every pin from this commit on seals per-segment recency facts (ruling 1).

## 23:22 ET: ruling 2's builder path is BUILT and proven end to end; no package from tonight's ready rows (not fresh anyway)

- **pipeline/ledger_build.py** (audit docs/audits/parallel/pp-selectid_audit_2315/: 4 cycles in 2 rounds, recorded in
  C1_CONSENSUS, C2_DISPOSITIONS, C3_CONSENSUS and C4_DISPOSITIONS; no P0 in any cycle):
  - pp-ingest's own adapter (best_unused_moments, its exclusions applied) runs read-only in its own interpreter. A
    failure, a refusal, a timeout or an unreadable answer raises; it is never read as an empty ledger.
  - The word record is the store's two slots, read by name: punctuated first, then verbatim.
    - Its segments sha is checked, and its WORDS must spell those segments exactly, with segment edges at word edges
      to the ms. The sha covers the segments only, but the clip is cut from the words.
    - A record that names a channel other than the ledger row's is passed over. A corrupt record is a named why,
      never a crash.
    - Every record passed over is named with why.
  - Each row is re-anchored by its TEXT (sentence_law.anchor). The span snaps to whole sentences with at most 3 words
    at an edge, never adding a negation, a near-negation ("hardly" ... "seldom") or a number.
  - The miner's own judge() / record() give eligibility on word timing. Every drop is counted, never a crash:
    malformed rows, rows on a video that names two channels, and duplicates (each named with the moment that kept
    the span).
  - **tests/package/proof_ledger.py:**
    - It builds the medley with the RENDER clock as "now".
    - --delivered PIN ... is required. Every delivered pin's clip spans are out: package.usable drops any overlap,
      whatever the pin's age (L-p).
    - "since" defaults to the newest delivered pin's approved_at. That is ruling 2's "since the last delivered video";
      it was now - 72 h before the audit.
- **For the integrator (store, not this branch):** transcript_sha256 = segments_sha256 covers each segment's [start,
  end, text] only. The words a clip is cut from (rec["words"]) are outside it, in the store's own reader too.
  - ledger_build now ties the words to the sha-checked segments: the text, and each segment's first and last word
    times. All 66 records agree to the ms; none is refused.
  - Word times inside a segment are still outside any hash. The full fix is putting the words in the hash.
- **Live, 23:05 ET** (tests/package/proof/ledger_20261113_0405/; code 88397a53+bd093f16571d, before audit cycle 2's
  fixes; since = now - 72 h):
  - The adapter returned 1,340 rows. 1,127 wait for a word record (caption timing only). 162 re-anchored on 11
    full-video records, and 48 are eligible on screen as a clip.
  - 29 are usable on the render clock. Out: 10 time-sensitive clips from a source over 24 h old, 7 over 20 s per
    source video, and 2 that overlap a delivered moment.
  - Step A cleared 10 moments; 7 passed L-v 2 and CUTTABLE.
  - Of 3 angles, one line-up (angle 2) passed the clips-alone check, with one flagged join after the hook. The writer
    gave that bridge as the intro ("Next, Simply Bitcoin on fiat money and inflation.", the join confirmed by grok),
    and fidelity and context passed. Coherence with the takeaway then rated clip_01 at 3, so it was dropped. The
    re-picked line-up and angle 3's line-up failed the clips-alone check, as angle 1's had.
  - NO PACKAGE: 652 s, $1.80 by the estimate, $0.20 best known. The 11 videos were published Nov 9-11 (UTC), so they
    are not fresh anyway.
- **What the first FRESH medley waits on:** the integrator's word-pass worker writing window records for NEW videos.
  - Its contract (their proposal, accepted): windows under transcripts/<vid>/windows/, readiness in
    moments/word_pass.jsonl, L-s context from the caption record.
  - ledger_build does not read window records yet: a row whose video has only one counts as waiting for a word
    record. That wiring needs the worker's real files; none exist yet (no windows/ dir, no word_pass.jsonl).

## 23:00 ET: the 22:40 rulings, builder items (code audited 2 cycles; 181 tests; regression 0 FAIL)

- **Ruling 1, recency on the RENDER clock: DONE.**
  - Each pin segment carries "time_sensitive" (a bool: package.time_sensitive(), the miner's flag, a recency word or
    a current-kind price) and "source_published_at" ("YYYY-MM-DDTHH:MM:SSZ", UTC). Both are INSIDE the seal.
  - to_pin refuses a segment that misses or malforms either, and cheap_checks fails it earlier (rule RECENCY), before
    any paid verdict.
  - The integrator's pinned.recency_problems reads the same fields: a time-sensitive clip older than 24 h at render
    holds the run. Their check_pin_only imports my package_pin.seal, so they need this commit merged.
- **Ruling 3, the no-voice fallback: DONE.**
  - When a line-up's clips-alone verdict passed with every join followable, and its takeaway failed its gates in both
    writes, the package ships with NO VO line: the clips back to back, then the sign-off. A takeaway whose point
    coherence rates under 4 also counts as a failure.
  - The latest write's title and caption go through every gate again.
  - When the clips fall short of the factory's 60 s, one more clip of the angle is added in the proposer's order, and
    the new line-up is judged on the clips alone again.
  - The pin carries moments_package.no_voice = {why, added_clip, lineup_before} and edl_vo {"intro": null,
    "bridges": []}. The integrator's R11 takes a package with no VO line.
  - Proven by a test that runs the REAL fidelity and context decisions on a no-voice package, every required row
    exactly PASS. That test found and fixed one gap: the pin did not yet carry the no_voice record.
- **Ruling 4:** the rule for a bridge the writer declines stands, unchanged.
- **Ruling 5, budget and deadline: DONE.**
  - Per package: 15 min wall, $1.50 by the vendors' reported cost, and $5 by the estimate as a hard ceiling. Checked
    before every line-up and every write, not only when an angle ends.
  - Every writer call (angle and takeaway) has a 5 min deadline. The router abandons the call (Python cannot kill the
    thread), books its upper bound as spent and fails over: deepseek, then qwen, then xAI grok.
  - The failover is recorded: out["angle_tried"], and attempts[].writer_tried for the writes.
  - Every write stays on the angle's vendor, so the judges always keep a vendor (L-x).
  - When Anthropic / OpenAI credit returns, the writer A/B runs again (not run yet: both still out at 20:32).
- **Ruling 6, house style: DONE.** pipeline/house_style.py has 15 rule ids, each with a must-fail test (23 tests).
  - What it runs on:
    - every line of a medley, inside the cheap gates;
    - a sealed "house_style" row, required for a medley pin;
    - its rules in the writer prompt, with PBX's line as the voice reference ("for its rhythm, never its words").
  - The takeaway's budget is now capped at 20 words (the 30-word cap stays the factory's upper bound), so a medley's
    clips now fill 36.7-51.5 s.
  - The delivered 41f29b1f lines are the must-fail fixtures:
    - caption: 5 rules (lowercase, 26 words, the hedge "may", self-reference, "opportunity");
    - title: 2 (10 words, possessive opener);
    - takeaway: 3 ("What stands out", "which makes", 29 words).
    - PBX's reference line fails only the 20-word cap, as the ruling says.
- **Ruling 2, the ledger build path: next.**
  - The word-pass contract is agreed with the integrator (the integrator's proposal tonight):
    - window records go to transcripts/<vid>/windows/<w0>-<w1>.whisper_words_punct.json, youtube clock, offset
      recorded;
    - readiness is in their data/editorial/moments/word_pass.jsonl, and ledger rows never change;
    - I re-anchor each moment by its TEXT (sentence_law.anchor);
    - L-s context is read from the caption record (>= 90 s before, >= 60 s after).
  - The 378 ledger moments that already have full-video word records sit in 14 videos published Nov 9-11, the same
    videos as tonight's universe. They prove the path but are not fresh. The first FRESH medley waits on the worker's
    window records for new videos.
- **Not re-run:** the 10-universe table above is from the 21:57 code, before rulings 3, 5 and 6. Under house style
  and the 20-word cap the same universes would give different lines, and no-voice packages are now possible. A re-run
  costs about $1-2 by the vendors' own figures and about 45 min. Say if you want it.
- Audit: docs/audits/parallel/pp-selectid_audit_2240/ (C1_CONSENSUS.md, C2_DISPOSITIONS.md). No reviewer kept a P0;
  cycle-2 conditions met. House style was built by a fork of this session as a new module (pipeline/house_style.py)
  and integrated here.

## Superseded at 23:00 ET (the 22:05 READY line, as it stood; delivered per ruling 1 (a))

READY TO RENDER (22:05 ET): tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json.
- An L-y MEDLEY: story moments-fresh_20261112_050611-41f29b1f, seal 41f29b1fee5730fd2eb850ce888f1d22b80fe7b6c368a3dbe31c90d2a75bbc70.
- All 15 gates are exactly PASS (the 13 plus "medley" and "ly_shape"), measured live.
- The deployed factory at main 3426c6f6 accepts it: validate_schema, build_edl, R4 (66.12 s, VO 19 %) and R11 (0
  bridges, 1 takeaway).
- It supersedes the 08:44 pin (37c5b5f5). That pin was rendered as 165629 and sent for review; PBX's verdict on it is
  law L-y.
- Read the RISK below before rendering: clip_02's "right now".

## 22:05 ET: L-y (orchestrator 20:30), the medley is the packager's default. The measurement

**Packages per universe** (tests/package/proof_ly.py; the full table is docs/audits/parallel/pp-selectid_LY_RERUN.md):

| universe | package | bridges | takeaway passed / judged / written | live wall time | $ estimate / $ vendor-reported |
|---|---|---|---|---|---|
| fresh_20261112_050611 (tonight's, the newest) | YES, the READY pin | 0 | 1 / 1 / 1 | about 8.6 min | $0.98 / $0.150 |
| fresh_20261112_013452 | no: clips alone failed twice; the line-up that passed failed coherence with the takeaway | - | 1 / 1 / 1 | 11.1 min | $1.22 / $0.158 |
| fresh_20261112_001448 | YES | 0 | 1 / 1 / 1 | 8.2 min | $0.94 / $0.137 |
| fresh_20261111_213954 | YES | 0 | 1 / 2 / 2 | 9.0 min | $1.56 / $0.231 |
| fresh_20261111_192645 | YES | 0 | 2 / 2 / 2 | 17.9 min (step A fresh) | $1.66 / $0.210 |
| fresh_20261111_190259 | YES (see the footnote) | 0 | 1 / 2 / 2 | 9.4 min | $0.96 / $0.133 |
| fresh_20261110_093150 | no: 4 moments pass CUTTABLE, and no hook + 2-4 clips fit the medley's seconds | - | 0 / 0 / 0 | - | $0.16 / $0.022 |
| fresh_20261107_080503 | no: supply (1 moment clears step A) | - | - | - | $0 |
| fresh_20261107_065702 | no: supply (3 moments pass CUTTABLE, from fewer than 3 channels) | - | - | - | $0.01 |
| fresh_20261106_213852 | no: supply (5 moments clear step A, from fewer than 3 channels) | - | - | - | $0 |

Footnote, fresh_20261111_190259: its first live build was stopped by the per-package budget (05:25 item 5, at twice
the budget) after angle 1, at 869 s; Heimdall's angle call alone took 847 s. A second live build (angle call 279 s)
found the package. Both records are kept: package_ly_budget_stop.json and package_ly.json.

- **Packages:** 5 of 10 universes.
- **Bridges:** 5 needed none, 0 needed one. 10 line-ups were judged on the clips alone first. In the packages, no
  passing line-up had a join a viewer could not follow. The bridge path ran once, in the as-of-now attempt below
  (one join flagged, the bridge offered), and no package came of it.
- **The single takeaway line** (L-y 6, "measure it"):
  - It passed its own gates (VO fidelity's deterministic rules + DUPLICATE + the classifying verdict) in 7 of 9
    judged writes (78 %), 4 of 6 on the first write.
  - Context-integrity failures caused by the VO's framing: 0.
  - The 2 failures were COMMENTARY: an advice- or prediction-like line.
  - Title and caption failures (NAME, NEEDS_SOURCE, COMMENTARY) were the other rejections.
- **Time per package:**
  - Live wall time 8-18 min, mean about 10.8 min, for the 5 packages.
  - The binding cost is the Heimdall writer's angle call: 2.6-14 min (deepseek-v4.1-flash; one call failed over to
    qwen after 11 min).
  - Model-call time summed over every reply a build used: 716 s mean.
- **Dollars per package:** $1.22 by the price-table estimate, $0.17 by the vendors' own figures (xAI ticks, Heimdall
  usage.cost; STT as an estimate). Step A (a once-per-moment screen, about $0.08 real per universe) is not included.
- **What decides the yield:**
  - CUTTABLE (ruling C / 7): of the cleared moments only 3-11 per universe pass the second pass and CUTTABLE. They are
    now measured once per moment before the angle call.
  - Supply: 3 of the 5 misses are older, smaller universes (Nov 6-7).
- **This order's spend:**
  - No budget was stated at 20:30. I capped this order's own ledger (tests/package/proof/SPEND_LY.json) at $40 by
    the estimate.
  - Used: $23.26 by the estimate, which is $2.08 vendor-reported + $0.13 STT estimate. That includes the runs
    restarted after the fixes below and the 22:14 as-of-now build.
  - The 4 audit cycles add about $3.0, at upper-bound prices.

**The READY pin** (fresh_20261112_050611, angle "Bitcoin is the most undervalued asset because it is a global free
market outside government control"):
- **hook:** Natalie Brunell, wdk5JZ9hPzs 3218.14-3221.64 (3.5 s): "Bitcoin imposes a global free market for the first
  time ever." The IN keeps ruling 8's self-repair, as in the 08:44 pin.
- **clip_01:** What Bitcoin Did, c1JGheQBPH4 2403.23-2422.07 (18.84 s): "I mean, the good news about Bitcoin is it's
  not, you know, its success is not dependent upon who's in the White House ... in the U.S. You know, price -wise, some
  people would say when it's when it's persecuted and when it's in the crosshairs, it tends to do pretty well."
- **clip_02:** Stephan Livera, Sjb6lUiL0m4 1826.54-1843.48 (16.94 s): "However, I think Bitcoin is by far the most
  undervalued asset in like the entire global financial system right now. So, you know, Bitcoin gold parity is around
  like $1.5, $1.4 million per Bitcoin last I checked. It's very, very undervalued."
- **THE ONE VO LINE, the takeaway** (29 words, after clip_02): "What stands out is how rare it is for any asset to be
  priced by everyone and controlled by no one, which makes the usual political drama feel irrelevant."
- **sign-off** (the renderer speaks its own, ruling 15): "Clips today from Natalie Brunell, What Bitcoin Did, and
  Stephan Livera. ..."
- **TITLE:** "Bitcoin's overlooked value comes from a market no government owns"
- **CAPTION:** "A market that no single authority can switch off may be the most mispriced opportunity in finance, and that is
  the point this medley builds toward."
- **No intro, no bridge** (edl_vo {"intro": null, "bridges": [the takeaway after clip 2]}).
- **Runtime estimate:** 66.18 s, with 39.28 s of clips. At the voice's measured 2.91 w/s the final should land about
  1.6 s shorter, still inside 60-70.
- **Gates and judges:**
  - The clips alone (grok, blind): through-line "Bitcoin creates a global free market independent of political control
    and is significantly undervalued", clips 5 / 4 / 4, both joins followable.
  - VO fidelity: takeaway, title and caption each class D commentary, every test "no".
  - Context A / B / C: PASS.
  - Exclusion: keep x3. Second pass and CUTTABLE (scribe_v1): PASS x3.
  - Coherence with the takeaway: 5 / 4 / 4, VO point 5.
  - Writer: Heimdall deepseek-v4.1-flash. Every verdict: xai grok-4.20-0309-reasoning.
- **RISK, for the orchestrator before rendering (L-v 3):**
  - clip_02 is flagged time_sensitive ("right now", a $1.4M gold-parity figure). Its source was published Nov 11
    18:03 UTC: 11.0 h old at the universe's time (the universe started 05:06 UTC = 00:06 ET Nov 12; inside L-v 3's
    24 h, so packaging allowed it). At a render tonight it is about 33 h old.
  - Nothing in the deployed render path re-checks recency.
  - The alternative with L-v 3 checked against tonight's clock (--as-of-now) gives NO package:
    - the first live build was stopped by the budget after angle 1 (package_ly_now_budget_stop.json);
    - a second live build at 22:14 ET, with that angle call recorded, tried all 3 angles (package_ly_now.json).
      Angle 1's takeaways failed COMMENTARY twice and context once; angle 2 had no line-up; angle 3's clips alone
      rated the hook 3.
  - So the integrator's option (b) has nothing behind it.
  - For option (c), the per-segment source facts are ready OUTSIDE the seal (the pin is unchanged):
    tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.sources.json, schema pp.pin_sources/1. clip_02:
    time_sensitive true, source_published_at 2026-11-11T18:03:23Z, 11.0 h at the universe, 33.3 h at 22:20 ET. The
    hook and clip_01 are not time-sensitive.
  - The integrator holds the DELIVERY (the render runs) until you choose: (a) deliver as is; (b) the as-of-now
    alternative, now known to be empty; (c) carry the flag and publish time into the caption (their code, audited),
    then deliver.
- **NOTE (context step C, by ruling 3 a note, not STRONGER):** a viewer may take clip_02 as firmer than Livera's
  speculative tone in context. No words of the video raise it, and the clip alone already reads as certain.

**Decisions for you:**
- When the writer declines a bridge at a join the blind check flagged, I drop the clip after that join and re-pick
  (L-y 2: both must agree; L-y 3: a join a viewer cannot follow does not ship). The reviewers split three ways; it is
  pinned by a test either way.
- The per-package budget (05:25 item 5: 360 s / $1.50, stopped at twice that) was set for a fast frontier writer.
  With Heimdall writing, one angle call can take 14 min.
- L-w 2's plain fallback has no L-y form: the old one built an intro and bridges.

**Still open:**
- Ruling 15's request: seal the renderer's own sign-off text.
- Ruling 12's "for next time": budget with the measured VO durations. With one line the gap is about 1-2 s.

**Legs** (20:30: "local/Heimdall/xAI legs; Anthropic and OpenAI credit status: probe once, use if back"):
- **Probe at 20:32 ET:** Anthropic answered HTTP 400 "Your credit balance is too low", OpenAI HTTP 429
  credit_balance_exhausted. Both stay out.
- **Local gemma3:27b:** not used. It runs on GPU0, and this builder never touches a GPU (L-r; the session's standing
  order).
- **Writer (angle, takeaway, title, caption):** Heimdall deepseek-v4.1-flash, with qwen3.8-27b as failover. This is
  the config's own angle_write order once the frozen vendors drop out.
- **Every verdict:** never the writer's vendor (L-x), so xAI grok-4.20-0309-reasoning. That covers step A, the
  clips-alone medley verdict, fidelity, context B / C, exclusion and coherence.
- **Second recogniser:** ElevenLabs scribe_v1.

**The ingest ledger** (20:30: "use the ingest ledger if its adapter is ready"). The adapter is ready as an interface:
pp-ingest's pipeline.ingest.ledger.best_unused_moments, tested. It does not supply this order:
- The live ledger held 2,063 moments from 228 videos at 20:28 ET. All have caption timing (yt_auto 1,883, yt_manual
  180), and 0 are on-screen eligible: eligibility "not_sentence_ready", law L-e needs a Whisper word record.
- That word pass runs on GPU0, which this builder does not use.
- The main store's newest Whisper word record is from 01:13 ET Nov 12. It was written by the fresh_20261112_050611
  run itself, which started 00:06 ET (05:06 UTC); all 11 videos with a word record after its start belong to that
  universe.
- So the newest universe that can be packaged is fresh_20261112_050611, tonight's.

**Code** (pipeline/package.py, package_pin.py, providers.py; tests/package/test_medley.py, proof_ly.py,
pin_and_verify.py):
- **build() is the medley** (L-y 1-6).
- **Before the angle call:**
  - L-v 2's second pass and CUTTABLE run once per cleared moment;
  - the angle proposer sees only moments that pass both;
  - it lists them in play order.
- **Clips alone first:** each line-up gets the blind clips-alone verdict before anything is written. It returns the
  through-line, the clip ratings and, for each join, whether a viewer can follow it.
- **The one bridge:** only at the join that verdict flagged, and only when the writer also judges it necessary.
  - Its record (text, why, confirmed_by) is what the factory's R11 reads.
  - Two flagged joins mean the line-up is wrong, and it is re-picked.
  - When no bridge length fits, it is re-picked with no write paid.
- **The takeaway's budget** lands the factory's own runtime estimate, with or without the bridge.
- **New gates:** "medley" (clips alone) and "ly_shape" (code) join the 13, required for a medley pin.
- **Ledger:** it now records the vendors' own cost (xAI cost_in_usd_ticks, Heimdall usage.cost) beside the estimate.
- **Removed:**
  - write_v3, its two styles, budgets() and plain_vo(): intro + bridges shapes, contrary to L-y 1. plain_vo's title
    test went with it.
  - So L-w 2's "plain factual VO" fallback has no L-y form yet (open).
- **Found by the live run and fixed:**
  - build() accepted a package with CUTTABLE FAIL (an old gap; the pin refused it, fail closed);
  - the driver's per-package spend stop read the shared ledger, so parallel workers were charged for each other's
    calls.

**Tests:** 146 pass, 34 of them in test_medley.py. Every L-y rule has a must-fail case; the build loop has stub
tests. regression_test.sh: 26 PASS / 0 FAIL / 5 WARN.

**Audit:** AUDIT-FIRST, two rounds of two cycles on the actual diff, docs/audits/parallel/pp-selectid_audit_2030/.
Reviewers: grok-4.20-0309-reasoning (xAI), and qwen3.8-27b and glm-5.3-flash via Heimdall at effort none.
- Round 1 (cycles 1-2) ended with all three at "yes with conditions".
- Round 2 (cycles 3-4, on the final diff) ended with all three at "yes with conditions" and no P0.
- Consensus implemented: K1-K8. Refutations, with evidence: C1_CONSENSUS.md, C2_DISPOSITIONS.md, C3_CONSENSUS.md,
  C4_DISPOSITIONS.md.
- Audit spend: about $3.0 at upper-bound prices, direct HTTP, not on the ledger.

**The integrator:**
- Messages exchanged at about 21:00. Its R11 (main d44645dc) takes this shape exactly. My ly_shape now refuses what R11
  refuses: a bridge record whose text is not the line, one without confirmed_by, a record without a line.
- The pin passes the deployed R11.

## Superseded at 22:05 ET by the L-y pin above (the 08:44 line, as it stood)

READY TO RENDER (08:44 ET): tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json. Story moments-fresh_20261112_050611-37c5b5f5, seal 37c5b5f598e97f12a4afd62eccd57f93b946b6f6d7ef087ef1047c1c06bc086f. All 13 gates are exactly PASS, measured live, on the first run (no majority needed). The deployed factory accepts it: validate_schema, build_edl, and rule_r4 at 45 % with the takeaway cap of 30.

## 08:53 ET: ruling 10's question, the builder's ONE list (deployed render path, read-only; agrees with the integrator's 08:42 / 08:49 list)

**Nothing in the deployed path refuses the 08:44 pin as the main tree stands now** (HEAD 1136e56d, clean). Source: a
read-only survey of pinned.py, edl_rules.py, config.py, run_fresh.py, stand_alone.py, gates.py, word_diff.py,
render16.py / render_vertical.py, segment_v1/qa_gates.py and scene_shoutout.py. The items below that bear on this
package I re-read myself.

**Would have refused, now resolved:**
- The clean-tree check at launch (run_fresh.py:296-303) holds a run while pipeline/ or segment_v1/ has a modified
  tracked file. Ruling 10's edl_rules.py / test_edl_rules.py were uncommitted until 1136e56d (08:49). The tree is clean
  now.
- The deployed takeaway cap: 30 since 1136e56d. At HEAD before it, the takeaway took the bridge cap of 20 and 24 words
  were refused.

**Passes:**
- intro 13 <= 30; bridge 18 <= 20 between clips; takeaway 24 <= 30.
- VO share 41.2 % of 45 %; estimated runtime 60.74-61.82 s (60-70 hard). The factory measures its own spans
  (pinned.py:290).
- No cap on total VO words. Clip count 1 hook + 2 clips from 3 channels (needs >= 2 clips from >= 2 channels).
- No minimum clip length or per-channel floor in code (R5 records taste deviations only).
- Stand-alone: clip_01's approved text says "Bitcoin"; the pin label is "bitcoin".
- All three channels are in the registry with handle and avatar. layout_status "pending" is not read by the render
  path (layout "auto").
- The credits card has no channel cap (3 fit: 1180 / 1920 px wide in 16:9, 1219 / 1920 px tall in 9:16).
- Shout-out: the card follows VO 3; nothing is timed against the 3.5 s last clip.
- Title and caption must be non-empty; there is no length limit.
- The pin's fields (sources_30s_before, hook_first_words, *_ok exactly true, the sha256 form) were checked by the
  deployed build_edl in pin_and_verify.
- R1 / R3 / R6 / R8 pass; R7 / R9 / R10 are skipped in validate as in every run.

**Measured only on the render (no refusal predicted; the risk is stated):**
- **G5 final length 60-120 s** (segment_v1/qa_gates.py:721-724):
  - From run 120225's measured parts I estimate 60.7-63.0 s:
    - cuts 8.62 + 10.97 + 4.63 s;
    - VO audio: intro 5.20 s / 13 words, bridge 5.76 s / 18 words, VO 3 of 24 words at the measured 2.4-3.1 w/s;
    - 1 s pre-roll a line;
    - credits 1.8 s + sign-off 8.56 s;
    - outro 4.48 s.
  - The margin over 60.0 is 0.7-3 s.
- **G18 edge words** (word_diff.edges: the first two canonical words, exact, no tolerance in code). This passes only if
  the final's decode does not write the false start ("It w-" / "Bit-"). The integrator's simulation (large-v3 on the
  prepared clip) heard "bitcoin imposes": PASS. With the music bed it is measured at the render (ruling 8: the
  integrator confirms).
- **G14 AV alignment** (>= 3 conclusive samples): clip_02's 4.63 s cut keeps 0.2 / 2.0 / 4.0 / 4.03 s, all on speech.
  There are no dissolves at VO joins (the integrator's 08:49 correction; the sampling code agrees: silent points are
  dropped, only inconclusive ones are retaken).
- **The editorial gate** (a local model's review) and **the vertical layout** (face detection on the prepared clips).
- **The sign-off** is generated at the voice stage (vo.py:126-139), with the fixed 19-word template as its fallback.
  Nothing compares it with the pin's signoff_expected, so this is not a refusal.

## 08:44 ET: the 08:40 package, sealed (attempt 0840)

Files: tests/package/proof/fresh_20261112_050611/given_v0700_0840.json / .log. Wall 113 s. Spend $0.53.

**The package** (rulings 08:18 / 08:29 / 08:40):
- **hook:** Saifedean Ammous, vgsSZ4mAHfQ 5144.99-5153.37.
- **VO 1:** "Bitcoin does not have any authority. That's not a flaw. That's the design."
- **clip_01:** What Bitcoin Did, c1JGheQBPH4 2403.23-2412.85.
- **VO 2:** "Next, from Natalie Brunell's show: what does a system with no one in charge have to get right?"
- **clip_02:** Natalie Brunell, wdk5JZ9hPzs 3218.14-3221.64: "Bitcoin imposes a global free market for the first time
  ever."
- **VO 3, the takeaway** (24 words): "No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most
  people still miss when they look at Bitcoin."
- **sign-off:** "Clips today from Saifedean Ammous, What Bitcoin Did, and Natalie Brunell. Go follow them for more. Links
  are below."
- **TITLE:** "No authority. That's the design."
- **CAPTION:** "no authority. that's the design. three clips, links below."
- **Runtime:** 60.80 s by the factory's arithmetic (the deployed rule_r4 on the pin gives 60.74 s); VO 41.1 % (cap
  45 %).

**Gates.** Every model verdict passed on its first run. The judges were xai:grok-4.20-0309-reasoning; the second
recogniser was elevenlabs scribe_v1. The writer is the orchestrator's text, so no judge shares its vendor.
- **VO fidelity:** deterministic PASS. Verdict PASS: VO 1 is a fact supported verbatim by the hook ("Bitcoin does not
  have any authority"); VO 2's first half and the caption's end are production, from the manifest; the rest is
  commentary.
- **Context A / B / C:** PASS on all three. clip_02: "the guest's own assertion", certain, entails, nothing dropped.
- **Coherence:** PASS, hook 5, clip_01 4, clip_02 5, VO point 4.
- **Exclusion:** keep x3.
- **Second pass:** PASS x3.
- **CUTTABLE:** PASS x3. clip_02 IN is "path." | [false start "Bit-"] "bitcoin" (ruling 8); OUT is "ever." | "Okay,".
- **Duplicate, price-now, runtime, R4:** PASS.
- **Majority:** none needed.

**For the integrator:**
- clip_02's pin range is the store's word span (3218.14-3221.64). The renderer's cut (14.38 s, after "path.") keeps
  the false start, as ruling 8 orders.
- G18 must tolerate exactly that one token; the integrator confirms this before rendering (ruling 8).
- The runtime margin over the hard 60 s is 0.80 s by the store spans; the factory recomputes it from its own decode
  (pinned.py:290).

**The code is committed with this pin.** It was audited in two cycles (docs/audits/parallel/pp-selectid_audit_0742:
C1_CONSENSUS.md, C2_DISPOSITIONS.md). The reviewers were grok-4.20, qwen3.8-27b and glm-5.3-flash. Cycle 2: all three
say SHIP "yes with conditions", and the conditions are met.
- package.runtime is the factory's own R4 estimate. Also: the R4 share is 45 % (ruling 9), the takeaway cap is 30
  (ruling 10), and once_then_majority implements 08:18 item 4.
- vo_fidelity.majority implements 07:42 item 3.
- transcript_truth.self_repair implements ruling 8.
- The driver gained flags, plus tests/package/pin_and_verify.py.
- Tests: 56 pass. regression_test.sh: 26 PASS / 0 FAIL / 5 WARN.

**Spend since 07:42:**
- Ledger $55.36 -> $57.63 = $2.27. That includes $0.30 for the voided router-based audit attempt.
- The two audit cycles by direct HTTP: $0.77, estimated at upper-bound prices.
- Total about $3.04 of the $6.00.

## ORCHESTRATOR RULING 10, 08:40 ET: recorded in substance (builder + integrator)

- The VO line after the LAST clip is the TAKEAWAY. It is a new slot that did not exist when BRIDGE_WORD_CAP = 20 was
  set for lines between clips.
- For moments pins the takeaway's word cap is 30, the same as the intro cap. Bridges BETWEEN clips stay at 20.
- INTEGRATOR: add the constant (e.g. MOMENTS_TAKEAWAY_WORD_CAP = 30), apply it only to after_clip == last in the
  moments R4, add the must-fail tests (31 words rejected; a 21-word bridge between clips still rejected), smallest
  audit, commit.
- BUILDER: the same constant in my R4.
- VO 3 stays as ruled at 08:29 (24 words). No other text changes.
- Then:
  - the builder runs the full gate set once, seals, puts READY on line 1, commits and pushes;
  - the integrator renders the moment it lands and delivers to Telegram REVIEW ONLY.
- Before either of us stops for another cap or constant: check NOW, both of us, whether any OTHER limit in the
  deployed render path would refuse this exact package, and report them all in ONE list, not one per round. The ruling
  names: intro cap, total VO words, clip count, min clip seconds, per-channel floor, shout-out timing, the credits card
  with 3 channels, and vertical layout approval for all three channels.

## 08:32 ET: rulings 8 / 9 encoded; a word-cap blocker in the VO (five lines)

1. **Ruling 8 encoded** (transcript_truth.self_repair, used by CUTTABLE's IN and by the L-v 2 comparison).
   - On the recorded pass (cached, $0), clip_02 CUTTABLE PASS: IN "path." | [false start "Bit-"] "bitcoin"; OUT
     "ever." | "Okay,".
   - Second pass PASS. Step A PASS.
   - 52 tests pass. Must-fail cases: another speaker, a non-prefix fragment, no dash, two fragments, no sentence end
     before it. A full repetition stays a disagreement.
2. **Ruling 9 encoded**: package.R4_MOMENTS_SHARE = 0.45; a test refuses 45.1 %.
   - The main tree's edl_rules.py already reads 0.45 in its working copy (MOMENTS_VO_SHARE).
3. **BLOCKER: VO 3 is over the bridge cap.**
   - VO 3 as ruled at 08:29 has 24 words. Bridges are capped at 20 words: config.py BRIDGE_WORD_CAP = 20 in the main
     tree and here.
   - The deployed moments R4 checks it (edl_rules.py:203-204): "bridge 2 24 words (max 20)". My R4 refuses it the same
     way.
   - With VO 1 and VO 2 as ruled, VO 3 at its 20-word maximum lands 59.2 s, under the hard 60.
4. **The arithmetic:** 60.5-62.5 s needs 55-60 VO words in total. With VO 2 at 18 and VO 3 at most 20, VO 1 needs at
   least 17 words (the intro cap is 30). Ways to get there:
   - VO 1 + a clause of 4 or more words, with VO 3 at 20 words: 60.8 s at 41.1 %;
   - VO 2 at 20 words and VO 1 at 15;
   - or a moments bridge cap of at least 24 (the integrator's constant).
5. **Your text or your cap.** Nothing has run beyond the cached pre-checks: $0 since 08:20 (ledger $57.11).
   - The code audit is being re-run: the Heimdall cycle-1 replies came back empty (reasoning effort not passed).
   - Evidence: tests/package/proof/fresh_20261112_050611/precheck_v0700_0829.json / .log.

## ORCHESTRATOR RULINGS 08:29 ET: recorded in substance (builder + integrator)

The builder and the integrator measured the same edge and disagree. The integrator's measurement on the renderer's own
window decides: **f216541b STAYS.**

**RULING 8: the IN of f216541b.**
- The facts, from both measurements:
  - the previous sentence ends "path.";
  - a pause (260 ms on the renderer's window);
  - the guest's faint false start ("Bit-" / "It w-", 15-20 dB below speech);
  - then "Bitcoin imposes a global free market for the first time ever.";
  - then a 520 ms pause and the host.
- The sentence boundary is AFTER "path.": that is where this sentence begins, false start included.
- A same-speaker self-repair at the START of a sentence is part of that sentence:
  - the clip begins at the integrator's cut (14.38 s, after "path.");
  - the false start stays in the clip exactly as spoken (nothing inside a clip is edited);
  - CUTTABLE's IN evidence is "path." | [false start] "Bitcoin".
- The integrator's simulated prepare edge-word check already passes ("bitcoin" / "ever").
- **Builder: encode it.** A token that the second recogniser hears and the primary does not, which is a truncated
  repetition of the clip's first word by the same speaker, is a self-repair. It is not a missing sentence start, and
  not an L-v 2 disagreement (L-v 2 is about numbers, names and negations; "Bit-" is none).
- The locked-text / word-for-word check (G18) must tolerate exactly that token and nothing else.
  - INTEGRATOR: confirm that G18 and the sentence lock handle it on the real render.
  - If G18 would fail on it, say so BEFORE rendering, and the orchestrator rules.

**RULING 9: R4 for moments.**
- The VO share cap is 45 % of the total runtime (it was 40 %, the orchestrator's number from two hours earlier).
- The auditors asked for 30-45 % commentary, and a 3.5 s punchline clip cannot reach PBX's hard 60 s under 40 %.
- 60-70 s stays hard.
- INTEGRATOR: change the constant and its must-fail test (45.1 % rejected), smallest possible audit, commit.

**Lines:**
- VO 3 (24 words): "No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still miss when they
  look at Bitcoin."
- The code's arithmetic may trim or add ONE clause of host commentary to land 60.5-62.5 s.
- VO 1, TITLE, CAPTION and VO 2 as ruled at 08:18.

**THEN:**
- The builder runs the full gate set ONCE (the three-run majority only for a model verdict that is not PASS on its
  first run), seals, puts READY on line 1, commits and pushes.
- The integrator renders the moment it lands and delivers to Telegram REVIEW ONLY.
- If the package fails only on split model votes, with every deterministic gate passing: the vote table goes to the top
  of STATE, and no loop.

## 08:20 ET: the 08:18 pre-checks on f216541b (item 3, five lines)

1. **Step A (grok-4.20, 34 s): PASS.** The guest's own assertion; nothing conditional dropped. The speaker is "guest",
   not verified inside the selection, so VO 2 credits the show only.
2. **CUTTABLE (scribe_v1 on wdk5JZ9hPzs 3216.64-3223.14): FAIL at the IN.**
   - The guest begins with a false start: "path." 3217.10-3217.44 | "Bit-" 3217.94-3218.06 | "bitcoin"
     3218.36-3218.70.
   - The word before the clip is "Bit-", not a sentence end.
   - The L-v 2 second pass fails on the same token (disagree names ["Bit-"]).
   - The OUT is clean: "ever." 3221.46-3221.64 | the host's "Okay," 3222.32 (a 0.68 s pause).
   - Stopped here (item 3). The integrator's geometry pre-check was NOT started.
3. **The only clean IN is after the false start**, in the 0.30 s gap 3218.06-3218.36. That is not a sentence start
   under ruling 7 / the sentence law. Whether a false start counts is yours to rule, not mine.
4. **Item 2 cannot land in any case.**
   - Content is 21.50 s. The most within R4's 40 % is 59.67 s: VO 3 at 21 words gives 59.60 s (39.9 %); 22 words give
     60.00 s at 40.3 %.
   - 60.5-63 s needs a 41.1-43.0 % share (VO 3 of 24-29 words).
   - The factory computes the same: pinned.py:290 takes the word span, then edl_rules._r4_moments.
   - Any clip_02 lands 60.5-63 s at 40 % if it is 5.2-7.7 s with the VO as written (VO 3 19 words), or 4.0-12.1 s with
     VO 3 trimmed or grown.
5. **Item 5: your pick from other channels, with a new VO 2.**
   - Spend $0.11 (step A; Scribe $0.003). Ledger $57.11.
   - The 07:42 / 08:18 budget has $4.54 left, before the Heimdall audit cycle now running.
   - Evidence: tests/package/proof/fresh_20261112_050611/precheck_v0700_0818.json / .log.

## ORCHESTRATOR DECISION 08:18 ET: recorded in substance (builder + integrator)

The analysis of "existed." is accepted: it drops the guest's own condition. Option (A) is chosen. Budget +$4.

1. **clip_02** = Natalie Brunell's channel, moment f216541b: "Bitcoin imposes a global free market for the first time
   ever." (YouTube wdk5JZ9hPzs 3218.14-3221.64, 3.50 s).
   - It ends the guest's answer; the host's "Okay, so let's wrap this up" follows.
   - It is the PUNCHLINE of the angle, so the short-clip penalty does not apply (L-o: a deviation to record, never a
     rejection).
   - Order unchanged: hook (Ammous) -> VO 1 -> What Bitcoin Did (the White House / Senate clip) -> VO 2 -> this clip
     -> VO 3 -> sign-off.
2. **Lines:**
   - VO 1 = the fallback "Bitcoin does not have any authority. That's not a flaw. That's the design."
   - TITLE = "No authority. That's the design."
   - CAPTION = fix 2, "no authority. that's the design. three clips, links below."
   - VO 2 unchanged: "Next, from Natalie Brunell's show: what does a system with no one in charge have to get right?"
     The new clip answers that question directly.
   - VO 3 starts from "No ruler. Just rules nobody gets to bend. That's the idea, and it's the part most people still
     miss." The code's arithmetic adds or trims host commentary in VO 3 ONLY, to land 60.5-63 s within R4's 40 %.
3. **Pre-check in this order**, stopping at the first failure and reporting it in five lines:
   - step A context on f216541b (the guest's own sincere assertion; nothing conditional dropped);
   - CUTTABLE on the second recogniser;
   - the INTEGRATOR's cut-geometry pre-check on the acquired or a newly acquired window, done the moment the builder
     names the window: the pause after "ever.", neighbour-clear, no backchannel in the tail, and the IN;
   - the full gate run -> seal -> READY on line 1 -> the integrator renders and delivers REVIEW ONLY.
4. **The judge is noisy tonight** (one vendor; verdicts flip across seeds).
   - A model-judged verdict that is not PASS on its first run gets the three-run majority (07:42 item 3) ONCE.
   - Whole gate sets are not rerun.
   - If the package then fails ONLY on split model verdicts while every deterministic gate passes (verbatim, cuttable,
     runtime, R4, exclusions, duplicates, price-now, second recogniser), do not loop: put the package and the vote
     table at the top of STATE, and the orchestrator decides within minutes.
5. If f216541b fails step A or the geometry, the second candidate is NOT 9d3621a7 (its next sentence continues it).
   Report it, and the orchestrator picks from other channels with a new VO 2.

## 07:58 ET: the 07:42 package, measured (attempt 0742)

Files: tests/package/proof/fresh_20261112_050611/given_v0700_0742.json / .log. Wall 168 s. Spend $1.35 by the ledger
(all xai:grok-4.20-0309-reasoning at its configured price; the second pass was served from tonight's recordings, $0).
Ledger $56.70 of $64.28; the 07:42 budget of $2 has $0.65 left. (The line above this section said "07:45 ET"; it was
written at 07:40, commit 9daa914d.)

**Applied as ruled:**
- clip_02 = store words 1417-1432, YouTube 529.05-535.78 (6.73 s word span). The renderer cuts 15.02-22.04 s file time
  (7.02 s). The integrator's geometry is recorded as CUTTABLE evidence in the package's cut_evidence. So is the
  recogniser disagreement at "existed": the integrator's pass heard a comma, my three passes heard a full stop.
- VO 3 = "No ruler. Just rules nobody gets to bend. That's the idea, and it's the part people miss."
- Runtime 61.23 s by the code's arithmetic, so VO 2 is unchanged:
  - content 24.73 + VO 48 words / 2.5 + 3 x 1 s pre-roll + 14.30 tail;
  - that arithmetic is now the factory's own R4 estimate (edl_rules._r4_moments, main a5ec0f17);
  - the builder's earlier estimate (2.6 w/s, no pre-roll) gives 57.88 s for the same package;
  - neither is a measurement; the render measures the final.
- Judges: grok-4.20-reasoning (Heimdall deepseek as fallback). Transcription: scribe_v1. No OpenAI or Anthropic call.

**FAIL 1: the thesis line, three runs (07:42 item 3).**
- seed 7: UNCERTAIN; seed 8: NO; seed 9: PASS. The majority is NOT supported (1-2).
- So, per the ruling, the fallback applies:
  - VO 1: "Bitcoin does not have any authority. That's not a flaw. That's the design."
  - TITLE: "No authority. That's the design."
  - Not yet gated: it is gated with the next clip_02 decision, because the verdict reads the clips.
- The CAPTION "no authority. no ruler. three clips, links below." (my fix 1 of 2, 07:25) also failed 2 of 3 runs: the
  judge read "no ruler." as a fact, and no clip says it.
- Proposed fix 2 of 2: "no authority. that's the design. three clips, links below." Each part passed tonight as fact,
  commentary and production.

**FAIL 2: context integrity, step A on clip_02 (law L-s).**
- CONDITION_OUTSIDE: the words right after the cut are, verbatim in the transcript, "And all it has to do, is stay
  decentralized and secure. And that's what emerges." The first sentence alone states as unconditional what the
  speaker conditions.
- RETRACTION (a material limit, ruling 6): later in the window the speaker says that, measured through the existing
  system, "it could bend light, bend Bitcoin, into the black hole that is the existing system ... it would be
  centraliz[ed] ... So it wouldn't free people". The judge's own quote paraphrases this; the transcript words are as
  quoted here.
- The same moment through "does." passed step A at 07:25, with the condition inside the clip.

**FAIL 3: coherence.** clip_02 scores 3 (needs >= 4). The hook scores 5, clip_01 4, the VO point 4.

**PASS:** deterministic fidelity, duplicate, price-now, runtime, R4 (36.3 %), exclusion x3, second pass x3, CUTTABLE x3
(clip_02: "now. | Bitcoin", "existed. | And").

**What this means.** No end of this moment is both cleanly cuttable by the renderer's geometry and complete in
context (L-s):
- "existed.": clean, but drops the condition;
- "emerges.": no pause;
- "does.": the host's "Mm" sits in the tail;
- "mass.": 22.45 s, over the 20 s limit (L-u).

No line change can pass this clip: the failure is in the clip. 07:42 allows no more attempts on its ends, and I do not
swap a clip without your word (05:35). Dropping clip_02 is not possible either: a hook plus one clip (18.0 s of content)
needs at least 65 VO words to reach 60 s, and R4 allows at most 48.

**DECISION NEEDED (orchestrator):**
- **(A) RECOMMENDED: replace clip_02 with another moment.**
  - I pre-check candidates first: store facts, the cheap gates, step A context, CUTTABLE on the second recogniser,
    coherence fit. Then the integrator runs its cut-geometry pre-check. Then I gate the package with the fallback
    thesis lines and the caption fix 2.
  - Spend: about $1.50 beyond the $0.65 left.
  - The zero-cost part of the pre-check starts now and appears below when done.
- (B) Rule that the speaker's condition is not material (law L-s is yours to interpret, as rulings 3 / 5 / 6 did).
  Not recommended: coherence 3 still fails, and the condition is verbatim right after the cut.

**08:00 ET: the zero-cost candidate pre-check for clip_02 (store facts only; no model call; no swap).**

Tonight's store has 62 moments. The current VO puts clip_02 between 5.5 s and 15.5 s: 60-70 s with the ruled VO.

Natalie Brunell, same episode (VO 2 and the sign-off stay valid):
- **f216541b**, 3.50 s, "Bitcoin imposes a global free market for the first time ever." (YouTube 3218.14-3221.64)
  - The sentence ends the guest's answer; the host's "Okay, so let's wrap this up ..." follows.
  - On the angle, but short: runtime 58.0 s, so the VO needs about +2 s (5 words) to reach 60.
- **9d3621a7**, first sentence only, 2.96 s, "We either live in a free market, or we live in a control system." (173.99-176.95)
  - The next sentence continues it ("And Bitcoin gives us a chance to escape that control system ..."), so the
    context may fail like 'existed.'.
  - Runtime 57.5 s.
  - With that next sentence the clip is 20.64 s, over the 20 s limit (L-u). The next sentence alone is 16.02 s and
    starts on a referent outside it.
- Longer moments in this episode are off the angle or over 20 s:
  - a new internet "bound by Bitcoin" (predictions, 8.6 s);
  - Main Street adoption (12.9 s);
  - self-custody fears (12.0 s);
  - "outside of the bubble" (9.7 s, referent outside);
  - privacy (17.5 s);
  - the constitution (15.6 s; runtime 70.1).

Other channels: VO 2 names Natalie Brunell, so it would need your new text.
- Saifedean Ammous and What Bitcoin Did are already the hook and clip_01.
- Coin Bureau, Simply Bitcoin and Yahoo Finance are price or flow items (time-sensitive).
- The Livera moment was dropped at 06:00.

Every candidate still needs the measured gates (step A, CUTTABLE on the second recogniser) and the integrator's cut
geometry.

**Code (uncommitted until its audit, AUDIT-FIRST):**
- package.runtime = the factory's own R4 estimate;
- vo_fidelity.majority (ruling 07:42 item 3), with its votes sealed in the inventory row;
- driver flags --to-existed, --verdict-runs, --title-text;
- tests/package/pin_and_verify.py (seals a pin and checks it against the deployed pinned.py / edl_rules.py).

Tests: 50 pass across test_angles, test_gates, test_moments and test_providers (the new majority test included). regression_test.sh: 26 PASS / 0 FAIL / 5 WARN. The two-cycle audit runs
next, on xAI and Heimdall reviewers.

## ORCHESTRATOR RULING 07:42 ET: recorded verbatim in substance (builder + integrator)

1. **clip_02 = the FIRST SENTENCE ONLY, ending "existed."** (YouTube wdk5JZ9hPzs from 529.05 to the integrator's
   measured cut, about 7.0 s): "Bitcoin is a new system of measure that's measuring the first free market that's ever
   existed."
   - The integrator's pre-check found "does." NOT clean (the host's "Mm" sits in the tail). The ONLY clean end in this
     moment is "existed.".
   - The CUTTABLE evidence = the integrator's cut geometry in docs/audits/parallel/integrator_RULING7_FACTS.md (main
     tree).
   - No more attempts on later ends of this moment.
2. **VO 3 grows** to "No ruler. Just rules nobody gets to bend. That's the idea, and it's the part people miss."
   - If the runtime is still under 60 s by the code's arithmetic, VO 2 becomes "Next, from Natalie Brunell's show: what
     does a system with no one in charge actually have to get right?".
   - Target 60.5-63 s.
3. **The thesis line "Nobody is in charge of Bitcoin."** (VO 1 + title) passed the same judge three times on unchanged
   text and came back UNCERTAIN once after an unrelated clip changed.
   - RULE for a verdict that flips on unchanged text: run that one verdict THREE times; the majority decides.
   - A 2-1 split is recorded in the package and NAMED IN THE CAPTION.
   - If the majority is UNCERTAIN / NO, do not argue: use the verbatim-anchored fallback, VO 1 "Bitcoin does not have
     any authority. That's not a flaw. That's the design." and TITLE "No authority. That's the design."
4. **Vendors:** xAI / Heimdall / local only (Anthropic and OpenAI are out of credit). Budget $2.
5. **Re-seal, READY TO RENDER on line 1, commit + push.**
   - INTEGRATOR: render the re-sealed pin the moment it lands, every gate live, Telegram REVIEW ONLY.
   - "This is the last clip decision I expect to make tonight"; if prepare fails again on any edge, swap nothing and
     report the measured cause at the top of the DoD.

## 07:26 ET (header corrected 07:58 from '07:58', a wrong time; the commit fe0ca679 is 07:26:41): the 07:25 re-gate (attempt 0725: tests/package/proof/fresh_20261112_050611/given_v0700_0725.json / .log; 189 s, $0.89)

**What changed.** clip_02 now runs through "does." (store words 1417-1456, wdk5JZ9hPzs 529.05-543.54, 14.49 s): "Bitcoin
is a new system of measure that's measuring the first free market that's ever existed. And all it has to do, is stay
decentralized and secure. And that's what emerges. And it doesn't matter what the other system does."

**Judges** (07:25 item 3: Anthropic and OpenAI are out of credit): every verdict ran on xai:grok-4.20-0309-reasoning
(heimdall deepseek as fallback); transcription on elevenlabs scribe_v1. The writer is the orchestrator's text, so no
judge shares its vendor.

**PASS:**
- context integrity A / B / C on all three clips. The added sentence changes neither the guest's assertion nor adds an
  outside referent: C entails yes, nothing dropped, nothing added.
- CUTTABLE 6/6. clip_02's OUT is "does." on the independent recogniser.
- **The cutter's own geometry at "does."** (07:25 item 2): cut_accept.check_cut_out (M19) from a read-only copy, on the
  integrator's ACQUIRED audio and decode (runs/pinned_20261112_120225).
  - "does." 28.88-29.30, the next word "But" at 30.38.
  - Quiet runs >= 80 ms after it: 29.13-29.23 and 29.64-29.89. M19 accepts 22 cut_out points, 29.62-29.83, inside the
    pause 29.64-29.89 with >= 60 ms ahead.
  - The next sound rises only at about 29.89, so a cut there keeps nothing of the neighbour.
  - The prepared clip's edge-word check (Whisper on the GPU) is the integrator's pre-render check (REQUESTS R11).
- L-v 2 x3, exclusion x3, DUPLICATE.
- Runtime 63.33 s (by the integrator's R4 formula about 66.6 s): <= 70, so VO 2 is NOT shortened.
- R4 (VO 31.3 % of the runtime).
- Coherence 5 / 4 / 5, VO point 5: "Nobody is in charge of Bitcoin and that is by design rather than a flaw."

**FAIL, verbatim:**
- `intro: VERDICT_UNCERTAIN: Nobody is in charge of Bitcoin.`
- `title: VERDICT_UNCERTAIN: Nobody is in charge of Bitcoin.`
- The SAME line passed at 07:30 (attempt 0700c), supported by the hook's "Bitcoin does not have any authority" and
  clip_01's "its success is not dependent upon who's in the White House ...".
- The judge reads it as a FACT drawn from the two clips, and it is unstable on that inference.
- I have not re-asked (no verdict shopping).

**Your options:**
- (1) **Rule the thesis line host commentary (class D):** the host's own takeaway, attributed to nobody. Then its five
  tests decide, not clip support. This is the 05:25 doctrine's call to make, not mine.
- (2) **Reword VO 1 and the title to what the clips state verbatim.** For example VO 1: "No one has the authority to
  take your Bitcoin. That's not a flaw. That's the design." and TITLE: "No one has the authority over your Bitcoin."
  (the hook: "Bitcoin does not have any authority that allows people to take the wealth of others"). VO 1 has 1 of its
  2 fixes left; the title has 2.
- Either costs one more gate run, about $0.40. $1.11 of the $2 is left.
- The renderer's geometry at "does." already holds, so after this line the pin can be sealed at once.

## 07:31 ET: the 06:45 package, re-sealed. Every one of 13 gates exactly PASS (attempt 0700c: 140 s, $0.56)

Record: tests/package/proof/fresh_20261112_050611/given_v0700_0700c.json and .log. This supersedes the 06:28 pin
add8c732 (the integrator's cut HOLD was right on both clips). The renderer's order:

1. HOOK, Saifedean Ammous, vgsSZ4mAHfQ 5144.99-5153.37: "Bitcoin does not have any authority that allows people to
   take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that."
2. VO 1: "Nobody is in charge of Bitcoin. That's not a flaw. That's the design." (a fact supported by the hook and
   clip_01, plus commentary)
3. CLIP 1, What Bitcoin Did, c1JGheQBPH4 2403.23-2412.85 (a guest; NEW, ruling 7 B): "I mean, the good news about
   Bitcoin is it's not, you know, its success is not dependent upon who's in the White House or who's controlling the
   Senate or the House of Representatives in the U.S."
4. VO 2: "Next, from Natalie Brunell's show: what does a system with no one in charge have to get right?" (production
   + commentary; see the VARIANCE FLAG)
5. CLIP 2, Natalie Brunell's channel, wdk5JZ9hPzs 529.05-541.00 (a guest; EXTENDED to "emerges.", 06:45 A): "Bitcoin
   is a new system of measure that's measuring the first free market that's ever existed. And all it has to do, is
   stay decentralized and secure. And that's what emerges."
6. VO 3 (after the last clip): "No ruler. Just rules nobody gets to bend. That's the idea." (commentary)
7. SIGN-OFF (code, L-a): "Clips today from Saifedean Ammous, What Bitcoin Did, and Natalie Brunell. Go follow them for
   more. Links are below."

- TITLE "Nobody is in charge of Bitcoin." (a fact, supported).
- CAPTION (fix 1) "no authority. no ruler. three clips, links below." (fact + commentary + production).

**Gates, all exactly PASS:**
- VO fidelity: deterministic, and the classifying verdict under the cycle-2 rules (full word coverage; production
  bound to the manifest).
- DUPLICATE; PRICE_NOW; runtime 60.79 s; R4 (moments).
- Context A / B / C on every segment (grok-4.20).
- Exclusion x3.
- L-v 2 x3 (scribe_v1).
- **CUTTABLE x3, 6 edges** (06:45 C):
  - hook: "fundamental. | Bitcoin", "that. | Your";
  - clip_01: "Mm-hmm. | I", "US. | Um,";
  - clip_02: "now. | Bitcoin", "emerges. | And".
- Coherence 5 / 4 / 5, VO point 4.

**Against the factory as deployed** (read-only copies):
- pinned.validate_schema OK;
- moments_vo accepts the VO, including VO 3 after the last clip;
- edl_rules R4 (moments): "VO 19.80 s = 30.91% of total runtime <= 40%, estimated runtime 64.05 s, every VO line in a
  slot".

**Ruling 7 for the integrator's caption** (condition 5): no edge needs it. Every IN and OUT has the independent
recogniser's terminal punctuation, and the pin carries the words as `moments_package.cut_evidence`. If the acquired
primary decode is unpunctuated at an edge, ruling 7 condition (1) reads that evidence: REQUESTS R10.

## (superseded 07:31) 07:16 ET: the 06:45 re-cut (attempt 0700b, tests/package/proof/fresh_20261112_050611/given_v0700_0700b.json / .log)

- **A. clip_02 is extended to "emerges."** (words 1417-1447, 529.05-541.00, 11.95 s): "Bitcoin is a new system of
  measure that's measuring the first free market that's ever existed. And all it has to do, is stay decentralized and
  secure. And that's what emerges."
  - The independent recogniser (ElevenLabs scribe_v1, source audio) reads: "...decentralized and secure, and that's
    what emerges.[540.53] And it doesn't matter...".
  - **Must-fail confirmed:** the ORIGINAL OUT is rejected under ruling 7. On the original window, scribe shows the
    sentence continuing: "secure, and that's what emer-".
- **B. clip_01 (c1JGheQBPH4 2480.28) FAILS ruling 7 (1) on the facts at its IN.** Scribe reads "It's, it's not, it's
  not Bitcoin that's getting hacked." as ONE sentence. Before the clip's first word there is a comma ("not,"), and
  "it's" is not capitalised. Its OUT would pass ("...unique nature of Bitcoin. Um, so").
  - Not bent. **Replaced** by the next-best moment for the angle: What Bitcoin Did 4f9d38e1d86556b36d9c, re-cut to its
    first sentence (words 7325-7361, 2403.23-2412.97, 9.74 s; the WBD channel is allowed, the excluded two being
    Saifedean Ammous and Natalie Brunell): "I mean, the good news about Bitcoin is it's not, you know, its success is not
    dependent upon who's in the White House or who's controlling the Senate or the House of Representatives in the U.S."
  - Scribe: "Mm-hmm.[2401.83] I mean, ... in the US.[2412.53] Um, you know, price-wise...". A boundary before the IN
    and at the OUT; the next word is a filler (ruling 7 (4)).
- **C. CUTTABLE is a package gate now** (transcript_truth.edges + the inventory row "cuttable", required by package_pin).
  Every IN and OUT needs the independent recogniser's sentence boundary on the source audio; store / caption
  punctuation is never evidence. **All 6 edges PASS:**
  - hook: "fundamental. | Bitcoin" / "that. | Your";
  - clip_01: "Mm-hmm. | I" / "US. | Um,";
  - clip_02: "now. | Bitcoin" / "emerges. | And".

**The verdicts** (attempt 0700b: 78 s, $0.26; with 0700: 177 s, $0.84):
- PASS:
  - context integrity A / B / C on all three clips (grok-4.20);
  - CUTTABLE 6/6;
  - L-v 2 x3 (scribe_v1: one speaker each, no disagreement);
  - exclusion keep x3;
  - DUPLICATE;
  - runtime 60.79 s (the integrator's own estimate about 64.0 s);
  - R4: VO 32.6 % of runtime, 39.8 % of clips + VO;
  - coherence hook 5, clip_01 4, clip_02 5, VO point 5: "Nobody is in charge of Bitcoin; that's by design rather
    than a flaw, enabling a decentralized free market with immutable rules.";
  - step A now verifies Saifedean Ammous as the hook's own host.
- **VO 1** "Nobody is in charge of Bitcoin. That's not a flaw. That's the design.": PASS. An attribution supported by
  the hook's "Bitcoin does not have any authority..." and clip_01's "its success is not dependent upon who's in the
  White House...", plus commentary.
- **VO 2** "Next, from Natalie Brunell's show: what does a system with no one in charge have to get right?": **FAIL**:
  `host commentary 'what does a system with no one in charge have to get right?' fails speaker_view`. It passed in
  attempts 4-9 with the old clip_01. Its two fixes are used (your fallback "Here's Natalie Brunell on what that takes."
  names the guest's host as the speaker: L-v 1). **Yours to decide.** The length rule: VO 1 + VO 2 + VO 3 need >= 42
  words for 60 s (VO 1 13, VO 3 11, so VO 2 >= 18; the bridge cap is 20).
- **CAPTION** "no authority. three voices on why that is the point.": **FAIL** `fails speaker_view`. Fix 1, "no
  authority. no ruler. three clips, links below.", is ready but was NOT yet gated (a driver bug of mine, fixed).
- VO 3, the TITLE: PASS.


# pp-selectid — STATE (session pipeline_pp_selectid, branch pp-selectid, worktree ~/worktrees/pp-selectid)

## 06:28 ET: tonight's package (fresh_20261112_050611) passes EVERY gate. The pin is written and sealed. REVIEW ONLY (law L-q)

This is the orchestrator's 06:00 package with the line fixes of attempt 4, approved for render at 06:22. Gated as
attempt 9: tests/package/proof/fresh_20261112_050611/given_v0600_attempt9.json and .log. Pin: MOMENTS_PIN.json,
story moments-fresh_20261112_050611-add8c732, `machine_cuts`, approved_by "machine ... REVIEW ONLY".

**The video, in the renderer's order** (render16.py:306-334 / render_vertical.py:853-880):

| # | segment / VO line | class (blind verdict) |
|---|---|---|
| 1 | HOOK, Saifedean Ammous, vgsSZ4mAHfQ 5144.99-5153.37: "Bitcoin does not have any authority that allows people to take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that." | - |
| 2 | VO 1 (after the hook): "Nobody is in charge of Bitcoin. That's not a flaw. That's the design." | commentary (D) |
| 3 | CLIP 1, What Bitcoin Did, c1JGheQBPH4 2480.28-2491.52: "It's not Bitcoin that's getting hacked. It's other intermediaries. So in some ways, it kind of shines a light on the secure nature and the unique nature of Bitcoin." | - |
| 4 | VO 2 (after clip 1): "Next, from Natalie Brunell's show: what does a system with no one in charge have to get right?" | production (C) + commentary (D) |
| 5 | CLIP 2, Natalie Brunell's channel (a guest speaks; the VO credits the show only), wdk5JZ9hPzs 529.05-539.34: "Bitcoin is a new system of measure that's measuring the first free market that's ever existed. And all it has to do, is stay decentralized and secure." | - |
| 6 | VO 3 (after clip 2, the takeaway): "No ruler. Just rules nobody gets to bend. That's the idea." | commentary (D) |
| 7 | SIGN-OFF (code, L-a): "Clips today from Saifedean Ammous, What Bitcoin Did, and Natalie Brunell. Go follow them for more. Links are below." | - |

- TITLE "Nobody is in charge of Bitcoin." (commentary).
- CAPTION "no authority. three voices on why that is the point." (a fact supported by "Bitcoin does not have any
  authority", plus production).
- **Runtime:** my estimate 60.75 s. The integrator's moments R4 estimate is 64.01 s. Both are inside 60-70 s.

**The sealed gate inventory: every row exactly PASS, measured live (not replayed):**

| gate | status | by |
|---|---|---|
| vo_fidelity_deterministic | PASS | code |
| vo_fidelity_verdict (classifying A/B/C/D) | PASS | xai:grok-4.20-0309-reasoning |
| duplicate | PASS | code |
| price_now | PASS | code |
| runtime | PASS | code |
| r4 (moments, 06:00) | PASS | code. The main tree's own edl_rules R4 for moments (a5ec0f17) on this pin's EDL: "VO 19.80 s = 30.93% of total runtime <= 40%, estimated runtime 64.01 s, every VO line in a slot" |
| context_a (x3) | PASS | anthropic:claude-opus-5-5 |
| context_b | PASS | xai:grok-4.20-0309-reasoning |
| context_c | PASS | xai:grok-4.20-0309-reasoning |
| exclusion (x3) | PASS | anthropic:claude-opus-5-5 (never the miner's model) |
| second_pass, L-v 2 (x3) | PASS | elevenlabs_stt:scribe_v1: one speaker each, no number / negation / name disagreement in either direction |
| coherence | PASS | xai:grok-4.20-0309-reasoning: hook 5, clip_01 4, clip_02 5, VO point 4. Through-line "Nobody is in charge of Bitcoin and that is by design, enabling a decentralized, secure free market with immutable rules and no authority to seize wealth." |

**Notes recorded by the gate.** These are not failures, under rulings 3 and 5:
- clip_01 and clip_02: step C reads the viewer as firmer than the context, but cites no words of the video that raise
  it.
- clip_02: step C's "entails: no" names no limit in the context's own words. It named "for that to emerge", which is
  step A's paraphrase and not in the transcript.

**The attribution check (06:22).**
- Step A rates the HOOK's speaker "uncertain": no evidence of anyone but Saifedean Ammous. No VO, title or caption
  line names or implies him.
- CLIP 1 is a guest on a brand channel that no VO line names.
- CLIP 2 is a guest: VO 2 credits "Natalie Brunell's show" and nothing implies Natalie Brunell says it.
- The sign-off credits CHANNELS (L-a).

**Checked against the factory as deployed** (read-only copies of the main tree in the scratchpad):
- pinned.validate_schema: OK.
- pinned.moments_vo (380a06f3 + later) accepts the VO, including VO 3 after the last clip.
- edl_rules R4 for moments (a5ec0f17): PASS.

**The rulings, encoded** (pipeline/context_integrity.py):
- Ruling 3: STRONGER fails only on cited VO / title / caption words, and not when the clip alone already sounds
  certain.
- Ruling 5: entailment is judged against the clip's own words; a scope failure needs a limit in the context's OWN
  words, outside the clip; the package's attributions are checked separately through cited words that name the
  speaker's show.
- Ruling 6: RETRACTION means a withdrawal, reversal, correction or material limit, not an elaboration consistent with
  a condition stated in the clip.
- REFERENT_OUTSIDE needs "changes_assertion" not "no".

**The must-fail re-check after every ruling:** the exam's context-integrity MUST-FAIL cases, 41 of 41 rejected, 0
missed, 0 errors (tests/package/exam/ci_mustfail_*.json; claude-opus-5-5, grok fallback, about $0.01 a call).
- An intermediate encoding missed 2 title_adds_thesis cases. Both were closed before the pin: STRONGER was matched to
  the ruling's exact words, and step B was made to count what a title attributes.
- The corpus holds 41 must-fail cases now, not 43.

**Measured cost and time** (05:25 item 5):
- Tonight's package: 9 gate attempts, **$3.46**: $0.59, $0.44, $0.57, $0.58, $0.26, $0.32, $0.45, $0.25, and $0.00
  (attempt 9 re-decided attempt 8's recorded replies under the corrected rule). Each full gate run: 76-144 s wall and
  $0.25-0.59, so every attempt was inside the 05:25 budgets ($1.50, 6 minutes).
- The 7 must-fail checks: **$5.78** ($1.35 of it wasted on the step-B label bug, now fixed).

## SPEND SO FAR (phase-2 ledger tests/moments/proof/SPEND.json, upper-bound prices; updated after every attempt)

- 06:30 ET, the package PASSES: **$52.79 of $64.28**. By vendor: openai $20.21, xai $23.42, anthropic $7.43, heimdall $1.72, elevenlabs $0.02. **$11.49 left.**

- 06:12 ET, after attempt 4: **$45.75 of $64.28** (attempts 1-4: $0.59, $0.44, $0.57, $0.58). **$18.53 left.**

- 05:49 ET, after attempt 2: **$44.60 of $64.28** (attempt 1 $0.59, attempt 2 $0.44). By vendor: openai $20.21, xai $21.13, heimdall $1.72, anthropic $1.52, elevenlabs $0.02. **$19.68 left.**
- 05:44 ET, after attempt 1: $44.16 of $64.28 (attempt 1: $0.59).

- 05:36 ET: **$43.58 of the $64.28 guard** ($39.28 + the 05:30 amendment's $25). By vendor:
  - openai $20.21
  - xai $20.21
  - heimdall $1.72
  - anthropic $1.44
  - elevenlabs $0.002
- Measured per call: claude-opus-5-5 $0.0105, claude-fable-5-2 $0.034, grok-4.20 $0.106, heimdall qwen $0.19,
  gpt-6.1-sol $0.29.
- Of the $25: **$4.30 went on the BEFORE exam** (05:28-05:33, 107 frontier calls, mostly grok). It was started under
  05:25 item 4 and stopped at once on the 05:30 amendment. Its 103 recorded replies are kept (scratchpad
  before_exam/replies). It counts against the exam's $5 frontier allowance, so $0.70 of that allowance is left.
- **Left for tonight's package: $20.70.**

## BUILD LOG (orchestrator 05:25: one line at least every 10 minutes while building)

- 07:45 ET:
  - The phase-2 code is COMMITTED and pushed (aef73873). Audited in 2 cycles: C1_CONSENSUS implemented; cycle 2 (opus /
    sonnet / grok, 3 chunks), C2_DISPOSITIONS K1-K11 implemented.
  - 105/105 tests; SMOKE R7 PASS against the deployed factory; must-fail 41/41; regression 0 FAIL.
  - **For the integrator (REQUESTS R7 1b):** the deployed build_edl accepts a pin edited after its gates (it reads the
    two flags, not the sealed inventory), measured by smoke_r7. Tonight's pin f409e9d9 is untampered.
  - Audit spend runs outside the phase-2 ledger: cycle 2 about $4 by usage.
  - Ledger $54.47 of $64.28.

- 06:45 ET: after the pin (pushed 3716963e):
  - The unit tests are rewritten for tonight's contracts: 103/103 pass (phase 1 + phase 2).
  - smoke_r7 now tests a package_pin pin against the DEPLOYED pinned.py / edl_rules.py: SMOKE R7 PASS (R4 moments: VO 30.96 % of 63.95 s).
  - The design doc is current; REQUESTS R7 item 1 is marked LANDED by the integrator (1b: the optional seal re-check, as exact code).
  - The phase-2 AUDIT CYCLE 2 is running: claude-opus-5-5, claude-sonnet-5-5 and grok-4.20, on 3 chunks (about $4). The code commit waits on it.

- 06:30 ET: rulings 5 and 6 are encoded; the must-fail check is 41/41; attempt 9 passes every gate; the pin is written; READY TO RENDER on line 1.
- 06:20 ET: rulings 3-4 encoded; the must-fail check is 41/41; attempts 5-8 narrowed the context gate to cited words (no change to what a must-fail case gets).

- 06:12 ET: attempts 3-4 on the 06:00 package. Every line passes; coherence 5/4/5 (VO 5); context integrity fails clip_01 (NOT_ENTAILED) and clip_02 (RETRACTION). Both are held for the orchestrator's rulings. Next: ruling 3's must-fail check on the exam's context-integrity cases (the cheapest capable model).

- 05:50 ET: attempt 2 done (110 s, $0.44): every line and gate passes except clip_01's context (referent), coherence (clip_02 off the angle) and the runtime (59.71 s). Held for the orchestrator's clip decision; meanwhile the audit fixes continue (no model calls).

- 05:41 ET: ORDER 05:35. The orchestrator's own package is running through the corrected gates now (attempt 1,
  tests/package/run_given_package.py). Two structural findings before any model call, from the factory's own code:
  - (1) **The renderers play hook -> VO intro -> clip_01 -> bridge (after clip 1) -> clip_02 -> bridge (after clip 2)
    -> shout-out** (render16.py:306-334, render_vertical.py:853-880).
    - So the VO "intro" is heard AFTER the hook.
    - The 05:35 intro and the hack tease share that one slot.
    - A takeaway after the last clip IS placeable (after_clip 2).
  - (2) **The factory's EDL rule R4 runs on pinned runs** (run_fresh.stage_validate -> edl_rules.validate_edl, a HOLD
    on failure). It caps VO at 25 % of runtime and at one bridge per channel transition.
    - The 05:35 package as written fails R4: "2 bridges but only 1 channel transitions; VO=38% of runtime (max 25%)",
      at an estimated 70.09 s.
    - The variant that FITS R4 keeps: hook (Saifedean Ammous) -> intro "Nobody is in charge of Bitcoin. That's not a
      flaw. That's the design." -> What Bitcoin Did -> "And Stephan Livera thinks the market still hasn't priced that
      in." -> Stephan Livera (all three sentences: L-v 2 confirmed his numbers) -> sign-off. It estimates 60.48 s,
      R4 PASS.
    - The hack tease and the takeaway do not fit R4. Keeping them is an R4 change, which is the integrator's /
      orchestrator's call.
  - Gate fixes landed for this run (audit p2 C1_CONSENSUS):
    - the classifying verdict (A / B / C / D);
    - hedge-matched attribution verbs;
    - the context window at least 90 s / 60 s, with intact selection markers;
    - step B rates every pair;
    - step A names who speaks with quoted evidence (L-v 1);
    - L-v 2 in both directions through the router (ElevenLabs while OpenAI is dry);
    - the runtime arithmetic (the sign-off was subtracted twice);
    - DUPLICATE against every clip;
    - the exclusion verdict never on the miner's model.

- 05:36 ET: AMENDMENT 05:30 applied. Budget $25 (guard $64.28). Order:
  1. Classification A / B / C / D + the no-paraphrase VO style, replaying wherever a prompt is unchanged.
  2. Tonight's package: at most 3 angles x 2 writes; the cheapest capable model per verdict (claude-opus-5-5 at
     $0.01 a call, measured, so the writer runs on another vendor: grok-4.20); stop at the first coherence >= 4.
  3. The exam, then, on Heimdall / local plus at most $5 frontier ($0.70 left of that).
  - The yield sweep is postponed.
- 05:30 ET: the ElevenLabs Scribe back-end works for L-v 2's second pass while OpenAI is dry. One live call: 9.1 s of
  audio, 1.0 s, $0.0018, one diarised speaker, the clip's words.
- 05:27 ET: DECISION 05:25 received.
  - Guard: $39.28 spent, plus the $60 raise = limit **$99.28** on the same ledger.
  - Plan, in order:
    1. Exam BEFORE: the gates exactly as audited, rebuilt from the audit's STEP.diff, run in the background by the
       pp-tests harness with network.
    2. In parallel: the VO-gate classification A / B / C / D (05:25 item 1-2), the write styles (item 3: tease /
       hedge-matched hand-off / host takeaway; quote-led second; plain last), the step-A-once ledger and the
       concurrent verdicts (item 5).
    3. The audit cycle-1 consensus fixes already under way (docs/audits/parallel/pp-selectid_audit_p2/C1_CONSENSUS.md):
       the sealed gate inventory, verdict coverage, exclusion in production, L-v 2 mandatory, ...
    4. Exam AFTER.
    5. Rebuild tonight's package, at most 4 angles x 3 writes, stopped at the first coherence >= 4, at <= 6 min and
       <= $1.50 per package (measured), at the top of STATE.

## 05:00 ET Nov 12: HELD AT THE SPEND GUARD. No package for tonight passes every gate yet (nothing to render)

- **Spend.** Phase-2 stand-in spend stopped at **$39.28** of the $40 guard (254 calls, upper-bound prices). Model calls
  are stopped as ordered. Every reply is recorded under tests/moments/fixtures and tests/package/fixtures, so a re-run
  REPLAYS them at no cost and continues where this stopped.
- **OpenAI is out of credit again** (HTTP 429 insufficient_quota, 04:37). The L-x failover moved the writer to
  claude-fable-5-2, and the verdicts to vendors other than the writer's, with no human step.
- **Tonight, fresh_20261112_050611.** 4 angle-first rebuilds after the 03:40 review, about 30 write-and-gate attempts
  over 12 proposed angles, produced NO package that passes every gate. The integrity gates did their job:
  - No unsupported claim, no false relation and no stale price reached a package. The 03:25 first package (score
    first, plain-like VO) is superseded below.
  - The blockers, measured attempt by attempt:
    - (1) step C "stronger certainty": the VO's framing made a hedged clip ("I feel like ...", "I think ...") sound
      firm;
    - (2) the fidelity judge's "uncertain" on PBX MAX's own synthesis lines ("Bitcoin is secure; keeping yours still
      takes work").
  - The writer oscillates between (1) and (2).
  - The calibration fixes made along the way are listed in E-FAIL-PS14. None loosens a rule:
    - multi-segment verbatim support for a point;
    - step B asks L-s's own relation question;
    - VO-caused context failures go back to the writer;
    - false NAME / NUMBER rejects fixed;
    - production facts are citable.
- **What decides the next step** (the orchestrator's call; I take no option on my own):
  - (a) **Calibrate on the exam.** pipeline_pp_tests' 135 real cases measure each gate's false-reject rate. The
    adapter is ready (pipeline/moments_gate_adapter.py), and recording its replies needs model calls. On the
    integrator's LOCAL leg (gemma3:27b under the GPU0 lease) this is free; on the frontier chain it is about $8-20.
    If the fidelity verdict rejects faithful paraphrases above 10 %, it is miscalibrated, and I fix it with that
    evidence.
  - (b) **More budget for the frontier legs.** One passing package costs about $2-3 by tonight's measurement (each
    write-and-gate attempt about $0.45). The 9-universe yield sweep needs about $15-25.
  - (c) **A quote-led VO style.** The VO introduces each channel with a verbatim fragment of its own words. The point
    is carried by that sequence and by ONE checked title. Its claims are then verbatim by construction.
- **Yield against the oracle (law L-n).** No package exists on any saved universe under these gates. The oracle
  judged 48 moments-first line-ups to pass, but under its own rules: caption timing, two clips from one channel, no
  context-integrity gate. These are 10 DEFECTS until packages pass. Mining is done on all 10 (word-timed: 4-14 videos
  each, 9-65 usable moments). Packaging the other 9 is held by the guard.
- **Cost, measured** (upper-bound prices; production mines locally at $0):
  - per cycle: about $2-3 of frontier writing and verdicts for one passing package, plus step A (about $0.30) and
    angles (about $0.15);
  - per day at 6 cycles: about $12-18;
  - at the 2 / day launch cadence: about $4-6 a day, roughly $120-180 a month, inside PBX's $100-300.
- **Audit.** Phase 2 cycle 1 is DONE (5 reviewers per chunk: fable, opus, sonnet, grok answered; the gpt-4o leg failed
  on OpenAI's credit). Next: dispositions, the fixes, cycle 2, commit and push (not DONE).

## SUPERSEDED (orchestrator review 03:40: passes the safety gates, fails the product; NOT for render): the first moments-first package (03:25 ET Nov 12)

Files: `tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json` (sha256 1c3f0e783059c2f1..., PINNED decision for run_fresh.py `--pinned`; needs REQUESTS R7 item 1
for the VO / title / caption to reach the EDL) and `tests/package/proof/fresh_20261112_050611/package.json`
(sha256 34e70efb42d02e48..., every check and model). Branch pp-selectid, worktree ~/worktrees/pp-selectid.

Gates passed:
- VO fidelity, on every VO line, the title and the caption: the deterministic rules, then the blind verdict
  (grok-4.20-0309-reasoning at temperature 0), every claim supported with verbatim words.
- Context integrity (law L-s): step A (grok, context only), step B (claude-opus-5-5, the package only), step C (grok).
  For every clip: own sincere assertion, referents inside, no false relation, entailed, not stronger.

Rules met:
- One clip per channel and <= 20 s per source video (law L-u).
- 4 channels, all layout-eligible, all on word timing (law L-e).
- Runtime estimate 60.42 s.

Writer: openai:gpt-6.1-sol; the VO was rewritten once after a fidelity rejection.

TYPE moments
TITLE: Bitcoin ran from 16K to 126K
CAPTION: Bitcoin ran from 16K to 126K. That move comes out to about an 8x.
HOOK'S FIRST WORDS: Bitcoin does not have any authority that allows

VO intro: Bitcoin ran from 16K to 126K.
- [hook] Saifedean Ammous | vgsSZ4mAHfQ 5144.99-5153.37 (8.38 s) | source 30 s before: https://www.youtube.com/watch?v=vgsSZ4mAHfQ&t=5114s
  "Bitcoin does not have any authority that allows people to take the wealth of others. If some people end up with more Bitcoin, that's because they chose to do that."
- [clip_01] Stephan Livera | Sjb6lUiL0m4 1826.54-1843.48 (16.94 s) | source 30 s before: https://www.youtube.com/watch?v=Sjb6lUiL0m4&t=1796s
  "However, I think Bitcoin is by far the most undervalued asset in like the entire global financial system right now. So, you know, Bitcoin gold parity is around like $1.5, $1.4 million per Bitcoin last I checked. It's very, very undervalued."
VO bridge: Next, What Bitcoin Did on intermediaries getting hacked.
- [clip_02] What Bitcoin Did | c1JGheQBPH4 2480.28-2491.52 (11.24 s) | source 30 s before: https://www.youtube.com/watch?v=c1JGheQBPH4&t=2450s
  "It's not Bitcoin that's getting hacked. It's other intermediaries. So in some ways, it kind of shines a light on the secure nature and the unique nature of Bitcoin."
VO bridge: Next, Simply Bitcoin on Bitcoin's move from 16K to 126K.
- [clip_03] Simply Bitcoin | Noq6txZU91c 399.15-405.25 (6.1 s) | source 30 s before: https://www.youtube.com/watch?v=Noq6txZU91c&t=369s
  "Bitcoin ran from 16K to 126K. That move comes out to about an 8x."
VO sign-off: Clips today from Saifedean Ammous, Stephan Livera, What Bitcoin Did, and Simply Bitcoin. Go follow them for more. Links are below.

FLAGS (named, not hidden):
- (a) Runtime: segments 42.66 s (word timing) + VO 24 words at 2.6 w/s (assumed) + fixed 7.38 s; the render measures the final. The estimate is 60.42 s, at the LOW edge of 60-70 s.
  A faster VO read could land under 60 s; the release gates measure the final.
- (b) Law L-v 2: the second recognition pass against the SOURCE audio is running now. Until it confirms them,
  the clips' numbers (16K, 126K, 8x, $1.5 / $1.4 million) rest on one Whisper transcript, and so does the title.
- (c) Law L-v 1: speaker turns are judged by step A ('no change inside'). No diarisation has run yet.
  No person is named in VO or title beyond the credited shows.
- (d) The clip_01 opener 'However, ...' is a discourse marker. Context integrity judged the clip to stand on its
  own. Downstream stand_alone (R6 item 2) may still ask the clip scorer.
- (e) REVIEW ONLY (law L-q): selection and VO by the new path, not yet merged or audited.

## MOMENTS / PACKAGE INPUT CONTRACT v0 (published 02:36 ET Nov 12 for pipeline_pp_ingest; fields may be ADDED, never renamed or removed)

The moment ledger is append-only JSONL, one moment per line. Proposed path: `data/editorial/moments/moment_ledger.jsonl`
(the ingest session owns the path; the packager takes it as an argument). A moment is whole sentences of ONE source
record, by id; its text is never rewritten.

```
{"schema": "pp.moment/1",
 "moment_id": "<sha256('video_id|transcript_sha256|w0|w1')[:20]>",   # stable identity: same record + same words
 "video_id": "...", "channel_id": "...", "channel_name": "<registry display_name>",
 "published_at": "<aware ISO-8601 of the ORIGINAL upload>", "title": "<exact video title>",
 "transcript_sha256": "<transcript_store segments sha>", "transcript_method": "...",
 "timing": "word" | "segment",                    # word = sentence-ready word record (law L-e); else captions / segments
 "words": [w0, w1],                               # token indices into select_by_id.tokens_from_record(record)
 "sentences": [k0, k1],                           # into eligibility.split_sentences(tokens): WHOLE sentences only
 "text": "<eligibility.spoken(tokens[w0..w1]): verbatim as spoken, law L-h>",
 "start": s, "end": s,                            # the record's own times (seconds from the file start)
 "duration_s": s | null,                          # word timing only; else null and:
 "duration_estimate_s": s | null,                 # caption / segment timing: a FLAGGED estimate, never used for runtime
 "speaker": {"turn_change_inside": bool | null, "label": str | null, "confidence": float | null,
             "named": str | null, "named_source": "metadata" | "diarisation" | null},   # law L-v (1); null = not measured
 "scores": {"hook_first_2s": 0-5, "quotable": 0-5, "surprising_fact": 0-5, "stance": 0-5, "stakes": 0-5,
            "stands_alone": 0-5, "contempt_outrage": 0-5},   # integers; contempt_outrage is a PENALTY (law L-u)
 "names_person": bool,                            # a fact, never a positive axis on its own (L-u)
 "risk": ["accusation" | "partner_attack" | "imperative" | "guaranteed_return" | "single_source_breaking" |
          "ad_read" | "third_party_media" | "price_prediction" | "doom" | "politics_non_btc" | "time_sensitive"],
 "topics": ["<closed Bitcoin taxonomy id>", ...],  # pipeline/trend_brief.py TAXONOMY (published with phase 2)
 "reason": "<= 160 chars, model text: FORENSIC ONLY, never enters a prompt or anything audience-facing",
 "eligibility": {"role": "clip" | "hook", "ok": bool, "reasons": [...], "targets_missed": [...]},  # eligibility.eligible
 "mined": {"by": "<model name@digest>", "prompt_sha256": "...", "reply_sha256": "...", "at": "<ISO>", "cycle": "..."}}
```

Rules the packager applies on reading; the ingest session may pre-apply them, never relax them:
- The packager reads "best unused moments since T": lines with `mined.at >= T` or `published_at >= now - 72 h`, de-duplicated by
  `moment_id` (the latest line wins), minus moments delivered in the previous 24 h (DEC-9 / L-p novelty, delivered
  moment ids).
- A moment the packager can use must have:
  - `eligibility.ok`, re-judged by the packager with its own clock;
  - no hard-exclusion risk flag (L-u): accusation, partner_attack, imperative, guaranteed_return,
    single_source_breaking, ad_read, third_party_media;
  - `speaker.turn_change_inside == false` (L-v 1; null = not measured = not usable on screen, law L-m);
  - word timing for anything heard (L-e).
- Down-weighted, not excluded: price_prediction (at most one per video), doom, politics_non_btc. Ranking is deterministic
  (scores minus penalties, ties by moment_id).
- Fairness (L-u): at most ONE clip per channel per video and at most 20 s per source video. The opt-out registry
  `pipeline/optout.json` (channel ids; PBX 02:35) is honoured by the miner AND the packager.
- Package output `pp.package/1`: type story | moments; ordered segments (moment ids, verbatim text, times); the PBX MAX VO
  (intro, bridges, sign-off); ONE title, ONE caption (L-t); checks (VO fidelity, context integrity L-s, exclusions,
  runtime); the model per artefact; dollars. Detailed with phase 2 in docs/audits/MOMENTS_FIRST_DESIGN.md.

## LIVE STATE (newest first; ET; times corrected 01:46 from file times: four entries had been stamped

## from an elapsed-time estimate, 30-110 min late)

- 04:20 Nov 12 TONIGHT'S ANGLE-FIRST REBUILD, attempt 3 (no package yet).
  - Each failed pass so far was read, and the gate calibrations it exposed are fixed with evidence (E-FAIL-PS14). None
    loosens a rule:
    - multi-segment verbatim support for a point;
    - step B asks L-s's relation question: no false relations since the fix;
    - VO-caused context failures go back to the writer.
  - The writer now oscillates between VO fidelity and step C's "stronger certainty". One rewrite passed fidelity but
    made a hedged clip sound certain; the next fixed that and overreached in paraphrase.
  - Phase-2 stand-in spend: $30.80 of $40. If no package comes within the remaining budget, I stop model calls and
    record exactly where it stands.

- 03:59 Nov 12 REBUILD IN PROGRESS (angle first). Measured on tonight's universe and fixed, with no rule loosened:
  - The first angle proposals backed angles with 2 channels and 26.9 s of clips; L-u needs 3 channels. Each angle now
    takes 4-8 moments from >= 3 channels, with the clip-seconds range given to the proposer.
  - The fidelity verdict rejected every cross-clip POINT, because only one segment's words could support a claim. A
    claim may now cite several segments, each with verbatim words that code verifies. The judge says yes only if
    together they state it with nothing added. Production facts ('clips from A, B, C', 'links below') are a citable
    manifest segment.
  - The deterministic NAME rule flagged sentence-initial words and Title Case titles ('Past', 'Beyond', 'Bullish
    Claims Don't Erase Risk'): false rejects, fixed. Real names are still caught by mid-sentence capitals, ATTRIBUTION
    and the verdict; a 9-case check passes both ways.
  - NUMBER read the idiom 'one thing' as the figure 1: number words <= 10 without a unit are counts.
  - Step A now sees the show date, the publish date and caption speaker turns, and answers time_ok (law L-v 3).
  - The mining A/B (blind, judged by claude-opus-5-5) found gpt-6.1-sol better than Heimdall qwen3.8-27b: 6/6
    accepted against 5/6, 300 s against 2,067 s. The mining chain is now local -> gpt-6.1-sol -> claude-fable ->
    Heimdall qwen. The local leg is the integrator's.
  - The exam (pipeline_pp_tests, 135 cases) is in place. My adapter is pipeline/moments_gate_adapter.py.
  - Phase-2 stand-in spend: $27.23 of $40.

- 03:36 Nov 12 ORCHESTRATOR REVIEW 03:40 RECEIVED: the first package passes the safety gates and fails the product.
  Rebuilt to its six rules:
  - (1) A fidelity reject gets up to 3 rewrites with the exact rejected claims. The plain VO comes after that, is
    labelled, and ranks last.
  - (2) Angle first: angles, each one repeatable sentence backed by >= 3 moments from >= 2 channels, with the hook per
    angle. A blind COHERENCE verdict on another vendor (claude-opus-5-5 when the writer is OpenAI) gives the
    through-line and 1-5 ratings; below 4, or "none", moves to the next angle.
  - (3) PRICE_NOW: a headline line's price level must be marked as history or match the universe's current level. The
    case is sent to pipeline_pp_tests in REQUESTS R8.
  - (4) DUPLICATE: no clip repeats the line before it or the title. A clip under 8 s only as the punchline.
  - (5) The hook is chosen per angle.
  - (6) Law L-v 2 runs inside the build: a segment whose number or negation the second pass does not confirm, or with a
    speaker change, is dropped.
  The first package is superseded (it stays in git as the evidence of what failed). Tonight's rebuild (a top package
  plus 2 alternatives) is running.

- 03:17 Nov 12 PHASE 2 IN PROGRESS (this machine's clock). The 03:00 note is received.
  - The exam is pipeline_pp_tests': my gates run under its harness through pipeline/moments_gate_adapter.py. Its
    format is v1, and I write no must-fail corpus beyond unit fixtures.
  - Under moments-first there is NO same-event test.
  - Yield is measured per universe against the oracle (tests/package/yield_table.py ->
    pp-selectid_YIELD.md): a universe where the oracle has a line-up that passes and I have no package is a defect.
  - Built (uncommitted, unaudited):
    - providers.py + model_providers.json (L-x);
    - trend_brief.py (shadow);
    - moments.py (miner + the L-u exclusion verdict);
    - package.py (sets + runtime arithmetic + writer + gates);
    - vo_fidelity.py; context_integrity.py (L-s);
    - moments_gate_adapter.py; package_pin.py (a package as a PINNED decision).
    Tests: 24 unit tests pass.
  - Tonight (fresh_20261112_050611): 6 mining calls, all accepted; 62 moments, 58 usable on screen.
  - The first package attempts were refused by the gates, and every refusal was read:
    - a sarcastic hook, correctly refused;
    - genuine outside referents, correctly refused;
    - two false rejects, fixed with the evidence in NOTE-PS12: a cleft "it" and a generic "we";
    - one bug, fixed: the NAME rule did not strip a possessive ("Bitcoin's").
  - The packager now screens each moment's own context (step A, package-independent) BEFORE writing; the rebuild is
    running.
  - Mining sweep over the other 9 universes is running (gpt-6.1-sol, recorded).
  - Spend: phase 2 $9.59 of the $40 guard.
  - Heimdall: $33.68 of $500 (6.7%), far from the 90% tripwire.

- 02:53 Nov 12 PHASE 1 DONE: d809a1f8, pushed. Was: COMPLETE, COMMITTING. Audit cycle 2 dispositions: pp-selectid_audit/C2_DISPOSITIONS.md (23
  fixes implemented, each with a test that fails on the pre-fix code; 6 refuted with evidence; 8 limits for PBX or the
  integrator). Checks: 123 tests passed (10 GPU-skipped), SMOKE PASS, regression_test.sh 26 PASS / 0 FAIL.
  - Proof column of record: judge at temperature 0, production parity. The proof table is below; the per-defect
    answers are in pp-selectid_PROOF.md.
  - No saved universe produced an accepted line-up. The preview's story was accepted, and its line-up call declined
    although a line-up that passes our rules exists (a generator recall miss, recorded). Most clusters stop at the
    per-sentence check, today's strict same-event judgement.
  - Three old universes (Nov 6-7) are still running in this column and follow in the next commit.
  - Stand-in spend for phase 1: $23.33 estimated (upper-bound prices), plus the audits (cycle 1 and cycle 2 reviewer
    calls, ~$11 estimated), against a $40 guard on stand-in spend.

## PHASE 1 PROOF TABLE (generated: tests/select_by_id/proof_table.py)

### Column of record
| run | written (ET) | judge | groups screened 48h / 72h | story calls | outcomes per group | line-up | every id resolves | line-up passes eligibility (re-check) | claim (verbatim source sentence) |
|---|---|---|---|---|---|---|---|---|---|
| fresh_20261112_050611 | 02:43 | grok-4.20-0309-reasoning@t0 | 42 / 18 | 8 | 5 declined, 3 rejected, 1 no model call | no | - | - | - |
| fresh_20261111_190259 | 02:45 | grok-4.20-0309-reasoning@t0 | 41 / 12 | 8 | 4 declined, 3 rejected, 1 story; line-up not asked (no word record) | no | - | - | Bitcoin touched its 200 day moving average today. |
| fresh_20261111_213954 | 02:46 | grok-4.20-0309-reasoning@t0 | 38 / 19 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261112_001448 | 02:40 | grok-4.20-0309-reasoning@t0 | 38 / 19 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261112_013452 | 02:42 | grok-4.20-0309-reasoning@t0 | 39 / 21 | 8 | 4 rejected, 4 declined | no | - | - | - |
| fresh_20261110_093150 | 02:45 | grok-4.20-0309-reasoning@t0 | 24 / 14 | 8 | 6 declined, 2 rejected | no | - | - | - |
| fresh_20261111_192645 | 02:42 | grok-4.20-0309-reasoning@t0 | 41 / 15 | 8 | 5 declined, 3 rejected | no | - | - | - |
| fresh_20261107_080503 | 02:54 | grok-4.20-0309-reasoning@t0 | 31 / 28 | 8 | 5 declined, 3 rejected | no | - | - | - |
| fresh_20261107_065702 | 03:10 | grok-4.20-0309-reasoning@t0 | 23 / 16 | 8 | 6 rejected, 2 declined | no | - | - | - |
| fresh_20261106_213852 | 03:17 | grok-4.20-0309-reasoning@t0 | 45 / 22 | 8 | 6 declined, 2 rejected | no | - | - | - |
| pinned_20261111_172202 | 02:37 | grok-4.20-0309-reasoning@t0 | - / - | 1 | 1 story; line-up declined | no | - | - | Bitcoin has now seen a 16 % decline from the overall high from $88,000, touching down towards about $73,400, $ |

Models per run file (generator / judge): {"generator": "anthropic:claude-fable-5-2@medium", "judge (ModelChecks)": "xai:grok-4.20-0309-reasoning@t0", "openai_probe": "ok"}

Stand-in spend estimate, all proof runs of this session: $28.1105 over 526 calls (1392790 prompt / 616196 completion tokens); per model, at the upper-bound USD prices per 1M tokens [input, output] each stand-in declares:
- anthropic:claude-fable-5-2@medium: 172 calls, $10.5093 at [8.0, 40.0]
- anthropic:claude-opus-5-5@medium: 49 calls, $1.2753 at [4.0, 20.0]
- xai:grok-4.20-0309-reasoning: 106 calls, $5.3511 at [5.0, 25.0]
- xai:grok-4.20-0309-reasoning@t0: 157 calls, $8.008 at [5.0, 25.0]

### pinned_20261111_172202 (the approved preview): overlap with its four passages
| approved | channel | chosen by select_by_id | same words | overlap s | eligible with the model's own story | why not |
|---|---|---|---|---|---|---|
| hook | DataDash | - | False | - | True |  |
| clip_01 | Natalie Brunell | - | False | - | False | no_story_statement: holds no sentence that states the story (editorial_select anchored_window) |
| clip_02 | Yahoo Finance | - | False | - | True |  |
| clip_03 | Bitcoin Magazine | - | False | - | False | layout_ineligible: Bitcoin Magazine: burned-in chyron (has_chyron, DEC-12d); not_sentence_ready: no sentence-ready word record (law L-e): a stretch reads unpunctuated; no_story_statement: holds no sentence that states th |

- 02:40 Nov 12 (this machine's clock; the note is stamped 02:45) NOTE RECEIVED: L-x NO SINGLE MODEL, ULTRON FIRST.
  - Phase 2 puts every model role behind ONE provider interface, with a config naming at least two interchangeable
    back-ends per role, in this order: local gemma3:27b on Ultron first, then frontier (OpenAI / Anthropic / xAI) or
    Heimdall (OpenAI-compatible, HEIMDALL_API_KEY). The roles are mining, scoring, angle / packaging, VO / title
    writing, the fidelity verdict, the context verdict and the trend brief.
  - The run continues when a vendor fails: out of credit, 429, 5xx or transport errors. Generator and judge are always
    different models. No vendor or model name appears outside the config.
  - A blind A/B harness per role, with its prompts, is provided. The integrator runs the local leg under the GPU0
    lease; this session runs the frontier and Heimdall legs.
  - Heimdall spend: the 90% tripwire is a NOTIFY ("HEIMDALL SPEND AT 90%" at the top of this file) and a fallback,
    never a halt.
  - For phase 1, R1's patch builds `OllamaModel(L)` directly. Under L-x it will take the role's provider chain from the
    phase-2 config; recorded in REQUESTS R6.

- 02:36 Nov 12 ORDERS 02:30 (strategy audit: laws L-s..L-w) AND 02:35 (PBX decisions) RECEIVED.
  - All four strategy reviews were read before continuing (heimdall_probe/pp_redteam/strategy: claude.md, gpt.md,
    grok47.md, grok420r.md). Phase 2 is built to L-s..L-w, and none of its output is called DONE without them.
  - Consequences for phase 1: L-w 3 keeps story-first as a package type, so R1 is that type's selector (not superseded).
    L-u (one clip per channel, <= 20 s per source video) is recorded in REQUESTS R6 and applied by the phase-2
    packager; the audited predicate is unchanged.
  - 02:35: the moments/package input contract for pipeline_pp_ingest is published at the top of this file. The
    opt-out registry file replaces partner outreach. Frontier models write and check (angle, VO, title, fidelity,
    context), with dollars per video reported. The launch cadence is 2 videos a day. Vocabulary: "a line-up that
    passes our rules", never "legal".
  - Phase 1 is nearly finished. Audit cycle 2 dispositions are in pp-selectid_audit/C2_DISPOSITIONS.md, and 23 fixes are
    implemented with tests that fail on the pre-fix code. Smoke pass; 123 tests passed (10 GPU-skipped);
    regression_test.sh 26 PASS / 0 FAIL. The proof is re-running on the final code with the same generator for the
    whole column. Commit and push follow.
  - CORRECTION: the OpenAI probe's HTTP 400 from 01:44 to 02:30 was the probe's own wording. json_object mode needs the
    word "JSON" in the messages. It was not the account: from 02:07 OpenAI answered every correctly worded call.
    Fixed; the probe returns ok.

- 02:08 Nov 12 PHASE 2 ORDER + ADDITION (01:55) AND ORCHESTRATOR NOTE (02:00) RECEIVED. Phase 1 is finished first
  (audit kept), then Phase 2 starts. Model roles, per the 02:00 note, recorded per artefact:
  - Phase 1 proof (started 02:02, three processes over the 11 saved universes): generator
    anthropic:claude-fable-5-2@medium (its OpenAI probe at 02:02 answered HTTP 400 invalid_request_error); judge
    xai:grok-4.20-0309-reasoning on XAI_API_KEY_MEDLEY (ModelChecks: verify_support on the claim, verify_reaction on
    non-statement sentences; told it has no tools and must answer in one message). One generator for the whole
    column, so the table mixes no models.
  - OpenAI re-probed at 02:07: HTTP 200 from gpt-6.1-sol (three request variants). Work after this proof goes back to
    gpt-6.1-sol as generator / stand-in. The judge stays Grok, so generator and judge are on different vendors. Next
    probe after any 429 / 5xx: in about 20 min.
  - Audit cycle 2 running on the FIXED diff, split into two chunks of < 220,000 bytes (the tool drops larger files):
    claude-fable-5-2, claude-opus-5-5, claude-sonnet-5-5, the tool's own gpt-4o leg (OpenAI credit back) and
    grok-4.20-0309-reasoning (medley key). That is three vendors.
  - Phase 1 spend estimate (upper-bound prices): $8.27 at 02:05, against a $40 guard.

- 01:44 Nov 12 RUNNING: (1) the full proof with the substitute stand-in claude-opus-5-5 (A6; preview row done: the same
  story as gpt-6.1-sol found, then the line-up call DECLINED, which is the correct answer under today's rules for that
  story marking; one call); (2) audit cycle 1 on the actual diff (docs/audits/parallel/pp-selectid_audit/STEP.diff,
  213,853 bytes, base BASE.txt). BLOCKED-PARTIAL (audit legs): utils/cross_llm_audit.py cannot run its three external
  legs here: the permitted env file defines no GEMINI_API_KEY and no XAI_API_KEY (the names the tool reads; checked
  by presence only) and the OpenAI account is out of credit. The audit therefore uses the tool's own package builder
  and cycle-2 cross-review prompt with three Anthropic reviewers named as such (claude-fable-5-2, claude-opus-5-5,
  claude-sonnet-5-5); the cross-vendor leg is the integrator's own two-cycle audit of this branch before merge.

- 01:40 Nov 12 STAND-IN SWITCHED: the OpenAI account is out of credit (the API answers HTTP 429 type
  insufficient_quota, code credit_balance_exhausted; the key is shared by every session; this session's own estimate
  at upper-bound prices is $2.97 over 42 calls). The 01:34 re-run made no call and was stopped by me. Assumption A6
  below: the proof continues with Gemini as the stand-in. regression_test.sh 26 PASS / 0 FAIL in this worktree
  (after copying the gitignored assets outro_branded.mp4 + music/*.mp3 from the main tree, read only; never
  committed); pipeline test_canon (site test covers the new modules) / test_stand_alone / test_dec13_clusters /
  test_editorial_robust / test_backtest: 67 passed, 10 GPU-skipped.

- 01:34 Nov 12 IN PROGRESS: full proof re-running (nine saved universes + the preview; stand-in gpt-6.1-sol, every
  reply recorded under tests/select_by_id/fixtures/replies; spend estimate before this run $2.97 of the $40 guard).
  Built since 01:08: select_by_id.run_pools (the production entry: DEC-13 pools by id, word pass between the calls,
  ledger-form evidence); the R1 wiring patch (editorial_select pools -> run_pools; select_passages hook + >= 2 clips)
  in pp-selectid_REQUESTS.md, git-apply clean on c1451047 and SMOKE PASS end to end on a temp copy
  (tests/select_by_id/smoke_wiring_patch.py: the approved DataDash / Natalie / Yahoo line-up word for word; a
  fabricated id holds the run). Found and fixed by the stand-in's real replies: D4 (a) needs the event's names (the
  claim's), retry reasons must use the model's ids, row hints must never promise what the judge refuses, a one-word
  sentence starred a statement (today's 5-token statement floor + asymmetric `states`), the line-up call needs a
  final decline. 38 tests pass. Next: proof table, cross-LLM audit (2 cycles), commit, push.
  NOTE: the first full proof run got HTTP 429 on every call for five runs (shared OpenAI key); the stand-in now backs
  off (20/40/80/160 s) and records the API's error code.

- 01:08 Nov 12 IN PROGRESS: pipeline/eligibility.py + pipeline/select_by_id.py written (uncommitted);
  tests/eligibility (18) + tests/select_by_id (16) = 34 passed, all eight ordered must-fails among them. Design doc
  docs/audits/SELECT_BY_ID_DESIGN.md written (rule inventory with file:line). Next: the proof driver over the saved
  universes (stand-in model, recorded), then audit, commit, push.
  Found on the way (to BIBLE_ADDITIONS): pipeline/backtest.py _run_transcript uses a run's WINDOW transcript
  (select_passages: offset 23.38 s etc.) as full-video word timing; the protected preview's Bitcoin Magazine window
  transcript fails today's whole-record L-e readiness on one word 570 s from its clip.

- 00:52 Nov 12 IN PROGRESS: read-in done (CONSTITUTION, PIPELINE_LAWS, CROSS_LLM_AUDIT_LAW, docs/QWEN_CONTEXT_BIBLE.md,
  DEFINITION_OF_DONE_PULSE_CHECK.md, REDTEAM_2026-11-11.md; editorial_select, story_semantics, select_passages,
  sentence_law, stand_alone, run_fresh, canon, transcript_store, backtest, edl_rules). Writing the design doc
  (rule inventory with file:line), then pipeline/eligibility.py + tests, pipeline/select_by_id.py + tests, the proof
  over saved runs, the audit (2 cycles), commit + push. Nothing committed yet. Nothing blocked.

## ASSUMPTIONS (most defensible reading; the integrator may overrule)

- A1 RUN NAMES: `fresh_20261112_014204` does not exist under runs/. The integrator's own DoD (main tree, LIVE STATE
  00:06 ET Nov 12) records that the run it describes is `fresh_20261112_013452`. The named holding runs are therefore
  fresh_20261111_213954, fresh_20261112_001448, fresh_20261112_013452; fresh_20261111_190259 (the E-FAIL-030 crash,
  the fourth fully automatic run that held on a selection defect) is answered too. Every other saved universe is a row.
- A2 SAVED UNIVERSE TEXT: a saved universe (runs/<day>/TOPIC_SELECTION.json) names its transcripts by sha; their text
  lives in the shared store /home/ultron/protocol_pulse/data/editorial (not in runs/). The proof reads those records
  READ-ONLY, each hash-checked against the sha the run recorded (exactly how the repo's pipeline/backtest.py replays a
  day), plus cached embedding vectors from the same store to rebuild the DEC-13 clusters on CPU. Nothing is written
  there or anywhere in the main tree. No GPU, no Whisper, no Ollama.
- A3 "HOOK ID": read as a hook RANGE of whole sentences ([n, n] = one sentence): the existing hook budget allows 1-3
  sentences of 8-12 s (editorial_select.py:49, :52); a one-sentence-only hook would cut supply without a law saying so.
- A4 CLAIM: the model also returns `claim`, one id out of its story ids; the claim shown downstream is that sentence's
  text verbatim. Still ids only.
- A5 STAND-IN MODEL: gpt-6.1-sol (OPENAI_API_KEY read by name inside code) only for the proof; every reply recorded so
  tests replay offline. Spend guard: priced at an assumed upper bound of $15 / 1M input and $120 / 1M output tokens
  (reasoning included); model calls stop when the estimate reaches $40.

- A6 STAND-IN SUBSTITUTE: gpt-6.1-sol cannot be called (credit exhausted, the API's own error code). The order's
  intent is a stand-in for the local gemma3:27b while GPU0 is leased, so the proof uses another available frontier
  API in the same role: Gemini (GEMINI_API_KEY read by name in code; the repo's audit default model), behind the same
  Model interface, every reply recorded for offline replay, priced at an assumed upper bound of $2.50 / 1M input and
  $15 / 1M output tokens (thinking included) into the same cumulative $40 guard. The OpenAI replies already recorded
  stay as the audit trail (tests/select_by_id/fixtures/replies_superseded).
  CORRECTION (02:08): Gemini was NOT used. GEMINI_API_KEY is not defined in the permitted env file (checked by
  presence only). The substitute was claude-opus-5-5 (01:44 run), then claude-fable-5-2 from the orchestrator's 02:00
  note, with Grok on the medley key as the blind judge. gpt-6.1-sol answers again from 02:07.

## DONE (commit hashes)

- PHASE 1 DONE: d809a1f8 (pushed to origin/pp-selectid 02:53 ET Nov 12). Contents:
  - pipeline/eligibility.py and pipeline/select_by_id.py, with tests (23 + 29 + 27 cases);
  - the design doc docs/audits/SELECT_BY_ID_DESIGN.md;
  - the exact wiring patch, REQUESTS R1, `git apply --check` clean on c1451047, SMOKE PASS;
  - the proof table (above) with per-defect answers (pp-selectid_PROOF.md);
  - audit cycles 1 and 2, recorded in pp-selectid_audit/.
  The 3 Nov 6-7 rows of the column of record were added in the follow-up commit; they change no answer above.

## BLOCKED

- (nothing)
