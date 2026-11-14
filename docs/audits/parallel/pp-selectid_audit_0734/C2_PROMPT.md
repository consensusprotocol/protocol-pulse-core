# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0734
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 264 s finish=stop usage in 17079 / out 7144 usd~0.158 (upper-bound price)

<medium> **(d) nv_order() is called twice with potentially different state — the in-loop decision and no_voice()'s call can diverge, and the divergence is silent.** `pipeline/package.py:274` (in-loop, `nv_plan = nv_order(angle, segs, med, dropped)`) vs `pipeline/package.py:176` (inside `no_voice()`, `plan = nv_order(angle, segs, med, dropped)`). `nv_order` reads the closure variables `cleared`, `dropped`, `doomed`, `held_map` (lines 147–157). Between the in-loop call and the later `no_voice()` call, the loop body can mutate `doomed`/`cleared`/`held_map` (e.g. a later iteration's `medley()` failure adds to `doomed`, or a registry hold adds to `held_map`). Concrete scenario: value loss on line-up 1 → in-loop `nv_order` returns an order (rewrite skipped, `break` to `no_voice`) → between the break and `no_voice()`'s own `nv_order` call nothing runs, so here they agree — but the *in-loop* call's result is discarded and recomputed; if any intervening code (e.g. the `rec`/`t_refused` bookkeeping, or a second value loss on the *same* iteration's `v_redo` path) mutated `doomed`, the second call could return `order=None` where the first returned an order, and `no_voice()` would then return `None` with `why_not` "no one clip of the angle lands…" while the loop's `break`-skip-rewrite decision was made on the opposite premise. The code as written does `break` immediately after the in-loop call, so within one iteration they agree; the risk is only that the decision is *recomputed* rather than reused — a latent inconsistency, not a proven bug. I cannot verify from the diff whether any code between the two call sites mutates that state; flagging as needs-verification. </medium>

<medium> **(c) The fixed-caption trigger condition can pass when a cheap violation is NOT on the caption slot — `lone_slot` is checked on the merged list, but the guard `cx["ok"] and fid.get("measured")` does not require the fidelity verdict to be *ok*, only measured; combined with `lone_slot(cheap + fid["violations"]) == "caption"`, a title violation inside `fid["violations"]`... ** Actually, re-reading: `lone_slot` (line 30–32, unchanged) returns the slot only when *every* violation is on that one slot, so a title+caption failure correctly yields `None` (tested at test line 445–449). The real gap: **`fixed_caption_gates` re-runs cheap checks on the *new* package but the `note["caption_fallback"]["refused"]` list (line 245) records only `("rule","detail")` of the cheap+fid violations — the context-integrity violations that also existed are dropped from the record, though they're re-checked.** Minor, record-keeping only. </medium>

<medium> **(b) Extraction is behaviour-preserving for `rewrite_alone` except one visible difference: the `a_use(pk3)` → `a_by[sg["moment_id"]]`-dict change.** Old code (line 76 of old, removed): `CI.check_contexts(..., a_use(pk3), ...)`; new code (line 56): `{sg["label"]: a_by[sg["moment_id"]] for sg in pk3["segments"]}`. If `a_use(pk3)` did anything beyond that dict-comprehension (e.g. filtering by label collisions, or handling segments whose `moment_id` is missing from `a_by`), the extraction changed behaviour. From the diff alone I cannot see `a_use`'s definition; if `a_use` is exactly that comprehension, this is fine — needs-verification, not a proven defect. Also note `fixed_caption_gates` builds `man` (line 49) locally while the old `rewrite_alone` presumably had `man` in scope from earlier code — the diff shows the old code used the same `man`-shaped dict; the new function reconstructs it from `pk3["segments"]` and `ctx.now`, which matches the removed lines 72–74's usage. Likely equivalent; cannot fully confirm. </medium>

<medium> **(e) `no_voice_fits()` removed — the diff shows no remaining caller, and the new `nv_order` (lines 134–143) reproduces its logic (`measured is True`, `flagged == []`, `RUNTIME_S[0]-FINAL_TAIL_S <= content <= RUNTIME_S[1]-FINAL_TAIL_S`) at lines 128, 134–135, 142.** But: the old `no_voice_fits` used `med.get("flagged") == []` (exact equality with empty list); `nv_order` line 128 uses `med.get("flagged") != []` — same. One behavioural difference: old `no_voice_fits` was also the *documented* ruling-91 guard cited in the module docstring (lines 9–10 of the diff, which still says "the no-voice shape when the line-up's own clips meet the seconds, else ONE rewrite" — now stale, since (A) changed that; the docstring at lines 9–12 *is* updated, good). The removed test `test_a_value_loss_never_counts_toward_ruling_3s_two_failures` (old lines 372–380) asserted the *count* of value calls; its replacement tests assert `len(rig.value_calls) == 1` (line 332) and `rig.value_calls == []` (line 491), which together cover the count semantics. No remaining caller of `no_voice_fits` is visible in the diff; if any other module imported it, the diff doesn't show it — needs-verification. </medium>


## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 68 s finish=stop usage in 16959 / out 264 usd~0.091 (upper-bound price)

<medium> pipeline/package.py:60 (rewrite_alone call to fixed_caption_gates): extraction changes pk3 construction from build_pk(line, msg) to assemble_medley(..., by_id, dict(fields, caption=line), ctx, f"{pk.get('vo_kind')}; {why}"); old code used a_use(pk3) for context call while new uses dict comp on pk3["segments"]. Cannot verify exact preservation for voiced ruling-65 path (no test in diff exercises rewrite_alone + fixed_caption).</medium>
<medium> pipeline/package.py:247 (no_voice call to fixed_caption_gates): passes 'cleared' as by_id param (and order as segs) vs. voiced path passing explicit by_id; function assumes they are interchangeable dicts but diff provides no proof they are identical for all inputs (e.g. a moment_id present in by_id but absent from cleared after prior drops).</medium>
<medium> tests/package/test_medley.py:328 (test_a_lost_takeaway...): asserts pk["no_voice"]["added_clip"] but diff does not show note["added_clip"] = added (only note["why"] uses added and note["registered_skipped"]); uncertain how key appears on final pk without guessing unshown code.</medium>

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 65 s finish=stop usage in 18570 / out 4456 usd~0.123 (upper-bound price)

To audit `pp-selectid-0734`, I will analyze the diff against the Orchestrator's Rulings (A) and (C), the Governing Laws, and the specific attack vectors provided.

### Findings

#### <critical>
**1. `nv_order` uses stale `dropped`/`doomed` state in the value-loss branch (Attack d)**
*   **File:** `pipeline/package.py` (in `build()`, value-loss branch, approx. line 274 in diff context)
*   **Scenario:**
    1.  A line-up is formed.
    2.  The takeaway fails its value verdict (Ruling 91).
    3.  The code calls `nv_order(angle, segs, med, dropped)`.
    4.  `nv_order` iterates `angle["moments"]` to find a candidate clip to add. It checks `if ... mid in dropped or mid in doomed ...`.
    5.  **The Bug:** At this point in the `build()` loop, `dropped` and `doomed` reflect the state *before* the current line-up's specific failures were processed. However, `nv_order` is a pure function of its inputs. The critical issue is whether the *decision* to skip the rewrite (because `nv_plan["order"] is not None`) matches the *execution* in `no_voice()`.
    6.  In the diff, the value-loss branch does:
        ```python
        nv_plan = nv_order(angle, segs, med, dropped)
        if nv_plan["order"] is not None:
            v_novoice = val
            break
        ```
    7.  Later, `no_voice()` is called with the *same* `dropped` and `doomed` (which haven't changed between the check and the call, as no other code runs in between).
    8.  **However**, look at `nv_order`'s logic for adding a clip:
        ```python
        for mid in angle["moments"]:
            m = cleared.get(mid)
            if m is None or m in segs or mid in dropped or mid in doomed or ...
        ```
        If `nv_order` finds a valid `mid` and returns `order=cand`, the `break` happens.
        Then `no_voice` is called. Inside `no_voice`, it calls `nv_order` *again* (line 176 in diff: `plan = nv_order(angle, segs, med, dropped)`).
        Since `nv_order` is deterministic and inputs are identical, it returns the same `plan`.
        **Wait**, there is a subtle state mutation risk. Does `no_voice` modify `dropped` or `doomed`? No, it takes them as read-only.
        **BUT**, does the *first* call to `nv_order` in the value-loss branch have access to the correct `med`?
        The value-loss branch passes `med` (the current line-up's medley verdict).
        `nv_order` checks `if med.get("measured") is not True or med.get("flagged") != []: return ... why_not ...`.
        If the current line-up's clips *already* failed the medley check (e.g., a join was flagged), `nv_order` returns `order=None`.
        If `order=None`, the code proceeds to `if len(v_lost) > 1: ... break` or `v_redo = True`.
        This seems consistent.

    **Let's look closer at Attack (d): "Is nv_order() deterministic and identical between the in-loop decision and the post-loop no_voice() call"**
    The in-loop decision is:
    ```python
    nv_plan = nv_order(angle, segs, med, dropped)
    if nv_plan["order"] is not None:
        v_novoice = val
        break
    ```
    The post-loop call is inside `no_voice`:
    ```python
    plan = nv_order(angle, segs, med, dropped)
    ```
    The inputs `angle`, `segs`, `med`, `dropped` are the same.
    **However**, `nv_order` depends on `cleared`, `doomed`, `held_map`, `pos`.
    `pos` is computed inside `nv_order` from `angle["moments"]`.
    `cleared` is a dict in `build` scope.
    `doomed` is a set in `build` scope.
    `held_map` is a dict in `build` scope.
    
    **Is there a case where `nv_order` returns `order` in the check, but `no_voice` fails?**
    If `nv_order` returns `order`, `no_voice` proceeds to:
    ```python
    if added is not None:
        ok2, nv_med = medley(router, order, ctx, ...)
        if not ok2 or nv_med["flagged"]:
            note["why_not"] = "fails on the clips alone"
            return None
    ```
    This is a *new* medley call. The initial `nv_order` check only verified that a *candidate* exists based on duration and rules. It did *not* verify that the new line-up passes the medley gate.
    The in-loop check `if nv_plan["order"] is not None: break` assumes that if a candidate exists, we *should* go to `no_voice`.
    If `no_voice` then fails because the *new* medley check fails, it returns `None`.
    The `build` loop then continues? No, `no_voice` is called *after* the loop or *inside* the loop?
    Looking at the diff structure:
    The value-loss logic is inside the `for` loop over takeaways/angles.
    If `break` is hit, the loop ends.
    Then `no_voice` is called?
    Actually, the diff shows `no_voice` is a nested function.
    The value-loss branch sets `v_novoice = val` and `break`s.
    After the loop, there is likely a check `if v_novoice: ... no_voice(...)`.
    If `no_voice` returns `None` (because the added clip's medley failed), the line-up ends.
    This matches the te

## CLAUDE'S CYCLE 1 CONSENSUS
# Audit 0734 (the orchestrator's 07:30 rulings (A) and (C)), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes, three <medium>.
- qwen3.8-27b: SHIP yes with conditions. Its <critical> and <high> each resolve inside its own text: "Since nv_order is
  deterministic and inputs are identical, it returns the same plan"; "The extraction seems behavior-preserving".
- glm-5.3-flash: SHIP yes with conditions, all findings <medium>.

No defect that could ship a wrong pin. Upper-bound cost: about $0.37 ($0.091 + $0.123 + $0.158), outside
SPEND_LY.json.

## Implemented

- qwen condition 3: test the added-clip search against a DOOMED clip.
  - test_a_doomed_clip_is_never_the_added_clip: z fails exclusion in angle 1's line-up, which makes it doomed for the
    whole build.
  - Angle 2's takeaway then loses its value verdict on 39 s of clips. nv_order skips z, no no-voice line-up exists,
    and ruling 91's one rewrite is used. z never comes back.
  - Mutation M21 (drop "mid in doomed" from nv_order) is killed by it. The mutation check: 16 of 16 killed.

## glm's conditions, resolved from the code

- (1) "Are fid / cx always bound at the fixed-caption check?" Yes. In no_voice, `fid, cx = paid_gates(...)` runs
  unconditionally inside the `with` block. Every earlier exit (the cheap gate, the clips' own gates) returns None.
  - So when `fixed = None` and the check below it run, both are bound.
  - The (C) tests execute that path: a caption failing its cheap gates, a caption failing its verdict, a failing title.
- (2) "Does any other module import the removed no_voice_fits?" No. grep over the scratch copy (pipeline, tests) and
  over the main tree's pipeline and scripts finds no reference.

## Refuted, with evidence from the code

- grok <medium> 1 / glm (b): "the extraction of fixed_caption_gates may change ruling 65's voiced path".
  - rewrite_alone's build_pk was assemble_medley(order, by_id, dict(fields, **{slot: line}), ctx,
    f"{pk.get('vo_kind')}; {why}") with slot "caption", plus p["medley"] = pk.get("medley"). The helper makes exactly
    that.
  - a_use(pk3) is {sg["label"]: a_by[sg["moment_id"]] for sg in pk3["segments"]}, the helper's dict.
  - man's channels come from pk (before) and pk3 (now): the same segments.
  - Existing tests run the voiced path through the helper: TestRuling65Caption's fixed-caption tests and ruling 66's
    caption case. All pass, and M19 (drop caption_fallback in the helper) kills 4 tests, ruling 65's among them.
- grok <medium> 2: "no_voice passes cleared as by_id". no_voice already assembled its package with cleared as by_id,
  and every clip in the order comes from it: nv_order picks from cleared, and segs is a line-up of cleared moments.
- grok <medium> 3: "where does pk['no_voice']['added_clip'] come from". no_voice's fields carry "no_voice":
  {"why", "added_clip": added, "lineup_before", ...}, unchanged code. assemble_medley copies it to pk["no_voice"].
- qwen condition 1, "seed 7 in fixed_caption_gates' context c

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0734/C2_STEP.diff (510 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index f7f2d5a..58fa458 100644
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
 105 | @@ -2624,53 +2631,61 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
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
 165 | +    def no_voice(angle, segs, med, last, exception, dropped, rec, ai, n_lineup, value=None):
 166 | +        """THE NO-VOICE SHAPE: the package ships with NO VO line, clips back to back and the sign-off; it is not
 167 | +        dropped. Ruling 3 (22:40): the takeaway failed its gates twice; RULING 91 (value = the value verdict the
 168 | +        takeaway lost): its value verdict said no. The orchestrator's 07:30 ruling (A): "one shape whatever removed the
 169 | +        takeaway": the line-up is nv_order's (its own clips, or the added clip when the seconds need it); a line-up
 170 | +        with an added clip is judged on the clips alone again, and every clip gate runs on every clip. The title and
 171 | +        caption are the latest write's and go through every gate again. 07:30 (C): when ONLY the caption fails (its
 172 | +        cheap gates, or its verdict with context integrity passing: ruling 65's own trigger), ruling 65 (b)'s fixed
 173 | +        caption is used, as there (fixed_caption_gates, caption_fallback true); a failing title still holds (65 c).
 174 | +        The record names the ruling and, for 91, carries the verdict. -> a package, or None (rec["no_voice"] why)."""
 175 | +        rec["no_voice"] = note = {"tried": True, "ruling": 3 if value is None else 91}
 176 | +        plan = nv_order(angle, segs, med, dropped)
 177 | +        if plan["registered_skipped"]:
 178 | +            note["registered_skipped"] = plan["registered_skipped"]
 179 | +        if plan["order"] is None:
 180 | +            note["why_not"] = plan["why_not"]
 181 |              return None
 182 | -        if content < nv_lo:                                  # "the packager may add a clip"
 183 | -            chans = {m["channel_id"] for m in segs}
 184 | -            for mid in angle["moments"]:
 185 | -                m = cleared.get(mid)
 186 | -                if m is None or m in segs or mid in dropped or mid in doomed or m["channel_id"] in chans or \
 187 | -                        not (m.get("eligibility") or {}).get("clip", {}).get("ok"):
 188 | -                    continue
 189 | -                cand = [segs[0]] + sorted(segs[1:] + [m], key=lambda x: pos.get(x["moment_id"], 99))
 190 | -                if len(cand) - 1 > LY_CLIPS[1] or [x for x in cand[1:-1] if x["duration_s"] < SHORT_CLIP_S] or \
 191 | -                        sum("price_prediction" in x.get("risk", []) for x in cand) > PRICE_PREDICTIONS_MAX or \
 192 | -                        sum(bool(x.get("trimmed_leading")) for x in cand) > TRIMMED_PER_LINEUP_MAX or \
 193 | -                        not nv_lo <= sum(x["duration_s"] for x in cand) <= nv_hi:
 194 | -                    continue
 195 | -                if tuple(x["moment_id"] for x in cand) in held_map:   # ruling 66: the registry's, never this search's
 196 | -                    note.setdefault("registered_skipped", []).append(held_map[tuple(x["moment_id"] for x in cand)]["key"])
 197 | -                    continue
 198 | -                order, added = cand, mid
 199 | -                break
 200 | -            if added is None:
 201 | -                note["why_not"] = (f"{content:.1f} s of clips and no one clip of the angle lands {nv_lo:.1f}-{nv_hi:.1f} s"
 202 | -                                   + (f" (ruling 66: {note['registered_skipped']} left to the registry)"
 203 | -                                      if note.get("registered_skipped") else ""))
 204 | -                return None
 205 | +        order, added, nv_med = plan["order"], plan["added"], med
 206 | +        if added is not None:                                # its new line-up, judged on the clips alone again
 207 |              ok2, nv_med = medley(router, order, ctx, writers_v, seed=50 + n_lineup + 10 * ai, writer_family=writers_f)
 208 |              note["medley"] = nv_med
 209 |              if not ok2 or nv_med["flagged"]:
 210 | @@ -2681,8 +2696,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 211 |              ("ruling 91: the takeaway did not earn its place (its value verdict: " +
 212 |               (", ".join(f"{k} {value.get(k)}" for k in ("adds", "no_restate", "missed", "short"))
 213 |                if value.get("measured") else "no verdict") +
 214 | -             f"; {str(value.get('why') or '')[:200]}); the line-up's own clips meet the seconds, so L-y's no-voice "
 215 | -             f"shape ships them back to back with the sign-off only")
 216 | +             f"; {str(value.get('why') or '')[:200]}); L-y's no-voice shape (one shape, 07:30 (A)) ships the clips back "
 217 | +             f"to back with the sign-off only" + (f", one clip added ({added})" if added else ""))
 218 |          fields = {"takeaway": None, "bridge": None, "bridge_after": None, "title": last["title"],
 219 |                    "caption": last["caption"], "type": "moments", "angle": angle["angle"], "style": "medley, no voice",
 220 |                    "supply_exception": exception,
 221 | @@ -2710,7 +2725,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 222 |          pk = assemble_medley([m["moment_id"] for m in order], cleared, fields, ctx, "medley (L-y), no voice")
 223 |          pk["medley"] = nv_med
 224 |          cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 225 | -        if cheap:
 226 | +        if cheap and lone_slot(cheap) != "caption":          # 07:30 (C): only the caption failing alone goes on
 227 |              note["why_not"] = f"cheap gates: {sorted({v['rule'] for v in cheap})}"
 228 |              note["violations"] = cheap
 229 |              return None
 230 | @@ -2723,10 +2738,23 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 231 |                  note["why_not"] = "a clip fails exclusion, the second pass or CUTTABLE"
 232 |                  return None
 233 |              fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, nv_pool)
 234 | -        if not fid["ok"] or not cx["ok"]:
 235 | -            note["why_not"] = "the title / caption fail VO fidelity or context integrity"
 236 | -            note["violations"] = fid["violations"] + cx["violations"]
 237 | -            return None
 238 | +        fixed = None
 239 | +        if cheap or not fid["ok"] or not cx["ok"]:
 240 | +            if not (cx["ok"] and fid.get("measured") and lone_slot(cheap + fid["violations"]) == "caption"):
 241 | +                note["why_not"] = "the title / caption fail VO fidelity or context integrity" + \
 242 | +                    (f" (cheap gates: {sorted({v['rule'] for v in cheap})})" if cheap else "")
 243 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 244 | +                return None
 245 | +            refused = [{k: v.get(k) for k in ("rule", "detail")} for v in cheap + fid["violations"]]
 246 | +            pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), fixed = fixed_caption_gates(   # 07:30 (C): ruling 65 (b)
 247 | +                router, pk, fields, fid, order, cleared, ctx, a_by, sources, levels, writers_v, writers_f,
 248 | +                "the fixed caption on a no-voice path (07:30 (C), ruling 65 b)")
 249 | +            note["caption_fallback"] = {"refused": refused, "written": fields["caption"]["text"],
 250 | +                                        "fixed": fixed["text"]}
 251 | +            if cheap or not fid["ok"] or not cx["ok"]:
 252 | +                note["why_not"] = "the fixed caption (07:30 (C), ruling 65 b) did not pass its gates"
 253 | +                note["violations"] = cheap + fid["violations"] + cx["violations"]
 254 | +                return None
 255 |          coh = dict(nv_med, vo_point=None,
 256 |                     note=f"no VO line: the clips-alone verdict is the coherence verdict (ruling {note['ruling']})")
 257 |          a_lab = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 258 | @@ -2741,7 +2769,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 259 |          if problems:
 260 |              note["why_not"] = f"a required gate is not exactly PASS: {problems}"
 261 |              return None
 262 | -        pk["models"] = {"angle": angle_reply.backend, "writer": "the latest write's title and caption",
 263 | +        pk["models"] = {"angle": angle_reply.backend,
 264 | +                        "writer": "the latest write's title and caption" if fixed is None else
 265 | +                                  "the latest write's title; the caption is code's fixed line (07:30 (C), ruling 65 b)",
 266 |                          "medley": nv_med.get("backend"), "fidelity_verdict": fid.get("backend"),
 267 |                          "context": cx.get("backends"), "coherence": nv_med.get("backend")}
 268 |          pk["checks"] = {"fidelity": fid, "context": cx, "coherence": coh, "medley": nv_med}
 269 | @@ -3077,13 +3107,13 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 270 |                                 "detail": (f"{answers}: {val.get('why')}" if val.get("measured") else
 271 |                                            f"no clear yes ({val.get('why')})")[:300]}
 272 |                          t_refused += [ref] if ref not in t_refused else []      # what its one rewrite is told
 273 | -                        if no_voice_fits(segs, med):       # its OWN clips meet the seconds: L-y's no-voice shape
 274 | +                        nv_plan = nv_order(angle, segs, med, dropped)          # 07:30 (A): the ONE no-voice shape,
 275 | +                        if nv_plan["order"] is not None:   # its own clips or the added clip: no_voice() below
 276 |                              v_novoice = val
 277 |                              break
 278 |                          if len(v_lost) > 1:                # its one rewrite did not earn its place either
 279 |                              rec["why"] = ("ruling 91: the takeaway did not earn its place, nor did its one rewrite, "
 280 | -                                          "and the line-up's own clips do not meet the no-voice seconds "
 281 | -                                          f"({sum(m['duration_s'] for m in segs):.1f} s of clips)")
 282 | +                                          f"and no no-voice line-up exists ({nv_plan['why_not']})")[:500]
 283 |                              break
 284 |                          v_redo = True                      # ONE rewrite of the takeaway alone, told why
 285 |                          last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 286 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 287 | index ed2b1e3..7f3c518 100644
 288 | --- a/tests/package/test_medley.py
 289 | +++ b/tests/package/test_medley.py
 290 | @@ -530,10 +530,11 @@ class Rig:
 291 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 292 |                   trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 293 |                   cached=False, candidate=None, visuals=None, registered=None, lock_check=None, values=None,
 294 | -                 real_value=False):
 295 | +                 real_value=False, caption=None):
 296 |          import providers as P
 297 |          self.values, self.value_calls = list(values or []), []   # ruling 91: the value verdicts' answers, in order
 298 |          self.real_value = real_value                       # ruling 91: package.takeaway_value itself, on the router
 299 | +        self.caption = caption or "nobody bends these rules"   # 07:30 (C): a caption that fails its own gates
 300 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 301 |          self.takeaways, self.spend = list(takeaways or []), spend
 302 |          self.uncuttable, self.excluded, self.no_hook = set(uncuttable), set(excluded), set(no_hook)
 303 | @@ -625,7 +626,7 @@ class Rig:
 304 |          fields = {"takeaway": {"text": self.takeaways.pop(0) if self.takeaways else self.LINE, "cites": []}, "bridge": b,
 305 |                    "bridge_after": join[0] if join is not None and b is not None else None,
 306 |                    "title": {"text": "Nobody bends the rules", "cites": []},
 307 | -                  "caption": {"text": "nobody bends these rules", "cites": []},
 308 | +                  "caption": {"text": self.caption, "cites": []},
 309 |                    "type": "moments", "angle": angle_["angle"], "style": "medley", "takeaway_budget": [10, 30]}
 310 |          return self.P.Reply("{}", self.write_from[0], self.write_from[1], family=self.write_from[2]), fields
 311 |  
 312 | @@ -3261,17 +3262,64 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 313 |          self.assertEqual([x["text"] for x in tried["value_lost"]], [Rig.LINE])
 314 |          self.assertEqual(tried["result"], "PACKAGE")
 315 |  
 316 | -    def test_a_second_loss_ends_the_line_up_and_never_adds_a_clip(self):
 317 | -        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # ruling 3 would add z (52 s)
 318 | -        rig = Rig(ms, ["h", "x", "y", "z"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 319 | +    def test_a_lost_takeaway_takes_the_one_no_voice_shape_with_the_added_clip(self):
 320 | +        """The orchestrator's 07:30 ruling (A): "the no-voice shape is one shape whatever removed the takeaway (two
 321 | +        failed writes, or the value verdict's no): clips back to back, the sign-off, and the added clip when the seconds
 322 | +        need it, each added clip passing every clip gate and the joins as usual." No rewrite is spent."""
 323 | +        ms = self.SHORT + [pm("z", "D", 13.0)]                                    # 39 s + z = 52 s with no VO line
 324 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED * 2, [None], values=[{"adds": "no", "why": "it restates"}])
 325 | +        out = rig.run()
 326 | +        pk = out["package"]
 327 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y", "z"])
 328 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 329 | +        self.assertIn("one clip added (z)", pk["no_voice"]["why"])
 330 | +        self.assertEqual(pk["no_voice"]["value"]["adds"], "no")
 331 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])          # the new line-up judged on the clips alone
 332 | +        self.assertEqual((len(rig.write_calls), len(rig.value_calls)), (1, 1))  # no rewrite of the takeaway
 333 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 334 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 335 | +        self.assertNotIn("takeaway_value", pk["gates"])
 336 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 337 | +        self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": []})
 338 | +
 339 | +    def test_a_failed_no_voice_line_up_ends_the_line_up_without_a_rewrite(self):
 340 | +        """As on ruling 3's path: the added clip's line-up fails the clips-alone verdict, so there is no package, and
 341 | +        the takeaway is not rewritten (a no-voice line-up existed)."""
 342 | +        ms = self.SHORT + [pm("z", "D", 13.0)]
 343 | +        rig = Rig(ms, ["h", "x", "y", "z"], self.MED + [(False, [], {"clip_03": 2}, Rig.LINE)], [None],
 344 | +                  values=[{"adds": "no"}])
 345 | +        out = rig.run()
 346 | +        self.assertIsNone(out["package"])
 347 | +        self.assertEqual(len(rig.value_calls), 1)
 348 | +        self.assertIn("ruling 91", out["tried"][0]["why"])
 349 | +        self.assertIn("fails on the clips alone", out["tried"][0]["why"])
 350 | +
 351 | +    def test_a_doomed_clip_is_never_the_added_clip(self):
 352 | +        """Audit 0734 C1 (qwen's condition): z fails exclusion in angle 1's line-up, so it is doomed for the whole build.
 353 | +        Angle 2's takeaway then loses its value verdict on 39 s of clips: nv_order skips z, no no-voice line-up exists,
 354 | +        and ruling 91's one rewrite is used instead."""
 355 | +        ms = self.SHORT + [pm("z", "D", 13.0)]
 356 | +        rig = Rig(ms, [["h", "z", "y"], ["h", "x", "y", "z"]], self.MED * 2, [None, None], excluded={"z"},
 357 | +                  lines=[{"takeaway": {"text": self.NEW, "cites": []}}], values=[{"adds": "no"}])
 358 | +        out = rig.run()
 359 | +        pk = out["package"]
 360 | +        self.assertIn("'z': 'exclusion'", out["tried"][0]["why"])                # doomed in angle 1
 361 | +        self.assertEqual([s["moment_id"] for s in pk["segments"]], ["h", "x", "y"])   # never added back
 362 | +        self.assertNotIn("no_voice", out["tried"][-1])
 363 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "takeaway"), self.NEW)
 364 | +        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])
 365 | +
 366 | +    def test_a_second_loss_ends_the_line_up_when_no_no_voice_line_up_exists(self):
 367 | +        """No clip of the angle can be added (h, x, y are all it has), so ruling 91's one rewrite is used; its loss
 368 | +        ends the line-up."""
 369 | +        rig = Rig(self.SHORT, ["h", "x", "y"], self.MED, [None], lines=[{"takeaway": {"text": self.NEW, "cites": []}}],
 370 |                    values=[{"adds": "no"}, {"missed": "no"}])
 371 |          out = rig.run()
 372 |          self.assertIsNone(out["package"])
 373 |          self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # one rewrite, no more
 374 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 375 |          self.assertIn("nor did its one rewrite", out["tried"][0]["why"])
 376 | -        self.assertNotIn("no_voice", out["tried"][0])                            # never the no-voice shape with z
 377 | -        self.assertEqual(rig.medley_calls, [["h", "x", "y"]])
 378 | +        self.assertIn("no no-voice line-up exists", out["tried"][0]["why"])
 379 | +        self.assertNotIn("no_voice", out["tried"][0])
 380 |          self.assertIn("ruling 91", out["why_none"])
 381 |  
 382 |      def test_no_verdict_is_a_loss(self):
 383 | @@ -3294,18 +3342,115 @@ class TestRuling91MedleyHalf(unittest.TestCase):
 384 |          self.assertEqual(out["package"]["no_voice"]["added_clip"], "z")          # ruling 3 may still add a clip
 385 |          self.assertNotIn("value", out["package"]["no_voice"])
 386 |  
 387 | -    def test_a_value_loss_never_counts_toward_ruling_3s_two_failures(self):
 388 | -        """One value loss, one ordinary failure (its rewrite breaks house style), then a second value loss: the
 389 | -        takeaway failed its OTHER gates once, so ruling 3's no-voice (which would add z) is not reached."""
 390 | -        bad = "Ultimately nobody bends the rules."                                # house style: the opener
 391 | -        rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 392 | -                  takeaways=[Rig.LINE, self.NEW], lines=[{"takeaway": {"text": bad, "cites": []}}],
 393 | -                  values=[{"adds": "no"}, {"adds": "no"}])
 394 | -        out = rig.run()
 395 | +    @staticmethod
 396 | +    def contexts_pass():
 397 | +        """context_integrity stubbed to a measured pass (the fixed caption's own context run calls it directly);
 398 | +        returns the restore function."""
 399 | +        import context_integrity as CI
 400 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 401 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 402 | +                                             "backends": {"B": "xai", "C": "xai"}}
 403 | +        CI.contexts_from_sources = lambda *a, **k: {}
 404 | +
 405 | +        def restore():
 406 | +            CI.check_contexts, CI.contexts_from_sources = saved
 407 | +        return restore
 408 | +
 409 | +    UPPER = "Nobody Bends These Rules."                           # house style: a caption is all lowercase
 410 | +    FIXED = "nobody bends the rules\na / b / c"                   # ruling 65 (b): the title lowercase, then the shows
 411 | +
 412 | +    def test_c_a_no_voice_caption_that_fails_its_cheap_gates_becomes_the_fixed_caption(self):
 413 | +        """The orchestrator's 07:30 ruling (C): "on a no-voice path, when only the caption fails its gates, ruling 65
 414 | +        (b)'s fixed caption is used and the line-up goes on (caption_fallback: true, as there)."""
 415 | +        restore = self.contexts_pass()
 416 | +        try:
 417 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 418 | +            out = rig.run()
 419 | +        finally:
 420 | +            restore()
 421 | +        pk = out["package"]
 422 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 91)")
 423 | +        self.assertTrue(pk["caption_fallback"])
 424 | +        self.assertEqual(pk["caption"], self.FIXED)
 425 | +        self.assertEqual(next(x["text"] for x in pk["lines"] if x["slot"] == "caption"), self.FIXED)
 426 | +        self.assertEqual(pk["title"], "Nobody bends the rules")                  # the title as written and gated
 427 | +        cf = out["tried"][0]["no_voice"]["caption_fallback"]
 428 | +        self.assertEqual((cf["written"], cf["fixed"]), (self.UPPER, self.FIXED))
 429 | +        self.assertTrue(cf["refused"])
 430 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 431 | +        self.assertIn("ruling 65 b", pk["checks"]["fidelity"]["backend"])        # no model judged the fixed line
 432 | +        mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 433 | +        self.assertTrue(mp["caption_fallback"])
 434 | +        self.assertEqual(mp["caption"], self.FIXED)
 435 | +
 436 | +    def test_c_a_no_voice_caption_that_fails_its_verdict_becomes_the_fixed_caption(self):
 437 | +        restore = self.contexts_pass()
 438 | +        try:
 439 | +            bad = TestRuling66Amended().failing("caption", "it says the clips agree", "VERDICT_NO")
 440 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[bad])
 441 | +            out = rig.run()
 442 | +        finally:
 443 | +            restore()
 444 | +        pk = out["package"]
 445 | +        self.assertTrue(pk["caption_fallback"])
 446 | +        self.assertEqual(pk["caption"], self.FIXED)
 447 | +        self.assertTrue(all(g["status"] == "PASS" for g in pk["gates"].values()), pk["gates"])
 448 | +        self.assertEqual(out["tried"][0]["no_voice"]["caption_fallback"]["refused"][0]["rule"], "VERDICT_NO")
 449 | +
 450 | +    def test_c_a_failing_title_still_holds_and_so_do_a_title_and_caption_together(self):
 451 | +        """"The title keeps ruling 65 (c)": no fixed title. A title failing alone, or with the caption, holds."""
 452 | +        restore = self.contexts_pass()
 453 | +        try:
 454 | +            title_bad = TestRuling66Amended().failing("title", "it names no show", "VERDICT_NO")
 455 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad])
 456 | +            out = rig.run()
 457 | +            self.assertIsNone(out["package"])
 458 | +            self.assertIn("title / caption fail", out["tried"][0]["no_voice"]["why_not"])
 459 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 460 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], fids=[title_bad],
 461 | +                      caption=self.UPPER)                                       # both lines fail: no lone caption
 462 | +            out = rig.run()
 463 | +            self.assertIsNone(out["package"])
 464 | +            self.assertNotIn("caption_fallback", out["tried"][0]["no_voice"])
 465 | +        finally:
 466 | +            restore()
 467 | +
 468 | +    def test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends(self):
 469 | +        """As there (ruling 65 b): the fixed line has no model verdict, but context integrity on the package as it will
 470 | +        be sealed still decides. A failing run ends the line-up; nothing ships unchecked."""
 471 | +        import context_integrity as CI
 472 | +        saved = (CI.check_contexts, CI.contexts_from_sources)
 473 | +        CI.check_contexts = lambda *a, **k: {"ok": False, "violations": [{"rule": "STRONGER", "segment": "hook",
 474 | +                                                                          "detail": "x"}], "measured": True,
 475 | +                                             "replayed": False, "backends": {"B": "xai", "C": "xai"}}
 476 | +        CI.contexts_from_sources = lambda *a, **k: {}
 477 | +        try:
 478 | +            rig = Rig(self.FITS, ["h", "x", "y"], self.MED, [None], values=[{"adds": "no"}], caption=self.UPPER)
 479 | +            out = rig.run()
 480 | +        finally:
 481 | +            CI.check_contexts, CI.contexts_from_sources = saved
 482 |          self.assertIsNone(out["package"])
 483 | -        self.assertEqual([c["line"] for c in rig.value_calls], [Rig.LINE, self.NEW])   # the bad line never reached it
 484 | -        self.assertNotIn("no_voice", out["tried"][0])
 485 | -        self.assertIn("ruling 91", out["tried"][0]["why"])
 486 | +        nv = out["tried"][0]["no_voice"]
 487 | +        self.assertIn("the fixed caption", nv["why_not"])
 488 | +        self.assertEqual(nv["caption_fallback"]["fixed"], self.FIXED)
 489 | +
 490 | +    def test_c_ruling_3s_no_voice_path_takes_the_fixed_caption_too(self):
 491 | +        """(C) covers either no-voice path: the takeaway failed its gates twice (ruling 3), clip z is added, and the
 492 | +        latest write's caption, failing alone, becomes the fixed line."""
 493 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 494 | +        restore = self.contexts_pass()
 495 | +        try:
 496 | +            rig = Rig(self.SHORT + [pm("z", "D", 13.0)], ["h", "x", "y", "z"], self.MED * 2, [None, None],
 497 | +                      takeaways=bad, caption=self.UPPER)
 498 | +            out = rig.run()
 499 | +        finally:
 500 | +            restore()
 501 | +        pk = out["package"]
 502 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")
 503 | +        self.assertEqual(pk["no_voice"]["added_clip"], "z")
 504 | +        self.assertTrue(pk["caption_fallback"])
 505 | +        self.assertEqual(pk["caption"], "nobody bends the rules\na / b / c / d")
 506 | +        self.assertEqual(rig.value_calls, [])                                  # house style refused both takeaways first
 507 |  
 508 |      def test_the_real_verdict_runs_inside_the_build_and_its_row_seals(self):
 509 |          """build() with package.takeaway_value itself (not the Rig's stub), only the router faked: a clear yes seals
 510 | 
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
