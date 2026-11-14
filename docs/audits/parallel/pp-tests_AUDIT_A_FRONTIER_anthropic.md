# Frontier review (claude-opus-5-5, effort high) - pp-tests_audit_A

stop_reason: end_turn; model: claude-opus-5-5; usage: in 67603 / out 15804

# Review: PP-TESTS adversarial wall (tests-only diff)

## Findings, most severe first

### 1. HIGH (categories 2 and 5): the fixtures encode the pre-fix contract, so the proposed fixes R-09, R-10 and R-12 break today's controls and silence other xfails

**R-09 and R-10 (family 2).**
- `adv_helpers.write_source` writes `sources/<vid>.mp4` and `transcripts/<vid>.json` (`{"words", "language", "duration"}`). It writes no `sources/<vid>.section.json` and no `media_sha256`.
- R-09's fix says: "a cache hit is accepted only when that record exists … anything else is a cache miss."
- R-10's fix says: "reuses a cached transcript only when it matches."
- Once either fix lands, three things break:
  - `TestKnownOffset::test_a_window_at_a_known_offset_is_recorded_in_file_coordinates` fails. It asserts `ytdlp.calls == []` and `source_window_offset_s == off`.
  - The module fixture `cut_template` fails at `assert SP.select_and_build_edl(...) is True`.
  - Everything built on `cut_run` errors in setup. That includes the two passing `TestLockBinding` tests and the R-10 / R-11 xfails.
- Pytest applies an xfail mark to setup-phase exceptions too; this is my understanding of `skipping.py`, so please verify. If so, the strict xfails `test_a_lock_whose_words_are_not_its_transcripts_words_is_refused` (R-11) and `test_g16_refuses_a_source_whose_bytes_changed_after_the_lock` (R-10) stay "xfailed" for the wrong reason. Their flip signal is lost.
- Other xfails would XPASS for the wrong reason. `test_select_with_fewer_than_two_clips_is_not_a_success`, `test_select_with_one_channel…` (R-23) and `test_a_failed_download…` (R-22) only need `ok is False`. A fixture that now misses its cache supplies that.

**R-12 (family 3).**
- `adv_helpers.MEASURED` lists the two finals and the two manifests only; it does not include `edl.json`.
- R-12's fix makes `attest` compare `"edl.json"` against `measured_files`.
- When that lands, `test_control_the_clean_run_is_authorised_and_delivered` fails.
- Every `attested_hold` / `refused` must-fail test then passes vacuously, because every run HOLDs for the missing EDL digest rather than for its own mutation.
- Also in `test_an_edl_changed_after_the_gates_ran_holds`, `d.__setitem__("headline", "Bitcoin price dip")` sets the value `release_run` already wrote. The "another headline" half of the mutation is a no-op; only the channel change is applied.

**Fix.**
- Make the helpers produce what the fixed code will require, as extra data that today's code ignores:
  - `write_source` writes `section.json` (`dl_start` = offset, `dl_end`, `sha256`) and puts `media_sha256` in the transcript.
  - `release_run` adds `edl.json` to `measured_files`.
- Check that today's code ignores the extra keys (I cannot verify that from the diff).
- In family 3, use a genuinely different headline.
- State this dependency in REQUESTS R-09, R-10 and R-12.

### 2. HIGH (category 2): no strict xfail pins its failure to an assertion, so any crash keeps the test "xfailed" forever

- None of the roughly 25 `pytest.mark.xfail(strict=True, …)` marks passes `raises=AssertionError`.
- Without it, any exception counts as the expected failure, including a KeyError, a TypeError or a fixture error.
- "Each was read with --runxfail" protects only the day it was read.
- Concrete case: `TestDirtyCache::test_a_transcript_of_other_bytes_is_never_used` asserts `ok is False or whisper_attempts()`.
  - After R-10, `select` attempts Whisper. The conftest stub raises `RuntimeError`.
  - If `select_and_build_edl` does not catch it (I cannot verify this), the test keeps raising after the fix and never flips.
- Other examples where a rename turns the test into a permanent false xfail:
  - `rows[0]["lock_diff_reported"]` in `test_gate_g18_fails_a_number_that_differs_from_the_lock`.
  - The guessed frame names `g8_hook_{i}.png` in `test_g8_never_measures_a_frame_of_an_earlier_render`. Whether G8 uses those names is not verifiable from the diff.

**Fix.**
- Add `raises=AssertionError` to every strict xfail.
- In the transcript test, catch the refused Whisper load explicitly (`pytest.raises` or `try`) and assert on it.

### 3. MEDIUM (category 5): R-19's proposed CamelCase split would break family-1 tests that pass today

- R-19 proposes that "`canon.fold` splits a lower-to-upper CamelCase boundary … applied to both sides by every site."
- The generator mixes CamelCase subjects with an all-caps surface variant:
  - `SUBJECTS` includes `"MicroStrategy"` and `"BlackRock's fund"`.
  - `ACTOR_SWAPS` includes `"BlackRock"`.
  - `_surface` branch `k == 2` is `t = t.upper()`.
