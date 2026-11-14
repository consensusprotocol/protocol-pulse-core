# claude-fable-5-2 (519 s) usage={'input_tokens': 72091, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 52538, 'output_tokens_details': {'thinking_tokens': 48536}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Scope.** Pipeline code, fixtures and the session's own audit records are not in the diff, so anything depending on them is marked UNCERTAIN. Line numbers are given only where I counted them; elsewhere the quoted code identifies the place. Nothing was executed. By my count the diff holds 38 strict xfails and every R-01..R-23 has at least one.

## BLOCKING

**B1. Family 3 can vanish as a skip.** `test_f3_release_auth.py` l.27–28: `RA = pytest.importorskip("release_auth")` / `TG = pytest.importorskip("telegram")`. If either module (or anything it imports) fails to import, the whole release-authorisation family reports SKIPPED with exit 0. Use plain imports.

**B2. The F2 template violates R-23, which the same session requests.** `test_f2_provenance.py` `template` (l.29–31) builds one hook and one clip; `test_select_with_fewer_than_two_clips_is_not_a_success` says so ("the template has a hook and ONE clip"). Once R-23 lands, `select_and_build_edl` returns False on every use of the template:
- `cut_template`'s `H.control(SP.select_and_build_edl(...) is True, ...)` fails, so every `cut_run` test errors (all of TestLockBinding, the cut test, both R-10 pins).
- `assert _select(run) is True` in `test_a_window_at_a_known_offset...` fails, and so does the control in the R-18 test.
- `ok is False or ...` (R-09 pin) and `assert ok is False` (R-22 pin) XPASS for the wrong reason.
- `test_select_with_one_channel_is_not_a_success` uses the same one-clip template, so it flips on the clip-count half alone. The channel half of R-23 has no independent pin.

**B3. R-19 loosens the quote check, and a strict xfail demands it.** REQUESTS R-19 says itself: "it changes what the quote check accepts". Removing spaces between alphabetic tokens equates different word sequences. As worded it can also re-admit R-02's own trap ('coin fell below' inside 'Bitcoin fell below'); that depends on implementation. `test_a_compound_name_written_apart_is_the_same_quote` can only clear by that loosening. Do not apply R-19; pull the test from the wall pending an orchestrator decision.

**B4. R-02 / R-03 as written verify an empty quote.** R-02's code is `any(tt[i:i + len(qt)] == qt for i in range(len(tt) - len(qt) + 1))`. With `qt == []` this is True for any text. BIBLE PP-E10 says `quote_in` has a "5-token minimum" today; neither request says to keep it, and no shown test pins an empty or short quote as unverified. Whether the guard lives in `quote_in` or a caller is UNCERTAIN. Blocking for applying the requests verbatim.

## (1) Not load-bearing — not blocking

- **`test_f0_cpu_guard.py::test_no_cuda_device_is_visible`**: asserts `os.environ.get("CUDA_VISIBLE_DEVICES") == ""`, which the autouse `_cpu_only` fixture set immediately before. `import qa_gates` is a cached no-op. Tautology.
- **F3 required set comes from the unit under test**: `REQUIRED = [... sorted(RA.INVENTORY[fmt])]` and `passing_rows(ra)`. Deleting a row from `release_auth.INVENTORY` shrinks the parametrisation and the control together. `test_every_required_row_has_a_vacuity_probe` only checks `required <= set(covered)`. Only `G14_av_alignment` is named independently (test_f5, last test).
- **`test_f4_vacuity.py::call_gate`**: any exception whose last frame is outside `tests/adversarial` returns `RAISED`, and the test then does `return`. The 25 unmarked probes pass if the gate crashes on the probe's malformed input, with only a warning.
- **`production_reading` and `blocked()` are the test's own model of `run_fresh.stage_gates`.** The docstring concedes "the stage itself needs GPU0". The "recorded SKIPPED" reading for G12/G15 and the "samples = `_samples(data)`" evidence are never observed from production.
- **`test_every_required_row_has_a_vacuity_probe`**: `probes = [...] + ["V1", "vertical_silent_fallback"]`. Those two rows are covered by literals. No gate function for `vertical_silent_fallback` is called anywhere; only `blocked("9x16", "vertical_silent_fallback", [])` runs.
- **Garbage-reply tests without a positive control**: `rate_passages`, `label_cluster`, `sentence_on_event`, `adjacent_admissible`, `derive_story_query`. Only `adjudicate` and V1 have one. If the fake never reaches the decision (e.g. the `pid` / `id` mapping), they still pass. UNCERTAIN whether that happens.
- **`test_adjudicate_never_counts_a_garbage_reply`**: `v["verdict"] in ("INCONCLUSIVE", "UNRELATED", "TOPIC_ONLY", "BACKGROUND", "CURRENT_EVENT")` includes the positive verdict, so that clause filters nothing.
- **`test_the_legacy_send_path_is_gone`** and **`refused()`**: `pytest.raises(RuntimeError)` with no `match`. For the legacy test the argument is a non-existent `"run_dir"`, so any RuntimeError satisfies it.
- **`test_the_9x16_swapped_during_delivery_never_reaches_the_chat`**: `except RuntimeError: pass`, then `all(...)` over a possibly empty `vert`. It also accepts a half-delivered drop.
- **`test_l_b_the_documented_must_fail_is_an_overlap`**: the first loop asserts `LB["measured"][...] > 0`, fixture against fixture.
- **`adv_helpers.WindowAudio`** is a test-side replica of `sentence_law.SourceAudio`. "Equal to the whole-file decode ... (checked 2026-11-12)" is enforced by no test.
- **`test_no_network_connection_can_be_opened`**: the last `try` has no `else`, so a silent success would pass. The earlier `pytest.raises` blocks cover it.

