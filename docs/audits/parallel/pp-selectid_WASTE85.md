# WASTE85: paid calls that bought nothing (ruling 85.3), pp-selectid

Read-only analysis. Window: every record in `tests/package/fixtures/replies/` with `recorded_at` from
2026-11-13T07:37:38Z (ledger_20261113_073738) to 2026-11-14T02:36:01Z (the last record; ledger_20261114_021501 had
finished and no build was running when the numbers were taken). Fixture paths below are relative to
`tests/package/fixtures/replies/`.

## What was counted, and what cannot be

- 432 recorded calls: 288 verdict / write calls, **$3.4549 vendor-reported** (every one of them carries
  `usage.usd_reported`, so the "estimated" column of classes (a)-(c) is $0.0000), and 144 transcriptions, $0.4690
  price-table estimate (no vendor figure).
- The builds' own meters since the cut (`usd_best_known` in each package.json) sum to $8.574. About $4.73 of the gap
  is calls abandoned at a deadline, booked but never recorded (see "Outside the three classes").
- Two kinds of call leave no record, so they cannot be costed per call: replies rejected as out of contract
  (`Router.reject` deletes them, pipeline/providers.py:817-826) and calls abandoned at a deadline
  (pipeline/providers.py:262-293). They show only as residuals between a build's meter and its records.
- Step A is batched (up to 8 moments a call). A re-asked moment is charged its share of the call (call cost divided
  by the excerpts in it); whole-call figures are given too.
- Clips-alone and coherence prompts carry no moment ids. Clips were mapped to ids by text and channel from each
  build's inputs.json. All 81 line-up verdicts since the cut resolved.
- Scratch scripts (python3 -I, read-only) are in this scratchpad: load.py, common.py, stepa.py, stepa_reask.py,
  hooks.py, lineups.py, facts.py, classb.py, writes.py, final.py. classb_out.txt is a dump of classb.py's output.

## (a) The same verdict asked again for an unchanged input

| sub-class | calls | $ reported | deliberate? | today |
|---|---|---|---|---|
| a1 step A: the identical excerpt (same moment, window, title, publish time, show date; the STEP_A prompt unchanged since 2026-11-12T11:22Z) asked again of the same model | 51 calls carry 243 such excerpts (14 calls are re-asks in full, $0.2844) | 0.7274 (excerpt share) | no | closed |
| a2 clips-alone: the identical prompt (same clips, same order) under another seed | 3 | 0.0269 | no | 2 closed, 1 open |
| a3 angle proposal: the identical prompt asked again of another writer | 2 | 0.0034 | no | open |
| hook ratings, fidelity, step B, step C, exclusion, speaker, visual, writes | 0 | 0 | | |

Re-asks that were deliberate (not counted as waste above):

