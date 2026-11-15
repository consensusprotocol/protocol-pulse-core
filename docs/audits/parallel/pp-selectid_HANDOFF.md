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
  - RULING 107 (2), from 20:20 Nov 14: reviewers go Heimdall-FIRST, two Heimdall families (qwen + glm). Grok joins
    only as the THIRD reviewer, when the first two disagree (one finds a critical or high point the other does not)
    or when one of them is down. An audit of a change UNDER 60 CHANGED LINES is ONE reviewer set, two cycles, capped
    at $0.30. Record each review's vendor-reported cost (Heimdall usage.cost, xAI cost_in_usd_ticks), not only the
    list-price upper bound;
  - implement consensus only, and record every refutation with evidence (C1_CONSENSUS.md / C2_CONSENSUS.md in the
    audit folder);
  - `bash regression_test.sh` must show 0 FAIL in the worktree, and every suite must pass (section 3.10).
  Data-only commits (build records, STATE) need no audit.
- **Fail closed (law L-j); nothing measured is never a pass (law L-m).** Never change what a check accepts in order
  to make something pass.
- **No cron changes.** Nothing is sent to Telegram or published by you. No manual tasks for PBX. Triple-verify before
  calling anything done.
- **Questions to the ORCHESTRATOR** go on **STATE line 1, in CAPITALS**, and always with a default: see "How
  questions work" at the end of this section (ruling 106). STATE line 1 is ONE physical line, prepended (newest
  first); a block the orchestrator asks for (texts, tables) may follow it under the same timestamp
  (`state_block.py`). After every build it carries:
  - the ruling-76 (d) counts;
  - the spend: "SPEND (ruling 48): $X of $20.00" (the orchestrator, 13:02 Nov 14: stop at $19 and say so on line 1
    in capitals; never start a build that would end over $20);
  - RULING 107 (3), from 20:20 Nov 14: "ALL-IN TODAY: $x (builds $a, audits $b, other $c)" beside it. Builds are
    SPEND_LY.json's ruling-48 total since 00:00 ET. Audits are the day's audit folders: the vendor-reported cost
    where the driver kept it, else the list-price upper bound, labelled as such. Other is the exam or any other
    ledger of yours;
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

### How questions work (RULING 106, orchestrator 20:20 ET Nov 14: standing, for all three sessions)

PBX, 20:08 Nov 14: "pls fix that weakest part of how we are running this". The orchestrator's checks arrive late,
and a session that stops at a question loses hours: about five on Nov 14, two of them with a finished spotlight
waiting. So NO SESSION WAITS ON THE ORCHESTRATOR:

- **(a) Every question carries its default.** Write it as: the question; your RECOMMENDED answer;
  `DEFAULT IN 20 MIN: <what you will do>`. If there is no answer in 20 minutes, ACT ON THE DEFAULT and say so on
  STATE line 1. Never stop work on an unrelated item while a question is open.
- **(b) What a default may be:** anything that publishes nothing, installs no schedule, touches no cron, spends
  inside the caps, and can be undone. That covers a build, a render, a review-only or candidate delivery to PBX's
  Telegram, and an audited merge on our branches. When two readings of a law are possible, the default is the
  STRICTER reading for integrity (L-s, L-v, L-u, a number or name hold) and the reading that DELIVERS for taste and
  process. A finished video that passes every gate is always launched and delivered as a candidate. If one
  integrity point is open, it is rendered and delivered on the REVIEW path with that point stated in the caption,
  never left unrendered.
- **(c) What still waits for a human:** publishing, a schedule, cron, a spend cap, loosening an integrity gate,
  deleting what is not ours. For those, do the preparatory work and say exactly what is needed.
