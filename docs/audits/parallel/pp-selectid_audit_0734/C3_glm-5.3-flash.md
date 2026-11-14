# glm-5.3-flash (z-ai/glm-5.3-flash) 120 s finish=stop usage in 20539 / out 3933 usd~0.121 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid-0734)

## 1. WHAT THEY CAUGHT THAT I MISSED

Honest accounting against my Cycle 1 output (reconstructed from the consensus):

- **grok's "cleared as by_id" question (no_voice → fixed_caption_gates, package.py:246-248):** I did not explicitly verify that `cleared` is the correct `by_id` for the no-voice path. The consensus resolution is right — `nv_order` picks the added clip *from* `cleared` (line 147: `m = cleared.get(mid)`), and `segs` are cleared moments, so every moment_id in `order` resolves in `cleared`. I missed stating this; it's sound.
- **grok's "where does pk['no_voice']['added_clip'] come from" (test line 328):** I didn't trace the fields→assemble_medley copy. The consensus answer (fields carry `"no_voice": {..., "added_clip": added, ...}` unchanged; assemble_medley copies it) is consistent with the diff at lines 218-220, where `fields` includes the no_voice dict. Missed by me, resolved correctly.
- **glm's (b) — the `a_use(pk3)` → inline dict-comp change (line 56):** I likely treated the extraction as trivially safe. glm correctly flagged it as needs-verification; the consensus refutation (a_use *is* that comprehension; the voiced-path tests + M19 kill coverage) is convincing, but the flag itself was sharper than my treatment.

What I caught that they mostly didn't: the (C) trigger's reliance on `lone_slot(cheap + fid["violations"])` semantics, and the (d) determinism question — which glm and qwen both worked through, and which the consensus correctly downgraded to "latent, not proven."

## 2. WHERE I AGREE / DISAGREE

**glm (d) — nv_order called twice, state may diverge.** *Agree, with a sharpening.* The diff shows the in-loop call at line 274 and no_voice's call at line 176. Between them: the `break` exits the loop, and the consensus says nothing runs in between. But there IS one intervening mutation glm only gestured at: the in-loop call itself. `nv_order` mutates its *own* `plan` dict (`plan["registered_skipped"].append(...)` at line 158), not the closure state — so `dropped`/`doomed`/`held_map`/`cleared` are untouched. I verified from the diff: between line 274's call and the `break` at 277, only `v_novoice = val` runs. After the loop, the code between the loop end and `no_voice()` is not shown in the diff — that's the residual gap. **Verdict: agree it's needs-verification, but the diff-visible window is mutation-free.** The cheaper fix: have the value-loss branch pass `nv_plan` into `no_voice()` instead of letting it recompute. That eliminates the question entirely.

**glm (c) — refused list drops context violations.** *Agree, minor.* Line 245: `refused = [... for v in cheap + fid["violations"]]` — `cx["violations"]` excluded. But the guard at line 240 requires `cx["ok"]` for the fallback to fire, so context violations are empty by construction when the record is written. glm's own "record-keeping only" verdict stands. No action needed.

**glm (b) / grok 1 — extraction equivalence for rewrite_alone.** *Agree with the consensus refutation.* One residual: the old code's `man` (line 72 of old) — the new helper rebuilds it at line 49 from `pk3["segments"]` and `ctx.now`. If the old `man` was built from `pk` (pre-rewrite) rather than `pk3`, the channels list could differ when the rewrite changes nothing (it doesn't — same segments). Equivalent. Also note the helper's `why` parameter: rewrite_alone passes `"the fixed caption (ruling 65 b)"` (line 80), matching the old `build_pk(line, "the fixed caption (ruling 65 b)")` — the vo_kind prefix `f"{pk.get('vo_kind')}; {why}"` (line 45) vs old `build_pk`'s second arg. If `build_pk` did NOT prepend vo_kind, the note string changed. **Cannot verify from the diff — needs-verification, cosmetic (note text only, not gating).**

**grok 2 — cleared vs by_id interchangeability.** *Agree with consensus refutation* (see §1).

**grok 3 — added_clip provenance.** *Agree with consensus refutation.*

**qwen's (d) analysis — the new medley call.** *Agree, and this is the strongest point in their output.* `nv_order`'s candidate check (lines 152-155) validates durations/limits but NOT the joins; `no_voice` then runs `medley(router, order, ...)` (line 207) which can fail → `return None` (line 209-210). The in-loop decision "a no-voice line-up exists → skip the rewrite" is therefore *optimistic*: the rewrite is forfeited even if the added-clip line-up fails its medley. Is that (A)-compliant? (A) says the no-voice shape is ONE shape; the builder's reading, stated on STATE, says "a no-voice line-up that then fails a gate ends the line-up, as on ruling 3's path" — and ruling 3's path behaves exactly this way. So it's consistent, and test `test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite` (lines 339-349) pins it. *Agree with the implemented semantics; no defect.*