| sub-class | calls | $ reported | why |
|---|---|---|---|
| d1 step A: the same excerpt except its show date (2026-11-13 to 2026-11-14) | 10 calls carry 51 such excerpts (3 in full) | 0.1500 | ruling 58 keys the show date so time words are judged again (pipeline/package.py:522-525) |
| d2 clips-alone: the same line-up after ruling 52 changed the question | 2 | 0.0192 | a new question |
| d3 step A by a second vendor (law L-x, order 06:22 item 45, ruling 82's failover) | 70 excerpts (each had only a grok verdict before) | 0.0378 | required, not waste |
| d4 retry after an out-of-contract reply | 1 recorded (hook rating, seed 8: e0/e06653910d5227ad2cdc298d023fd153d26a872be3e978dfb7e7a93ba8e44507.json, 2026-11-13T18:08:08Z) | 0.0048 | pipeline/package.py:712-728; the rejected seed-7 reply was deleted, its cost is unrecorded |
| d5 3-run majority (fidelity, seeds 7/8/9) | 0 | 0 | every fidelity call since the cut is seed 7; the build never runs the majority (VF.check with seed 7 at pipeline/package.py:1780, 1847, 1991); MAJORITY_SEEDS is used only by tests/package/run_given_package.py:276-322 |
| d6 fresh-write seed (ruling 66, FRESH_SEED 1000) | 0 | 0 | no write seed >= 1000; the one resting candidate (210211 tried[5]) expired under ruling 76 before its 6 h ended |

Examples:
1. a1: fb/fb259628cc09312cd813e5bbaeaab53b0fcce499333f9449c7775633b19b9695.json, 2026-11-13T07:40:19Z
   (ledger_20261113_073738). The identical 7-excerpt prompt had been answered by grok at 07:19:59Z
   (bc/bcf68fe1016e29075ddeb9b6cf2e7991aec9a5d4b9ccbcec99eb5b22a2990306.json, seed 15); asked again with seed 23
   (the seed is the batch's place in the queue, pipeline/package.py:543). $0.0196.
2. a1: 2e/2e30fa9200a5120e497bee643af8a2370039600a6411e3ca4648fbcb0a9a1807.json, 2026-11-13T09:24:25Z
   (ledger_20261113_092234). All 8 excerpts had been answered by grok in earlier builds. This re-ask turned
   c3be6f1c71c4397b081a from pass to RETRACTION. $0.0224.
3. a2: 0d/0d2c0bbb3d38506a262d99eb0838e544a331f773827c870f2a0b2b4ecd12c97c.json, 2026-11-13T14:01:45Z
   (ledger_20261113_135746). The same clips-alone prompt was asked at 13:36:04Z
   (43/439b61825bd6cdb5cfd0e3e0f161dcb8a21555dbf88b44df107558edea0aabd2.json, seed 8) and 13:36:37Z
   (5e/5e1a2aba57c32dea843d83ee44d463428169d94b52602ed29e9bcaa9ced2413e.json, seed 28) in ledger_20261113_132702.
   Third ask, seed 18; all three fail. $0.0093.
   (a3, for completeness: 5b/5b5a318087e96771909519b38ef19f9c4baf8e767e4a0aa7c40f3bcfd4fb424a.json,
   2026-11-13T12:46:42Z: deepseek answered the angle prompt grok had answered at 12:36:10Z,
   04/042bd3741c63379e296c6fae59dc6c448f121a680dd78b43d87bcb83cf7579d9.json, after deepseek and qwen missed the 300 s
   deadline in the build before.)

Closed by today's code:
- a1: the step-A cache every build shares (ruling 58): key = moment id + text sha + context sha + STEP_A_VERSION,
  reused when its verdict is off the writers (pipeline/package.py:512-537), stored after each batch (:569), file
  tests/package/proof/STEP_A_CACHE.json. Of the 243 excerpts: 185 were in builds before the cache existed (each
  build kept step A only in its own step_a.json, tests/package/proof_ledger.py:191); 45 were the one-time refill of
  the empty cache in ledger_20261113_163106; 13 were first post-cache encounters of moments last screened before it
  (ledger_20261113_172217, 210211). None after 2026-11-13T21:07Z. All 243 re-asks were of excerpts asked in an
  earlier build.
- a2 inside one build (2 of 3: 7d/7d3a8d27dc62074ef48c81652d876cc09bc7db98db233f79d502a6ed5ae1f8a0.json 11:23:30Z
  and 5e/5e1a2aba…json 13:36:37Z): the per-build `judged` map serves an identical line-up's verdict free
  (pipeline/package.py:2612, 2664-2672; commit 680dfb7a, 12:22 ET).
- Hook ratings: asked once per moment and cached (pipeline/package.py:696-705, 737; HOOK_CACHE.json). 0 re-asks
  since the cut; ledger_20261114_021501 rated 7 hooks with no call.

Still open:
- a2 across builds: `judged` dies with the build, and the verdict's seed is the line-up's place
  (`seed=7 + n_lineup + 10 * ai`, pipeline/package.py:2669), so the same line-up at another place in a later build
  is paid again. Closes with: a clips-alone verdict cache shared by builds, keyed by the ordered moment ids, their
  text sha and the MEDLEY_PROMPT version (as HOOK_CACHE is), read before `medley()` at pipeline/package.py:2664.
- a3: `Router.call` serves a recording only for the back-end it is trying (pipeline/providers.py:877-882), so a
  recorded answer from a later chain member is ignored when an earlier one is asked live. Closes with: look up every
  unskipped chain member's recording before any live call (note: the writer's vendor then follows the recording).
- d1 (deliberate, open by design): of the 51 date re-asks, 5 newly failed on STALE_TIME (the purpose of the key), 26
  passed again, 13 failed again, 5 turned a failed moment into a pass on rules unrelated to time (REFERENT_OUTSIDE,
  NOT_OWN_SINCERE), 2 newly failed on unrelated rules. Flagged, not changed: the show date is the UTC date (`ctx.now`
  is UTC, tests/package/proof_ledger.py:107; pipeline/package.py:524), so the pool is re-screened at 19:00 ET, not at
  midnight ET. If it is to be closed: re-ask on a new show date only moments whose words carry a time word
  (`time_sensitive`, pipeline/package.py:202-207) and carry every other verdict, failures included.

## (b) Clips-alone or coherence verdicts on a line-up holding a moment already known to fail

81 line-up verdicts since the cut (77 clips-alone, 4 coherence-with-takeaway). By the definition given, **74 of them
($0.5884)** held such a moment before the call. A call can fall in several sub-classes:

| sub-class | calls | $ reported | today |
|---|---|---|---|
| b1 a clip's step A had failed before the call | 43 | 0.3474 | 38 calls ($0.3108): failed on the identical excerpt, later re-asked to a pass: closed for the same key (ruling 58). 5 calls ($0.0366): failed for the previous UTC show date, passed on the new one: open |
| b2 the hook had been rated below 4 (as the hook, inside an earlier clips-alone verdict) | 14 (13 from an earlier build, 1 from the same build) | 0.1335 | closed (rulings 59 / 61); the last one was 2026-11-13T15:36:41Z |
| b3 a clip rated below 4 in an earlier build's clips-alone verdict | 60 | 0.5069 | open, and not reliable evidence (below) |
| b3x the same ordered line-up failed in an earlier build | 3 | 0.0284 | 1 open (the a2 case); 2 had a changed question |

Every b2 call is also a b1 call: b1, b2 and b3x together are 43 calls, $0.3474. 31 calls ($0.2411) are b3 only.

Read before closing b1 or b3: the data shows these failures do not repeat reliably.
- Step A on an identical input flips. Across all recorded step-A answers, 48 of the 159 (excerpt, model) pairs asked
  two or more times got both a pass and a fail. c3be6f1c71c4397b081a: 13 askings of the identical excerpt, 4 fails
  (grok RETRACTION twice and REFERENT_OUTSIDE once, deepseek REFERENT_OUTSIDE once).
- A clip's earlier rating below 4 predicted nothing. Of 106 (call, clip) pairs where the clip had been rated below 4
  in an earlier build, 52 were rated below 4 again and 54 were rated 4 or more. 7 of the 60 b3 line-ups passed.
- Both sealed packages hold such clips. ledger_20261113_183302 (pin 61fd55d0, re-sealed 0c68b589):
  a45d26b88cd5b176ae13 (1 failing step A in 14 askings) and c3be6f1c71c4397b081a (4 in 13). ledger_20261113_215708
  (pin 13949b7c): a5f5a1d5d1e5482718f6 (rated 1 in two earlier builds) and c7646b4ee91f955cf58f (rated 1 and 3
  earlier). A rule that never reuses a moment with a failing step A, or with an earlier rating below 4, would have
  blocked both pins.

Examples:
1. b2: 1f/1f241a86108dec165f5517899d7d650e7ad170d9b96d056bea93c432e256c7e6.json, 2026-11-13T11:23:05Z
   (ledger_20261113_111825). Hook fda2c6856295ea156a9d had been rated 3 as the hook at 10:33:19Z
   (e1/e17e8490325137e14ecb9956956c5c04e6b622cdb1a999e5ff3c8e48348cfc93.json, ledger_20261113_102658); rated 3
   again, $0.0058. Its twin 7d/7d3a8d27…json (11:23:30Z) asked the identical prompt once more.
2. b1, identical excerpt: 5b/5b8e746855c450bdf28aee3fadfe7f02f0968d0edb063ebf95d0fe329f5902fa.json,
   2026-11-13T16:46:50Z (ledger_20261113_163106). Clip c3be6f1c71c4397b081a had failed step A (grok, RETRACTION) on
   the identical excerpt at 14:57:11Z (5a/5a2e1e0e3f6e1953aaa1e6562bbaff81c50d936d45bf41c30d0490367dd8de55.json);
   the cache-filling re-ask at 16:33:21Z passed it. This line-up failed (clip_03 rated 2). $0.0110.
3. b1, previous show date (open): 87/87fd3033a0ad409ae02b736c828cd3248baa039d51ada593be68584079cca07a.json,
   2026-11-14T01:25:05Z (ledger_20261114_011253). Clip e05b34a672b73f3334ea failed deepseek step A
   (REFERENT_OUTSIDE) for show date 2026-11-13
   (e9/e9d7562192b50cf38866b76f7a019428b91b47b70cae6e746d87c3d0a24691d2.json, 22:03:24Z). For 2026-11-14 deepseek
   and glm missed the 120 s deadline and qwen passed it
   (e3/e36e17ed2ebf0c2ae39cffa21499343f3177a02baf066cd18a7d6f20d03892a1.json, 01:18:57Z). The line-up passed
   ($0.0085). Retried as ruling 66's candidate in ledger_20261114_021501, it took $0.1062 of writes, fidelity, step B,
   step C, exclusion and coherence before the coherence verdict
   (9e/9e221024271264f6f17b6254609597a85226fc92d35aa9af64031d8ae3237cb0.json, 02:28:17Z) rated that clip 2.
   (A b3 case that passed: 61/6134eb794ebed6dc11edf84c935384449cb4b08be243fe46b57045184d9cd648.json,
   2026-11-13T22:08:31Z, the 215708 package's line-up: a5f5a1d5d1e5482718f6 had been rated 1 at 21:11:00Z,
   f7/f74a3a3ccf01b176d3bc30c6acd8d1bd1e151180d31e29035b2a81ca71d50890.json; rated 4 this time.)

Closed by today's code:
- b2: the hook's own-job rating is asked once per moment and cached (pipeline/package.py:685-739); only a hook rated
  4 or more may open (:1215-1227); a build with no such hook stops before any line-up (:2344-2351); the clips-alone
  verdict no longer rates the hook (ruling 61, :1516, 1537-1541).
- b1 on the same key: one verdict per moment, context and model (ruling 58), so a moment can no longer fail in one
  build and pass in the next on the same input.

Still open:
- b1 on a new show date or a new answering model (the 5 calls): the date in the cache key (pipeline/package.py:
  522-525) and the second-vendor failover chain (:75-76, :591-593; pipeline/context_integrity.py:336-354) give a
  failed moment a fresh draw. Closes with: a failing step-A verdict sticks to the moment's text across show dates and
  models unless its only failure is STALE_TIME (by the flip data above, this would also have blocked pin
  61fd55d0 / 0c68b589).
- b3x across builds: the shared clips-alone cache of a2.
- b3: the per-build `dropped` and `bad_pairs` (pipeline/package.py:2463, 2612, 2615) are not kept across builds. No
  closing rule is recommended from this data: the earlier rating is a coin flip and both pins hold such clips.

## (c) Writes that ended in the same refusal as an earlier write for the same line-up and line

- Paid: **0**. The 13 paid writes since the cut (12 full writes, 1 caption-alone write; $0.0417) were matched to the
  build records' attempts by their text. None repeated an earlier (line-up, line, rule) refusal.
- Served free from recordings and refused the same way: **4**, all in ledger_20261113_212949 (16:30 ET). The two
  writes recorded for line-up 82473bb0964f115fbdda + afe8101ad97672f4a9ad + 9c14612153405f8983e4 in
  ledger_20261113_210211, 5d/5d9751c05ed29279c7f48dfde0ee4804f72cea2eb1f213cc30275d3a9dedff84.json
  (2026-11-13T21:16:43Z, takeaway COMMENTARY) and ba/ba159e27110bd3790141df811d26a40e4e0469f3d4533af0ad72289a0e8be93b.json
  (21:24:38Z, clip_02 STRONGER), were each served twice: once as ruling 66's candidate try (package.log lines
  15-20), once when the search re-formed the same line-up (lines 36-40). $0.
