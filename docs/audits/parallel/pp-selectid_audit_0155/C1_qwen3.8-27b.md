# qwen3.8-27b (qwen/qwen3.8-27b) 109 s finish=stop usage in 14582 / out 3641 usd~0.098 (upper-bound price)

# Audit: pp-selectid-0155 (G17a at the PIN stage)

## Findings

### P1 — `hook_onset.measure` can return `pass: True` for a hook that has *no* cut before it (file head)
**File:** `pipeline/hook_onset.py:65-79`

The code path:
```python
cin = plan.get("in") or {}
if not cin.get("cuttable"):
    return {"pass": False, ...}
cut_in = float(cin["cut"])
...
pad = float(cin.get("lead_in_pad_s") or 0.0)
lead = int(round(ht["lead_ms"] + pad * 1000))
ok = lead >= need
```

If the hook is the **first word in the source file** (a file-head hook), `edge_plan` will report the "in" cut as the file head (t=0) and grant a `lead_in_pad_s` (the room-tone pad). The `_Slice` will be `[0, cut_out]`. `head_tail` on that slice will measure `lead_ms` as the quiet before the first onset *within the slice* — which is the pad region. So `lead = pad_ms + head_tail_lead_ms`.

**The problem:** The pad is *synthetic* room tone inserted by the renderer. The law says "a source that starts speaking at its file head, and the hook, need >= 80 ms of genuine sub-speech audio before the first onset **or a declared room-tone lead-in pad**." The code adds the pad to the measured lead, which is correct per the law. However, the `head_tail` measurement on the slice `[0, cut_out]` will see the pad as part of the audio. If the pad is, say, 100 ms of -55 dBFS room tone, `head_tail` will report `lead_ms ≈ 100`, and `pad` will also be 100 ms, giving `lead = 200 ms`. **This double-counts the pad.** The pad is already in the slice; adding it again inflates the lead.

**Failure scenario:** A file-head hook with a 50 ms pad and 30 ms of genuine quiet before onset. True genuine lead = 30 ms (FAIL). Code computes `lead = 30 + 50 = 80 ms` (PASS). The hook opens a medley with only 30 ms of genuine quiet, violating D1.

**Mitigation check:** I cannot verify from the diff whether `edge_plan`'s `lead_in_pad_s` is *included* in the slice or *added on top*. The `_Slice` is `[cut_in, cut_out]` where `cut_in = cin["cut"]`. If `cin["cut"]` is 0 for a file head, the slice starts at 0 and does *not* include the pad (the pad is added by the renderer *before* the cut). In that case, `head_tail` on `[0, cut_out]` measures only the source audio, and adding `pad` is correct. **I am uncertain** which interpretation is correct without seeing `edge_plan`'s contract. Flagging as P1 pending verification.

---

### P1 — `lineup_for` with `need_onset=True` can silently drop all hooks, producing a medley that opens with a *clip* instead of a hook
**File:** `pipeline/package.py:106-107` (the `hooks` filter) and `:164-167` (the call sites)

```python
hooks = [m for m in ms if (m.get("eligibility") or {}).get("hook", {}).get("ok") and
         (not need_onset or (m.get("hook_onset") or {}).get("pass") is True)]
```

If *no* moment in the angle has `hook_onset.pass == True`, `hooks` is empty. The code then iterates `for h in hooks:` (line 109), which does nothing. The function returns `None` (implied by the "None if impossible" docstring). This is correct: no line-up is produced.

**However**, the test at `test_medley.py:347-359` confirms this: `no_hook={"h","x","y","z"}` → `out["package"] is None`. Good.

**But:** What if the angle has *some* hooks that pass and some that don't? The proposer's hook (`angle["hook"]`) is sorted first (line 108: `m["moment_id"] != angle["hook"]` as primary key). If the proposer's hook fails G17a but another moment passes, the proposer's hook is skipped and the next hook is used. This is the intended behavior ("the proposer's hook gives way to the angle's next one that did"). **No defect here.**

---

### P2 — `hook_onset_for` caches by `moment_id` but the cache is shared across all angles
**File:** `pipeline/package.py:115-126`