**qwen's truncated output.** Its condition 1

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> (C) — the second guard can pass on a *stale* `cheap` when the first guard passed on a fresh one, and vice versa.** package.py:241-256. Trace: the first guard (line 241) fires when `cheap or not fid["ok"] or not cx["ok"]`. Inside, the lone-slot check (line 242) uses the *pre-fallback* `cheap`/`fid`. Then `fixed_caption_gates` returns a *new* `cheap3`/`fid3`/`cx3` (line 248), and the second guard (line 253) checks those. But note: the second guard's failure message (line 254) says "the fixed caption did not pass its gates" — yet `cheap3`/`fid3`/`cx3` include violations on ALL slots (merge_fid keeps the other lines' verdicts), not just the caption's. So a *title* violation that was already present pre-fallback (but the title passed its own verdict — wait, no: if the title's verdict failed, `fid["ok"]` is False, and lone_slot(cheap + fid["violations"]) == "caption" requires ALL violations on the caption slot, so a title verdict failure can't reach the fallback). Let me re-trace: `fid["ok"]` False with only caption violations → lone_slot returns "caption" → fallback fires. Then `fid3 = merge_fid(fid, "caption", one)` where `one["verdict"]["ok"]` is hardcoded True (line 52). So fid3["ok"] = fid["ok"] AND one["ok"] = False AND True = **False**. The second guard (line 253) then fires: "the fixed caption did not pass its gates" — but the *caption* passed (one["ok"] is True); it's the *stale title*... no wait, if fid["ok"] was False only on caption, and one["ok"] is True, then fid3["ok"] = False AND True = False. **That's the bug: merge_fid's `ok` is the AND of the old fid["ok"] (False, from the caption's own verdict) and the new one (True), so fid3["ok"] stays False even though the fixed caption passed, and the second guard kills the line-up.** Concrete scenario: caption fails its model verdict (VERDICT_NO), everything else passes. Guard 1 fires (not fid["ok"]), lone_slot → "caption", fallback runs, the fixed line's verdict `one` is ok:True, but `merge_fid(fid, "caption", one)` — if merge_fid's `ok` = fid["ok"] and one["ok"], fid3["ok"] = False. Second guard: `not fid3["ok"]` → return None, "the fixed caption did not pass its gates". **Unless merge_fid recomputes ok from the merged violations rather than ANDing** — which I cannot verify from the diff (merge_fid's body is not shown; only its signature and the `backend` line at 34). This is exactly the kind of thing the test `test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption` (line 492) should catch — and it asserts `pk["caption_fallback"]` and all gates PASS, so if the test passes, merge_fid must NOT simply AND. So: either the test passes and merge_fid recomputes (no bug), or the test fails and this is a real P1. **Needs-verification: merge_fid's `ok` computation.** Flagging as the one thing the diff cannot settle.

**<medium> (b) — `fixed_caption_gates`'s `man` uses `pk3["segments"]`' channels, but the old rewrite_alone's `man` provenance is unverifiable.** Covered in §2; cosmetic.

**<low/medium> (e) — `no_voice_fits` removal: grep-verified no remaining callers in the diff, but the diff doesn't show the whole module.** If any other module imported it (tests, other pipelines), it's now an ImportError. The consensus says "no other callers found in grep" (grok, §2) — I'll trust that but note the diff alone can't prove it.

**<medium> (d) — the residual gap: code between the loop and no_voice() is not in the diff.** Lines 284-308 show the loop's value-loss branch (break at 293) and the no_voice call at 306-308, but lines 309-3194 of package.py are elided. If anything between the `break` (line 293) and the `no_voice(...)` call (line 306) mutates `dropped`/`doomed`/`held_map`/`cleared`, the passed `v_plan` (line 308, `plan=v_plan`) is now *the* decision — which is exactly why the implemented fix (passing the plan) is right. With `plan=v_plan`, the (d) question is *closed by construction* for the value-loss path; only ruling 3's path (plan=None) recomputes, and there the state is whatever it is at call time, which is correct by definition. **So the implemented fix resolves (d) fully — better than the consensus's "latent, not proven" verdict.**glm/grok's residual concern is now moot for the ruling-91 path; for ruling 3's path there was never a double-call to diverge.

