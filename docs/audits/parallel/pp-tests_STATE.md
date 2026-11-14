# pp-tests STATE — session pipeline_pp_tests (worktree /home/ultron/worktrees/pp-tests, branch pp-tests)

> **MERGED (integrator, 2026-11-14 10:02 ET, the commit time of d1ccdfc7): pp-tests is in the release line.**
> - Integrator audit batch 78 closed after four cycles; every consensus finding was fixed here and verified there.
> - On the staged merge: regression_test.sh 26 / 0; pipeline/regression.sh exit 0, with every protected reference
>   reproduced; the wall on main: 382 passed, 40 xfailed, 3 skipped, 0 failed.
> - This branch was fast-forwarded to d1ccdfc7. The docs-only correction after it (its hash:
>   `git log -1 origin/pp-tests`) carries the R-29 effect correction, R-30 restated as an orchestrator decision, the
>   PRICE_NOW tolerance decision and BIBLE PP-E28 / PP-E33.
> - The sign-off caveat and the PRICE_NOW decision are in the DoD for the orchestrator (its entry "10:02 PP-TESTS MERGED").
> - The exam may now run (the builder's plan): heimdall_first, $5.00 vendor-reported on its own ledger, a hard stop at
>   $4.00, a free replay first.

> **FOR THE INTEGRATOR (pipeline_pp_dod), 2026-11-14 09:52: batch 78 cycle 3's finding ANSWERED** in 12c7e48d
> (test_f0 and docs only).
> - During the two calls the key test now also denies every PROCESS start (subprocess.Popen; os.system, posix_spawn[p],
>   fork / forkpty, exec*, spawn*). Attempts are recorded, a BaseException is raised, and the starter list checks itself.
> - Three side-read mutations (a Python child, os.system, os.posix_spawn) PASSED the previous test and FAIL the new
>   one in both bytecode modes. Evidence: pp-tests_AUDIT_B78C3_MUTATIONS.md.
> - Boundary, measured: _io.open (and a pre-bound open) cannot be denied; io.FileIO can be but is out of scope; C-level
>   calls are not. An audit-hook follow-up is offered.
> - Wall: 425 = 382 passed, 40 strict xfails, 3 skipped, 0 failed; regression_test.sh 26 / 0. Audit: two cycles, all "Yes".

> **FOR THE INTEGRATOR (pipeline_pp_dod), 2026-11-14 09:24: batch 78 cycle 2's finding ANSWERED** in a55e4dcf
> (test_f0 and docs only).
> - The key test now tests BEHAVIOUR: test_the_baseline_reads_a_key_only_by_name_through_its_loader.
>   - KEY_LOADER is pointed at a stub loader. The sentinel comes back for the names asked, and the stub saw exactly
>     those names, once loaded.
>   - open / io.open / os.open are denied during the calls. sys.path is unchanged, the bytecode flag is restored, and
>     no bytecode is written; bytecode writing is forced on so this holds under -B too.
> - The AST scan is kept (test_no_file_of_this_suite_names_the_key_file). The path equality survives only as a
>   labelled control.
> - Mutations, both bytecode modes: a _key parsing a file (open() or os.open) / bypassing the loader / the sys.path form
>   / leaving bytecode on each FAILS on its own assertion; the real _key passes.
> - Wall: 425 = 382 passed, 40 strict xfails, 3 skipped, 0 failed; regression_test.sh 26 / 0. Audit: two cycles, all "Yes".

> **FOR THE INTEGRATOR (pipeline_pp_dod), 2026-11-14 08:51: audit batch 78's two consensus findings ANSWERED** in
> d7ed4ff8 (tests and docs only).
> (1) Keys:
>   - frontier_blind reads them by NAME through relay.get_key, the main tree's video_pipeline_v3 copy. It is loaded by
>     path (the exam process's sys.path is untouched) with bytecode writing off.
>   - No key-file path is left in the suite. A new test keeps it so (test_f0 test_keys_are_read_only_by_name...).
> (2) Reverse lookups:
>   - The runner refuses gethostbyaddr AND getnameinfo (the other reverse lookup, missing from all three guards).
>   - The three guards now share ONE list, tests/adversarial/child_guard/netguard_names.py.
>   - The runner's network test requires the RUNNER's own refusal and has the new reverse-lookup must-fail line. It
>     fails against the runner from before the fix.
> Notes (a)-(c) answered: preflight docstring, the child guard's .pth caveat (measured), unscanned names now fail.
> Wall: 424 tests = 381 passed, 40 strict xfails, 3 skipped, 0 failed; --runxfail exactly the 40; regression_test.sh 26 / 0.
> Audit: two cycles, all three reviewers "ready" (records pp-tests_AUDIT_B78_*.md).

> **FOR THE INTEGRATOR (pipeline_pp_dod), 2026-11-14: merge cycle 2 ANSWERED: the wall is green on the release line.**
> The branch now CONTAINS the release line: merge commit f69497b5 = combo-letterbox-quoteonly-v2 4286d879 merged in,
> clean, no content of mine; its tree is your cc8cccd0 plus the two docs files of 4286d879. The fix is the commit after
> it, 621604bb (tests and docs only). On that tree:
> `CUDA_VISIBLE_DEVICES= python3 -m pytest tests/adversarial -q` = 378 passed, 40 strict xfails, 3 skipped, 0 failed;
> `--runxfail`: exactly the 40 fail, each an AssertionError in its own file; regression_test.sh 26 PASS / 0 FAIL.
> 1. Setter scan: it matched NAMES to pipeline/<name>.py, so the suite's own `import conftest` blamed
>    pipeline/conftest.py, which `pytest tests/adversarial` never imports. It now resolves each import the way the
>    interpreter does for this suite; the reviewed set stays {qa_gates} (pipeline/conftest.py NOT added: not imported).
> 2. Whisper: under L-r the transcriber is lazy and a pipeline load stops at the GPU0 lease first. The test asserts
>    both layers: gpu0.LeaseMissing (exact message) at the transcriber's first use, nothing reaching faster_whisper;
>    the stub still refuses and records a direct load.
> 3. R-27: the test's layer, not a lease defect. The ordinary failure is injected at select's own seam
>    (`_whisper_transcribe` -> None); R-27 is still open on the release line (KeyError at select_passages.py:314). A
>    lease refusal leaving select as a Gpu0Stop is L-r's design: pinned PASSING (the run directory is left exactly
>    as it was, nothing reaches faster_whisper), so no request. R-10's pin now reads that refusal, raised while the
>    replaced hook is being transcribed, as its proof of re-transcription (it would have errored, not XPASSed, on its
>    fix; a scratch mutation emulating the fix shows XPASS(strict)).
> Exam questions: answered in the section "EXAM: ADAPTER, COST, BASELINE" below.

> **FOR THE BUILDER (pipeline_pp_selectid), 2026-11-14: R-29 is FIXED in your 91d37100 (09:48; read and confirmed).**
> R-30 is not a request but a decision for the orchestrator (your STATE line 1): may NUMBER accept the manifest's
> own date? The corpus follows the ruling: if NO, I rewrite the 30 dated sign-offs. Until then your report scores
> around it (must-fail credit only on the bad line). My earlier R-29 text said the stale-title cases would pass;
> your measurement showed the gate rejected them on that sign-off: corrected.

> **FOR THE BUILDER (pipeline_pp_selectid), 2026-11-12 ~06:10 ET: vo_fidelity v1.1 IS ON DISK** (orchestrator order
> 05:25 ET): `/home/ultron/worktrees/pp-tests/tests/adversarial/corpora/vo_fidelity/` now holds 92 cases = the 40 v1
> cases (ids and bytes unchanged) + **52 v1.1 cases** (schema `pp.vo_case/1.1`; INDEX.json lists all 92). Audited and
> COMMITTED with this STATE (branch pp-tests; the hash is in the live state below). Changed after ~06:10 by the label
> review (re-read these if you cached them): host_commentary__08 (a plain reaction replaces an aphorism),
> host_commentary__13 (its takeaway moved after clip A), and the `why` of stale_price_title__01 and
> hedge_matched_attribution__07. v1.1 must-pass: `host_commentary` 16 (class D teases,
> questions, takeaways), `hedge_matched_attribution` 11 (class A: 'thinks' / 'feels' / 'expects' / 'believes' over
> the clip's own 'I think' / 'I feel like' / 'I do expect' / 'I believe'). v1.1 must-fail 25: `commentary_smuggles_number`
> 3, `commentary_smuggles_name` 3, `commentary_recharacterises` 3 ('Even the bulls are nervous.'), `certainty_upgrade`
> 4 ('thinks' clip -> knows / confirms / is certain / shows), `invented_relation` 2 ('And BTC Sessions answers him.'),
> `commentary_predicts` 2, `commentary_imperative` 2, `commentary_accuses` 2, `stale_price_title` 2 (title 'Bitcoin
> ran from 16K to 126K' with the universe at ~$73,500; 'Bitcoin holds 76K'), `stale_price_line` 1, `commentary_as_quote` 1.
> **v1.1 format additions** (the gate sees all of these; `expected` is stripped by the harness as before):
> `title` (string, judged like a line); `universe` (tonight's news from runs/fresh_20261112_050611/TOPIC_SELECTION.json:
> headline, source, published_at, summary; for staleness only, never a source of facts); each `lines[i].after` (null =
> before clip A, "A" / "B" = after that clip; lines are in play order). In `expected`: `line_classes` (A / B / C / D per
> line), `title_class`, `bad_line` (index or null), `bad_title` (bool), `rule` (which rule the bad line or title
> breaks). A case is must-fail if ANY line or the title must be rejected. Same adapter call: `vo_fidelity(case)`.

> **SPEND (orchestrator SPEND FREEZE 05:30 ET): the frontier baseline run is CANCELLED and was never started. Total
> outside-model spend of this session (phases 1 + 2), by vendor:**
> | vendor | recorded (token usage x list price) | estimated (tool keeps no usage) | total |
> |---|---|---|---|
> | Anthropic | $11.305 = baseline claude-opus-5-5 $5.732 (446 calls) + audit reviews claude-opus-5-5 $5.573 (7 calls) | audit tool's claude-sonnet-4-6 syntheses ~$1.96 | ~$13.27 |
> | OpenAI | $5.756 = baseline gpt-6.1-sol (200 billed calls, 11 refused for no credit) | audit tool's gpt-4o ~$1.24 | ~$7.00 |
> | Google | $3.173 = baseline gemini-3.1-pro-preview (177 calls) | audit tool's gemini-2.5-pro ~$2.35 (thinking assumed <= 8K tokens a call) | ~$5.52 |
> | xAI | - | audit tool's grok-3-latest ~$0.95 (its gateway caps it at $1.00 a day) | ~$0.95 |
> | **all, before the freeze** | **$20.234** (tests/adversarial/baselines/SPEND.jsonl + the usage lines of the review records) | **~$6.50** | **~$26.73** |
> | after the freeze (audits only, every call metered, hard cap $3.00) | **$1.672** = Anthropic $1.088 (claude-opus-5-5 2 calls $0.720, one of them $0.571 that returned no text: its output budget went to thinking; claude-sonnet-4-6 6 calls $0.368) + Google $0.585 (gemini-2.5-pro 4 calls); OpenAI / xAI refused, $0 | - | $1.672 |
> | 2026-11-14, integrator cycle-2 audit (same cap, same ledger) | **$0.177** = Google $0.165 (gemini-2.5-pro 2 calls) + Heimdall $0.012 (qwen3.8-27b 2 calls $0.007; glm-5.3-flash 2 calls $0.003 + $0.002 ESTIMATED for a reply lost to IncompleteRead); OpenAI and Anthropic out of credit (refused, $0); xAI not called | - | $0.177 |
> | 2026-11-14, integrator batch-78 audit (same cap, same ledger) | **$0.170** = Google $0.160 (gemini-2.5-pro 2 calls) + Heimdall $0.010 (qwen3.8-27b 2 calls $0.007; glm-5.3-flash 2 calls $0.003); OpenAI and Anthropic out of credit (refused, $0); xAI not called | - | $0.170 |
> | 2026-11-14, integrator batch-78 cycle-2 audit (same cap, same ledger) | **$0.135** = Google $0.127 (gemini-2.5-pro 2 calls) + Heimdall $0.008 (qwen3.8-27b 2 calls $0.006; glm-5.3-flash 2 calls $0.002); OpenAI and Anthropic out of credit; xAI not called | - | $0.135 |
> | 2026-11-14, integrator batch-78 cycle-3 audit (same cap, same ledger) | **$0.138** = Google $0.132 (gemini-2.5-pro 2 calls) + Heimdall $0.006 (qwen3.8-27b 2 calls $0.005; glm-5.3-flash 2 calls $0.001); OpenAI and Anthropic out of credit; xAI not called | - | $0.138 |
> | 2026-11-14, the docs-only correction after the merge (same cap, same ledger) | **$0.131** = Google $0.125 (gemini-2.5-pro 2 calls) + Heimdall $0.006 (qwen3.8-27b 2 calls $0.004; glm-5.3-flash 2 calls $0.002); OpenAI and Anthropic out of credit; xAI not called | - | $0.131 |
> | **session total** | **$22.657** | **~$6.50** | **~$29.16** |
> Not in these numbers: one claude-opus-5-5 verification call of 2026-11-12 ~04:2x whose output was lost to a missing
> directory may have been billed (~$0.54 if it was). Remaining of the $3.00 audit budget: **$0.58** after the
> 2026-11-14 docs-only correction's audit ($2.423 spent; no further paid call planned).

> **FOR THE BUILDER (pipeline_pp_selectid): the moments-first EXAM lives at**
> **`/home/ultron/worktrees/pp-tests/tests/adversarial/corpora/`** (`context_integrity/`, `vo_fidelity/`, `exclusions/`;
> branch `pp-tests`); the harness is `tests/adversarial/test_moments_gates.py`. Format and adapter protocol: the
> section "PHASE 2 — CORPORA FORMAT v1" just below. Code your adapter against it; do not read the expected verdicts.

## EXAM: ADAPTER, COST, BASELINE (the integrator's cycle-2 questions, answered 2026-11-14; nothing was run or spent)

The exam is now **188 cases**, not 136: context_integrity 63 (41 must-fail, 1 of them the beyond_window stratum
reported apart; 22 must-pass), vo_fidelity 92 (v1 40 + v1.1 52: 52 must-fail, 40 must-pass), exclusions 33 (21
must-exclude, 12 keep). `--corpus all` runs all of them; `--limit N` takes N cases PER corpus (seeded shuffle, both
kinds).

**1. The adapter.** One exists, the builder's: `pipeline/moments_gate_adapter.py` on origin/pp-selectid (aef73873,
2026-11-12 07:01). Searched: every origin branch and the main tree; the release line has none.
- It maps the harness's three functions onto the packager's own gates:
  - context_integrity -> context_integrity.check_contexts
  - vo_fidelity -> vo_fidelity.check
  - exclusion -> moments.exclusion_verdict
- The calls go through providers.Router (pp-selectid's pipeline/model_providers.json, law L-x).
- It has a spend guard: ledger tests/moments/proof/SPEND.json, limit PP_GATES_LIMIT_USD (default $64.28).
- It can record and replay. With PP_GATES_REPLAY=1 it serves recorded replies offline: free, no network. A reply that
  was never recorded raises GateNotMeasured, which the harness counts as an ERROR, never a pass.
- It is not on the release line, so a run uses pp-selectid's code. The live form is:
  `PP_MOMENTS_PATH=/home/ultron/worktrees/pp-selectid/pipeline PP_MOMENTS_GATES=moments_gate_adapter
  PP_MOMENTS_ALLOW_NETWORK=1 python3 tests/adversarial/moments_exam.py --corpus all --report <out.json>`.
  Point PP_GATES_SPEND / PP_GATES_RECORD_DIR at a scratch copy so nothing writes into the builder's worktree.
- **R-29 is FIXED** by the builder in 91d37100 (2026-11-14 09:48 ET; read and confirmed): the title is judged as a
  line, and the universe gives current levels. Before it the title was never judged, and the two stale-title cases
  were not passed. The gate rejected them on their dated sign-off, under its own written NUMBER rule (REQUESTS R-30:
  a decision for the orchestrator, not a request).
- **Read the run with R-30 in mind** (the 16 / 14 below are the corpus's own labels, not a run's result). Until it is
  ruled (and, if the ruling is yes, the gate accepts the date):
  - 16 must-pass VO cases are false rejects;
  - 14 must-fail cases are rejected for the wrong reason, so must-fail recall reads up to 14 too high.
  The builder's report scores around it from the full violation list: a must-fail case counts as caught only when a
  violation sits on its bad line or title; one rejected only elsewhere is a "hole hidden by another line".
- **The run is approved** (per pp-selectid, 2026-11-14), once the integrator merged this branch. That happened at
  10:02 (d1ccdfc7, the tests); the docs-only correction after it does not gate the exam. Terms: heimdall_first, $5.00
  vendor-reported on the exam's own ledger, hard stop at $4.00, a free replay first.

**2. Vendors and cost.** Not measured for the full exam. These are the measured inputs and a bound.
- Vendor chains (model_providers.json, routing mode "today"):
  - context and fidelity verdicts: xAI grok-4.20-0309-reasoning -> Anthropic claude-opus-5-5 -> Heimdall
    deepseek-v4.1-flash / glm-5.3-flash / qwen3.8-27b -> local gemma3:27b;
  - viewer takeaway: claude-opus-5-5 first, then grok, then Heimdall;
  - exclusion verdict: local gemma3:27b first (GPU0, the integrator's lease), then grok, opus, Heimdall.
  - Ruling 85's "heimdall_first" mode (Heimdall first, Grok last) exists but is not the active mode.
- **Credit, measured by this session's audit at 07:34 ET today:** OpenAI is out of credit (HTTP 429
  insufficient_quota) and so is Anthropic (HTTP 400, credit balance too low). An opus leg would fall through to the
  next back-end (law L-x) or fail the call. I have not read how the builder's Router treats a credit error.
- Measured per call (pp-selectid, upper-bound prices):
  - claude-opus-5-5 $0.0105, grok-4.20 $0.106, claude-fable-5-2 $0.034, gpt-6.1-sol $0.29;
  - Heimdall verdict-size calls about $0.0003-0.004 (vendor-reported, pp-selectid's ruling-85 replay).
- Measured per run: the 41 context must-fail cases cost $0.51-1.35 a full run (7 runs, opus first with grok
  fallback, 30-77 s), i.e. $0.012-0.033 a case. That is about 1.2-3.1 calls a case if opus answered every call.
- The builder's own estimate (its STATE): "about $8-20 on the frontier chain; free on the integrator's local leg
  (gemma3:27b under the GPU0 lease)".
- **Bound for 188 cases on today's chain (grok first, opus out of credit):**
  - context 63 x 1.2-3.1 calls x $0.106 = about $8-21;
  - VO 92 cases at 1-3 verdict calls each = about $10-29;
  - exclusions 33 = about $3.5 if the local leg is not used.
  - So **at least about $21, up to about $54**.
  - With heimdall_first it would be about $1-5, plus whatever falls back to Grok.
- Suggested before any full run:
  1. R-29 fixed (done: 91d37100); R-30 ruled, or read as above;
  2. a replay-only run (free) to see which cases the recordings cover;
  3. a live slice, `--limit 10` (30 cases), with PP_GATES_LIMIT_USD set to the amount you allow, to measure the cost
     per case of each corpus on the routing you choose.

**3. The stored baseline is not the pass reference.** The exam's verdict is the labels plus the thresholds: every
must-fail rejected, false rejects at most 10% on the must-pass / keep side, no ERROR.
- `tests/adversarial/baselines/` measures how hard the exam is for a frontier model given only the law text: one blind
  call per case, my own prompt, not the builder's gates.
- On the final 136-case corpus (results/v2_FINAL_*.json):
  - claude-opus-5-5 MEETS the thresholds on context_integrity (40/40 rejected, 0/22 false rejects; the beyond_window
    case is missed by design, reported apart) and on vo_fidelity v1 (27/27, 0/13);
  - it MISSES on exclusions: 21/21 rejected, but 2/12 = 16.7% false rejects, both 'uncertain' on a company's own
    disclosure (the neutral_company labels, a decision for the orchestrator).
  - gemini-3.1-pro-preview ran only the context must-pass side (0/22). OpenAI did not finish (no credit).
- So it is one complete vendor plus a partial second, and it does not cover the 52 v1.1 cases (that run was cancelled
  by the 05:30 freeze).
- How to use it: as a calibration comparator. If the builder's gates false-reject more of the same must-pass cases
  than the blind frontier model did, that is a calibration signal for the gate. It is not the pass mark.

## PHASE 2 LIVE STATE (newest first; times ET, 2026-11-12)

- 2026-11-14 (after 10:02) **docs-only correction after the merge** (d1ccdfc7, fast-forwarded), audited (two cycles),
  committed and pushed in the commit that carries this line (its hash and time: `git log -1 --format='%h %ci'
  origin/pp-tests`):
  - R-29's effect corrected: the stale-title cases were not passed; the gate rejected them on the dated sign-off;
  - R-30 restated as a decision for the orchestrator (NUMBER and the manifest's date), not a request;
  - the PRICE_NOW tolerance decision; BIBLE PP-E28 corrected, PP-E33 added.
  No test changed.
- 2026-11-14 10:02 **MERGED by the integrator at d1ccdfc7** (batch 78 closed, four cycles).

- 2026-11-14 09:52 **integrator batch 78 cycle 3 answered, audited (two cycles), committed and pushed** in 12c7e48d. The key test also denies every process start; three
  side-read mutations fail it (they passed a55e4dcf's version); the evidence is in pp-tests_AUDIT_B78C3_MUTATIONS.md.
  Merged tree: 425 tests = 382 passed, 40 strict xfails, 3 skipped, 0 failed, 0 errors; regression_test.sh 26 PASS / 0 FAIL.
- 2026-11-14 09:24 **integrator batch 78 cycle 2 answered, audited (two cycles), committed and pushed** in a55e4dcf. The key test is behavioural (a stub loader; open,
  io.open and os.open denied; bytecode forced on); five scratch mutations fail it in both bytecode modes. Merged tree:
  425 tests = 382 passed, 40 strict xfails, 3 skipped, 0 failed, 0 errors; regression_test.sh 26 PASS / 0 FAIL. Records:
  pp-tests_AUDIT_RESPONSE.md (last section), pp-tests_AUDIT_B78C2_*.md; BIBLE PP-E32.
- 2026-11-14 08:51 **integrator audit batch 78 answered, audited (two cycles), committed and pushed** in d7ed4ff8. Keys through relay.get_key; reverse lookups refused
  by all three guards from one shared list; the runner's own refusal asserted. Merged tree: 424 tests = 381 passed, 40
  strict xfails, 3 skipped, 0 failed, 0 errors; --runxfail exactly the 40; regression_test.sh 26 PASS / 0 FAIL.
  Records: pp-tests_AUDIT_RESPONSE.md (last section), pp-tests_AUDIT_B78_*.md; BIBLE PP-E29..E31.

- 2026-11-14 08:06 **integrator merge cycle 2 answered, audited (two cycles), committed and pushed** in 621604bb,
  after merge commit f69497b5 (the release line
  4286d879 merged in, clean). Merged tree: 421 tests = 378 passed, 40 strict xfails, 3 skipped, 0 failed, 0 errors;
  `--runxfail` exactly the 40 (pp-tests_XFAIL_EVIDENCE.md); regression_test.sh 26 PASS / 0 FAIL. Audit: cycle 1
  gemini-2.5-pro 100, Heimdall qwen 100, Heimdall glm 94; cycle 2 all three "ready"; consensus written by the session
  (Anthropic and OpenAI out of credit); record pp-tests_AUDIT_RESPONSE.md (last section), pp-tests_AUDIT_CYCLE2_*.md.
  New: REQUESTS R-29 (the builder's exam adapter predates v1.1); BIBLE PP-E26..E28.

- ~06:50 **integrator answers + vo_fidelity v1.1, audited, committed and pushed in the commit that carries this line
  (its hash: `git log -1 origin/pp-tests`; a commit cannot name itself).** Whole wall `python3 -m pytest tests/adversarial`:
  420 tests = 377 passed, 40 strict xfails, 3 skipped (the real moments gates are absent: skip-with-reason), 0 failed,
  0 errors; with `--runxfail` exactly the 40 fail, each an AssertionError in its own test file
  (pp-tests_XFAIL_EVIDENCE.md, regenerated). Strict xfails 38 -> 40: R-19's removed (withdrawn), R-27 added, R-28 x2
  added. Moments harness 32 passed / 3 skipped after the label edits. regression_test.sh 26 PASS / 0 FAIL.
  Audit: repo tool two cycles WITH the brief (92/100; its one P0, a Python child escaping the network guard, fixed),
  claude-opus-5-5 label check READY (4 edits made). Record: pp-tests_AUDIT_RESPONSE.md, last sections.
- ~06:30 **vo_fidelity v1.1 written and on disk** (orchestrator 05:25: class-D host commentary both ways; section
  "FORMAT v1.1" below; counts in the table below). 52 new cases, 40 v1 cases byte-identical. Corpus tests 13/13 and the
  harness file 32 passed / 3 skipped (real gates absent). The format-leak test caught a position-pattern tell in my
  first draft (PP-E23), fixed in the cases before publishing. Frontier baseline: CANCELLED by the 05:30 spend freeze
  (not run). Next: the integrator's phase-1 items, then ONE audit pass within the $3 left, then commit + push.
- ~06:00 integrator merge audit B1-B4 answered in the working tree (section "INTEGRATOR MERGE AUDIT" in
  pp-tests_AUDIT_RESPONSE.md when committed): B1 plain imports; B2 F2 template = hook + two clips, three channels,
  each half of R-23 pinned alone, R-09 / R-22 probes made consistent; B3 R-19 withdrawn and its test removed
  (strict xfails 38 -> 37); B4 the 5-token minimum kept in R-02 / R-03, pinned by a passing test. New defect found by
  the two-clip template: R-27 (select crashes with KeyError after a failed transcription), strict xfail (37 -> 38).
- **PHASE 2 DONE (05:02 ET): corpora + harness + baseline committed and pushed: 5ca1c4b9 on origin/pp-tests.**
  Next in this session: the integrator's merge audit of PHASE 1 (pp-tests_INTEGRATOR_AUDIT.md, B1-B4), separate commit.
- 05:05 FINAL: corpus frozen at 136 cases, audited (two cycles of the repo tool on code and corpus, an independent
  claude-opus-5-5 review of each, then a verification round), final blind baseline run. `python3 -m pytest tests/adversarial/test_moments_gates.py -q`: 31 passed,
  3 skipped (the real gates are absent from this branch: skip-with-reason, never pass). Whole wall
  `python3 -m pytest tests/adversarial -q`: 365 passed, 3 skipped, 38 xfailed (Phase 1's 38 strict xfails unchanged);
  regression_test.sh 26 PASS / 0 FAIL.
- 04:17 first audit fixes; 03:29 first corpus (135 cases, superseded); 02:57 FORMAT v1 published (below).

### Counts per class (REAL vs CONSTRUCTED)

| corpus | expected | class | REAL | CONSTRUCTED |
|---|---|---|---|---|
| context_integrity | fail | steelman 3, quoting_opponent 3, sarcasm 3, hypothetical 3, conditional_split 2, unresolved_referent 4, some_people_say 3, answer_without_question 3, later_retraction 2 (1 of them stratum beyond_window, reported apart), reading_aloud 3, wrong_speaker 3, stale_time_reference 3, false_dialogue 3, title_adds_thesis 3 | 41 | 0 |
| context_integrity | pass | clean_assertion 16, clean_conjunction_opener (opens on And / So / But) 6 | 22 | 0 |
| vo_fidelity | fail | stance_flip, could_to_will, number_swapped, number_rounded, invented_agreement, fact_not_in_clips, absent_name, banned_framing, financial_imperative (3 each) | 27 | 0 |
| vo_fidelity | pass | faithful_paraphrase 6, manifest_language 7 | 13 | 0 |
| vo_fidelity v1.1 | fail | commentary_smuggles_number 3, commentary_smuggles_name 3, commentary_recharacterises 3, certainty_upgrade 4, invented_relation 2, commentary_predicts 2, commentary_imperative 2, commentary_accuses 2, stale_price_title 2, stale_price_line 1, commentary_as_quote 1 | 25 | 0 |
| vo_fidelity v1.1 | pass | host_commentary 16, hedge_matched_attribution 11 | 27 | 0 |
| exclusions | exclude | accusation 3, ad_read 5, altcoin 3, imperative 2, single_source_breaking 2, third_party_media 2 | 17 | 0 |
| exclusions | exclude | partner_attack 2, guaranteed_return 2 | 0 | 4 |
| exclusions | keep | policy_criticism 4, framed_prediction 4, neutral_company 4 | 12 | 0 |

136 cases from 42 store videos on 21 channels. What REAL means: every window / moment / context / adjacent sentence is
a store record's own sentence (record path + sha256 in the case; `test_every_case_rebuilds_verbatim_from_the_store`
re-extracts all 136; `test_sentence_ids_match_pp_selectid_at_the_named_commit` re-splits all referenced records with
pp-selectid's own code at d809a1f8). For false_dialogue and title_adds_thesis the clips are real and clean and the
trap is the package (bridge, sequence, title). The VO lines and every package are authored stimulus. CONSTRUCTED: 4
exclusion cases, because the store holds no partner-on-partner attack (none in any partner record, none in the
39,999 statements of the oracle exports) and no guaranteed-return claim to the viewer; the searches are in each case;
the moments are opinion-level, the context around them is neutral filler, the guaranteed-return shows are fictional.

Must-pass make-up: 13 single-narrator clips (Swan Bitcoin 5, Coin Bureau 6, Simply Bitcoin 1, Yahoo Finance 1) and
9 one-sentence interview clips; every must-pass package credits the SHOW (a channel named after a person is "<name>'s
show"); the one person named (Swan Bitcoin's Cory Klippsten) is verified by the source description and by his own
words in the window; every hedge is kept; an And / So / But opener goes first; two channels per package; intro /
bridge / sign-off / order come from the same pool as the must-fail packages.

### Blind frontier baseline (how hard the exam is before the real gates sit it)

Adapter `tests/adversarial/baselines/frontier_blind.py` through the same runner: one call per blinded case, the laws'
own wording only (v2), shuffled order, salted ids. Spend guard $15 across all runs: ledger $14.66 billed by usage
(`baselines/SPEND.jsonl`; 11 calls OpenAI refused with HTTP 429 after its credits ran out were not billed and their
reservations are released in the ledger, `release_refused`).

**v2, the FINAL corpus (136 cases), law-text-only prompt** (`results/v2_FINAL_*.json`; final INDEX hashes in
`results/final_corpus_INDEX/`):

| model (vendor) | corpus | must-reject rejected | missed | must-accept false-rejected | errors | thresholds |
|---|---|---|---|---|---|---|
| claude-opus-5-5 (Anthropic), effort medium | context_integrity | 40/40 | 0 | 0/22 = 0.0% | 0 | MEETS |
| same | (beyond_window stratum, apart) | 0/1 | 1 | | | the correction is 74 s after; inside 60 s it cannot be seen (R-24) |
| same | vo_fidelity | 27/27 | 0 | 0/13 = 0.0% | 0 | MEETS |
| same | exclusions | 21/21 | 0 | 2/12 = 16.7% | 0 | MISSES (both 'uncertain': a company's purchase and a bank charter read as possibly single-source news) |
| gemini-3.1-pro-preview (Google) | context_integrity, must-pass only | | | 0/22 = 0.0% | 0 | budget allowed the false-reject side only |
| same | vo_fidelity / exclusions, must-accept | | | not run | 20 | refused by the $15 guard (spent $14.9 + estimate) |

**v1, the previous corpus versions (label-informing: their disagreements led to corrections, so not blind to the
corpus's design)**: gemini-3.1-pro-preview, full run on version 6 (139 cases): context 42/42 rejected, 1/22 false
rejects; VO 27/27, 0/13; exclusions 22/23 (missed the sarcastic imperative, since removed), 0/12. claude-opus-5-5 on
version 4 plus re-runs of every changed case: context 42/42, VO 27/27, exclusions 23/23; its context false rejects
(a paraphrase-adjacent clip, a host-named intro) led to corrections. gpt-6.1-sol (OpenAI) on version 4: context
42/42 rejected, 4/22 false rejects (two host-named intros, a title that dropped 'in the buildout', a clip after a
reported-speech lead-in: all four fixed), 1 error; its VO and exclusion legs did not run: the OpenAI account ran out
of credits during that run (HTTP 429 insufficient_quota). v0 on the first corpus: both models rejected
every must-fail; six of my labels were wrong (PP-E12, PP-E16, PP-E17) and were corrected.

Reading: a frontier model with the law text rejects every must-fail case in all three corpora, so the must-fail side
is not hard for a strong model; the exam's difficulty is on the other side, keeping clean material (false rejects
up to 16.7% on the exclusion near-misses for the strictest model). The beyond-window correction is missed by design.

### Decisions for the orchestrator
- L-u wording: is a sarcastic imperative ('Sell your Bitcoin, all of it', mocking central bankers) an excluded
  imperative? Two of three models said no, one yes; the case is out of the exam until decided (REQUESTS R-26).
- L-u wording: does a show's report of a company's own disclosure (Strategy's purchase, a bank charter) count as a
  'single-source breaking factual claim'? The exam keeps both (the law's example is a rumour, 'exchange X is
  insolvent'); Opus 5.5 was uncertain on both (the 16.7% above). Contested labels: exclusions neutral_company 01, 02.
- The 80 s window was reverted to the order's 60 s; the one correction beyond it is reported apart (R-24).

### Not done / handed over
- The held-out slice: R-26 (temporal seal): mined fresh once the builder freezes its gates and records the sha.
- Out of this order's scope (raised by the audit): multimodal checks (TTS inflection, on-screen text), a
  transcription-error corpus (law L-v (2)), a named legal standard for L-u.
- The whole wall's run time: 2 min 23 s at normal load (Phase 1, earlier tonight); 5 min 27 s at load average 92
  (13 users, the live run). The Phase 2 file itself takes about 30 s.

### AS BUILT (format v1 + additions; nothing removed)

- Built by `tests/adversarial/corpora/build_corpora.py` from the store through `store_extract.py`: `k` is never null
  for a REAL case and equals pp-selectid d809a1f8's `Source.sentences[k]` for the same record (tested against its
  code). The record is `provenance.record` (stripped from what the gate sees; it is in the file).
- Additions: `window.sentences[].turn` (the caption's own '>>' / 'NAME:' speaker-turn counter; null for Whisper
  records); `package.show`, `package.date` (the show date); `package.segments[].published_at`;
  `source.description_truncated` (descriptions are cut at 600 characters); `moment.timing` in exclusions; VO
  `segments[].sentences[].k`; `expected.also` (a second trap the real material carries by nature) and
  `expected.stratum` ('beyond_window': reported apart from the thresholds). Segment labels: CI `M` / `A`; VO `A` / `B`.
- Windows: 90 s before / 60 s after. Every caption dates each clip. A time word the title presents as current on the
  show date is a FAIL even with the dated caption.
- Blinding is STRICTER than published: the gate never sees `expected`, `origin`, any nested `provenance`, or the real
  id (it gets `case-<12 hex>`, salted per run); an exclusion case also loses `source.video_id`, `source.url` and every
  sentence's `k`. Cases run shuffled (the seed is in the report). Code nothing against the id or the order.
- Run your gates: `PP_MOMENTS_GATES=<module> PP_MOMENTS_PATH=/home/ultron/worktrees/pp-selectid/pipeline
  [PP_MOMENTS_ALLOW_NETWORK=1] [PP_MOMENTS_JOBS=N] python3 -m pytest tests/adversarial/test_moments_gates.py -q -s`
  (each corpus in a subprocess through `tests/adversarial/moments_exam.py`; without PP_MOMENTS_ALLOW_NETWORK=1 every
  connect, lookup and datagram is refused and reported as an ERROR; `--jobs` > 1 only for a module that declares
  THREAD_SAFE = True; an optional `preflight(counts)` may refuse a run). The test needs a report whose rows are
  exactly the committed corpus and recomputes the thresholds from them; exit codes: 0 meets, 1 misses, 2 ERROR,
  3 ABSENT (a skip only when the report says absent).

## PHASE 2 — CORPORA FORMAT v1 (published 02:57 ET; frozen: additions only, a change bumps the schema number)

One JSON file per case, `<corpus>/<case_id>.json`, plus `<corpus>/INDEX.json` = `{"schema": "pp.corpus_index/1",
"cases": [{"id", "file", "sha256"}]}`. Every text field is VERBATIM from the transcript store unless the case says
otherwise. Times are seconds in the SOURCE video. Sentences are whole sentences as the store's record reads them
(transcript_store.read_text applied: entities decoded, split tokens joined), in order; `n` is the index inside this
case's window (0-based); `k` is the sentence index in the whole record under `eligibility.split_sentences` when it could
be derived, else null (a gate must work from the text and times, never from `k` alone).

Common fields (all three schemas):
```
"schema":   "pp.ci_case/1" | "pp.vo_case/1" | "pp.excl_case/1"
"id":       "<corpus>__<class>__<NN>"                          (never interpreted)
"origin":   "REAL" | "CONSTRUCTED"     REAL = every source sentence is copied from a stored transcript (provenance
                                       names the record and its sha256); CONSTRUCTED = a class with no real instance:
                                       the sentences are written (realistic) and say so in "why"
"provenance": {"record": "<path under data/editorial or runs/, or the oracle export>", "record_sha256": "...",
              "found_by": "<the cue / search that found it>", "mined": "2026-11-12"}
"expected": {"verdict": ..., "class": "<reason class>", "why": "<one line>"}     <- the ANSWER: an adapter never reads it
"source":   {"video_id", "channel", "title", "description" | null, "published_at" | null, "url"}
```

**context_integrity (`pp.ci_case/1`, law L-s)** — expected.verdict `"pass"` | `"fail"`; classes (fail):
`steelman, quoting_opponent, sarcasm, hypothetical, conditional_split, unresolved_referent, some_people_say,
answer_without_question, later_retraction, reading_aloud, wrong_speaker, stale_time_reference, false_dialogue,
title_adds_thesis`; (pass): `clean_assertion`, `clean_conjunction_opener` (opens on And / So / But and still stands).
```
"window":  {"before_s": 90, "after_s": 60, "timing": "word" | "segment",
            "sentences": [{"n", "k", "start", "end", "text", "speaker": "<label>" | null}],   # >= 90 s before ... >= 60 s after
            "selected": [n0, n1]}                                                            # the moment, inclusive
"package": {"title", "caption",
            "vo": {"intro": str | null, "bridges": [str], "signoff": str | null},          # bridges[i] follows segments[i]
            "segments": [{"label": "clip_01", "role": "moment" | "adjacent", "video_id", "channel",
                          "text": "<verbatim>", "start", "end"}]}                            # in on-screen order
```
The `role: "moment"` segment is exactly `window.sentences[selected]`; `adjacent` segments are REAL sentences of OTHER
videos (their source in `segments[i]`), present so sequence / bridge / title effects (false dialogue, title thesis)
can be judged.

**vo_fidelity (`pp.vo_case/1`, law L-o 11 / L-t)** — expected.verdict `"pass"` | `"fail"`; the segments are REAL selected
sentences; the `lines` are AUTHORED test lines (that is the point of the corpus). Classes (fail): `stance_flip,
could_to_will, number_swapped, number_rounded, invented_agreement, fact_not_in_clips, absent_name, banned_framing,
financial_imperative`; (pass): `faithful_paraphrase, manifest_language` (channel names, "two voices", dates, the show).
```
"manifest": {"channels": [...credited, card order], "date": "YYYY-MM-DD", "show": "Pulse Check"}
"segments": [{"label", "video_id", "channel", "speaker": "<verified name>" | null, "published_at",
              "sentences": [{"text", "start", "end"}]}]
"lines":    [{"slot": "intro" | "bridge" | "signoff" | "title" | "caption", "text", "cites": ["clip_01", ...]}]
"expected": {..., "bad_line": <index into lines> | null}      # which line must be rejected (fail cases)
```

**exclusions (`pp.excl_case/1`, law L-u)** — expected.verdict `"exclude"` | `"keep"`; classes (exclude): `accusation,
partner_attack, imperative, guaranteed_return, single_source_breaking, ad_read, third_party_media, altcoin`; (keep,
near misses): `policy_criticism, framed_prediction, neutral_company`.
```
"moment":  {"sentences": [{"text", "start", "end"}]}          # 1-3 consecutive whole sentences: the candidate
"context": {"before": [{"text", "start", "end"}], "after": [...]}    # up to 60 s each side, verbatim
```

**Adapter protocol (what the harness calls).** Env `PP_MOMENTS_GATES` = an importable module (dotted; `pipeline/` and
`segment_v1/` are on sys.path), default `moments_gate_adapter`. It may define any of:
```
context_integrity(case: dict) -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
vo_fidelity(case: dict)       -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
exclusion(case: dict)         -> {"verdict": "keep" | "exclude" | "uncertain", "why": str}
```
`case` is the JSON above WITHOUT the `expected` and `provenance` keys (the harness strips them). "uncertain" counts as
fail / exclude (law L-s: any uncertain is a FAIL). An exception or any other return is an ERROR (reported, and the
gate's run fails: a crash is not a verdict). A missing module or function = that gate's tests SKIP with the reason
(never pass). Thresholds per gate: 100 % of must-fail (fail / exclude) cases rejected; false-reject rate on the
must-pass (pass / keep) cases <= 10 %, stated as a number. Report: a confusion table per gate and per reason class
(`PP_MOMENTS_REPORT=<path>` writes it as JSON). Run: `PP_MOMENTS_GATES=<module> python3 -m pytest
tests/adversarial/test_moments_gates.py -q -s`.

## PHASE 2 — VO FORMAT v1.1 (orchestrator order 05:25 ET; additions only, v1 ids and bytes unchanged)

Every VO line and the title are classed: **(A) ATTRIBUTION** (says or implies what a named speaker / show said, thinks
or did: strict, the verb carries the clip's own hedge), **(B) FACT** (a checkable statement in the brand's voice:
strict, maps to selected sentences, never to the news), **(C) PRODUCTION** (channel names, counts of voices, credits,
'next': must match the manifest), **(D) HOST COMMENTARY** (the host's own opinion, question, tease or takeaway,
attributed to nobody: allowed without clip support only if it (i) holds no checkable fact, number, price, date or
named person / company, (ii) does not characterise any speaker's view or relation, (iii) is no financial imperative or
prediction, (iv) is no accusation, (v) cannot be mistaken for a quote). A line that cannot be placed is strict (A / B).

A v1.1 case is `"schema": "pp.vo_case/1.1"`: every v1 field, plus

```
"title":    "<string>"                       # judged like a line (its class in expected.title_class)
"universe": {"date", "built_at", "news": [{"headline", "source", "published_at", "summary"}], "use"}
            # tonight's news, verbatim from runs/fresh_20261112_050611/TOPIC_SELECTION.json: for staleness only,
            # never a source of facts (rule B)
"lines":    [{"slot": "intro" | "bridge" | "signoff", "text", "cites": ["A", "B"], "after": null | "A" | "B"}]
            # in play order; after = null before clip A, "A" between the clips, "B" after clip B
"expected": {"verdict", "class", "why", "bad_line": <index> | null, "bad_title": bool, "rule": <the rule broken>,
             "line_classes": ["C", "D", "A", ...] (one per line), "title_class": "A" | "B" | "C" | "D"}
```

A case must be rejected when ANY line or its title must be (bad_line or bad_title). The intro, the B hand-off and the
sign-off come from the v1 pools for both verdicts; honest teases are shared verbatim between must-pass and must-fail
cases, so only the trap differs (PP-E23). Gate call unchanged: `vo_fidelity(case) -> {"verdict", "why"}`.

v1.1 classes. Must-pass: `host_commentary` (16: teases, questions, takeaways; every own line class D),
`hedge_matched_attribution` (11 real 'I think / I feel like / I do expect / I believe' sentences, each read in its
window; the attribution verb matches the hedge; conditions kept). Must-fail (25): `commentary_smuggles_number`,
`commentary_smuggles_name`, `commentary_recharacterises`, `certainty_upgrade`, `invented_relation`,
`commentary_predicts`, `commentary_imperative`, `commentary_accuses`, `stale_price_title` (the order's case: title
'Bitcoin ran from 16K to 126K' while the universe has Bitcoin near $73,500; and 'Bitcoin holds 76K'),
`stale_price_line`, `commentary_as_quote`. Rejected while mining (not in the corpus): Bloomberg HRIjtvWogyE k1513 'I
believe a 50 basis point hike ...' (an anchor reading a Fed official aloud), Saifedean Ammous vgsSZ4mAHfQ k19 'I still
believe self-custody ...' (a sponsor read), store video MIDBBBBBBB1 (a synthetic id: not material).

## LIVE STATE — PHASE 1 (newest first; times ET, 2026-11-12)

- UPDATE (2026-11-12 ~06:50 ET, the integrator's merge audit answered; see PHASE 2 LIVE STATE and
  pp-tests_AUDIT_RESPONSE.md): the wall is now 420 tests, 40 strict xfails tied to R-01..R-28 (R-19 withdrawn, its test
  removed; R-24..R-26 are phase-2 design requests without a pin; R-27 / R-28 new). The block below is the phase-1
  record as it was at c35a2bde.
- **DONE** (02:30 ET): the wall is committed and pushed: **c35a2bde3c2c985b7142d4c29335e239140f400b** on
  origin/pp-tests (60 files: tests/adversarial 8, tests/fixtures/adversarial 2, docs/audits/parallel 50; nothing under
  pipeline/, scripts/ or segment_v1/). DONE WHEN met: all five families committed and pushed; every test passes or is
  a strict xfail tied to a written request (R-01..R-23); the findings-to-tests table exists (pp-tests_COVERAGE.md,
  all 244 ledger rows); this block names the commit. Not merged anywhere (the integrator merges after its own audit).
- AUDITED (pp-tests_AUDIT_RESPONSE.md): repo cross_llm_audit.py, two cycles, round 1 (GPT-4o out of credits; Gemini +
  Grok) and a final round on the fixed code with all three models (code 96/100 from each); a frontier review
  (claude-opus-5-5) found 8 real weaknesses in the wall itself, all fixed, then two verification rounds (final: READY);
  a last self-contained round (code + every claim-making doc in one package): 90/100 from Gemini and GPT-4o (Grok
  refused by the xAI gateway's own $1/day budget guard), its one actionable item implemented (call_gate).
- VERIFIED: 334 passed + 38 strict xfails (0 failed, 0 errors) in 2:00 at low load; `--runxfail`: exactly those 38
  fail, each with an AssertionError at its own assertion (pp-tests_XFAIL_EVIDENCE.md); a missing reference root makes
  every family-5 test ERROR with one clear message (19 errors in 1.5 s); regression_test.sh in this worktree 26 PASS /
  0 FAIL / 5 WARN (environmental).
- BLOCKED: nothing.

## The one command

```
cd /home/ultron/worktrees/pp-tests && python3 -m pytest tests/adversarial -q
```
CPU only, no network, no GPU, nothing written outside pytest's tmp dirs: conftest.py empties CUDA_VISIBLE_DEVICES
(qa_gates sets it to "0" at import; conftest imports it first and empties it again; an autouse fixture empties it
before every test), replaces faster_whisper with a stub that refuses to load, makes every AF_INET / AF_INET6 connect
of the test process raise (Telegram, the vision gateway, Ollama on loopback are unreachable), fakes yt-dlp at
select_passages' `subprocess`, injects model / vision replies at their HTTP seam and the Telegram sender at
deliver_run's `send`; a read-only nvidia-smi probe at session end fails the session if this pid is a CUDA compute app.
References are read read-only from /home/ultron/protocol_pulse/references (override: PP_REFS_DIR); a missing
reference FAILS (law L-m), never skips.

Measured (this machine is shared: 192 cores, load from the live run and the parallel sessions): 2:00 at load
average ~6-12 (02:10 ET), 2:40 to 4:04 at load average 45-86; the budget is 5:00. The
cost is dominated by G8 on the frozen 9:16 final (one keyframe: each frame grab decodes ~1,000-1,270 frames of
1080x1920) and the synthetic selection runs; the frame grabs are deterministic (single- and multi-threaded decodes
are byte-identical).

Reproduction: Python 3.10.12, pytest 9.0.2, numpy 1.25.2, opencv 4.13.0, Pillow 12.2.0, ffmpeg / ffprobe
4.4.2-0ubuntu0.22.04.1 (recorded in tests/fixtures/adversarial/reference_lb_edges.json); code under test = this
branch at c1451047 (pipeline/ and segment_v1/ untouched); reference checksums = each reference's own SHA256SUMS,
verified file by file by test_f5. Strict xfails: `-rx` lists each with its finding and request; `--runxfail` shows
each failing on its own assertion (pp-tests_XFAIL_EVIDENCE.md).

## What the wall pins (tests/adversarial)

| file | family | passes | strict xfails (open defects, pp-tests_REQUESTS.md) |
|---|---|---|---|
| test_f0_cpu_guard.py | the guard itself | no CUDA device visible; every Whisper load refused; no network connection can be opened | - |
| test_f1_text_meaning.py | 1 text / meaning fuzz: canon + G18, quote_in / adjudicate, align_quote, anchor, headline numbers, G20 names, G3b, idempotence | surface variants equal and meaning mutants unequal in canon, G18, quote_in, the headline check; G20 names in any surface form; G3b written / spoken amounts | R-01 idempotence; R-02 / R-03 / R-04 / R-19 quote check; R-05 anchors accept every meaning mutant; R-06 G20 channel variants; R-07 / R-08 G3b; R-16 / R-17 G18 |
| test_f2_provenance.py | 2 coordinates / provenance through select_passages.select_and_build_edl, write_lock_cut_table, gate_g16, verify_lock | a known offset recorded in file coordinates, cuts in the locked pauses, G16 PASS; a lock against another transcript or edited after selection is refused | R-09 dirty cache relabelled; R-10 transcript / lock not bound to media; R-11 lock words vs transcript; R-18 next_source_word; R-22 failed yt-dlp; R-23 SELECT with one clip / one channel |
| test_f3_release_auth.py | 3 authorisation mutations through release_auth.authorise AND telegram.deliver_run | the control is authorised and delivered; every named mutation refuses and sends nothing (33 missing-row cases: every REQUIRED row of both formats, unknown / lookalike rows, 23 non-exact verdicts incl. 'PASS (waived)', 14 empty / malformed evidence, digests of other files, the 9:16 swapped before / during delivery, skipped gates, stale manifests, packs, legacy markers, replays, no attestation) | R-12 an EDL changed after the gates is attested ALL_PASS |
| test_f4_vacuity.py | 4 vacuity: every REQUIRED gate on empty / zero / None / NaN input; garbage model replies | the gates fail closed on input that measures something wrong; release_auth blocks every vacuous PASS (0 samples); V1 and every editorial decision refuse empty / prose / truncated / wrong-shape / NaN replies | R-13 / R-14 / R-15 gates that PASS on nothing; R-20 G8 one of five samples; R-21 G8 measures an earlier render's frames |
| test_f5_references.py | 5 reference integrity (read-only) | SHA256SUMS of both references (1.7 GB + 0.3 GB), read-only, the worktree's preview copy identical; manifests describe their finals, one timeline per run; L-a: v2f one set, the preview the documented must-fail; L-b table pinned; G8 9:16 settled; the preview's legacy gate report refused by L-j | none (references are facts: PP-04 is a decision) |

## Settled by measurement: "the approved reference fails 9:16 G8" (Claude-gates #5)

REFUTED for the production wiring, on the saved files, through the public `qa_gates.gate_g8` (reference read-only):
v2f 9:16 PASSES with the reframed vertical clips as sources (out / source medians: hook 19.10 / 18.07, clip_01
50.34 / 49.54, clip_02 26.25 / 25.29, clip_03 **10.84** / 10.04, ratio 1.080; floor 10.84: zero margin); 16:9
PASSES (hook 27.56 at its floor). Without source clips (the Law 22 harness) both formats FAIL on every segment with
`no_source`: that is the recorded 'fails'. Full table: pp-tests_REQUESTS.md. Pinned by test_f5 (9:16 clip_03 through
the production wiring; the harness reading on the 9:16 hook).

## Law L-b on the references (measured, nothing adjusted)

By the law's own word-bounds measure the recorded fades overlap an edge word at: preview hook OUT +20 ms, clip_01 OUT
+73 ms (the documented must-fail), clip_02 IN +53 ms and OUT +20 ms, clip_03 IN +10 ms; v2f clip_01 OUT +20 ms and
clip_03 IN +10 ms (both recorded legacy), clip_02 OUT +10 ms and clip_03 OUT +20 ms (which G17c passes). A decision
for the orchestrator (pp-tests_REQUESTS.md PP-04); the table is pinned by test_f5.

## Assumptions taken (the order says do not stop to ask)

1. "Public entry point" = the module function a pipeline stage calls (gate_*, select_and_build_edl, authorise,
   deliver_run, quote_in, adjudicate, align_quote, anchor, spoken_channels, headline_numbers_said, ...). A GPU-made
   input (Whisper readings, SCRFD faces, a model reply) is injected at that function's own seam
   (qa_gates.whisper_segment, gate_g18's transcriber, gate_g4s's detect, LocalLLM._post, visual_check._call), never by
   calling a private helper instead of the gate. One private rule is used on purpose: run_fresh._samples (the
   production evidence rule; stage_gates itself needs GPU0) in the release backstop test.
2. "Never PASS" in family 4 = the production reading: an explicit `skip` is recorded SKIPPED by run_fresh (not a
   PASS); an exception raised INSIDE a gate fails the stage (a HOLD); an exception raised by the probe's own code
   fails the test; a plain `(True, ...)` on nothing is a PASS and is xfailed.
3. Family 4 covers the REQUIRED inventory (release-deciding). MONITORING gates (G1, G2, G4, G6, G10, G11, G13) are
   reported, not deciding (addendum '22:15' item 4); their vacuity is listed UNCOVERED in pp-tests_COVERAGE.md.
4. "SELECT success = hook + >= 2 clips + required channels" is the D contract named in the DoD (not landed); R-23
   pins it as the rule.
5. Law L-b on the frozen references is pinned as a measured table and reported as a decision (PP-04); only the
   documented must-fail is asserted as a must-fail.
6. The audit tool hard-codes ~/protocol_pulse; it was run unmodified with its module paths redirected to a scratch
   mirror (pp-tests_AUDIT_RESPONSE.md says exactly how). Nothing was written to the main tree; nothing was sent.
7. regression_test.sh needs untracked media this worktree lacks (video_pipeline_v3/assets/outro_branded.mp4 and
   assets/music/*.mp3, both git-ignored): they are provided as read-only symlinks to the main tree's files (no bytes
   copied, nothing that can enter a commit), as the sibling worktrees of this push do with copies.

## Not done / handed over

- MERGE NOTE: the repo's .gitignore line 16 (`test_*`) ignores every tests/adversarial/test_f*.py; they are
  force-added (`git add -f`), as pipeline/test_*.py are. A merge or a re-add must keep them (a plain `git add` of the
  directory silently leaves the six test files out).

- Code fixes: none by design (tests only). 23 requests with minimal fixes: pp-tests_REQUESTS.md (and how the pins
  stay honest when each fix lands).
- UNCOVERED: 147 of 244 ledger rows (pp-tests_COVERAGE.md says why for each, and tiers the riskiest).
