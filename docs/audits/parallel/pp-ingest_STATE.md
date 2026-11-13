# pp-ingest: STATE (session pipeline_pp_ingest, branch pp-ingest, worktree ~/worktrees/pp-ingest)

## TOTAL SPEND BY VENDOR (this session, every use, to 18:20 ET Nov 13) - paid frontier vendors FROZEN since 05:30 ET Nov 12
| vendor | total | measured part | where it went | since the freeze |
|---|---|---|---|---|
| Anthropic | **$10.44** | all (each call's usage x the $4 / $20 per MTok list price) | the watcher's outage drill 08:36-08:43 UTC Nov 12 $7.17 (the whole of the watcher's Anthropic spend), the A/B generator $3.11, the smoke $0.13, a one-window proof $0.03 | $0.00 (0 calls) |
| Google | **~$0.79** | none: the vendor reports no cost (estimate: usage x the $2 / $12 list price) | audit reviews c1 + c2 ~$0.74, a one-window proof ~$0.05 | $0.00 |
| xAI | **$0.65** | $0.54 (the vendor's own `cost_in_usd_ticks`) | the A/B blind judge $0.45 (recorded at the time as $3.22 from the price-table estimate: INGEST-FAIL-11), audit c2 $0.09, audit c1 ~$0.09 and a one-window proof ~$0.02 (estimates: usage not saved) | $0.00 |
| OpenAI | **~$0.35** | none: estimate (usage x gpt-4o's $2.50 / $10 list price) | audit reviews c1 + c2 | $0.00 |
| Heimdall | **$0.97** | $0.84 (`usage.cost` of every reply) + at most $0.13 unrecorded (empty / timed-out audit replies whose usage was not saved) | the watcher $0.37 (mining since 03:26 ET Nov 12: $0.10 before the freeze, $0.27 after), ruling 40 $0.23 (the flag check $0.05, option A's dry run $0.18), the audits $0.11, the A/B $0.08, the smoke $0.05, the freeze drill $0.0006 | $0.63: mining $0.27 (432 calls), ruling 40 $0.23, the freeze audit $0.08 + at most $0.05 unrecorded |
| **TOTAL** | **~$13.20** | | Anthropic is 79 % of it, and 69 % of Anthropic was one outage drill | frontier $0.00 |
- Evidence: docs/audits/parallel/pp-ingest_audit/spend_by_vendor_20261113.json (tests/ingest/spend_by_vendor.py: every
  row with its basis). Live, the watcher's own share: data/editorial/ingest/live.json `usd_all_time_by_vendor`.
- Heimdall account (shared by the fleet's keys): /credits total_usage 34.58 at 07:22 ET Nov 12 -> 37.05 at 18:12 ET
  Nov 13 (+$2.47, the fleet's other sessions included); the cap's sweep spend $36.85 of $460 (8.0 %), meter ok, no
  tripwire. Ruling 77 spent nothing on models (no model call).

## RULING 40: LABEL PRECISION OF THE HARD FLAGS (measured 03:25-05:25 ET Nov 13; commit a462afda; report docs/audits/parallel/pp-ingest_FLAG_PRECISION.md)
Second model z-ai/glm-5.3-flash (Heimdall, default reasoning; 24/24 on the calibration quotes), one narrow question per
flag with the ruling's definition, the 200 newest of the 225 flagged rows published in the 72 h before 04:18 ET.

| flag | miner flagged -> checker yes / no (unsure 0, unmeasured 0) | precision (95 % CI) | miner not flagged -> checker yes / no |
|---|---|---|---|
| imperative | 41 / 15 of 56 | **73 %** (60-83 %) | 1 / 143 |
| accusation | 68 / 62 of 130 | **52 %** (44-61 %) | 2 / 68 |
| single_source_breaking | 20 / 10 of 30 | **67 %** (49-81 %) | 64 / 106 |

Five examples per cell: the report's last section. Proposal awaiting the ruling (nothing cleared): P1 "flag stands only
when both models agree" for imperative and single_source_breaking (24 h hard-flag removals 123 -> 116); P2 accusation
re-measured under a sharpened definition first (the checker's "no" released insinuations against identifiable
parties); P3 the tighter miner prompt is not the fix (measured: no precision gain). Rulings 76 + 77 now expire every
moment 12 h after publish, which removes most of what P1 would have released (the released rows were up to 72 h old).

## LIVE STATE (newest first; ET)

- 18:45 Nov 13 RULING 77 (18:09; with the builder's ruling 76; PBX 18:01 "delete all the contents after like 6 to 12
  hours so that we never reuse any of it"): BUILT, TESTED, LIVE IN THE WATCHER. (commit: see git log, pushed)
  - 1 EXPIRY IN THE LEDGER: every new row carries `expires_at` = its video's publish time + 12 h (written at mining;
    rows are never rewritten). The adapter (`best_unused_moments`: the builder's and the word-pass worker's only read)
    refuses a moment whose expiry has passed BEFORE any other rule ("expired (rulings 76 + 77 ...)"), using the
    EARLIER of the field and publish + 12 h, so the 2,000+ rows mined before the field expire the same way and a
    later field never extends a life (fail closed). Expired rows stay in the ledger file (A18). The adapter's horizon
    default is 12 h. On the live ledger at 18:24 (rows mined in 24 h or published in 12 h): 172 refused as expired,
    304 returned, every one under 12 h old; new rows carry the field from the next video mined.
  - 2 DELETE THE CONTENT (pipeline/ingest/purge.py, scope pipeline/ingest/purge.json): media files of videos
    published more than 12 h ago, from three targets only: the runs' acquired sections (`runs/*/sources/`), the lock
    precheck's (`data/lock_precheck/work/*/sources/`), and a dead word-pass cycle's temporary audio / window WAVs
    (`/tmp/word_pass_*` untouched 12 h). KEPT always: a delivered video's media wherever it lies (A19), a file whose
    publish time is unmeasured, a run touched in the last 2 h (a render in progress), a file a process holds open, a
    symlink, and every non-media file (transcripts, PROVENANCE.json, transcript hashes, the pins). A delivered set or
    /proc that cannot be read deletes nothing that pass (L-j). DELIVERED = a video cut into a delivery: 10 runs (2
    Telegram deliveries, 3 review drops, 5 runs of pins the stand-alone scorer records as delivered: 1b4a63d0,
    41f29b1f, 37c5b5f5) and 4 references with delivery evidence (not references/editorial_failures nor the test pins):
    15 videos.
    DRY RUN on the real tree (18:15): would free 0.09 GB, 6 files: the sources of three never-delivered runs
    (pinned_20261112_064032, pinned_20261113_075638, recut_sources_20261111b; videos 25-105 h old). FIRST REAL PASS
    (the watcher, 18:23 ET, restarted on this code): DELETED EXACTLY THOSE 6 FILES, 91.8 MB (each a line in
    data/editorial/ingest/purge/deleted.jsonl; checked gone), nothing else; 0.86 s. KEPT: 154 files,
    7.27 GB, every one a copy of one of the 15 delivered videos (118 of them, 6.84 GB, in runs that are not deliveries:
    re-renders and replays; A19); 51 symlinks to segment_v2/sources (the v2f reference's sources); 1 unnamed file; 1
    run in use; 1 file not yet expired.
    NEVER DELETED, MEASURED for your ruling (not in ruling 77's list; deletion cannot be undone; A20): renders'
    intermediates and QA cuts (runs/*/qa, VERIFY) 2,017 files 5.03 GB; rendered videos (runs/*/out) 64 files 1.01 GB;
    video_pipeline_v3 clip_engine's daily raw + branded clips (06:00 cron) 48 files 0.71 GB; the earlier segment
    pipelines (segment_v1-v3) 718 files 20.76 GB; the March video_engine clips and audio 48 files 0.39 GB. Each is one
    line of purge.json away from a target, on your word.
  - 3 RECURRING, NO CRON: the purge is a loop of the watcher process (`purge`, every 600 s, first pass at start): a
    file is deleted at most ~10 min after its video turns 12 h old (later only while its run is in use or the file is
    open). Every deletion is a line in data/editorial/ingest/purge/deleted.jsonl, every pass one in passes.jsonl; the
    last pass and the total freed are in live.json (`purge`). `python3 tools/ingest_watch.py purge [--measure]` shows a
    pass's plan without deleting (`--apply` deletes).
  - 4 MINING ORDER: newest uploads first, always (already so: the queue serves the caption fetch and the mining by
    publish time, newest first; 3 videos mine at once). Videos older than 12 h are still mined, last: their rows are
    the receipts the ruling keeps, about $0.001 each (A21). The word-pass worker's tiers (last 6 h, then 6-12 h,
    nothing older) are the integrator's: REQUESTS R11. The adapter it reads already returns nothing older than 12 h.
  - AUDIT: cycle 1 running on Heimdall-served reviewers (qwen, glm, muse; frozen vendors skipped), package
    pp-ingest_audit/r77/ (CONTEXT.md: the ruling verbatim and four questions on what the purge could wrongly delete).
  - TESTS: tests/ingest 204 passed (new: tests/ingest/test_purge.py 9; expiry 3 in test_ledger_coverage / test_mine;
    the purge loop 1 in test_service). py_compile clean.
  - LIVE (18:20 ET; 24 h): 129 videos mined, 0 partial, 0 waiting on an outage; 613 moments; publish -> mined p50 16.1
    min, p90 47.5; Heimdall $0.13 in 24 h.

- 05:35 Nov 13 RULING 40 (03:13): HARD-FLAG PRECISION MEASURED; FIX PROPOSED; WAITING FOR YOUR RULING. No flag
  cleared, no ledger line written, the adapter's exclusions untouched, the watcher still mines with mine/2.
  (commit: see git log, pushed) Report: docs/audits/parallel/pp-ingest_FLAG_PRECISION.md (confusion tables, 5
  examples per cell, option A dry run, option B simulation, proposal, spend); evidence pp-ingest_audit/flagcheck_20261113/.
  - SAMPLE: the 200 newest of the 225 rows flagged imperative / accusation / single_source_breaking and published in
    the last 72 h (A13); every row of the builder's 24 h funnel is inside (the adapter's own read reproduces it: 685
    rows, 123 removed by hard flags, imperative 28, alone 21).
  - SECOND MODEL: z-ai/glm-5.3-flash on Heimdall, default reasoning (role `flagcheck` in providers.json: glm then
    muse-spark-open; never a model that mined the row's video). Calibrated first on 24 quotes with a clear answer:
    24/24 (at reasoning effort none it scored 21/24, all misses false "yes": INGEST-FAIL-15). One narrow question per
    flag, your definition in the prompt verbatim, all three asked of every row (A14); strict JSON, a "yes" quotes the
    words (law L-l). 581 answers from glm, 19 from muse, 0 unmeasured.
  - CONFUSION (the miner's flag -> the checker): imperative 41 yes / 15 no = precision 73 % (95 % CI 60-83 %);
    accusation 68 / 62 = 52 % (44-61 %); single_source_breaking 20 / 10 = 67 % (49-81 %). Rows the miner did not
    give the flag (flagged with another of the three): imperative 1 yes / 143 no, accusation 2 / 68,
    single_source_breaking 64 / 106 (your definition is broader than the miner's: all 64 carry accusation or
    imperative, so they are excluded anyway). Agreement with a calibrated model, not ground truth: the checker is a
    little lenient on imperative ("I'm very excited to buy these dips": yes) and literal on accusation (below).
  - WHERE THE WRONG LABELS COME FROM: imperative: predictions, the speaker's own trades, "ignore / listen / look", your
    stablecoin line (checker: no). Accusation: any negative mention of a named party (a hack's victim, earnings,
    market talk, criticism with no wrongdoing). single_source_breaking: attributed claims, history, speculation. Not
    the union of overlapping windows (4 of 200 rows seen twice); both miners (qwen 79 / 53 / 62 %, Opus during the
    outage drill 38 / 46 / 83 %, small samples).
  - OPTION A (your definitions in the miner's prompt), DRY RUN on the same 123 windows, same model, against a control
    re-run of mine/2 (prompts rebuilt to the recorded hashes, 101 of 101): on the 119 rows both arms returned,
    imperative precision 87 -> 89 %, accusation 60 -> 59 %, single_source_breaking flags 18 -> 26 (61 -> 73 %); the
    control moved 1-4 labels per flag. A does not fix precision; it changes which ranges become moments.
  - OPTION B (a flag stands only when both models agree; unsure / unmeasured keep it), SIMULATED with the adapter's
    own read on a copy of the ledger: the 24 h funnel's hard-flag removals 123 -> 84, +25 rows to the packager
    (72 h: 311 -> 237, +52). BUT about 10 of the 52 are insinuations against identifiable parties (7 from one channel:
    CZ / Binance "manipulating" the market; nepotism; a registered partner's chairman called a gambler): the checker
    reads "alleges" literally and "identifiable" as named-in-the-quote.
  - PROPOSAL (your ruling): P1 option B now for imperative and single_source_breaking only (simulated: 24 h removals
    123 -> 116, +4 rows; 72 h +9; all 9 clean on my reading); P2 accusation NOT yet: sharpen its definition
    (insinuation; identifiable from the clip, its title or its channel; criticism alleges no wrongdoing), re-measure
    the same 130 questions (~$0.01, ~30 min), then rule; P3 option A is not the fix. Details and the implementation
    plan in the report. Also seen: a partner_attack recall gap (the gambler clip was flagged accusation only).
  - SPEND (ruling 40): $0.226, Heimdall only: the check $0.044 (757 calls over three runs; the first two were stopped
    for slowness and their answers reused from the cache), choosing the checker $0.004, smokes $0.002, option A's dry
    run $0.177 (253 qwen calls). Frontier vendors: not called (freeze).
  - NEW: pipeline/ingest/flagcheck.py + `tools/ingest_watch.py flagcheck`; providers.json back-ends
    heimdall_glm53flash / heimdall_muse and role `flagcheck` (the `mine` and `judge` chains unchanged; the running
    watcher does not use them); mine.prompt takes an optional template (the service never passes one);
    tests/ingest/dryrun_definitions.py; the spend tool counts the check. Tests: tests/ingest 191 passed (py_compile clean).
  - FINDING (not changed; K2): the reply-cache key (providers.Router._key) holds the back-end, model, prompt, schema
    and max_tokens but not `extra_body` (the reasoning setting): after a back-end's reasoning setting changes, its
    old replies would be reused as if new. I cleared this check's cache by hand when glm's setting changed. Adding
    `extra_body` to the key would invalidate the stored replies the A/B re-reads for frozen vendors, so it is the
    integrator's call (REQUESTS R10).
  - LIVE (05:30 ET; 24 h): 132 videos mined, 0 partial, 0 waiting on an outage; 782 moments (5.9 / video); publish ->
    mined p50 18.3 min, p90 31.7 (n = 129); Heimdall error rate 3.9 % (10 replies with a reason over 160 characters,
    each asked again and answered); $0.17 in 24 h.

- 07:25 Nov 12 FREEZE CHANGE AUDITED (2 cycles) AND LIVE. Nothing blocked. (commit: see git log, pushed)
  - WATCHER restarted 07:22 on this code: mine chain heimdall_qwen27b -> local_gemma (callable: Heimdall only),
    spend freeze openai / anthropic / xai / google, and the start line `WARNING: 1 callable mine back-end(s): when it
    is down the videos wait in the queue ... nothing is dropped`. Frontier calls since 05:30: 0. Heimdall since 05:30:
    8 calls, 8 ok, $0.0047 (a BTC Sessions upload: 20 moments from 8 windows in 23 s).
  - AUDIT of the change under the freeze (A11): OpenAI / xAI / Google skipped; four model families served by Heimdall:
    qwen3.8-27b, glm-5.3-flash, muse-spark-open-816b (minimax-m3.1-flash empty twice: its reasoning ignores effort none).
    Cycle 2 verdicts: all three "Yes, with conditions", no P0 (glm: "the orchestrator's 05:30 order is implemented
    exactly ... 'nothing is dropped' ... is now true and tested"). Fixed from the two cycles (each with a test):
    mined.at stamped under the append lock (the ledger in mined.at order by construction), the `calls` indexes, the
    outage count in SQL, a partial video's later passes append what they mine and its count is the ledger's, caption
    downloads respect the yt-dlp breaker, a stop in a fetch never strands a video, `load_config` enforces two
    back-ends per role, an interrupt is not a back-end failure, the local model released after 2 min idle and never
    under a request, its stored replies reusable without the lease, an unmeasured coverage report retried hourly, an
    outage over 30 min noticed at the top of STATE ("MINING WAITING ON AN OUTAGE ..."), windows of huge sentences no
    longer re-sent 3x (0 of 1,208 existing windows change), the better-ranked observation's scores kept. Refutations
    with evidence: pp-ingest_audit/freeze/C1_CONSENSUS.md, C2_CONSENSUS.md.
  - A CONDITION from the audit (glm), recorded here: while the freeze lasts the `judge` role has no callable back-end,
    so the NEXT A/B's quality dimension is UNMEASURED unless the integrator configures a judge of an unfrozen model
    family (REQUESTS R9; glm-5.3-flash and muse-spark-open each reviewed a 100k-token package coherently at effort none).
  - TESTS: tests/ingest 166 passed (py_compile clean).
  - LIVE NUMBERS (07:23 ET; 24 h window since the watcher's start 03:26): 18 new uploads discovered (4.6 / h) + the
    72 h backfill; 121 videos mined, 0 partial, 0 waiting on an outage; 1,310 moments (10.8 / video); publish -> mined
    p50 21.4 min, p90 25.3 (n = 12; discovered -> mined p50 0.4 min); Heimdall error rate 0.6 % outside the 08:36 drill
    (1 invalid in 164 calls); dollars in 24 h: Heimdall $0.11, Anthropic $7.17 (all the 08:36 drill, before the freeze).

- 06:25 Nov 12 SPEND FREEZE IN FORCE + INTEGRATOR B1-B4 ANSWERED. Nothing blocked. (commit: see git log, pushed)
  - FREEZE (orchestrator 05:30): frontier back-ends out of the running watcher at 05:33 (config + restart; no frontier
    call had happened since 08:43 UTC); the durable form since 06:05 (restart on the new code): providers.json
    `spend_freeze` = openai, anthropic, xai, google (A10); every back-end names its vendor; a frozen vendor is never
    called by any role (Router.available and _try refuse; chain, `only`, `enabled` cannot override; its stored replies
    cost nothing and may be re-read). Mine chain = heimdall_qwen27b -> local_gemma; callable now: Heimdall only (no
    GPU0 lease here). Both down = the videos queue and are mined later. The watcher's start line:
    `mine chain ['heimdall_qwen27b', 'local_gemma'] (callable now: ['heimdall_qwen27b']), spend freeze ['anthropic',
    'google', 'openai', 'xai']`.
  - FREEZE DRILL (real components, scratch store, channel swan_bitcoin, 11:06-11:13 UTC): Heimdall's URL dead for 10
    mining passes (= 100 min of production retries): both videos `mine_waiting` "OUTAGE ... no try used", mine_tries 0,
    24 refused calls ($0), 0 calls to any frozen vendor; URL restored -> the breaker's half-open probe found Heimdall,
    both mined 328 s later (3 calls, $0.00065), nothing lost. docs/audits/parallel/pp-ingest_audit/drill_freeze_20261112.json
  - INTEGRATOR MERGE AUDIT c1 (05:02): the 4 BLOCKING findings FIXED, each reproduced on the old code first
    (pp-ingest_audit/integrator_c1/mustfail_old_753dec1d.json): B1 the 90 % tripwire halted Heimdall (now: notify +
    metered back-ends last, never out); B2 an 80-min outage became permanent silent loss (now: an outage waits with no
    try used, as long as it lasts; only rejected replies count; partial stays retryable and is never counted as mined);
    B3 the env-string lease (now gpu0.held() + main's require/swap_to; the local model released at cycle end); B4 the
    age gate tripped the global YouTube breaker (now terminal per video; calm() on every non-limit answer). All 20
    non-blocking items fixed or answered with evidence: docs/audits/parallel/pp-ingest_INTEGRATOR_ANSWERS.md.
  - TESTS: tests/ingest 147 passed (was 123): must-fail tests for B1-B4, the freeze, redaction, the refused redirect,
    the override allow-list, the store lock, the flag union, append validation, the torn tail, fail-closed adapter
    defaults, the vendor-name guard on code.
  - COVERAGE (automatic, 06:00 ET; old rules, no partial videos): 70 long-form partner videos in 24 h, 68 mined =
    97.1 %, every channel measured; the 2 not mined: a Bitcoin Magazine VOD without English captions yet, a Bitcoin
    Magazine stream scheduled but not started. data/editorial/ingest/coverage/2026-11-12.md
  - LIVE NUMBERS (06:13 ET; 24 h window, the watcher started 03:26): 10 new uploads discovered (3.6 / h) + the 72 h
    backfill; 116 videos mined, 0 partial, 1,290 moments (11.1 / video); publish -> mined p50 19.0 min, p90 24.8 (n = 7;
    discovered -> mined p50 0.4 min: the delay is YouTube's RSS cache); Heimdall error rate 0.6 % outside the 08:36
    drill (38 % with its 104 deliberate refusals); dollars in 24 h: Heimdall $0.10, Anthropic $7.17 (all the drill).

- 04:06 Nov 12 DONE WHEN MET. Commit 753dec1d (branch pp-ingest, pushed). Nothing blocked.
  - WATCHER RUNNING on 753dec1d: tmux `pipeline_pp_ingest_watch` (worktree; `python3 tools/ingest_watch.py run`;
    log data/editorial/ingest/logs/service.log; live numbers data/editorial/ingest/live.json every minute;
    `python3 tools/ingest_watch.py status`). Store = data/editorial of this worktree (staging; never the main tree).
  - LIVE NUMBERS (window: watcher start 03:26 ET to 04:04 ET, 0.63 h; small sample, refreshed in live.json):
    - videos seen: 7 new uploads discovered (11 / h) + the 72 h backfill of 328 at first listing (481 older uploads
      recorded as seen, 219 Shorts recorded, never mined).
    - publish -> mined (new uploads only): p50 19.3 min, max 24.8 min (n = 4); discovered -> mined p50 0.4 min. The
      delay is YouTube's 15-min RSS cache + the 10-min poll (INGEST-FAIL-07), not processing.
    - moments: 1,290 from 113 mined videos (mean 11.4; 52 videos with >= 1; general-finance uploads are mostly screened
      out before any model call: no Bitcoin term).
    - Heimdall error rate: 0.6 % outside the drill (1 invalid reply in 156 calls, retried); 38 % including the drill's
      104 deliberately refused connections.
    - dollars: since start Heimdall $0.10 (about $0.005 per mined video) and Anthropic $7.17, of which $6.69 was the
      outage drill. Steady state on Heimdall: about $0.35 / day at ~70 long-form partner videos a day.
    - Heimdall spend (the probe's measure, /credits minus the sweep baseline): $34.00 of $460 (7.4 %) at 04:03 ET.
  - COVERAGE (08:51 UTC = 03:51 ET, independent RSS listing of all 64 channels, last 24 h): 117 published, 47 Shorts,
    70 long-form, 65 mined = 92.9 %, every channel measured. The 5 not mined, with reasons: 1 Bitcoin Magazine stream
    VOD with no English captions yet (re-probed; no_captions at 48 h), 1 Bitcoin Magazine scheduled stream not started,
    3 uploads published 8-21 min before the check (inside the RSS-cache discovery window; all three discovered at
    08:54 UTC). Report: data/editorial/ingest/coverage/2026-11-12.md; daily at 06:00 ET inside the watcher.
  - OUTAGE DRILL on the live watcher (dead Heimdall URL via the runtime override, 08:36:28-08:42:17 UTC): Heimdall
    calls refused (104), breaker opened, Anthropic mined every window from 08:36:54; 17 videos mined during the outage,
    0 windows failed, 0 videos lost (every video reached mined / waiting states; none dropped); restored URL seen at the
    half-open probe 08:42:17, Heimdall mining again from 08:42:39. Evidence: queue.sqlite calls / events, service.log.
  - A/B (30 saved-universe videos, same 127 windows, blind judge grok-4.20 = neither generator):
    docs/audits/parallel/pp-ingest_AB_REPORT.md. Near tie on quality (Anthropic 15 / Heimdall 11 / 4 ties; 2.80 vs
    2.77); Heimdall $0.0028 vs $0.10 per video (8 windows), p50 18.8 s vs 5.0 s, 1 vs 0 failed windows; approved-
    preview recall 1/3 vs 2/3. Order in providers.json kept: local (when measured) -> Heimdall -> Anthropic -> xAI.
    LOCAL gemma3:27b: harness and prompts ready; the integrator runs it under the GPU0 lease (REQUESTS R6.4).
  - AUDIT: 2 cycles on the actual diff (gpt-4o, grok-4.20, gemini-3.1-pro, qwen3.8-27b; deepseek returned empty twice):
    no law violation reported; consensus fix = whole-transcript fingerprint (INGEST-FAIL-06); verified single-reviewer
    fixes = Gemini schema, bounded ledger read; refutations with evidence in pp-ingest_audit/C1_CONSENSUS.md and
    C2_CONSENSUS.md (incl. the twice-repeated "Anthropic output_config does not exist": 294 live calls used it).
  - ADAPTER: `pipeline.ingest.ledger.best_unused_moments(path, since, now, delivered_ids, registry, optout,
    store_root)` / `tools/ingest_watch.py moments --since <ISO>`; on the live ledger: 1,290 lines, 0 bad, exclusions
    pre-applied (239 hard flags, 270 altcoin / not Bitcoin, 20 measured speaker changes). Tests: tests/ingest (123).
  - Data fixes in the staging queue (logged as events): first_sight=1 for the 809 first-listing rows (column added
    03:4x ET); text_fp recomputed over the whole transcript (113 rows, 0 collisions).
  - Requests for the integrator: pp-ingest_REQUESTS.md (R1-R7: freeze-proof meta, uploads playlist in scan.py,
    stream dating, TAXONOMY / altcoin field, optout.json format, wiring + local A/B, the 3 h ceiling).

- 03:31 Nov 12 WATCHER RUNNING (tmux pipeline_pp_ingest_watch, worktree, store data/editorial = staging, no GPU).
  Built (uncommitted until the audit): pipeline/ingest/{config,contract,providers,spend,queue,watch,fetch,mine,ledger,
  coverage,stats,service,ab}.py + providers.json, tools/ingest_watch.py, tests/ingest (119 passed, no network).
  - First watch: 64 channels in 4.9 s (RSS answered for all 64 at 03:26; the 02:45 404s were transient), 809 uploads
    entered the last-seen ledger: 481 older than 72 h (recorded, not processed), 216 Shorts (recorded, never mined),
    ~110 inside 72 h being probed / captioned / mined (the backfill).
  - Real smoke (scratch store, Scott Melker): his three daily livestream VODs, frozen as `is_live` in the main store
    since Nov 9-11 (INGEST-FAIL-01), transcribed from captions and mined: 112 moments; 9 carry a measured speaker
    change inside (caption '>>') and are excluded by the adapter.
  - Two prompt / config fixes from live measurement: Heimdall qwen3.8-27b at reasoning effort low returned EMPTY
    content after 101 s (all 4,000 tokens reasoning; INGEST-FAIL-04) -> effort none (20 s, $0.0008 / window); under
    mine/1 it chose 6-8-sentence ranges 17 times -> mine/2 replies "first" + "count" with count an enum 1-5 (guided
    decoding cannot exceed it): 37/37 windows then mined on Heimdall, none fell back.
  - Every back-end proven live on one window: Heimdall qwen 20 s / $0.0008 valid; Anthropic 8.4 s / $0.028 valid;
    xAI 65 s valid; Gemini (gemini-pro-latest -> 3.1-pro-preview) truncated its JSON at 4,000 tokens (thinking counts)
    -> config floor 16,000 for it.
  - A real defect found by the end-to-end test and fixed: the circuit breaker re-opened a recovered back-end on the
    outage's old failures (INGEST-FAIL-05; must-fail tests proven against the old code).
  - IN PROGRESS: A/B Heimdall vs Anthropic on 30 saved-universe videos (tmux pp_ingest_ab, 8 in flight, $25 cap, blind
    judge = xAI, a model that is neither generator). NEXT: outage drill on the live watcher (dead Heimdall URL), audit
    cycles 1 + 2 on the actual diff, commit + push, live numbers here.

- 02:50 Nov 12 IN PROGRESS: read-in done (CONSTITUTION, PIPELINE_LAWS incl. L-n..L-w from the main tree, the bible,
  DoD, REDTEAM ledger, the four strategy reviews + BRIEF, transcript_store / transcript_ingest / scan /
  editorial_select universe, pp-selectid's published moments contract v0 and its eligibility / select_by_id, the
  Heimdall replay v3 report and client, the fleet probe's rate-limit and spend notes, CROSS_LLM_AUDIT_LAW). Orchestrator
  note 02:45 (L-x NO SINGLE MODEL, ULTRON FIRST) received and built into the design. Design written:
  docs/audits/INGEST_DESIGN.md. Three failure patterns recorded (pp-ingest_BIBLE_ADDITIONS.md INGEST-FAIL-01..03).
  Next: pipeline/ingest/ + tests, then live run, outage test, A/B, audit x2, commit. Nothing committed yet. Nothing
  blocked.
  Measured facts so far: YouTube RSS answers 404 for every channel (02:45); the uploads playlist lists streams and
  Shorts; Heimdall /credits total_usage 33.68 (sweep spend 33.48 of the 460 cap = 7.3 %); qwen/qwen3.8-27b answers in
  3.6 s on a tiny call, provider "Consensus Protocol"; regression_test.sh 27 PASS / 0 FAIL / 4 WARN in this worktree
  (after copying the gitignored outro_branded.mp4 + music/*.mp3 from the main tree, read only, never committed).

## ASSUMPTIONS

See docs/audits/INGEST_DESIGN.md section 11 (A1-A6). Added:
- A7 Reading main-tree data read-only: the selector's registry (pipeline/channels.json, identical in this worktree),
  the main transcript store (transcripts of the saved universes for the A/B, hash-checked; the frozen-meta survey),
  the gitignored outro / music assets copied for regression_test.sh (never committed). Nothing is written there.
- A8 The cross-LLM audit uses the repo tool's own review templates through tests/ingest/xllm_audit.py (its run_audit
  writes into the main tree and reads key names the env file does not define); outputs in pp-ingest_audit/.
- A9 The 90 % Heimdall tripwire and an unmeasured spend both notify (top line of this file) and fall back; neither
  halts (orchestrator 02:45). Since 06:05 ET (integrator B1): "fall back" = the metered back-ends go to the end of the
  chain; they are never taken out, so with no other callable back-end Heimdall keeps mining (order 05:30).
- A10 The 05:30 freeze names OpenAI, Anthropic and xAI; Google (Gemini) is frozen too as a paid frontier vendor (the
  order's intent: no paid frontier spend). Models served THROUGH Heimdall (other families on the same gateway) are
  Heimdall spend, not frozen; they are used only as audit reviewers here, never as miners (the order's chain is
  Heimdall qwen then local).
- A11 The cross-LLM audit of the freeze change cannot call the frozen vendors; it runs on Heimdall-served models of
  four families (qwen, glm, muse, minimax), and the integrator's merge audit is the cross-vendor check.
- A12 Spend not measured by its vendor is reported as an estimate with its basis (Google, OpenAI; unsaved usages),
  never as zero (law L-m).
- A13 Ruling 40's "the last 72 h" is by PUBLISH time, the adapter's window (`best_unused_moments` horizon): the
  builder's funnel counts that way (the adapter's own read of this ledger reproduces it: 685 rows in 24 h, 123
  removed by hard flags, imperative on 28, alone on 21). Over the cap of 200, the newest 200 by publish time are
  checked (every row of the builder's 24 h funnel is inside).
- A14 "One narrow question per flag": one call per (row, flag), and every sampled row is asked all three questions,
  so each flag gets a full table (the miner's yes / no by the checker's yes / no / unsure / unmeasured). Its "miner
  no" rows are rows flagged with one of the other two flags: they are not an estimate of what the miner misses.
- A15 The checker sees what the clip would show: the moment's exact text, with its channel, title and date as
  context; never the miner's flags or reason. It may answer "unsure"; "unsure" and "unmeasured" never count as
  agreement or disagreement, and both keep the flag in the option-B simulation (fail closed, L-j).
- A16 The checker's setting is chosen by its score on 24 quotes with a clear answer (glm-5.3-flash at its default
  reasoning 24/24; at effort none 21/24, every miss a false "yes"). A question it timed out on (300 s) or answered
  empty goes to the role's second back-end (muse) without a same-back-end retry, since at temperature 0 a retry
  reasons the same way again; the report says which model answered each question.
- A17 Ruling 77 assigns the purge to this watcher, so it deletes files OUTSIDE this worktree: the only writes pp-ingest
  makes there, limited to the three targets of pipeline/ingest/purge.json (refused at load if a target names a
  protected path: references, tests, the transcript store, the pins, renders' out/qa/VERIFY, voice-over, transcripts).
  Nothing else in the main tree is written (the standing "never edit the main tree" holds for everything else).
- A18 "Marked expired (a field, with the time)": the ledger is append-only (rows never rewritten), so the field is
  `expires_at`, the time the moment expires, written on every row when it is mined; a row is expired from that time
  on. Rows mined before the field: the same time from their publish time. Nothing is deleted from the ledger.
- A19 "EXCEPT the sources of DELIVERED videos": read literally, so every cached copy of a delivered video's media is
  kept, not only the delivery run's own copy (6.84 GB of copies in re-renders and replays). Keeping one copy per
  delivery and deleting the rest is your call (one rule in purge.py).
- A20 "Cached source media and audio ... (downloads, windows' WAVs, acquired mp4 sections)": deleted = the three kinds
  listed (acquired sections, the word pass's window WAVs, the worker's audio downloads). Renders' intermediates, the
  rendered videos, the V3 daily clips, the earlier segment pipelines and the March clips are measured and reported,
  not deleted: not listed, and a deletion cannot be undone.
- A21 "Newest uploads first, always" orders the mining; it does not stop it: videos older than 12 h are mined after
  every newer one, for the receipts.

## HOW TO OPERATE (for the orchestrator)
- status: `cd ~/worktrees/pp-ingest && python3 tools/ingest_watch.py status`
- packager read: `python3 tools/ingest_watch.py moments --since 2026-11-12T00:00:00+00:00 [--delivered ids.txt]`
- coverage now: `python3 tools/ingest_watch.py coverage --hours 24`
- outage drill: write `data/editorial/ingest/overrides.json` = {"heimdall_qwen27b": {"base_url": "http://127.0.0.1:9/api/v1"}};
  remove it to restore (recovery at the breaker's half-open probe, <= 5 min); or, without touching the live watcher:
  `PP_INGEST_STORE=<scratch> PP_INGEST_CHANNELS=<slug> python3 tests/ingest/drill_freeze.py --out <json>`
- spend freeze: `pipeline/ingest/providers.json` `spend_freeze.vendors`; lift = remove the vendor(s), restore the mine
  chain's tail (REQUESTS R6.5), restart. Spend by vendor: `tests/ingest/spend_by_vendor.py --out <json>`; live:
  `status` -> `usd_all_time_by_vendor`
- one service per store: a second `run` / `once` on the same store is refused (`ServiceBusy`)
- stop / start: `tmux send-keys -t pipeline_pp_ingest_watch C-c`; `tmux new-session -d -s pipeline_pp_ingest_watch
  -c ~/worktrees/pp-ingest "python3 tools/ingest_watch.py run"` (restart-safe: the queue recovers, replies are cached)
