# pp-backtest: cross-LLM audit record

Tool: utils/cross_llm_audit.py (feature header `pulse-sentence-law`, two cycles forced), run with HOME set to a scratch
directory so nothing is written into the main tree (bible addition B1). Keys only from
/home/ultron/protocol_pulse/.env, by name (the order's law): that file holds no Gemini key, so the **Gemini leg is NOT
RUN** in every cycle below (recorded as such by the wrapper, no fake answer; REQUESTS R6 asks the integrator for it).
GPT-4o and Grok-3 (xAI key XAI_API_KEY_MEDLEY mapped in-process) ran both cycles; Claude synthesised the consensus. An
independent claude-fable-5-2 review of the same cycle-1 package was added (schema-constrained findings), priced on its
own audit ledger, not the oracle's spend guard.

Packages (each under the tool's 220,000-byte file limit): **A** = the code, pipeline/oracle/*.py +
tools/backtest_oracle.py, prefixed with pp-backtest_audit/QUESTION_A.txt; **B** = tests/oracle/*.py + pp-backtest_ANALYSIS.md +
pp-backtest_STATE.md + docs/audits/BACKTEST_SUPPLY_REPORT.md, prefixed with pp-backtest_audit/QUESTION_B.txt. Each package is the question
followed by `git diff --no-index /dev/null <file>` for every file of the package.

## Round 1: package A, 2026-11-12 03:21-03:30 ET

- Cycle 1 / 2 (GPT-4o, Grok-3): READY, no defects. Consensus P0 "run regression_test.sh and the tests against this
  diff": done (regression_test.sh 26 PASS / 0 FAIL / 5 WARN; tests/oracle all pass). P1 "CI on push": no CI config is
  in this branch's scope; not applicable here.
- claude-fable-5-2 independent review: NOT READY, 12 findings (2.07 USD on the audit ledger). These were substantive;
  the two-model consensus had not looked past the tool's generic checklist. Dispositions:

| # | finding (short) | disposition |
|---|---|---|
| F1 HIGH | unpriced Heimdall calls bypass the spend cap; tripwire read once per A/B batch; credits 0 skips the tripwire | FIXED: Ledger.allow_unpriced refuses any unpriced call once recorded spend reaches the cap; call_backend checks the Heimdall tripwire on EVERY call (VendorDown -> the chain falls back); no credits = unavailable. Tests: test_oracle_ledger.py, test_oracle_providers.py (tripwire every call). |
| F2 HIGH | layout blame from today's registry; LAYOUT before NOT_REACHED | FIXED (registry): survival uses each coverage verdict's own layout_eligible flag (the run's decision; the run's universe flag if a verdict lacks it). NOT CHANGED (ordering): the selector applies the layout gate in the same step as coverage (editorial_select.py: coverage verdicts -> "rejected: only N layout-eligible" -> "coverage_qualified"), so a candidate with coverage done has been through the layout gate. Re-score: 36 of 36 traces unchanged. Tests: the record decides; today's registry never rewrites it. |
| F3 MEDIUM | reservation released before the cost is recorded; reservations per process only | FIXED: Ledger.settle appends the row and drops the reservation in one locked step; reservations live on disk (<ledger>.inflight) under an fcntl file lock, so separate processes see each other's in-flight worst cases; a dead process's reservation is dropped. RESIDUAL (stated): a call that raises after the vendor billed it (a timeout mid-generation) releases its reservation unrecorded; vendors do not bill 4xx/5xx refusals. Tests: cross-process reservation, settle. |
| F4 MEDIUM | writer vendor None -> nothing excluded in group / witness | FIXED: writer_vendor refuses (SystemExit) when the writer's vendor cannot be named. Every saved artefact resolves (openai). |
| F5 MEDIUM | must-fail swaps built from windows-as-targets line-ups, judged under hard windows; "caught" on any reason | FIXED: the first 9 swaps are WITHDRAWN (never counted; their paid calls still counted in dollars). New swaps: a line-up of the windows-HARD run that the reference passed under this exact prompt, last clip replaced by a clip of the day's least-related development (least canonical-word overlap), all deterministic checks passing with the windows hard; caught only when the judge fails it ON rule 1. The reference judge itself catches 6 of 8, so the report treats swaps as calibration, not certain ground truth. Test: right verdict for the wrong reason is not caught. |
| F6 MEDIUM | context guard only for the local model; a 400 context error does not move the chain | FIXED: a vendor's context-length refusal (400/413 + context wording) is ContextTooLong and the chain moves on; a remote reply that counted fewer than 1 prompt token per 6 characters is ContextTooLong (a cut prompt; the paid call is still recorded). NOT DONE: declaring every remote context window (the values are not known reliably for these models; a wrong declaration would skip or send wrongly). Tests: both paths. |
| F7 MEDIUM | a failed re-ask leaves the day OK and reported NOT_AVAILABLE | FIXED: when every first-reply line-up failed the checks and the re-ask never returned whole, availability is NOT_MEASURED (re-ask failed). No saved day was in this state (all variants: every run AVAILABLE). Test added. |
| F8 MEDIUM | stale WITNESS / GROUPS / SCORE after a re-run | FIXED: archive_previous moves every derived file too; GROUPS / WITNESS / SCORE carry the sha256 of the ORACLE.json they used; readers check run.fresh() (stamp, or for files written before the stamp: not older than ORACLE.json); survivors() counts only line-ups DAY.json accepted; the report prints "stale: not counted". Check on the saved data: 50 of 50 derived files fresh. Tests added. |
| F9 LOW | (a) docstring says altered record = gap, code aborts; (b) witness context error loses the batch; (c) registry not in the manifest | (a) DOCS FIXED to the tested behaviour: an altered record stops the export (that universe cannot be reproduced); a missing record stays a counted gap. (b) FIXED: any context error is that line-up's WITNESS_FAILED. (c) FIXED: manifest registry_sha256 (exports written from this commit on; the ten saved exports predate it and are unchanged). |
| F10 LOW | (a) SELECTED override; (b) caveat notes dropped; (c) hard-coded neighbourhood / static claims; (d) precision never computed; (e) vendor names outside providers.py | (a) FIXED (only when the line-up itself reached PRODUCIBLE / SELECTED; test). (b) FIXED: notes printed per trace and caveated CLUSTER_FORMATION counted under the section 3 table (this changed the analysis: those losses are "where the record stopped"). (c) FIXED (export.NEIGHBOURHOOD; the determinism claim cites the session's three exports and the test). (d) REFUTED: no record accepted a line-up, so precision is reported as not measured with that reason; computing it needs a selector-accepted line-up. (e) FIXED in report.py; REFUTED for replay.py: "gemma" there names the selector's own model (the pipeline's LocalLLM), not a role of this instrument; the L-x test checks every configured model id, back-end name and endpoint. |
| F11 LOW | raw exception text could echo a key | FIXED: llm.redact masks every loaded key value and key-shaped token (sk-, xai-, Bearer) in every persisted or printed error. Scan of 1,413 artefact / log / doc files before the fix: 0 key-like strings. Test added. |
| F12 MEDIUM | package header / laws do not fit; tests not in the package | FIXED for round 2: both questions carry the texts of L-j, L-l, L-m, L-o, L-q, L-x and the spend guard; package B carries the tests. |

Spend guard incident handled during this round (not a finding): the A/B harness's parallel batches were stopped by the
ledger's worst-case reservations at 55-56 USD of actual spend (the guard working); stopped items are reported as NOT
MEASURED (own column), never as failures. claude-fable-5-2's reply cap went from 96,000 to 32,000 tokens at 03:31 ET
(its largest reply in 293 calls: 8,129 tokens; a reply that reaches the cap fails closed), so a fable call reserves
1.3 USD instead of 3.9 USD.

## Round 2: package A after the fixes, 2026-11-12 03:51-03:58 ET (diffA sha256 095f101138422439...)

- Cycle 1 / 2 (GPT-4o, Grok-3): no code defect found by either; consensus HOLD only because package A holds no tests
  (by design: they are package B). Each consensus item maps to tests that exist in tests/oracle:

| consensus item | where it is tested |
|---|---|
| P0 parse_oracle must-fail (malformed / empty / inconsistent) | test_oracle_lineup.py: test_an_empty_or_malformed_reply_is_oracle_failed, test_a_malformed_sentence_id_is_oracle_failed, test_an_id_that_is_not_in_the_universe_is_oracle_failed, test_a_partial_or_contradictory_reply_is_oracle_failed; test_oracle_run.py: test_an_empty_reply_twice_is_oracle_failed_never_none |
| P0 parse_judge must-fail | test_oracle_lineup.py: test_an_inconsistent_or_empty_verdict_is_judge_failed, test_a_mistyped_or_partial_verdict_is_judge_failed; test_oracle_run.py: test_a_judge_that_never_answers_whole_is_not_measured_never_available |
| P0 every rule branch of check | test_oracle_lineup.py: test_each_structural_rule_fails_its_fixture (parametrised), test_one_channel_and_the_per_video_and_per_channel_limits, test_an_altcoin_sentence_smuggled_into_a_lineup_fails, test_the_legal_fixture_passes_every_check |
| P0 Ledger over the cap under concurrency | test_oracle_llm_replay.py: test_concurrent_reservations_never_pass_the_cap_together; test_oracle_ledger.py: cross-process reservation, settle, unpriced refusal |
| P0 swap caught only on rule 1 | test_oracle_ab.py: test_a_swap_counts_as_caught_only_when_the_judge_fails_it_on_the_swapped_rule |
| P1 no live calls in tests | every provider / A/B test replaces the transport (providers._KIND) with a fake; no test reads a key or opens a socket (fixtures monkeypatch llm.env_key) |
| P1 NotRerun synthetic record | test_oracle_llm_replay.py: test_a_cache_miss_is_not_rerun_and_escapes_every_except_exception, test_a_not_rerun_writes_the_selectors_live_record_and_restores_checkpoint; test_oracle_score.py: the NOT_RERUN stage from a synthetic record |

- claude-fable-5-2 independent review: its first reply hit the 32,000-token cap (no text: recorded as NOT MEASURED,
  never as a pass). Re-run with a 96,000-token cap for the audit review only (the instrument's config is unchanged):
  see below.
- Changes after this package was built (wording and rendering only, no logic): run.py's NOT_AVAILABLE text says "the
  blind judge said every checked line-up fails our rules"; report.py translates older artefacts' verdict words
  (plain()) and labels withdrawn rows. Covered by the tests (152 pass) and by package B (the report).
- claude-fable-5-2 independent review, re-run with the 96k cap (04:01-04:06 ET, 1.97 USD): NOT READY, 16 findings.
  Dispositions (the re-score after F8 changed 11 of 36 traces from CLUSTER_FORMATION to NOT_REACHED; no other stage):

| # | finding (short) | disposition |
|---|---|---|
| F1 HIGH | recall counts crashed / stopped / NOT_RERUN records as misses | FIXED: recall counts only records that completed a selection; the rest are "not measured" with their count. Report now: as run 0 of 6 (4 not measured), cold 0 of 1 (1 not measured), HEAD not measured (0 of 10 replays completed). Analysis 5.1 rewritten. |
| F2 MEDIUM | the swaps' writer vendor (windows-hard run) not in the avoided set | FIXED: the judge A/B avoids the vendors of "" and same_dev_hard_max (where its items come from). Every saved writer is openai, so no row changes. |
| F3 MEDIUM | unpriced calls reserve nothing; a missing gateway cost is 0; a failure after billing is released | FIXED: every remote call reserves a worst case (price table, or the config's reserve_usd: 0.25 USD for Heimdall, 1 USD default); a gateway that reports no cost is charged that worst case ("unreported: worst case"); a timeout or dropped connection with no HTTP status is charged at worst case ("failed after sending"); a refusal with a status is released (not billed). Tests added. |
| F4 MEDIUM | a local 5xx (urllib HTTPError .code) or a reset connection does not fall through the chain | FIXED: _status reads .status_code / .response.status_code / .code; URLError / OSError are vendor-side. Test: a local 503 and a connection reset move the judge to the next back-end. |
| F5 MEDIUM | a schema retry can use the attempt the violation re-ask needed | FIXED: ORACLE.json records reask_answered; every-line-up-fails-the-checks is NOT_AVAILABLE only when the re-ask was answered whole, else NOT_MEASURED (re-ask not answered). No saved day is in this state. Test added. |
| F6 MEDIUM | rows over 20 s hidden in target-mode variants | STATED: report section 7 now gives the hidden rows (per universe and in all) and calls the target-mode columns lower bounds for this reason; the variants were not re-run (spend guard). |
| F7 MEDIUM | only segments are hashed; two records with one sha; words read unhashed | FIXED: two records carrying the run's sha are an ExportError (on the saved universes: 0 of 981 entries ambiguous); the manifest's per-video read_sha256 hashes exactly what was read (from this commit on). The store is write-once (transcript_store._write_once), so a record cannot change in place. |
| F8 MEDIUM | CLUSTER_FORMATION blamed in incomplete records | FIXED: no carrier in an incomplete record is NOT_REACHED with the note "no cluster held its statements ..."; CLUSTER_FORMATION only in complete records. Re-score: as run CLUSTER_FORMATION 4 -> 1 (NOT_REACHED 3 -> 6), cold 2 -> 0, HEAD 6 -> 0 (NOT_REACHED 8 -> 14). Report section 3 keeps the split-cluster evidence for both. Analysis 5.2 rewritten. |
| F9 LOW | the A/B path does not write the Heimdall NOTIFY file | FIXED: _one passes the batch dir as notify_dir. |
| F10 LOW | local first in every default chain before its A/B passed | FIXED: providers.LOCAL_VALIDATED (all False); a role's default chain skips the local back-end until its A/B passes (an explicit chain, e.g. the A/B harness, still reaches it). Test added. |
| F11 LOW | a remote reply without a prompt-token count skips the cut-prompt check | FIXED: ContextTooLong ("no prompt-token count"). Test added. |
| F12 LOW | swap pairs fall through to related developments; min() on an empty group | FIXED: pairs are tried least-overlap first and never above 20 % canonical-word overlap (the 8 swaps used: 0.023-0.194, unchanged); an empty group is skipped. |
| F13 LOW | a row cut by a speaker change can sit inside a segment | FIXED: check() requires every row of a segment to be a whole sentence (complete). On the saved data: 0 of 136 accepted line-ups have such a row, so no number changes. Test added. |
| F14 LOW | a second copy of canon | FIXED: import canon (flat). |
| F15 LOW | cache digest from an unsorted sample; read-only not enforced in the replay | FIXED: the digest counts every cached reply, sorted; the replay command runs inside replay.no_writes_under(main tree) (open-for-write, os.open, replace, rename, unlink, makedirs of a new dir, pathlib writes: PermissionError -> the replay records CRASH). Test added. The ten replays already saved ran before the guard existed: their stand-ins (CacheOnlyLLM, CpuEmbedder) have no write path into the store, but nothing enforced that then. |
| F16 MEDIUM | package scope | ANSWERED: package B (tests, analysis, state, report) is audited in round 3. |

## Round 3 (package A, diff sha256 391f4663...) and package B round 1 (diff sha256 cbfa6e2e...), 04:27-04:33 ET

- Tool legs: Grok-3 only. GPT-4o FAILED in both packages, both cycles: OpenAI returned 429 insufficient_quota (the
  account is out of credit again); Gemini NOT RUN (no key). Grok: package A READY WITH CONDITIONS (tests: package B);
  package B NOT READY (placeholders; see below).
- claude-fable-5-2 independent reviews: package A 8 findings (2.14 USD), package B 8 findings (2.02 USD). Dispositions:

| # | finding (short) | disposition |
|---|---|---|
| A-F1 HIGH | a flat 1-token-per-6-characters cut check lets a gateway drop half a prompt | FIXED: per-back-end max_chars_per_token = 1.25 x the largest ratio measured on this instrument's stored prompts (grok 3.7, fable 2.6, gpt 3.8, deepseek 4.4, glm 5.2, qwen 3.8); 6.0 only for an unmeasured back-end. NOT DONE: declared remote context windows (unknown). |
| A-F2 MEDIUM | a decided carrier wins while another is undecided in an incomplete record; LAYOUT blamed before coverage finished | FIXED: incomplete record + any undecided carrier = NOT_REACHED (note: the furthest decided stage); LAYOUT only after coverage is done. Re-score: no count changed. Tests updated. |
| A-F3 MEDIUM | a killed process's reservation is dropped | FIXED: an orphaned reservation is charged at its worst case (a row "orphaned: worst case"); Ctrl-C / exit mid-call settles at worst case. The live in-flight file was empty when this went in (nothing charged retroactively). Tonight's batches stopped by hand ran the older in-memory ledger: up to 4 grok judge calls (~0.08 USD each) and a few Heimdall calls (<= 0.03 USD each) were in flight when stopped and are NOT in the ledger, so the ledger may understate spend by up to about 0.5 USD. |
| A-F4 MEDIUM | word records unhashed; the witness re-derives sentence indices | FIXED: witness.context refuses (WitnessFailed) when the record no longer gives the exported sentence text at each clip index; the manifest's read_sha256 covers what was read (new exports). Test added. |
| A-F5 LOW | SDK silent retries; fixed Heimdall reserve | FIXED: SDK max_retries 0 (retries are the instrument's own attempts, each priced); the Heimdall reserve is the larger of 0.25 USD and (estimated prompt + reply budget) tokens at 2 USD per million. |
| A-F6 LOW | the write guard is best effort | STATED in its docstring (dir_fd, keyword paths, truncate / chmod, sqlite, subprocesses not covered); no replay is planned. |
| A-F7 LOW | the selector's limits copied as literals | FIXED: lineup.py raises ImportError at import if its windows / sentence / channel limits differ from editorial_select's. |
| A-F8 MEDIUM | scope | ANSWERED by package B. |
| B-F1 HIGH | unfilled @GLM_*@ placeholders | FIXED: filled with the final numbers; report generation now raises on any @NAME@ left in the analysis (test). |
| B-F2 HIGH | swaps not run on grok / glm not shown as not run; glm "16 of 17" vacuous | FIXED: the A/B table shows items run / planned per back-end (the reference judge: planned = the 8 swaps); 5.7 states glm passed all 17 recorded line-ups and gives its swap result; grok's swaps not run (spend guard) are visible as 17 / 25. |
| B-F3 HIGH | 24 local-model calls in the ledger vs "PENDING / never touched GPU0" | EXPLAINED + FIXED: those are the integrator's R5 runs under the GPU0 lease (another session's run_r5_ab.py, started 03:47 ET with PP_GPU0_LEASE_HELD=1, cwd this worktree); this session never called the local back-end. The report says so and shows their results (judge: complete; witness: in progress). |
| B-F4 MEDIUM | grouping / moments blindness tests vacuous | FIXED: markers planted in the writer's development / current_because; asserted absent from every grouping and moments-judge prompt. |
| B-F5 MEDIUM | determinism only in one interpreter | FIXED: two subprocesses with PYTHONHASHSEED 1 and 2 must write byte-identical exports; the manifest has no wall-clock field. |
| B-F6 MEDIUM | witness fail-closed aggregation untested | FIXED: an unrun witness leaves every model check None; a WITNESS_FAILED line-up is counted only in the base row (tests). |
| B-F7 MEDIUM | three text / table disagreements | FIXED: (a) the one channel counted for Nov 10 L2's candidate was Yahoo Finance through a different video (36HPi9UZPOc), not the line-up's; (b) "held one channel's, no decision recorded (NOT_REACHED)" replaces "none held any" where one-channel clusters exist; (c) six runs, not five. |
| B-F8 LOW | the name scan misses unregistered names; no failover-aware judge test | FIXED: a shape scan (model-id patterns, vendor endpoints, the local port) over every file but providers.py; providers.paired_calls makes the judge avoid the vendor that ACTUALLY wrote (after a failover), used by the oracle command, with a test. |