- Under the proposed fold, `MicroStrategy` becomes `micro strategy`, but `MICROSTRATEGY` stays `microstrategy`.
- The following then fail on those cases:
  - `TestCanonicalForm::test_surface_variants_compare_equal`
  - `TestG18::test_diff_equal_variants_and_unequal_mutants`
  - `TestQuoteVerification::test_variants_verified_mutants_refused`
  - `TestSelectionAnchors::test_surface_variants_anchor_on_the_sentence`
- REQUESTS mentions only the `Microstrategy` gap, not this break.

**Fix.**
- Record in R-19 that the split breaks upper-case equality.
- Prefer the alternative it already names: a token run compared with internal spaces removed.

### 4. MEDIUM (categories 1 and 3): the family-4 probe swallows its own crashes, and the backstop test does not filter what its docstring says

**The probe.**
- `test_a_required_gate_never_passes_on_nothing` does `except Exception: return`.
- A TypeError in the probe's own call therefore passes the non-xfail cases silently. Examples: a wrong signature in `RF.tail_rows(True, False, None)` or `Q.gate_g8(..., fmt=...)`.
- A 3-tuple return also crashes `production_reading`'s unpacking and passes the same way.

**The backstop.**
- `test_whatever_a_gate_returns_on_nothing_release_blocks_it` claims "For every vacuous probe that PASSES at gate level".
- It actually iterates every case that has a mark (`if mark is None: continue`) and asserts `RF._samples(data) == 0`.
- After R-13, R-14 or R-15, a gate returns `(False, [{"error": "nothing measured"}])`. If `_samples` counts rows (not verifiable from the diff), this currently passing test breaks once those fixes land.

**Fix.**
- In the probe, catch only expected gate failures and fail on `TypeError` / `ValueError` raised from the test frame.
- In the backstop, filter on `production_reading(res) == "PASS"` rather than on the mark.

### 5. MEDIUM (category 3): one must-fail mutant kind is silently skipped, with a comment the code contradicts

- `TestHeadlineNumbers::test_a_different_number_sign_or_unit_is_not_said` has `if lab == "decimal dropped": continue   # '$40 billion' vs '$40.0 billion': no decimal to drop`.
- But `_case_scale` only creates that mutant when there is a decimal (`if "." in x: mutants.append(("decimal dropped", …))`).
- So the skip removes every real case, for example `$1.66 billion` vs `$1 billion`. Those are different numbers and should be "not said".
- If it fails today, the brief requires a strict xfail plus a request, not a skip.

**Fix.** Remove the skip, or make it a strict xfail with a REQUESTS entry.

### 6. MEDIUM (category 4): network, Telegram and GPU are not blocked globally

**Network and Telegram.**
- "No network" depends on per-test fakes: `VC._call` in `_v1` only, `fake_llm`, and injected `send`.
- `test_the_legacy_send_path_is_gone` calls the real `TG.send_telegram_preview("run_dir", "caption")`. If the legacy path regresses, the test itself attempts a real Telegram send.

**GPU.**
- `pytest_sessionfinish` checks nvidia-smi once, at the end of the session. It misses memory that was held and then released.
- It also passes silently when nvidia-smi is missing: `except (OSError, ...): return`.
- The brief's claim, "asks nvidia-smi whether the suite held GPU memory", is stronger than this check.

**Fix.**
- Add an autouse conftest guard that blocks outbound connections, for example by monkeypatching `socket.socket.connect` to raise on non-loopback addresses.
- Monkeypatch the Telegram HTTP seam before calling the legacy entry.

### 7. LOW (category 1): delivery test and surface variants

**Delivery test.**
- `test_the_9x16_swapped_during_delivery_never_reaches_the_chat`'s docstring says "The 16:9 goes out, then the 9:16 … is replaced."
- But `swap` fires on send #1. The control shows non-video sends exist (`[m for m in s.sent if m["kind"] == "video"]`), so send #1 may be a text message.
- The property is still tested, but not in the order described.
- Fix: swap after the first send whose kind is `"video"`.

**Surface variants (uncertain).**
- As shown in the diff, `_surface` branch 4 `t.replace(" ", " ", 2)` is a no-op. `_dollars("narrow_nbsp")` also uses an ordinary space.
- If the non-breaking-space characters were lost, the no-break-space variant is never generated.
- Fix: use `"\u00a0"` / `"\u202f"` escapes.

### 8. LOW (category 6): pinned values depend on the environment, and some files are left unclosed

**Pinned values.**
- `reference_lb_edges.json` (10 ms grid, exact equality) and `abs(row["out_median"] - floor) < 0.005` depend on the installed ffmpeg/libavcodec decoder and resampler.
- An ffmpeg upgrade fails family 5 even though the references did not change.

**Unclosed files and runtime.**
- `json.dump(d, open(tp, "w"))` (f2, f3, f4) relies on CPython refcounting to flush before the next read.
- The two v2f G8 tests each decode about 1,000+ frames of 1080×1920 video; this is a timing risk under load against the 5-minute budget.

**Fix.**
- Record the ffmpeg version in the fixture and fail with a clear "decoder changed, re-measure" message.
- Use `with open(...)`.

## Categories with nothing found

- **Writes outside tmp / references:** none found. All writes go to `tmp_path`, `tmp_path_factory` or `mkdtemp`, and the references are only read. The `_finals()` scratch directory is never removed, which is acceptable.

**NOT READY**
