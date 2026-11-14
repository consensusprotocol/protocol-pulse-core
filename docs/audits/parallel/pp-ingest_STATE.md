08:28 ET: F1 FIXED AND LIVE since 08:07 ET (197b35ec, 2 audit cycles): calibration (asked live, 497 s) [('heimdall_glm53flash', 16, 16, 0), ('heimdall_muse', 16, 16, 0)] (right, answered, unanswered); allowed to answer: ['heimdall_glm53flash', 'heimdall_muse']; next calibration in 86400 s; THE 08:15 RULINGS RECEIVED: A32 as built (no change); the hook pass (B) + (C): being built, one audit, then run over the 12 h window and every new upload (rows per video and cost reported here); A19 one copy per delivery: being built, audited, then the disk freed reported here; CYCLES SINCE THE NEWEST LEDGER ROW (04:16 ET) THAT FOUND SOMETHING (newest first; video, channel, mined, moments, hooks, seconds from publish to rows): 08:17 ET cycle, 3 new: (1) 0SieuLwuKEg Swan Bitcoin: a Short, never mined (A2), no rows; (2) nHC9s2csYak Simply Bitcoin: a Short, never mined (A2), no rows; (3) cROYooVLSeY Bloomberg Television: mined yes 08:17 ET, 0 moments, 0 hooks (all 4 window(s) without a Bitcoin term: screened before any model call); 1071 s publish -> mined (seen 1047 s after publish via rss, mined 24 s after) | 08:06 ET cycle, 1 new: (1) NowbrISU73s Bloomberg Television: mined yes 08:06 ET, 0 moments, 0 hooks (all 2 window(s) without a Bitcoin term: screened before any model call); 1197 s publish -> mined (seen 1178 s after publish via rss, mined 19 s after) | 07:26 ET cycle, 2 new: (1) -mXPLiq_zX4 Bitcoin Magazine: a Short, never mined (A2), no rows; (2) 32h8S4ODggc Bloomberg Television: mined yes 07:26 ET, 0 moments, 0 hooks (all 1 window(s) without a Bitcoin term: screened before any model call); 1390 s publish -> mined (seen 1360 s after publish via rss, mined 30 s after) | 07:07 ET cycle, 1 new: (1) Qlt84Qg7IgQ Bloomberg Television: mined no, queued (live_waiting: is_live: re-probed every 20 min (meta.json not written)) | 06:28 ET cycle, 1 new: (1) wtQorzoJFy8 Scott Melker: a Short, never mined (A2), no rows | 06:17 ET cycle, 1 new: (1) vqcziGjEDA8 Simply Bitcoin: a Short, never mined (A2), no rows | 06:07 ET cycle, 2 new: (1) LO50JV239YU Fox Business: mined yes 06:08 ET, 0 moments, 0 hooks (all 2 window(s) without a Bitcoin term: screened before any model call); 471 s publish -> mined (seen 438 s after publish via rss, mined 33 s after); (2) oCLBN6SGSXY Fox Business: mined yes 06:08 ET, 0 moments, 0 hooks (all 5 window(s) without a Bitcoin term: screened before any model call); 462 s publish -> mined (seen 444 s after publish via rss, mined 18 s after) | 05:28 ET cycle, 1 new: (1) ogU99e2dfGo Bloomberg Television: mined yes 05:28 ET, 0 moments, 0 hooks (all 2 window(s) without a Bitcoin term: screened before any model call); 805 s publish -> mined (seen 786 s after publish via rss, mined 19 s after); NO LEDGER ROW SINCE 04:16 ET because every upload since was a Short, had no Bitcoin term in any window, or is still live; the 12 h pool now: 9 moments from 1 video(s) (Stephan Livera 7po5mnYMAjM 9 moments, 2 hooks, to 10:17 ET) | # pp-ingest: STATE (session pipeline_pp_ingest, branch pp-ingest, worktree ~/worktrees/pp-ingest)

