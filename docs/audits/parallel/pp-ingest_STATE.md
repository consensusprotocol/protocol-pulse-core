# pp-ingest: STATE (session pipeline_pp_ingest, branch pp-ingest, worktree ~/worktrees/pp-ingest)

## LIVE STATE (newest first; ET)

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

See docs/audits/INGEST_DESIGN.md section 11 (A1-A6).
