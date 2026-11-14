# Frontier verification round (claude-opus-5-5, effort high)

stop_reason: end_turn; model: claude-opus-5-5; usage: in 75210 / out 12009

# Verification round: PP-TESTS adversarial wall (after fixes)

## 1. Previous findings

**#1 HIGH (fixtures encode the pre-fix contract): RESOLVED**, with one caveat I cannot verify.
- `adv_helpers.write_section` writes `{"dl_start", "dl_end", "sha256"}`, and `write_source` calls it.
- The transcript now carries `"media_sha256": sha256(media)`.
- `MEASURED = ("edl.json", "out/segment.mp4", …)`.
- Family 3 now uses a genuinely different headline: `"Bitcoin price surges past $90,000"`.
- `_replace_source` rewrites a consistent download record, so only R-10's media binding can flip the byte-replacement pins.
- REQUESTS states the dependency in its preamble and in R-09, R-10 and R-12.
- Caveat: whether today's code ignores the extra keys is still not visible in the diff. If it does not, the clean controls (`test_control_the_clean_run…`, `TestKnownOffset`) fail loudly, not silently.

**#2 HIGH (strict xfails not pinned to an assertion): RESOLVED.**
- Every strict xfail in f1–f4 now carries `raises=AssertionError`, including the `_xf` helper in f4.
- Preconditions use `H.control`, which calls `pytest.fail`. That raises `Failed`, not `AssertionError`, so a broken fixture or control reports FAILED/ERROR even in setup.
- `rows[0]["lock_diff_reported"]` raises `KeyError` if the field is renamed, which also reports FAILED.
- The G8 stale-frame test no longer guesses frame names: it runs the gate twice into the same `qa_dir`.
- The Whisper refusal in the transcript test is still not caught explicitly; see new item 3.

**#3 MEDIUM (R-19's CamelCase split): RESOLVED.** R-19 now proposes removing spaces between alphabetic tokens. It explicitly rejects the `canon.fold` CamelCase split, citing the all-caps break.

**#4 MEDIUM (probe swallows crashes; backstop filter): RESOLVED**, with a residual gap.
- The probe re-raises when `tb[-1]` is in `H.HERE`. That catches a wrong signature at the call site and a bad tuple unpacking in `production_reading`.
- The backstop now filters on `production_reading(res) != "PASS": continue`. It also checks the vacuous shapes `([], {}, {"skip":…}, None, …)` directly, so it never checks nothing.
- Residual gap: see new item 2.

**#5 MEDIUM (silent "decimal dropped" skip): RESOLVED.** `test_a_different_number_sign_or_unit_is_not_said` no longer has a `continue`. Whether it passes today is not verifiable from the diff.

**#6 MEDIUM (network, Telegram, GPU not blocked globally): PARTLY.**
- Network: the global guard `socket.socket.connect/connect_ex` raises for `AF_INET`/`AF_INET6`, loopback included, and `test_f0` proves it.
- GPU: the session check still runs once at the end and still returns when nvidia-smi is missing. The docstring now states both limits honestly ("an extra probe, not the guarantee"). Rejected-by-author, acceptable.
- Telegram: the guard's exception type makes the legacy-send test unable to fail; see new item 1.

**#7 LOW (delivery order; no-break spaces): PARTLY.**
- No-break spaces are fixed: `"\u00a0"` and `"\u202f"` are now escapes.
- The swap now fires on the first `kind == "video"` send.
- But the control contradicts that logic; see new item 4.

**#8 LOW (environment-dependent pins; unclosed files; runtime): RESOLVED / acceptable.**
- `ffmpeg_version` is recorded in `reference_lb_edges.json`. The failure message distinguishes "the DECODER changed: re-measure" from "same decoder".
- Writes now go through `with open` or `edit_json`; the remaining bare `open` calls are read-only.
- The G8 reference tests now measure one segment each, which reduces the runtime risk.

