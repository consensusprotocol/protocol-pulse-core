# pp-ingest: answers to the INTEGRATOR MERGE AUDIT, cycle 1 (pipeline_pp_dod, 05:02 ET Nov 12)

The questions: docs/audits/parallel/pp-ingest_INTEGRATOR_AUDIT.md (as the integrator wrote it) and the record
/home/ultron/protocol_pulse/docs/audits/pulse-sentence-law/merge_pp-ingest/cycle1/FRONTIER_anthropic.md. The answers
are in the commit after 9500030f (branch pp-ingest), together with the orchestrator's 05:30 SPEND FREEZE, which B1
and B2 directly concern: with the frontier vendors frozen, Heimdall is the only callable miner of this session, so a
tripwire that removes it (B1) or an outage limit that drops videos (B2) would have stopped or lost the day's mining.

Evidence of each blocking defect ON THE OLD CODE (753dec1d, an untouched `git archive` export, its own helpers):
docs/audits/parallel/pp-ingest_audit/integrator_c1/mustfail_old_753dec1d.json (script: mustfail_old.py beside it).
Each new test below passes on the new code; tests/ingest: 161 pass.

## BLOCKING

**B1 the 90 % tripwire halted the Heimdall leg (and did so when merely unmeasured). FIXED.**
- Old code, reproduced: `{"B1": "HALTED at 90 % with the metered back-end alone: [('h', 'skipped', 'heimdall spend
  tripped')]; calls made: 0", "B1_unmeasured": "HALTED when merely unmeasured ..."}`.
- Now `Router.available` never reads the meter (pipeline/ingest/providers.py). While the meter is not 'ok' (tripped or
  unmeasured), `Router.order` moves the metered back-ends to the END of the chain: others go first where any are
  callable (orchestrator 02:45 "fall back to the other back-ends rather than halting"), and the metered one keeps
  mining when it is the only one (orchestrator 05:30 "Heimdall mining continues"). The STATE notice now says so
  ("... NOTIFY only; mining continues on it ...; nothing halted.") and the STATE file is rewritten only when that line
  changes.
- Tests: test_providers.py `test_the_tripwire_notifies_and_moves_the_metered_back_end_last_never_out`,
  `test_an_unmeasured_spend_is_never_read_as_below_the_tripwire_and_never_halts`; test_service.py
  `test_the_tripwire_notifies_prefers_the_others_and_never_halts`; test_store_contract.py
  `test_the_real_label_writes_the_orchestrators_exact_words` ("HEIMDALL SPEND AT 90%" comes from providers.json).

**B2 an ~80 min outage became permanent, silent loss; coverage counted it as mined. FIXED.**
- Old code, reproduced: `after 8 passes of a pure outage (= 80 min): state=mined_partial, next_at in 32 years, ledger
  lines=0, coverage counts it mined: 1/1`.
- Now (pipeline/ingest/service.py `_settle`; mine.py; providers.py `AllBackendsFailed.outage`): a failed window says
  whether its chain was in an OUTAGE (every back-end skipped (frozen, disabled, budget, circuit open), down,
  overloaded or refusing access: nothing answered and was rejected) or REJECTED it (a back-end answered: invalid,
  refused, empty, a 4xx). An outage pass uses no try: the video waits (`mine_waiting`, reason `OUTAGE ...`), retried
  every 10 min for as long as the outage lasts. A rejected pass uses a try; after 3 the good windows' moments go to the
  ledger and the video is `mined_partial`, which is in MINE_DUE (retried every 6 h until 72 h after publish), never in
  TERMINAL, and never counted as mined by coverage or stats (`videos_partial` is reported apart). A skip (budget,
  freeze) is never a failure. The module docstring's "nothing is dropped" is now what the code does.
- Tests: test_service.py `test_every_back_end_down_for_any_number_of_passes_waits_without_a_try_then_completes`
  (13 passes), `test_rejected_windows_become_partial_retryable_and_never_counted_as_mined`,
  `test_coverage_never_counts_a_partial_or_waiting_video_as_mined`,
  `test_the_spend_freeze_never_falls_through_to_a_frozen_vendor_videos_wait_then_complete`; test_providers.py
  `test_a_chain_that_is_down_or_skipped_is_an_outage_not_a_rejection`.
- Real components: the drill under the freeze (DRILL below).

**B3 the GPU0 'lease' was an environment string. FIXED as the integrator directed.**
- `PP_INGEST_GPU0_LEASE_HELD` is gone (ab.py), and so is the `lease` predicate (providers.Router / make_backend /
  service.Service). `OllamaLocalBackend.enabled()` = enabled in providers.json AND `gpu0.held()` (a check, never an
  acquisition); without pipeline/gpu0.py (this worktree before the merge) it is never available, so nothing here can
  load a model on GPU0. Custody itself is main's: `LocalLLM._post` takes `gpu0.require` + `swap_to` on every request
  (4867a74a). A Gpu0Stop (BaseException) is never renamed: it propagates; the watcher only puts the video back in the
  queue (`mine_waiting`) so it is not left claimed.
