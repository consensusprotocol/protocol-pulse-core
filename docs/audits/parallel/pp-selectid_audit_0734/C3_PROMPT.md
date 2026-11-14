# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0734
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 125 s finish=stop usage in 18060 / out 3343 usd~0.104 (upper-bound price)

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

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 17913 / out 1404 usd~0.125 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0734**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   GLM's (d) on the double `nv_order()` call (pipeline/package.py:274 vs :176) and the closure variables (`cleared`, `doomed`, `held_map`) that *could* mutate between the in-loop decision and the later `no_voice()` call. I had not explicitly traced that the `break` exits the takeaway loop but that later bookkeeping (`t_refused`, `v_lost`, `last_fid` updates) and the outer `if v_novoice` path sit between the two sites. Grok's extraction note on `a_use(pk3)` → dict-comp also escaped my first pass; the diff alone does not define `a_use`. Qwen's doomed-clip test idea (now implemented) was absent from my Cycle 1.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - GLM (d): partially agree — the latent recomputation risk exists in the diff (closure state), but the added `test_a_doomed_clip_is_never_the_added_clip` plus mutation M21 killing all 16 variants makes it non-breaking. The in-loop `break` + identical arguments guarantee same return for all concrete test inputs.  
   - GLM (b)/Grok extraction: agree — `fixed_caption_gates` reconstructs exactly the `man`, `pk3["medley"]`, `a_by` dict, and `merge_fid` that the old `rewrite_alone` path used. Existing ruling-65 tests + M19 (drop fallback) kill the voiced path; behaviour preserved.  
   - GLM (c)/ (e): fully agree — lone-slot guard, `fixed_caption_gates` re-check, removed `no_voice_fits` (no other callers found in grep), and the replaced count tests are sufficient.  
   - Qwen "critical" on stale `dropped`/`doomed`: disagree — its own text correctly concludes the calls are deterministic with identical inputs; the test added in C2 kills the mutation.  
   - Grok's `added_clip` key and `by_id` vs `cleared`: agree these were un-obvious from diff alone; the C2 tests and `assemble_medley` copy now make the provenance clear.

3. **NEW FINDINGS FROM THIS REVIEW**  
   <medium> **pipeline/package.py:240 (the combined cheap/fid/cx guard after first cheap check)**: concrete input — a no-voice line-up whose *first* `cheap_checks` returns a single RUNTIME violation on the caption slot *and* a clip-exclusion failure (so `paid_gates` never runs). The early `if cheap and lone_slot(cheap) != "caption"` is bypassed (lone caption), but the later `if cheap or not fid["ok"] or not cx["ok"]` sees `cheap` truthy, `cx` never bound, and `lone_slot(cheap + fid["violations"])` cannot be evaluated. Current code would NameError or treat unbound `cx` as falsy, skipping the fixed-caption path that (C) requires. (The test suite never hits a clip-gate failure *after* a lone-caption cheap failure.)  
   <medium> **tests/package/test_medley.py:399 (contexts_pass stub)**: the lambda hard-codes `"measured": True` but the real `CI.check_contexts` can return measured=False on replay. The fixed-caption test that expects a context failure (test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends) overrides the stub but leaves the ruling-3 path test using the measured=True version, leaving one edge unexercised.

4. **REVISED SCORES**  
   | Subsystem                  | Cycle 1     | Cycle 2          | Why changed |
   |----------------------------|-------------|------------------|-------------|
   | nv_order / ruling-91 path  | 2 mediums   | 1 medium         | GLM (d) + new guard bug raised visibility; doomed test lowered severity |
   | fixed_caption_gates extraction | 1 medium | 2 mediums        | New NameError scenario on cheap+clip-gate combo; extraction itself still clean |
   | Test coverage & mutations  | 0           | 0                | Added tests kill all listed mutations; no change |
   | Overall risk               | medium      | medium           | One new latent crash path, but narrow |

5. **FINAL PRIORITY LIST**  
   **P1 HIGH** — pipeline/package.py:240: add `cx is not None and cx["ok"]` (or restructure to always bind `fid, cx` before the guard) so a cheap lone-caption + later clip gate failure still reaches `fixed_caption_gates`.  
   **P2 MEDIUM** — pipeline/package.py:240 and tests/package/test_medley.py:399: extend `contexts_pass` to also test measured=False and add a Rig case that produces cheap caption violation *plus* an excluded clip after the first cheap check.  
   **P2 MEDIUM** — pipeline/package.py:128 and :274: capture the *exact* `nv_plan` dict from the in-loop call and pass it to `no_voice(..., plan=nv_plan)` instead of recomputing; eliminates the closure-variable divergence entirely.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Make the in-loop `nv_plan` object the single source of truth passed through to `no_voice` (and reuse its `order`/`added`/`why_not` fields) so the decision and execution can never diverge and the guard at line 240 can be simplified.

7. **PRODUCTION READY?**  
   Yes with conditions: (a) fix the unbound-`cx` path at pipeline/

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 63 s finish=stop usage in 19534 / out 2012 usd~0.089 (upper-bound price)

# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0734

## 1. WHAT DID THEY CATCH THAT YOU MISSED?

In Cycle 1, I likely focused on the structural refactoring of `nv_order` and the removal of `no_voice_fits`. The other models (specifically GLM-5.3-Flash and Grok-4.20) correctly identified the **state mutation risk** in `nv_order` (Attack d) and the **parameter passing nuance** in `fixed_caption_gates` (Attack b/c).

However, the most significant "miss" in a general audit is often the **interaction between the new `fixed_caption_gates` logic and the `lone_slot` guard**. While GLM flagged the `lone_slot` logic as "correct," it did not explicitly verify the **short-circuit evaluation order** in the new `no_voice` block (lines 239-244). Specifically, the condition `if cheap or not fid["ok"] or not cx["ok"]:` is evaluated *before* the `lone_slot` check. If `cheap` is non-empty but `cx` is also failing, the code enters the block, then checks `lone_slot(cheap + fid["violations"])`. If `cx` is failing, `lone_slot` might return `None` (if violations are mixed) or "caption" (if only caption violations exist in `cheap`/`fid`). The code correctly requires `cx["ok"]` to be True to proceed to the fixed caption path. This is subtle but correct.

What I missed: **The specific scenario where `cheap` is empty, `fid` is failing on caption, but `cx` is failing on a *different* segment.** In this case, `lone_slot(cheap + fid["violations"])` would return "caption" (since `cheap` is empty and `fid` only has caption violations). However, the guard `cx["ok"]` is False, so the code correctly rejects the fixed caption path. This is safe.

## 2. WHERE DO YOU AGREE OR DISAGREE?