**Missing reference FAILS, never skips: ACCEPTABLE, and correct.** That is law L-m in the brief, and `PP_REFS_DIR` gives a portable override.
- `_need` asserts.
- Tests that open a reference file directly, such as `test_the_two_formats_share_one_timeline`, error out with `FileNotFoundError`, which is also a failure.

## 2. New defects

**1. MEDIUM: the network guard raises the same exception the Telegram tests expect, so they cannot detect a network regression.**
- conftest `_no_network` does `raise RuntimeError("tests/adversarial: network is disabled …")`.
- `test_the_legacy_send_path_is_gone` passes with `with pytest.raises(RuntimeError): TG.send_telegram_preview(...)`. If the legacy path regresses and really tries to send, the guard's `RuntimeError` satisfies the test, so it passes on the exact regression it pins. (`requests`/`urllib3` wrap `OSError`, not `RuntimeError`, so it propagates unchanged.)
- `refused()` and `test_a_partially_delivered_run…` rely on the same `pytest.raises(RuntimeError)` around `deliver_run`.
- The f4 probe's `except Exception: return` would likewise swallow a gate that reached the network.
- Fix:
  - Raise a dedicated `class NetworkBlocked(BaseException)` from the guard (update `test_f0` to `pytest.raises(NetworkBlocked)`), or
  - in each `RuntimeError` expectation, assert `"network is disabled" not in str(e.value)`.

**2. LOW: the backstop does not tolerate what the probe accepts.**
- `test_a_required_gate_never_passes_on_nothing` treats an exception raised inside a gate as "not a PASS".
- `test_whatever_a_gate_returns…` calls `res = fn(media, qa)` unguarded.
- A fix that makes a gate raise on empty input (legitimate per the probe) turns the backstop into an ERROR.
- Relatedly, a stub-signature mismatch is misread. If a gate calls the test's `whisper_segment` lambda with another arity, the `TypeError`'s last frame is the gate's, so the probe reads it as a gate crash and passes silently.
- Fix: share one `_call_gate` helper with the probe's exception rule. Make the stubs `lambda *a, **k: ""`.

**3. LOW: the R-10 transcript pin may report a crash instead of XPASS once the fix lands.**
- `test_a_transcript_of_other_bytes_is_never_used` calls `_select(run)` bare.
- After R-10, the Whisper stub raises `RuntimeError`. If `select_and_build_edl` does not catch it, the test reports FAILED with a `RuntimeError` (loud, thanks to `raises=`), not XPASS. The integrator then sees an unexplained crash.
- Fix:
  ```python
  try:
      ok = _select(run)
  except RuntimeError as e:
      H.control("forbidden" in str(e), str(e))
      ok = False
  ```

**4. LOW: the delivery control contradicts the first-video swap.**
- `H.control(swapped == [1] and s.sent[0]["name"] == "segment.mp4", …)` while `swap` records `n` for the first video.
- If a text message precedes the first video, which the clean control allows (`[m for m in s.sent if m["kind"] == "video"]`), this control fails.
- Fix: `H.control(len(swapped) == 1 and s.sent[swapped[0] - 1]["name"] == "segment.mp4", …)`.

**5. LOW (uncertain): the fixture download record sits exactly on R-09's boundary.**
- `write_section(run_dir, vid, offset, …)` sets `dl_start = offset`, while the passage's first word is placed at `PAD_S = 15.0` and the pad is 15 s.
- Under R-09's proposed rule (`[start_s - pad, …] ⊆ [dl_start, dl_end]`), the clean fixture is a hit only if `start_s - 15 ≥ offset` survives the 3-decimal rounding in `speech_like` and `source_audio`.
- A floor or rounding of `start_s - pad` in the fix would make the clean template a cache miss. That would show loudly in `TestKnownOffset`, but it would block the fix.
- Fix: state in R-09 that the containment check is inclusive with a small tolerance (for example 1 ms), or place the first word at `PAD_S + 0.5`.

**NOT READY.** Item 1 leaves a test that cannot fail on its own regression; it is a one-line fix. Items 2–5 are small.
