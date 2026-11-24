# Build 172: the three operational requirements (R1 ceiling, R2 routing, R3 deadline)

Prepared for the owner's order of 15:25 ET Nov 24. **Nothing was run live**: no launcher, no driver on live data, no
render, no service started or stopped, no model call. The scripts below are in git. Nothing starts on its own.
**End to end: NOT DEMONSTRATED.**

Branches: `pp-lean` (the builder) and `lean-release` (the release, new; cut from the pushed release head
`aff5e601b`, worktree `/home/ultron/worktrees/pp-lean-release`). The code is at `pp-lean db38b58e7` (R1-R3 in 98f703533, then a comment fix) and `lean-release cf2035dad` (dbb364f6c, then the
same comment fix), both pushed. `pipeline/spend_ceiling.py` is the same blob on both.

**Suites.**
- **pp-lean:** 53 files, 0 failing, 1157 passed.
- **lean-release:** 89 files, 1256 passed, 13 failing. The 13 are the same files, failing the same tests, at the
  UNMODIFIED release head `aff5e601b` in an equally fresh worktree. They read git-ignored reference data and
  assets (`references/`, the music) that no fresh worktree has.
- Evidence in `docs/audits/lean/ops172/`:
  - `SUITES_pp-lean.txt`, `SUITES_lean-release.txt`, `RELEASE_BASELINE.txt`;
  - `MUTATIONS.txt`;
  - `DRYRUN_start.txt`, `DRYRUN_launch.txt`, `DRYRUN_restore.txt` (run against the pushed heads at 16:43 ET; they
    created nothing);
  - `PRODUCTION_SNAPSHOT_1625ET.json` (read only).

## Read this first: two facts the owner has to weigh

1. **2700 s cannot hold build 172 as the code stands.** No measured render has been shorter than 3488 s. The six
   full renders on file since Nov 13 spent 1260-1705 s in their two renders and 999-1415 s in their QA gates. The
   three whose run folders end at their verdict took 3523, 3951 and 3488 s from preflight to verdict; the one
   delivered run sent at 3683 s. The deadline is enforced, so build 172 at 2700 s will stop, recorded as `DEADLINE_STOPPED`
   at the render, unless that render runs faster than any measured one. Nothing in the order lets me shorten the
   render or its gates.
2. **$1.50 is a hard limit on reservations, and a near-hard limit on bills.** No paid call starts if its reservation
   would take the day past $1.50. Grok and xAI vision are reserved at ruling 123's calibrated share of their list-price
   bound (Grok 25 %: none of the 895 recorded Grok bills passed it; vision 60 %: the highest recorded was 59 %). A bill
   above its reservation is counted as billed and stops every paid call at once. The arithmetic worst case (every
   call then in flight billing its full list bound) cannot be excluded offline. Reserving every call at full list
   price would make $1.50 hard for bills too, but it leaves no room to work: the lean (5) completion reserve alone
   would be **$2.29** at list (computed by `package.completion_reserve`), more than the whole budget.

## The commands (run by hand, in this order; each has `--dry-run`)

```
cd /home/ultron/worktrees/pp-lean
python3 -B tests/package/lean/lean_ops.py start   [--dry-run]     # R2: the two experimental instances
python3 -B tests/package/lean/lean_ops.py launch  [--dry-run] --build-no 172 --deadline-s 2700
python3 -B tests/package/lean/lean_ops.py restore [--dry-run]     # stops them; safe to run twice
python3 -B tests/package/lean/lean_ops.py snapshot                # production's state, read only
```

`launch` checks each of these and prints the result. A live launch refuses if any one fails:

- both trees clean and pushed: pp-lean, and lean-release (`git ls-remote`);
- the release copy at the pushed lean-release head;
- the live tree (the build reads it) has no uncommitted code;
- the one ledger is readable and not stopped (it prints the spend day, spent, held and room);
- the day's other spend is accounted for, with no unknown source;
- both experimental sessions are up with fresh heartbeats;
- production is undisturbed since `start` (`snapshot`, compared);
- nothing starts by itself (crontab, user timers, running loops);
- Book Terminal is named and avoided;
- the deadline, its shares and the measured stage times.

