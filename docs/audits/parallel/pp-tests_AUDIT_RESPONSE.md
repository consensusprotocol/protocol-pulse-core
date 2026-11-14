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

## The STATE-only commit (the hash and DONE): audited with the repo tool, two cycles (Gemini, GPT-4o; Grok budget-refused)

0/100 for "the package is missing all subject-matter code": the package was the 3 KB STATE diff itself. REFUTED as a
finding about this commit: the code it reports was audited as chunk A3 (96/100 from all three models) and in the
self-contained round (code + every claim-making doc, 90/100); c35a2bde holds exactly those files plus the consensus
change that round asked for (call_gate). "Revert DONE to IN PROGRESS": REFUTED, every DONE-WHEN condition is checked
on the pushed commit (`git ls-tree` lists the 8 test files, 2 fixtures and 50 docs; nothing under pipeline/,
scripts/, segment_v1/; the full suite on HEAD: 334 passed + 38 strict xfails in 2:07). The process point (a docs-only
diff is judged without the code it describes) is filed for the tool: pp-tests_REQUESTS.md "Tooling".

# PHASE 2 — the moments-first exam (order 03:00 ET 2026-11-12)

## How it was audited
Same scratch driver and unmodified `utils/cross_llm_audit.py`, two cycles, with a phase-2 brief
(`PP_TESTS_MOMENTS_GOSPEL.md`: the order's requirements, laws L-s / L-t / L-u / L-v, what to check, label correctness
first). Chunk A = the code (store_extract, build_corpora, moments_exam, test_moments_gates, the toy gates, the
baseline adapter) + the STATE diff, 114,861 bytes. Chunk B = a digest of all 137 cases (the answer, the selected words,
the context the 'why' relies on, the package), 179,923 bytes (the full JSON is 1.3 MB). Grok was refused by its $1/day
budget both cycles, so the tool ran on Gemini 2.5 Pro and GPT-4o; an independent claude-opus-5-5 review (effort high)
ran on each chunk. Before the audit, the blind frontier baseline v0 had already acted as a label audit (STATE: six
label defects of mine found, each verified in the source window and corrected).