## (2) xfail reason vs assertion — not blocking unless noted

- **R-04**: the control `H.control(v["quote_verified"] is True, ...)` contradicts the proposed fix (`quote_ok = quote_in(quote, supporting excerpts)`). After the fix the quote is not in the supporting excerpt, so the control fires and the test goes FAILED as "test setup", not XPASS. This assumes `quote_verified` reflects `quote_ok`, which the REQUESTS wording implies. Fix in the same change as R-04.
- **R-22 pin** (`test_a_failed_download_never_supplies_a_source`): it removes `section.json` but leaves the template transcript, whose `media_sha256` is of other bytes. With R-10 alone it either fails on the Whisper stub's RuntimeError or XPASSes; which depends on select's exception handling (UNCERTAIN). Either way it contradicts PP-E11's rule that each probe keeps every other fix's record consistent.
- **R-09 pin**: the reason names only R-09, but REQUESTS says it flips only with R-09 and R-22 together. Its alternative `source_window_offset_s == 285` also accepts selecting the 300 s repeat in place of the verified 60 s passage.
- **R-11 pin**: `assert L.verify_lock(lock, tp) != []` accepts any error string, unlike its neighbour, which matches "transcript changed". It could flip on an unrelated verify_lock error.
- **R-17 pin**: the stub fires only on `(media, t0) == ("final.mp4", 0.0)` and there is no control that the gate calls `span` with exactly that. UNCERTAIN.
- **F4 marked probes**: a gate that starts raising on empty input makes the strict xfail XPASS via `RAISED`, and so reads as fixed.
- **LAW 24**: eight xfails (R-07, R-08, R-13 ×4, R-20, R-21) call `qa_gates` directly. REQUESTS claims they work "either way", but a wrapper fix in `pipeline/gates.py` would never flip them.

## (3) State, network, GPU, lease

- No shown test references `/tmp/pulse_gpu0.lease`. UNCERTAIN whether these touch the lease or write outside the run directory: `import run_fresh` (at collection, `test_f4` `_cases()`), `RA.attest`, `TG.deliver_run`, `VC.ask_panel`.
- **Network guard is weaker than conftest claims.** It patches only `socket.socket.connect` / `connect_ex` in this process. DNS lookups, `sendto` and child processes are not covered. `FakeYtDlp` intercepts only `.run`; `__getattr__` passes `Popen` / `check_output` to the real module. Today's download path does go through `.run` (asserted in test_f2).
- **GPU guard**: conftest runs `import qa_gates` while that module has set `CUDA_VISIBLE_DEVICES='0'`. Whether anything initialises CUDA at import, or another module sets the variable on first import inside a test, is UNCERTAIN.
- **Process-global side effects**: the `faster_whisper` stub in `sys.modules`, the socket patch and the `sys.path` inserts are set at conftest import and never undone. Running `pytest tests/` applies them to every other suite in the session.
- `adv_helpers._finals()` leaks an `adv_finals_*` temp directory per process.
- F5 reads `/home/ultron/protocol_pulse/references` by absolute path. Frames go to `tmp_path`; this is allowed by the order.

## (4) Requests

- R-19 and R-02/R-03: see B3, B4.
- **R-08**: it does not say what happens when the lock's last two tokens are not found as a run in a reading. It must fail closed, or it loosens the leak check. Not blocking.
- The rest read as tightenings.

## (5) BIBLE_ADDITIONS vs code — not blocking

- **PP-E1** (and R-05) say "40 per kind" / "240 generated cases"; the code has `ANCHOR_CASES = CASES[:120]  # ... 20 of each kind`. "Accepted every one" is not what the tests assert; one accepted mutant keeps them xfailed.
- **PP-E9** (and R-12) say "attested ALL_PASS and delivered". The cited test stops at `RA.attest` and never calls `deliver_run`. The mutated headline adds "$90,000", which the G18 readings lack, so delivery may refuse. UNCERTAIN.
- **PP-E5**: "recorded SKIPPED" and "release_auth's evidence rule blocks them" rest on the test's own `production_reading` / `blocked()`.
- **PP-E11** and the REQUESTS preamble ("a fix implemented with exactly those names keeps every control valid"): contradicted by B2, the R-04 control and the R-22 probe.
- **PP-E6**: the 2,197-sentence figure is from R-01; the shipped test covers only the `canon_20261111` fixture.
- **REQUESTS G8 table "SETTLED"**: tests pin only 9:16 clip_03 (production wiring, rebuilt in the test) and hook (no sources). The other cells are unpinned.