- **(d) The alarm.** If something that needs the orchestrator or PBX has waited 45 minutes (a ready video not
  launched, a cap reached, a real outage, every build refused), the INTEGRATOR sends ONE plain text message to PBX's
  Telegram review chat through the pipeline's own sender: 'PULSE CHECK NEEDS A DECISION: <one sentence>. Waiting
  since <time>.' At most one per issue and at most one an hour in total, and nothing for routine progress (PBX's
  rule: alerts are accurate and meaningful, or off). The builder (you) and pp-ingest raise it with a line the
  integrator reads: `ALARM FOR PBX: ...` on STATE line 1. You never send to Telegram yourself.

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
- 91 The closing line must earn its place: default NO line; one write and ONE value verdict off the writer's family (four clear yeses, ≤ 12 words), plus fidelity and context; anything less means no line: `spotlight.value_verdict` / `package_for`. Its MEDLEY half (the same value verdict on a medley's takeaway: lose it to the no-voice shape only if the clips meet the seconds, else one rewrite) is BUILT: `package.takeaway_value` (6626c45d, 06:33 ET Nov 14, audit 0608; tests in test_medley.py; the seal's `takeaway_value` row agreed with the integrator).
- 92 Spotlight sources: conversation, not reaction. A measured layout verdict of "conversation" or "first_hand" is required; caption markers can only make it stricter (a marked episode under 1.0 turns a minute is not a conversation); unmeasured never passes. 23:50: KEEP 1.0, re-measure after 20 spotlights' worth of episodes: `spotlight.source_test` / `layout_for` / `episode_turns`, `LAYOUT_CACHE.json`.
- 93 DEC-12d per CLIP, never by channel name: the visual check's question 4. A ticker or crawl, or a lower third / bug that is not whole in the 16:9, that the 9:16 would cut mid-word, or that covers the speaker, holds the clip in any role; a whole static strap / bug is eligible and flagged: `eligibility.layout_ok`, `visual_pin` (visual-2, `layout_block`, `burned_block`), `package.build`, `spotlight.clean_visual`.
- 94 Hook openers, medley and spotlight: (a) a conjunction / reply opener opens as ruling 33's trim variant (a clean cut, and the scorer affirms it); (b) I / me / my / we / us / our / you / your open freely; a third-person or demonstrative opener needs the scorer's affirmation: `pipeline/stand_alone.py` (the integrator's 409188ef, BYTE FOR BYTE), `eligibility` T8, `package._can_open` / `hook_trim` / `third_opener` / `scorer_pass`, `spotlight.pool`.
- 95 With no medley and no spotlight, STATE line 1 carries the three nearest and the next attempt (the newest conversation upload's publish time + its mining state): `spotlight.next_attempt`, the driver's `res["next_attempt"]`.
- 96 ROUTING, FINAL until re-measured: the table in section 3.6. Re-run the replay monthly or when a Heimdall model changes; a type goes back to Grok first if its agreement falls under Grok's own self-agreement: `model_providers.json` routing.heimdall_first (+ its `ruling_96` note).
- 97 The honest cost is about $0.20 a sealed pin, $0.18 outside; never chase the $0.05 target by moving a verdict the table says should stay. (a) The non-reasoning Grok fails the bar (`tests/package/proof/replay97/`); (b) confirmed; (c) Grok already confirms 8 to a call: STATE 01:41 ET.

Added 20:2x ET Nov 14 (rulings after this file was written; each has its own module docstring and tests):
- 98 pp-ingest's (the paid route); nothing in this worktree.
- 99 THE CIRCUIT BREAKER: two deadline misses in a row, or an answer over 2x the max_tokens the call sent, skip a
  model in every list for 30 minutes. Then ONE trial call: an answer closes the breaker, a miss or a runaway re-opens
  it for 60 minutes. STATE line 1 counts the open breakers: `pipeline/circuit_breaker.py`, `BREAKERS.json` (runtime
  state, never committed).
- 100 A verdict pair's DEADLINE comes from its row in the deadline table (p90 x 1.5, clamped 60-300 s, at least 3
  samples, recomputed daily), and only where a deadline applies at all: `providers.Router.effective_deadline`,
  `pipeline/deadline_table.py`, `package.first_bounds`.
- 101 Parallel CONFIRM-AHEAD, only with more than 20 new moments, a Heimdall lead, a wait over 600 s and a usable Grok
  confirm leg (Grok only): `package.step_a_plan`, `_confirm_leg`.
- 102 A clip that gets NO step-A answer from the second chain (Grok, deepseek, glm, gemini-2.5-pro, then the
  integrator's local gemma3:27b as a last resort) is STEP_A_HELD: never refused, never cached, retried next build. A
  local-judge verdict is noted on the pin and on STATE. The build stops at $19 (LY_STOP_USD): `package.HELD`,
  `held_why`, `last_resort_note`, `tests/package/proof_ly.py`.
- 103 THE TARGETED RE-LISTEN (the integrator's pre-check): both recognisers re-read a short window around ONE number
  or name token. A hold after it is final. The re-listen record is sealed onto the pin when one ran:
  `lock_precheck.relisten_of` / `apply`, `package_pin.SEALED_LATER` "relisten"; DECODER d1e155c642a6, RULES
  "+ ruling 103" (they land in LOCKSTEP with the integrator).
- 104 THE TAIL-SIDE VARIANT: a moment may be sealed ending at an earlier sentence boundary of itself, when that keeps
  it lawful (a held word after the boundary, a tail the cut cannot make, the 35 s ceiling). It faces every gate again
  and records `derived_from`. A held parent is replaced by its variant. On the orchestrator's WRITTEN directive only
  (`tests/package/proof/RULING_104_DIRECTIVES.json`), a variant may be the ALTERNATIVE to a named story:
  `pipeline/tail_variant.py`, `spotlight.day_taken`, `proof_ledger.directives` / `spot_place`.
- 105 THE UNSTABLE SECOND READING (20:13 Nov 14). A number or name hold is lifted, and the token adjudicated as the
  lock's, only when ALL THREE hold: (1) the decoder reads the token the same on every pass; (2) the second
  recogniser's repeated readings of the SAME audio differ among themselves and one of them equals the lock's token;
  (3) every differing reading is a TRUNCATION (a prefix) of it ('401' of '401k'). Every reading goes on the pin
  under 'unstable_second_reading' (the decoder passes, and each scribe reading named by its time, window and request:
  scribe keeps no call id). Anything else stays a final hold: a stable disagreement, a different number, a different
  name, each with a must-fail test. First case: Blockware 3f481f5a, recorded beside its pin in
  `tests/package/proof/ledger_20261114_230148/UNSTABLE_SECOND_READING.json`. The audited code follows that render.
- 106 HOW QUESTIONS WORK: see the end of section 1.
- 107 COST (20:20 Nov 14).
  - (1) A build that judges nothing new costs $0.00. proof_ledger fingerprints its inputs before any router exists;
    nothing new means NOTHING_NEW.json and a stop (9895c861).
  - (2) Audits go Heimdall-first (Appendix A).
  - (3) STATE line 1 carries the all-in figure (now batch 3's, section 3.5).
  - Q1 (20:40): an abandoned call is booked at the model's own reported rate (e7f68e11).
- 93 AMENDED (21:10 Nov 14).
  - The source's burned CAPTIONS are asked for by visual-3: one frame a second, kind "caption" with its times.
  - A caption the 9:16 crop cuts makes the clip 16:9-ONLY, never ineligible: moments_package["formats"] =
    ["16x9"], sealed; absent means both (visual_pin.formats, package_pin.formats_of).
  - A role ("a guest", "the host", "an analyst") is a claim: rule ROLE in vo_fidelity, and both writers are told.
  - The pin's spotlight_source row carries "format" (FIRST_HAND / CONVERSATION).
  - The flip (RENDER_16X9_ONLY True) followed the integrator's format-aware release (0d6957dd).
- 108 BATCH 3 (21:20 Nov 14 to 21:10 Nov 15): the $8.00 all-in cap; section 3.5.
- 109 (21:30 Nov 14): free gates first, cheapest first. In the spotlight build, an ALONE score already known below 4
  never reaches a paid verdict (7b69e5ef). The medley's free screens already ran first.
- THE RE-SEAL DIRECTIVE (ruling 104's file, "reseal": true) puts the SAME moment, as a marked copy, in its own earlier
  story's day place, never as a second spotlight. It was used once, on ruling 106's default at 21:48 Nov 14:
  Blockware 06d34e15, refused by step A (Grok disagreeing with itself on the same context).

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
- The last build is batch 3's build 3, 23:02 ET Nov 14 (`ledger_20261115_040228`, code 2c802bcf): no medley, no
  spotlight, $0.21, 0 moments held, 0 items left undone (the ruling-107 (1) guard skips the next build at $0.00
  if nothing is new).
- The last pin delivered as a pass is `moments-ledger_20261113_215708-13949b7c` (built 16:57 ET Nov 13, approved
  17:14 ET; $0.24 total / $0.23 outside). It is the last `--delivered` above. The last SEALED pin is the spotlight
  `moments-ledger_20261114_230148-3f481f5a`: the integrator sent its 16:9 on the REVIEW path at 22:37 ET Nov 14
  ("REVIEW ONLY - NOT A PASS", ruling 106 (b); two open integrity points stated; the 9:16 withheld). It is not in
  `--delivered`; the reseal directive (RULING_104_DIRECTIVES.json) holds its place for 06d34e15, which step A
  refused on re-judgment (cached: no new cost).
- Every pin you seal and the integrator delivers is ADDED to `--delivered` (its spans and speech are never used again,
  ruling 76 b).
- The default `--work-dir` is `<proof_ly.SCRATCH>/lv2`, a hard-coded OLD session's scratchpad (see section 6).
- The record goes to `tests/package/proof/ledger_<UTC stamp>/`: inputs.json, package.json (everything, including
  `spotlight` and `next_attempt`), package.log, step_a.json.
- A medley pin is MOMENTS_PIN_LEDGER.json; a spotlight pin is SPOTLIGHT_PIN.json, and a row in
  `tests/package/proof/SPOTLIGHTS.json`.
- Commit each build's record (data, no audit) with STATE, `CANDIDATES.json`, the caches, `SPEND_B3.json`,
  `BATCH3_LEDGER.json`, the deadline log and new `tests/package/fixtures/replies/*` recordings (not the
  `gate_replies/` the integrator's gate adapter writes, and never runtime state: `*.lock`, BREAKERS.json,
  HEIMDALL_HEALTH.json, DEADLINE_TABLE.json, judge_requests/).
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

### 3.5 Spend (ruling 108: BATCH 3, 21:20 ET Nov 14 to 21:10 ET Nov 15)
- The $20 order's `tests/package/proof/SPEND_LY.json` is CLOSED at $11.47, restated on ruling 107 Q1's basis
  (e7f68e11). Never write it again.
- Builds book into `tests/package/proof/SPEND_B3.json` (proof_ly.SPEND). Its basis is vendor-reported, plus abandoned
  calls at the model's OWN reported rate (ruling 107 Q1, providers.Router.booking_usd). The builds' share is a $4.50
  LIMIT; no build starts at $4.00 or more.
- THE BATCH LEDGER (you keep it): `tests/package/proof/BATCH3_LEDGER.json`, written by the script in Appendix B. It
  sums the builds, every audit started in the batch (each audit folder's COST.json) and the other two sessions'
  reported spend, which they put on their own STATE line 1 each hour. The all-in cap is $8.00 (builds and sealing
  $4.50, audits $2.50, mining and checks $1.00).
- At $6.00 all-in, say so on line 1 in CAPITALS. At $7.50 it is "ALARM FOR PBX: ..." on line 1 (ruling 106 (d)).
- RESERVATIONS: while a paid call is in flight the guard holds its LIST-price upper bound (a Grok step-A call is
  about $0.85: prompt + 8 x max_tokens of reasoning). Under $4.50 only about four fit at once, and step A runs six
  (package.PRESCREEN_WORKERS). The ledger build's router therefore WAITS for calls in flight before refusing a call
  that fits by itself (Router reserve_wait_s = proof_ly.RESERVE_WAIT_S, 600 s; 7a2ddf91). Before that, builds 1-2
  held 65 moments on SpendLimit while under $0.30 was spent ($0.02 and $0.27). Every other Router (the render's) keeps reserve_wait_s 0: refused
  at once. Lower the limit, or raise the parallelism, and this headroom must be checked again.
- proof_ly.meter wraps Router._settle and must pass every keyword on (**kw). Its old signature turned each call
  abandoned at its deadline into a TypeError hold and lost 3 glm bookings; they were booked by hand
  (`restated_b3_meter` in SPEND_B3.json, +$0.086).
- Line 1, every build: 'BATCH 3: $x of $8.00 (builds $a, audits $b, mining $c); videos sealed n; cost per sealed
  video $y'.

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

- CONTRACTS ADDED 14 Nov evening (both land in lockstep with the integrator):
  - moments_package["formats"]: exactly ["16x9"] when sealed; absent means both. The integrator's
    release_auth.package_formats reads it, and check_pin_only recomputes through pin_seal.
  - 'unstable_second_reading' (ruling 105): the pre-check entry's record, carried onto the segment as it stands and
    sealed via SEALED_LATER only when present. This side re-checks a pass that rests on it (lock_precheck.
    ruling_105_fails). DECODER a4c307f78c94.

## 5. Open items, in priority order

1. **Done (this item was stale until 23:15 ET Nov 14):** ruling 91's MEDLEY half has been built since 6626c45d (06:33 ET
   Nov 14, audit 0608): `package.takeaway_value`, the value verdict on a medley's takeaway, with the no-voice
   fallback and one rewrite; tests in test_medley.py. Nothing to build.
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
5a. **Ruling 109's count is not in the build record:** spotlight.build sets out["ruling_109"], but
    proof_ledger copies only listed spotlight keys (`res["spotlight"] = {k: sp.get(k) for k in (...)}`), so
    package.json lacks it. Until it is added (a code change: test it, audit it), count the moments whose
    spotlight `out` says "(ruling 109)", and look each one's moment id (a snapped span or a trim has its own id) up
    in STEP_A_CACHE.json to tell a first-screen call saved from a cached verdict. Build 2 of batch 3: 49 stopped,
    4 uncached ($0.03 saved at $0.0075 a moment).
5b. **Ruling 110 (d), PENDING the Heimdall team's 2x deepseek speed-up ("this week", told 23:32 ET Nov 14):** when
    it lands, re-measure deepseek's p50/p90 and reset the ruling-100 deadlines from the NEW numbers. The daily
    table (deadline_table.compute) pools EVERY recorded answer, so the old slow ones would dilute a reset:
    computing from the answers after the change needs a `since` in compute (a code change: audit it). To see it
    land: compare each build's deepseek answer times (tests/package/fixtures/replies, role context_verdict) with
    the table's step-A p50 165 s / p90 272 s; and re-run tests/package/replay110.py with a fresh OUT for the
    same 319 records. No routing change from ruling 110: a candidate enters a verdict type only by a later ruling.
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
- The same self-match breaks an "is a build running?" guard: `ps -eo args | grep '[p]roof_ledger.py'` matches the
  shell that launches the build, so the build never starts. Guard on the process name:
  `ps -eo comm=,args= | awk '$1 ~ /^python/ && $0 ~ /proof_ledger\.py/' | grep -q .`
- A wrapper over a Router method must take and pass `*a, **kw`: a new keyword in the router (ruling 107 Q1's
  `unreported`) otherwise raises inside the router and holds every call that reaches that path.
- A spend limit below (parallel calls x a call's upper bound) refuses calls at once unless the router waits
  (reserve_wait_s): read the SpendLimit message's "reserved" figure before blaming the spend.
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

## Appendix A: the audit driver under RULING 107 (2) (copy to `<your scratchpad>/audit_<LABEL>.py`)

Set LABEL (ET date and time, from `date`), DEV (the scratch copy) and FILES (every edited file; `git add -N` new
ones). Then:
1. Write `docs/audits/parallel/pp-selectid_audit_<LABEL>/QUESTION.txt`: what changed, the rulings, the unchanged
   guards (with file:line), and what to check.
2. Run `python3 -B audit_<LABEL>.py 1`.
   - The reviewers are two Heimdall families. glm's breaker open means deepseek + qwen.
   - Grok runs only on a P1 disagreement or a missing answer. A review cut at its cap with no closing
     "P1_OR_WORSE: n" counts as missing.
   - The caps are $0.30 under 60 changed lines and $1.00 over.
   - COST.json in the folder holds the vendor-reported total. PUT IT ON THE COMMIT LINE.
3. Write `C1_CONSENSUS.md`: what you implemented, and what you refuted with evidence.
4. Fix the code in DEV. Run `... 2 C1_CONSENSUS.md`, then write `C2_CONSENSUS.md`.
5. A third cycle runs only on a real defect that cycle 2 found: `DEFECT="<it>" ... 3 C2_CONSENSUS.md`.

```python
"""The pp-selectid audit driver under RULING 107 (2) as the orchestrator set it at 20:40 ET Nov 14:
- reviewers: TWO HEIMDALL FAMILIES (qwen + glm; while glm's breaker is open, deepseek + qwen: any family whose ruling-99
  breaker is open is skipped, in the order qwen, glm, deepseek);
- GROK is asked only when those two DISAGREE ON A P1 (one raises a P0 or P1 finding, the other none) or one of them
  gives NO ANSWER (failed or empty);
- a change UNDER 60 CHANGED LINES: one reviewer set, two cycles, cap $0.30 VENDOR-REPORTED; over that, cap $1.00; a
  call with no vendor figure counts at its list-price upper bound (the safe side);
- a THIRD CYCLE only when cycle 2 found a REAL DEFECT: DEFECT="<the defect, one line>" in the environment, else refused;
- each review records the vendor's own cost (Heimdall usage.cost; xAI usage.cost_in_usd_ticks, 1 USD = 1e10 ticks)
  beside the upper bound, and COST.json in the audit folder holds the running total: report it on the commit line.
The code sent is the actual change: the git diff against the scratch copy's base (no whole files).

Copy to <scratchpad>/audit_<LABEL>.py and set LABEL / DEV / FILES. Write QUESTION.txt first.
Usage: python3 -B audit_<LABEL>.py <cycle> [<previous cycle's consensus file>]"""
import importlib.util, json, os, re, subprocess, sys, threading, time, urllib.request
from pathlib import Path

LABEL = "YYYYMMDD_HHMM"                                          # the audit's label (ET date + time it starts, from date)
WT = Path("/home/ultron/worktrees/pp-selectid")
AUD = WT / "docs" / "audits" / "parallel" / f"pp-selectid_audit_{LABEL}"
DEV = Path("/tmp/claude-1000/-home-ultron-worktrees-pp-selectid/a80f37a3-3482-4017-9152-9c0c6e2f0dab/scratchpad/devNN")
FILES = []                                                       # every edited file, as in DEV's git base
ENV = "/home/ultron/protocol_pulse/" + "." + "env"      # read by name inside code only; never printed
SMALL_LINES, SMALL_CAP, CAP = 60, 0.30, 1.00                     # ruling 107 (2), 20:40 Nov 14
sys.path.insert(0, str(WT / "pipeline"))
from providers import env_value  # noqa: E402
import circuit_breaker as CB  # noqa: E402

HEIMDALL = "https://api-staging.heimdallm.com/api/v1/chat/completions"
THIRD = "grok-4.20-0309-reasoning"
REVIEWERS = {                                                    # name -> call; "breaker": its ruling-99 model id
    "qwen3.8-27b": {"url": HEIMDALL, "key": "HEIMDALL_API_KEY", "breaker": "heimdall:qwen/qwen3.8-27b",
        "body": {"model": "qwen/qwen3.8-27b", "max_tokens": 16000, "temperature": 0,
                 "reasoning": {"effort": "none"}}, "price": (3, 15)},
    "glm-5.3-flash": {"url": HEIMDALL, "key": "HEIMDALL_API_KEY", "breaker": "heimdall:z-ai/glm-5.3-flash",
        "body": {"model": "z-ai/glm-5.3-flash", "max_tokens": 24000, "temperature": 0,
                 "reasoning": {"effort": "none"}}, "price": (3, 15)},
    "deepseek-v4.1-flash": {"url": HEIMDALL, "key": "HEIMDALL_API_KEY", "breaker": "heimdall:deepseek/deepseek-v4.1-flash",
        "body": {"model": "deepseek/deepseek-v4.1-flash", "max_tokens": 16000, "temperature": 0}, "price": (3, 15)},
    THIRD: {"url": "https://api.x.ai/v1/chat/completions", "key": "XAI_API_KEY_MEDLEY", "breaker": None,
        "body": {"model": "grok-4.20-0309-reasoning", "max_tokens": 30000, "temperature": 0}, "price": (5, 25)},
}
ORDER = ["qwen3.8-27b", "glm-5.3-flash", "deepseek-v4.1-flash"]
HEAD = re.compile(r"usd_reported=([0-9.]+|none) usd~([0-9.]+)")
P1 = re.compile(r"\[P[01]\]")
ASK = ("\n\nTag EVERY finding with its severity: [P0] (wrong result, data loss, a gate passing what it must refuse), "
       "[P1] (a real defect that must be fixed before merge), [P2] (should fix), [P3] (nit). "
       "End with ONE line: P1_OR_WORSE: <the number of [P0] and [P1] findings>.\n")
spec = importlib.util.spec_from_file_location("cross_llm_audit", WT / "utils" / "cross_llm_audit.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
m.BASE, m.GOSPELS = WT, WT / "docs" / "gospels"
FEATURE = f"pp-selectid-{LABEL}"
m.FEATURE_MAP[FEATURE] = ("PULSE_SENTENCE_LAW_GOSPEL.md", "pp-selectid")
m.CUSTOM_REVIEW_TASKS[FEATURE] = (AUD / "QUESTION.txt").read_text()


def first_two():
    """The two Heimdall families asked first: ORDER, skipping any whose ruling-99 breaker is open."""
    try:
        shut = {o["model"] for o in CB.summary(CB.STATE)["open"]}
    except Exception as e:                                       # noqa: BLE001  unreadable: no family is skipped
        print(f"breaker state unreadable ({type(e).__name__}): no family skipped", flush=True)
        shut = set()
    names = [n for n in ORDER if REVIEWERS[n]["breaker"] not in shut]
    if len(names) < 2:
        sys.exit(f"refused: fewer than two Heimdall families are closed to breakers ({sorted(shut)})")
    return names[:2], sorted(shut)


def reported_usd(name, u):
    """The vendor's own dollars for one reply, or None when it gives none."""
    if name == THIRD:
        t = u.get("cost_in_usd_ticks")
        return t / 1e10 if isinstance(t, (int, float)) else None
    c = u.get("cost")
    return float(c) if isinstance(c, (int, float)) else None


def cost():
    """(vendor-reported dollars, upper-bound dollars of the reviews with no vendor figure, their count, per review)."""
    rep = upper = 0.0
    n_upper, rows = 0, []
    for p in sorted(AUD.glob("C*_*.md")):
        h = HEAD.search(p.read_text()[:400])
        if not h:
            continue
        if h.group(1) == "none":
            upper += float(h.group(2)); n_upper += 1
        else:
            rep += float(h.group(1))
        rows.append({"review": p.name, "usd_reported": None if h.group(1) == "none" else float(h.group(1)),
                     "usd_upper_bound": float(h.group(2))})
    return rep, upper, n_upper, rows


def spent():
    rep, upper, _, _ = cost()
    return rep + upper                                           # a call with no vendor figure counts at its bound


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
        upper = (u.get("prompt_tokens", 0) * r["price"][0] + u.get("completion_tokens", 0) * r["price"][1]) / 1e6
        rep = reported_usd(name, u)
        head = (f"# {name} ({r['body']['model']}) {round(time.time() - t0)} s finish="
                f"{j['choices'][0].get('finish_reason')} usage in {u.get('prompt_tokens')} / out "
                f"{u.get('completion_tokens')} usd_reported={'none' if rep is None else f'{rep:.6f}'} "
                f"usd~{upper:.3f} (upper-bound price)" + (" EMPTY" if not text.strip() else "") + "\n\n")
    except Exception as e:
        head, text = f"# {name}: FAILED {type(e).__name__}: {str(e)[:200]}\n\n", ""
    out.write_text(head + text)
    print(out.name, head.strip()[:220], flush=True)


def down(p):
    """No answer: failed, empty, or cut off at its token cap with no closing P1_OR_WORSE line (its tags are then a
    fragment, never a count)."""
    if not p.exists():
        return True
    t = p.read_text()
    return ("FAILED" in t[:400] or "EMPTY" in t[:400] or
            ("finish=length" in t[:400] and not re.search(r"P1_OR_WORSE:\s*\d+", t)))


def p1_count(text):
    """The review's own closing 'P1_OR_WORSE: n'; without one, its [P0] / [P1] tags."""
    n = re.findall(r"P1_OR_WORSE:\s*(\d+)", text)
    return int(n[-1]) if n else len(P1.findall(text))


def run(names, prompt, cycle):
    ts = [threading.Thread(target=review, args=(n, prompt, AUD / f"C{cycle}_{n}.md")) for n in names]
    for t in ts:
        t.start()
    for t in ts:
        t.join()


def main():
    cycle = int(sys.argv[1])
    diff = subprocess.run(["git", "diff", "HEAD", "--", *FILES], cwd=DEV, capture_output=True, text=True,
                          check=True).stdout
    changed = sum(1 for ln in diff.splitlines()
                  if ln[:1] in "+-" and not ln.startswith("+++") and not ln.startswith("---"))
    cap = SMALL_CAP if changed < SMALL_LINES else CAP
    if cycle >= 3 and not os.environ.get("DEFECT", "").strip():
        sys.exit("refused: a third cycle only when cycle 2 found a real defect (DEFECT=\"<the defect>\")")
    if spent() >= cap:
        sys.exit(f"refused: ${spent():.4f} spent of the ${cap:.2f} cap ({changed} changed lines)")
    (AUD / f"C{cycle}_STEP.diff").write_text(diff)
    m.EXPLICIT_FILES[FEATURE] = [str((AUD / f"C{cycle}_STEP.diff").relative_to(WT))]
    package = m.build_audit_package(FEATURE)
    assert f"### File: {m.EXPLICIT_FILES[FEATURE][0]}" in package, "the package holds no code"
    if cycle == 1:
        prompt = package
    else:                                   # a later cycle cross-validates the previous cycle's reviews and consensus
        prev = f"C{cycle - 1}_"
        c1 = {p.stem[3:]: p.read_text() for p in sorted(AUD.glob(prev + "*.md"))
              if p.stem not in (prev + "PROMPT", prev + "CONSENSUS") and not down(p)}
        prompt = m.build_cycle2_prompt(FEATURE, package, c1, (AUD / sys.argv[2]).read_text()).replace(
            "## ORIGINAL CODE (same code as Cycle 1)", "## THE CODE NOW: the FIXED diff")
        if cycle >= 3:
            prompt += f"\n\nTHIS THIRD CYCLE CHECKS THE FIX OF CYCLE 2'S REAL DEFECT: {os.environ['DEFECT'].strip()}\n"
    prompt += ASK
    (AUD / f"C{cycle}_PROMPT.md").write_text(prompt)
    first, shut = first_two()
    print(f"prompt {len(prompt.encode())} bytes; {changed} changed lines, cap ${cap:.2f}; reviewers {first}"
          + (f" (breakers open: {shut})" if shut else ""), flush=True)
    run(first, prompt, cycle)
    outs = [AUD / f"C{cycle}_{n}.md" for n in first]
    p1 = [None if down(p) else p1_count(p.read_text()) for p in outs]
    why = ("one of them gave no answer" if None in p1 else
           "they disagree on a P1 (one raises a P0 / P1, the other none)" if (p1[0] == 0) != (p1[1] == 0) else None)
    print(f"P0/P1 findings: {dict(zip(first, p1))}; Grok: {why or 'not asked (they agree)'}", flush=True)
    if why:
        if spent() >= cap:
            print(f"GROK REFUSED: ${spent():.4f} spent of the ${cap:.2f} cap", flush=True)
        else:
            run([THIRD], prompt, cycle)
    rep, upper, n_upper, rows = cost()
    (AUD / "COST.json").write_text(json.dumps({"ruling": "107 (2), 20:40 ET Nov 14", "changed_lines": changed,
                                               "cap_usd": cap, "usd_reported": round(rep, 6),
                                               "usd_upper_bound_unreported": round(upper, 6),
                                               "reviews": rows}, indent=1) + "\n")
    print(f"CYCLE{cycle}_DONE AUDIT COST so far: ${rep:.4f} vendor-reported"
          + (f" + ${upper:.4f} upper bound for {n_upper} review(s) with no vendor figure" if n_upper else ""),
          flush=True)


if __name__ == "__main__":
    main()
```

## Appendix B: the batch-3 ledger keeper (copy to `<your scratchpad>/batch3.py`)

`python3 -B batch3.py --other integrator=<usd> --other pp-ingest=<usd> --other pp-ingest:audits=<usd> [--sealed N]`
writes BATCH3_LEDGER.json and prints line 1's figure. A session's audits go in as `NAME:audits` and count under
audits; `pp-ingest` alone is mining and checks. The values persist in the ledger between runs.

```python
"""RULING 108 (orchestrator 21:20 ET Nov 14): BATCH 3's all-in ledger, kept by the builder, to 21:10 ET Nov 15.
builds = tests/package/proof/SPEND_B3.json (vendor-reported + abandoned calls at the model's own rate);
audits = every pp-selectid audit folder started in the batch (label >= START_LABEL): its COST.json (vendor-reported,
the upper bound only for a review with no vendor figure); others = the other sessions' own reported spend, as they
report it on their STATE line 1 (set by hand from their reports: --other NAME=USD; --other NAME:audits=USD for a
session's audits, counted under audits; pp-ingest alone is mining and checks). Writes
tests/package/proof/BATCH3_LEDGER.json and prints STATE line 1's figure.
Usage: python3 -B batch3.py [--other integrator=0.0058 --other pp-ingest=0.00] [--sealed N]"""
import glob, json, os, sys
WT = "/home/ultron/worktrees/pp-selectid"
START_LABEL, CAP, TELL, ALARM = "20261114_2110", 8.00, 6.00, 7.50
SHARE = {"builds": 4.50, "audits": 2.50, "mining": 1.00}
OUT = os.path.join(WT, "tests/package/proof/BATCH3_LEDGER.json")


def main(argv):
    others, sealed = {}, None
    if os.path.exists(OUT):
        prev = json.load(open(OUT))
        others, sealed = prev.get("others") or {}, prev.get("videos_sealed")
    it = iter(argv)
    for a in it:
        if a == "--other":
            k, v = next(it).split("=")
            others[k] = float(v)
        elif a == "--sealed":
            sealed = int(next(it))
    try:
        d = json.load(open(os.path.join(WT, "tests/package/proof/SPEND_B3.json")))
        builds = float(d.get("usd_reported", 0.0)) + float(d.get("usd_unreported_estimate", 0.0))
    except OSError:
        builds = 0.0
    audits, rows = 0.0, {}
    for f in sorted(glob.glob(os.path.join(WT, "docs/audits/parallel/pp-selectid_audit_2*/COST.json"))):
        label = f.split("pp-selectid_audit_")[1].split("/")[0]
        if label >= START_LABEL:
            c = json.load(open(f))
            usd = float(c.get("usd_reported", 0.0)) + float(c.get("usd_upper_bound_unreported", 0.0))
            rows[label] = round(usd, 6)
            audits += usd
    mining = float(others.get("pp-ingest", 0.0))              # pp-ingest's mining and checks
    audits += sum(v for k, v in others.items() if k.endswith(":audits"))   # another session's audits ("NAME:audits")
    other = sum(v for k, v in others.items() if k != "pp-ingest" and not k.endswith(":audits"))
    total = builds + audits + mining + other
    sealed = sealed or 0
    rec = {"ruling": "108, orchestrator 21:20 ET Nov 14", "batch": 3, "to": "2026-11-15T21:10 ET", "cap": CAP,
           "shares": SHARE, "builds": round(builds, 6), "audits": round(audits, 6), "audit_rows": rows,
           "mining": round(mining, 6), "others": others, "all_in": round(total, 6), "videos_sealed": sealed}
    json.dump(rec, open(OUT, "w"), indent=1)
    per = f"${total / sealed:.2f}" if sealed else "n/a"
    flag = (" ALARM FOR PBX: BATCH 3 HAS SPENT ${:.2f} OF $8.00.".format(total) if total >= ALARM else
            " BATCH 3 HAS PASSED $6.00." if total >= TELL else "")
    print(f"BATCH 3: ${total:.2f} of $8.00 (builds ${builds:.2f}, audits ${audits:.2f}, mining ${mining:.2f}"
          + (f", integrator ${others.get('integrator', 0.0):.2f}" if "integrator" in others else "")
          + f"); videos sealed {sealed}; cost per sealed video {per}.{flag}")


if __name__ == "__main__":
    main(sys.argv[1:])
```