## Chunk A (code) — cycle 1 consensus 87/100, cycle 2 80/100 ("ready for a targeted second pass")
| # | finding (cycle) | disposition | evidence |
|---|---|---|---|
| A1 | hard-coded absolute paths, `.env` and the store (U1, both cycles, P0) | REFUTED for `.env`: the order fixes it ("keys are read only from /home/ultron/protocol_pulse/.env, by name, inside code"); an override variable would let keys come from elsewhere. Store: already `$PP_EDITORIAL_STORE` (store_extract.py `STORE = os.environ.get(...)`). The default test run reads no key at all; only the opt-in baseline does. | order text; `store_extract.STORE`; `test_moments_gates` imports no key |
| A2 | `print()` instead of `logging` (U2, both cycles, P1) | REFUTED as framed, root cause FIXED: the runner's stdout IS the report (the confusion table), every verdict / error is a structured row in the JSON report and the exit status encodes the result; what was really missing was where a gate crashed: ERROR rows now keep `traceback` (last 1,500 chars). | `moments_exam._judge`; `test_a_crash_or_an_invalid_verdict_is_an_error` asserts the traceback |
| A3 | oracle toy gate loads the corpora at import (Gemini c1, both c2, P1) | FIXED: loaded on first call. | `moments_toy_gates/oracle.py` |
| A4 | `--jobs` silently requires a thread-safe gate (Gemini c2, P2) | FIXED: threads only for a module that declares `THREAD_SAFE = True`; any other gate runs one case at a time and the run says so. The baseline declares it (SDK clients are thread-safe; spend guarded by the lock). | `moments_exam.run_corpus`; checked: oracle at `--jobs 4` -> "does not declare THREAD_SAFE = True: --jobs 4 -> 1" |
| A5 | 600 s subprocess timeout hard-coded (Gemini c2, P2) | FIXED and it was a real bug: a model-backed gate at one case at a time on 66 cases would be killed. The real-gate test now takes `PP_MOMENTS_TIMEOUT_S` (default 3 h); the toy controls keep 600 s. | `test_the_gate_sits_the_exam` |
| A6 | rate limiting / back-off (Gemini c1, P2) | REFUTED (measured): both SDK clients run with `max_retries=3` (exponential back-off on 429 / 5xx); the full v0 baseline made 274 calls at 6 threads per vendor with 0 errors. | `baselines/SPEND.jsonl`; v0 reports |
| A7 | thread lock + file lock may deadlock (GPT-4o c1) | REFUTED (the tool's own tiebreak agreed): one context manager takes them in a fixed order and they are never nested; `_client()` takes the thread lock outside it. Comment added. | `frontier_blind._locked` |
| A8 | linear word-time interpolation (Gemini) | KEPT, documented: it is pp-selectid's own `tokens_from_record`, which `k` must match; segment timing is never enough for an on-screen cut. | `store_extract.tokens` comment |
| A9 | partner_attack text inline in Python; INDEX meta block with build time / git sha (Gemini) | REFUTED: one spec file keeps every case reviewable in one place, CONSTRUCTED marked in the case; a build time or sha in INDEX would break the byte-identical rebuild that `test_every_case_rebuilds_verbatim_from_the_store` relies on. | that test |

## Chunk B (corpus digest) — repo tool cycle 1 87/100, cycle 2 (Gemini, GPT-4o)
The tool's two models contested no label. Their items: multimodal (avatar / TTS / lip-sync) tests, transcription-error
cases, enumerating legal statutes, a corpus refresh cadence, structured result logs, structured `why` fields, keeping
the digest private. Dispositions: OUT OF SCOPE for this order (three text corpora + harness): multimodal, TTS and
transcription-error tests (the second recognition pass is law L-v (2), the builder's; Phase 1's family 1 already
fuzzes meaning-changing text mutations), legal statutes and refresh cadence (orchestrator / PBX decisions, noted in
STATE); FIXED: structured result logs (every report now carries `started_at`, `finished_at`, the gate's `IDENTITY`,
the run's `seed` and, after the run, its `salt`; every row carries case id, class, expected, verdict, why, seconds,
traceback on ERROR); REFUTED: structured `why` fields (the 74 s figure is derivable from the window's own times);
the digest is a scratch audit artifact and is not committed.

## Frontier review, chunk A (claude-opus-5-5, effort high): NOT READY, 12 findings — all acted on
| # | finding | disposition |
|---|---|---|
| 1 CRITICAL | every must-pass CI case had the bridge "Also on the record:": a one-line gate met every threshold | FIXED: intro, bridge, sign-off and clip order are drawn by hash from ONE pool for both labels; captions all dated; windows all 90 / 80 s; `test_no_package_field_separates_the_verdicts` proves no single field lets a lookup gate pass (each would false-reject 100% of the must-pass set) and no value is a free win for one class (bridge / order exempt only where they ARE the trap) |
| 2 HIGH | order leak (fails first), unsalted id, answers in INDEX.json, no held-out set | FIXED: seeded shuffle per run (seed in the report; `test_a_gate_that_answers_by_position_fails`), id salted per run (salt written to the report after the run), INDEX.json back to v1 (`id`, `file`, `sha256`) in hash order. HELD-OUT: REFUTED as not achievable under the rules: every session runs as the same user on one machine, so no file is unreadable to the builder; the case files carry `expected` by the published format; the mitigation is the blinding plus the instruction to the builder, and a sealed set needs storage the orchestrator controls (noted in STATE) |
| 3 HIGH | must-pass speaker attribution unverifiable (Saifedean debate clips, kaifu_apps) | FIXED: the must-pass set was rebuilt: 10 single-narrator clips (Swan, Coin Bureau, Simply Bitcoin, Yahoo Finance) and 12 one-sentence interview clips credited to the SHOW; the three debate clips are out of the corpus |
| 4 HIGH | must-pass titles name persons not verifiable (Booth, Moss, Lee, Burnett) | FIXED: no must-pass package names a person; the one role named ('Swan Bitcoin's Founder') is verified inside its own window (k4 'I'm Corey Clifston, founder of Swan Bitcoin') |
| 5 MEDIUM | hedges dropped in must-pass titles; inconsistent BTC Sessions attribution | FIXED: titles quote the hedges ('I Think', 'in My Opinion', 'I Don't Think'); BTC Sessions clips are all credited 'On BTC Sessions'; the time-sensitive 'bottom's in' clip is out |
| 6 MEDIUM | the bear-market relabel: weak either way; baseline-influenced; still used in VO | FIXED: the clip is out of every corpus (an exam case must be unambiguous); the VO number cases use Coin Bureau and Swan clips instead; the baseline's influence on labels is disclosed in STATE |
| 7 MEDIUM | must-fail packages with second defects | FIXED: CI VO lines are channel-only templates (no topic, number or name); titles quote the clip verbatim or restate it without adding a name, number, imperative or accusation (sarcasm 04, quoting_opponent 01, answer_without_question 02, steelman 02, conditional 03 rewritten); false_dialogue 03 now crosses channels (What Bitcoin Did's question, CoinTelegraph's answer) and no moment is used by two cases |
| 8 MEDIUM | banned-framing VO lines also flip stance | FIXED: each line is the clip's own words plus the banned verb only ('confirms', 'exposes', 'admits') |
| 9 MEDIUM | undated captions, constructed metadata, unique 80 s window | FIXED: all captions dated; constructed cases carry the same fields, realistic contexts (8-10 sentences a side, inside the real range 1-27) and fictional show names where no real channel is needed; blinding drops video id, url and sentence ids from every exclusion case; all CI windows 90 / 80 s; the blinding test now checks values too |
| 10 MEDIUM | skip decided by exit code; a gate's `SystemExit(3)` looked ABSENT | FIXED: `_judge` records any BaseException except KeyboardInterrupt as ERROR (`test_a_gate_that_exits_is_an_error_never_absent`); the real-gate test skips only when the report says the gate is absent |
| 11 MEDIUM | spend guard under-reserved | FIXED: each call reserves its worst case (input at 2.5 chars / token + full max_out) and settles to actual; vendors run one after the other (6 and 3 threads) so spent + open reservations stays under $15; shuffled order spreads any refusal |
| 12 LOW | sentence-id claim untested against pp-selectid; DNS / UDP not blocked; single_source 01 wording | FIXED: `test_sentence_ids_match_pp_selectid_at_the_named_commit` runs pp-selectid's own `tokens_from_record` / `split_sentences` / `read_text` / `is_terminal` from the git object d809a1f8 on every record the corpora use (44 records, every sentence equal); `refuse_network` also refuses name resolution and datagram sends; the why now says the tweet is single-source AND disputed |

## Frontier review, chunk B (claude-opus-5-5): 11 findings (reply cut at the token limit) — all acted on
| # | finding | disposition |
|---|---|---|
| 1 CRITICAL | bridge leak; undated stale captions; both-clip cites only in invented_agreement | FIXED (as A1 / A9); a must-pass VO bridge now cites both clips ('Swan Bitcoin and Coin Bureau, one after the other.') |
| 2 HIGH | harness not in the material; 9 keep cases make 10% effectively 0 | the harness was in chunk A; keep cases now 12 (one false exclude = 8.3%) and every must-accept set has >= 11 (asserted) |
| 3 HIGH | later_retraction 04 (bear market) not defensible | FIXED: removed (A6) |
| 4 HIGH | must-pass titles naming guests | FIXED (A4) |
| 5 MEDIUM | steelman 03 (Scaramucci) reaffirmed at k175 | FIXED: replaced by Fox Business's reporter stating Big Tech's counterargument (1s_i1us5q8w k7) |
| 6 MEDIUM | eight confounded must-fails | FIXED (A7); hypothetical 03 (Saifedean debate) replaced by TFTC's 'Let's say ... in that case' (W2LIxB2kAH0 k777-778); quoting_opponent 03 (debate audio in Simply Bitcoin) replaced by the Bitcoin Mechanic mimicking officials (NM_WPezsI0I k503); later_retraction 02 (the interviewer's question) removed |
| 7 MEDIUM | later_retraction 01: 80 s window, title dropped 'reportedly' / 'I believe' | FIXED: all windows 80 s after (the case is no longer unique); title keeps both hedges |
| 8 MEDIUM | a hedge dropped in a must-pass title | FIXED (A5) |
| 9 MEDIUM | guaranteed_return 01 is a hedged personal view; one case | FIXED: dropped; no real guaranteed-return claim exists in the store (search recorded), so the class is two CONSTRUCTED cases under fictional show names, labelled so |
| 10 LOW | neutral_company 01 names no company in the moment; single_source 04 reported twice | FIXED: replaced by 'Coinbase is entering the federal banking framework.' and 'Strategy bought 1,036 BTC per its latest filing'; single_source 04 removed |
| 11 LOW | absent_name lines add false claims | FIXED: each line now puts the clip's own words in an absent person's mouth ('Jerome Powell says ...', 'Michael Saylor: ...', 'Larry Fink on BTC Sessions: ...') |

## Verification round (claude-opus-5-5, effort high, shown its own findings + the fixed code / digest): NOT READY ×2 — all acted on
Code (A2), 10 new items; corpus (B2), 10 new items. Overlaps merged. Every change below is in the final corpus (136
cases) and was made BEFORE the final baseline v2 ran; nothing changed after it.
| item | disposition |
|---|---|
| A2 N1 / B2 1: must-pass 'our 75K target never broke ... once the results were in' (unresolved 'the results'; time claim) | FIXED: out (both baseline models had also failed it in v1c) |
| A2 N2: the clean pool is both the must-pass set and the filler (a must-pass moment recurs as an adjacent clip; a must-fail one does not) | PARTLY FIXED / REFUTED in part: a gate sees one blind case per call in a shuffled order; using recurrence needs the other case files, which carry the answers by the published format anyway; the remedy for a builder tuning on the corpus is the temporal held-out slice (next row). Minimal pairs are now on both sides: three false_dialogue and three title_adds_thesis cases are built FROM must-pass clips |
| A2 #2 / B2 held-out | ACCEPTED in the reviewer's form: a temporal seal needs no unreadable file. Protocol (pp-tests_REQUESTS.md R-26): when the builder freezes its gate it records the commit sha; pp-tests then mines a fresh slice (>= 15 CI, >= 8 VO, >= 6 exclusions) from material the corpus does not use, the frozen gate sits it, and the slice is reported apart. Not run in this order (no frozen gate exists yet) |
| A2 N3 / B2 4: Simply Bitcoin k203 may continue Gromen's argument; kaifu_apps unlabelled | FIXED: both out of the must-pass set (and out of every adjacent / VO use); the Simply Bitcoin clips left are k135 only, after the narrator's own 'So whoever you voted for ...' |
| A2 N4: 'Bitcoin Mechanic' reads as a person | FIXED: the channel is named 'Bitcoin Mechanic'; it is now credited 'Bitcoin Mechanic's show' everywhere |
| A2 N5: the real-gate test passed on exit status 0 alone | FIXED: it needs a report, the report's rows must be exactly the committed corpus, the table is recomputed in the test process, and PP_MOMENTS_CORPORA is not passed to the real exam |
| A2 N6 / B2 3, 7, 8: second defects in must-fails | FIXED: false_dialogue rebuilt from clean must-pass clips (the bridge 'Coin Bureau responds:', the bridge 'Not everyone is convinced.', and the sequence alone); sarcasm 04 (an imperative in the clip) and conditional_split 03 (condition expected to be met) out; Scott Melker titles now credit the show; hypothetical 02's title drops the source's own 'confirms'; where the real material carries a second trap by nature (a consequence clause's 'that' / 'it', a quoted opponent's accusation, a garbled referent) the case says so in `expected.also` |
| A2 N7 / B2 9: constructed cases recognisable (timing, spans, short descriptions, shared filler) | FIXED: each constructed case has its own neutral filler (no sentence shared with another case), irregular 2-decimal timings, ~60 s of context a side, a channel-style description cut at 600 characters like the real ones, a non-round publish time; `test_constructed_cases_look_like_real_ones` checks each shape occurs among the real cases; the partner attacks are now opinion-level ('have completely lost the plot', 'unwatchable'), no factual accusation |
| A2 N8: baseline not blind; cue words in the prompt; '60 s' text | FIXED: the prompt is now the laws' own wording (no example lists: the VO imperative and the exclusions are stated as L-t / L-u state them); v0 / v1 are labelled label-informing in STATE; v2 ran once on the frozen corpus |
| A2 N9: VO wording drift | FIXED: the paraphrases keep the clip's verbs and full disjunctions |
| A2 N10: no run pre-estimate; per-process ledgers; key fragments in reports | FIXED: a gate may define `preflight(counts)` and the baseline refuses a run its remaining budget cannot finish; the ledger path is pinned; every report row's why / traceback is redacted (sk-…, AIza…, xai-…, Bearer …, masked keys) |
| B2 1: the 80 s window departs from the order's 60 s | FIXED: every window is 90 s before / 60 s after; the one correction 74 s after the clip is stratum `beyond_window`, reported apart from the thresholds (R-24) |
| B2 2: only must-fail titles named persons; Scott Melker credited as a person | FIXED: one must-pass title names a verified person ('Swan Bitcoin's Cory Klippsten': the source description names him and he introduces himself inside the window); Scott Melker titles credit the show; the wrong_speaker titles keep the guest's name because that misattribution IS the class |
| B2 5: stale boundary unstated; a must-pass 'now' | FIXED: the rule is in every stale case's why ('a time word the title presents as current on the show date is a FAIL even though the caption dates the clip'); the 'we are now already at the phase' clip is out |
| B2 6: VO intro citations / a B-only line told the verdict | FIXED: intro, B line and sign-off are drawn from one pool for both labels; the format test covers VO slots, line count, intro citations and the B-only line |
| B2 10: 'no moment is used by two cases' was false; wrong_speaker 03's why; steelman 03 truncated?; Paraguay single-source? | CORRECTED: minimal pairs exist by design (above); wrong_speaker 03's why now says the host's voice is credited to the guest; steelman 03 is the full store sentence (the digest cut text at 240 characters; `test_the_package_carries_the_selected_sentences` asserts equality); the Taiwan 'just in' item (widely reported) is out; Paraguay stays because, as aired, it rests on one unnamed report plus speculation (why says so) |
| the sarcastic 'Sell your Bitcoin, all of it' | OUT of the exclusions corpus: two of three models read L-u's imperative rule as intent-based; whether a sarcastic imperative is excluded is a question for the orchestrator (STATE); the clip stays an unambiguous must-fail (sarcasm) in context_integrity only as long as it carries no second trap, so it left that corpus too |

# INTEGRATOR MERGE AUDIT OF PHASE 1 (pipeline_pp_dod, cycle 1, 2026-11-12 04:47 ET) — answers

Record: pp-tests_INTEGRATOR_AUDIT.md (+ the integrator's FRONTIER_anthropic.md). Every answer below is a fix in this
branch; every new or changed strict xfail was re-read with `--runxfail` (it fails on its own assertion, its controls
hold). Whole wall after the changes: see STATE.

## BLOCKING

- **B1 (fixed).** test_f3: `import release_auth as RA` / `import telegram as TG` (plain). An import error is now a
  collection ERROR (exit != 0), never a family skipped with exit 0.
- **B2 (fixed).** test_f2's template is a hook + TWO clips from THREE channels (DataDash, Natalie Brunell, Yahoo
  Finance: `adv_helpers.CLIP2_TEXT`, `CHANNELS`), legal under every reading of R-23, so R-23's fix keeps cut_template,
  every TestLockBinding test, the cut test and the R-09 / R-22 / R-18 pins valid (`cut_template` now also controls
  that all three cuts verify). R-23 is pinned per half: the clip half with hook + ONE clip from two channels, the channel
  half with hook + two clips all credited to one channel; each pin's control checks the other half holds. The R-09 pin
  asserts `ok is False` only (285 would select the 300 s repeat, not the verified 60 s passage) and its reason names
  R-09 + R-22; the R-22 probe now carries the leftover's OWN transcript (words up to the cut, its duration and sha256),
  so R-10's fix cannot flip it. New defect exposed by the two-clip template (a real one, measured): a failed
  transcription makes select's slot fallback raise `KeyError: 'VIDAAAAAAAA'` instead of a STOP: R-27, its own strict
  xfail (catches KeyError only); the R-10 select probe now asserts only its own subject (no old transcript used) and
  accepts an exception only after the transcription attempt.
- **B3 (withdrawn).** R-19 is withdrawn in REQUESTS (it loosened the quote check); its test was removed from the wall;
  the observed false reject is kept as a fact for the orchestrator, with what a non-loosening restatement would need.
- **B4 (fixed).** R-02 / R-03 now state `len(qt) >= 5 and ...` (the existing minimum kept); new passing pin
  test_f1 `test_an_empty_or_short_quote_is_never_verified` ('', whitespace, punctuation only, 1-4 canonical tokens said
  verbatim in the text: unverified; a 5-token control is verified). It must keep passing after R-02 / R-03.

## Not blocking (all answered in code unless said)

| item | answer |
|---|---|
| tautological CPU-guard test | replaced: a static scan of every pipeline / segment_v1 module the suite imports for code that sets CUDA_VISIBLE_DEVICES (only `qa_gates`, reviewed, may), and a runtime check that no CUDA runtime is initialised (torch, if loaded, `is_initialized()` False; ctranslate2 never loaded) |
| F3 required set from the unit under test | `PINNED_INVENTORY` (version 1, 16 + 17 rows) written in the test; the parametrisation uses it; `test_the_required_inventory_is_the_pinned_one` fails on any change |
| F4 call_gate RAISED-as-pass | removed: a gate exception now FAILS the probe (an xfail-marked probe reports FAILED, never XPASS); measured: no probe raises today |
| garbage-reply tests without positive controls | five controls added (rate_passages, derive_story_query, label_cluster, sentence_on_event, adjacent_admissible): a whole valid reply reaches each decision |
| adjudicate verdict filter | `verdict == "INCONCLUSIVE"` (measured for every BAD reply) |
| pytest.raises without match | `refused()` matches "^STOP: not authorised for release"; the legacy path matches "send_telegram_preview is removed" and checks nothing was sent; the partial-delivery resend matches "^STOP: " |
| 9:16 swap test | pins today's contract exactly: complete delivery, exactly one 9:16 sent, its sha256 the attested one |
| production_reading / blocked() model | corrected and pinned: production writes PASS iff the gate's ok is True (a gate-level skip nested in data is NOT read; stage_gates honours only run_all_gates' own top-level skip); `test_the_production_reading_is_the_code` pins the stage_gates / run_all_gates lines the model reads. Consequence, a NEW finding: G12 / G15 with no shout-out are PASS rows on nothing (R-28, two strict xfails); the release backstop now also covers G5, G9, G12, G15, G16, G20 rows and is controlled to have backed a real PASS |
| probes literal list | V1 covered by the module's real V1 tests (counted); `vertical_silent_fallback` named in NO_GATE_FUNCTION with the reason (a renderer flag: release backstop only) |
| R-04 control vs its fix | the control no longer reads `quote_verified`: precondition via `quote_in` (in B, not in A) + the reply reached the decision |
| R-22 / R-09 / R-11 / R-17 pins | R-22 and R-09 under B2; R-11 matches "not the transcript's words" with a control that digest and seal are valid; R-17 has a control that the gate asks the transcriber for `(final.mp4, 0.0)` |
| conftest process-global side effects | guards installed for collection, removed at `pytest_collection_finish`, re-installed by a MODULE-scoped autouse fixture per module of this directory; `remove()` restores exactly what `install()` replaced (tested) |
| network guard weaker than claimed | also sendto / sendmsg and every name lookup (getaddrinfo, gethostbyname[_ex], gethostbyaddr); child processes limited to ffmpeg / ffprobe / git / nvidia-smi / this interpreter (yt-dlp, curl, wget refused through run / check_output / Popen / call: tested) |
| network test's try without else | `else: pytest.fail(...)` |
| LAW 24 (qa_gates called directly) | the pins import `gates` first (a patch installed onto qa_gates at import applies); REQUESTS restated: a post-processing wrapper would leave the eight pins failing (never a false pass) and must re-point them in the same change |
| L-b fixture vs fixture | each documented must-fail edge is MEASURED on the reference now |
| WindowAudio equivalence | new test: edge_word_bounds on WindowAudio equals the whole-file SourceAudio decode on the 7 reference edges whose source is <= 1,300 s (the 8th source is 3,863 s: named) |
| _finals temp-dir leak | removed at process exit (atexit) |
| R-08 fail closed | REQUESTS: a reading where the lock's last-two-token run is not found counts as a leak / FAIL vote |
| PP-E1 / E5 / E6 / E9 / E11 wording | corrected to what the code and tests show (PP-E1: measured 233 / 233 accepted over 120 cases, 20 per kind; PP-E5: G12 / G15 are PASS rows, R-28; PP-E6: the 2,197 figure was a one-off; PP-E9: the pin stops at attest; PP-E11: the three broken promises and the rules added) |
| G8 table "SETTLED" | restated: measured once, two cells pinned |

Not done: nothing from the list. The integrator's UNCERTAIN lease question, checked by grep: run_fresh, release_auth,
telegram, visual_check and verify_pack never name the GPU0 lease file; the GPU0 helper (`run_fresh.free_gpu0_for_whisper`
-> `story_semantics.release_gpu0_for_whisper`) is called only from run_fresh's stages, and no test calls a stage (the
tests use `_samples`, `_status`, `tail_rows` and the text of `stage_gates`).

## How this answer was audited (spend freeze 05:30 ET: $3.00 for audits; every call metered, ledger + hard cap)

- Repo tool, run 1 (two cycles): its package extracts only a gospel section headed "## THE LAWS", and my brief had
  none, so the reviewers saw the diff without the orders. Not counted as an audit; kept in the scratch record.
- Repo tool, run 2 (two cycles, Gemini 2.5 Pro with the brief; GPT-4o: no credit; Grok: its gateway's daily cap):
  92 / 100, "production-ready after the P0". Consensus items and what was done:
  - P0 a Python child process escapes the network guard (the parent's socket patches are not inherited): FIXED.
    Every Python child starts with tests/adversarial/child_guard/ first on its PYTHONPATH (its sitecustomize refuses
    the network), -I / -S / -E children are refused, the exam's PP_MOMENTS_ALLOW_NETWORK=1 opt-in is the only way
    around it; regression test test_f0 test_a_python_child_refuses_the_network_too (BIBLE PP-E24).
  - P2 document the intentionally brittle assumption pins: done (docstrings; BIBLE PP-E25); P2 the R-19 example:
    PP-E11 / PP-E25; P3 atexit vs a fixture: kept (release_run is a plain helper), reason in the code.
- claude-opus-5-5, full diff (effort medium, 16K output): spent all 16,000 output tokens thinking and returned no text
  ($0.571, no finding). Not repeated.
- claude-opus-5-5, the 52 v1.1 labels only (effort low): READY; no confound, no wrong class. Acted on: the `why` of
  stale_price_title__01 now rests first on rule B (16K / 126K are in no selected sentence); host_commentary__08's
  aphorism after the freedom clip (readable as a gloss of the speaker's view) replaced by a plain reaction;
  host_commentary__13's 'That is why scarcity matters to me.' moved after the gold-mining clip it follows from;
  hedge_matched_attribution__07's `why` notes the clip was recorded two days before the show ('later this year' is the
  same year).
- Spend of these audits: see STATE (top).

## INTEGRATOR MERGE CYCLE 2 (pipeline_pp_dod, 2026-11-14 ~07:00 ET): three wall failures against law L-r, answered

The message (essentials): B1-B4 VERIFIED in 7a9a3555; the merge into release HEAD 6d7d4287 (which now carries law L-l
and law L-r's GPU leases, pipeline/gpu0.py) is conflict-free but HELD: `CUDA_VISIBLE_DEVICES= python3 -m pytest
tests/adversarial -q` -> 375 passed, 39 xfailed, 3 skipped, 3 FAILED: (1) test_f0's setter scan `{'conftest',
'qa_gates'} != {'qa_gates'}`; (2) test_f0's Whisper test "DID NOT RAISE RuntimeError"; (3) test_f2's R-27 pin meets
gpu0.LeaseMissing (gpu0.py:287) before its mocked failure: "decide whether the test should fake the failure below the
lease, or whether you see a real defect ... do not loosen the lease". Plus three questions about running the exam.

What was done:
- Merge commit f69497b5: the release line (combo-letterbox-quoteonly-v2 4286d879 = 6d7d4287 + one docs-only DoD commit)
  merged INTO pp-tests, so the wall is fixed against the code it will run on. Clean, no conflict, no content of mine:
  `git diff --stat cc8cccd0 f69497b5` lists only 4286d879's two docs files. Reproduced there first: the same 3 FAILED,
  375 passed, 39 xfailed, 3 skipped.
- The fix commit after it (tests and docs only):
  1. Setter scan: a TEST bug. It mapped each imported NAME to pipeline/<name>.py, so the suite's own `import conftest`
     blamed pipeline/conftest.py, which `pytest tests/adversarial` never imports. `_resolve(name)` now gives the file the
     interpreter gives this suite (`sys.modules[name].__file__`, else `importlib.util.find_spec`), with a control that
     `conftest` is the suite's own. Measured: old resolution 18 modules, setters {conftest, qa_gates}; new 17 modules,
     setters {qa_gates}; `conftest` is the only name that changed. KNOWN_CUDA_SETTERS stays {"qa_gates"}.
  2. Whisper: under L-r `word_diff.Transcriber()` is lazy and every pipeline load goes through gpu0. The test asserts
     both layers: at the transcriber's first use (span on a 1 s ffmpeg tone) gpu0.LeaseMissing with its exact message,
     nothing reaching faster_whisper, the gpu0 model not loaded, LeaseMissing not an Exception; and the stub still
     refuses and records a direct faster_whisper load.
  3. R-27: the TEST's layer, not a lease defect. The ordinary failure is injected at select's own seam
     (`_whisper_transcribe` returns None, its documented failure); R-27 is re-measured OPEN on the release line
     (`KeyError: 'VIDAAAAAAAA'` at select_passages.py:314). A lease refusal during select's transcription is L-r's
     design (a Gpu0Stop passes every `except Exception` to run_fresh's stage runner, which HOLDs): pinned PASSING by
     test_a_gpu_stop_during_transcription_leaves_select_and_writes_nothing (LeaseMissing with its message; the whole run
     directory identical before and after; nothing reaches faster_whisper). No request.
  4. R-10 (not failing, but broken by L-r): its proof of re-transcription was the stub's record, which L-r never
     reaches, so R-10's fix would have shown as an error, not an XPASS. Now: a LeaseMissing raised while select's seam
     is transcribing the replaced HOOK (the real function runs, wrapped to record which source).
  5. Docs: REQUESTS R-10 / R-27 notes and a new R-29 (for the builder: the exam adapter predates vo_fidelity v1.1);
     BIBLE PP-E26 (name-based import scans), PP-E27 (a newer, earlier guard takes over from a test's own), PP-E28 (an
     adapter older than its format); COVERAGE; XFAIL_EVIDENCE regenerated; STATE (top, and the exam answers).

Verification (merged tree, CPU only, nothing on any GPU, no network):
- Whole wall: 421 tests = 378 passed, 40 strict xfails, 3 skipped, 0 failed, 0 errors.
- `--runxfail`: exactly the 40 fail, each an AssertionError in its own test file (pp-tests_XFAIL_EVIDENCE.md).
- Scratch mutations (plugins loaded with -p from the scratchpad, never in the worktree): R-10's fix emulated for the
  hook -> XPASS(strict); a record written into the run directory before the GPU stop -> the snapshot test fails naming
  the file.
- regression_test.sh: 26 PASS / 0 FAIL / 5 WARN (relay key check, uncommitted files, shared stash count, two health
  URLs: the same five as on Nov 12).

How it was audited (spend freeze 05:30 ET Nov 12: $3.00 for audits; every call checked against and logged in the
ledger pp-tests_AUDIT_SPEND_0530.jsonl):
- Cycle 1, the repo tool's own package (utils/cross_llm_audit.py built it from pp-tests_AUDIT_CYCLE2_BRIEF.md and the
  diff; the brief is one "## THE LAWS" section, its extraction replayed before paying: 26,633 of 26,741 bytes reach the
  reviewers):
  - gemini-2.5-pro (the tool's leg): 100/100, no finding.
  - Heimdall qwen/qwen3.8-27b, reasoning effort none: 100/100, no finding.
  - Heimdall z-ai/glm-5.3-flash, reasoning effort none: 94/100, ready, five items.
  - gpt-4o: not reviewed (OpenAI HTTP 429 insufficient_quota). Grok: not run (xAI goes through its gateway with
    urllib, which this session's ledger cannot meter).
  - The tool's consensus step (claude-sonnet-4-6) failed: Anthropic HTTP 400, credit balance too low. The consensus
    was therefore written by the session, by pp-ingest's rule (same finding from >= 2 reviewers, or one reviewer's
    finding verified against the code): pp-tests_AUDIT_CYCLE2_C1_CONSENSUS.md.
- Cycle-1 dispositions:
  - glm P1, a control that `qa_gates` resolves to the expected file: REFUTED. The check is an equality with
    {"qa_gates"}: a qa_gates resolved elsewhere drops out of the set and FAILS the test (measured: it resolves to
    segment_v1/qa_gates.py; there is no pipeline/qa_gates.py).
  - glm P2, R-10's `whisper:` control too loose: ROOT CAUSE ACCEPTED (nothing tied the stop to the hook; my own review
    found the same): the hook attribution above. The exact model key is NOT pinned: a correct fix may use another
    Whisper variant.
  - glm P2, "writes nothing" claimed more than it asserted: ACCEPTED: the whole-run-directory snapshot.
  - glm P3, the ffmpeg timeout: not acted on (the test's own 1 s tone). glm P3, `_resolve` and packages: docstring.
- Cycle 2, the tool's own build_cycle2_prompt on the diff AFTER those dispositions:
  - Heimdall qwen3.8-27b: agrees with the cycle-1 consensus and the snapshot; "Yes with conditions". One new item,
    P1 "replace the ffmpeg tone with a pure-Python WAV": REFUTED. Transcriber.span() itself runs ffmpeg on the media
    before it reaches the model (word_diff.py:128), so the test cannot avoid ffmpeg. The order says "synthesise
    audio/video with ffmpeg on CPU", and the suite already depends on ffmpeg throughout (adv_helpers.make_media,
    ALLOWED_PROGRAMS, test_f0's own ffmpeg control). Its P2 (sys.modules and conftest) is covered by the control it
    names.
  - gemini-2.5-pro (retried once after HTTP 503 "high demand"): "Production ready: Yes"; agrees with every cycle-1
    disposition; no new finding.
  - Heimdall glm-5.3-flash (retried once; its first reply was cut by IncompleteRead, logged as an estimate): "Yes";
    agrees with every disposition and writes out the verifications (the anchored LeaseMissing regex, Model.__getattr__
    re-entering get(), `_whisper_transcribe -> None` as the documented ordinary failure, the unchanged 40-xfail
    count). Two P2s: N1, a missing ffmpeg should fail as a precondition (pytest.fail), not as an error: CONSENSUS
    with qwen's ffmpeg item in the form that fits the suite's convention, IMPLEMENTED (`H.control(shutil.which
    ("ffmpeg") ...)` and a control on the synthesis; with ffmpeg off PATH the test fails "CONTROL (test setup, not
    the pinned defect): ffmpeg is on PATH ..."); N2, record the R-10 mutation in the repo: already in REQUESTS R-10
    and in these committed records.
  - Final: no P0 or P1 stands (pp-tests_AUDIT_CYCLE2_FINAL_CONSENSUS.md). Records: pp-tests_AUDIT_CYCLE2_*.md.
- Spend of this audit: $0.177 over 7 calls (gemini-2.5-pro 2 calls $0.165; Heimdall qwen 2 calls $0.007; Heimdall glm 2
  calls $0.003 + $0.002 estimated for the lost reply). The audit ledger now stands at $1.850 of the $3.00 cap.
