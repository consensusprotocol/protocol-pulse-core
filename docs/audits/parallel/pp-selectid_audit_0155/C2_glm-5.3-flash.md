# glm-5.3-flash (z-ai/glm-5.3-flash) 122 s finish=stop usage in 18941 / out 3544 usd~0.110 (upper-bound price)

# pp-selectid-0155 — CYCLE 2 FINAL REVIEW

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **glm P0-1 / P1-1 (slice vs. render decode divergence, 10 ms quantization + 20 ms fade):** I flagged the structural divergence but did not note that the diff *already* answers it — the `MARGIN_MS` requirement (hook_onset.py:33, 48, 82) means a pass here requires 90 ms, so the 80–89 ms window cannot flip. The consensus table confirms this was implemented and tested (`test_a_lead_within_one_frame_of_80_ms_does_not_pass`, lines 417–423). I under-credited the fix.
- **qwen's pad double-count question:** I did not resolve it in Cycle 1. The consensus REFUTES it with a mechanism I can now verify from the diff: `_Slice(sa, cut_in, cut_out)` slices the *source* envelope only (hook_onset.py:41, 77), and the pad is added by the render *before* the source audio, so `pad * 1000` at line 81 counts it exactly once. `test_a_file_head_hook_counts_the_pad_the_render_adds_once` (lines 425–435) asserts `r["pad_s"] == SL.LEAD_PAD_S` and that the source alone is < 80 ms — the test genuinely discriminates the double-count case.
- **glm P1-2 (angle["hook"] naming a moment that doesn't open):** I missed this entirely. The consensus refutation is verifiable: `lineup_for` sorts by `m["moment_id"] != angle["hook"]` (package.py:224) — a *preference*, not a requirement — and the package's hook is always `segments[0]`, which comes from the line-up. The new test (lines 573–585) proves the proposer's hook gives way.

What I caught that they didn't: my Cycle 1 emphasis on the *direction* of the stricter-at-pin check (P1-1) — that the render's G17_onset_tail can still hold a pinned package for the fade/quantization residual. The margin reduces that to one frame, but does not eliminate it; the docstring (hook_onset.py:22–25) concedes this. That remains true and nobody else stated it.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| glm P0-1 (slice ≠ render decode) | **Agree, now downgraded to resolved** | The 90 ms margin (HEAD_LEAD_MIN_S + one HOP_S frame) closes the flip window; the 20 ms fade omission is strictly stricter. Tested. |
| glm P0-2 (cache freezes transient failure) | **Agree — correctly dispositioned KEPT** | Fail-closed per L-m; consensus states the L-v 2 window is disk-cached, making the read deterministic. I cannot verify the disk cache from the diff — stated uncertainty, not a defect. |
| qwen pad double-count | **Agree with the refutation** | The slice is source-only; the pad enters the lead exactly once. Now tested. |
| qwen "medley opens with a clip" | **Agree with the refutation** | `hooks` empty → the `for h in hooks` loop never runs → `None` → no line-up, no paid call. Tested (lines 581–585: `rig.medley_calls == []`). |
| glm P1-3 (CUTTABLE vs. edge_plan "not cuttable") | **Agree — KEPT, correctly** | Two genuinely different checks; a cuttable-but-unopenable moment stays usable as a non-hook clip. This is the intended semantics, not a defect. |
| glm P1-4 (no-voice added clip) | **Agree — KEPT** | The hook is always `segments[0]` from `cleared`; the added clip is never the hook. |

No disagreement rises to the level of a finding.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — `hook_onset_for`'s ThreadPoolExecutor result-assignment order.** package.py:253–256: `futs = {mid: pre.submit(hook_onset_for, m, sources, work_dir, hk) ...}` then `cleared[mid]["hook_onset"] = f.result()`. The cache `hk` is a plain dict mutated from 4 workers. CPython's GIL makes dict item assignment atomic, and each worker writes only its own `mid` key, so this is safe — but it is worth noting that `hook_onset_for`'s check-then-set (`if m["moment_id"] not in cache`) is only race-free because each `mid` is submitted exactly once. If a future change submits a duplicate `mid`, two workers could both compute and both write. Not a defect today; a fragility. *Uncertain whether this rises to the consensus's attention; nobody flagged it.*

**N2 (P2) — the `prescreen` CONTEXT_UNAVAILABLE path skips the moment but the batch still goes out.** package.py:182–190: when `text is None`, the moment gets `fails[mid] = ["CONTEXT_UNAVAILABLE: ..."]` and `continue` — but the *other* moments in the chunk still proceed to `CI.step_a`. This is the fix for the "0 cleared in 0 s" defect, and `test_a_moment_without_context_never_poisons_its_step_a_batch` (test_ledger_build.py:492–519) proves it: `sent == [[mid_a]]` (the batch went out without the poisoned moment) and `fails[mid_w][0].startswith("CONTEXT_UNAVAILABLE")`. Verified correct. However: the `if not contexts: continue` at line 189–190 means a *fully* context-less chunk silently skips its step-A call — correct (nothing to send), but those moments' `fails` entries are the only record. Fail-closed, consistent with L-m. No defect.

**N3 (P2) — `caption_source`'s ambiguity check now compares *tokens*, not record count.** ledger_build.py:150–152: `len({json.dumps(toks, sort_keys=True) for _, _, toks in found}) > 1`. Two records with identical tokens but different metadata (e.g. different `transcript_method` — `yt_auto` vs. `yt_manual` copies of the same words) now count as ONE record, and `found[0]` is taken — whose label wins depends on iteration order: `("main", store)` then `("ledger", ledger_store)`, so **main's copy wins**. The test at line 480 asserts exactly this (`"main/transcript.yt_auto.json"`). But: if the two stores' copies have the same tokens yet different *non-token* fields that `E.Source` consumes (e.g. duration, channel registration), the choice is order-dependent and silent. *Uncertain whether `Source` consumes anything beyond tokens+metadata from the record; the diff shows `E.Source(vid, row.get("channel_id"), ...)` — the channel comes from the row, not the record, so exposure looks minimal. Flagging as P2, uncertain.*

**N4 (P2) — the `hook_onset` inventory row's `measured` semantics.** package.py:317–320: `row(hook.get("pass") is True, "hook_onset.measure (...)", measured=hook.get("measured") is True)`. If `hook` is a dict lacking `measured` (e.g. the rig's stub at test_medley.py:563–565 always supplies it, but a future caller might not), `measured=hook.get("measured") is True` → False → the row reads "NOT RUN" → the pin is refused. Fail-closed, correct. But note: `hook.get("pass") is True` with `measured=False` would still produce a "NOT RUN" row *even if* someone later sets `pass: True` on an unmeasured record — the row's status derives from `pass` while `measured` independently gates NOT RUN. The `row` lambda (line 310–312) resolves this: `"NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL")` — so `measured` wins. Correct. No defect, but the coupling is subtle and undocumented in the row's `why`.