```python
def hook_onset_for(m, sources, work_dir, cache):
    if m["moment_id"] not in cache:
        ...
        cache[m["moment_id"]] = HO.measure(...)
    return cache[m["moment_id"]]
```

The cache is a plain dict keyed by `moment_id`. Since a moment belongs to exactly one video and has fixed `start`/`end`, the measurement is deterministic and caching is safe. **No defect.**

---

### P2 — The `hook_onset` gate row is only added to `inventory` when `hook is not None`
**File:** `pipeline/package.py:201-204`

```python
**({"hook_onset": dict(row(...), ...)} if hook is not None else {}),
```

If `hook` is `None`, the row is absent. `package_pin.MEDLEY_GATES` includes `"hook_onset"`, so `to_pin` will refuse the pin (missing required row). This is correct fail-closed behavior.

**However**, in `build()`, the `hook` argument is:
```python
hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset")
```

If `pk["segments"][0]["moment_id"]` is not in `cleared` (e.g., the moment was dropped after the hook_onset measurement), `cleared.get(...)` returns `None`, `{}.get("hook_onset")` returns `None`, and the row is absent → pin refused. **Correct fail-closed.**

---

### P2 — No-voice path: is `hook_onset` still required?
**File:** `pipeline/package.py:1308-1309` (the no-voice `inventory` call)

```python
pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab,
                        {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
                        ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
                        style=HS.lint_lines(pk["lines"]),
                        hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
```

Yes, the no-voice path also passes `hook=...`. And `MEDLEY_GATES` includes `"hook_onset"` unconditionally. The test at `test_medley.py:364-373` confirms: the no-voice test passes `hook={"pass": True, ...}` and the pin succeeds. **Correct.**

---

### P2 — Test coverage: does `test_hook_onset.py` actually fail on the named defect?
**File:** `tests/package/test_hook_onset.py:273-279`

```python
def test_breath_then_digital_zeros_before_the_first_word_fails_g17a(self):
    env = Env(SPEECH + [(1.41, 1.58, -27.0), (1.65, 1.78, -200.0), (1.78, 1.81, -60.0), (1.81, 3.20, -20.0)])
    r = self.measure(env)
    self.assertEqual((r["pass"], r["measured"]), (False, True), r)
    self.assertLess(r["lead_ms"], 80)
```

The synthetic envelope has:
- 0.20–1.36: speech (-20 dB)
- 1.41–1.58: breath (-27 dB)
- 1.65–1.78: digital zeros (-200 dB)
- 1.78–1.81: quiet (-60 dB)
- 1.81–3.20: speech (-20 dB)

The hook words are at 1.75–3.20. The cut is planned before word 3 ("When" at 1.75). The `edge_plan` will find the gap between "markets." (ends 1.35) and "When" (starts 1.75). The cut will be somewhere in [1.35, 1.75]. The `_Slice` will be `[cut_in, cut_out]`. `head_tail` on that slice will measure the lead before the first onset.