- One paid near-repeat (same line, same fact check, another rule label):
  04/043257db81b47d101625a9908d05874e62f3320423db1678eeb982cc6e6fc4f2.json, 2026-11-13T17:40:06Z: caption
  VERDICT_UNCERTAIN, after 26/2698064b1b318f653901136755ac61fa5cb7d19a25761e1e719698aaedbcd8c1.json (17:36:21Z) was
  refused VERDICT_NO for the same line-up (ledger_20261113_172217). $0.0008.

Closed by today's code: the search never re-forms a registered line-up; it is recorded "registered", neither judged
nor written (pipeline/package.py:2649-2657; commit 2f145afa, 16:56 ET). ledger_20261114_021501 shows it twice
(package.log lines 38 and 43). A refused caption gets one caption-alone write, then the code-written caption (ruling
65, pipeline/package.py:1813-1883, 2916-2932); a refused title or takeaway gets at most LINE_ONLY_WRITES = 2 more
writes (:1678, :1833-1834, :2766-2796).

Still open ($0): a line-up whose writes failed in the very build that found it is seeded "open"
(pipeline/candidates.py:72-80), so its first registry retry replays those recorded writes to the same refusal (free)
before it rests 6 h. Closes with: seed such a line-up as "resting" in `candidates.seed`.