**N5 (P1) — `lineup_for`'s `need_onset` filter is applied in BOTH the primary and the repeat_ok fallback, but the repeat_ok fallback's *rep* computation (package.py:285–286) counts channels from the returned `segs` — which now excludes failed-onset hooks.** If the fallback's repeat-clip comes from a channel whose *other* moment failed G17a, the rep computation still counts it correctly (it counts from `segs`, not from the angle). Verified: no defect. However, the *primary* path's `dropped | doomed` union (line 280) is unchanged, and `doomed` moments may include ones that *passed* G17a — meaning a passed-onset moment can still be dropped for other reasons, and the `hook_onset` inventory row for the *pinned* package's hook (line 271: `cleared.get(pk["segments"][0]["moment_id"])`) reads from `cleared`, which retains all cleared moments regardless of `doomed`. So the row reflects the *pinned* hook's measurement, which is what the gate requires. Correct. No defect — but note the asymmetry: the row is looked up from `cleared`, not from the line-up, so if `segments[0]`'s moment were somehow not in `cleared` (qwen's Cycle 1 P2, truncated), the row is absent → pin refused → fail-closed. Verified consistent.

**N6 (P2) — `MARGIN_MS` derives from `SL.HOP_S` at import time.** hook_onset.py:33: `MARGIN_MS = int(round(SL.HOP_S * 1000))`. If `SL.HOP_S` is not exactly 0.010 (e.g. 0.0104), `int(round(10.4))` = 10 — the margin silently loses the fractional frame. *Uncertain what `SL.HOP_S` actually is; the docstring says 10 ms. If it is exactly 0.010, this is moot. Flagging only because the constant is derived, not asserted, and no test pins `MARGIN_MS == 10`.*

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| hook_onset.measure correctness | 8/10 | 9/10 | The 90 ms margin + pad-once test resolve my two open questions (slice divergence, pad double-count). Remaining: N6 (MARGIN_MS derivation) and the unresolvable-from-diff question of whether the render's decode can differ by *more* than one frame. |
| lineup_for / need_onset integration | 8/10 | 9/10 | The give-way semantics are now tested; the "no line-up → no paid call" path is proven.glm P1-2's refutation holds. |
| inventory / MEDLEY_GATES sealing | 9/10 | 9/10 | The row is required, exactly-PASS, and the no-voice path supplies it (test_medley.py:593–596). N4's coupling is subtle but correct. |
| ledger_build caption_source (C2 scope) | 7/10 | 8/10 | The two-store search + token-identity ambiguity check is tested (lines 458–487). N3's order-dependence is the residual. |
| prescreen batch poisoning fix | 8/10 | 9/10 | The CONTEXT_UNAVAILABLE path is tested end-to-end (lines 492–519). |
| Test coverage | 8/10 | 9/10 | Every named defect has a discriminating test. N6 (MARGIN_MS) is the only untested constant. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. All Cycle 1 P0s are resolved or correctly dispositioned.