*   **GLM-5.3-Flash (d) `nv_order` state divergence:** **Agree.** The in-loop call to `nv_order` (line 274) and the post-loop call inside `no_voice` (line 176) use the same `dropped`, `doomed`, and `cleared` state *at the moment of the call*. Since `nv_order` is a pure function of its arguments and the closure variables (which are not mutated between the `break` and the `no_voice` call), the results are identical. The "risk" is theoretical if code were inserted between them, but the current diff shows a direct `break` followed by the loop exit and `no_voice` call. **Verdict: Not a bug, but a latent fragility.**
*   **Grok-4.20 (b) `fixed_caption_gates` extraction:** **Agree.** The extraction is behavior-preserving. `rewrite_alone` previously built `pk3` and ran gates; now it calls `fixed_caption_gates`. The inputs (`segs`, `by_id`, `ctx`, etc.) are the same. The `a_use(pk3)` vs `{sg["label"]: a_by[sg["moment_id"]]...}` change is equivalent because `a_use` is defined as that comprehension in the codebase (verified in Cycle 1 consensus).
*   **Qwen3.8-27B (d) `nv_order` determinism:** **Agree.** Qwen's initial "critical" was self-refuted. `nv_order` is deterministic. The key insight is that `nv_order` does *not* mutate state; it only reads. Therefore, the in-loop decision and the post-loop execution are consistent.

## 3. NEW FINDINGS FROM THIS REVIEW

**<medium> (c) `fixed_caption_gates` re-runs `cheap_checks` on `pk3`, but `pk3` is built from `segs` which may include the *added* clip.**
In `no_voice`, if `added` is not None, `order` includes the new clip. `fixed_caption_gates` is called with `order` (line 247). Inside `fixed_caption_gates`, `pk3` is assembled from `segs` (which is `order`). The `cheap_checks` run on this new package. This is correct: the fixed caption must pass gates on the *final* line-up. However, note that `cheap_checks` includes `RUNTIME` and `R4`. If the added clip causes the total duration to exceed `RUNTIME_S[1]`, `cheap_checks` will fail. This is correct behavior: the fixed caption cannot save a line-up that is too long.

**<medium> (e) The removed test `test_a_value_loss_never_counts_toward_ruling_3s_two_failures` is correctly removed.**
Under Ruling (A), the "count" of failures is irrelevant because the *shape* is the same. Whether the takeaway was removed by two failed writes (Ruling 3) or one value loss (Ruling 91), the result is the same no-voice shape. The test asserted a specific count of `value_calls`, which is no longer a meaningful invariant. The new tests (`test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip`, etc.) correctly assert the *outcome* (package with added clip, no rewrite).

