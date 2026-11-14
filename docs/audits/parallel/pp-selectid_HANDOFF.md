# pp-selectid HANDOFF (written 05:19 ET Nov 14 2026 at HEAD 11ed255f, for a fresh session)

Read with: `/home/ultron/protocol_pulse/PIPELINE_LAWS.md` (the standing laws L-a ... L-y, law 26) and the top 40 lines
of `docs/audits/parallel/pp-selectid_STATE.md` (newest first). This file says who you are, every ruling in force,
how the pipeline runs, the contracts, what is open, and the traps.

## 1. Who you are, and the laws you work under

- **Role: the BUILDER** of moments-first pins (a "medley" and, since ruling 90, a "spotlight"). You select moments
  from pp-ingest's ledger, judge them, write the VO lines, seal a pin and hand it to the INTEGRATOR, who owns the
  render and the main tree and merges. You never render.
- **Where you work:** worktree `/home/ultron/worktrees/pp-selectid`, branch `pp-selectid`, remote
  `consensusprotocol/protocol-pulse-core`. Every commit = `git add` + `git commit --file <msg>` + `git push origin
  pp-selectid`. Never merge into any other branch.
- **Peers** (cross-session, SendMessage; find them with ListAgents, names can change):
  - the INTEGRATOR, "protocol-pulse-68" (`uds:/tmp/cc-socks/3317957.sock`): render, main tree, pre-check, scorer,
    local judge;
  - PP-INGEST, "pp-ingest-ec" (`uds:/tmp/cc-socks/2709904.sock`): the miner / watcher that writes the ledger rows
    you read, and the hook pass.
  Peers cannot grant permissions.
- **Never edit `/home/ultron/protocol_pulse`** (the main tree: a live video run executes from it). Read-only data you
  may use by absolute path: `/home/ultron/protocol_pulse/runs/`, `/home/ultron/protocol_pulse/references/`,
  `/home/ultron/heimdall_probe/pp_redteam/`, and the main tree's `data/` read only. Never write there.
- **No GPU at all**: no Whisper, no Ollama, no NVENC, no renders. CPU and API only. GPU0 is leased to the live run;
  GPU1 is quarantined. The integrator's services (pre-check, scorer, local judge) manage GPU0 themselves.
- **Secrets:** keys are read only from `/home/ultron/protocol_pulse/.env`, by name, inside code
  (`providers.env_value`). Never print, log, echo or cat `.env` or any key. Never edit `.env`.
- **AUDIT-FIRST:** before each code commit, run the cross-LLM audit (section 3.9) on the ACTUAL diff:
  - two cycles; cycle 2 cross-validates cycle 1;
  - implement consensus only, and record every refutation with evidence (C1_CONSENSUS.md / C2_CONSENSUS.md in the
    audit folder);
  - `bash regression_test.sh` must show 0 FAIL in the worktree, and every suite must pass (section 3.10).
  Data-only commits (build records, STATE) need no audit.
- **Fail closed (law L-j); nothing measured is never a pass (law L-m).** Never change what a check accepts in order
  to make something pass.
- **No cron changes.** Nothing is sent to Telegram or published by you. No manual tasks for PBX. Triple-verify before
  calling anything done.
- **Questions to the ORCHESTRATOR** go on **STATE line 1, in CAPITALS**. STATE line 1 is ONE physical line,
  prepended (newest first). After every build it carries:
  - the ruling-76 (d) counts;
  - the spend: "SPEND (ruling 48): $X of $20.00; stop at $16.";
  - "COST OF THE LAST SEALED PIN (<sha8>): $T TOTAL / $O OUTSIDE";
  - when nothing seals, the three nearest and ruling 95's next attempt.
  Generate times with `date` INSIDE the command that writes them (`TZ=America/New_York date +%H:%M`).
- **Conventions:**
  - `python3 -B`; `git --no-optional-locks` for reads;
  - develop code in a scratch copy (section 3.9), never in the worktree directly;
  - new `test_*` files need `git add -f` (.gitignore has `test_*`);
  - never commit `*.lock` files or main-tree files;
  - never put `-f` and `push` in one shell command (the pre_bash hook blocks it);
  - never `pkill -f` a pattern your own shell's command line contains (use `ps -eo pid,args` + awk on argv).
- **Standing order:** the FIRST pin that passes your gates AND the pre-check goes to the integrator immediately (send
  the pin path, story_id and package_sha256).

## 2. Rulings in force, 28 to 97 (one line each; the file / function that carries it)

Numbers are the orchestrator's, shared with the other sessions. "Not the builder's / no record" means nothing in this
branch carries it and it never reached this session (addressed to another session, or a one-off report).

