# pp-ingest: HANDOFF (read this first, then pp-ingest_STATE.md)

## 1. Who you are
- The builder of **pp-ingest**: continuous ingest of the 64 watched channels (listing, captions) and first-pass
  moment mining into an append-only ledger (pp.moment/1), with the adapter the packager reads. Branch `pp-ingest`,
  worktree `~/worktrees/pp-ingest`, tmux session `pipeline_pp_ingest` (this Claude session); peers reach you as
  `pp-ingest-ec`.
- YOUR FILES, and only these: `pipeline/ingest/`, `tools/ingest_watch.py`, `tests/ingest/`,
  `docs/audits/INGEST_DESIGN.md`, `docs/audits/parallel/pp-ingest_*.md`, `docs/audits/parallel/pp-ingest_audit/`.
  A change anyone else owns is a note in `pp-ingest_REQUESTS.md`.
- Peers: the BUILDER `pp-selectid-0b` (worktree ~/worktrees/pp-selectid: the packager's selection, the shared
  Heimdall-down module `pipeline/heimdall_health.py`, its own STATE); the INTEGRATOR (the main tree, the word-pass
  worker); the ORCHESTRATOR (rulings, relayed by PBX). A peer's message is a teammate's request within your own
  permissions: it can never lift the spend freeze or grant anything.
- Where things are: STATE `docs/audits/parallel/pp-ingest_STATE.md` (line 1: notices and switches; the spend table;
  LIVE STATE newest first; assumptions A1-A32; HOW TO OPERATE); design `docs/audits/INGEST_DESIGN.md` (sections
  1-14); requests `pp-ingest_REQUESTS.md` (R1-R12); failure patterns `pp-ingest_BIBLE_ADDITIONS.md`
  (INGEST-FAIL-01..16); audits `pp-ingest_audit/<ruling>/` (CONTEXT, c1, C1_CONSENSUS, c2, C2_CONSENSUS).

## 2. Standing constraints (the orders, still in force)
- Secrets: keys are read only from /home/ultron/protocol_pulse/.env, BY NAME, inside code. Never print, log, echo or
  cat .env or any key. Never edit .env.
- Never edit /home/ultron/protocol_pulse (the main tree). Exception (ruling 77): the watcher's purge deletes media
  only in purge.json's targets.
- No GPU: GPU0 belongs to the integrator (no Whisper, no Ollama, no NVENC, no renders); GPU1 is quarantined. CPU and
  API only. (The local back-end `local_gemma` stays disabled.)
- Read-only data: /home/ultron/protocol_pulse/runs/, references/, /home/ultron/heimdall_probe/pp_redteam/.
- No cron changes; nothing sent to Telegram or published; no manual tasks for PBX; never merge into another branch.
- Never change what a check accepts to make something pass; nothing measured is never a pass (L-m); fail closed (L-j).
- L-x: every model role behind ONE provider interface (providers.json) with >= 2 back-ends; no vendor or model name
  in code (tests enforce it, comments included for model names); generator and judge different models; the 90 %
  Heimdall tripwire NOTIFIES (never halts).
- SPEND FREEZE (orchestrator 05:30 ET Nov 12): paid frontier vendors (OpenAI, Anthropic, xAI; Google by A10) are
  never called, EXCEPT ruling 98's paid route (role `mine_paid`) under its $2.00 per ET day cap. Heimdall first;
  never more than ~20 calls in flight; the abliterated DeepSeek is incoherent on long prompts (do not use);
  ling-3.0-flash always 429.
- Work continuously; do not stop to ask: take the most defensible reading, write it in STATE as an assumption; a
  question that must be asked follows section 2a (its recommended answer and its 20-minute default).
- Every change: build, test, 2-cycle cross-LLM audit (Heimdall-served reviewers under the freeze), then live.

