# Build 172: SCORER FAILURE OF 12:08 ET: THE DIAGNOSTIC (Nov 25)

This is the owner's one diagnostic of 12:14 ET. There was no build, no driver, no launcher `run` or `launch`, no render,
no paid call and no vendor network call. **End to end: NOT DEMONSTRATED.**

Everything ran in a scratch run folder (`/var/tmp/pp_leantest_run`, removed afterwards), inside the namespaces the live
services run in:
- lean_ops's own `ns_script`;
- the host network (the scorer must reach the local Ollama);
- the key files bound from /dev/null;
- a scratch ledger in place of `/home/ultron/pp_spend`.

**Code and evidence:**
- **Code:** the fix and its tests are pp-lean `99252369f`. The diagnostic's last two phases and this evidence are in the
  commit that carries this section. lean-release is unchanged at `7f4317bb0`.
- **Evidence:** in `docs/audits/lean/ops172/`:
  - `SCORER_DIAG_ss.txt`
  - `SCORER_DIAG_score.txt`
  - `SCORER_DIAG_lockcheck.txt`
  - `SCORER_DIAG_lockreplay.txt`
  - `SCORER_DIAG_restore.txt`
  - `MUTATIONS_owner.txt`

  The harness is `tests/package/lean/scorer_diag.py` (phases `setup`, `ss`, `score`, `lockcheck`, `lockreplay`).

**Why the checks themselves are not edited.** Both checks sit in files that other code pins by sha:
- **story_semantics.py** is one of the two files the scorer's `scorer_sha` hashes (`stand_alone_scorer.py:55-57`). The
  builder accepts a verdict only under the sha of the LIVE tree's copies of those two files (`package.py:231`,
  `render_scorer_sha` `:1606`), and the stand-alone floor is pinned to `edd54964...` (`package_pin.py:196`). Any edit
  would make every experimental verdict unusable and drop the floor rule, which is an editorial change.
- **gpu0.py** is in the lock pre-check's `decoder_sha` (`lock_precheck.py:82`).

So the release code stays byte-identical, and the fix is in what the namespace shows to the unchanged checks.

## (a) The ss outputs, verbatim (`SCORER_DIAG_ss.txt`)

**On the host** (uid ultron, the init user namespace):
```
$ ss -ltnp 'sport = :11434'
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0      4096       127.0.0.1:11434      0.0.0.0:*    users:(("ollama",pid=24220,fd=3))
$ ss -ltn 'sport = :11434'
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0      4096       127.0.0.1:11434      0.0.0.0:*
```
The code's own checks on the host gave:
- `LocalLLM()._listener_pid()`: 24220.
- `LocalLLM().start()`: serve_pid 24220, `CUDA_VISIBLE_DEVICES=0`, `OLLAMA_HOST=127.0.0.1:11434`, digest `a418f5838eaf...`.
- `gpu0._ollama_pids()`: `[24220]`.

**Inside the scorer's namespace, as at 12:08** (no owner record):
```
$ <scorer namespace> ss -ltnp 'sport = :11434'
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0      4096       127.0.0.1:11434      0.0.0.0:*
$ <scorer namespace> ss -ltn 'sport = :11434'
State  Recv-Q Send-Q Local Address:Port  Peer Address:PortProcess
LISTEN 0      4096       127.0.0.1:11434      0.0.0.0:*
```
The code's own checks inside gave:
- `_listener_pid()`: `null`.
- `LocalLLM().start()`: `RuntimeError: no Ollama listening on 127.0.0.1:11434`, the 12:08 error.
- `gpu0._ollama_pids()`: `Gpu0Unreadable: the GPU0 Ollama listener's pid is not visible to this user`.

**Inside, with the fix:** `ss -ltnp` shows `users:(("ollama",pid=24220,fd=3))`, and all three checks give exactly the
host's answers.

## (b) Every exception met, in order

1. **`RuntimeError: no Ollama listening on 127.0.0.1:11434`** at `story_semantics.py:171`. Met by the live scorer at
   12:08:30 and reproduced in the ss phase.
   - **Cause:** the scorer runs in a user namespace. For a process outside it (Ollama, pid 24220, the same uid), the
     kernel refuses `/proc` access to the process's fd links from inside a child user namespace. So `ss -p`
     (`story_semantics.py:160`) sees the socket but names no owner.
   - **Fix:** `lean_ops.ollama_owner` `:223` and `owner_bridge` `:290`, described below.
2. **`PermissionError: [Errno 13] Permission denied: '/proc/24220/environ'`**, met in my probe inside a user namespace.
   `story_semantics.py:172` would raise it next had a pid been found.
   - **Cause:** the same kernel rule.
   - **Fix:** the same; the recorded environment is presented in place of the real one.
3. **`Gpu0Unreadable: the GPU0 Ollama listener's pid is not visible to this user`** at `gpu0.py:412`, met in the ss
   phase.
   - **Cause:** the same; `gpu0.py:405` runs its own `ss -ltnpH`. This runs in every `swap_to` and `release_all`, as
     part of the check for foreign GPU users. So the lockcheck's first GPU0 decode, and the render's, would have
     failed here next.
   - **Fix:** the same bridge.
4. **After the fix:**
   - **The scorer:** no exception; exit 0.
   - **The lockcheck:** only the designed refusal, three times (one per window):
     `CeilingRefused: the ceiling: spent $1.5000 + held $0.0000 + this elevenlabs_stt:scribe_v1 call's $0.0079 > $1.50:
     refused before the vendor is asked`.

**The fix** (pp-lean `99252369f`, `tests/package/lean/lean_ops.py`):
- **`ollama_owner` (`:223`)** runs OUTSIDE the namespace, right before each service starts (`start` `:941`) and before
  the render (`launch` `:1146`).
  - It reads the listener exactly as the checks do: `ss -ltnpH`, then `/proc/<pid>/environ`.
  - It keeps the pid, its start time, the listening socket's inode and fd, and the two variables the check reads,
    `CUDA_VISIBLE_DEVICES` and `OLLAMA_HOST` (`:209`).
  - Nothing else of Ollama's environment is copied.