- 28 "Quiet after the cut" is G17a's own measure: the first onset comes after the first 10 ms hop, so nothing of a trimmed word opens the clip. It is used by ruling 33's trim check: `sentence_law.trimmed_onset`. (The hook's 80 ms lead itself is G17a / D1: `pipeline/hook_onset.py`, `package.hook_onset_for`, `_can_open`.)
- 29, 30, 31 Not the builder's / no record.
- 32 The ledger's OUTWARD snap of a row to whole sentences (≤ 20 s, no caption speaker marker; the added words judged as usual): `ledger_build.reanchor`, `SNAP_MAX_S`. Ruling 90 reuses it: `spotlight.snap`.
- 33 Part 2: ONE leading TRIM_WORDS word (but/and/so/well/now/yeah) may be trimmed; a `~trim` variant carries trimmed_leading/untrimmed_start; (a) the trimmed cut opens in quiet; (b) the scorer affirms the trimmed text; (c) judged like any moment: `package.trim_variant`, `hook_onset` "trim" record, `package_pin.trim_problems`, `stand_alone.trimmed_opener`.
- 34 The topic test is the miner's about-Bitcoin screen (`eligibility.BTC_SCREEN`); the hook passes it itself, the medley names Bitcoin once; `btc_screen` is sealed: `package.no_topic`, `stand_alone_check`, `package_pin.screen_problems` (medley + spotlight).
- 35 T9's sentence count is RETIRED as a rule (recorded only): `eligibility.py` T9.
- 36 Not the builder's / no record.
- 37 A question may end the HOOK only (never a clip); a question hook takes no bridge after it: `eligibility` T8/T9, `package.ly_shape`.
- 38 L-v 2's audio window: 4.0 s before the clip; a measured ≥ 0.7 s pause also opens a clip: `transcript_truth.PAD_BEFORE_S`, `PAUSE_MIN_S`.
- 39 L-v 2's canonicaliser may match a short run of recognised words for a number ("sixty-eight"): `transcript_truth` (CANON_RUN).
- 40 Not the builder's (pp-ingest's second-model flag check).
- 41 Up to 8 judged line-ups per BUILD over every angle; the search may spend $3 vendor-reported / $10 estimate / 2400 s per build; ruling 5's $1.50 / 15 min is per package: `package.LINEUPS_PER_BUILD`, `SEARCH_*`, `build.over_budget` / `package_over`.
- 42 Use ruling 33 part 2 (the trim) now: standing as 33 / 94 (a).
- 43 A report (the cause of "no line-up"): answered, no standing rule.
- 44 A failed off-vendor step-A re-screen removes THAT clip only (out for good, with its reason); the line-up's other clips stay and it is re-lined: `package.build` (doomed set).
- 45 The off-vendor step-A re-screen runs on every cuttable clip BEFORE the angle step: `package.second_screen` (ruling 88 (c) now: Grok confirms Heimdall's passes).
- 46 Angles go to Heimdall first, Grok only on Heimdall failure, 5 min a writer call: `tests/package/proof_ly.WRITERS` (deepseek -> qwen -> Grok, which replaces the config's angle_write chain), `package.WRITER_DEADLINE_S`.
- 47 A report: answered.
- 48 The spend ledger: the vendors' own reported dollars (the price-table estimate where a vendor reports none), reservations at the upper bound; no build starts at the stop: `providers.Router` (_settle), `tests/package/proof_ly.py` (`SPEND_LY.json`), the driver's refusal.
- 49 (a) retired by 56 (`scorer_pending` kept only so old pins recompute); (b) at most ONE trimmed clip per line-up / pin: `package.TRIMMED_PER_LINEUP_MAX`, `package_pin.TRIMMED_PER_PIN_MAX`.
- 50 A report: answered.
- 51 Not the builder's / no record.
- 52 The hook's job: scroll / alone / setup, each 1-5 (the gating rating is 61's): `package.HOOK_QUESTION`, `HOOK_PARTS`.
- 53 The same speech re-posted by a second channel is ONE moment (time-aligned ≥ 0.80, or equal text); the original publisher's is kept: `package.reposted_once`.
- 54 A clip's placement limits are told to the angle proposer exactly as `lineup_for` applies them: `package.placement`.
- 55 Every missed Heimdall deadline is recorded (model, prompt size, seconds): `docs/audits/parallel/pp-selectid_HEIMDALL_DEADLINES.jsonl` (the Router's `deadline_log`).
- 56 The integrator's pin-stage scorer verdicts (the render's own clip scorer, read only, fail closed); "seal only what it affirms"; this build's candidates go to its next pass: `package.scorer_verdicts`, `scorer_pass`, `with_verdict`, `package_pin.affirmed_verdict` / `scorer_problems`.
- 57 A line-up holding a clip ≤ 24 h old is preferred; an unreadable publish time counts as the oldest (its 72 h window is superseded by 76): `package.FRESH_H`, `fresh_key`.
- 58 EVERY usable candidate is screened at step A (the 24 cap retired), paid once (cached by moment + text + context + version), batches in parallel: `package.prescreen`, `STEP_A_CACHE.json`.
- 59 HOOK FIRST: every cleared, cuttable opener is rated in one batched call (cached); only ≥ 4 opens; no hook means the build stops before any angle: `package.hook_ratings`, `can_open`, `HOOK_CACHE.json`.
- 60 Scorer verdicts are kind "moments", no event; affirmation = the score alone ≥ 3.5: `package.SCORER_KIND`, `stand_alone.affirmed(moments=True)`.
- 61 The hook's OWN-job rating = min(scroll, alone), cached, never re-asked per line-up; "sets up what follows" is judged at the hook -> clip_01 join: `package.HOOK_OWN`, `hook_own`.
- 62 A clips-alone failure of only the LAST clip: the line-up is judged without it: `package.last_clip_only`.
- 63 JOINS BEFORE SWAPS: a new order of the same clips is tried before any swap: `package.reorder`.
- 64 At most `per` angles per hook, an angle for each passing hook: `package.allot`.
- 65 ONE more write of a failed line alone (title or caption); (b) the caption placeholder fallback: `package.write_line`, `caption_fallback`.
- 66 A PASSED LINE-UP IS KEPT: the candidates registry (open; resting 6 h, then once more with fresh writes; closed); amended 17:02: up to TWO fresh writes of the failed line only: `pipeline/candidates.py`, `tests/package/proof/CANDIDATES.json`, `package.load_candidate`, the driver's `run_due`.
- 67 ATTESTED-TEXT RE-SEAL: the second recogniser's text, sealed with an "attested" record, when it differs from the decode inside the allowed class: `pipeline/attest.py`, `tests/package/reseal_attested.py`, SEALED_LATER "attested".
- 68 The render's own lock (ruling 17) is asked BEFORE any write is paid and before a pin is sealed; no verdict stops the search: `pipeline/lock_precheck.py` (check / apply / pin_problems), the driver's `lock_check`.
- 69 The speaker attribution reads the caption turn markers and addresses by name (one turn holds the clip): `pipeline/speakers.py` (captions / turn_of / attribute).
- 70 The pin-stage VISUAL check: one contact sheet per clip; findings sealed as FLAGS; a third-person still with a negative claim may not be the HOOK; not measured is never a pass: `pipeline/visual_pin.py`, `VISUAL_CACHE.json`, gate "visual".
- 71 Not the builder's / no record.
- 72 The pre-check compares the second recogniser with the lock (adopt_spoken inside the allowed class): `lock_precheck`.
- 73 The render's own cut placement joins the pre-check (a span the render cannot cut holds): `lock_precheck` (RULES).
- 74, 75 Not the builder's / no record.
- 76 (a) A clip only while its source is ≤ 12 h old on the RENDER clock (expired for good); (b) never reuse delivered speech (`same_speech`) anywhere; (c) the render clock checks again; (d) STATE line 1 carries 4 counts (inside 12 h, cleared, cuttable, hooks ≥ 4): `package.usable` / `expired` / `same_speech`, `package_pin.window_problems`, `candidates.expire`, the driver's `ruling_76`.
- 77 Not the builder's (pp-ingest's media purge of `runs/*/sources`).
- 78, 79 Not the builder's / no record.
- 80 pp-ingest's hook rows (role_hint "hook") feed the pool: read through the ledger.
- 81 Not the builder's / no record.
- 82 The second / off-writer step-A chain, deepseek -> glm -> qwen at 120 s a call; an out-of-contract answer moves on; an outage is never a verdict; extended at 20:33 to every one-Heimdall-model step: `package.SECOND_VERDICT_*`, `providers.call_parsed`, `model_providers.json` roles.
- 83 (a) A call abandoned at its deadline is booked at its PROMPT tokens (a late vendor figure replaces it); (b) the cap is $20 vendor-reported, stop and tell at $16: `providers._within` / `abandon` / `_late`, `proof_ly.LY_LIMIT_USD` / `LY_STOP_USD`.
- 84 The pre-check's adopt class: fillers the second recogniser hears, plus ONE function-word disagreement per span (the lock keeps the decode's word and records the other); two or more hold: `attest.class_84`, `lock_precheck.decide`.
- 85 Heimdall first behind a switch: per-type lists, the two-family rule inside Heimdall, Grok last, completing with xAI answering nothing; 85.1 the replay is DONE (`tests/package/proof/replay85/TABLE.md`); 85.4's $0.05 target is superseded by 97: `providers` (ROUTINGS, chain, call_parsed), `model_providers.json` routing, `tests/package/replay85.py`.
- 86 The Grok SHADOW on pins sealed under heimdall_first (recorded, never deciding) until 3 pins in a row show no decision-changing difference: `providers` (shadow), `tests/package/shadow86.py`, `SHADOW86.json` (streak 0: no pin sealed under it yet).
- 87 PLAN B: "down" = 15 min with no Heimdall family answering; a probe every 2 min, one claimed per slot; back after 3 answers in a row; Plan B chains Grok -> Gemini -> OpenAI / Anthropic (probed); one outside family means step A's second verdict comes from the integrator's GPU0 judge; every switch goes to STATE line 1 and the evidence file; shared with pp-ingest's watcher: `pipeline/heimdall_health.py`, `providers` (Plan B chain, probe thread, LocalJudgeBackend, GeminiBackend), `HEIMDALL_HEALTH.json`.
- 88 Folded into 96: (a) fidelity / exclusion on Heimdall; (b) the hook moved, step C stayed Grok first (the full table); (c) step A Heimdall first, Grok confirms the passes in 8-clip batches; (d) clips-alone / coherence Grok, glm out; (e) qwen never decides coherence or step C: `model_providers.json` routing.heimdall_first, `package.first_bounds` / `_second_bounds`.
- 89 A report from records (answered on STATE: no clip has a followable join after L6H7538ogGs). STANDING: "Build nothing for [a two-clip Short] until I rule." "Keep building as new uploads arrive."
- 90 THE SPOTLIGHT (LAW): one moment, one speaker, one channel, 12-35 s of clip (snapped outward to 13.7 s, never padded); ≥ 4 on the hook's own job AND the ALONE scorer ≥ 4; step A from both families; the visual check clean; ≤ 12 h; never a delivered span; one per channel per ET day; at most one closing line; the sign-off + credits with that channel; 28-50 s; title ≤ 8 words; caption in house style; the first comment in PBX's format; built after the medley search (no medley, or a moment no medley used); the 22:58 note: L-u's 20 s is a medley rule, the spotlight's ceiling is 35 s: `pipeline/spotlight.py`, `package_pin` (SPOTLIGHT_GATES ...), the driver (`SPOTLIGHT_PIN.json`, `SPOTLIGHTS.json`).
- 91 The closing line must earn its place: default NO line; one write and ONE value verdict off the writer's family (four clear yeses, ≤ 12 words), plus fidelity and context; anything less means no line: `spotlight.value_verdict` / `package_for`. Its MEDLEY half (the same value verdict on a medley's takeaway: lose it to the no-voice shape only if the clips meet the seconds, else one rewrite) is NOT BUILT: open item 1.
- 92 Spotlight sources: conversation, not reaction. A measured layout verdict of "conversation" or "first_hand" is required; caption markers can only make it stricter (a marked episode under 1.0 turns a minute is not a conversation); unmeasured never passes. 23:50: KEEP 1.0, re-measure after 20 spotlights' worth of episodes: `spotlight.source_test` / `layout_for` / `episode_turns`, `LAYOUT_CACHE.json`.
- 93 DEC-12d per CLIP, never by channel name: the visual check's question 4. A ticker or crawl, or a lower third / bug that is not whole in the 16:9, that the 9:16 would cut mid-word, or that covers the speaker, holds the clip in any role; a whole static strap / bug is eligible and flagged: `eligibility.layout_ok`, `visual_pin` (visual-2, `layout_block`, `burned_block`), `package.build`, `spotlight.clean_visual`.
- 94 Hook openers, medley and spotlight: (a) a conjunction / reply opener opens as ruling 33's trim variant (a clean cut, and the scorer affirms it); (b) I / me / my / we / us / our / you / your open freely; a third-person or demonstrative opener needs the scorer's affirmation: `pipeline/stand_alone.py` (the integrator's 409188ef, BYTE FOR BYTE), `eligibility` T8, `package._can_open` / `hook_trim` / `third_opener` / `scorer_pass`, `spotlight.pool`.
- 95 With no medley and no spotlight, STATE line 1 carries the three nearest and the next attempt (the newest conversation upload's publish time + its mining state): `spotlight.next_attempt`, the driver's `res["next_attempt"]`.
- 96 ROUTING, FINAL until re-measured: the table in section 3.6. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement: `model_providers.json` routing.heimdall_first (+ its `ruling_96` note).
- 97 The honest cost is about $0.20 a sealed pin, $0.18 outside; never chase the $0.05 target by moving a verdict the table says should stay. (a) The non-reasoning Grok fails the bar (`tests/package/proof/replay97/`); (b) confirmed; (c) Grok already confirms 8 to a call: STATE 01:41 ET.

## 3. The pipeline as it runs

### 3.1 The build (one command; medley first, then the spotlight)
```
cd /home/ultron/worktrees/pp-selectid && python3 -B tests/package/proof_ledger.py --routing heimdall_first \
  --since 2026-11-13T03:01:09Z --delivered \
  tests/package/proof/fresh_20261112_050611/MOMENTS_PIN.json \
  tests/package/proof/fresh_20261112_050611/MOMENTS_PIN_LY.json \
  tests/package/proof/fresh_20261111_213954/MOMENTS_PIN_BATCH_B1.json \
  tests/package/proof/ledger_20261113_073738/MOMENTS_PIN_LEDGER.json \
  tests/package/proof/ledger_20261113_183302/MOMENTS_PIN_ATTESTED.json \
  tests/package/proof/ledger_20261113_215708/MOMENTS_PIN_LEDGER.json > <log> 2>&1 &
```
- `--routing heimdall_first` is REQUIRED. `pipeline/model_providers.json` still has `routing.mode` "today", so a
  build that omits the flag runs the old chains. Every build since 01:41 ET Nov 14 has run heimdall_first.
- The last build is 01:41 ET Nov 14 (`ledger_20261114_064132`, commit 604ed5f5): no medley, no spotlight, $0.00.
- The last sealed and delivered pin is `moments-ledger_20261113_215708-13949b7c` (built 16:57 ET Nov 13, approved
  17:14 ET; $0.24 total / $0.23 outside). It is the last `--delivered` above.
- Every pin you seal and the integrator delivers is ADDED to `--delivered` (its spans and speech are never used again,
  ruling 76 b).
- The default `--work-dir` is `<proof_ly.SCRATCH>/lv2`, a hard-coded OLD session's scratchpad (see section 6).
- The record goes to `tests/package/proof/ledger_<UTC stamp>/`: inputs.json, package.json (everything, including
  `spotlight` and `next_attempt`), package.log, step_a.json.
- A medley pin is MOMENTS_PIN_LEDGER.json; a spotlight pin is SPOTLIGHT_PIN.json, and a row in
  `tests/package/proof/SPOTLIGHTS.json`.
- Commit each build's record (data, no audit) with STATE, `CANDIDATES.json`, the caches, `SPEND_LY.json` and new
  `tests/package/fixtures/replies/*` recordings.
- A build that judges nothing new costs nothing: every verdict is cached or recorded.

### 3.2 The ledger watcher (re-create it: the old session's background shells died with it)
Rebuild whenever the ledger moves. Save this as `<your scratchpad>/rows_now.py`; run it from the worktree. It prints
"rows word-ready videos":
```python
import sys
from datetime import datetime, timezone
for p in ("pipeline", "tests/package", "tests/select_by_id", "tests/moments"):
    sys.path.insert(0, p)
import ledger_build as LB
now = datetime.now(timezone.utc)
rows, rep = LB.rows(datetime.fromisoformat("2026-11-13T03:01:09+00:00"), now, horizon_h=12.0)
wp, wrep = LB.word_pass_index(LB.WORD_PASS)
print(f"{len(rows)} {wrep.get('ready')} {len({r['video_id'] for r in rows})}")
```
Watch it in the background (Bash `run_in_background`); it exits, and wakes you, when the word-ready count changes:
```
S=<your scratchpad>; B0=$(timeout 120 python3 -B $S/rows_now.py); while true; do
  N=$(timeout 120 python3 -B $S/rows_now.py 2>/dev/null)
  if [ -n "$N" ] && [ "$(echo $N | cut -d' ' -f2)" != "$(echo $B0 | cut -d' ' -f2)" ]; then
    echo "CHANGED: was '$B0' now '$N' at $(TZ=America/New_York date +%H:%M)"; break; fi; sleep 300; done
```
At handoff (05:20 ET Nov 14) the reading was "62 1450 5". It was "231 1450 13" at 00:11 ET: the row and video counts
fall as videos pass 12 h, so the watcher keys on word-ready, which has not moved since 00:11. BTC Sessions
nvEftLDdab4 expired at 04:37 ET. pp-ingest also
messages you when new hook rows land.

### 3.3 The candidates registry (ruling 66)
`tests/package/proof/CANDIDATES.json`, seeded from every build record (`pipeline/candidates.py`): a line-up that
passed the clips-alone verdict is tried again (open -> resting 6 h -> one try with fresh writes -> closed). Expired
clips close it (ruling 76).

### 3.4 Caches (all shared by every build; only PARSED verdicts are ever cached)
- `tests/package/proof/STEP_A_CACHE.json`: step A, keyed by moment id + text sha + the sha of the exact context +
  STEP_A_VERSION. A verdict is reused from any back-end off the writers.
- `tests/package/proof/HOOK_CACHE.json`: hook ratings, keyed by `"<moment_id>:<text sha>:<HOOK_VERSION>"`, then by
  back-end.
- `tests/package/proof/VISUAL_CACHE.json`: visual-2 records, keyed by moment : start-end : VERSION : digest. A hit is
  used only on the same sheet bytes, from `<work_dir>/visual/`.
- `tests/package/proof/LAYOUT_CACHE.json`: ruling 92's layout verdict, keyed by moment : sheet sha : LAYOUT_VERSION.
  No moment has reached that step yet, so the file does not exist until the first one does. `SPOTLIGHTS.json` (the
  first spotlight) and `SHADOW86.json` (the first pin sealed under heimdall_first) are also created on first use.
- The router's recordings: `tests/package/fixtures/replies/<2 hex>/<sha256>.json`, keyed by sha256 of [role, backend,
  prompt, max_tokens, seed, system]. In a live run, the same bytes are served from the recording at no cost, marked
  `cached` (the same model's reply). `replayed` means served offline, and that is never deliverable. `router.reject(r)`
  deletes a reply that is out of contract.
- The L-v 2 audio windows live in `--work-dir` (default under proof_ly.SCRATCH, "lv2").

### 3.5 Spend (rulings 48 / 83)
- `tests/package/proof/SPEND_LY.json`: usd_reported + usd_unreported_estimate. CAP $20.00, STOP AND TELL at $16.00;
  no build starts at $16.
- NOW: $13.83 (at 05:19 ET Nov 14; $7.94 vendor-reported + $5.89 estimated where a vendor reports none).
- The audit drivers' calls are NOT on this ledger (they print their own upper-bound estimate); the replays' are.

### 3.6 Routing: ruling 96 (heimdall_first; the driver passes `--routing heimdall_first`)

| type (role:kind) | order |
|---|---|
| step A first screen (context_verdict:step_a_first), and any context_verdict with no kind of its own | glm -> deepseek -> qwen -> Grok (step A: 2 clips, 120 s a call) |
| step A confirm (context_verdict:step_a_second) | Grok (8-clip batches, no deadline) -> qwen -> glm -> deepseek |
| hook rating (coherence_verdict:hook) | qwen -> glm -> deepseek -> Grok |
| fidelity_verdict | glm -> qwen -> Grok |
| exclusion_verdict | glm -> deepseek -> Grok |
| step C (context_verdict:step_c) | Grok -> glm -> deepseek |
| clips-alone (coherence_verdict:clips_alone) | Grok -> qwen -> deepseek |
| coherence (coherence_verdict:coherence) | Grok -> deepseek |
| step B (viewer_takeaway), speaker_verdict | Grok -> deepseek -> glm -> qwen |
| visual_check (and ruling 92's layout) | xai_vision:grok-4.7 -> Heimdall qwen -> nemotron-3.5-super-vl (the role's chain) |
| writes (angle_write) | `proof_ly.WRITERS`: Heimdall deepseek -> qwen -> Grok (verdicts avoid the writer's vendor AND family) |

- `proof_ly.chains()` builds every chain the driver uses. It drops the FROZEN legs (`local:`, `anthropic:`,
  `openai:`, `openai_stt:`): OpenAI and Anthropic have been out of credit since 20:32 Nov 13, and local is GPU0. A
  role with no routed list keeps its `roles` chain minus those legs.
- Plan B's lists (`routing.plan_b`, via `proof_ly.plan_b_chains`) keep Gemini, OpenAI and Anthropic, which are
  tried and never assumed, plus `local_judge:`.

- qwen as step A's third family is the builder's addition; the orchestrator was asked to strike it if unwanted.
- Under heimdall_first each Heimdall family is its own vendor ("heimdall/<family>"); `providers.gateway()` keeps
  "heimdall".
- Grok's self-agreement on the same prompt (the bar for any model swap): step A 85 %, clips-alone 79 %, fidelity 60 %.

### 3.7 Plan B (87) and the shadow (86), now
- `tests/package/proof/HEIMDALL_HEALTH.json` (shared with pp-ingest's watcher, which notes its real Heimdall calls
  and probes with who="pp-ingest probe"): mode heimdall_first, no switch so far. The last answer was at 09:16 UTC
  (04:16 ET) Nov 14.
- The file is live state, written every few minutes by both sessions under its flock. It is UNTRACKED on purpose:
  never commit it, its `.lock` or the `*.json.lock` files.
- The probe claims its slot (`heimdall_health.probe_due`).
- Every switch appears on STATE line 1 in capitals.
- The shadow: SHADOW86.json streak 0. The first pin sealed under heimdall_first is judged twice (Grok in shadow); the
  side-by-side is SHADOW86.md in that build's folder.

### 3.8 The integrator's services you call (read their outputs only)
- **Lock pre-check** (rulings 68/72/73/84):
  - requests: `tests/package/proof/lock_requests/`;
  - results: `/home/ultron/protocol_pulse/data/lock_precheck/results`;
  - DECODER `c705b20ed800` (`lock_precheck.DECODER`); RULES "ruling 17 + ruling 72 + ruling 73 + ruling 84".
  - The decoder sha changes whenever the integrator changes `pinned.py`: they tell you; update DECODER and its test.
    Results under an old sha are never read.
- **Clip scorer** (the ALONE scorer; rulings 56/60/94):
  - its verdicts: `/home/ultron/protocol_pulse/data/stand_alone_scorer/verdicts/latest.json`;
  - its requests (this branch writes them): `docs/audits/parallel/pp-selectid_SCORER_CANDIDATES.json`. The
    integrator's tmux `pipeline_pp_scorer` watches that file:
    - a new `generated_at` starts a new pass, and moments already rated are reused;
    - it yields GPU0 to any render;
  - gemma3:27b, threshold 3.5, scorer_sha `91d75457ceec`. It changes whenever the main tree's `stand_alone.py` or
    `story_semantics.py` change; old verdicts are then unreadable until re-rated (the integrator restarts
    pipeline_pp_scorer).
- **Local judge** (Plan B only, ruling 87):
  - requests: `tests/package/proof/judge_requests/`;
  - results: `/home/ultron/protocol_pulse/data/local_judge/results`;
  - judge_sha `c62a1e12088c`.

### 3.9 Scratch copies and the audit driver (they lived in the old session's scratchpad; the driver is Appendix A)
- **Scratch copy:**
  - copy `config pipeline references utils regression_test.sh` and `tests/*` into `<scratchpad>/devNN`;
  - in it, `git init`, then commit a BASE holding the worktree-HEAD version of EVERY file you will edit (`git -C
    <worktree> show HEAD:<f> > <f>`). `git add -N` new files;
  - edit, then run the suites there.
- **The audit driver:** a small Python script that wraps `utils/cross_llm_audit.py`:
  - it loads the module with importlib, sets `BASE` = worktree and `GOSPELS` = `docs/gospels`;
  - `FEATURE_MAP[F] = ("PULSE_SENTENCE_LAW_GOSPEL.md", "pp-selectid")`;
  - `CUSTOM_REVIEW_TASKS[F]` = the text of `docs/audits/parallel/pp-selectid_audit_<LABEL>/QUESTION.txt`;
  - it writes `git diff HEAD -- FILES` of the scratch copy to `<audit dir>/C<n>_STEP.diff` and sets
    `EXPLICIT_FILES[F]` to it;
  - cycle 1 prompt = `m.build_audit_package(F)`; cycle 2 prompt = `m.build_cycle2_prompt(F, package, {cycle-1
    reviews}, C1_CONSENSUS.md)`;
  - it posts the prompt to three reviewers in parallel threads and writes `C<n>_<reviewer>.md`.
- **The three reviewers:**
  - grok-4.20-0309-reasoning at `https://api.x.ai/v1/chat/completions` (key `XAI_API_KEY_MEDLEY`, max_tokens 30000,
    temperature 0);
  - qwen/qwen3.8-27b and z-ai/glm-5.3-flash at `https://api-staging.heimdallm.com/api/v1/chat/completions` (key
    `HEIMDALL_API_KEY`, `"reasoning": {"effort": "none"}`, max_tokens 16000 / 24000);
  - system message "You have no tools and no internet access. Answer in ONE message.";
  - timeout 1800 s. Keys by name inside code only.
- Every past audit's QUESTION / reviews / consensus are under `docs/audits/parallel/pp-selectid_audit_*` (models for
  a new one, e.g. `_0230`).

### 3.10 The suites (all must pass; 19 suites, 518 tests at 11ed255f)
`for f in tests/package/test_*.py tests/moments/test_*.py tests/select_by_id/test_*.py tests/eligibility/test_*.py
tests/providers/test_*.py pipeline/test_stand_alone.py; do python3 -B -m pytest -q -p no:cacheprovider "$f"; done`
then `bash regression_test.sh` (26 PASS, 0 FAIL, 5 WARN).

## 4. Contracts with the integrator (it imports this worktree's `pipeline/package_pin.py` LIVE)

- **Medley pin:**
  - `package_pin.to_pin` / `write_pin` -> `MOMENTS_PIN_LEDGER.json`, schema `protocol_pulse.pinned_story.v1`,
    `machine_cuts`;
  - `moments_package` {shape "medley", edl_vo {intro, bridges [{text, after_clip}]}, signoff_expected, title,
    caption, gates, btc_screen, ...};
  - required gates: `REQUIRED_GATES + MEDLEY_GATES`, each exactly PASS and replayed false;
  - `package_sha256` = `seal()`. Any NEW sealed field goes in `SEALED_LATER` (present only when carried), so every
    earlier pin recomputes (a test checks every proof pin). Tell the integrator before changing `seal()`.
- **Spotlight pin** (agreed 22:44 ET Nov 13):
  - shape "spotlight", ONE segment (role "hook");
  - edl_vo {"intro": null, "bridges": [], "closing": a line or null};
  - signoff_expected names that channel; `first_comment` is the WHOLE comment, printed verbatim with nothing
    appended;
  - gates `SPOTLIGHT_GATES`, plus `CLOSING_GATES` when closing is non-null;
  - `seal(..., shape="spotlight", first_comment=...)`: their exact readiness call; `package_pin.pin_seal(pin)` does
    it from a pin. The closing, the kind and the comment are sealed for the spotlight only;
  - the render side is the integrator's L-ab (merged fd5c9cc4).
- **Attested text:**
  - ruling 67: `attest.py`, `reseal_attested.py`, MOMENTS_PIN_ATTESTED.json;
  - ruling 84: the pre-check adopts inside `attest.class_84`; `lock_precheck.apply` seals the spoken text with its
    "attested" record; `LP.pin_problems` re-checks at the pin.
- **SPEAKERS_ATTESTED:** `tests/package/proof/ledger_20261113_183302/SPEAKERS_ATTESTED.json` (orchestrator 15:29
  (2)) sits beside a kept pin. The speaker is attested, NOT re-sealed; the tagging and the description read it. New
  pins seal the speaker record per segment (`speakers.attribute_package`, `package_pin.speaker_problems`).
- **First comment** (ruling 90):
  - one or two casual lines (written, gated by house style + fidelity), a blank line, "Credits 🧡", a blank line,
    then the handles;
  - handles come ONLY from `/home/ultron/protocol_pulse/pipeline/channels.json` `x_handle` (verified; empty = none);
    an untagged name is recorded with why (`spotlight.credits`, `package_pin.first_comment_text`).
- **Visual flags:**
  - `visual_pin.sealed()` seals version, measured, flags, third_person, on_screen_text, lower_third, burned_in,
    backend, replayed, sheet {name, sha256, times};
  - the sheet image is copied beside the pin;
  - flags are third_person, on_screen_text and (ruling 93) burned_in.
- **stand_alone.py** must stay the integrator's file byte for byte (now 409188ef, sha256 14f30115...); pp-ingest's
  tests compare its word sets.
- **Delivery:** the pin goes to the integrator the moment it seals, with path + story_id + package_sha256. GPU0 renders
  it.
- **pp-ingest imports `pipeline/heimdall_health.py` LIVE too** (ruling 87). Its watcher loads the module ONCE at start
  and has run 11ed255f since 02:57 ET Nov 14 (pp-ingest 4f805fcf).
  - Its load check needs `note`, `mode`, `probe_due` (with `who`), `probe_result`, `HealthUnreadable`, `STATE` and
    `MODES`, with MODES holding plan_b and one up mode.
  - Any change to that file: send pp-ingest the commit sha after the audit. It reads the diff and restarts its
    watcher.
  - The contract: probe_due stamps the slot, saves and returns True as one step under the flock. A claimed slot that
    sends no probe_result stays spent.

## 5. Open items, in priority order

1. **Ruling 91's MEDLEY half is NOT BUILT:** the value verdict on a medley's takeaway (off the writer's family, four
   clear yeses, ≤ the takeaway's word cap). If it fails, the medley falls back to L-y's no-voice shape only if its
   clips meet the seconds; otherwise the takeaway may be rewritten once. Build it in package.build's takeaway path
   (reuse `spotlight.value_verdict`'s contract), test it, audit it two cycles, commit.
2. **Standing:** build on every ledger change; seal the first medley or spotlight that passes; send it to the
   integrator at once; STATE line 1 after every build (counts, spend, last pin cost, and the three nearest +
   ruling 95's next attempt when nothing seals).
3. **Waiting on the ORCHESTRATOR** (asked on STATE in capitals):
   - (a) the COHERENCE GAP: with xAI down and deepseek writing, coherence has no family. glm as the last fallback, or
     fail closed (asked 22:13 Nov 13);
   - (b) qwen as step A's third filter family: strike or keep (01:41 Nov 14);
   - (c) pp-ingest's miner Plan B (paid models, or queue and wait) is open with the orchestrator; pp-ingest queues
     meanwhile.
4. **Re-measure ruling 92's 1.0 turns-a-minute line** after 20 spotlights' worth of episodes, and tell the
   orchestrator. A data point is on record: Stephan Livera's interview podcast measured 0.61.
5. **Re-run the replay** (`tests/package/replay85.py`) monthly or when a Heimdall model changes (ruling 96).
6. **Ruling 97 is answered** (STATE 01:41): nothing to build unless the orchestrator rules otherwise.
7. **Done tonight:**
   - rulings 85-88 + 96 (125e7381, audit 0108);
   - 90-92 (8bf5f278, audit 2322);
   - 93 (85c3895f, audit 0003);
   - 94-95 (2f081cba, audit 0041);
   - pp-ingest's R12 (11ed255f, audit 0230);
   - the decoder c705b20ed800.
   No pin has sealed since `moments-ledger_20261113_215708-13949b7c` (16:57 ET Nov 13). The pool is empty of
   spotlight sources: the newest conversation upload, BTC Sessions nvEftLDdab4, expired at 04:37 ET Nov 14. The next
   real attempt needs a new conversation upload, mined. The FIRST action of a fresh session is to start the watcher
   (3.2) and run one build (3.1) to read the live counts.

## 6. Known traps (one line each)

- A passing line-up was thrown away when a later gate failed: ruling 66's registry keeps it, and only a failing clip is dropped (44).
- An outage cached as a verdict: only a PARSED answer is ever cached; a failed / late / out-of-contract call is "no verdict", never a pass, never stored.
- The 24-candidate cap starved step A: retired (58, `PRESCREEN_N = None`).
- Identical-prompt replay: the router serves the recorded reply to the same bytes, so a "fresh" try needs a different `seed`, and a bad reply must be `router.reject`ed.
- `proof_ly.SCRATCH` and `tests/package/run_given_package.py`'s SCRATCH hard-code the OLD session's scratchpad (`/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/9e163ea0-e85c-404b-9baf-67af8f2ebf8b/scratchpad`).
  - The build's default `--work-dir` is `<SCRATCH>/lv2`: 190 MB of L-v 2 audio windows and the visual contact sheets under `lv2/visual/`. VISUAL_CACHE.json records sheet paths there.
  - While it exists, keep using it.
  - If it is gone, pass `--work-dir <your scratchpad>/lv2`. Media is fetched again (CPU and network). A cached visual verdict is reused only when the rebuilt sheet has the same bytes; otherwise it is a paid Grok vision call.
  - Moving SCRATCH is a code change: audit it.
- `tests/package/proof/judge_requests/` holds one untracked request (22:27 ET Nov 13). It was the end-to-end test with the integrator's local judge and was answered. Leave it.
- `model_providers.json` `routing.mode` is "today": only `--routing heimdall_first` gives ruling 96's lists.
- pp-ingest's watcher keeps the heimdall_health it loaded at start: a change to that file reaches it only after pp-ingest restarts (section 4).
- Heimdall deepseek returns HTTP 429 at about 12 calls in flight, and a 429 storm can mark the back-end down for a whole build: keep a build's parallel calls to one family small.
- glm answers out of contract on clips-alone / coherence (ruled out of both); for audits give glm 24k tokens and effort "none".
- The integrator imports `package_pin.py` live: an always-present new seal field broke every earlier pin once (use SEALED_LATER / spotlight-only fields).
- The decoder sha and the scorer_sha move with the integrator's `pinned.py` / `stand_alone.py`: update DECODER, and expect a scorer re-rate.
- A scratch copy's git base must include every file you edit, or that file's change never reaches the audited diff (also `git add -N` new files).
- Never swap files in a scratch copy while suites run in it.
- `pkill -f <pattern>` matching your own shell kills the shell (exit 144): use `ps -eo pid,args` + awk.
- `-f` and `push` in one command are blocked by the pre_bash hook: push in its own command.
- New `test_*` files are git-ignored: `git add -f`.
- The stop hook flags OTHER sessions' main-tree files: never commit them.
- A module-level name used inside `package.build` without a local import (a NameError the suites missed): after a refactor, run a real build.
- The local-judge test helper once answered an OLD request and a test hung 40 min: answer only unanswered requests.
- STATE line 1 must be ONE physical line; typed times drift, so take them from `date` in the writing command.
- Snapped spotlight spans often fail step A on REFERENT_OUTSIDE (a sentence added before points back); trimmed hooks often fail the clean-cut test (a co-articulated word, ruling 94 a).
- DEC-12d is per clip (ruling 93): never hold a channel by name; `has_chyron` only orders the check.
- The 12 h window (ruling 76) drops supply sharply at its edge (about 50 moments at 01:00): builds early in a fresh window find the most.
- `usable()`'s default ceiling is the medley's 20 s; the spotlight passes `seg_max=35`.
- Grok disagrees with itself 15-40 % of the time on the same prompt: judge any model swap against that baseline (replay85's TABLE.md), never against 100 %.

## Appendix A: the audit driver (copy to `<your scratchpad>/audit_<LABEL>.py`, set LABEL / DEV / FILES)

This is the driver that ran audits 2322, 0003, 0041, 0108 and 0230.
1. Write `docs/audits/parallel/pp-selectid_audit_<LABEL>/QUESTION.txt`: what changed, the rulings, and what to
   attack.
2. Run `python3 -B audit_<LABEL>.py 1`. Read the three reviews and write `C1_CONSENSUS.md` (implemented / refuted with
   evidence).
3. Fix the code in DEV, then run `python3 -B audit_<LABEL>.py 2 C1_CONSENSUS.md`. Write `C2_CONSENSUS.md`.
4. To re-ask failed reviewers only: `... 2 C1_CONSENSUS.md glm-5.3-flash`.
```python
import importlib.util, json, subprocess, sys, threading, time, urllib.request
from pathlib import Path

LABEL = "HHMM"                                          # the audit's label (ET time it starts)
WT = Path("/home/ultron/worktrees/pp-selectid")
AUD = WT / "docs" / "audits" / "parallel" / f"pp-selectid_audit_{LABEL}"
DEV = Path("<your scratchpad>/devNN")                   # the scratch copy: its git base = worktree HEAD of every file
FILES = ["pipeline/....py", "tests/.../test_....py"]   # every file the change touches (check `git diff --stat HEAD`)
ENV = "/home/ultron/protocol_pulse/" + "." + "env"      # read by name inside code only; never printed
sys.path.insert(0, str(WT / "pipeline"))
from providers import env_value  # noqa: E402

HEIMDALL = "https://api-staging.heimdallm.com/api/v1/chat/completions"
REVIEWERS = {
    "grok-4.20-0309-reasoning": {"url": "https://api.x.ai/v1/chat/completions", "key": "XAI_API_KEY_MEDLEY",
        "body": {"model": "grok-4.20-0309-reasoning", "max_tokens": 30000, "temperature": 0}, "price": (5, 25)},
    "qwen3.8-27b": {"url": HEIMDALL, "key": "HEIMDALL_API_KEY",
        "body": {"model": "qwen/qwen3.8-27b", "max_tokens": 16000, "temperature": 0,
                 "reasoning": {"effort": "none"}}, "price": (3, 15)},
    "glm-5.3-flash": {"url": HEIMDALL, "key": "HEIMDALL_API_KEY",
        "body": {"model": "z-ai/glm-5.3-flash", "max_tokens": 24000, "temperature": 0,
                 "reasoning": {"effort": "none"}}, "price": (3, 15)},
}
spec = importlib.util.spec_from_file_location("cross_llm_audit", WT / "utils" / "cross_llm_audit.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.BASE, m.GOSPELS = WT, WT / "docs" / "gospels"
FEATURE = f"pp-selectid-{LABEL}"
m.FEATURE_MAP[FEATURE] = ("PULSE_SENTENCE_LAW_GOSPEL.md", "pp-selectid")
m.CUSTOM_REVIEW_TASKS[FEATURE] = (AUD / "QUESTION.txt").read_text()


def review(name, prompt, out):
    r = REVIEWERS[name]
    body = dict(r["body"], messages=[
        {"role": "system", "content": "You have no tools and no internet access. Answer in ONE message."},
        {"role": "user", "content": prompt}])
    req = urllib.request.Request(r["url"], data=json.dumps(body).encode(), headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + (env_value(ENV, r["key"]) or "")})
    t0 = time.time()
    try:
        j = json.loads(urllib.request.urlopen(req, timeout=1800).read())
        text = j["choices"][0]["message"].get("content") or ""
        u = j.get("usage") or {}
        usd = (u.get("prompt_tokens", 0) * r["price"][0] + u.get("completion_tokens", 0) * r["price"][1]) / 1e6
        head = (f"# {name} ({r['body']['model']}) {round(time.time() - t0)} s finish="
                f"{j['choices'][0].get('finish_reason')} usage in {u.get('prompt_tokens')} / out "
                f"{u.get('completion_tokens')} usd~{usd:.3f} (upper-bound price)"
                + (" EMPTY" if not text.strip() else "") + "\n\n")
    except Exception as e:
        head, text = f"# {name}: FAILED {type(e).__name__}: {str(e)[:200]}\n\n", ""
    out.write_text(head + text)
    print(out.name, head.strip()[:200], flush=True)


def main():
    cycle = int(sys.argv[1])
    names = sys.argv[3].split(",") if len(sys.argv) > 3 else list(REVIEWERS)
    diff = subprocess.run(["git", "diff", "HEAD", "--", *FILES], cwd=DEV, capture_output=True, text=True,
                          check=True).stdout
    (AUD / f"C{cycle}_STEP.diff").write_text(diff)
    m.EXPLICIT_FILES[FEATURE] = [str((AUD / f"C{cycle}_STEP.diff").relative_to(WT))]
    package = m.build_audit_package(FEATURE)
    assert f"### File: {m.EXPLICIT_FILES[FEATURE][0]}" in package, "the package holds no code"
    if cycle == 1:
        prompt = package
    else:                                   # cycle 2 cross-validates cycle 1's reviews and consensus
        prev = f"C{cycle - 1}_"
        c1 = {p.stem[3:]: p.read_text() for p in sorted(AUD.glob(prev + "*.md"))
              if p.stem not in (prev + "PROMPT", prev + "CONSENSUS") and "FAILED" not in p.read_text()[:200]
              and "EMPTY" not in p.read_text()[:300]}
        prompt = m.build_cycle2_prompt(FEATURE, package, c1, (AUD / sys.argv[2]).read_text()).replace(
            "## ORIGINAL CODE (same code as Cycle 1)", "## THE CODE NOW: the FIXED diff")
    (AUD / f"C{cycle}_PROMPT.md").write_text(prompt)
    print(f"prompt {len(prompt.encode())} bytes; diff {len(diff.encode())} bytes", flush=True)
    ts = [threading.Thread(target=review, args=(n, prompt, AUD / f"C{cycle}_{n}.md")) for n in names]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    print(f"CYCLE{cycle}_DONE", flush=True)


if __name__ == "__main__":
    main()
```
- Run it in the background. A cycle took 1-14 min in audits 2322-0230; glm is the slowest. glm has failed with HTTP 503
  and IncompleteRead, and has hit its 24k-token cap (finish=length). Record any of these in the consensus file and
  re-ask that reviewer alone.
- Its calls are not on SPEND_LY.json. It prints an upper-bound estimate, $0.14-0.74 a cycle for the three
  reviewers so far; add it to the commit message.
- After the audit:
  - copy the scratch copy's files to the worktree;
  - re-run the suites and `bash regression_test.sh`;
  - `python3 -m py_compile` every changed .py;
  - commit with `--file`: the audit folder, the code and the tests (`git add -f` for new test_*). Push in its own
    command.