## TOTAL SPEND BY VENDOR (this session, every use, to 08:15 ET Nov 14) - paid frontier vendors FROZEN since 05:30 ET Nov 12, except ruling 98's capped paid route (unused so far: $0.00)
| vendor | total | measured part | where it went | since the freeze |
|---|---|---|---|---|
| Anthropic | **$10.44** | all (each call's usage x the $4 / $20 per MTok list price) | the watcher's outage drill 08:36-08:43 UTC Nov 12 $7.17 (the whole of the watcher's Anthropic spend), the A/B generator $3.11, the smoke $0.13, a one-window proof $0.03 | $0.00 (0 calls) |
| Google | **~$0.79** | none: the vendor reports no cost (estimate: usage x the $2 / $12 list price) | audit reviews c1 + c2 ~$0.74, a one-window proof ~$0.05 | $0.00 |
| xAI | **$0.65** | $0.54 (the vendor's own `cost_in_usd_ticks`) | the A/B blind judge $0.45 (recorded at the time as $3.22 from the price-table estimate: INGEST-FAIL-11), audit c2 $0.09, audit c1 ~$0.09 and a one-window proof ~$0.02 (estimates: usage not saved) | $0.00 |
| OpenAI | **~$0.35** | none: estimate (usage x gpt-4o's $2.50 / $10 list price) | audit reviews c1 + c2 | $0.00 |
| Heimdall | **$1.88** | $1.75 (`usage.cost` of every reply) + at most $0.13 unrecorded (empty / timed-out audit replies whose usage was not saved) | the watcher $0.57 (mining, hooks, the second-model check and, since 08:07 ET Nov 14, its live calibration: $0.10 before the freeze, $0.46 after; 1,231 calls), the audits $0.87 (the build's c1 + c2 $0.10, the freeze $0.08, rulings 40 P1 $0.06, 77 $0.05, 80 $0.08, 92 $0.08, 87 $0.12, 87's probe claim $0.10, 98 $0.09, F1 $0.11), ruling 40's measurements $0.25, the A/B $0.08, the smoke $0.05, the freeze drill $0.0006 | $1.50: the watcher $0.46, the audits $0.78, ruling 40 $0.25 + at most $0.05 unrecorded |
| **TOTAL** | **~$14.11** | | Anthropic is 74 % of it, and 69 % of Anthropic was one outage drill | frontier $0.00 (ruling 98's paid route: $0.00 so far) |
- Evidence: docs/audits/parallel/pp-ingest_audit/spend_by_vendor_20261114.json (tests/ingest/spend_by_vendor.py: every
  row with its basis; since e2878d54 it sums EVERY audit directory: the 18:20 ET Nov 13 table left out the audits of
  rulings 40 P1 to 92, which it now carries; the smoke and freeze-drill rows are carried from the 20261113 file, their
  scratch stores being gone). Live, the watcher's own share: data/editorial/ingest/live.json `usd_all_time_by_vendor`.
- Heimdall account (shared by the fleet's keys): /credits total_usage 34.58 at 07:22 ET Nov 12 -> 39.77 at 08:07 ET
  Nov 14 (+$5.19, the fleet's other sessions included); the cap's sweep spend $39.57 of $460 (8.6 %), meter ok, no
  tripwire. Ruling 87's probe runs only while calls fail or in Plan B (3 probe call(s) so far, each at $0.00 recorded).

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

- 08:15 Nov 14 THE ORCHESTRATOR'S 08:15 RULINGS (to pp-ingest): (1) A32: AS BUILT (the paid route takes conversations
  first, then newest: with a $2 cap the money goes to what a spotlight or a medley hook can use). (2) THE HOOK PASS:
  BOTH (B) up to 5 candidates a window in conversation episodes and (C) the 12-35 s spotlight question for them ('one
  speaker's complete claim, number or question that a stranger understands cold and would stop scrolling for'); last
  night's pools had exactly one opener rated 4 in each window: this is where the supply is; audit as one change; run
  it over the current window and every new upload; report rows per video and cost. (3) A19: ONE COPY PER DELIVERY:
  keep the acquired source section(s) the delivered pin's PROVENANCE names, by hash; delete the other cached copies;
  report the disk freed. F1: FIX IT (the daily calibration and the one that gates 'allowed to answer' after an outage
  asked LIVE, the cache bypassed for calibration prompts only; the log line says live or replayed; until fixed, line 1
  says 'calibration replayed from <date>'). ALSO: the 07:26 cycle's 2 uploads explained on line 1, one line each; from
  now on line 1 carries, after each cycle that finds something: video, channel, mined yes/no, moments, hooks, seconds
  from publish to rows.
  - F1 IS LIVE since 08:07 ET (197b35ec; the build 0abeb304; audit c1 2af6c379: glm's crash path and the discarded
    wrong answers fixed; c2 197b35ec: muse's empty calibration and glm's crash count in; $0.115 Heimdall;
    pp-ingest_audit/f1/). The watcher restarted 08:07 ET (pid by `status`; nothing in flight; the signal module
    unchanged since its start). The first live calibration: in progress at 08:15 (its calls so far: glm53flash ok 16,
    muse ok 13, muse server 17; muse's gateway 502s are re-asked); the result goes on line 1. Every calibration quote
    is asked live (the cache bypassed for calibration prompts only; the real questions keep the cache: one row's
    question is asked once); the log line says 'asked live'; nothing in the watcher replays a calibration any more
    (the measurement CLI still reads its stored replies, A35).
  - LINE 1 now lists every cycle since the newest ledger row that found something (video, channel, mined, moments,
    hooks, seconds from publish to rows; seen-after-publish and mined-after-seen split), written by hand from the
    queue until the watcher writes it itself (built after the hook pass, audited). The 07:26 cycle: -mXPLiq_zX4
    Bitcoin Magazine, a Short (never mined); 32h8S4ODggc Bloomberg Television, mined 30 s after it was seen, its one
    window without a Bitcoin term (screened before any model call): 0 rows. Every upload since the newest row (04:16
    ET) was a Short, had no Bitcoin term in any window, or is still live.
  - NOTED for the standing job: Bloomberg Television's uploads were SEEN 786-1,360 s after publish via RSS (Fox
    Business 438-444 s); a cycle runs every 10 min, so the rest is the feed's own lag. To measure: RSS against the
    uploads playlist on the same uploads.
  - NEXT, in order: the hook pass (B) + (C) (one audit, then run over the 12 h window and every new upload; rows per
    video and cost on line 1); the watcher writes the cycle report on line 1 (audited); A19 one copy per delivery
    (audited; the disk freed on line 1). Disk: 431 GB free (76 % used), so A19 is not urgent for space.

- 07:31 Nov 14 FRESH SESSION UP: a new pipeline_pp_ingest session took over from the handoff 3af063d0 (the previous
  one ran out of context). Read PIPELINE_LAWS.md in full, the HANDOFF in full, this file's top. Line 1 was "HANDOFF
  READY 3af063d0 (docs/audits/parallel/pp-ingest_HANDOFF.md)"; it now carries the facts below and the orchestrator's
  three open questions (A32, ruling 92 (b) / (c), A19), each with the built default that stands until answered.
  - THE WATCHER: alive, pid 4164250 (cwd the worktree) in tmux pipeline_pp_ingest_watch, up since 06:46 ET on 13de013b
    (ruling 98 live); not restarted. Last watch cycle 07:26 ET: 64 channels, 2 new, 0 errors, rss 64, 2.8 s. The
    listing reads RSS again since 03:28 ET (uploads playlists before). Queue: captions_pending 1, live_waiting 1,
    mined 381, no_captions 1, probe_retry 2, seen_old 956, short 549, too_long 1, upcoming_waiting 3.
  - THE LEDGER: 3,046 rows (7.97 MB). Newest row 04:16 ET: TFTC ZtnhDQODni8, 36 moments, published (stream start)
    12:44 ET Nov 13. Its queue history: upcoming, live, then post_live re-probed every 20 min (36 times) from 14:12 ET
    Nov 13 to 01:56 ET Nov 14 (YouTube's processing), 'VOD without English captions yet' at 02:16, captions at 04:16
    and mined at once: already past its 12 h, so every row was written expired (the design's receipt, section 12:
    first-said, the dedupe against re-posts) and no hook pass ran (outside 12 h). Nothing broken on this side. No row
    since (the uploads mined after it gave 0 moments: Bloomberg Television x2, Fox Business x2), so 0 rows carry
    miner_route yet (ruling 98's field arrives with the next mined video).
  - THE 12 H POOL (the adapter, the packager's read, at 07:31 ET): 22 moments from 2 videos: Altcoin Daily 13 (hooks
    3) to 07:56 ET, Stephan Livera 9 (hooks 2) to 10:17 ET; 5 hook rows; refused: 288 expired, 1 hard exclusion flag,
    1 altcoin or not about Bitcoin; 1 returned with a flag released by the second model. live.json hooks_12h.hook_rows
    says 1: it sums the queue's LATEST hook pass per video (mine-hook/2), while the ledger also holds the mine-hook/1
    rows of the same videos (written before ruling 92) and the adapter serves them (5 v1 hook rows of the pool's
    videos): the stat under-reports the pool's hooks until the last v1 row expires (10:17 ET). Reporting only; no
    change.
  - FINDING F1, THE FLAG CHECK'S CALIBRATION IS A REPLAY: at the 06:46 start the calibration read glm 16/16, muse
    16/16, but all 32 answers came from the reply cache (the queue's calls since the start: flagcheck cache 32); the
    cached answers were measured glm53flash 20:10-20:12 ET Nov 13; muse 20:11-23:05 ET Nov 13. flagcheck.calibrate()
    calls router.run with the default use_cache=True, so the daily re-calibration (service.CHECK_RECALIBRATE_S, 'once
    a day (and at every start)') replays the same answers forever and never re-measures the models it releases hard
    flags on (ruling 40 P1); the router's own comment: a stored reply 'calls nobody, proves nothing about health'. A
    model changed behind the same gateway name would keep releasing flags on a stale calibration. Fix to follow (the
    calibration asks live; build, test, 2 audit cycles, then live).
  - THE SECOND MODEL, 12 h: 39 rows checked, 8 released, $0.0072. Back-ends, 24 h: qwen 525 calls, 8.6 % errors (40
    invalid, 5 routing); glm 73 calls, 24.7 % errors (15 invalid, 2 timeout, 1 empty); muse 43 calls, 62.8 % errors
    (27 server).
  - SPEND: Heimdall $0.2856 in 24 h (all of it); the meter $39.42 of $460 (8.57 %, ok, read 2026-11-14T12:26:45Z);
    paid frontier $0.00; the paid route closed (the signal says heimdall_first), $0.00 of $2.00 today.
  - THE SIGNAL: heimdall_first; since the start 0 answers and 0 failures noted, 0 probes (no real Heimdall call was
    made: the uploads since were screened out before any model call), switches seen 0.
  - TESTS: tests/ingest 282 passed (34.8 s).

- 06:46 Nov 14 RULING 98 IS LIVE: THE MINER'S PLAN B (orchestrator 06:13 ET Nov 14). Audited 2 cycles
  (pp-ingest_audit/r98/: c1 no P0 after verification, six fixes in; c2 glm "production ready with one condition" and
  muse "ready, with conditions", both in; qwen's "No" listed two fixes already made; $0.092 Heimdall), commits
  230652f0 -> 13de013b; the watcher restarted 06:46 ET; the builder told.
  - WHEN: the shared signal says plan_b AND no Heimdall family has answered for 20 min running (its failure clock;
    PBX: "fails to respond for more than perhaps 10 to 20 minutes"). Back at the signal's back switch (3 good probes).
    A signal not read opens, closes and spends nothing.
  - WHAT: only NEW uploads (published in the last 6 h; conversations first by the caption turn measure, then newest;
    no backfill; no hook pass) are mined on role mine_paid: Grok, then the Gemini key (no other vendor wired: it
    would need a credit probe). The Nov 12 freeze is lifted for this one role only (no other role can reach a frozen
    vendor). CAP $2.00 per ET day across both, counted from each call's recorded cost (xAI's own; Gemini's price-table
    estimate, it reports none); each call holds its priced worst case before it starts, so $2.00 is a ceiling; then
    the videos queue and wait.
  - EVERY ROW carries `miner_route` (the role that mined it: mine | mine_paid | hook). When the signal is back, every
    video the paid route mined that is still inside 12 h is mined again on Heimdall, once; every moment both found
    carries both models' flags. The builder: every clip a build uses is judged again by its own gates whatever mined
    it, so a paid label can cost yield, never integrity.
  - EVERY SWITCH on this file's line 1, IN CAPITALS: "MINER ON THE PAID ROUTE (...)", "MINER OFF THE PAID ROUTE
    (...)", "MINER PAID ROUTE CAP REACHED (...)" (once per ET day), next to the signal's own; the Plan B switch line
    now reads "THE MINER'S PLAN B (RULING 98): NEW UPLOADS ON GROK, THEN GEMINI AFTER 20 MINUTES DOWN, CAPPED".
  - LIVE: `tools/ingest_watch.py status` / live.json `paid_route` (open, why not open, the day's spend, the cap). At
    06:48: closed ("the signal says heimdall_first"), $0.00 of $2.00 today. Not exercised live yet (no outage since):
    tests only (tests/ingest/test_paid_route.py, 11; the suite 282).

- 02:27 Nov 14 RULING 87 IS WIRED: THE WATCHER IS ON THE ONE SHARED HEIMDALL-DOWN SIGNAL (the builder's module,
  pp-selectid pipeline/heimdall_health.py at 125e7381, used through its API only; its state file
  tests/package/proof/HEIMDALL_HEALTH.json in the builder's worktree). Audited 2 cycles (c1: no P0 after
  verification, six fixes in; c2: glm "P0 none, P1 none, production ready with one condition" (in), muse "P0 none in
  this diff"; pp-ingest_audit/r87/, $0.118 Heimdall), commits 31a50fe6 -> 5a3a2ae2; the watcher restarted 02:27 ET.
  The builder was told right after the restart (the contract as built, and REQUESTS R12).
  - NOTED: every real call of the watcher to a Heimdall back-end (mining, hooks, the second-model check). Answered =
    the gateway answered inside the back-end's deadline (a reply, even one the validator rejects); not answered = any
    other outcome of a real call (down, refusing, empty, late, 429, 4xx). Not noted: a stored reply, a missing key, a
    probe call, a non-Heimdall back-end. A back-end under an overrides.json base_url override (the outage drill) is
    noted drill=True (recorded, never counted). One thread calls the module, so its lock never stalls the miner.
  - THE PROBE, while the shared state says one is due (calls failing, or Plan B; every 2 min): "Reply with the
    single word OK." to qwen3.8-27b, then glm-5.3-flash (Heimdall, 60 s each, the first answer ends it; never a
    stored reply; never during a drill). Spend: only while calls fail (none so far).
  - EVERY SWITCH, whoever made it, goes to the start of this file's line 1 (IN CAPITALS with the time ET, who made it
    and the miner's Plan B; newest first, one physical line) and to data/editorial/ingest/down_signal.jsonl.
  - THE MINER'S PLAN B IS UNCHANGED: QUEUE AND WAIT (the 05:30 Nov 12 spend freeze; the orchestrator's question is
    open). Nothing in the signal changes what the miner calls: Heimdall (the local model is disabled), and when
    nothing answers the videos wait in the queue (a line here after 30 min), never dropped.
  - A signal that cannot be read is never taken as up or down: live.json `down_signal.mode` null with the reason at
    once, a "HEIMDALL DOWN SIGNAL NOT READ" line here after 30 min. Operating note (audit c2, muse): for the first
    48 h, `counts.probes_not_made` should stay 0 outside drills and `not_read` null.
  - FIRST READINGS: wired at 02:27 (the calls right after the restart were stored replies: not noted); 02:35 ET the
    first real note (a new upload's mining, every call answered) created the shared state file; at 02:58:
    mode heimdall_first, 4 notes written (an answer is written at most once per 30 s per process), last answer
    2026-11-14T07:49:43Z, no probe (nothing failing), 0 switches. Live: `tools/ingest_watch.py status` /
    live.json `down_signal`.
  - Also fixed on the way (audit c1): a STATE file that exists but cannot be read is never rewritten from nothing by
    a notice writer (before, any read error was taken as an empty file).
  - REQUESTS R12 DONE: the builder's `probe_due` claims the 2-minute slot (pp-selectid 11ed255f: one probe per slot
    fleet-wide; "3 in a row" = 3 slots). Taken up at 02:57 ET (pp-ingest 4f805fcf; audited 2 cycles in
    pp-ingest_audit/r87claim/, no P0/P1/P2, $0.104): this watcher's probes claim as "pp-ingest probe" (live.json
    `probe_claimed_as`); a module whose probe_due takes no `who` is called without one and said once in the log at
    start. The watcher restarted 02:57 ET; the builder told.

- 00:13 Nov 14 THE BUILDER'S RULINGS 90-93 ARE LIVE ON ITS SIDE (8bf5f278 the spotlight, 85c3895f ruling 93: DEC-12d
  per clip, not per channel: has_chyron no longer keeps a channel's clips off screen; each clip is judged on its own
  frames). The watcher was restarted 00:12 ET so the eligibility it records at mining is the builder's current one
  (its modules load at process start; the contract fingerprint 40f1d65a is unchanged, so no ledger line drifts). The
  builder: Bitcoin Magazine's and CNBC's hooks are in play again; its 00:11 build runs on the v2 hook rows (the medley
  first, then the spotlight); the 23:54 build found no spotlight (its snapped spans mostly failed step A on
  REFERENT_OUTSIDE, the nearest rated 2-3 as openers); it recounts caption turns itself (our counts match).

- 23:20 Nov 13 RULING 92: HOOK v2 (mine-hook/2) IS LIVE; the 12 h window re-asked. The builder's 22:13 build showed
  where the 22 conversation hooks stopped: Bitcoin Magazine's 16 at a channel-level layout rule (burned-in chyron, no
  miner change helps); BTC Sessions' 6 at step A's REFERENT_OUTSIDE, openers on 'and' / 'but' / 'so', a second
  recognition, no quiet before the first onset ("the useful change is DIFFERENT rows rather than more"). Ruling 92's
  text (to the builder, relayed verbatim): "... tell pp-ingest that the hook pass should favour conversations for this
  purpose (role_hint stays 'hook')".
  - v2: the hook prompt states the builder's OPENER rule with the builder's own word sets (pronouns, conjunctions,
    reply words; a test compares them with pp-selectid stand_alone.py), "names who or what it is about", "a new
    thought", and "in a conversation, ONE speaker's complete claim, number or question a stranger understands at
    once"; a hook whose first word breaks the rule is never written; every new row carries `episode` (the caption
    turn measure: speaker markers, minutes, turns per minute, unmarked). Audited 2 cycles (no P0 / P1; the '>>' P1
    refuted by measurement; glm's conditions in: the re-run idempotent per question version), commit c66494a0, the
    watcher restarted 23:03.
  - THE RE-RUN (82 mined videos of the window, newest first; $0.044, 92 calls): 19 v2 hook rows: >= 1 turn / min 9
    (BTC Sessions nvEftLDdab4 5; Bitcoin Magazine 2 + 1 + 1), < 1 turn / min 7 (Simply Bitcoin L6H7538ogGs 4, CNBC 1,
    Altcoin Daily 1, Digital Asset News 1), unmarked captions 3 (Yahoo); 40 candidates not written by the OPENER rule
    (pronoun 18, conjunction 14, reply word 8), 9 outside 4-14 s. Simply Bitcoin NtaQGnfWRR8 waits a retry (2 windows;
    its 23 v1 hooks stand). v1 hooks v2 did not find again stay in the ledger (append-only; the builder's OPENER check
    rejects the bad ones). Live: live.json `hooks_12h.rows_by_episode`. The builder was told at each step.
  - NOT BUILT (the orchestrator's choice, on this STATE since 23:10): more hook candidates per window, or a
    spotlight-length (12-35 s) question for conversation episodes.

- 23:10 Nov 13 RULING 92 (orchestrator 22:52, relayed by the builder, NOT RECEIVED HERE DIRECTLY): spotlights (ruling
  90: one 12-35 s moment, >= 4 as a cold opener and >= 4 standing alone) only from a CONVERSATION (two or more
  speakers by the caption turn structure) or a first-hand statement; "the hook pass should favour conversations for
  this purpose; role_hint stays 'hook'". MEASURED here first (the '>>' markers, stored escaped as &gt;&gt; in the
  captions): the live 12 h pool ALREADY holds 22 hook rows from conversation episodes (BTC Sessions nvEftLDdab4 2.51
  turns/min: 6; Bitcoin Magazine 1.18-1.64: 16) against 36 from solo recaps (Simply Bitcoin 0.48 / 0.05: 30; Altcoin
  Daily 0.21: 3; Digital Asset News 0.17: 3) and 4 from news networks; so the conversations' hooks exist and did not
  reach 4 at the builder's judge. QUESTION FOR THE ORCHESTRATOR (asked of the builder too: where did the 22 stop?):
  which miner change, if any? (a) every row carries its episode's turn measure (no model cost); (b) up to 5 hook
  candidates per window (not 3) in conversation and first-hand episodes (+ about $0.0002 a window); (c) for those
  episodes only, a spotlight question per ruling 90 (one 12-35 s cold opener that stands alone, role_hint "hook"; a
  new miner question, about $0.0004 a window). Until ruled, the hook pass stays as ruling 80 defines it (4-14 s, every
  mined video), audited.

- 21:25 Nov 13 RULING 87 (orchestrator 21:18, relayed by the builder, NOT YET RECEIVED HERE DIRECTLY): one shared
  "Heimdall down" signal for the builder and this watcher (pp-selectid pipeline/heimdall_health.py, state under an
  flock in the builder's tree; down = no Heimdall family answering for 15 min; plan_b; probes). Answered the builder:
  it fits the watcher's outage handling (videos wait, no try used, STATE line 1 after 30 min, the breaker's 5-min
  probe); once the module is committed the watcher will call HH.note after its Heimdall calls and use HH.mode /
  probe_due / probe_result. MY MINER'S PLAN B IS "QUEUE AND WAIT": the spend freeze (05:30 Nov 12, "until told
  otherwise") still binds this watcher; plan_b never sends it to a paid frontier vendor unless the orchestrator lifts
  the freeze for pp-ingest directly. Raised: (1) a drill (overrides.json pointing Heimdall at a dead port) must never
  flip the fleet's signal (no HH.note while an override is active; asked for a drill flag in the module); (2) call
  volume (up to ~20 in flight: a note per call under an flock would contend; asked whether HH.note writes only on
  transitions); (3) the state file is in the builder's tree: written only through its module, once committed, and
  only with the ruling's text from the orchestrator.
  - 21:40 THE BUILDER'S ANSWER: (1) the module takes drill=True (recorded, never counted; tested: 40 min of drill
    failures leave the clock untouched); the watcher still skips HH.note while an override is active; (2) an answer is
    written at most once per 30 s per process, a failure always; (3) only through the module, once committed. It
    reads ruling 87 as ONE SHARED DOWN SIGNAL for the miner, the outside keys being named for its pin stage only, and
    not as lifting the 05:30 freeze; it put the question ("does Plan B send the miner to paid models, or does it queue
    and wait as today?") on its STATE line 1 for the orchestrator. Ruling 87's text (to the builder, 21:18), as
    relayed: "... When down: switch the whole pin stage to PLAN B at once: Grok mainly, then any other outside key
    that answers ... The same switch covers the miner and the writer: tell pp-ingest the contract so the watcher uses
    the same 'down' signal (its outage drill already exists). Plan B's spend counts on the same ledger and the same
    cap ...". UNTIL THE ORCHESTRATOR ANSWERS: the miner's Plan B is queue and wait. The watcher is wired to the
    signal when the module is committed (the builder will say).

- 20:25 Nov 13 RULING 40 P1 IS LIVE: imperative and single_source_breaking stand as hard flags only when BOTH models
  agree. Audited 2 cycles (cycle 1: glm / muse no P0, qwen's P0 the append race already refuted; cycle 2: qwen "P0
  None", glm "production ready, with two conditions", both implemented; muse timed out; pp-ingest_audit/r40p1/),
  commit 3c8132ed, the watcher restarted on it 20:09 ET. The builder was told at 20:25.
  - HOW: the watcher's `check` loop (every 30 s, 4 rows at once, newest first) asks the second model (glm-5.3-flash
    on Heimdall, never a model that mined the row's video) the narrow question with the ruling's definition for every
    imperative / single_source_breaking flag of a moment still inside 12 h; the answer goes into a new line of the
    moment (`risk_checks`). The adapter excludes on the EFFECTIVE flags: a counting "no" (another model than the
    miner, the current definitions) moves the label to `risk_notes` on the returned row (a recorded note, not an
    exclusion); "yes", "unsure", no answer keep it. The ledger keeps the miner's labels. Accusation is never released
    (P2 below). Only checkers that answer every calibration quote of these two flags right may answer: at 20:20 glm
    16/16 (allowed), muse 11/11 with 5 unanswered (not allowed).
  - FIRST ANSWERS (20:20-20:23): single_source_breaking yes 2, imperative yes 4, imperative NO 1 (released: Altcoin
    Daily 5dd8d204 "Buying crypto today ... is like buying Bitcoin over five years ago, but completely derisked", now
    returned with risk ['time_sensitive'] and the note). Cost $0.002 so far (cents a day). Live: live.json
    `second_model_checks_12h`; the adapter's report `released_by_the_second_model`.
  - THE BUILDER CONFIRMED (20:40): its adapter read excludes on `risk` only (its HARD_RISKS: accusation,
    partner_attack, imperative, guaranteed_return, single_source_breaking, ad_read, third_party_media), never
    recomputes imperative or single_source_breaking (the one label it adds is price_prediction on a snapped text), so a
    row whose label moved to `risk_notes` is eligible at its next build (about 21:05 ET, on the 12 h pool). No change
    needed on its side.

- 19:50 Nov 13 RULING 40 P2 MEASURED: THE SHARPENED DEFINITION DOES NOT MAKE THE SECOND MODEL SAFE ON ACCUSATION.
  ACCUSATION STAYS HARD AS THE MINER LABELS IT; I recommend no release path for it with this checker.
  - WHAT: the same 200 rows as this morning's table, the accusation question asked again under the sharpened
    definition ("alleges or insinuates wrongdoing (crime, fraud, market manipulation, corruption, self-dealing,
    dishonesty or abuse of office) by a person or organisation named in the clip or identifiable from its words, its
    title or its channel; criticism of a strategy, an opinion or a policy alleges no wrongdoing"), the checker
    calibrated first on this morning's accusation quotes plus 6 insinuation quotes (fictional names). $0.024.
  - CALIBRATION: glm-5.3-flash 10/12 (2 unmeasured): it answered NO to 2 of the 3 insinuation quotes ("Every time Dan
    Mercer tweets something bullish, the price dumps an hour later. Funny how that keeps happening."; "Ever since the
    hack, that exchange has been clearing the order book to refill its insurance fund."); muse 9/10, the second one
    missed too. Under P1's own rule (a checker answers only after EVERY calibration quote right) neither would be
    allowed to answer accusation.
  - THE TABLE: precision 66 / 129 = 51 % (95 % CI 43-60 %), the same as the first definition's 52 %. But the answers
    MOVED: of the 130 the miner flagged, 10 went no -> yes and 12 went yes -> no (17 % churn between two definitions
    of nearly the same meaning). Of the 9 insinuations the first definition let through, it now catches 3 (the
    Binance "book being cleared to refill the fund", CZ "the wealthiest man in crypto ... the price absolutely dumps",
    "one venue keeps forcing liquidations"); 6 are still "no" (CZ "does a bullish tweet and then the price absolutely
    dumps", "liquidate as many people as possible ... the Safu fund", CZ "is going to liquidate the market", "the
    venue that's been leaning on price", Susie Wiles' children's lobbyist jobs, MCI "picking winners and losers").
    Among the new "no": "99% of people depositing to Coinbase ... are fraudsters".
  - CONCLUSION: on accusation this checker is neither accurate on insinuation nor stable; a release would let through
    exactly "the one error we cannot afford". Unless you rule otherwise: accusation is never released; a future checker
    would first have to answer every insinuation calibration quote right before accusation is even measured again.
    Evidence: pp-ingest_audit/flagcheck_20261113/remeasure_accusation_sharpened.json.

- 19:25 Nov 13 RULING 80: THE HOOK PASS IS LIVE; THE 12 h BACKFILL IS DONE; THE BUILDER WAS TOLD AT 00:11:52 UTC (the
  first batch's minute). Audited 2 cycles first (qwen, glm, muse on Heimdall: no P0; pp-ingest_audit/r80/), deployed
  d4a15215 at 19:11 ET (the watcher restarted on it).
  - BACKFILL (every mined video published in the 12 h before 19:11 ET, newest first): 102 videos. 84 had no window
    with a Bitcoin term (no model call, no hook: Bloomberg, CNBC, Fox Business, Yahoo Finance and the like); 4 had
    Bitcoin windows and no line the model would open with; 14 gave 106 HOOK ROWS; 1 more (Simply Bitcoin NtaQGnfWRR8,
    23 hooks found) waits for one window the model answered invalidly 3 times (a reason over 160 characters), retried
    every 10 min; its hooks are written with the retry. 41 candidates were dropped outside 4-14 s (both sides: 1.2 to
    24 s; every dropped length is in the log).
  - COST: $0.060 for the whole backfill (141 Heimdall calls, 134 valid, 7 invalid and asked again; $0.0004 per
    window).
  - HOOK ROWS PER VIDEO (newest first): Simply Bitcoin L6H7538ogGs 7 ($0.0033); CNBC Television XXfT9oeM14c 1
    ($0.0007); Bloomberg Television Zgm4Vck6bVw 1 ($0.0006); Bitcoin Magazine QlieBet41X0 7 ($0.0028); Bitcoin
    Magazine 3kV3nWC5SAY 6 ($0.0021); Yahoo Finance Z1RFzHDftu8 2 ($0.0008); Bitcoin Magazine w6eeNCfT4yY 3 ($0.0022);
    CoinTelegraph VqNMYCgZ3Vw 11 ($0.0052); Stephan Livera NVUxOhIV3K8 16 ($0.0067); Robert Breedlove uaHNzi-Kgr8 27
    ($0.0112); Yahoo Finance MqVqfEDXgLo 1 ($0.0007); Bitcoin Magazine kqAD0sjfkz0 2 ($0.0019); Digital Asset News
    m83V9Xl9wLg 3 ($0.0016); Scott Melker KJRod6tJ_w8 19 ($0.0070); Simply Bitcoin NtaQGnfWRR8 23 ($0.0138; written
    19:36 ET after its one bad window failed 3 passes). BACKFILL TOTAL: 129 hook rows from 15 of 102 videos, $0.062.
  - THE BUILDER'S RESULT (pp-selectid, its 19:23 build on these rows): "the hook stage now PASSES. Before your rows, 0
    hooks rated >= 4": 378 adapter rows, 196 moments inside 12 h, 121 usable, 21 cleared step A, 14 cuttable, 7 can
    open, 1 rated >= 4: OUR hook, Simply Bitcoin L6H7538ogGs "AI can copy software, undercut margins, replace
    employees, help foreign actors to overthrow your CEO. But... They can't print more Bitcoin." (scroll 5, alone 4,
    setup 3; its visual check clean). That build then died at the line-up (a clip whose eligibility says not_statement;
    6 cuttable clips without a second-vendor step-A verdict: a Heimdall deepseek outage on its side). It rebuilds with
    NtaQGnfWRR8's 23 hooks (told 19:38).
    Live: `python3 tools/ingest_watch.py hooks`; live.json `hooks_12h`.
  - FROM NOW: every new upload gets the hook pass right after its moment pass (the `hook` loop, every 5 s; at most 4
    hook calls in flight, so new uploads' moment passes are never starved).
  - RULING 40 (19:22): P1 being built now as one change (the second-model check in the watcher; the adapter releases
    imperative / single_source_breaking only when the checker answers no); P2's re-measure of accusation under the
    sharpened definition is running; P3 accepted (no miner-prompt change). Accusation stays hard meanwhile.

- 19:25 Nov 13 RULING 80 (18:42, priority one): THE HOOK PASS IS BUILT AND TESTED (commit 3c69de24, pushed); AUDIT
  RUNNING; NOT LIVE YET: the backfill over the current 12 h window and the watcher loop start only on the audited code
  (the ruling).
  - WHAT IT ASKS: a second mining question over the same windows (mine-hook/1, Heimdall, role `hook`): "the 1 to 3
    lines in this window that would stop a scroll as the FIRST words of a short video". In the prompt, verbatim: the
    builder's judge question (pp-selectid package.py HOOK_QUESTION, rulings 52 / 59: "scroll" / "alone" / "setup",
    1-5; a test compares it with the builder's source), the ruling's hook (4 to 14 s, whole sentences, one speaker,
    understandable alone, a concrete / surprising / sharply put claim, contrast, number or question about Bitcoin or
    money) and its NOT list (greeting / show intro, a date or "this week", an ad read, a price prediction, an
    accusation), and the moment prompt's own score axes and flag list.
  - ROWS: moments with `role_hint: "hook"`, eligibility judged with the builder's role "hook", the span's own moment
    id (the builder's dedupe and delivered checks keep working); a row outside 4-14 s is not written. Every ledger
    append now carries the video's earlier flags for the same moment (a hook on a span the moment pass flagged keeps
    the flag: the adapter returns the latest line). The adapter is unchanged: hook rows are returned like any row.
  - LOOP: `hook`, every 5 s, 2 videos at once: mined videos published in the last 12 h, newest first (the current
    window's backfill at start, then every new upload after its moment pass); an outage waits without using a try.
  - THE BACKFILL, sized: 100 mined videos published in the last 12 h, 131 windows with a Bitcoin term (the rest are
    screened: no model call), about $0.10.
  - RULING 77's audit cycle 1 (qwen, glm, muse: no P0; "ready for production") is implemented: a corrupt delivered
    record now stops the pass (the one fail-open path), "PURGE NOT RUNNING" goes on line 1 of STATE after 30 min,
    unreadable paths are fail closed, stricter spec types (pp-ingest_audit/r77/C1_CONSENSUS.md). This audit cycle
    cross-validates those fixes too.
  - TESTS: tests/ingest 224 passed.

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
  delivery and deleting the rest is your call (one rule in purge.py). RULED 08:15 Nov 14: ONE COPY PER DELIVERY (the acquired section(s) the delivered pin's PROVENANCE names, by hash; the other cached copies deleted; the disk freed reported).
- A20 "Cached source media and audio ... (downloads, windows' WAVs, acquired mp4 sections)": deleted = the three kinds
  listed (acquired sections, the word pass's window WAVs, the worker's audio downloads). Renders' intermediates, the
  rendered videos, the V3 daily clips, the earlier segment pipelines and the March clips are measured and reported,
  not deleted: not listed, and a deletion cannot be undone.
- A21 "Newest uploads first, always" orders the mining; it does not stop it: videos older than 12 h are mined after
  every newer one, for the receipts.
- A22 Ruling 87, "every switch ... STATE line 1": the module is given NO STATE path (its writer would leave a lock
  file beside STATE.md and bypass the notices' lock); this watcher writes EVERY switch in the shared state, whoever
  made it, to its own line 1 under the notices' lock (the module still writes its own switch record to this
  watcher's evidence file when this watcher trips it).
- A23 "Answered inside its deadline": the gateway gave a reply within the back-end's own timeout (ok, or a reply the
  validator rejects); every other outcome of a real call is "not answered", as the contract says ("down, refused,
  empty or late"): 429 and 4xx included (the signal measures whether the fleet gets through).
- A24 One thread calls the builder's module; the router's threads only leave the outcome in memory, so a held or
  stuck shared lock can never stall the miner (the signal's notes wait instead; STATE says so after 30 min).
- A25 The probe: two probe-only Heimdall back-ends at the builder's 60 s deadline (the same models as the live ones),
  free of the circuit breaker, no transport retry, the first answer ends it, never a stored reply.
- A26 A drill = a base_url override present for that back-end in overrides.json: a real call wrongly taken for a
  drill only loses evidence, never flips the fleet's signal.
- A27 Ruling 98, "Heimdall down by ruling 87's signal for 20 minutes": the shared state says plan_b AND its failure
  clock (failing_since_utc, a time with its zone) is at least 20 min old (no family answering for 20 min running);
  closed at the back switch; a signal not read opens, closes and spends nothing.
- A28 "No hook-pass re-runs": the hook pass is not run on the paid route at all; its passes wait and catch up inside
  their 12 h once Heimdall is back.
- A29 "Others only if a probe shows credit": no other paid vendor is wired (no credit probe built); Grok, then Gemini.
- A30 The $2.00 cap: per ET day across the route, each call's recorded cost (xAI vendor-reported; Gemini's price-
  table estimate, an upper bound), each call holding its priced worst case before it starts.
- A31 "So its labels can be re-checked on Heimdall when it returns": miner_route on every row; the paid route's
  videos still inside 12 h are mined again on Heimdall once the signal is back (both models' flags kept on every
  moment both found; moments only the paid route found keep its labels; the second-model check still asks Heimdall
  about their imperative / single-source flags).
- A32 "Newest first, conversations first": conversations first (caption turns per minute >= 1.0, ruling 92's measure),
  then newest within each group (if the orchestrator meant newest first with conversations breaking ties, it is the
  order of one sort key). RULED 08:15 Nov 14: AS BUILT.
- A33 F1, "calibrated" (ruling 40 P1) means measured on the model as it answers now: a replayed reply is not
  a measurement. Every calibration quote is asked live; 16 short questions per back-end per calibration (two
  back-ends), at start and daily: about $0.003 a day. (Confirmed by the orchestrator's 08:15 F1 ruling.)
- A34 F1, the schedule: 3 rounds inside a calibration for unanswered quotes; none passing and one that could (or
  none callable, or a crash) -> tried again after 600 s, doubling up to a day; a pass, or every back-end
  answering a quote wrong -> the daily one. When one back-end passed and the other was left unanswered, the
  other waits for the daily calibration (the passing one answers).
- A35 F1, the measurement CLI (tools/ingest_watch.py flagcheck: flagcheck.main / remeasure) keeps its stored
  replies (a report is reproduced from them; it releases nothing).

## HOW TO OPERATE (for the orchestrator)
- status: `cd ~/worktrees/pp-ingest && python3 tools/ingest_watch.py status` (ruling 87: its `down_signal` block is the watcher's view of
  the shared Heimdall-down signal: mode, last probe, counts, switches seen; from live.json, with that file's age)
- packager read: `python3 tools/ingest_watch.py moments --since 2026-11-12T00:00:00+00:00 [--delivered ids.txt]`
- coverage now: `python3 tools/ingest_watch.py coverage --hours 24`
- outage drill: write `data/editorial/ingest/overrides.json` = {"heimdall_qwen27b": {"base_url": "http://127.0.0.1:9/api/v1"}};
  remove it to restore (recovery at the breaker's half-open probe, <= 5 min). Ruling 87: a drilled back-end's calls go
  to the shared Heimdall-down signal as drill=True (recorded, never counted); while a probe back-end
  (heimdall_qwen27b_probe, heimdall_glm53flash_probe) is overridden no probe runs. Or, without touching the live watcher:
  `PP_INGEST_STORE=<scratch> PP_INGEST_CHANNELS=<slug> python3 tests/ingest/drill_freeze.py --out <json>`
- spend freeze: `pipeline/ingest/providers.json` `spend_freeze.vendors`; lift = remove the vendor(s), restore the mine
  chain's tail (REQUESTS R6.5), restart. Spend by vendor: `tests/ingest/spend_by_vendor.py --out <json>`; live:
  `status` -> `usd_all_time_by_vendor`
- one service per store: a second `run` / `once` on the same store is refused (`ServiceBusy`)
- ruling 98's paid route: `status` / live.json `paid_route`; to stop it for good, remove `paid_route` (and the role
  `mine_paid`) from providers.json and restart: the freeze then binds every role again
- stop / start: `tmux send-keys -t pipeline_pp_ingest_watch C-c`; `tmux new-session -d -s pipeline_pp_ingest_watch
  -c ~/worktrees/pp-ingest "python3 tools/ingest_watch.py run"` (restart-safe: the queue recovers, replies are cached)
