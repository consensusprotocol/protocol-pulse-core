# claude-fable-5-2 (96 s) usage={'input_tokens': 7308, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0}, 'output_tokens': 8824, 'output_tokens_details': {'thinking_tokens': 7063}, 'service_tier': 'standard', 'inference_geo': 'global', 'speed': 'standard'} usd=0.41 stop=end_turn

Line numbers are counted from the hunk headers, so treat them as approximate. I could not see the old R4 body, the renderers, `build_edl`'s clip/hook fields or the rest of `moments_vo`, and I ran nothing.

**1. The hard 70 s limit fails open on a missing duration.** `edl_rules.py` ~L189: `content = sum(float(s.get("duration") or 0) for s in [hook] + clips)`.
- A hook or clip with no `duration` (or `None`) counts as 0 s; only the all-zero case is caught (`if content <= 0`, ~L191).
- One missing duration understates runtime by that segment's length, so an over-long final can pass. A negative duration does the same.
- Whether `build_edl` writes `duration` on the hook and every clip is unverified. The old rule reads `edl.get("total_clip_duration", 0)`, so the per-segment field is not established by this diff.
- The check is also on an estimate: VO at 2.5 w/s and `FINAL_TAIL_S = 14.30` taken from one preview (~L156), though "cut leads / tails, pads" plausibly scale with clip count. Nothing in the diff checks the measured final.

**2. Boundary error at 60.0 and 70.0.** ~L197-198: `runtime = round(content + vo_s + FINAL_TAIL_S, 2)` is rounded before `60.0 <= runtime <= 70.0`.
- Estimates up to about 70.005 s and down to about 59.995 s pass a limit described as hard.
- The tests probe only ±0.1 s (`test_runtime_59_9_and_70_1_fail_60_and_70_pass`, hooks 15.6/15.7/25.7/25.8), so nothing pins 70.004 or 59.996.
- The share is compared unrounded (`share > MOMENTS_VO_SHARE`, ~L195), so the two limits are treated differently. A share of 40.04 % is rejected with the message "VO=40.0% … (max 40%)".

**3. The moments rule is selected by one unvalidated string.** ~L210: `if edl.get("package_type") == "moments": return _r4_moments(edl)`.
- There is no cross-check that the EDL actually came from a pinned moments package, for example that `moments_package_sha256` is present. Any EDL from any builder carrying that key gets the 40 % rule.
- `pinned.py` ~L331 copies `package_type=mp.get("type")` straight from the package. No validation of `type` against an allowed set appears in the diff; it may exist in `package.py`, which I cannot confirm.
- The same field now widens the strict gate in `moments_vo` (~L391: `top = last if mp.get("type") == "moments" else last - 1`). A story-first package that declares itself "moments" gets both relaxations.

**4. A blank VO line passes the slot check and costs nothing.** ~L184-190, for a bridge such as `{"text": "", "after_clip": 1}`:
- It passes the slot check, adds 0 words, and is dropped from `vo_s` by `if t.strip()`.
- R4 then reports "every VO line in a slot". By your renderer description it would still get a still frame plus 1.0 s pre-roll, uncounted in share and runtime.
- `pinned.moments_vo` refuses blank text, but `_r4_moments` does not, and it is the only gate for an EDL that did not come through `pinned`.
- Separately, `idx` (~L170) is not checked for uniqueness or type. With duplicate clip indexes, `a in idx` passes and what the renderer does is unverified.

**5. Tests do not fully test what they claim.**
- **No end-to-end test.** No test feeds a `build_edl` EDL to `rule_r4`. `test_pinned.py` asserts only `package_type` and `after_clip`. `TestR4Moments.edl` invents the shape (`hook.duration`, `clips[].duration`), so finding 1's field question is untested.
- **Story test comment is unverifiable.** `test_story_type_and_untyped_edls_keep_the_old_rule` is commented "40 % share: old rule max 25 %", but the helper never sets `total_clip_duration`, which the old rule reads. The old rule likely sees zero clip duration (uncertain, body not shown). The test proves dispatch by message only, not that the old rule judges this EDL as intended.
- **No-slot fixtures are confounded.** `test_a_vo_line_with_no_slot_fails` uses `edl(20.0, [14, 14], 10, …)`, which is 48 + 8 or more + 14.3 = at least 70.3 s. Every case also fails runtime, so `assertFalse(ok)` proves nothing alone; only `assertIn("has no slot")` carries the test. `test_word_caps_are_unchanged` has the same problem (75.7 s).
- **Wrong comment.** `test_a_line_after_each_clip_including_the_last_has_a_slot` says "VO … = 10 s"; it is 5 + 3 + 3 = 11 s.
- **Coarse share boundary.** No share case sits between 40.0 % and 40.5 %, so a limit mutated to 0.404 survives.