## Outside the three classes (bought nothing; for the record)

- Calls abandoned at a deadline: 21 since the cut in docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.jsonl (7
  writer calls in ledger_20261113_082157, 092234, 104817, 121442; 14 second-vendor step-A calls in
  ledger_20261114_011253 and 021501). Booked at upper bounds before ruling 83: $4.6683 (082157 $0.5048, 092234
  $0.2574, 104817 $0.5036, 121442 $0.5022, 011253 $2.9003); these are bookings, not vendor charges. In 021501, $0.0646
  booked at prompt tokens, replaced by $0.0042 vendor-reported for the 3 late answers. A late answer's text is dropped
  unrecorded (pipeline/providers.py:262-293, 761-791), so it is never served later.
- Out-of-contract replies: deleted on rejection. Unrecorded spend of $0.0148 (meter basis) in 134638, 145246, 163106,
  180515 and 002300 (134638: both angle replies out of contract, "no readable angles").
- Writes paid before a gate that could run first: 2 grok writes ($0.0341;
  a9/a96d05786616645677a0fe0fa6ef36c98c2bb90d6e749b9c237570e4be1abd0a.json 09:38:27Z,
  51/516896334e254f42f8d94a4c22e4ceb52e54c9d047c660abfc053151d1774df4.json 11:09:05Z) were thrown away when step A
  was re-screened off the writer's vendor. Closed by order 06:22 item 45 (the second screen before any angle,
  pipeline/package.py:2352-2363). 1 write (d9/d9650f7cd11273fb7f200cbf4317f2f1d30ca392820ddb85b70a5f5ff4970400.json,
  08:46:40Z, $0.0005) was thrown away because the hook's exclusion verdict, run in parallel, excluded it. Still open:
  the exclusion is awaited only after the write (submitted at pipeline/package.py:2729-2730, read at :2876).