A dry run prints every check and every command, and executes nothing. The test
`test_lean_ops.py::TheDryRun` checks that it creates no file.

At 16:43 ET the launch's dry run passed every check except the four that need `start` (not authorized): the
release copy, the two sessions, and production's BEFORE snapshot. `start`'s own dry run passed every check.

## R1: one ceiling

**What changed**

| Branch | Change |
|---|---|
| both | `pipeline/spend_ceiling.py`, byte-identical on both (a test on each branch checks the other's copy). |
| | The one ledger: `/home/ultron/pp_spend/SPEND_D<day>.json`, one file a spend day (21:10 to 21:10 ET), under `flock` with a 10 s wait. |
| | `reserve` (:159) before the call; `settle` (:213) after it, with the vendor's figure or the metered one. |
| | `charge()` (:310) wraps a vendor call; `mark_dead` (:202) handles dead reservations. |
| | The guard (`install_guard` :418): urllib, requests and httpx refuse a paid endpoint without a live reservation. |
| pp-lean | `pipeline/providers.py`: the router's ceiling mode (`ceiling=` :816) on the same file and lock: |
| | - a bounded lock wait (:900); dead reservations kept (:928), and they stop the ledger (:1046); |
| | - a stopped ledger refuses (:1048); held reservations count as spent (:1002); |
| | - cost unknown keeps the reservation and stops: `_keep` (:1129), abandon (:1603), unavailable or no-answer (:1630, :1638); |
| | - a refusal before sending or a 4xx releases: `cost_known_zero` (:70) with the marks `_answered` / `_not_sent` (:58, :64); |
| | - a bill above its reservation stops (:1162); the guard sees the reservation in the call's thread (:1615); |
| | - a late answer settles a kept reservation (:1203); |
| | - `xai_search` refused (:1022), since its live-search fees are not in its reply. |
| | `tests/package/proof_ly.py:57,66`: under `PP_SPEND_CEILING=1` the driver's day ledger is the one ledger. |
| | `pipeline/package.py:5321`: the lean (5) reserve counts the render's sign-off ($0.05) and the lock Scribe ($0.0101) at their reservations under the one ledger, not their bills ($0.0045, $0.01); the reserve is then $0.8651 (computed), not $0.8193. Before this, a build that spent down to its reserve could leave its own render refused its sign-off. |
| | `tests/package/proof_ledger.py:456`: the router runs in ceiling mode. |
| | `tests/package/lean/ceiling_seed.py`: carries the day's other spend in. |
| | `tests/package/lean/ceiling_site/sitecustomize.py`: installs the guard in the builder. |
| lean-release | Reserve and settle at the four call sites, nothing else changed: |
| | - `pipeline/second_recogniser.py:60` (Scribe); |
| | - `pipeline/signoff.py:206` (the sign-off, per round); |
| | - `pipeline/visual_check.py:233` (xAI vision); |
| | - `pipeline/vo.py:77` (the voice). |
| | `scripts/lean/sitecustomize.py`: the guard for the render and the services. |
| | `pipeline/conftest.py:28`: tests use a temporary ledger. |

**Every chargeable operation of the three programs**

| Program | Operation | File:line | How its cost is known | Reserved before |
|---|---|---|---|---|
| builder | Grok (`xai:grok-4.20-0309-reasoning`): step A, verdicts, writes | providers.py:499 | vendor-reported (`cost_in_usd_ticks`) | 25 % of its list bound (ruling 123) |
| builder | xAI vision (`xai_vision:grok-4.7`) | providers.py:587 | vendor-reported | 60 % of its list bound |
| builder | Gemini 2.5 Pro (clips alone, step A second family; Plan B) | providers.py:316 | the vendor's token counts × the price table (Gemini reports no cost) | its list bound |
| builder | GPT (`openai:gpt-6.1-sol`), Claude (`anthropic:claude-opus-5-5`): Plan B only | providers.py:293, :531 | the vendor's token counts × the price table | its list bound |
| builder | the second ear (`elevenlabs_stt:scribe_v1`) | providers.py:699 | metered: audio seconds × the table's $ a minute | the audio + 5 s |
| builder | `xai_search` (trend brief) | providers.py:561 | not called by the build (nothing imports `trend_brief.py`); refused under the ceiling, since its live-search fees are not in its reply | n/a |
| lock service | Scribe on a span's window | second_recogniser.py:60 | metered: the request's audio seconds × $0.012 a minute (ElevenLabs reports no cost) | the same figure + $0.0001 |
| render | the render's own lock check, Scribe | the same site | the same | the same |
| render | the sign-off, up to 3 rounds (`xai:grok-3-mini`) | signoff.py:206 | vendor-reported; a reply without it is a cost unknown (stop) | $0.05 a round, stated (12 × its one recorded bill, $0.004013) |
| render | xAI vision route | visual_check.py:233 | vendor-reported | $0.50, stated; not seated (`VISION_MODELS` are Heimdall's), so not called |
| render | the voice (ElevenLabs TTS) | vo.py:77 | characters | per-build character cap (below) |
| free, not counted | Heimdall (in-house); the preflight's voice-plan read (`preflight.py:92`, an account read); Telegram; the clip scorer and the local judge (local GPU) | | | |

**The voice.** The plan is "creator", 363,000 characters a month. The last eight render preflights (Nov 14-23) logged 351,580
to 354,985 characters left; the latest, Nov 23 22:39 ET, logged 351,580. Whether characters past the limit are billed, and at what USD rate, was not established offline. I did not
invent a rate. The default is option B: the voice is outside the dollar ceiling, and a build may not pass **1000
characters** (`PP_SPEND_RUN` names the build). The preflight already refuses a render with fewer than 2000 characters
left, so a build can never pass the plan's included characters. The 1000 is 4.5 × the one real render on the outside
ledger (223 characters, Nov 23 22:43 ET). Option A (count the voice at a USD rate) works only with a rate the owner
states (`PP_VOICE_MODE=usd PP_VOICE_USD_PER_1K_CHARS=<rate>`); without it, every voice call is refused.

**Fail closed:**
- an unreadable ledger, or its lock not free within 10 s: refused;
- a call that ends with its cost unknown (a dropped connection, a timeout, a 5xx, a reply without the vendor's figure,
  an abandoned call, a process that died between reserve and settle): its reservation stays counted at full amount,
  and the ledger STOPS for every program until the owner clears it (`spend_ceiling.clear_stop`, logged in the ledger);
- a 4xx refusal, or a refusal before sending: released.

**The day's other spend** is carried in at launch by `ceiling_seed.py`:
- the production builder's day ledger;
- the integrator's priced outside lines;
- the builder's Grok audits.

Any other worktree's day ledger must be a copy of production's, or the launch refuses. The day ending 21:10 ET tonight
already stands at **$1.5101** (builder $1.4305 + the outside ledger's $0.0796), over $1.50. Build 172's spend day is the
next one, and it starts from whatever that ledger holds at launch.

**The maximum the launch could charge (one number): $1.50, minus the spend day's carried-in spend at launch.** That is
what the ledger lets reservations reach. The only way past it is a bill above its own reservation, which also stops
everything (see "Read this first", fact 2).

**Offline evidence** (no vendor asked; every ledger a temporary file; sockets blocked)

- `tests/package/test_ceiling.py` (pp-lean, 21 tests):
  - three processes (the builder's router, the lock service's Scribe, the render's sign-off) race one ledger: the total
    never passes $1.50, no update is lost, no reservation is left;
  - at the cap, the vendor is never asked and no socket opens;
  - a dead process's reservation stays counted and stops the ledger;
  - 4xx and refused-before-send are released; 5xx, a dropped connection and a 200 without an answer stop (driven
    through the router's own `_with_backoff` and key paths);
  - the per-build voice cap; the completion reserve reads the same ledger; the seed.
- `pipeline/test_lean_ceiling.py` (lean-release, 7 tests):
  - each of the four sites holds a reservation at the moment of its request and settles after;
  - at the cap each is refused before its request;
  - with the guard installed, urllib, requests and the ElevenLabs SDK (httpx) are refused without a reservation;
  - **a test that fails if a paid client is reachable without the ledger**: the static import closure of the render's
    and the lock service's entry points may name a paid endpoint only at the four charged sites, the preflight's free
    read, `spend_ceiling` itself, and `relay.call_llm`, which nothing they import calls (asserted).
- Must-fail credit (all three requirements): **20 mutations, 20 KILLED**, each made in a scratch copy and run
  after its unmodified control passed (`docs/audits/lean/ops172/MUTATIONS.txt`):
  - R1: the ledger's lock; dead reservations; the ceiling check; the guard; the stop on a cost unknown; the
    router's unavailable branch; the sign-off and Scribe reservations removed; a new paid client in a module the
    render imports; the reserve's render figures; `xai_search`; the driver's day ledger;
  - R3: the router's deadline; the lock wait; the alarm; the seal; the render's time; the deadline's record;
  - R2: a watchdog marker in a command line; restore by prefix.

**CANNOT BE VERIFIED OFFLINE:**
- that the vendors bill what they report (xAI's ticks);
- that a 4xx is never billed;
- whether ElevenLabs bills characters past the plan;
- the race against the live ledger's real load;
- the production services' own spend during the build: they are not in the one ledger live. The seed counts them at
  launch, and `restore` reports any change.

## R2: reversible routing

**What changed**
- pp-lean:
  - `tests/package/lean/lean_ops.py` (new: start, launch, restore, snapshot);
  - two path overrides, unset meaning production's paths as before:
    - `pipeline/lock_precheck.py:92` (`PP_LOCK_PRECHECK_RESULTS`);
    - `pipeline/package.py:228` (`PP_SCORER_VERDICTS`).
- lean-release: `scripts/lean/serve.py` (new: runs `lock_precheck.py serve` / `stand_alone_scorer.py serve` unchanged,
  under a command line without production's watchdog markers).

**The experimental instances (tmux `pipeline_lean_lockcheck`, `pipeline_lean_scorer`)**

They run the pushed lean-release head as a shared clone in `/home/ultron/pp_lean_run/release`, mounted at
`/home/ultron/protocol_pulse` inside a private mount namespace (`unshare --user --map-root-user --mount`):

- they keep the host's `/tmp`, pids, network and GPU0 lease;
- every live tree is mounted read-only, and every write lands in `/home/ultron/pp_lean_run/ns/<name>`;
- the key file is bound read-only, by name.

Their own environment (exact):

| Variable | Value |
|---|---|
| `PP_SPEND_CEILING` | `1` |
| `PP_SPEND_RUN` | `build172` |
| `PYTHONPATH` | `/home/ultron/protocol_pulse/scripts/lean` (inside the namespace: lean-release's) |
| `PP_HEARTBEAT_DIR` | `/home/ultron/pp_lean_run/heartbeats` |
| `PP_OUTSIDE_LEDGER` | `/home/ultron/pp_lean_run/spend/integrator_outside.jsonl` |
| `PP_LOCK_PRECHECK_DIR` | `/home/ultron/pp_lean_run/lock_precheck` (results seeded with a copy of production's) |
| `PP_LOCK_PRECHECK_EXTRA` | `/home/ultron/worktrees/pp-lean/tests/package/proof/lock_requests` |
| `PP_SCORER_DIR` | `/home/ultron/pp_lean_run/stand_alone_scorer` (verdicts seeded with a copy of production's); the scorer gets `--candidates` pp-lean's `docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json` |
| `CUDA_VISIBLE_DEVICES` | `0` |

The builder gets these:

| Variable | Value |
|---|---|
| `PP_LOCK_PRECHECK_RESULTS` | `/home/ultron/pp_lean_run/lock_precheck/results` |
| `PP_SCORER_VERDICTS` | `/home/ultron/pp_lean_run/stand_alone_scorer/verdicts/latest.json` |
| `PP_SPEND_CEILING` | `1` |
| `PYTHONPATH` | `tests/package/lean/ceiling_site` |
| `--work-dir` | `/home/ultron/pp_lean_run/work` (a copy of the builder's audio cache) |

- **GPU:** both services take the normal GPU0 lease per pass, with `wait_s=0`, and hold nothing while idle.
- **If an experimental instance dies:** nothing happens to production. They share only what any tenant shares: the
  GPU0 lease, and for the render the render run lock. Both are `flock`s, released when the holder's processes end.
  The build's lock checks then go unanswered: UNVERIFIED, never a pass. Production's watchdog never restarts or
  confuses it: its heartbeats are elsewhere, and no experimental command line holds production's markers
  ("lock_precheck.py serve" and the rest).
- **Not routed:** the local judge, the last-resort leg of step A's second family. pp-lean's requests to it go
  unanswered and are HELD, never a pass. Routing it would need a third instance holding gemma3:27b on GPU0.
- **Book Terminal:** worktree `/home/ultron/worktrees/book-terminal`, branch `book-terminal` (head `6c76cafe2` at 16:25 ET; it commits on its own), tmux
  session `book_terminal_r2` (one Claude Code pane, no service). No command names any of them; the namespace keeps
  `/home/ultron/worktrees` read-only. The golds_ sessions are never named either.
- **Production before and after:** `start` writes `PRODUCTION_BEFORE.json`, and `restore` compares it with
  `PRODUCTION_AFTER_<time>.json`. The comparison covers:
  - production's service processes (pid, start time, command), its tmux sessions and their panes;
  - the live trees' HEAD and tracked changes;
  - the crontab;
  - the key file's size and time (never opened).
  It prints `PRODUCTION AS BEFORE`, or names what differs. A production ledger that grew is reported as production's
  own spend.
- **Restore:** kills the two sessions by exact name (`=pipeline_lean_…`; never `pipeline_pp_lean`, this session),
  stops leftover processes holding our markers only, and is safe to run twice. It leaves `/home/ultron/pp_lean_run` as
  evidence.

**Offline evidence:** `tests/package/test_lean_ops.py` (10 tests):
- a dry run executes nothing and creates nothing, yet prints every command;
- no experimental command line holds a watchdog marker or names Book Terminal;
- the namespace keeps every live tree read-only;
- restore stops only its own sessions, by exact name, and is safe twice;
- compare names what changed.

**CANNOT BE VERIFIED OFFLINE:** that the namespace mounts succeed on this kernel for this user tonight (they did for
the verifier's render on Nov 24); that the services serve from it; any live before/after comparison.

## R3: one deadline

**What changed (pp-lean)**
- `pipeline/providers.py:85` `DeadlineStopped`, a BaseException, so no `except Exception` reads it as a failure or
  a verdict. With it, `_deadline_left` (:1119, called :1575, :1707): no call starts whose own deadline would end past
  the build's.
- `tests/package/proof_ledger.py`:
  - `--deadline-at` (:686), armed at :696 (SIGALRM, `arm_deadline` :408);
  - the router gets it (:830);
  - the lock pre-check waits at most the time left, and an answer still missing at the deadline stops the build as
    UNVERIFIED (`lock_for` :377);
  - nothing seals after it (:942, :973);
  - at it, the build stops and writes its ONE outcome line with time per stage, then exits 124 (:635-654).
- `tests/package/outcomes.py`: the new word **`DEADLINE_STOPPED`** (:43), its plain notes (:105), the driver's stop
  (:481), and `amend_stage` (:617) for the launch's render and delivery.
- `lean_ops.py launch`: one deadline (`--deadline-s`, default 2700), with these shares:
  - the build to +1500 s (`--deadline-at`, and `timeout` 30 s after it);
  - the render only the time left before the delivery's 120 s;
  - the delivery the rest.
  Each stage is stopped at its limit and recorded.

**Shares, from measured times.**
- Build 171 reached its stop in about 1237 s. Its stage seconds:

  | pool | step A | second ear | out-edge | hooks | vision | line-ups | gates |
  |---|---|---|---|---|---|---|---|
  | 94 | 92 | 71 | 361 | 68 | 167 | 348 | 36 |

  The build's share is 1500 s.
- The render, preflight to verdict, took 3488-3951 s.
- The one delivered run's Telegram delivery took 18 s; its share is 120 s.

**What does not fit in 2700 s:**
- **the render**, measured: 3488 s at its fastest;
- the lock service's 1200 s wait per unanswered span, now bounded by the time left;
- model calls of 120-300 s, which are now not started without the time to finish.

**What was bounded:** every stage, every model call's start, the lock wait, and the seal.

**What was NOT shortened into a pass:**
- an unanswered lock check is UNVERIFIED;
- an unanswered model check stays unanswered;
- the build ends `DEADLINE_STOPPED`.

**Offline evidence**
- `tests/package/test_deadline.py` (10 tests):
  - the router starts no call that could not end in time;
  - the lock wait is the time left, and a missing answer at the deadline stops the build;
  - the driver, still in its line-ups at its deadline (0.5 s), stops there in under 5 s and writes its one line
    (`DEADLINE_STOPPED` at "line-ups", with seconds per stage);
  - a pin sealed before the deadline stands; a build that ends first is never stopped later;
  - the word is its own.
- `test_lean_ops.py::TheOneDeadline`, on a fake clock:
  - with 1200 s used by the build, the render is handed 1380 s and recorded `DEADLINE_STOPPED`;
  - a releasing render is delivered in the rest;
  - no time left means nothing starts.

**CANNOT BE VERIFIED OFFLINE:** the real stage times of build 172, and how a real render stops under `timeout` (it
holds the render lock and GPU0 lease, both released when its processes end).

## Nothing starts by itself (evidence printed by `lean_ops.py`, 16:12 and 16:43 ET Nov 24, `DRYRUN_*.txt`)

- **crontab:** 89 lines; 0 name `proof_ledger.py`, `build_and_record.sh`, `pulse_check_run.sh`, `lean_ops.py` or
  `watch_ledger.py`.
- **systemd:** 0 user timers; the system timers name none of them.
- **Running processes:** 0 running any of them.
- **Running watchers:**
  - the session watchdog only restarts its four services (`tools/session_watchdog.py` LAUNCH);
  - `tools/ingest_watch.py` (pp-ingest) has no `subprocess`, `send-keys`, driver or render call.
- **Nothing is scheduled at 21:10.**

## Found on the way (flagged, not changed)

- `pipeline/test_g20_signoff.py:115-118` (release) runs the voice with a stub client without pointing
  `outside_spend` at a temporary ledger. Run in the live tree, it has written 20 unpriced "service unknown" TTS lines
  into the live `data/spend/integrator_outside.jsonl` (Nov 24, 08:51 to 10:25 ET). They carry no dollars, but they
  look like renders.
- pp-ingest's miner has its own paid route (ruling 98, its own day cap). It is a fourth program, not one of the three:
  it is not carried into the $1.50. Counting it is the owner's call.
- At 15:39 ET, a first version of a guard test in `test_ceiling.py` installed a stub HTTPS handler that `urllib` ranked
  after its real one. It may have sent five unauthenticated GETs, with no key, no body and nothing billable:
  - to `api.x.ai` (2);
  - to the Heimdall host;
  - to `api.telegram.org/bot1`;
  - to ElevenLabs' subscription read.
  Every test since blocks sockets and DNS first.