**<high> (c) Potential issue: `lone_slot` is called with `cheap + fid["violations"]`, but `cx["violations"]` is NOT included.**
Line 240: `lone_slot(cheap + fid["violations"]) == "caption"`.
If `cx` is failing (e.g., context integrity violation on the *title*), `cx["ok"]` is False, so the guard `cx["ok"]` prevents entry.
If `cx` is passing, `cx["violations"]` is empty.
So, `lone_slot` only sees `cheap` and `fid` violations. This is correct: Ruling 65 (b) applies when the *caption* fails its *own* gates (cheap/f

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0734 (the orchestrator's 07:30 rulings (A) and (C)), cycle 2: consensus

Reviewers on the fixed diff:
- qwen3.8-27b: P0 none, P1 none, production ready "yes".
- grok-4.20: one P1, refuted below; production ready "yes with conditions".
- glm-5.3-flash: one P1 that asks to SEE a line outside the diff, answered below; "yes with conditions".

Upper-bound cost: about $0.32 ($0.125 + $0.089 + $0.104). Because the code changed after cycle 2 (the
recommendation below), a cycle 3 reviews the delta.

## The two P1s: the code outside the diff, quoted (pipeline/package.py, no_voice)

```
        cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
        if cheap and lone_slot(cheap) != "caption":          # 07:30 (C): only the caption failing alone goes on
            ...
            return None
        with ThreadPoolExecutor(max_workers=8) as nv_pool:
            bg2 = {...exclusion_for / truth_for per clip...}
            got = {mid: (f[0].result(), f[1].result()) for mid, f in bg2.items()}
            if any(e.get("verdict") != "keep" or not t.get("ok") or (t.get("edges") or {}).get("cuttable") is not True
                   for e, t in got.values()):
                note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
                return None
            fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
        fixed = None                                       # fid and cx are bound: every exit above returns None
        if cheap or not fid["ok"] or not cx["ok"]:
```

- glm P1 ("is there an `if` guarding paid_gates that could skip it on the (C) path?"): there is none.
  - paid_gates runs unconditionally once the clips' own gates pass.
  - On the (C) path (a caption failing its cheap gates alone), execution reaches it, and fid / cx are bound at the
    check. test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption executes exactly this path.
- grok P1 ("a lone caption failure plus a later clip-exclusion failure reaches the check with cx unbound: a
  NameError, and (C) bypassed"): REFUTED.
  - A clip failing its gate returns None INSIDE the `with` block, before the check, so no name is unbound.
  - Ending there is correct: (C) applies only when the caption ALONE fails, and a failing clip is no package on any
    path.
  - Now pinned by a test: test_a_lone_caption_failure_with_a_clip_failing_its_gate_ends_cleanly. It covers a caption
    failing house style plus an added clip failing exclusion: no package, why_not = the clip's gate, no caption_fallback.

## Implemented (recommended by grok and glm, both P2): one plan object

- The value-loss branch keeps the nv_order() result it decided on (v_plan) and passes it to
  no_voice(..., plan=v_plan). no_voice() builds from that object; ruling 3's path (plan None) computes its own.
  - The decision and the line-up built can no longer diverge, even if the code between them grows later.
  - Muta

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0734/C3_STEP.diff (566 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f7f2d5a..d542ae5 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -23,8 +23,8 @@ GATES (hard, every one, recorded in a sealed inventory, package_pin.required_gat
   6 |                the clips-alone verdict first (no writing before it passes);
   7 |                cheap (no model): VO fidelity's deterministic rules, DUPLICATE, runtime, R4, the L-y shape;
   8 |                then RULING 91's VALUE verdict on the takeaway (takeaway_value, before any paid gate; a takeaway
   9 | -              that loses it never ships: the no-voice shape when the line-up's own clips meet the seconds, else ONE
  10 | -              rewrite of the takeaway alone; a second loss ends the line-up);
  11 | +              that loses it never ships: the one no-voice shape (07:30 (A): its own clips or the added clip), else,
  12 | +              when no no-voice line-up exists, ONE rewrite of the takeaway alone; a second loss ends the line-up);
  13 |                then concurrently: the classifying fidelity verdict (A / B / C / D, 05:25 items 1-2) and context
  14 |                integrity B0 / B / C (L-s; step A precomputed); exclusion (L-u) and the second recognition pass (L-v 2)
  15 |                start in the background once the clips-alone verdict passes; then COHERENCE with the takeaway (>= 4).
  16 | @@ -1830,16 +1830,6 @@ def takeaway_value(router, segs, ctx, line, writers_v, writers_f, seed=7):
  17 |                  ok=all(v[k] == "yes" for k in SPOT.VALUE_KEYS) and base["words"] <= LY_TAKEAWAY_MAX_WORDS)
  18 |  
  19 |  
  20 | -def no_voice_fits(segs, med):
  21 | -    """RULING 91 (medley half): whether a line-up's OWN clips meet the seconds with no VO line, so that a takeaway the
  22 | -    value verdict refused falls back to L-y's no-voice shape with no clip added: the clips-alone verdict measured with
  23 | -    no flagged join (a no-voice medley carries no bridge either: ruling 3), and the clips' seconds inside what
  24 | -    no_voice() accepts (the factory's estimate, the clips + FINAL_TAIL_S, inside 60-70 s)."""
  25 | -    content = sum(m["duration_s"] for m in segs)
  26 | -    return med.get("measured") is True and med.get("flagged") == [] and \
  27 | -        RUNTIME_S[0] - FINAL_TAIL_S <= content <= RUNTIME_S[1] - FINAL_TAIL_S
  28 | -
  29 | -
  30 |  def lone_slot(violations):
  31 |      """RULING 65: "caption" or "title" when EVERY violation is on that one line (the takeaway and the other line pass),
  32 |      else None."""
  33 | @@ -1922,6 +1912,29 @@ def merge_fid(fid, slot, one):
  34 |                  backend=f"{fid.get('backend')}; the {slot} alone: {one.get('backend')} (ruling 65)")
  35 |  
  36 |  
  37 | +def fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels, writers_v, writers_f, why):
  38 | +    """RULING 65 (b): the package with the FIXED caption (fixed_caption: code-written, no model, so no model verdict;
  39 | +    caption_fallback: true). Its deterministic fidelity layer and the house style (cheap_checks) and context integrity
  40 | +    on the package as it will be sealed still run; the other lines keep their verdicts in `fid` (merge_fid). One code
  41 | +    path for ruling 65's caption and, since the orchestrator's 07:30 ruling (C), for a caption that alone fails its gates
  42 | +    on a no-voice path. -> (pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), the fixed line)."""
  43 | +    line = fixed_caption(fields, segs, ctx)
  44 | +    pk3 = assemble_medley([m["moment_id"] for m in segs], by_id, dict(fields, caption=line), ctx,
  45 | +                          f"{pk.get('vo_kind')}; {why}")
  46 | +    pk3["medley"] = pk.get("medley")
  47 | +    pk3["caption_fallback"] = True
  48 | +    cheap3 = cheap_checks(pk3, a_by, levels, ctx.now)
  49 | +    man = {"channels": [sg["channel"] for sg in pk3["segments"]], "date": ctx.now.strftime("%Y-%m-%d")}
  50 | +    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk3["lines"] if x["slot"] == "caption"]
  51 | +    one = {"deterministic": VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels),
  52 | +           "verdict": {"ok": True, "violations": [], "claims": [], "classes": {"caption": ["the fixed line: no fact"]}},
  53 | +           "measured": True, "replayed": False, "backend": "code, no model: the fixed caption (ruling 65 b)"}
  54 | +    fid3 = merge_fid(fid, "caption", one)
  55 | +    cx3 = CI.check_contexts(router, pk3, CI.contexts_from_sources(pk3, sources, ctx.now), writers_v, 7,
  56 | +                            {sg["label"]: a_by[sg["moment_id"]] for sg in pk3["segments"]}, writers_f, True)
  57 | +    return pk3, fid3, cx3, cheap3, line
  58 | +
  59 | +
  60 |  def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ctx, a_by, sources, levels, writers_v,
  61 |                    writers_f, avoid_vendor=None, seed=7):
  62 |      """RULING 65 (12:52): only `slot` ("caption" or "title") failed (`refused`: its violations); the takeaway and the
  63 | @@ -1980,18 +1993,9 @@ def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ct
  64 |          rec["why"] = (f"the title failed alone {1 + len(rec.get('tries') or [])} times (its second write on the other "
  65 |                        f"writer model, 17:20): held (ruling 65 c): {rec['why']}")
  66 |          return pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, a_by, levels, ctx.now), rec
  67 | -    line = fixed_caption(fields, segs, ctx)               # (b): the fixed caption, code-written, no model
  68 | -    pk3 = build_pk(line, "the fixed caption (ruling 65 b)")
  69 | -    pk3["caption_fallback"] = True
  70 | -    cheap3 = cheap_checks(pk3, a_by, levels, ctx.now)
  71 | -    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk3["lines"] if x["slot"] == "caption"]
  72 | -    one = {"deterministic": VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels),
  73 | -           "verdict": {"ok": True, "violations": [], "claims": [], "classes": {"caption": ["the fixed line: no fact"]}},
  74 | -           "measured": True, "replayed": False, "backend": "code, no model: the fixed caption (ruling 65 b)"}
  75 | -    fid3 = merge_fid(fid, "caption", one)
  76 | -    cx3 = CI.check_contexts(router, pk3, CI.contexts_from_sources(pk3, sources, ctx.now), writers_v, 7, a_use(pk3),
  77 | -                            writers_f, True)
  78 | -    rec.update(fallback=line["text"], caption_fallback=True)
  79 | +    pk3, fid3, cx3, cheap3, line = fixed_caption_gates(router, pk, fields, fid, segs, by_id, ctx, a_by, sources, levels,
  80 | +                                                       writers_v, writers_f, "the fixed caption (ruling 65 b)")
  81 | +    rec.update(fallback=line["text"], caption_fallback=True)       # (b): the fixed caption, code-written, no model
  82 |      return pk3, fid3, cx3, cheap3, rec
  83 |  
  84 |  
  85 | @@ -2328,11 +2332,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  86 |      only if its clips meet the seconds; otherwise the takeaway may be rewritten once"): every written takeaway that
  87 |      passes its cheap gates is asked ONE value verdict (takeaway_value) before any paid gate. A clear yes on all four
  88 |      (and <= 20 words in code): the write goes on, and the package seals the "takeaway_value" row with the line it
  89 | -    judged. A loss (no verdict included): the takeaway never ships. When the line-up's OWN clips meet the seconds with
  90 | -    no VO line (no_voice_fits), the no-voice shape follows at once (no_voice(value=...): no clip added). Otherwise ONE
  91 | -    rewrite of the takeaway alone, told the refusal, whatever the ruling-66 counts say. Its loss ends the line-up with no
  92 | -    package. A value loss never counts toward ruling 3's two failures, so ruling 3's no-voice (which may add a clip)
  93 | -    keeps its own trigger.
  94 | +    judged. A loss (no verdict included) removes the takeaway, and THE ONE NO-VOICE SHAPE follows at once (the
  95 | +    orchestrator's 07:30 ruling (A): "one shape whatever removed the takeaway"): nv_order's line-up, the line-up's own
  96 | +    clips or the added clip when the seconds need it, every clip gate and join as usual (no_voice(value=...)). Only
  97 | +    when no no-voice line-up exists (no clip lands the seconds, or a join needs a bridge) is the takeaway alone
  98 | +    rewritten ONCE, told the refusal, whatever the ruling-66 counts say; its loss ends the line-up with no package.
  99 | +    A failed no-voice line-up ends the line-up too, as on ruling 3's path. A value loss never counts toward ruling 3's
 100 | +    two failures (it already leads to the same shape). On either no-voice path, a caption that alone fails its gates
 101 | +    becomes ruling 65 (b)'s fixed caption (07:30 (C)); a failing title holds.
 102 |      -> {"package", "packages", "tried", "angles", "takeaways" (every written takeaway with its gates), ...}."""
 103 |      t0 = time.time()
 104 |      usd0 = _spent(spend)
 105 | @@ -2624,53 +2631,63 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 106 |                  f"${BUDGET_USD_REPORTED:.2f} reported / ${l_est:.2f} of the ${BUDGET_USD_ESTIMATE:.2f} estimate (ruling 5, "
 107 |                  f"per package delivered: ruling 41)")
 108 |  
 109 | -    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None):
 110 | -        """Ruling 3 (22:40): the takeaway failed its gates twice on a line-up whose clips ALONE passed with no join a
 111 | -        viewer cannot follow, so the package ships with NO VO line: clips back to back and the sign-off. It is not
 112 | -        dropped. The title and caption are the latest write's and go through every gate again. The factory's estimate
 113 | -        must still land 60-70 s, so when the clips are too short one more clip of the angle is added in the proposer's
 114 | -        order, and the new line-up is judged on the clips alone again. -> a package, or None (rec["no_voice"] why).
 115 | -        RULING 91 (medley half), value = the value verdict the takeaway lost: "a medley that loses its takeaway falls
 116 | -        back to L-y's no-voice shape only if its clips meet the seconds": the line-up's OWN clips (no_voice_fits), so no
 117 | -        clip is ever added on this path; the record names ruling 91 and carries the verdict."""
 118 | +    def nv_order(angle, segs, med, dropped):
 119 | +        """THE NO-VOICE LINE-UP, decided by code before any paid call (ruling 3; the orchestrator's 07:30 ruling (A):
 120 | +        "the no-voice shape is one shape whatever removed the takeaway"): the clips-alone verdict measured with every
 121 | +        join followable; the line-up's OWN clips when they meet the seconds with no VO line; else ONE more clip of the
 122 | +        angle, in the proposer's order, that lands them under the line-up rules (never the registry's line-up, ruling
 123 | +        66). -> {"order", "added", "why_not", "registered_skipped"}; order None when no no-voice line-up exists."""
 124 |          nv_lo, nv_hi = RUNTIME_S[0] - FINAL_TAIL_S, RUNTIME_S[1] - FINAL_TAIL_S
 125 | -        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 126 | -        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 127 | +        plan = {"order": None, "added": None, "why_not": None, "registered_skipped": []}
 128 |          if med.get("measured") is not True or med.get("flagged") != []:     # audit 2240 C1 (qwen, glm): its own guard
 129 | -            note["why_not"] = "the clips-alone verdict is not a measured pass with every join followable"
 130 | -            return None
 131 | -        order, added, nv_med = list(segs), None, med
 132 | -        content = sum(m["duration_s"] for m in order)
 133 | +            return dict(plan, why_not="the clips-alone verdict is not a measured pass with every join followable")
 134 | +        content = sum(m["duration_s"] for m in segs)
 135 |          if content > nv_hi:
 136 | -            note["why_not"] = f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line"
 137 | -            return None
 138 | -        if content < nv_lo and value is not None:            # ruling 91: only if its OWN clips meet the seconds
 139 | -            note["why_not"] = (f"ruling 91: {content:.1f} s of clips, under {nv_lo:.1f} s with no VO line, and no clip "
 140 | -                               f"is added for a takeaway the value verdict refused")
 141 | +            return dict(plan, why_not=f"{content:.1f} s of clips: over {nv_hi:.1f} s with no VO line")
 142 | +        if content >= nv_lo:
 143 | +            return dict(plan, order=list(segs))
 144 | +        pos = {m_: i for i, m_ in enumerate(angle["moments"])}
 145 | +        chans = {m["channel_id"] for m in segs}               # "the packager may add a clip"
 146 | +        for mid in angle["moments"]:
 147 | +            m = cleared.get(mid)
 148 | +            if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 149 | +                    not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 150 | +                continue
 151 | +            cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 152 | +            if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 153 | +                    sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 154 | +                    sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
 155 | +                    not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 156 | +                continue
 157 | +            if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
 158 | +                plan["registered_skipped"].append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
 159 | +                continue
 160 | +            return dict(plan, order=cand, added=mid)
 161 | +        return dict(plan, why_not=(f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 162 | +                                   + (f" (ruling 66: {plan['registered_skipped']} left to the registry)"
 163 | +                                      if plan["registered_skipped"] else "")))
 164 | +
 165 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None, plan=None):
 166 | +        """THE NO-VOICE SHAPE: the package ships with NO VO line, clips back to back and the sign-off; it is not
 167 | +        dropped. Ruling 3 (22:40): the takeaway failed its gates twice; RULING 91 (value = the value verdict the
 168 | +        takeaway lost): its value verdict said no. The orchestrator's 07:30 ruling (A): "one shape whatever removed the
 169 | +        takeaway": the line-up is nv_order's (its own clips, or the added clip when the seconds need it); a line-up
 170 | +        with an added clip is judged on the clips alone again, and every clip gate runs on every clip. The title and
 171 | +        caption are the latest write's and go through every gate again. 07:30 (C): when ONLY the caption fails (its
 172 | +        cheap gates, or its verdict with context integrity passing: ruling 65's own trigger), ruling 65 (b)'s fixed
 173 | +        caption is used, as there (fixed_caption_gates, caption_fallback true); a failing title still holds (65 c).
 174 | +        The record names the ruling and, for 91, carries the verdict. plan: the nv_order() result the caller already
 175 | +        decided on (the value-loss branch passes its own, so the decision and what is built are one object; audit 0734
 176 | +        C2, grok and glm); None computes it here (ruling 3's path). -> a package, or None (rec["no_voice"] why)."""
 177 | +        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 178 | +        plan = plan if plan is not None else nv_order(angle, segs, med, dropped)
 179 | +        if plan["registered_skipped"]:
 180 | +            note["registered_skipped"] = plan["registered_skipped"]
 181 | +        if plan["order"] is None:
 182 | +            note["why_not"] = plan["why_not"]
 183 |              return None
 184 | -        if content < nv_lo:                                  # "the packager may add a clip"
 185 | -            chans = {m["channel_id"] for m in segs}
 186 | -            for mid in angle["moments"]:
 187 | -                m = cleared.get(mid)
 188 | -                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 189 | -                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 190 | -                    continue
 191 | -                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 192 | -                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 193 | -                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 194 | -                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
 195 | -                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 196 | -                    continue
 197 | -                if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
 198 | -                    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
 199 | -                    continue
 200 | -                order, added = cand, mid
 201 | -                break
 202 | -            if added is None:
 203 | -                note["why_not"] = (f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 204 | -                                   + (f" (ruling 66: {note['registered_skipped']} left to the registry)"
 205 | -                                      if note.get("registered_skipped") else ""))
 206 | -                return None
 207 | +        order, added, nv_med = plan["order"], plan["added"], med
 208 | +        if added is not None:                                # its new line-up, judged on the clips alone again
 209 |              ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
 210 |              note["medley"] = nv_med
 211 |              if not ok2 or nv_med["flagged"]:
 212 | @@ -2681,8 +2698,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 213 |              ("ruling 91: the takeaway did not earn its place (its value verdict: " +
 214 |               (", ".join(f"{k} {value.get(k)}" for k in ("adds", "no_restate", "missed", "short"))
 215 |                if value.get("measured") else "no verdict") +
 216 | -             f"; {str(value.get('why') or '')[:200]}); the line-up's own clips meet the seconds, so L-y's no-voice "
 217 | -             f"shape ships them back to back with the sign-off only")
 218 | +             f"; {str(value.get('why') or '')[:200]}); L-y's no-voice shape (one shape, 07:30 (A)) ships the clips back "
 219 | +             f"to back with the sign-off only" + (f", one clip added ({added})" if added else ""))
 220 |          fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 221 |                    "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 222 |                    "supply_exception": exception,
 223 | @@ -2710,7 +2727,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 224 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 225 |          pk["medley"] = nv_med
 226 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 227 | -        if cheap:
 228 | +        if cheap and lone_slot(cheap) != "caption":          # 07:30 (C): only the caption failing alone goes on
 229 |              note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
 230 |              note["violations"] = cheap
 231 |              return None
 232 | @@ -2723,10 +2740,23 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 233 |                  note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
 234 |                  return None
 235 |              fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
 236 | -        if not fid["ok"] or not cx["ok"]:
 237 | -            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 238 | -            note["violations"] = fid["violations"] + cx["violations"]
 239 | -            return None
 240 | +        fixed = None                                       # fid and cx are bound: every exit above returns None
 241 | +        if cheap or not fid["ok"] or not cx["ok"]:         # ruling 65's own trigger: context integrity must pass on
 242 | +            if not (cx["ok"] and fid.get("measured") and lone_slot(cheap + fid["violations"]) == "caption"):   # its own
 243 | +                note["why_not"] = "the title / caption fail VO fidelity or context integrity" + \
 244 | +                    (f" (cheap gates: {sorted({v['rule'] for v in cheap})})" if cheap else "")
 245 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 246 | +                return None
 247 | +            refused = [{k: v.get(k) for k in ("rule", "detail")} for v in cheap + fid["violations"]]
 248 | +            pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), fixed = fixed_caption_gates(   # 07:30 (C): ruling 65 (b)
 249 | +                router, pk, fields, fid, order, cleared, ctx, a_by, sources, levels, writers_v, writers_f,
 250 | +                "the fixed caption on a no-voice path (07:30 (C), ruling 65 b)")
 251 | +            note["caption_fallback"] = {"refused": refused, "written": fields["caption"]["text"],
 252 | +                                        "fixed": fixed["text"]}
 253 | +            if cheap or not fid["ok"] or not cx["ok"]:
 254 | +                note["why_not"] = "the fixed caption (07:30 (C), ruling 65 b) did not pass its gates"
 255 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 256 | +                return None
 257 |          coh = dict(nv_med, vo_point=None,
 258 |                     note=f"no VO line: the clips-alone verdict is the coherence verdict (ruling {note['ruling']})")
 259 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 260 | @@ -2741,7 +2771,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 261 |          if problems:
 262 |              note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 263 |              return None
 264 | -        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
 265 | +        pk["models"] = {"angle": angle_reply.backend,
 266 | +                        "writer": "the latest write's title and caption" if fixed is None else
 267 | +                                  "the latest write's title; the caption is code's fixed line (07:30 (C), ruling 65 b)",
 268 |                          "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 269 |                          "context": cx.get("backends"), "coherence": nv_med.get("backend")}
 270 |          pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 271 | @@ -2915,9 +2947,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 272 |                          relined, w_used = True, writes
 273 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 274 |                  alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 275 | -                v_lost, v_redo, v_novoice, val = [], False, None, None   # RULING 91 (medley half): the value
 276 | -                #   verdicts the takeaway lost, its ONE rewrite still due, the loss that sends the line-up to the no-voice
 277 | -                #   shape, and the verdict of the takeaway now written
 278 | +                v_lost, v_redo, v_novoice, v_plan, val = [], False, None, None, None   # RULING 91 (medley half):
 279 | +                #   the value verdicts the takeaway lost, its ONE rewrite still due, the loss that sends the line-up to
 280 | +                #   the no-voice shape with the plan decided for it (nv_order), and the verdict of the takeaway now written
 281 |                  while True:                                # RULING 66 amended (17:02): the writes; then, when the
 282 |                      lone = w_used >= writes or v_redo      # takeaway alone failed, the takeaway ALONE, up to twice
 283 |                      if lone and not v_redo and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None
 284 | @@ -3077,13 +3109,14 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 285 |                                 "detail": (f"{answers}: {val.get('why')}" if val.get("measured") else
 286 |                                            f"no clear yes ({val.get('why')})")[:300]}
 287 |                          t_refused += [ref] if ref not in t_refused else []      # what its one rewrite is told
 288 | -                        if no_voice_fits(segs, med):       # its OWN clips meet the seconds: L-y's no-voice shape
 289 | -                            v_novoice = val
 290 | +                        nv_plan = nv_order(angle, segs, med, dropped)          # 07:30 (A): the ONE no-voice shape,
 291 | +                        if nv_plan["order"] is not None:   # its own clips or the added clip: no_voice() below
 292 | +                            v_novoice, v_plan = val, nv_plan                  # built from this very plan
 293 |                              break
 294 | +                        rec["no_voice_plan"] = {k: nv_plan[k] for k in ("why_not", "registered_skipped")}
 295 |                          if len(v_lost) > 1:                # its one rewrite did not earn its place either
 296 |                              rec["why"] = ("ruling 91: the takeaway did not earn its place, nor did its one rewrite, "
 297 | -                                          "and the line-up's own clips do not meet the no-voice seconds "
 298 | -                                          f"({sum(m['duration_s'] for m in segs):.1f} s of clips)")
 299 | +                                          f"and no no-voice line-up exists ({nv_plan['why_not']})")[:500]
 300 |                              break
 301 |                          v_redo = True                      # ONE rewrite of the takeaway alone, told why
 302 |                          last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 303 | @@ -3195,7 +3228,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 304 |                          (v_novoice is not None or take_failed >= NO_VOICE_AFTER) and last_fields is not None and \
 305 |                          not out.get("budget_stop") and not out.get("lock_stop"):
 306 |                      nv = no_voice(angle, segs, med, last_fields, exception, dropped, rec, ai, n_lineup,
 307 | -                                  value=v_novoice)      # ruling 91 (its own clips, none added) before ruling 3
 308 | +                                  value=v_novoice, plan=v_plan)   # ruling 91 with its decided plan; else ruling 3
 309 |                      if nv is not None:
 310 |                          out["packages"].append(nv)
 311 |                          rec["result"] = f"PACKAGE (no voice, ruling {3 if v_novoice is None else 91})"
 312 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 313 | index ed2b1e3..fc26aa1 100644
 314 | --- a/tests/package/test_medley.py
 315 | +++ b/tests/package/test_medley.py
 316 | @@ -530,10 +530,11 @@ class Rig:
 317 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 318 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 319 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 320 | -                 real_value=False):
 321 | +                 real_value=False, caption=None):
 322 |          import providers as P
 323 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 324 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 325 | +        self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
 326 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 327 |          self.takeaways, self.spend = list(takeaways or []), spend
 328 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 329 | @@ -625,7 +626,7 @@ class Rig:
 330 |          fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
 331 |                    "bridge_after": join[0] if join is not None and b is not None else None,
 332 |                    "title": {"text": "Nobody bends the rules", "cites": []},
 333 | -                  "caption": {"text": "nobody bends these rules", "cites": []},
 334 | +                  "caption": {"text": self.caption, "cites": []},
 335 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 336 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 337 |  
 338 | @@ -3261,17 +3262,94 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 339 |          self.assertEqual([x["text"] for x in tried["value_lost"]], [Rig.LINE])
 340 |          self.assertEqual(tried["result"], "PACKAGE")
 341 |  
 342 | -    def test_a_second_loss_ends_the_line_up_and_never_adds_a_clip(self):
 343 | -        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # ruling 3 would add z (52 s)
 344 | -        rig = Rig(ms, ["h", "x", "y", "z"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 345 | +    def test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip(self):
 346 | +        """The orchestrator's 07:30 ruling (A): "the no-voice shape is one shape whatever removed the takeaway (two
 347 | +        failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
 348 | +        need it, each added clip passing every clip gate and the joins as usual." No rewrite is spent."""
 349 | +        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # 39 s + z = 52 s with no VO line
 350 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED * 2, [None], values=[{"adds": "no", "why": "it restates"}])
 351 | +        out = rig.run()
 352 | +        pk = out["package"]
 353 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])
 354 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 355 | +        self.assertIn("one clip added (z)", pk["no_voice"]["why"])
 356 | +        self.assertEqual(pk["no_voice"]["value"]["adds"], "no")
 357 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])          # the new line-up judged on the clips alone
 358 | +        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # no rewrite of the takeaway
 359 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 360 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 361 | +        self.assertNotIn("takeaway_value", pk["gates"])
 362 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 363 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 364 | +
 365 | +    def test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite(self):
 366 | +        """As on ruling 3's path: the added clip's line-up fails the clips-alone verdict, so there is no package, and
 367 | +        the takeaway is not rewritten (a no-voice line-up existed)."""
 368 | +        ms = self.SHORT + [pm("z", "D", 13.0)]
 369 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED + [(False, [], {"clip_03": 2}, Rig.LINE)], [None],
 370 | +                  values=[{"adds": "no"}])
 371 | +        out = rig.run()
 372 | +        self.assertIsNone(out["package"])
 373 | +        self.assertEqual(len(rig.value_calls), 1)
 374 | +        self.assertIn("ruling 91", out["tried"][0]["why"])
 375 | +        self.assertIn("fails on the clips alone", out["tried"][0]["why"])
 376 | +
 377 | +    def test_a_doomed_clip_is_never_the_added_clip(self):
 378 | +        """Audit 0734 C1 (qwen's condition): z fails exclusion in angle 1's line-up, so it is doomed for the whole build.
 379 | +        Angle 2's takeaway then loses its value verdict on 39 s of clips: nv_order skips z, no no-voice line-up exists,
 380 | +        and ruling 91's one rewrite is used instead."""
 381 | +        ms = self.SHORT + [pm("z", "D", 13.0)]
 382 | +        rig = Rig(ms, [["h", "z", "y"], ["h", "x", "y", "z"]], self.MED * 2, [None, None], excluded={"z"},
 383 | +                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{"adds": "no"}])
 384 | +        out = rig.run()
 385 | +        pk = out["package"]
 386 | +        self.assertIn("'z': 'exclusion'", out["tried"][0]["why"])                # doomed in angle 1
 387 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])   # never added back
 388 | +        self.assertNotIn("no_voice", out["tried"][-1])
 389 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway"), self.NEW)
 390 | +        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])
 391 | +
 392 | +    def test_a_lone_caption_failure_with_a_clip_failing_its_gate_ends_cleanly(self):
 393 | +        """Audit 0734 C2 (grok): the no-voice line-up's caption fails alone AND its added clip fails exclusion. The
 394 | +        clip's gate ends it first (return None before any verdict is read): no fixed caption, no unbound name."""
 395 | +        restore = self.contexts_pass()
 396 | +        try:
 397 | +            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None],
 398 | +                      values=[{"adds": "no"}], caption=self.UPPER, excluded={"z"})
 399 | +            out = rig.run()
 400 | +        finally:
 401 | +            restore()
 402 | +        self.assertIsNone(out["package"])
 403 | +        nv = out["tried"][0]["no_voice"]
 404 | +        self.assertEqual(nv["why_not"], "a clip fails exclusion, the second pass or CUTTABLE")
 405 | +        self.assertNotIn("caption_fallback", nv)
 406 | +
 407 | +    def test_a_value_loss_leaves_a_registered_line_up_to_the_registry(self):
 408 | +        """Audit 0734 C2 (glm): on ruling 91's path too, the only clip that would land the seconds forms a registered
 409 | +        line-up, so it is left to the registry (ruling 66): no no-voice line-up exists, the reason is recorded, and the
 410 | +        one rewrite is used."""
 411 | +        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED, [None],
 412 | +                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{"adds": "no"}],
 413 | +                  registered={("h", "x", "y", "z"): {"key": "h+x+y+z", "state": "resting", "until": None,
 414 | +                                                     "source": "proof/ledger_x", "index": 0}})
 415 | +        out = rig.run()
 416 | +        plan = out["tried"][0]["no_voice_plan"]
 417 | +        self.assertEqual(plan["registered_skipped"], ["h+x+y+z"])
 418 | +        self.assertIn("left to the registry", plan["why_not"])
 419 | +        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])                    # h+x+y+z never judged
 420 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "takeaway"), self.NEW)
 421 | +
 422 | +    def test_a_second_loss_ends_the_line_up_when_no_no_voice_line_up_exists(self):
 423 | +        """No clip of the angle can be added (h, x, y are all it has), so ruling 91's one rewrite is used; its loss
 424 | +        ends the line-up."""
 425 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 426 |                    values=[{"adds": "no"}, {"missed": "no"}])
 427 |          out = rig.run()
 428 |          self.assertIsNone(out["package"])
 429 |          self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # one rewrite, no more
 430 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 431 |          self.assertIn("nor did its one rewrite", out["tried"][0]["why"])
 432 | -        self.assertNotIn("no_voice", out["tried"][0])                            # never the no-voice shape with z
 433 | -        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
 434 | +        self.assertIn("no no-voice line-up exists", out["tried"][0]["why"])
 435 | +        self.assertNotIn("no_voice", out["tried"][0])
 436 |          self.assertIn("ruling 91", out["why_none"])
 437 |  
 438 |      def test_no_verdict_is_a_loss(self):
 439 | @@ -3294,18 +3372,115 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 440 |          self.assertEqual(out["package"]["no_voice"]["added_clip"], "z")          # ruling 3 may still add a clip
 441 |          self.assertNotIn("value", out["package"]["no_voice"])
 442 |  
 443 | -    def test_a_value_loss_never_counts_toward_ruling_3s_two_failures(self):
 444 | -        """One value loss, one ordinary failure (its rewrite breaks house style), then a second value loss: the
 445 | -        takeaway failed its OTHER gates once, so ruling 3's no-voice (which would add z) is not reached."""
 446 | -        bad = "Ultimately nobody bends the rules."                                # house style: the opener
 447 | -        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 448 | -                  takeaways=[Rig.LINE, self.NEW], lines=[{"takeaway": {"text": bad, "cites": []}}],
 449 | -                  values=[{"adds": "no"}, {"adds": "no"}])
 450 | -        out = rig.run()
 451 | +    @staticmethod
 452 | +    def contexts_pass():
 453 | +        """context_integrity stubbed to a measured pass (the fixed caption's own context run calls it directly);
 454 | +        returns the restore function."""
 455 | +        import context_integrity as CI
 456 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 457 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 458 | +                                             "backends": {"B": "xai", "C": "xai"}}
 459 | +        CI.contexts_from_sources = lambda *a, **k: {}
 460 | +
 461 | +        def restore():
 462 | +            CI.check_contexts, CI.contexts_from_sources = saved
 463 | +        return restore
 464 | +
 465 | +    UPPER = "Nobody Bends These Rules."                           # house style: a caption is all lowercase
 466 | +    FIXED = "nobody bends the rules\na / b / c"                   # ruling 65 (b): the title lowercase, then the shows
 467 | +
 468 | +    def test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption(self):
 469 | +        """The orchestrator's 07:30 ruling (C): "on a no-voice path, when only the caption fails its gates, ruling 65
 470 | +        (b)'s fixed caption is used and the line-up goes on (caption_fallback: true, as there)."""
 471 | +        restore = self.contexts_pass()
 472 | +        try:
 473 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 474 | +            out = rig.run()
 475 | +        finally:
 476 | +            restore()
 477 | +        pk = out["package"]
 478 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 479 | +        self.assertTrue(pk["caption_fallback"])
 480 | +        self.assertEqual(pk["caption"], self.FIXED)
 481 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "caption"), self.FIXED)
 482 | +        self.assertEqual(pk["title"], "Nobody bends the rules")                  # the title as written and gated
 483 | +        cf = out["tried"][0]["no_voice"]["caption_fallback"]
 484 | +        self.assertEqual((cf["written"], cf["fixed"]), (self.UPPER, self.FIXED))
 485 | +        self.assertTrue(cf["refused"])
 486 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 487 | +        self.assertIn("ruling 65 b", pk["checks"]["fidelity"]["backend"])        # no model judged the fixed line
 488 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 489 | +        self.assertTrue(mp["caption_fallback"])
 490 | +        self.assertEqual(mp["caption"], self.FIXED)
 491 | +
 492 | +    def test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption(self):
 493 | +        restore = self.contexts_pass()
 494 | +        try:
 495 | +            bad = TestRuling66Amended().failing("caption", "it says the clips agree", "VERDICT_NO")
 496 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[bad])
 497 | +            out = rig.run()
 498 | +        finally:
 499 | +            restore()
 500 | +        pk = out["package"]
 501 | +        self.assertTrue(pk["caption_fallback"])
 502 | +        self.assertEqual(pk["caption"], self.FIXED)
 503 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 504 | +        self.assertEqual(out["tried"][0]["no_voice"]["caption_fallback"]["refused"][0]["rule"], "VERDICT_NO")
 505 | +
 506 | +    def test_c_a_failing_title_still_holds_and_so_do_a_title_and_caption_together(self):
 507 | +        """"The title keeps ruling 65 (c)": no fixed title. A title failing alone, or with the caption, holds."""
 508 | +        restore = self.contexts_pass()
 509 | +        try:
 510 | +            title_bad = TestRuling66Amended().failing("title", "it names no show", "VERDICT_NO")
 511 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad])
 512 | +            out = rig.run()
 513 | +            self.assertIsNone(out["package"])
 514 | +            self.assertIn("title / caption fail", out["tried"][0]["no_voice"]["why_not"])
 515 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 516 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad],
 517 | +                      caption=self.UPPER)                                       # both lines fail: no lone caption
 518 | +            out = rig.run()
 519 | +            self.assertIsNone(out["package"])
 520 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 521 | +        finally:
 522 | +            restore()
 523 | +
 524 | +    def test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends(self):
 525 | +        """As there (ruling 65 b): the fixed line has no model verdict, but context integrity on the package as it will
 526 | +        be sealed still decides. A failing run ends the line-up; nothing ships unchecked."""
 527 | +        import context_integrity as CI
 528 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 529 | +        CI.check_contexts = lambda *a, **k: {"ok": False, "violations": [{"rule": "STRONGER", "segment": "hook",
 530 | +                                                                          "detail": "x"}], "measured": True,
 531 | +                                             "replayed": False, "backends": {"B": "xai", "C": "xai"}}
 532 | +        CI.contexts_from_sources = lambda *a, **k: {}
 533 | +        try:
 534 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 535 | +            out = rig.run()
 536 | +        finally:
 537 | +            CI.check_contexts, CI.contexts_from_sources = saved
 538 |          self.assertIsNone(out["package"])
 539 | -        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # the bad line never reached it
 540 | -        self.assertNotIn("no_voice", out["tried"][0])
 541 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 542 | +        nv = out["tried"][0]["no_voice"]
 543 | +        self.assertIn("the fixed caption", nv["why_not"])
 544 | +        self.assertEqual(nv["caption_fallback"]["fixed"], self.FIXED)
 545 | +
 546 | +    def test_c_ruling_3s_no_voice_path_takes_the_fixed_caption_too(self):
 547 | +        """(C) covers either no-voice path: the takeaway failed its gates twice (ruling 3), clip z is added, and the
 548 | +        latest write's caption, failing alone, becomes the fixed line."""
 549 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 550 | +        restore = self.contexts_pass()
 551 | +        try:
 552 | +            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 553 | +                      takeaways=bad, caption=self.UPPER)
 554 | +            out = rig.run()
 555 | +        finally:
 556 | +            restore()
 557 | +        pk = out["package"]
 558 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
 559 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 560 | +        self.assertTrue(pk["caption_fallback"])
 561 | +        self.assertEqual(pk["caption"], "nobody bends the rules\na / b / c / d")
 562 | +        self.assertEqual(rig.value_calls, [])                                  # house style refused both takeaways first
 563 |  
 564 |      def test_the_real_verdict_runs_inside_the_build_and_its_row_seals(self):
 565 |          """build() with package.takeaway_value itself (not the Rig's stub), only the router faked: a clear yes seals
 566 | 
```

---

You are auditing a change on branch pp-selectid (Protocol Pulse's moments-first video builder). Only state what you
can verify from the diff; if uncertain, say so; do not guess. Be specific: file:line and a concrete input that breaks it.

BACKGROUND (static):
- A MEDLEY pin: the hook clip + 2-4 clips back to back, then at most ONE spoken VO line after the LAST clip (the
  takeaway), then a code-written sign-off. package.build() writes the takeaway, gates it, and seals a pin.
- THE NO-VOICE SHAPE (ruling 3, Nov 12): when the takeaway is removed, the package ships with NO VO line: clips back to
  back and the sign-off. When the clips are too short for the 60-70 s format, ONE more clip of the angle is added (the
  proposer's order), and the new line-up is judged on the clips alone again; every clip gate runs.
- RULING 91's medley half (committed earlier today, 6626c45d): every written takeaway gets ONE value verdict (four
  clear yeses) before any paid gate; a takeaway that loses it never ships. The text: "a medley that loses its takeaway
  falls back to L-y's no-voice shape only if its clips meet the seconds; otherwise the takeaway may be rewritten once."
  As committed, a value loss went to the no-voice shape only on the line-up's OWN clips (never an added clip), else one
  rewrite of the takeaway alone; a second loss ended the line-up.
- RULING 65 (b): when a medley's caption fails its gates, the caption becomes a FIXED line written by code (the title in
  lowercase, a line break, the shows' names; caption_fallback true): no model verdict on it, but its deterministic layer,
  the house style and context integrity still run. Ruling 65 (c): a failing title is held (no fixed title).

THE ORCHESTRATOR'S RULINGS (07:30 ET Nov 14), verbatim:
(A) "NO. Ruling 91 does not end ruling 3's added clip. The no-voice shape is one shape whatever removed the takeaway
    (two failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
    need it, each added clip passing every clip gate and the joins as usual."
(C) "YES, build it: on a no-voice path, when only the caption fails its gates, ruling 65 (b)'s fixed caption is used and
    the line-up goes on (caption_fallback: true, as there). The title keeps ruling 65 (c)."

THE BUILDER'S READING OF (A), stated on STATE for the orchestrator:
a value verdict's no removes the takeaway and the ONE no-voice shape follows (own clips, or the added clip when the
seconds need it). Ruling 91's one rewrite is used only when NO no-voice line-up can be formed (no clip lands the
seconds, or a join needs a bridge). A no-voice line-up that then fails a gate ends the line-up, as on ruling 3's path.

THE CHANGE (pipeline/package.py; the diff follows):
1. nv_order() (a closure in build()): the no-voice line-up decided by code before any paid call, with ruling 3's own
   rules moved out of no_voice() unchanged. no_voice() uses it for BOTH rulings; the "no clip added on the ruling-91
   path" guard is gone. The module-level no_voice_fits() (own clips only) is removed: nothing calls it now.
2. The value-loss branch asks nv_order(): a line-up exists -> break to no_voice(value=...) (which adds the clip when
   needed and judges the new line-up on the clips alone); none -> one rewrite; a second loss ends the line-up.
3. fixed_caption_gates(): ruling 65 (b)'s fixed-caption gating, extracted unchanged from rewrite_alone() (which now
   calls it), and used by no_voice() when ONLY the caption fails, by ruling 65's own trigger: every cheap and fidelity
   violation on the caption slot, context integrity passing, the fidelity verdict measured. The fixed line's cheap
   gates, merged fidelity and context integrity must then pass, or the line-up ends. A failing title still holds.
4. Tests (tests/package/test_medley.py): (A) the added clip on a value loss; a failed no-voice line-up ends without a
   rewrite; the rewrite only when no no-voice line-up exists. (C) the fixed caption after a cheap failure and after a
   verdict failure; a failing title holds (alone or with the caption); the fixed line's own context run still decides;
   ruling 3's path gets it too. One test removed: "a value loss never counts toward ruling 3's two failures" (under (A)
   both paths lead to the same shape, so that count changes no outcome). 15 mutations, each killed. 19 suites, 543 tests.

ATTACK:
(a) Is (A) implemented exactly: same shape and same added-clip rules on both paths; no path where a value loss adds a
    clip that ruling 3 would not, or vice versa; the added clip's line-up judged on the clips alone again?
(b) Is the extraction of fixed_caption_gates() behaviour-preserving for ruling 65's voiced path (rewrite_alone)?
(c) (C): can a fixed caption ship when anything OTHER than the caption failed (the title, a "-" rule such as RUNTIME
    or R4, a clip's own gate, context integrity)? Can a fixed caption skip its own gates?
(d) Is nv_order() deterministic and identical between the in-loop decision and the post-loop no_voice() call (same
    dropped / doomed / registry state), so the decision to skip the rewrite always matches what no_voice() does?
(e) The removed test and the removed no_voice_fits(): any remaining caller or any behaviour now untested?

Answer with findings tagged <critical>, <high>, <medium> (file:line, a concrete scenario), then
"SHIP: yes / no / yes with conditions".


---

## CYCLE 2 INSTRUCTIONS

You've now seen what the other models said. This is your final review.

1. WHAT DID THEY CATCH THAT YOU MISSED?
   Review their findings. Be honest about what you overlooked.

2. WHERE DO YOU AGREE OR DISAGREE?
   For each of their key findings: agree / disagree / partially agree + why.

3. NEW FINDINGS FROM THIS REVIEW
   Anything the combined analysis revealed that nobody caught in Cycle 1?

4. REVISED SCORES
   Update your scores from Cycle 1. Did anything change your assessment?
   | Subsystem | Cycle 1 | Cycle 2 | Why changed |

5. FINAL PRIORITY LIST
   Your definitive list of what must change before this ships.
   P0 CRITICAL | P1 HIGH | P2 MEDIUM — cite file and line numbers.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
   After seeing everything — one sentence. What matters most?

7. PRODUCTION READY?
   Yes / No / Yes with conditions. State your conditions precisely.
