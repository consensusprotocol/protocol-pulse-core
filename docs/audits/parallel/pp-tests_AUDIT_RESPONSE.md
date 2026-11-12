# pp-tests AUDIT RESPONSE — cross-LLM audit of the actual diff (two cycles) + frontier review

## How the audit was run
- The repo's `utils/cross_llm_audit.py`, unmodified, two cycles (cycle 2 cross-examines cycle 1), consensus by its
  own synthesis step. It hard-codes `~/protocol_pulse` for its inputs, outputs and registry and the main tree must not
  be written, so a scratch driver imported it and pointed its module paths at a scratch mirror (`BASE`: the brief +
  `CURRENT.diff`; `AUDITS`: a scratch output dir), loaded its xAI gateway from a scratch COPY (its budget ledger stays
  in the scratchpad), removed Telegram credentials from that process, and read the API keys by name from
  `/home/ultron/protocol_pulse/.env` inside the process (this project's `GEMINI_API_KEY_MEDLEY` / `XAI_API_KEY_MEDLEY`
  under the names the tool expects, as `pipeline/signoff.py` and the red-team's `frontier.py` do). Nothing was printed,
  written to the main tree, or sent. The tool's registry write failed harmlessly in the scratch mirror (no git there).
- The diff (213 KB) was split in two so neither part reaches the tool's 220,000-byte cut-off (a larger file is
  silently dropped: batch 16's Grok saw no code): A = all code + fixtures + pp-tests_REQUESTS.md (150 KB); B = STATE,
  BIBLE_ADDITIONS, COVERAGE (63 KB).
- **GPT-4o could not take part**: every call returned `429 insufficient_quota` ("You have no credits remaining") —
  an account condition, recorded here, not worked around. Gemini 2.5 Pro and Grok-3 ran both cycles of both chunks.
- Because the panel was down to two generic reviews, one **independent frontier review** was added (as batches 16 / 17
  did): `claude-opus-5-5` (effort high) asked one pointed question on chunk A (tests that do not test what they claim,
  strict xfails that can fail for the wrong reason or never flip, vacuous must-fails, writes / GPU / network paths,
  REQUESTS claims, flakiness). It found the substantive defects; after the fixes it reviewed the fixed diff again
  (verification round, below).
- Outputs: pp-tests_AUDIT_A_*.md and pp-tests_AUDIT_B_*.md next to this file (the package / cycle-2 prompt files are
  the diff itself plus the brief and are not copied).

## Chunk A (code + REQUESTS) — consensus 94/100, "production-ready with one pre-merge condition"

| item | models | disposition | evidence |
|---|---|---|---|
| U-1 hard-coded reference root `/home/ultron/protocol_pulse/references` | Gemini + Grok | IMPLEMENTED (the env half): `MAIN_TREE_REFS = os.environ.get("PP_REFS_DIR", "/home/ultron/protocol_pulse/references")`; the missing-reference message names PP_REFS_DIR | adv_helpers.py MAIN_TREE_REFS; test_f5 `_need` |
| U-1 (skip half): `pytest.skip(allow_module_level=True)` when the references are absent | Gemini + Grok | REFUTED | The order: "every test either passes or is a strict xfail"; law L-m: "nothing measured is never a pass". A module-level skip makes the one-command run report success while family 5 measured nothing. The default (the worktree's `references/`) proposed in the final list lacks v2f and the preview's media: it would fail or skip family 5 on this very machine. A missing reference FAILS with a message naming PP_REFS_DIR. |
| UI-1 nvidia-smi guard "false-positives on shared GPU hosts" (gate it behind PP_STRICT_CPU_GUARD) | Grok | REFUTED | conftest.py compares ONLY `str(os.getpid())` with the listed pids: another job's GPU process can never match. The full suite passed with the live run on GPU0 the whole time. The docstring now states it. |
| UI-2 the mid-delivery swap test depends on deliver_run verifying every payload before the first send | Gemini | IMPLEMENTED (comment) + strengthened: the swap fires after the first VIDEO send (frontier #7) and a control checks that it did | test_f3 test_the_9x16_swapped_during_delivery_never_reaches_the_chat |
| CONFLICT-1 "timeouts missing on ffmpeg / ffprobe" | Grok vs Gemini | REFUTED (the consensus' tiebreaker agrees) | adv_helpers `_run(..., timeout=120)` for every make_media / make_video ffmpeg call; WindowAudio `timeout=120`; test_f5 ffprobe `timeout=60`; conftest nvidia-smi `timeout=20`; speech_like runs no subprocess (numpy only) |
| P2-B / P3: CI env matrix, README, a session fixture for the root | Gemini | NOT APPLICABLE / DEFERRED | no CI config exists for this suite; PP_REFS_DIR is documented in pp-tests_STATE.md |

## Frontier review of chunk A (claude-opus-5-5) — NOT READY, 8 findings

| # | finding | disposition | what changed |
|---|---|---|---|
| 1 HIGH | the fixtures encode the pre-fix contract: R-09 / R-10 / R-12's fixes would break today's controls and silence or flip other xfails for the wrong reason | ACCEPTED, FIXED | `write_source` writes the R-09 download record (`sources/<vid>.section.json`: dl_start, dl_end, sha256) and `media_sha256` in every transcript; `release_run` records `edl.json` in `measured_files`; today's code ignores all three (suite result unchanged: verified). The byte-replacement probes rewrite a CONSISTENT download record for the new bytes, so only the R-10 binding can flip them; the partial-download / missing-file probes remove the record as a real failed download would. The EDL probe now changes the headline for real ('Bitcoin price surges past $90,000'). REQUESTS R-09 / R-10 / R-12 name the exact records. |
| 2 HIGH | no strict xfail pins its failure to an assertion: any crash or fixture error stays "xfailed" | ACCEPTED, FIXED (verified pytest semantics first: a fixture `assert` on an xfail test reports XFAIL; `raises=AssertionError` alone does not stop that) | every strict xfail is `raises=AssertionError` (24 markers / 38 instances); every precondition (fixtures, controls inside xfail tests) is `adv_helpers.control` = `pytest.fail`, so a broken setup or a renamed field shows FAILED / ERROR, never the pinned defect. The stale-frame probe no longer guesses G8's file names: an earlier G8 run in the same qa dir leaves whatever the gate writes. |
| 3 MED | R-19's CamelCase split would break the all-caps surface variants | ACCEPTED | R-19 now proposes the space-insensitive token-run comparison guarded by R-05's protected tokens, and records why the CamelCase split is wrong |
| 4 MED | the family-4 probe swallowed its own crashes; the backstop filtered on the mark, not on the reading | ACCEPTED, FIXED | an exception whose innermost frame is in tests/adversarial (a probe bug, e.g. a wrong signature) is re-raised; only an exception raised inside the gate counts as a stage failure. The backstop checks every probe that reads PASS today (so it stays right as fixes land) and always checks the vacuous result shapes themselves (no `checked >= 8` floor that the fixes would break) |
| 5 MED | the 'decimal dropped' headline mutants were skipped with a wrong comment | ACCEPTED, FIXED | measured first: all 63 are reported as not said; the skip is gone (the test passes with them) |
| 6 MED | network / Telegram not blocked globally; the GPU probe is weaker than claimed | ACCEPTED, FIXED | conftest makes every AF_INET / AF_INET6 connect of the test process raise (loopback too: a real Ollama listens on 127.0.0.1); test_f0 proves it with literal addresses (no DNS); the legacy-send test can no longer reach Telegram if the path regressed. The nvidia-smi probe is described as an extra end-of-session probe, not the guarantee. |
| 7 LOW | swap after send #1, not after the first video; invisible NBSP / narrow NBSP / curly quotes in source | ACCEPTED, FIXED | swap on the first `video` send + control; ` `, ` `, `’`, `—`, `“` / `”` written as escapes (they were real characters, invisible in a diff) |
| 8 LOW | pinned values depend on the decoder; unclosed files | ACCEPTED, FIXED | the L-b table records `ffmpeg_version` (4.4.2-0ubuntu0.22.04.1) and a mismatch says whether the decoder changed; every write uses `with open` |

## Chunk B (STATE, BIBLE_ADDITIONS, COVERAGE) — consensus 42/100 "documentation only"

| item | disposition | evidence |
|---|---|---|
| U-1 "the test source files are absent" (P0) | REFUTED: a chunking artefact | the code was audited as chunk A (11 files, 150 KB, 94/100); the file names chunk B asked for (`test_f1_canon.py`, `test_f2_scoring.py`...) do not exist and never did |
| U-2 exact reproduction steps (command, revision, versions, reference checksums) | IMPLEMENTED | pp-tests_STATE.md: the command, the commit, Python 3.10.12, pytest 9.0.2, ffmpeg 4.4.2, the reference checksums = each reference's own SHA256SUMS, verified file by file by test_f5 |
| U-3 a remediation plan for the 147 UNCOVERED rows | PARTLY: a risk-tiered list of the most important UNCOVERED rows added to pp-tests_COVERAGE.md; owners and target cycles are the orchestrator's to assign, not this session's | pp-tests_COVERAGE.md "Highest-risk UNCOVERED rows" |
| U-4 hard-coded absolute paths in STATE | REFUTED | the order names these absolute paths (worktree, read-only data); the code honours PP_REFS_DIR |
| UNIQUE-1 generate the docs from test metadata | DEFERRED (P3) | COVERAGE is already generated from the ledger's own rows (no finding can be omitted); the row-to-test mapping stays hand-written |
| UNIQUE-2 artefact-type ambiguity | NOTED | resolved by U-1's explanation |

## Verification round on the fixed chunk A (claude-opus-5-5): findings 1-8 RESOLVED / acceptable; 5 new, all fixed

| # | new finding | disposition |
|---|---|---|
| 1 MED | the network guard raised RuntimeError, the type `refused()`, the partial-delivery test and the legacy-send test expect: a regressed send path would SATISFY them | FIXED: the guard raises `NetworkBlocked(BaseException)` (adv_helpers); measured first that a BaseException subclass escapes production `except Exception` and `pytest.raises(RuntimeError)` and is reported FAILED, also inside a strict xfail, without stopping the session; test_f0 checks all three |
| 2 LOW | the backstop called the gates unguarded; stub arity changes would read as gate crashes | FIXED: one `call_gate` rule shared by the probe and the backstop; the stubs take `*a, **k` |
| 3 LOW | the R-10 pin could crash instead of XPASS if a refused Whisper load escaped select | FIXED: the refusal is caught and checked with a control (select catches it today: `_whisper_transcribe`'s `except Exception`) |
| 4 LOW | the delivery control assumed the 16:9 was send #1 | FIXED: the control follows the recorded first-video send |
| 5 LOW | the fixtures' download record sat exactly on R-09's containment boundary | FIXED: the passage's first word is 0.25 s inside the pad (round(start - pad) is still the offset: TestKnownOffset passes); R-09 says the containment is inclusive |

## Final round on the fixed code (repo tool, two cycles; GPT-4o back with credits: three models) + frontier final

Chunk A3 (code + REQUESTS): **96/100 from all three models**. Chunk B3 (docs alone): 18/100, again for "no code in the
diff" (the chunking). Frontier final verification (claude-opus-5-5): **READY**.

| item | models | disposition | evidence |
|---|---|---|---|
| A3 U1 fail fast when the reference root is missing (a session guard with `pytest.exit`, PP_REFS_DIR mandatory) | all three | PARTLY IMPLEMENTED: a module-scoped control in test_f5 makes EVERY family-5 test ERROR at once with one clear message naming PP_REFS_DIR (measured: `PP_REFS_DIR=/nonexistent` -> 19 errors in 1.5 s, no skip, no pass). REFUTED: `pytest.exit` (it would stop families 0-4 from measuring anything for a family-5 environment problem) and a mandatory variable (the default IS the location the order names) | test_f5 `_references_present` |
| A3 UI1 `_need` used a bare assert for a precondition (against the suite's own control rule) | Gemini | IMPLEMENTED | `_need` -> `H.control` |
| A3 M1 escalate R-09 / R-10 | GPT-4o + Gemini | IMPLEMENTED (a priority note at the top of REQUESTS) | - |
| A3 M2 annotate the dominant CPU cost | Grok + Gemini | IMPLEMENTED (PERF comment at speech_like) | - |
| A3 UI2 setup docs / UI3 a CI pre-validation helper | one model each | BACKLOG | no CI exists for this suite |
| B3 U-1..U-4, M-1, M-3 "code absent / unverifiable" | all three | REFUTED as findings about the change (the code is in the same commit and was audited as A3); ACCEPTED as procedure (M-2: an audited unit should be self-contained): one more round on ONE package holding the code, fixtures, REQUESTS, STATE, AUDIT_RESPONSE, BIBLE_ADDITIONS and the brief, under the 220,000-byte cut-off (COVERAGE, a table generated from the ledger, stays out) | below |
| frontier final #1: the R-09 pin flips only with R-22 (a miss falls through to the failed yt-dlp, which returns the file under the name) | Opus | IMPLEMENTED (R-09 says so: it errs safe, never a false pass) | REQUESTS R-09 |
| frontier final #2: the mid-delivery swap test would error on a correct streaming refactor that refuses | Opus | IMPLEMENTED: a refusing delivery is accepted; the assertion is that no 9:16 other than the attested bytes was ever sent; the control still requires the 16:9 to have gone out first | test_f3 |
| frontier final #3: `::1` fails before `connect` where the kernel has no IPv6 | Opus | IMPLEMENTED: IPv6 is probed only where an AF_INET6 socket can be created | test_f0 |

## Self-contained round (one package: code, fixtures, REQUESTS, STATE, AUDIT_RESPONSE, BIBLE_ADDITIONS, XFAIL_EVIDENCE; 202,180 bytes)

90/100 from Gemini and GPT-4o. Grok did not run: the xAI gateway's own budget guard refused the calls
("max_usd_per_day ($1.00) exceeded", the scratch copy's ledger after five audit runs today): a guard working, recorded.

| item | models | disposition | evidence |
|---|---|---|---|
| U-1 `call_gate`'s `except Exception` is too broad: a crash could silently count as RAISED | Gemini + GPT-4o | PARTLY IMPLEMENTED: MemoryError / RecursionError propagate (a resource failure is not a gate's decision), and any gate exception is reported as a pytest warning naming it (never silent). KEPT: an exception raised inside a gate is not a PASS (in production it fails the stage, a HOLD); harness bugs already propagate (innermost frame in tests/adversarial). Narrowing to a list of exception types would turn a legitimate fail-closed `raise` of a fixed gate into a test failure | test_f4 `call_gate` |
| U-2 no structured logging | Gemini + GPT-4o | REFUTED | every gate prints its own report, captured by pytest and shown with a failure; every assertion carries the measured object; every control names what broke (`CONTROL (test setup, not the pinned defect): ...`); a logging layer over subprocess calls would add noise, not evidence |
| UI-1 `_FINALS` module cache | Gemini | REFUTED | the cache holds three read-only media files made once per process; every consumer copies them (`shutil.copy`), none writes in place; a session fixture changes nothing observable |
| UI-2 earlier unanimous items "not addressed" | Gemini | NOTED | each is dispositioned above with its evidence (implemented, partly implemented with the reason, or refuted) |
| UI-3 CI wiring | GPT-4o | OUT OF SCOPE (no CI exists for this suite; the one command is CI-ready) | - |