## 2a. How questions work (RULING 106, orchestrator 20:22 ET Nov 14: no session waits on the orchestrator)
Standing, for all three sessions (PBX, 20:08: "pls fix that weakest part of how we are running this"; the
orchestrator's checks arrive late, and a session that stops at a question cost about five hours on Nov 14):
- (a) EVERY QUESTION CARRIES ITS DEFAULT. A question to the orchestrator goes on STATE line 1 (in capitals) as: the
  question, your RECOMMENDED answer, and 'DEFAULT IN 20 MIN: <what you will do>'. If it is not answered in 20 minutes,
  ACT ON THE DEFAULT and say so on line 1. Never stop work on an unrelated item while a question is open.
- (b) WHAT A DEFAULT MAY BE: anything that publishes nothing, installs no schedule, touches no cron, spends inside
  the caps, and can be undone (a build, a render, a review-only or candidate delivery to PBX's Telegram, an audited
  merge on our branches). When two readings of a law are possible: the STRICTER reading for integrity (L-s, L-v, L-u,
  a number or name hold), the reading that DELIVERS for taste and process. A finished video that passes every gate is
  always launched and delivered as a candidate; with one integrity point open it is rendered and delivered on the
  REVIEW path with that point stated in the caption, never left unrendered. (pp-ingest renders and delivers nothing
  itself: its defaults are builds, audited changes going live, readings recorded as assumptions.)
- (c) WHAT STILL WAITS FOR A HUMAN: publishing, a schedule, cron, a spend cap, loosening an integrity gate, deleting
  what is not ours. For those: do the preparatory work, and say exactly what is needed.
- (d) THE ALARM: when something that needs the orchestrator or PBX has waited 45 minutes (a ready video not
  launched, a cap reached, a real outage, every build refused), the INTEGRATOR sends ONE plain text message to PBX's
  Telegram review chat through the pipeline's own sender: 'PULSE CHECK NEEDS A DECISION: <one sentence>. Waiting since
  <time>.' At most one per issue and one an hour in total; nothing for routine progress (PBX: alerts are accurate and
  meaningful or off). pp-ingest NEVER sends it: it raises it with a line the integrator reads, 'ALARM FOR PBX: <one
  sentence>. Waiting since <time ET>.' on its STATE line 1 (e.g. the paid route's daily cap reached while Heimdall is
  really down, or a real outage of every mine back-end past 45 minutes). Write it with
  `spend.write_alarm_notice("<one sentence>", "<HH:MM ET from date>")` (it lands on line 1 after the batch spend; never
  edit line 1 by hand: the watcher rewrites it); remove it with `spend.write_alarm_notice(None, None)`.

