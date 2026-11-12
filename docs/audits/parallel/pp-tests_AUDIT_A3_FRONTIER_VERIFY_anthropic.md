# Frontier verification round (claude-opus-5-5, effort high)

stop_reason: end_turn; model: claude-opus-5-5; usage: in 74931 / out 9319

# Verification round: PP-TESTS adversarial wall (after the second fixes)

## 1. Previous findings

### Original findings 1–8

**#1 HIGH (fixtures encode the pre-fix contract): RESOLVED.** The original caveat still stands.
- The diff still cannot show that today's `select_and_build_edl` ignores `sources/<vid>.section.json` and the transcript's `media_sha256`.
- If it does not, the clean controls (`TestKnownOffset`, `cut_template`) fail loudly. That is acceptable.

**#2 HIGH (strict xfails not pinned to an assertion): RESOLVED.**
- Unchanged from the last round: every strict xfail carries `raises=AssertionError`, and preconditions go through `H.control` → `pytest.fail`.

**#3 MEDIUM (R-19's CamelCase split): RESOLVED.**
- Unchanged: R-19 proposes removing spaces between alphabetic tokens and explicitly rejects the CamelCase split.

**#4 MEDIUM (probe swallows crashes; backstop filter): RESOLVED.**
- The residual gap is closed; see new item 2 below.

**#5 MEDIUM (silent "decimal dropped" skip): RESOLVED.**
- `test_a_different_number_sign_or_unit_is_not_said` has no `continue`.

**#6 MEDIUM (network, Telegram, GPU not blocked globally): RESOLVED.**
- The Telegram part is fixed by new item 1 below.
- The GPU limits are stated honestly in the conftest docstring: "an extra probe, not the guarantee … skipped when nvidia-smi is unavailable". Rejected-by-author, acceptable.

**#7 LOW (delivery order; no-break spaces): RESOLVED.**
- The no-break spaces are escapes (`"\u00a0"`, `"\u202f"`).
- The control is fixed; see new item 4 below.

**#8 LOW (environment-dependent pins; unclosed files; runtime): RESOLVED.**
- Unchanged from the last round.

### Missing reference FAILS, never skips: REJECTED-BY-AUTHOR, ACCEPTABLE and correct

- This is law L-m in the brief: "a missing reference is a FAILURE, not a skip".
- `_need` asserts with a message naming `PP_REFS_DIR`.
- `test_the_worktree_copy…` uses `pytest.fail`.
- Tests that open a reference directly raise `FileNotFoundError`, which is also a failure. Nothing can pass on an absent reference.

### Last round's new items 1–5

**New 1 MEDIUM (network guard raised `RuntimeError`): RESOLVED.**
- `adv_helpers.NetworkBlocked(BaseException)` is defined.
- conftest `_no_network` and `_no_network_ex` raise it.
- `test_f0` uses `pytest.raises(NetworkBlocked, match="network is disabled")`. It also proves that an `except Exception` does not absorb it (the `except Exception: pytest.fail(...)` / `except NetworkBlocked: pass` block).
- As a result, `pytest.raises(RuntimeError)` in `refused()`, `test_the_legacy_send_path_is_gone` and `test_a_partially_delivered_run…` can no longer be satisfied by a real send.
- The f4 probe's `except Exception` cannot swallow it either.
- `urllib` only wraps `OSError`, so `NetworkBlocked` propagates through `urlopen`, as `test_f0` asserts.

**New 2 LOW (backstop vs probe; stub arity): RESOLVED.**
- There is now one shared `call_gate(call, media, qa)` with the exception rule.
- Both `test_a_required_gate_never_passes_on_nothing` and the backstop use it (`if res is RAISED or production_reading(res) != "PASS": continue`).
- The stubs accept any arity: the `qa` fixture's `lambda *a, **k: ""`, `_Silent.span(self, *a, **k)`, and `no_face = lambda *a, **k: []`.

**New 3 LOW (R-10 transcript pin crash): RESOLVED.**
- The test now reads:
  ```python
  try: ok = _select(run)
  except RuntimeError as e: H.control("forbidden" in str(e), …); ok = False
  ```
- A RuntimeError other than the Whisper refusal surfaces as a CONTROL failure, not as an XPASS.

**New 4 LOW (delivery control vs first-video swap): RESOLVED.**
- The control is now `H.control(len(swapped) == 1 and s.sent[swapped[0] - 1]["name"] == "segment.mp4", …)`.
- `Sender` passes `n = len(self.sent)` after the append, so `sent[n-1]` is the message just sent.

**New 5 LOW (fixture on R-09's boundary): RESOLVED.**
- `source_audio(..., first_word_at=PAD_S + 0.25)`, so `start_s - pad ≈ dl_start + 0.25`.
- R-09 now says the containment is "(inclusive)" and that the request starts "0.25 s inside it".
- I checked the end side by arithmetic on `AFTER`:
  - 0.5 s pause before `AFTER`;
  - 13.36 s of words (36 words);
  - 1.5 s of pauses between its sentences;
  - 1.2 s tail.
- That totals 16.56 s after the last passage word, which is more than the 15 s pad. Containment holds on both sides.

## 2. New defects

**1. LOW–MEDIUM (uncertain: depends on `_download_window`'s structure, which is not in the diff): R-09's pin may not flip on R-09's own fix.**
- By R-22's own description, after a failed yt-dlp run `_download_window` "sees `getsize > 10_000` and returns the leftover".
- In `test_a_cached_window_of_another_request_is_never_relabelled`, the stale 285 s file is a full-size file.
- Under R-09's fix ("anything else is a cache miss"), the request falls through to yt-dlp. The fake fails, and today's post-download size check returns that same stale file under the requested offset 45.
- The test then keeps failing for an R-22 reason after R-09 lands. This errs in the safe direction (no false XPASS), but it misleads the integrator.
- Fix: in R-09, either require that "a miss whose download fails returns `(None, 0)` and never falls back to the file under the name", or state that this pin flips only with R-22.

**2. LOW: the 9:16 swap-during-delivery test fails a correct streaming refactor.**
- If `deliver_run` were refactored to verify each payload just before its send and refuse after the swap, it would raise.
- `TG.deliver_run(rd, send=s)` is called bare, so the test errors, even though the swapped bytes never reach the chat.
- The NOTE in the test already flags this.
- Optional fix: `try: TG.deliver_run(...) except RuntimeError: pass`, then assert that no `segment_vertical.mp4` was sent with a different sha256 (`vert == [] or vert[0]["sha256"] == att[...]`).

**3. LOW (environment-dependent): the `::1` case in `test_no_network_connection_can_be_opened`.**
- On a host or container with IPv6 disabled in the kernel, `socket(AF_INET6)` fails with `OSError` (EAFNOSUPPORT) before `connect` is called.
- `create_connection` then raises `OSError`, not `NetworkBlocked`, so `test_f0` fails for an unrelated reason.
- Fix: guard the `::1` address with `socket.has_ipv6`. Or build the socket directly, catch `OSError` at creation, and only then assert `NetworkBlocked` on `connect`.

No new defect is visible in the guard itself:
- `pytest.raises(..., NetworkBlocked)` with a `BaseException` subclass is supported.
- pytest records a non-`Exception` `BaseException` from a test as a failure.
- Under `raises=AssertionError` it shows as FAILED, not as the pinned defect.

**READY.** All of the last round's items are resolved. The remaining items are low-severity, and item 1 is a documentation fix in REQUESTS that errs in the safe direction (a pin that stays xfail longer, never a false pass).