**<medium> (C) — `note["caption_fallback"]["refused"]` drops the rule *details* and slot info.** Line 247: `refused = [{k: v.get(k) for k in ("rule", "detail")} for v in cheap + fid["violations"]]`. Cheap violations carry `rule`/`detail`; fid violations carry `rule`/`detail` (per the test at line 504: `{"rule": "VERDICT_NO", ...}` — actually the test's `failing()` helper builds `{"rule": ..., "detail": ...}`-shaped dicts, and the assertion at 504 reads `["refused"][0]["rule"] == "VERDICT_NO"`, so fid violations do carry `rule`). But there's no `slot` key, so a reader of the sealed record cannot tell whether the refused violation was on the caption or elsewhere — though by construction it's all-caption. Cosmetic; the record is still truthful.

**<medium> (C) — the fixed caption's `one["verdict"]["ok"]` is hardcoded True, so the fixed line's *fidelity verdict* is never re-checked against the model.** That's by design (ruling 65 b: "no model verdict on it"), and the deterministic layer + cheap + context still run (lines 48-56). Consistent with the ruling. But note: `VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels)` (line 51) — if the fixed line fails the *deterministic* layer, `one["deterministic"]` will show it, but `one["verdict"]["ok"]` stays True and `fid3`'s ok depends on merge_fid. Whether a deterministic failure on the fixed line kills the line-up depends again on merge_fid's ok computation — same needs-verification as above.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| (A) one-shape / added-clip parity | 0 findings | 0 | Tests at 345-420 pin both paths; the optimistic-rewrite-forfeit semantics are consistent with the builder's stated reading. |
| (b) fixed_caption_gates extraction | 1 needs-verify (a_use) | 1 cosmetic (man/why provenance) | Consensus refutation accepted; only note-string provenance remains, not gating. |
| (C) fixed-caption trigger + second guard | 1 (lone_slot semantics) | 1 needs-verify (merge_fid ok) | The second guard's correctness hinges on merge_fid's `ok` computation, which the diff doesn't show. |
| (d) nv_order determinism | 1 latent | 0 (closed by construction) | The implemented `plan=v_plan` pass-through eliminates the divergence question for the ruling-91 path; ruling 3's path never double-called. |
| (e) removals | 0 | 0.5 (import risk, unverifiable from diff) | no_voice_fits: no callers visible in diff; consensus grep says clean. |
| Test coverage | 0 | 0 | 15 mutations killed; the new tests pin (A) and (C) outcomes, including the clip-gate-fails-first ordering (line 392). |

## 5. FINAL PRIORITY LIST

**P1 HIGH** — pipeline/package.py:248+253 (second guard) + :54 (merge_fid call): **verify merge_fid's `ok` computation.** If `merge_fid(fid, "caption", one)["ok"]` = `fid["ok"] and one["ok"]`, then the (C) verdict-failure path (test at line 492) produces fid3["ok"]=False even after the fixed caption passes, and the second guard (line 253) kills the line-up — making (C) dead-on-arrival for the verdict-failure case, contradicted by the test's assertions (so either the test fails, or merge_fid recomputes). Concrete check: run `test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption`; if it passes, merge_fid recomputes and this closes; if it fails, fix merge_fid or the second guard. (The consensus did not flag this; it's my main new finding.)

**P2 MEDIUM** — pipeline/package.py:45-49: confirm the extracted helper's `man`/`why`/vo_kind note string matches the old `build_pk(line, "the fixed caption (ruling 65 b)")` output byte-for-byte (cosmetic, record-only; the consensus's "equivalent" verdict assumed build_pk prepends vo_kind — unverifiable from the diff).

**P2 MEDIUM** — module-level: confirm `no_voice_fits` has no importers outside the diff (tests, other modules). One grep; the consensus says clean.

**P3** — package.py:247: `refused` records lack a `slot` key (record-keeping only; by construction all-caption).

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Verify merge_fid's `ok` computation (one line of code, outside the diff) — it single-handedly decides whether (C)'s verdict-failure path ships the fixed caption or silently kills the line-up, and it's the only gating question the diff cannot settle.

## 7. PRODUCTION READY?

**Yes with conditions:**
(a) Run/confirm `test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption` passes — that closes the merge_fid/second-guard question (P1). If it fails, fix merge_fid's `ok` (recompute from merged violations, don't AND) before shipping.
(b) One grep confirming `no_voice_fits` has no remaining importers (P2).
(c) Optional, cosmetic: confirm the extracted helper's note string matches the old build_pk output (P2).

Everything else — (A) parity, (d) determinism (closed by the `plan=v_plan` pass-through), the extraction's gating equivalence, and the test coverage — I now consider settled. The 15 killed mutations and the new (A)/(C) tests cover the concrete scenarios the consensus worried about, including the clip-gate-fails-before-verdict ordering (test at line 392) that grok's P1 hypothesized and the consensus's added test refuted.