## 2b. Batch money (RULING 108, orchestrator 21:22 ET Nov 14; design section 18; audit b108)
- One ledger for everything every session spends on the pipeline, kept by the BUILDER; BATCH 3 runs 21:10 ET Nov 14
  to 21:10 ET Nov 15: cap $8.00 all-in (tell the orchestrator at $6.00; ALARM FOR PBX at $7.50: the builder's ledger);
  inside it builds + sealing $4.50, audits $2.50, mining and checks $1.00 (pp-ingest's share). A session that needs
  another's share asks on line 1 with its default (2a).
- STATE LINE 1 is one physical line, written by the WATCHER: 'BATCH 3 ingest spend: $x (...)' FIRST (the builder takes
  it every hour), then any 'ALARM FOR PBX: ...', then every switch (ruling 87). The figure runs to the batch's latest
  whole hour: the watcher's calls (mining, hook pass, flag checks and calibration, probes, the paid route), vendor-
  reported, an abandoned or cut-off call at the model's own rate (ruling 107's basis), plus your audits from the
  ledger `data/editorial/ingest/audit_spend.jsonl` (the driver writes it), and "NOTHING BITCOIN IN THE LAST 3 H" when
  it holds (the orchestrator: Sunday's light uploads, said on line 1). Your session line (line 3) must never start
  with 'BATCH' or 'ALARM' text: only line 1 holds those.
- A NEW BATCH: edit `pipeline/ingest/batch.json` (name "BATCH <n>", start_et / end_et "YYYY-MM-DD HH:MM" ET, share_usd,
  share_of) and commit it as data; the watcher reads it again on its next minute, no restart. Outside a batch the paid
  route spends nothing (the stricter money reading), and line 1 says the batch closed: ask for the next batch's money
  then, on line 1 with its default.
- Ruling 98's paid route is held inside the share (a question with its default goes on line 1 if the share stops it).
  The watcher's own pace is about $0.28 a day (Nov 14), well inside $1.00.
- AUDITS (ruling 107 (2)) with tests/ingest/xllm_audit.py: `git add -N` (and `--force` for test_*) the new files, then
  `--cycle 1 --base <rev> --context <folder>/CONTEXT.md --out <folder>/c1` (qwen + glm by default; the package is the
  diff, laws and context, never the whole files; capped $0.30 under 60 changed lines, else $1.00, checked before any
  call). Since Nov 16 the pair is qwen + muse (glm out of every chain, ruling 119 (3)); if one is down, run the third
  family: `--only heimdall_mimo` (the paid frontier reviewers stay out
  under the freeze). Nov 14 22:00: the gateway dropped glm at 420 s and 511 s on a 30k-token package (booked at its
  own rate); muse took 315 s. COST.json in the folder; report the audit's cost on the commit line.

## 2c. The stalled miner (orchestrator 10:50 ET Nov 16; rulings 118, 119 (3); design section 19; audit r118)
- The cause on Nov 16: from 07:47 ET YouTube refused every caption download from this machine (HTTP 429) while it
  answered probes and listings; each refusal tripped the watcher's whole yt-dlp gate, so nothing was transcribed for
  three hours. The main tree's transcript ingest (cron */30, Whisper on GPU0) had most of the same videos.
- Now: the fetch step takes the pipeline's own transcript (main store, READ ONLY, every check, write-once copy) before
  any caption download and when a VOD has no English captions; a caption 429 stops the captions alone (retry in 10
  min); while the pipeline's own caption breaker is open no download is tried here.
- The outage clock is the watcher's OWN (`data/editorial/ingest/down_signal_state.json`, the builder's module, its API):
  another session's deadline misses never move it; any answer resets it.
- Ruling 118: the mine chain is qwen, deepseek 4.1, minimax, gemma, gpt-oss, mimo, then the local model (only under a
  GPU lease this watcher does not take); no paid route; never glm or muse in mining; glm in no chain at all.
- The self-check: "MINING STALLED SINCE ..." on line 1 when something waits and nothing was mined for 30 min; the
  watcher makes the waiting videos due at once (and every 30 min). When you see it, read what each waits on and act.
- If YouTube's 429s last and a video is not in the pipeline's store either: it waits for the pipeline's next Whisper
  run (every 30 min, its channels are the same registry); a clip with no English captions and no pipeline transcript
  waits to its 48 h `no_captions`.

## 3. The watcher (keep it running; it survives your restart)
- tmux `pipeline_pp_ingest_watch`, command `python3 tools/ingest_watch.py run` in ~/worktrees/pp-ingest. Log:
  `data/editorial/ingest/logs/service.log`; live numbers `data/editorial/ingest/live.json` (every 60 s);
  `python3 tools/ingest_watch.py status` (with the `down_signal` block). Store: `data/editorial` of this worktree
  (gitignored staging; never the main tree). One service per store (a second `run` is refused: ServiceBusy).
- Restart (restart-safe: the queue recovers, replies are cached):
  `tmux send-keys -t pipeline_pp_ingest_watch C-c`, then wait for the pid to exit
  (`timeout 420 tail --pid=<pid> -f /dev/null`; the session closes with it), then
  `tmux new-session -d -s pipeline_pp_ingest_watch -c ~/worktrees/pp-ingest "python3 tools/ingest_watch.py run"`.
  Find the pid with `ps -eo pid,args | awk '$2=="python3" && $3=="tools/ingest_watch.py" && $4=="run"'`.
- A restart loads the WORKING TREE: never restart with unaudited changes in it (Nov 16 11:31: a restart for an intake
  loaded r118 before its audit; put back by restoring the HEAD files, starting, then restoring the change).
- A stop can hang after "stopped" is logged while calls are in flight (11:33 Nov 16: two gateway calls of 300 s with
  transport retries): once "stopped" is in the log the queue is closed; `kill -9 <that pid>` is then safe.
- Loops: watch (10 min, all 64 channels), fetch (10 s), mine (5 s), hook (5 s), check (30 s), health (60 s), purge
  (600 s), signal (5 s). The builder's `heimdall_health.py` is loaded ONCE at start: after the builder commits a change
  to it, read the diff and restart the watcher.

## 4. What it does
- WATCH / FETCH: uploads playlists (RSS 404s: a canary every 30 min), new uploads queued; probe (yt-dlp gate, 3 at
  once), Shorts never mined, lives re-probed, captions stored through the store's own writer; duplicates by title +
  duration and whole-transcript fingerprint.
- THE MINER (`mine` role: qwen3.8-27b on Heimdall): windows of sentences, strict JSON (never repaired), moments to
  the ledger `data/editorial/moments/moment_ledger.jsonl` (append-only, flock, fsync). Every row: moment id (video,
  transcript hash, words), text, scores, risk flags, eligibility at mining (the builder's contract), `expires_at`
  (publish + 12 h), `episode` (caption turn measure, ruling 92), `miner_route` (the role that mined it, ruling 98).
  Outage (every back-end down or skipped): the video WAITS (no try used), retried every 10 min; a line on STATE after
  30 min. Newest uploads first (ruling 77).
- THE HOOK PASS (rulings 80 + 92, `mine-hook/2`, role `hook`): a second question over the same windows for videos
  published in the last 12 h: 1-3 openers of 4-14 s per window (the builder's OPENER rule applied; bad openers never
  written); rows are moments with `role_hint: "hook"`.
- THE FLAG CHECKS (ruling 40 P1, the `check` loop, role `flagcheck`: glm-5.3-flash, muse): a second model, never the
  miner, asks the narrow question for every `imperative` / `single_source_breaking` flag of a row still inside 12 h;
  the adapter releases such a flag only on a calibrated "no" (it moves to `risk_notes` in the returned row; the ledger
  keeps the miner's label). `accusation` is never released (P2 measured it unsafe). Calibration at start and daily.
- EXPIRY AND PURGE (rulings 76 + 77): the adapter refuses every moment 12 h after its video's publish time (rows
  kept); the purge loop deletes media of videos published > 12 h ago from exactly the targets in
  `pipeline/ingest/purge.json` (run sources, lock-precheck sources, abandoned /tmp/word_pass_*), never a delivered
  video's media, a run touched in 2 h, or an open file; log `data/editorial/ingest/purge/deleted.jsonl`.
- THE ADAPTER: `pipeline.ingest.ledger.best_unused_moments(...)` / `tools/ingest_watch.py moments --since <ISO>`.

## 5. Rulings in force on this side (one line each)
- Orchestrator 02:45 Nov 12: L-x, the blind A/B per role, the 90 % Heimdall tripwire is a NOTIFY.
- 05:30 Nov 12 SPEND FREEZE (above); its one exception is ruling 98's capped route.
- RULING 40 (03:13 + 19:22 Nov 13): P1 imperative / single_source_breaking stand only when both models agree; P2
  accusation stays hard as the miner labels it; P3 no miner-prompt change.
- RULINGS 76 + 77 (18:09 Nov 13): a moment usable only within 12 h of publish; rolling purge in the watcher's own loop;
  newest uploads first; the word-pass tiers "last 6 h, then 6-12 h" are the integrator's (REQUESTS R11).
- RULING 80 (18:42 Nov 13): the hook pass (role_hint "hook"), every new upload, the 12 h window.
- RULING 87 (21:18 Nov 13): ONE shared Heimdall-down signal (the builder's module); this watcher notes every real
  Heimdall call, probes while due, copies every switch to STATE line 1. REQUESTS R12 done: the probe claims its slot
  (pp-selectid 11ed255f; who="pp-ingest probe").
- RULING 92 (22:52 Nov 13): the hook pass favours conversations (mine-hook/2); role_hint stays "hook".
- RULING 98 (06:13 Nov 14): the miner's Plan B, the paid route (section 6).
- The builder's rulings 90-93 are on its side (its contract decides eligibility; the watcher records it at mining).

## 6. The outage signal and both Plan Bs
- THE SIGNAL (ruling 87; since r118, Nov 16, the watcher's OWN state file `data/editorial/ingest/down_signal_state.json`
  through the builder's module and its API: the orchestrator's 10:50 order (3); until then the builder's shared file
  `~/worktrees/pp-selectid/tests/package/proof/HEIMDALL_HEALTH.json`). Down = no Heimdall family answering for 15 min -> mode `plan_b`; back
  after 3 good probes (one probe per 2-minute slot fleet-wide, claimed). This watcher (`pipeline/ingest/downsignal.py`):
  notes every real Heimdall call (answered = ok or a reply the validator rejects; not = any other outcome of a real
  call; no note for a stored reply, a missing key, a probe call; a drill override = drill=True, never counted);
  probes with qwen then glm (60 s each) while due; copies every switch (anyone's) to the start of STATE line 1; its
  evidence file `data/editorial/ingest/down_signal.jsonl`. A signal not read is never taken as up or down
  (live.json at once; a STATE notice after 30 min). It passes the module NO state_md (its lock file would land beside
  STATE.md).
- THE BUILDER'S PLAN B: its pin stage on outside keys (Grok mainly), its side.
- THE MINER'S PLAN B since ruling 118 (Nov 16): the next Heimdall model of the chain, else the videos wait; the paid
  route below is CLOSED (paid_route and mine_paid removed from providers.json; the code stays dormant without them).
- (until Nov 16) THE MINER'S PLAN B (ruling 98): when the signal says plan_b AND no Heimdall family has answered for 20 min running
  (the state's failure clock), the route opens: only NEW uploads (published in the last 6 h; conversations first by
  the caption turn measure, then newest; no backfill; no hook pass) are mined on role `mine_paid` (Grok, then Gemini;
  the freeze lifted for this role only), capped at $2.00 per ET day (each call's recorded cost; each call holds its
  priced worst case before it starts, so $2.00 is a ceiling), then queue and wait. Back on Heimdall at the signal's back switch; then every video the paid route mined
  that is still inside 12 h is mined again on Heimdall once (both models' flags kept on every moment both found).
  Every route switch (on, off, cap reached) is on STATE line 1 IN CAPITALS. live.json `down_signal.paid_route`.

## 7. Spend
- The table at the top of STATE (every use, by vendor, with its basis). Refresh:
  `python3 tests/ingest/spend_by_vendor.py --carry docs/audits/parallel/pp-ingest_audit/spend_by_vendor_20261113.json
  --out docs/audits/parallel/pp-ingest_audit/spend_by_vendor_<YYYYMMDD>.json` (it sums the watcher's calls, every
  audit's results.json, the A/B and flag-check logs; the scratch stores' rows are carried). The Heimdall account:
  the watcher's spend meter (live.json; $460 cap, 90 % NOTIFY).

## 8. Open items
- The orchestrator's: A19 (the delivered videos' cached copies, 6.84 GB, kept); the out-of-scope media measured for
  ruling 77 (reported, never deleted); ruling 92 options (b) more hook candidates / (c) a spotlight question (not built).
- The integrator's: REQUESTS R10 (the reply cache key omits extra_body: clear a back-end's cache by hand after a
  reasoning change), R11 (the word-pass tiers).
- Recorded disagreements: muse's mine.py:481 overlap-rank point (kept as is; glm agrees it is not a defect).
- For the builder's next audit: "probe_due returned True" and "the slot is stamped" must stay one step (glm N2).
- Ruling 98's route is proven by tests only (no live outage since it went live at 06:46 ET Nov 14); at the first
  real outage watch live.json `paid_route` (open, why_not_open, spent_today_usd) and STATE line 1.
- Ruling 98 reading A32 ("newest first, conversations first" read as conversations first, then newest): the
  orchestrator may want the other order (one sort key in service._paid_due).
- Cosmetic, for the next change: the watcher's start-up WARNING still says "never a paid frontier fallback" (true of
  the mine role; ruling 98's route is a separate, capped role).
- The builder re-judges every clip with its own gates whatever mined it (its word, Nov 14): a paid-route label can
  cost yield, never integrity; it will say so before it ever builds on miner_route.

## 9. Traps (each cost time once)
- The stop hook audits the MAIN tree too and lists other sessions' uncommitted .py there: never commit them.
- The pre_bash hook blocks any command line holding '-f' (names, prose, --no-ff) together with 'push': commit and push
  in separate commands; force-add with `git add --force` in a command without push.
- The repo-wide `.gitignore` has `test_*`: new tests need `git add --force tests/ingest/test_x.py`.
- `pkill -f` matches its own shell: find pids with ps + awk; kill and edit in separate calls. Foreground `sleep` is
  blocked: wait for an exit with `timeout N tail --pid=<pid> -f /dev/null`.
- Times in STATE / DoD: take HH:MM from data or `date` inside the command that writes it; never type one.
- Audits under the freeze: `python3 tests/ingest/xllm_audit.py --cycle 1|2 --base <rev> --context <md>` (qwen + muse
  by default since Nov 16; glm is refused by name; ~5-10 min, ~$0.01-0.02 a diff-scoped cycle). qwen sometimes loops in cycle 2 (no
  verdict); glm may hit its length limit; muse is slow (timeout 1800 s). Verify every finding against the code.
- Tests must never touch the real shared state or STATE.md: pass `signal_state` / `signal_module` and monkeypatch
  `config.STATE_DOC` (see tests/ingest/test_signal.py, test_paid_route.py).
- Never write a note into the shared state from any other process (it is the fleet's signal).
- After an unreadable shared state, the signal is "read again" only at the next module call (mode, every 30 s).

## 10. State at this handoff
- The watcher: tmux `pipeline_pp_ingest_watch`, started 06:46 ET Nov 14 on 13de013b (ruling 98 live); the shared
  signal heimdall_first, the paid route closed, $0.00 of $2.00 spent today; 64 channels watched.
- Tests: tests/ingest 282 passed. Spend: the table at the top of STATE (to 06:48 ET Nov 14: ~$13.99; Heimdall $1.77;
  paid frontier $0.00 since the freeze).
- To pick up: read STATE line 1 (any switch or notice since), `python3 tools/ingest_watch.py status`, the tail of
  data/editorial/ingest/logs/service.log, then pp-ingest_STATE.md's LIVE STATE from the top.