- **`owner_bridge` (`:290`)** is a line in every namespace script (`:184`).
  - Inside that namespace only, it bind-mounts the recorded environment over `/proc/<pid>/environ` and the recorded fd
    link over `/proc/<pid>/fd`. The host's /proc is untouched.
  - It does so only while that pid is still the process recorded (same start time). A restarted Ollama, or none, gets
    nothing.
- **The checks still refuse** (tests `test_lean_ops.py:487-577`, real namespaces, the release's own unchanged checks
  against a stand-in listener):
  - nothing listening still raises (`:540`);
  - an owner that is not GPU0-only still raises `is not GPU0-only: CUDA_VISIBLE_DEVICES=1` (`:533`);
  - an owner that cannot be identified (a different process instance, or another namespace's record) is refused, not
    accepted (`:549`);
  - only the two variables are copied (`:565`);
  - every namespace script carries the bridge (`:572`);
  - the owner is recorded before each service (`:577`) and before the render (`:105`).
- **Must-fail credit:** 7 deliberate breakages of the fix, each run after a passing unbroken control. All 7 were caught
  (`MUTATIONS_owner.txt`). "Nothing listening" is a guard that no bridge change can break: nothing presented can make
  `ss` show a listener that is not there.
- **gpu0.py is fixed the same way, without being edited:** the bridge serves its `ss` exactly as it serves
  story_semantics'.

## (c) THE VERDICT of the one real score, and the scorer's whole log (`SCORER_DIAG_score.txt`, 12:28:49 ET)

**The candidate:** `cand.0173aaa66a555d57b86a~trim.42e3fab44edd.json`, the first of the 12:08 run's 47 queued for
2026-11-24T17:56:57. It was copied (read only) into the scratch scorer's requests folder, so the scorer served exactly
one.

**The reply cache:** an empty scratch store (`PP_EDITORIAL_STORE`). Production has answered all 47, so their cached
replies would have answered without loading the model.

**What ran:** the scorer, in its namespace, once, through `runpy` of `pipeline/stand_alone_scorer.py` (the module
`serve.py` runs, in its `once` mode).
- It took the normal GPU0 lease: the lease file records pid 397382, "pin-stage clip scorer (integrator, GPU0)", 12:28:52.
- It loaded gemma3:27b on the shared Ollama and scored.
- It released (gemma3:27b unloaded, the lease freed) and **exited 0 after 38 s**.
- The model's raw reply is in the scratch cache:
  `{"ratings": [{"id": "clip_01", "score": 2, "fault": "starts_mid_thought", ...}]}`.

```
[
 {
  "request_id": "cand.0173aaa66a555d57b86a~trim.42e3fab44edd",
  "kind": "moments",
  "event": null,
  "pid": "clip_01",
  "channel": "Bitcoin Magazine",
  "duration": 20.15,
  "prompt_sha256": "1145a8f4fa1e009906039f0e2e1cbb477f72e1d1c04fa54b1528d7d5b525c0be",
  "score": 2.0,
  "reason": "Starts by referencing 'that' and 'digital credit' without establishing context.",
  "fault": "starts_mid_thought",
  "affirmed": false,
  "threshold": 3.5,
  "model": "gemma3:27b",
  "digest": "a418f5838eaf7fe2cfe0a3046c8384b68ba43a4435542c942f9db00a5f342203",
  "scorer_sha": "edd54964a5ab15f4a17d74ecbe40bcbccf2fdf2818df97881e8f7039a4721f53",
  "at": "2026-11-25T17:29:25Z"
 }
]
```
**It matches production's verdict for the same moment and text** (read only, 2026-11-24T17:13:53Z): score 2.0, not
affirmed, the same prompt sha256 and the same digest.

The scorer's whole log:
```
pin-stage scorer: /var/tmp/pp_leantest_run/stand_alone_scorer | scorer_sha edd54964a5ab
12:29:25   cand.0173aaa66a555d57b86a~trim.42e3fab44edd.json: 1 passage(s), affirmed 0
```

## (d) The lockcheck walk (`SCORER_DIAG_lockcheck.txt`, 12:39:33 ET; `SCORER_DIAG_lockreplay.txt`)

**The request:** `pp-selectid.ledger_20261114_011253.1`. This is the request the live lockcheck took up at 12:08:30
from the builder's request folder (copied, read only). It has three segments: `L6H7538ogGs` 897.877-906.587 (hook),
`uaHNzi-Kgr8` 153.25-165.89 (clip) and `NtaQGnfWRR8` 3475.26-3494.26 (clip).

**The source fetch.** All three windows came from the lock pre-check's own cache: `r159-g18`'s
`data/lock_precheck/work/<window>.9326604699a7/sources/`, the same decoder sha, read only. Only the source files were
copied, so the decode and the Scribe leg really ran. The log says `acquired (youtube_window)`, with `download_s` 0.0.
A `yt-dlp` that refuses stood first on PATH; it was never called.

**The decode on GPU0 under the normal lease:** Whisper large-v3 (faster_whisper 1.2.1) took 19.9 s, 6.8 s and 14.7 s.
Its transcripts were written to the scratch work folders, and the lease was released.

**The transcript comparison** ran inside the namespace up to the Scribe leg. A replay of the same lock code on the
walk's own decode (CPU only, a second recogniser that only records where it is asked) shows where Scribe was needed:
- **`L6H7538ogGs` (hook):** ruling 17's lock stands without the second recogniser. The lock reads "AI can copy software,
  undercut margins, replace employees, help foreign actors to overthrow your CEO, but they can't print more Bitcoin."
  Scribe is asked next, by ruling 72's spoken comparison.
- **`uaHNzi-Kgr8` (clip):** the same; ruling 72 asks Scribe.
- **`NtaQGnfWRR8` (clip):** the decode differs from the approved text, so ruling 17 itself asks Scribe
  (`segment_lock` → `adjudicate_lock`).

**The Scribe leg was refused by the scratch ledger at room $0.** The scratch ledger was spent $1.5000, held $0.0000,
room $0.0000. Each call (estimated at $0.0079, $0.0087 and $0.0099) was refused "before the vendor is asked".
- Each window's outcome is `error`, never a pass: "no verdict".
- `scribe_usd` is 0.
- The scratch ledger is unchanged, and the outside ledger was never written.
- The request is answered and moved to `done/`. The lockcheck **exited 0 after 49 s**.

**Two notes on how this was set up:**
- **The fake key.** Scribe reads its key BEFORE it reserves (`second_recogniser.py:42`, then `:60`). With the key files
  masked and no key in the environment, the leg stops at `relay.get_key` (`KeyError`) before the ceiling is asked. So
  the walk gave it a dummy `ELEVENLABS_API_KEY` from the environment, to reach the ceiling.
- **The backstop.** A dead `https_proxy` (127.0.0.1:9) meant no https request could have left even if the ceiling had
  failed.

## (e) The restore (`SCORER_DIAG_restore.txt`, 12:41:54 ET)

- **Production:** PRODUCTION AS BEFORE against the snapshot taken before the lockcheck walk (12:38 ET). Also PRODUCTION
  AS BEFORE against the 12:08 run's own restore snapshot (`PRODUCTION_AFTER_20261125T170831Z.json`, read only), which
  covers the whole diagnostic.
- **GPU, before and after both GPU phases and now:**
  - GPU0 at 18 MiB;
  - the only compute processes are production's two, both on GPU1;
  - the GPU0 lease free, and no production GPU0 want flags;
  - Ollama's `/api/ps` reads `{"models":[]}`, as found.
  - The diagnostic ran no tmux session (only the suite's tests use `pipeline_leantest_t_*`). No experimental or
    diagnostic process is left.
- **The ledger:** `/home/ultron/pp_spend/SPEND_D20261124.json` sha256 `cce00c3ca43b2fcb` at 12:28 and now. That is its
  state after the 12:08 run's ledger-init.
- **The 11:08/12:08 evidence:** nothing under `/home/ultron/pp_lean_run` has changed since 12:09.

## (f) What was not exercised

- **The live key, and a real Scribe reading.** So neither the ruling-72 spoken comparison's result nor any final lock
  outcome (no_difference, adopt_spoken, hold) was produced.
- **A YouTube download.** The windows came from cache. The experimental lockcheck's own work folders start empty, so in
  a live run it downloads.
- **The tmux start with the bridge.** This diagnostic built the namespaces with `ns_script` directly. The tmux start
  path that records the owner is covered by tests (`:577`, and the real-tmux start tests), not by a live start.
- **The render's namespace with the bridge:** tests only (`:105`).
- **An Ollama that restarts mid-run:** refused by the bridge (tested with a stand-in), never tried on the real one.
- **The scorer's `--candidates` serve loop:** the queueing and `verdicts/latest.json`.

**Found, not changed (outside this order):**
- **The 47 candidates in a live run.** Production has answered all of them, so the experimental scorer would answer them
  from the shared reply cache without loading the model.
- **Stale lock requests.** The builder's request folder (`pp-lean tests/package/proof/lock_requests`) still holds two
  Nov 14 requests, for the same three windows walked here. The experimental lockcheck's scratch root has none of
  production's "answered" markers, so a live run re-answers them first: downloads, about 40 s of GPU0, and about $0.027
  of Scribe, inside the $1.50. That is what the 12:08 lockcheck had started on.

# Build 172: STARTUP FAILURE OF 11:08 ET AND ITS FIX (Nov 25)

Prepared for the owner's order of 11:18 ET. Beyond yesterday's limits, exactly one thing was run: the two experimental
services, started offline in a scratch run folder, then stopped. Offline means no network, the key files bound from
/dev/null, nothing to serve, and sessions named `pipeline_leantest_*`. No launch, driver, render, model call or vendor
call happened. **End to end: NOT DEMONSTRATED.**

- **Code:** the fix is pp-lean `881bae321`. `32e1a6629` adds one more preflight test and the evidence. Both are pushed.
- **lean-release:** unchanged at `7f4317bb0`. Nothing in the services needed to change.
- **Evidence:** `docs/audits/lean/ops172/`:
  - `STARTUP_REPRO_1108.txt`
  - `STARTUP_PROOF.txt`
  - `DRYRUN_startupfix.txt`
  - `MUTATIONS_startup.txt`
  - `RUN_1108_run_20261125T160800Z.log`, a copy of the 11:08 run log.

## The error, verbatim

```
$ tmux new-session -d -s pipeline_leantest_lockcheck -c /var/tmp/pp_leantest_run '<the 11:08 lockcheck line>'
command too long
(exit 1)
```

The first failing command was the tmux client itself, refusing the `tmux new-session` command. No session was created
and nothing in the namespace ran. The tmux session did not die with its output: it never existed, and the service never
started.

`tests/package/lean/startup_repro.py` rebuilt the 11:08 command from git at `f71e01c85`. Its first 4,000 characters,
which is all the run log keeps, match line 36 of the run log exactly. The reproduction then ran it against a scratch
folder whose path has the live one's length, with `--net`, the keys masked and empty request folders added. That
version was 22,302 bytes, and tmux refused it as above.

## Root cause

The lockcheck's whole start line (the namespace script with 67 overlay mounts, 22,156 bytes) was handed to tmux as one
command. tmux 3.2a sends a command to its server in one message of at most 16,384 bytes. It accepted at most 16,363
bytes as it counts them; at 16,312 bytes of shell command it answered "failed to send command", and at 17,000 and
22,222 bytes "command too long". `start` sent the tmux client's output to /dev/null, so the run log said only
"FAILED to start lockcheck".

**Why the offline namespace check passed yesterday** (`ns_check.py stat`, `NS_STAT_B123.txt`): it ran the same
namespace script through subprocess, that is execve, which accepts one argument of up to 128 KB. It never went through
tmux. The unit tests replaced the runner with a stub, and the dry run only printed the command. So nothing before 11:08
handed the full line to a real tmux client.

## The fix (`tests/package/lean/lean_ops.py` at pp-lean 881bae321)

| What | Where |
|---|---|
| The start line goes in a file, `RUN/ns/<name>.start.sh`. The service's command inside it is the same as at 11:08. | `service_script` :218; written by `start` :842 |
| tmux is handed only `exec bash <that file> </dev/null 2>>RUN/logs/<name>.log`: 257 bytes for the lockcheck, 245 for the scorer. `remain-on-exit on` is set in the same tmux command, before the server can see the process end. | `tmux_cmd` :234 |
| Everything the mount script and the service print goes through `tee -a RUN/logs/<name>.log` into the log and the pane. The log runs from the file's first line, with a START line and an ENDED line carrying the exit status (`pipefail`). | :229 |
| tmux's own output (its "command too long") goes into the same log. On a failed start, the log's last 40 lines are printed into the run log. | `start` :847-850, `say_tail` :255 |
| A pane kept after its process ended does not count as a service that is up. `services_ready` refuses at once and prints the log's last 40 lines. The launch's preflight fails it. | `pane_state` :262, `services_ready` :727-739, `preconditions` :692 |
| `Ops(offline=True)`, for the proof only: `unshare --net`, the key files from /dev/null, empty request folders, and the scratch run's ledger and GPU0 want flags. THE ONE COMMAND never sets it. | `Ops` :487, `env_instance` :128, `ns_script` :161/:176, `in_ns` :188 |

**Found while testing the fix:** tmux hangs up a pane at once (SIGHUP, "Pane is dead (signal 1)") when its process
points stdin, stdout and stderr all away from the pane's terminal. The tee keeps the terminal open, as the 11:08
design's tee would have.

## The proof

1. **The reproduction:** as above.
2. **Tests** (`tests/package/test_lean_ops.py`):
   - `TheStartupCommand` :333. The tmux command stays under 1,000 bytes even for a 200-character run folder, while the
     start file is over tmux's limit. Offline mode means `--net`, both keys masked, empty request folders and no
     candidates file.
   - `TheStartupErrorsAreKept` :375. These start real tmux sessions, `pipeline_leantest_t_*`, offline. A service made
     to fail at a mount leaves `mount: .../ns/live_main: mount point does not exist.` and `ENDED (exit 32)` in the run
     log, and its pane is kept until `restore`. tmux's own "command too long" also lands in the run log.
   - `ThePreflight` :533. A kept dead pane fails the launch's check.
3. **Must-fail credit:** 10 mutations, each run after an unmutated control that passed. All 10 were caught
   (`MUTATIONS_startup.txt`):
   - the old inline command, caught twice: by the length test and by the real-tmux test;
   - tmux's output discarded;
   - no 40-line log tail;
   - no tee;
   - no remain-on-exit;
   - has-session instead of the pane's state, in `services_ready` and in the launch's check;
   - offline without `--net`;
   - offline reading the live key.
4. **Initialization** (`STARTUP_PROOF.txt`, from `python3 -B tests/package/lean/startup_proof.py --run-dir
   /var/tmp/pp_leantest_run`, 11:38 to 11:39 ET):
   - **How they were started:** both services were started by `lean_ops.start` itself, not a copy: all 8
     preconditions PASS, the ledger-init on the scratch ledger, the release copy and seeds, then each service after its
     ledger check. `lean_ops.services_ready` waited for them.
   - **lockcheck:** `python3 scripts/lean/serve.py lockcheck --sleep 5`. Its own heartbeat is
     `RUN/heartbeats/lock_precheck.json`: 6 passes, 0 served. Its log line: "lock pre-check: decoder_sha 9326604699a7,
     root /var/tmp/pp_leantest_run/lock_precheck".
   - **scorer:** its own heartbeat is `scorer.json`: 3 passes, 0 served. Its log line: "pin-stage scorer: ... |
     scorer_sha edd54964a5ab".
   - **Inside each service's namespace:**
     - `.env` and `config/api_keys.json` are both `/dev/null`.
     - Each service has its own network namespace containing only `lo`, with 0 packets, 0 inet sockets and 0 socket
       file descriptors.
     - After 25 more seconds of idle passes, that namespace's own counters still read 0: Ip.OutRequests,
       Ip.OutNoRoutes, Tcp.ActiveOpens and Udp.OutDatagrams. No connection was attempted.
   - **Scratch ledger:** spent $0.0000, held $0.0000. The request folders stayed empty.
   - **GPU:** no GPU process was ours. The compute apps were the same two production processes before, during and
     after.
   - **After `restore`:**
     - restore printed PRODUCTION AS BEFORE;
     - both sessions were gone and no process was left;
     - `/home/ultron/pp_spend` was unchanged (same sha256);
     - `/tmp/pulse_gpu0.want` was unchanged.
5. **The launcher's `--dry-run`** on the pushed heads, pp-lean `787d3b754` and lean-release `7f4317bb0`
   (`DRYRUN_startupfix.txt`):
   - 20 PASS;
   - 3 FAIL, all three needing a live `start`: the lockcheck up, the scorer up, and production's BEFORE file, which
     `start` writes;
   - it wrote nothing: `find -newer` found no change in `/home/ultron/pp_lean_run` or `/home/ultron/pp_spend`.
6. **Suites:**
   - pp-lean at `32e1a6629`: 53 files, 0 failing, 1,191 passed.
   - lean-release, unchanged: 89 files, 1,257 passed, 13 failing. These are the same 13 files that fail on the
     unmodified release branch (the B3 section below explains them).

## What still cannot be verified without a live run

- **The live key and the network.** The proof masked both. The live key's bind mount itself was exercised yesterday:
  `ns_check` binds it, then masks it. Both services started with no key readable and opened no network socket.
- **Real requests.** Lock decodes take GPU0 through the normal lease, and the scorer's local model runs on GPU0. Nothing
  was asked of either service.
- **The build, render and delivery,** and the 6000 s timing.

## Left as found, or flagged

- **The 11:08 run folder.** `/home/ultron/pp_lean_run` was only read; its run log is copied into the repo. The retry
  reuses the folder as it is: `start` moves its release copy to the pushed head and writes a new run log. Moving the
  folder aside first also works.
- **The ledger.** `/home/ultron/pp_spend/SPEND_D20261124.json` came from the 11:08 ledger-init ($0.0000). The retry's
  ledger-init adds a second init record (`init_again`).
- **Not changed, because it is outside the startup fix: the GPU0 want flags.** The experimental lockcheck and scorer
  share production's GPU0 want-flag folder (`/tmp/pulse_gpu0.want`) and service names (`lock_precheck`,
  `stand_alone_scorer`). When idle, each removes its own name's flag, which production's service of the same name may
  just have set. This affects only timing (Whisper may give GPU0 back a few seconds later), never spend. The proof used
  a scratch folder for these flags.
- **If a service fails to start again,** its own error is in `RUN/logs/<name>.log`, and the last 40 lines are in the
  run log.

**Withdrawn at 12:08 ET.** This section's claim that one authorized retry could proceed was wrong: the retry's scorer
ended at its first request (the section above). The proof here served no request, so it never reached that check.

# Build 172: BLOCKERS 1-3 (Nov 25)

(Its `lean_ops.py` line numbers are at `f71e01c85`. The startup fix above moved them.)

Prepared for the owner's order of 08:38 ET Nov 25. **Nothing was run live.** No launcher, driver, render, service
start or stop, GPU job, or model call happened. Every check below is offline, and no vendor was asked. **End to end: NOT
DEMONSTRATED.**

The code is at `pp-lean f71e01c85` and `lean-release 7f4317bb0`, both pushed. On pp-lean that is 36078c31a, then the
service wait d19eb2846, the run lock bacfc1d22 and restore's whole-argument matcher f71e01c85; `pipeline/spend_ceiling.py` is the same
file on both branches. The evidence files are in `docs/audits/lean/ops172/` (`*_B123.txt`, `ASSETS.json`).

## THE ONE COMMAND

```
cd /home/ultron/worktrees/pp-lean && python3 -B tests/package/lean/lean_ops.py run --build-no 172 --deadline-s 6000
```

- **What it does, in order:** ledger-init, start the two experimental services, wait for each service's own first
  heartbeat (at most 180 s, else refused), preflight, build, render, delivery, restore.
- **Detached:** it returns at once and prints its pid and `LOG: /home/ultron/pp_lean_run/logs/run_<UTC>.log`. It runs in
  its own session with stdin from `/dev/null` and no terminal. Every stage also gets stdin from `/dev/null`.
- **To stop it early:** `kill -TERM <pid>`. It stops the running stage first, then restores.
- **`--dry-run`:** prints every check and every command, executes nothing and creates nothing
  (`DRYRUN_run_B123.txt`). On the pushed heads 18 checks pass. The 5 that fail all need a live `start`: the release
  copy, the initialized ledger, each of the two services (session and its own heartbeat), and production's BEFORE
  snapshot.
- **The deadline:** 6000 s is this one build's exception. The code's default stays 2700 s, the product's target. The
  build's share is 1929 s; the render gets what is left, which is at least the slowest measured render (3951 s); the
  delivery gets 120 s.
- **Start it before 19:24 ET.** The whole run must end inside the spend day (21:10 ET), or its preflight refuses.

## THE ACTUAL MAXIMUM FINANCIAL EXPOSURE: $2.38, not $1.50

**$2.38 = $1.50 − carried-in spend at launch ($0.00 now) + $0.88 for one call.**

- **$1.50 − carried-in is hard.** Every reservation by the builder, the lock service and the render is checked
  against it, together with production's live spend (re-read at every reservation). Nothing past it is sent to a
  vendor. Carried-in now: $0.00, because production has spent nothing since 21:10 ET Nov 24.
- **+ $0.8824: one call billing above its reservation.** Only one paid call is in flight at a time, and the first bill
  above its reservation stops every paid call, so at most one call can overshoot. The worst case is an xAI vision
  call:
  - input at the enforced bound: 65,536 bytes + 2 images = 77,736 tokens at $5/M;
  - output at the largest ever recorded for that model: 28,400 tokens at $25/M;
  - that is $1.0987 at list, minus its $0.2162 reservation.
- **Assumptions:**
  1. No xAI call uses more output + reasoning tokens than the most ever recorded for its model: vision 28,400,
     Grok 4.20 20,944, the sign-off's grok-3-mini 1,422. **Nothing enforces this.** xAI bills reasoning outside the
     output limit (B2). Beyond it, each extra 1,000 tokens of that one call adds $0.025 at list.
  2. Prices are the code's list prices (`pipeline/model_providers.json`). The 919 recorded Grok bills came to 9-15 % of
     list on their own token counts. Scribe is counted at the code's $0.012 a minute of audio, because ElevenLabs
     reports no cost; its bills are not read back.
  3. The voice is outside the dollars: at most 1,000 characters, inside the plan's included characters. The preflight's
     2,000-character floor stays.
  4. Ingestion is separate and not in this figure. Restore prints it. Its last 24 h, to 09:28 ET: $0.2985 in 648
     calls, all Heimdall (in-house).
  5. Production is frozen. A production charge that lands during one of our calls is not covered (B1).
- **Without one call in flight** (as of yesterday), build 171 had up to 5 paid calls in flight at once. The same
  residual would then be 5 × $0.88 = $4.41.

## B1: the ledger first; production's spend at every reservation

**What changed**
- `pipeline/spend_ceiling.py` (both branches):
  - `init_day` (:262) creates the spend day's ledger and seeds it with the carried-in spend.
  - `before_reserve` (:448) runs at every reservation of every program, under the ledger's lock. It refuses when the
    ledger is missing or not initialized (:453), so a service that starts first charges nothing.
  - `production_parts` / `refresh_production` (:308, :367): production's three day ledgers are re-read, read only, at
    every reservation: the production builder's router ledger (its in-flight reservations included), the
    integrator's outside ledger, and the audits. Each carried-in figure only rises.
  - `production_running` (:430): a production build or render not started by our launcher STOPS the ledger. That
    means `proof_ledger.py`, `build_and_record.sh`, `pulse_check_run.sh`, `run_fresh.py` or `daily_producer.py` run
    as a script, with no `lean_ops.py` among its ancestors. The same check is a launch precondition (`lean_ops.py:574`).
- `pipeline/providers.py:1066`: the router's ceiling mode calls the same `before_reserve`.
- `tests/package/lean/lean_ops.py`:
  - `start` runs the ledger-init first (`ledger_init` :672, called :720);
  - each service checks the ledger again just before it starts (`ledger_ready` :692, called :749);
  - the preflight refuses any test-only override in the environment (:571), and the services' tmux command unsets
    them (:196).
- `tests/package/lean/ceiling_seed.py:117`: the seed calls `init_day`, using spend_ceiling's own reading of
  production.

**Ingestion (B1 c).** Restore prints one separate line, never added to the $1.50:
`INGESTION (separate, NEVER in the $1.50): $… in … calls between … ET, from
/home/ultron/worktrees/pp-ingest/data/editorial/ingest/queue.sqlite (table calls); by back-end …; outside vendors …`
(`ingest_line` :863). It reads a copy of the database and its write-ahead log, so sqlite never opens the live files.
The test shows the live folder gains no file.

**What stays uncovered.** Production is frozen and was not modified, so it never reserves in our ledger. A production
charge that lands between one of our reservations and its settle is seen only at our next reservation. How large
that can be:
- **Production's builder:** reserves in its own ledger before each call. We re-read that ledger, so its in-flight
  calls already count.
- **Production's lock service:** charges only for requests the production builder writes. All 84 are answered; the
  last at 13:10:47 ET Nov 24.
- **A production build or render:** must start first, and our next reservation then stops on it.

So the uncovered amount is whatever a production program bills after starting during one of our calls, before that
call settles. The longest recorded paid call was 222 s (vision). That amount is bounded only by production's own caps.
Nothing schedules production: 89 crontab lines, none naming a build or render, and no user timers.

**Offline evidence**
- `python3 -B -m pytest -q tests/package/test_ceiling.py`: 29 passed. The new tests:
  - no paid call before init;
  - production's spend growing after init refuses the next call;
  - the outside ledger and a production reservation count;
  - an unreadable or unknown production ledger refuses;
  - a production render appearing stops every program, but one started under the launcher does not;
  - what counts as running a build.
- `python3 -B -m pytest -q tests/package/test_lean_ops.py`: 31 passed. The new tests:
  - start initializes before the first service;
  - a service is refused without an initialized ledger;
  - the preflight refuses a production run;
  - the ingestion line.
- lean-release, `python3 -B -m pytest -q pipeline/test_lean_ceiling.py`: 8 passed. Before init, each of the four
  charge sites is refused before its request.

**Cannot be verified offline**
- production's real timing;
- the live ledger under real load.

## B2: an enforceable maximum: what a vendor can bill

**From the code and the recorded replies**, xAI does not cap reasoning with the output limit:
- **Grok 4.20** (`max_tokens`, sent at most 12,000 since ruling 121, Nov 16): two replies on Nov 23 used 12,949 and
  14,411 output + reasoning tokens. They billed $0.0337 and $0.0373.
- **xAI vision, grok-4.7** (`max_output_tokens`, sent 8,000): 31 of 53 replies passed it, up to 28,400 tokens
  (×3.55), billed $0.1752.
- **The render's sign-off, grok-3-mini** (`max_tokens` 500): completion 143 + reasoning 1,279 = 1,422 tokens. Its
  outside-ledger line, Nov 24 03:43 UTC, shows prompt 474 and total 1,896.

No other parameter in the code caps xAI's reasoning. `reasoning_effort` goes only to OpenAI, and Heimdall takes its own `reasoning` effort; no xAI call sends either. So **no xAI call has
an enforceable per-call maximum.** For the other paid calls:
- **Scribe** has one: the audio seconds are known before sending.
- **The voice** has one, in characters.
- **Gemini, GPT and Claude** never reached their limits on record. Whether their thinking counts inside those limits is
  not established offline.

**What changed**
- `pipeline/providers.py:114-131` and `:1601`, ceiling mode only: a paid call whose prompt + system exceeds 65,536
  bytes is not sent. The bound is 1.76 × the largest recorded prompt (37,231 bytes); a token is at least one byte.
  The same applies to more than 2 images, or an image over 2,000,000 bytes. A call refused this way has no answer,
  which is never a pass.
- `spend_ceiling.py:205` and `providers.py:1070-1076`: **one paid call in flight** across the three programs.
  - A second call waits outside the lock for the first to settle, at most 600 s.
  - The router re-checks the deadline after the wait (`providers.py:1092`, `:1609`).
  - The voice, which holds characters and no dollars, never waits.
- **The output limits are unchanged.**
  - For xAI, a lower limit would bound only the visible answer, not the reasoning, so it creates no maximum, and it
    could cut a verdict. A cut reply fails strict parsing (`providers.call_parsed`): no verdict, never a pass or a
    fail.
  - The other models never reached their limits.

**The table** (`tests/package/lean/exposure_172.py`, output in `EXPOSURE_B123.txt`; outputs include reasoning)

| Call | Back-end | Limit sent | Largest recorded output | Largest input (tokens) | Bound now |
|---|---|---|---|---|---|
| step A, the line-up verdicts | Grok 4.20 | 12,000 | 15,913 (Nov 13, before the cap); 14,411 since | 8,413 | input ≤ 65,536 bytes; output: none enforceable |
| fidelity | Grok 4.20 | 12,000 | 14,220 | 1,387 | the same |
| coherence: hook, joins, clips-alone | Grok 4.20 | 8,000-12,000 | 7,353 | 1,567 | the same |
| speaker / exclusion / takeaway | Grok 4.20 | 8,000-12,000 | 5,229 / 1,331 / 6,488 | 2,641 | the same |
| vision (contact sheet) | xAI grok-4.7 | 8,000 | 28,400 | 3,934 | input ≤ 65,536 bytes + 2 images; output: none enforceable |
| the render's sign-off | xAI grok-3-mini | 500 | 1,422 | 474 | output: none enforceable |
| step A 3rd leg, clips-alone 2nd leg | Gemini 2.5 Pro | 8,000 | 6,627 | 6,398 | input bound; the limit stands |
| Plan B only | GPT-6.1 / Claude Opus 5.5 | 4,000 / 16,000 | 3,357 / 1,678 | 2,591 / 4,424 | input bound; the limits stand |
| the second ear, the lock check | Scribe | audio seconds | n/a | n/a | exact, known before sending |
| the voice | ElevenLabs TTS | characters | n/a | n/a | ≤ 1,000 characters a build |

**One package**: 3 segments, `package.completion_reserve`, heimdall_first, under the ceiling.

| Reservations | One package needs | Fits in $1.50? |
|---|---|---|
| today's (calibrated) | $0.8651 | yes; the search room is $1.50 − carried-in − $0.8651 = $0.6349 at $0 carried in |
| full list, no calibrated fraction | $2.3340 | no |
| each call's input bound and largest recorded output, full list | $5.6418 | no |

**The exact constraint.** One package needs 6 xAI calls: 2 vision, 2 step-A appeals, the value verdict and the
coherence verdict. The hook and join verdicts are Grok's alone (rulings 115 and 117) and come before it. Under a hard
$1.50 at list price, one package fits only if each xAI call's output + reasoning were capped at 6,425 tokens. No such
cap is in the code or the recordings.

**The owner's choice.** Both numbers:
- **HARD: guaranteed $1.50 − carried-in, and no video.** Every call is reserved at a true maximum. Only Scribe and the
  voice have one, so every xAI call is refused. Then there is no hook rating (Grok alone, ruling 115), no join verdict
  (ruling 117), no package, and nothing to render. There is no search to make smaller.
- **CALIBRATED: $2.38 − carried-in, under assumption 1.** This is THE ONE COMMAND's mode.
  - Reservations stay as ruled: Grok at 25 % of list, vision at 60 %, the sign-off at $0.05.
  - One call in flight; the first overshoot stops everything.
  - On record no bill passed these reservations: none of the 895 Grok bills (ruling 123's check), and vision's
    largest was $0.1752 against $0.178.
- **The time cost of one call in flight:** at least +226 s, measured on build 171's 48 paid calls (970 s of calls
  over 744 s of wall time, at most 5 at once). Build 171 took about 1237 s. The build's share in 6000 s is 1929 s.

**Offline evidence**
- `test_ceiling.py::TestOnePaidCallInFlight` and `::TestTheInputBound`.
- `exposure_172.py` prints every figure above from the code and the recordings.

**Cannot be verified offline**
- the vendors' own limits;
- whether Gemini's, GPT's or Claude's thinking counts inside their limits;
- any bill above the largest recorded.

## B3: assets, no delivery past the deadline, automatic restore

**(a) Reference assets**
- **What the inventory is.** `docs/audits/lean/ops172/ASSETS.json` lists every untracked file the renderer and its QA
  gates read at run time: 58 required and 2 optional. It was made by `tests/package/lean/assets_inventory.py`
  (09:21 ET), from the render's run-time reads traced through `pulse_check_run.sh` → `run_fresh.py --pinned`, each
  with its reader as file:line.
- **What is in it:**
  - the outro masters and their conformed copies (sha256 pinned by `run_fresh.APPROVED_OUTRO`);
  - the brand mark and 34 music tracks;
  - the v2f voice manifest (if missing, the voice stage HOLDs);
  - 3 channel avatars;
  - the face models (`det_10g.onnx`, sha256 pinned by `face_scrfd`; blaze_face);
  - whisper large-v3 and medium, resemblyzer, the haar cascade, and two fonts;
  - optional: `data/signoff_history.json` and `data/yt_cookies.txt` (stat only, never opened).
- **Where they are.**
  - Inside `/home/ultron/protocol_pulse`, under `brand/`, `video_pipeline_v3/`, `references/`, `segment_v1/` and
    `data/`. None is under `pipeline/`, `scripts/` or `.git`, the three folders the namespace takes from git alone.
  - Outside the tree, under `~/.insightface`, `~/.cache/huggingface`, `~/.local/lib/python3.10/site-packages` and
    `/usr/share/fonts`.
  - Not files, and checked elsewhere: the pin, post-live sources, Ollama's gemma3:27b, and the ledger.
- **How the renderer gets them.** Its namespace mounts the pushed copy at `/home/ultron/protocol_pulse`. Every other
  top-level folder is an overlay whose lower layer is the live folder, read only, so untracked files resolve. Files
  outside the tree are the host's.
- **The preflight.** `launch` (and `run`) checks every file by path and size, and the pinned ones by sha256, and
  refuses if any is missing or different (`assets_check`, `lean_ops.py:523`). Right now: 58 present, all pinned hashes
  equal.
- **Proved inside the namespace.** `python3 -B tests/package/lean/ns_check.py --run-dir <scratch> --sha 7f4317bb0
  stat` builds the render's own namespace (`lean_ops.ns_script`) from the pushed release head in a scratch folder, with
  no network (`unshare --net`) and the key file masked by `/dev/null`. Result: **60 files, 0 missing or of another
  size**; the key file reads as size 0 (`NS_STAT_B123.txt`).
- **The 13 release test files** that failed in a fresh worktree, run inside that namespace (`NS_13_B123.txt`):
  - **4 now pass**, because their reference data resolves: `test_check_medley_reference` (16 passed),
    `test_check_reference_manifest` (7), `test_fresh` (27, 1 skipped) and `test_pulse_20261110_mustfail` (33, 1 skipped).
  - **9 still fail. None of them is a file the render reads.**
    - **The GPU, which the test session hides by design** (the render itself takes GPU0 under its lease):
      - `test_g20_signoff`, `test_g3b_majority`: whisper medium;
      - `test_word_diff`, 4 of its 5: whisper large-v3;
      - `test_safe_frame_colour`: nvenc;
      - `test_edge_words`: `run_isolated.prerender_clips` encodes with `h264_nvenc` (`run_isolated.py:348`); its source
        (`references/pulse_preview_2026-11-11`) is present.
    - **The local Ollama, unreachable because this check has no network:** `test_preflight` (`/api/ps` on
      127.0.0.1:11434). The render's own preflight reaches it on the host's network.
    - **Media that no longer exists on this machine** (those runs' `sources/` folders are gone from the live tree):
      `test_word_diff`'s 5th test (`runs/pinned_20261111_172202_replay_cut1329/sources/36HPi9UZPOc.mp4`) and
      `test_ruling73` (`runs/pinned_20261113_221758/sources/DcUbBkyeh9M.mp4`). These are old runs' sources, not build
      172's.
    - **The same failure with or without any reference data,** in a fresh worktree too: `test_dec10_edges`
      (`KeyError: 'cut_lo'`) and `test_replay` (a temporary `edl.json` its own setup never writes).
  - Two files were first stopped by SIGTERM from this session's own test runs (restore's old substring scan, now
    fixed: see (c)). They were run again and fail as listed.

**(b) No delivery past the deadline.** The check sits immediately before the delivery (`lean_ops.py:975`), on the
launch's one clock. With less than 30 s left, nothing is sent, because the one measured delivery took 18 s. The line
then reads DEADLINE_STOPPED at "delivery". Fake-clock tests:
- a render that ends at 2730 s of 2700: no delivery;
- 20 s left: no delivery;
- 40 s left: delivered, and handed exactly 40 s.

**(c) Automatic restore**
- `run` (:1105) restores in its `finally` on every exit path. SIGTERM, SIGINT and SIGHUP become a stop that first
  ends the running stage's whole session (`_exec` :434, `kill_session` :375). Nothing interrupts the restore.
- A detached guard (`guard` :1055, started by `spawn_guard` :1035 in its own session) watches the launcher by pid and
  start time:
  - if the launcher disappears without its restore marker (SIGKILL), the guard stops the stages it left
    (`STAGES.json`) and restores;
  - if the launcher is still running 300 s past the deadline, the guard sends SIGTERM, then SIGKILL a minute later.
- Restore prints PRODUCTION AS BEFORE or what differs, then the ledger, then the ingestion line.
- Between `start` and the launch, `run` waits for each service's own first heartbeat (`services_ready` :654), at most
  180 s, and refuses (then restores) if one does not come. Until now the launch's check accepted any fresh
  heartbeat file for both services; it now reads each service's own file.
- **One run at a time** (`run_lock` :1087). `run` first takes an exclusive lock on `RUN/RUN.lock`, held for its life.
  The command typed twice therefore refuses the second copy at once, with nothing started and nothing restored;
  its restore would otherwise stop the live run's services. The guard restores a killed launcher only if it can
  take that lock.
- **Restore stops only our processes, matched on whole arguments** (`ours_argv` :250, `leftovers`
  :265). Until today it sent SIGTERM to any process whose command line merely contained `lean-ns` or
  `scripts/lean/serve.py`. During today's test runs that stopped two of my own offline namespace checks (their
  wrapper was named `lean-ns-check`); in a live restore it could have stopped any shell that mentioned those names.
  It now matches our wrapper (`lean-ns` as a whole argument) and our services (`scripts/lean/serve.py` as the
  interpreter's script) only, and every test replaces the scan: a test never signals a real process
  (`OnlyOurProcesses`).
- **Tests** (`test_lean_ops.py::TheExitPaths`): each path is run as its own process, with a real `sleep` as the build
  stage in a session of its own:
  - SIGTERM, SIGINT and SIGHUP: exit 128+signal, the stage killed, restored, PRODUCTION AS BEFORE;
  - SIGKILL: the guard restores and the stage is killed;
  - refusal and error: restored;
  - success and deadline: restored once.
  - a second run while one is live: refused, nothing started, nothing restored (`OneRunAtATime`).
  - `TheDetach`: the child is its own session leader, its stdin is `/dev/null`, it has no tty, and the printed LOG
    path exists.

**Cannot be verified offline**
- a real render in the namespace;
- how the real render ends under `timeout`;
- the guard against a real hung launcher.

## Must-fail credit, and the suites

- **Mutations: 22, all killed.** Each mutation is made in a scratch copy after its unmodified control passed
  (`MUTATIONS_B123.txt`):
  - B1: init skipped (3 ways); production read once; a production run not stopping; every process taken for ours;
    the preflight ignoring a production run;
  - B2: two calls in flight (2 ways); the input bound off;
  - B3: sizes not compared; the delivery check removed; no restore in finally; a signal leaving the stage; the guard
    not restoring; restore leaving a killed launcher's stage; not detached; a run crossing the spend day; the launch
    not waiting for the services; one service's heartbeat standing in for the other's; a second run without the
    run lock; restore's leftover scan matching substrings again.
  - One control failed on the first pass. The previous mutation's test had left an orphaned stand-in render running,
    which correctly read as production. The test now ends whole process groups, and the two mutations on that test
    were rerun: control passed, both killed.
- **pp-lean:** 53 files, 0 failing, 1186 passed, each judged by its exit code with the network blocked (`SUITES_pp-lean_B123.txt`).
- **lean-release:** 89 files, 1256 passed, 13 failing: the same 13 files as at the unmodified release head
  (`RELEASE_BASELINE.txt`).

---

# Build 172: the three operational requirements (R1 ceiling, R2 routing, R3 deadline)

*(Nov 24's report, kept as written. Its file:line references are at pp-lean db38b58e7 / lean-release cf2035dad; Nov 25's changes above move some of them.)*

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
  session `book_terminal_r2` on Nov 24 (`book_terminal_r3` on Nov 25: since then `lean_ops.book()` discovers the names at every use, never hard-coded; one Claude Code pane, no service). No command names any of them; the namespace keeps
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