- The cached LocalLLM is stopped when a cycle ends: `Router.release()` -> `OllamaLocalBackend.release()` ->
  `LocalLLM.stop()`; the watcher calls it whenever its mine loop is idle, the A/B at the end of its run.
- Tests: test_providers.py `test_the_local_back_end_needs_the_real_gpu0_lease_never_an_environment_string`,
  `test_the_local_model_is_released_at_the_end_of_a_cycle`.

**B4 one age-gated video stalled all YouTube access. FIXED.**
- Old code, reproduced: `age gate read as a RATE LIMIT: kind=rate_limited, breaker trips=1, open for 600 s; calm()
  callers in watch.py/fetch.py: 0`.
- Now (watch.py, fetch.py): the age gate is matched FIRST and is never a rate limit (`AGE_GATE_MARKS`); the bot-check
  marker is its distinctive "not a bot" (both apostrophes), no longer the prefix "Sign in to confirm you"; `probe`
  returns `age_gated` and `process` makes it terminal `unavailable` ("age-gated (needs a signed-in session)"); every
  yt-dlp answer that is not a rate limit calls `calm()`.
- Tests: test_watch_fetch.py TestYouTubeGateAgeGate (the real YouTubeGate with a stubbed yt-dlp).

## NOT BLOCKING (each: fixed, or answered with evidence)