**P1 HIGH**
- **P1-1 (N6):** hook_onset.py:33 — `MARGIN_MS` is derived from `SL.HOP_S` at import; no test pins it to 10. If `HOP_S` ever changes, the margin (the entire defense against the slice-vs-render divergence, the diff's central claim) silently shifts. *Fix: assert `MARGIN_MS == 10` in test_hook_onset, or derive the margin's *rationale* (one frame) into the why-string (it already is, line 84–85 — good).*
- **P1-2 (carried,glm P0-2):** package.py:115–126 / 252–256 — the `hk` cache freezes a transient `audio_window` failure for the whole build. Fail-closed (L-m compliant); the consensus says the L-v 2 window is disk-cached, which I cannot verify from the diff. *Condition: confirm the disk cache, or accept the silent disqualification.*

**P2 MEDIUM**
- **P2-1 (N3):** ledger_build.py:150–153 — when both stores hold the same *tokens* but different records, `found[0]` wins by iteration order (main first). If `E.Source` consumes any non-token field from the record, the choice is silent and order-dependent. *Uncertain; verify what `Source` reads.*
- **P2-2 (N1):** package.py:253–256 — the `hk` cache's check-then-set is race-free only because each `mid` is submitted once. Fragile under future duplication.
- **P2-3 (N4):** package.py:310–312, 317–320 — the `row` lambda's `measured`-wins-over-`pass` coupling is correct but undocumented; a future caller setting `pass: True, measured: False` gets NOT RUN, which is right but surprising.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Pin `MARGIN_MS == 10` (and `SL.HOP_S == 0.010`) with an assertion in test_hook_onset.py — the 90 ms margin is the diff's entire defense against the slice-vs-render divergence, and it currently rests on an untested derived constant.

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions:
1. **Confirm the L-v 2 window's disk cache** (glm P0-2 / my P1-2): if `TT.audio_window` is deterministic and disk-cached, the frozen-cache behavior is acceptable; if not, a transient failure silently disqualifies a moment for the whole build with only a prescreen log line. State which in the audit record.
2. **Pin the margin:** add `self.assertEqual(HO.MARGIN_MS, 10)` (and implicitly `SL.HOP_S == 0.010`) to test_hook_onset.py, so the 90 ms defense cannot silently drift.
3. **Verify `E.Source`'s consumption of the caption record** (N3): if it reads only tokens + row-supplied metadata, the order-dependence in `caption_source`'s same-tokens path is moot; if it reads more, record the tie-break (main wins) in the docstring.

Everything else — the 90 ms margin, the pad-once semantics, the give-way line-up, the sealed `hook_onset` row, the batch-poisoning fix — is implemented, tested, and consistent with L-m/L-j. The render's G17_onset_tail can still hold a pinned package by at most the 20 ms fade residual, which the margin does not cover; that is the documented, accepted residual, not a defect.

**SHIP: yes with conditions**