- Transcription: 1 window transcribed again from different audio bytes with the same text, $0.0045 estimate.

## Summary table

| class | calls | $ reported | $ estimated | closed by today's code? | what closes the rest |
|---|---|---|---|---|---|
| (a) step A, identical excerpt, same model | 51 calls / 243 excerpts (14 in full) | 0.7274 | 0 | yes: ruling 58 cache (pipeline/package.py:512-537, 569) | nothing left |
| (a) clips-alone, identical prompt, new seed | 3 | 0.0269 | 0 | 2 yes (in-build `judged`, :2664-2672); 1 no | a shared clips-alone cache keyed by ordered ids + text sha + MEDLEY_PROMPT version |
| (a) angle prompt asked of another writer | 2 | 0.0034 | 0 | no | Router serves any unskipped chain member's recording before a live call (providers.py:877-882) |
| (a, deliberate) step A for a new UTC show date | 10 calls / 51 excerpts | 0.1500 | 0 | by design (:522-525) | if wanted: re-ask only time-sensitive moments on a new date |
| (b) line-up verdicts holding a known failure, as defined | 74 | 0.5884 | 0 | partly (below) | |
| (b) of which b2, hook rated below 4 before | 14 | 0.1335 | 0 | yes: rulings 59 / 61 (:685-739, :1215-1227, :2344-2351) | nothing left |
| (b) of which b1, step A failed before | 43 | 0.3474 | 0 | 38 yes for the same key (ruling 58); 5 no | failing verdict sticky across show dates and models unless only STALE_TIME (would have blocked pin 61fd55d0 / 0c68b589) |
| (b) of which b3x, same line-up failed in an earlier build | 3 | 0.0284 | 0 | 1 no; 2 had a new question | the shared clips-alone cache |
| (b) of which b3, a clip rated below 4 in an earlier build | 60 | 0.5069 | 0 | no | none recommended: 52 of 106 repeat; both pins hold such clips |
| (c) writes replayed to the same refusal | 0 paid (4 free replays) | 0 | 0 | yes: never re-formed (:2649-2657) | seed a line-up whose writes failed in its finding build as "resting" (candidates.py:72-80) |
| (c) near-repeat, same line, same check | 1 | 0.0008 | 0 | yes: ruling 65 (:1813-1883, :2916-2932) | nothing left |
