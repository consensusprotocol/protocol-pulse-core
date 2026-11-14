# claude-fable-5-2 (134 s) usage={'input_tokens': 4224, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 13122, 'output_tokens_details': {'thinking_tokens': 10762}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'}

**Verdict: two BLOCKING holes remain in R5.** The cycle-1 fixes for the eight listed degenerate durations are correct as written: all eight take the fail branch at `pipeline/edl_rules.py:237-239`. Line numbers for `edl_rules.py` are counted from the hunk headers; `test_edl_rules.py` numbers are approximate (±1). Nothing was executed; all results are from reading the diff.

## Degenerate inputs that pass

**1. BLOCKING — a missing, None or empty channel counts as a distinct channel.** `edl_rules.py:235` reads `ch = clip.get("channel", "unknown")`, and `:240` runs `channels.add(ch)` with no validation.
- `{"clips":[{"index":1,"duration":15,"channel":"A"},{"index":2,"duration":15}]}` gives `channels == {"A","unknown"}` and returns `(True, "R5 PASS: clip lengths and channel diversity OK")`.
- `"channel": None` and `"channel": ""` pass the same way, as do `"A"` vs `"A "` or `"a"`.
- The default is pre-existing, not introduced here. But the docstring at `:220` now claims "INTEGRITY (law L-o, fail closed)", and channel count is the only integrity left in R5.
- This is the same class as the missing-duration hole fixed in cycle 1, on the other key.
- Whether R6 catches it downstream is uncertain (not in the diff).

**2. BLOCKING — any ε > 0 registers a channel.** `edl_rules.py:237` only requires `dur > 0`.
- A second clip of `{"duration": 1e-9, "channel": "B"}` returns `True` with `clip 2: 0.00s (12.00s under the 12-20s target)`.
- The docstring's purpose at `:221`, "so no channel is counted with no screen time", is therefore not met: a sub-frame duration is zero frames.
- The recorded text on this pass shows `0.00s`, the same value as the 0 case that fails.
- The removed lines `- if total_dur < 8` were the only floor, and nothing replaced them, not even one frame.
- Downgrade this only if the law owner states that any ε is acceptable.

**3. Not blocking (uncertain) — no upper sanity bound.** `duration: 1e300` is finite and positive, so it passes at `:243-244` as a "taste deviation" with a reason over 300 characters. Whether "the gates" on the final catch it is outside the diff.

**4. Not blocking — a huge integer crashes instead of failing.** `math.isfinite(dur)` at `:237` raises `OverflowError` for an int such as `10**400`, which `json.loads` will produce. It is a crash, not a pass, and the old `{dur:.1f}` raised too. Whether `stage_validate` treats an exception as a failure is uncertain.

**5. Not blocking (pre-existing, uncertain) — malformed containers crash.**
- `"clips": None` raises `TypeError` at `:229`.
- A non-dict clip raises `AttributeError` at `:234`.
- An unhashable channel (list or dict) raises `TypeError` at `:240`.

**6. Not blocking (uncertain) — "measured" is established by type only.** `:234` reads a declared `duration` field. Nothing in the diff cross-checks it against the clip's in/out points.

## Integrity and record

**7. Not blocking — stale spec text contradicts the code.** The claim "module docstring is updated" is only half true.
- `edl_rules.py:19` is an unchanged context line that still says `channels. Every channel >= 8s screen time.`
- `:18` now ends in a duplicated `>= 2 distinct`.
- The `TestR5ClipLength` docstring (`test_edl_rules.py` ≈180-181) says "the 8-25 s window and the per-channel >= 8 s total are taste (a recorded deviation with its size…)". The code uses 12-20 and records no per-channel total at all.

**8. Not blocking — rounding produces a self-contradictory record.** At `:242`, `dur = 11.996` yields `clip N: 12.00s (0.00s under the 12-20s target)`. The same happens at 20.004 on `:244`.

**9. Not blocking — the reason string is unsanitised.** `idx` and `{dur!r}` are interpolated raw at `:238`, `:242` and `:244` into a string whose structure depends on `; ` and ` | law L-o taste deviations…`. A string index or duration containing those delimiters makes the provenance text ambiguous, and its length is unbounded.

**10. Uncertain — the provenance claims cannot be checked here.** The docstring at `:224` and the `run_fresh.py:405-416` and Telegram claims are outside this diff. What is verifiable is that deviation sizes exist only as free text inside `reason`, with no structured field.

**11. Uncertain — the pass string changed shape.** `:253` returns `"R5 PASS | …"`, with no colon after PASS. Any consumer matching `"R5 PASS:"` or the old exact string would misread it; none is visible in the diff.

## Test weaknesses

**12. Not blocking — the unmeasured-duration test does not isolate its claim.** In `test_an_unmeasured_duration_is_never_a_pass` (≈232-241), every subtest uses channel A valid plus a bad channel B. Each EDL therefore also fails `only 1 channel(s)`.
- `assertFalse` plus `assertIn("is not a measured positive number")` would still pass if the message were appended to `deviations` instead of `failures`.
- The docstring's "must fail on its own" is untested. It needs a case with A valid, B valid and a third bad clip, with exact-string equality.

**13. Not blocking — the mixed-output assertion never checks `ok`.** The final case in `test_integrity_still_rejects_one_clip_or_one_channel` (≈228-230) uses only `assertRegex`. The regex also stops at `causes: `, so the two deviation strings are not pinned.

**14. Not blocking — "registers no channel" is asserted for `0` only** (≈222-223). The other seven degenerate values are covered only by sharing the code path.

**15. Not blocking — there are no just-outside boundary cases.** Nothing tests 11.99 or 20.01. Changing `dur < lo` to `dur < lo - 1` survives the suite (6.1, 30, 12.0, 20.0).

**16. Not blocking — no tests exist for findings 1, 2, 4 and 5.** Missing, None or empty channel, ε duration, huge int and a non-dict clip are all uncovered.

**17. Uncertain — tests outside the hunk may be stale.** The hunk ends at `test_single_channel_fails`. Whether later tests still assert `max 25s` or the per-channel `min 8s` cannot be seen, and no suite-run result is given.