The digital zeros at 1.65–1.78 are below `DIGITAL_FLOOR_DBFS` (presumably around -100 dB or lower; -200 dB is well below). `quiet_runs(genuine=True)` drops these frames. So the "genuine" quiet before the first onset is only 1.78–1.81 (30 ms) plus whatever is between the cut and 1.41. If the cut is at, say, 1.50, the genuine quiet is 1.50–1.41 (none, that's backwards) ... actually, the cut is *before* the hook, so the slice starts at the cut. The lead is measured from the start of the slice to the first onset.

**I cannot verify the exact `lead_ms` value without running the code**, but the test asserts `lead_ms < 80` and `pass == False`. Given the synthetic data, this should hold. **Likely correct, but I cannot confirm the exact numeric result from the diff alone.**

---

### P2 — `SPEECH` in the test includes the hook's own speech
**File:** `tests/package/test_hook_onset.py:260`

```python
SPEECH = [(0.20, 1.36, -20.0), (3.60, 5.00, -20.0)]
```

The hook words are at 1.75–3.20, but `SPEECH` has no span covering 1.75–3.20. The hook's speech is added separately in each test (e.g., `(1.81, 3.20, -20.0)`). This is correct: the hook's speech is not part of the "bed" but is added per-test. **No defect.**

---

### P2 — `lineup_for` signature change is backward-compatible
**File:** `pipeline/package.py:90`

```python
def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False):
```

`need_onset` defaults to `False`, so existing callers (if any outside `build()`) are unaffected. The only callers in the diff are at lines 164 and 167, both with `need_onset=True`. **No defect.**

---

## Answers to the specific questions

**(a) Can a hook with < 80 ms of genuine lead still reach a pin?**
- The slice vs. prepared clip: the slice is from the *source* audio, not the prepared clip. The render's `gate_g17_prepared` measures the prepared clip. The pin-stage check measures the source. These can differ by up to one 10 ms frame (noted in the docstring). The pin check is *stricter* (no fade-in applied). So if the pin check passes, the render check should also pass (or be very close). **However**, the P1 finding about pad double-counting could allow a false pass.
- The pad: see P1 above.
- Zeros: `head_tail` uses `quiet_runs(genuine=True)` which drops digital zeros. **Correct.**
- The cut's choice: `edge_plan` chooses the cut. If the cut is too late (closer to the first onset), the lead is shorter. The code uses the planned cut, not a re-optimized one. **Correct per SNAP LIMIT.**

**(b) Can an unmeasured hook pass or open a line-up?**
- `hook_onset_for` returns `{"pass": False, "measured": False, ...}` on any exception.
- `lineup_for` filters on `(m.get("hook_onset") or {}).get("pass") is True`. An unmeasured hook has `pass: False`, so it is excluded. **No, an unmeasured hook cannot open a line-up.**
- The `inventory` row: `measured=hook.get("measured") is True`. If not measured, the row is `NOT RUN`, which is not `PASS`, so the pin is refused. **Correct fail-closed.**

**(c) Does anything change for non-hook clips, or for the full-video and window paths?**
- Non-hook clips: `hook_onset` is only measured for moments that *could* be hooks (all cleared moments are measured, but only the first segment's `hook_onset` is used in the gate). Non-hook clips are unaffected. **No change.**
- Full-video and window paths: the `audio` parameter in `measure` allows reusing a pre-fetched window. If `audio=None`, it fetches the L-v 2 window. This is the same window used by the second recogniser. **No change to the window path.**

**(d) Is the `hook_onset` row really required and sealed for every medley pin, the no-voice path included?**
- `MEDLEY_GATES` includes `"hook_onset"`. `to_pin` checks all `MEDLEY_GATES` for medley packages. The no-voice path also produces a medley package (shape="medley"). **Yes, it is required for every medley pin, including no-voice.**

**(e) Do the tests fail on the defect each one names?**
- `test_breath_then_digital_zeros...`: should fail (assert `pass == False`). **Likely yes, but I cannot confirm the exact numeric result.**
- `test_room_tone_before_the_first_word_passes`: should pass (assert `pass == True`). **Likely yes.**
- `test_no_audio_or_words_outside_the_window...`: should not be measured. **Yes, the code returns `measured: False` on exception or out-of-window words.**
- `test_a_hook_without_80_ms...`: the rig stubs `hook_onset_for` to return `pass: False` for `no_hook` moments. The test asserts the proposer's hook gives way and that no line-up is produced when all hooks fail. **Yes, the test logic is correct.**

---

## Verdict

**SHIP: yes with conditions**

**Conditions:**
1. **Resolve the P1 pad double-counting question.** Verify whether `edge_plan`'s `lead_in_pad_s` is included in the slice or added on top. If it is included, the code double-counts and a file-head hook with a short pad could falsely pass. Add a test for a file-head hook with a pad.
2. **Add a test for the file-head hook case** (a hook that is the first word in the source file) to confirm the pad handling is correct.
3. **Confirm the exact `lead_ms` value** in `test_breath_then_digital_zeros...` by running the test, to ensure the synthetic envelope produces the expected < 80 ms result.