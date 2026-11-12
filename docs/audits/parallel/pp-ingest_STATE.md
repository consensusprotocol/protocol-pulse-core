# pp-ingest: STATE (session pipeline_pp_ingest, branch pp-ingest, worktree ~/worktrees/pp-ingest)

## TOTAL SPEND BY VENDOR (this session, every use, to 06:25 ET Nov 12) - paid frontier vendors FROZEN since 05:30 ET
| vendor | total | measured part | where it went | since the freeze |
|---|---|---|---|---|
| Anthropic | **$10.44** | all (each call's usage x the $4 / $20 per MTok list price) | the watcher's outage drill 08:36-08:43 UTC $7.17 (the whole of the watcher's Anthropic spend: $6.21 while Heimdall was dead + $0.97 windows in flight), the A/B generator $3.11, the smoke $0.13, a one-window proof $0.03 | $0.00 (0 calls) |
| Google | **~$0.79** | none: the vendor reports no cost (estimate: usage x the $2 / $12 list price) | audit reviews c1 + c2 ~$0.74, a one-window proof ~$0.05 | $0.00 |
| xAI | **$0.65** | $0.54 (the vendor's own `cost_in_usd_ticks`) | the A/B blind judge $0.45 (recorded at the time as $3.22 from the price-table estimate: INGEST-FAIL-11), audit c2 $0.09, audit c1 ~$0.09 and a one-window proof ~$0.02 (estimates: usage not saved) | $0.00 |
| OpenAI | **~$0.35** | none: estimate (usage x gpt-4o's $2.50 / $10 list price) | audit reviews c1 + c2 | $0.00 |
| Heimdall | **$0.39** | $0.31 (`usage.cost` of every reply) + at most $0.08 unrecorded (2 empty audit replies) | the watcher $0.10, the A/B $0.08, the smoke $0.05, the audits of 01:xx-04:xx and of this change (FREEZE AUDIT below) ~$0.07, the freeze drill $0.0007 | Heimdall mining continues (order) |
| **TOTAL** | **~$12.6** | | Anthropic is 83 % of it, and 69 % of Anthropic was one outage drill | frontier $0.00 |
- Evidence: docs/audits/parallel/pp-ingest_audit/spend_by_vendor_20261112.json (tests/ingest/spend_by_vendor.py: every
  row with its basis). Live, the watcher's own share: data/editorial/ingest/live.json `usd_all_time_by_vendor`.
- Heimdall account (shared by the fleet's keys): /credits total_usage 33.68 at 02:50 ET -> 34.37 at 06:13 ET (+$0.69,
  other sessions included: +$0.13 between 05:33 and 06:05 while this watcher made no call); the cap's sweep spend
  $34.17 of $460 (7.4 %), meter ok, no tripwire.

## LIVE STATE (newest first; ET)

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
  - FREEZE AUDIT of this change: see the entry it adds (Heimdall-served reviewers only; frozen vendors skipped).

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
