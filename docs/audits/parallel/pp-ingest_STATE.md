# pp-ingest: STATE (session pipeline_pp_ingest, branch pp-ingest, worktree ~/worktrees/pp-ingest)

## LIVE STATE (newest first; ET)

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
  halts (orchestrator 02:45).

## HOW TO OPERATE (for the orchestrator)
- status: `cd ~/worktrees/pp-ingest && python3 tools/ingest_watch.py status`
- packager read: `python3 tools/ingest_watch.py moments --since 2026-11-12T00:00:00+00:00 [--delivered ids.txt]`
- coverage now: `python3 tools/ingest_watch.py coverage --hours 24`
- outage drill: write `data/editorial/ingest/overrides.json` = {"heimdall_qwen27b": {"base_url": "http://127.0.0.1:9/api/v1"}};
  remove it to restore (recovery at the breaker's half-open probe, <= 5 min)
- stop / start: `tmux send-keys -t pipeline_pp_ingest_watch C-c`; `tmux new-session -d -s pipeline_pp_ingest_watch
  -c ~/worktrees/pp-ingest "python3 tools/ingest_watch.py run"` (restart-safe: the queue recovers, replies are cached)