| finding | disposition |
|---|---|
| Q1 local-first unreachable in `run` without a code edit | answered: with B3 the local back-end needs no lease argument; enabling it is one config value where the lease is held (REQUESTS R6.4) |
| Q2 vendor names outside providers.json (`== "heimdall"`, provider strings, `HeimdallMeter`, `heimdall_error_rate`, the docstring) | fixed: the meter is `spend.CreditMeter` with config section `spend_meter` (label HEIMDALL, from which the mandated "HEIMDALL SPEND AT 90%" is built); back-ends mark `"spend_meter": true`; Reply.provider comes from the config's `vendor`; stats report `metered_error_rate`. A new test reads every identifier and non-docstring string of the package and the tool for the vendor names in providers.json (`test_no_vendor_name_in_the_code_outside_the_provider_config`). Kept: the adapter classes `AnthropicBackend` / `GeminiBackend` / `OllamaLocalBackend` are wire protocols ("kinds"), excluded like providers.py from the guard. |
| Q2 `load_config` does not enforce two back-ends per role | answered: the test `test_the_real_config_under_the_spend_freeze` does (every chain >= 2). Under the freeze the callable mine back-ends are one (Heimdall; local needs the lease): the orchestrator's 05:30 order replaces "the run continues on another vendor" by "the videos queue and are mined later". |
| Q2 `daily_budget_usd` halts a back-end silently | answered: a used-up budget is a SKIP, never a failure (B2): the video waits; the skip and its reason are in the video's `reason`, `calls`-free. Budgets exist only on frozen back-ends now. |
| Q2 a circuit can stick half-open forever (validate raising non-Invalid) | fixed: any exception from a validator rejects the reply (`"the reply broke the validator: RecursionError"`), and `Router.run` records a failure on any exception out of `_try`, so no probe is left in flight. Test: `test_a_validator_that_crashes_rejects_the_reply_and_never_leaves_a_probe_in_flight`. |
| Q2 the meter measures the right account? | answered: the gateway keys are one account shared by the fleet; /credits is the fleet's spend, which is what the $460 cap is (PHASE3_FLEET_LOAD.md). Measured: total_usage rose $0.13 between 05:33 and 06:05 ET while this watcher made no Heimdall call. |
| Q3 crash between append and set_state re-appends | answered (as in C2_CONSENSUS.md): the contract de-duplicates by moment_id, the latest line wins; re-mined lines are byte-identical replies from the cache; a partial video's retries append only when they mine more windows. |
| Q3 no single-instance guard (`once` beside `run`) | fixed: `Service` holds an flock on `<store>/ingest/service.lock` and raises `ServiceBusy` before recovering anything. Test: `test_one_service_per_store` (the live MINING row is untouched). |
| Q3 `seal` only at start: a failed write mid-run glues the next line | fixed: `append` closes a torn tail under its own lock before writing. Test: `test_append_closes_a_torn_tail_left_by_a_failed_write_in_a_live_process`. |
| Q3 the second observation's risk flags discarded | fixed: union of risk / names_person / altcoin, conjunction of about_bitcoin (fail closed, L-u). Reproduced on the old code (`risk=[]` though the second observation flagged ad_read). Test: `test_a_range_seen_twice_keeps_every_observations_flags`. |
| Q3 `append` does not run `line_problems` | fixed: one bad line and nothing is written (ValueError; the video waits with the reason). Test: `test_append_refuses_a_bad_line_and_writes_nothing`. |
| Q3 `offset_before` "0 when in doubt" not implemented | fixed: the service now stamps `mined.at` under the append lock (`ledger.append(stamp=...)`), so the file is in mined.at order by construction; lines written before carry their pass's start, out of order by at most one pass, which the reader's 1-day margin covers (a skipped line is older than both `since` and the 72 h horizon). The docstring states exactly this. Tests: `test_the_service_stamp_puts_the_file_in_mined_at_order`, `test_the_bounded_read_is_exact_while_lines_are_out_of_order_by_less_than_its_margin` (1 h and 20 h of disorder, five `since` values). |
| Q3 `best_unused_moments` skips opt-out / registry at its defaults | fixed: left out, both are read from their files; an unreadable opt-out list refuses the read. Test: `test_the_exclusions_are_never_skipped_by_default`. |
| Q3 ids deterministic; text verbatim; timing labels | answered: ids are the contract's formula; text is `eligibility.spoken` of the record's tokens (pp-selectid's definition, fingerprinted per line); `timing` is "segment" for captions (`duration_s` null, `duration_estimate_s` set) as the contract defines it. |
| Q4 overrides.json can point the bearer key anywhere; urllib forwards it on redirects | fixed: a base-URL override is honoured only for this machine or the configured host (refusals logged); every redirect is refused (`redirect` kind), so the key never follows one. Tests: `test_a_runtime_override_may_point_only_at_this_machine_or_the_configured_host`, `test_a_redirect_is_refused_so_the_key_never_follows_it` (a live local 302 server). |
| Q4 vendor error bodies persisted | fixed: every key value of the env file is redacted from error text and raw bodies before they are recorded (calls, replies_log, the meter's last_error). Test: `test_error_text_is_redacted_of_every_key_before_it_is_recorded`. |
| Q4 a literal `</sentences>` closes the untrusted block | fixed: '<' in untrusted text (rows, channel, title; the A/B lists too) is shown as '‹'. Measured: 0 of 410,156 caption segments of both stores contain '<', so no prompt or cache key changes. Test: `test_untrusted_text_cannot_close_the_sentences_block`. |
| Q4 ab.py `_fmt` lists outside the SECURITY block | fixed: both list blocks carry the notice and quote the text the same way. |
| Q4 the rejection reason appended unquoted | fixed: quoted as JSON and labelled data. Test: `test_an_invalid_reply_is_asked_again_with_the_reason`. |
| Q5 `write_state_notice` rewrites STATE with no lock, on every start | fixed: rewritten only when its text changes, under an flock beside the NOTIFY log. Test: `test_ok_leaves_a_clean_state_untouched_not_even_rewritten`. |
| Q5 `contract._load_file` writes `__pycache__` into pp-selectid | fixed: bytecode writing is off during that import. The two .pyc files there dated 02:51 may be this session's earlier loads; left in place (gitignored caches, regenerated by Python; another session's tree is not this session's to edit). |
| Q5 `handoff --apply` leaves `.handoff.tmp` when `os.link` fails | fixed: the temp file is removed in a `finally`. |
| Q5 private APIs (`ts._ytdlp`, `_vdir`, `_write_once`, `_store`, `_log_attempt`, `LocalLLM._post`) | answered: deliberate (the SAME record format by construction, through the store's own writer); proposed public aliases in REQUESTS R8. |

## DRILL (real components, under the spend freeze)
Scratch store, channel swan_bitcoin, 11:06-11:13 UTC: Heimdall's URL dead for 10 mining passes: both videos
`mine_waiting` "OUTAGE ... no try used", mine_tries 0, 24 refused calls ($0), 0 calls to a frozen vendor; URL restored:
the breaker's half-open probe found Heimdall and both were mined 328 s later (3 calls, $0.00065).
docs/audits/parallel/pp-ingest_audit/drill_freeze_20261112.json (tests/ingest/drill_freeze.py).

## THE CROSS-LLM AUDIT OF THIS CHANGE (under the freeze)
OpenAI, xAI and Google are frozen, so the reviewers were four model families served by Heimdall: qwen3.8-27b,
glm-5.3-flash, muse-spark-open-816b (minimax-m3.1-flash answered empty twice). Cycle 1: docs/audits/parallel/
pp-ingest_audit/freeze/C1_CONSENSUS.md. Fixed from it: the ledger is in mined.at order by construction (mined.at
stamped under the append lock), the outage count in SQL, the `calls` indexes, a partial video's later passes always
append what they mine and an outage pass keeps its count, caption downloads respect the yt-dlp breaker, a stop inside
a fetch never strands a video, L-x's two back-ends per role checked by `load_config`, an interrupt never counts as a
back-end failure, the local model never stopped under a request, an unmeasured coverage report retried hourly, and an
outage longer than 30 min noticed at the top of STATE. Cycle 2: docs/audits/parallel/pp-ingest_audit/freeze/
C2_CONSENSUS.md. Tests: 161.
