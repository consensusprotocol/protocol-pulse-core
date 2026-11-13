# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1300
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 209 s finish=stop usage in 14607 / out 5517 usd~0.127 (upper-bound price)

# Audit: pp-selectid-1300 — RULING 65 (caption never kills a package) + 12:00 budget

Scope: I reviewed only the diff (package.py, package_pin.py, test_medley.py) against the ruling text and the stated readings. Where the diff references helpers I cannot see (`_lineup_block`, `assemble_medley`, `cheap_checks` internals, `VF.check_deterministic`, `CI.check_contexts`), I flag assumptions rather than assert.

---

## P0 findings

None. I could not construct a scenario from the diff alone where an ungated line is sealed or the ruling's shape is violated.

---

## P1 findings

**P1-1 — `merge_fid` drops the other lines' verdict `classes` when the first run's `verdict` is absent, and silently keeps a stale `ok` on the kept violations' parent.**
`package.py:94-99`. `ver = dict(v0, violations=..., claims=..., classes=dict(v0.get("classes") or {}, **{slot: ...}))`. If `fid` (the full-write record) has no `verdict` key at all (the diff's own fallback path constructs `one` with a `verdict` dict, so this is guarded there, but `merge_fid` is also called at line 161 with the hand-built `one` whose `verdict` has `classes: {"caption": [...]}` only), the merged `classes` for takeaway/title come from `v0` — correct — but in the fallback call at 158-160, `v0` is the *original failing* record's verdict, whose `violations` were the caption's. Those are correctly stripped by `keep()`. Verified consistent. However: `ver["ok"] = measured and not ver["violations"]` (line 99) — if `v0` carried a non-`violations` failure marker (e.g. `ok: False` with empty violations, which the record shape permits), the merged verdict reports `ok: True` while the original said otherwise. Concrete scenario: a fidelity record where the verdict failed for a reason recorded outside `violations` (I cannot confirm from the diff whether VF.check ever does this; if it never does, downgrade to P2). Same pattern at line 93: `det["ok"] = not det["violations"]` ignores `d0["ok"]`'s own value — a deterministic record that failed for a reason not in `violations` (e.g. `price_now_measured: False`, which the test fixture at line 300 shows is a *separate* key) would merge as `ok: True`. **Scenario:** `d0 = {"ok": False, "violations": [], "price_now_measured": False}` → merged `det["ok"] = True`, the package seals with an unmeasured price. The test at line 395-397 only covers `measured: False` at the top level, not inside `deterministic`. This is exactly the L-m/L-j "measured" concern.

**P1-2 — the title-hold path returns a `cx` record that was never computed for the held package, and `cheap` is recomputed but `dup`/`rt_ok`/`r4_res` come from it while the sealed package is the *old* `pk`.**
`package.py:150-152`. On the title hold, the function returns `(pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, ...), rec)`. The third element is a *literal* `{"ok": True, "violations": []}` — a context-integrity record with no `measured`, no `backend`, no `backends`. If the sealed inventory's context-integrity row reads this record (the caller unpacks `cheap, det, dup, rt_ok, r4_res` from the 4th element and `cx` is used for the gates), the row's evidence is thinner than a real run. I cannot see the inventory builder, so I cannot confirm whether it requires `measured`/`backend` on the cx record; if it does, the held line-up's record is not just failed-but-honest, it is *shape-deficient*. Flagging as P1 because the caller at line 213 then checks `not (fid["ok"] and cx["ok"])` — with the literal, `cx["ok"]` is `True`, so the hold's failure rests entirely on `fid["ok"]=False`. That is the ruling's intent (hold = the line-up stops), so behaviour is right; the record's provenance is the weakness. Say-so: uncertain whether the inventory cares.

**P1-3 — `rewrite_alone`'s success path does not re-check `cheap2` after the fidelity/context gates, but the fallback path's `cheap3` failures are only surfaced via `rec["why"]`, and the caller's break condition at 213-218 can seal a package whose `cheap` (the 5-tuple's first element) is non-empty.**
`package.py:213`: `if not (fid["ok"] and cx["ok"]) or cheap:` — after a *successful* rewrite, `cheap` was reassigned at line 209 from `cheap_t` (the rewrite's own cheap result). If the rewritten line passes fidelity and context but its cheap checks now fail (e.g. the new caption trips DUPLICATE or runtime), the condition catches it and breaks with `rec["why"]` = `rw.get("why")` — but `rw["why"]` is only set in the *except* branch (line 149). On the success path `rw` has no `why` key, so `rec["why"]` becomes `None`... no: line 214 reads `rw.get("why") if not rw.get("caption_fallback") else ...`. If `rw["passed"]` is True but `cheap` non-empty, `rw.get("caption_fallback")` is falsy, so `rec["why"] = rw.get("why")` = **None**, and the loop breaks with a `None` why. Then the caller's later logic (not in the diff) see

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 101 s finish=stop usage in 14556 / out 629 usd~0.089 (upper-bound price)

**P2: pipeline/package.py:74**  
lone_slot() correctly returns only when *every* violation shares a single slot ∈ {"caption","title"} (test at 376–380 confirms takeaway or mixed-slot cases stay on the old redo path).

**P2: pipeline/package.py:202**  
The guard `if cx["ok"] and fid.get("measured")` before calling lone_slot(...) plus the later `if not (fid["ok"] and cx["ok"]) or cheap:` after rewrite_alone() ensures a takeaway failure or unmeasured fidelity never takes the lone-write path (matches ruling 65 and test at 381–384).

**P2: pipeline/package.py:126**  
write_line() builds a *new* WRITE_LINE prompt that quotes the refused sentence + LINE_WHY reason and the gated takeaway/title; router.call("angle_write", …) therefore cannot hit an identical-prompt replay (explicitly satisfies the 12:52 ruling paragraph on replay trapping). writers_v.add(r.vendor) / writers_f.add(r.family) occurs before the subsequent VF.check, satisfying L-x for the line writer.

**P2: pipeline/package.py:158**  
fixed_caption() produces exactly the format required by ruling 65(b) and K2: gated title.lower() + "\n" + lowercase channel names joined by " / ", citing every clip. The fallback record supplies deterministic + "the fixed line: no fact" verdict class with no model verdict (K3). cheap3, house-style lint, and CI.check_contexts still run on the final pk3 bytes (L-j, L-t).

**P2: pipeline/package.py:90**  
merge_fid() retains the original fid's deterministic/verdict results for the other two lines, merges only the lone slot's violations/classes, requires measured on *both* runs, and annotates the backend with "(ruling 65)". The test at 387–397 verifies that an unmeasured second run forces ok=False (M12/L-j).

**P2: pipeline/package.py:175**  
medley() now surfaces cached=…; build() treats replayed *or* cached line-ups as free against the 8-line-up budget (12:00 note). Test at 400–403 confirms a cached clips-alone verdict costs 0 search lineups.

**P2: pipeline/package_pin.py:241 / tests/package/test_medley.py:354**  
caption_fallback flag is recorded outside the seal (like no_voice) and the test suite asserts the exact gate rows, house-style PASS on the fixed line, and that a title failing its second write is held with no package emitted. All six TestRuling65Caption cases pass; no path seals an ungated caption/title.

No P0/P1 findings. The diff introduces no new renderer/compositor/selector, changes no gate thresholds, keeps every required gate on the final bytes, and complies with every concrete clause of ruling 65 and the listed K1–K5 that can be verified from the patch alone.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 120 s finish=stop usage in 15937 / out 2764 usd~0.089 (upper-bound price)

# Audit: pp-selectid-1300 (Ruling 65)

## P0 Findings

**1. `pipeline/package.py` (approx. line 213-218 in diff): The "Fixed Caption" fallback can be sealed with failing gates.**
In `rewrite_alone`, if the model write for the caption fails (raising an exception or returning a failing verdict), the code falls through to the `fixed_caption` logic (lines 153-165). It constructs `pk3` with the fixed caption and runs `cheap3 = cheap_checks(...)`. However, it **does not check the result of `cheap3`** before returning `pk3`.
*   **Scenario:** The model write fails. The code generates the fixed caption. `cheap_checks` on this new package fails (e.g., due to a house style violation in the channel names, or a deterministic fidelity rule triggered by the specific title text). The code returns `pk3` (the package with the fixed caption) and `cheap3` (which contains violations).
*   **Consequence:** Back in the main loop (line 213), the check is `if not (fid["ok"] and cx["ok"]) or cheap:`. If `cheap3` has violations, `cheap` is truthy, so the loop breaks with `rec["why"]` set. **However**, look closely at the return value of `rewrite_alone` in the fallback path: it returns `pk3, fid3, cx3, cheap3, rec`.
    *   Wait, let's re-read the main loop logic at line 213:
        ```python
        if not (fid["ok"] and cx["ok"]) or cheap:
            rec["why"] = ...
            w_used = writes
            break
        ```
    *   If `cheap3` has violations, `cheap` is truthy. The loop breaks. The package `pk` is updated to `pk3` (line 204: `pk, fid, cx, cheap_t, rw = rewrite_alone(...)`).
    *   Does the loop *seal* the package? The `break` exits the `while` loop. The code after the loop (not shown in diff, but implied by "sealed inventory") likely checks `att["violations"]` or `rec["why"]`.
    *   **Crucial Check:** Does `att["violations"]` get updated with `cheap3`?
        *   Line 194: `att["violations"] = cheap + fid["violations"] + cx["violations"]` happens *before* `rewrite_alone`.
        *   Inside `rewrite_alone`, `att` is not modified.
        *   After `rewrite_alone` returns, `cheap` is updated to `cheap_t` (which is `cheap3`).
        *   But `att["violations"]` is **not** updated to include `cheap3`'s violations.
        *   If the downstream sealing logic relies on `att["violations"]` being empty to seal, it might seal a package where `cheap_checks` failed on the fixed caption, because `att["violations"]` still holds the *old* violations (which were only on the caption, and thus `lone_slot` was triggered).
        *   **Correction:** The `break` sets `rec["why"]`. If the sealing logic checks `rec["why"]` or `att["ok"]`, it might stop. But if it checks `att["violations"]` specifically, it sees the *old* violations.
        *   **More Critical:** Look at line 213 again. `if not (fid["ok"] and cx["ok"]) or cheap:`. If `cheap3` fails, we break. The package `pk` is now `pk3`. The `att` dict still has the *old* `violations`. If the final seal check is `if not att["violations"]: seal()`, it will seal `pk3` even though `cheap3` failed.
        *   **Verdict:** This is a **P0**. The fixed caption path does not update `att["violations"]` with the results of the gates run on the fixed caption. If the fixed caption fails `cheap_checks` (e.g., house style), the package may be sealed with a failing gate, violating Law 20/M2 (failed gate is a hard stop) and L-j (gates on bytes sent).

**2. `pipeline/package.py` (approx. line 158-160 in diff): The "Fixed Caption" verdict is hardcoded to `ok: True`.**
In the fallback path of `rewrite_alone`:
```python
one = {"deterministic": VF.check_deterministic(...),
       "verdict": {"ok": True, "violations": [], ...},
       ...}
```
The `verdict` is hardcoded to `ok: True`. The `deterministic` check is run, but its result is **not** checked for violations before merging.
*   **Scenario:** The fixed caption (title + channel names) triggers a deterministic fidelity violation (e.g., a number mismatch or a forbidden word in the channel name). `VF.check_deterministic` returns `ok: False`.
*   **Consequence:** `merge_fid` is called with `one` where `verdict.ok` is `True`. The merged `fid3` will have `verdict.ok` as `True` (assuming the other lines passed). The `deterministic` violations from `one` are merged into `det["violations"]`.
*   **Check:** `merge_fid` line 93: `det["ok"] = not det["violations"]`. So `fid3["deterministic"]["ok"]` will be `False`.
*   **Check:** `merge_fid` line 99: `ver["ok"] = measured and not ver["violations"]`. `ver["violations"]` comes from `v0` (old) and `v1` (new). `v1` is hardcoded to `[]`. So `ver["ok"]` remains `True`.
*   **Check:** `merge_fid` line 102: `ok=det["ok"] and ver["ok"]`. So `fid3["ok"]` will be `False`.
*   **Back to Main Loop (Line 213):** `if not (fid["ok"] and cx["ok"]) or cheap:`. `fid` is now `fid3`. `fid3["ok"]` is `False`. So the co

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1300 (RULING 65: a caption never kills a package): cycle 1 consensus

- **Run:**
  - grok: "SHIP: yes", no P0 or P1.
  - glm: "SHIP: yes with conditions", record-keeping P1s.
  - qwen: "SHIP: No", on a "P0" its own text re-grades.
- No P0 or P1 holds against the code. Nothing changes; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0: the fixed-caption path does not check its cheap gates before sealing, so a failing fixed line could be sealed | The caller checks them before anything is sealed. Right after rewrite_alone it sets `cheap, det, dup, rt_ok, r4_res = cheap_t` (the cheap checks on the package as it now stands), then `if not (fid["ok"] and cx["ok"]) or cheap:` records the why and breaks the line-up. The inventory is never built and nothing is sealed. The fixed line's own deterministic layer is merged into fid3 (merge_fid), so a deterministic failure there also makes fid3["ok"] False. qwen's own text: "This is not a P0 for sealing a bad package, because fid3["ok"] becomes False, triggering the break." |
| R2 | qwen P1: att["violations"] is stale after a successful rewrite, so the sealing logic will reject a valid package | att is the attempt's RECORD; nothing decides sealing from it. The inventory is built from the merged fid, dup / rt_ok / r4_res from the final cheap checks, the final cx, coherence, and style=HS.lint_lines(pk["lines"]) on the final package. to_pin reads only pk["gates"] and the package. The rewrite's own record (att["rewrite"]: refused, written, verdict, passed / fallback) is beside it. |
| R3 | glm P1-3: a rewrite that passes fidelity and context but fails the cheap checks breaks with why None | That state cannot occur. rewrite_alone runs the cheap checks on the new package BEFORE any verdict, and raises on a failure (`if cheap2[0]: raise ValueError("cheap gates: ...")`). A raise takes the caption to the fixed line, or holds the title with its why. A "passed" rewrite therefore always returns empty cheap results. |

## Recorded (no change)

| # | finding | why no change |
|---|---|---|
| G1 | glm P1-2: the title-hold path returns a literal context record ({"ok": True, ...}) | The hold breaks the line-up before any inventory is built, so that record is never sealed or gated. The hold rests on fid["ok"] False. That is the ruling's intent ("then hold"). |
| G2 | glm P1-1: merge_fid when the first record has no "verdict" key | Every record VF.check returns carries "verdict" (a dict, also on the unavailable path). The fallback's `one` carries one too. |
| G3 | glm P1-4: the line contract refuses extra keys | Intended: "Return ONLY this JSON object". A reply out of contract is rejected; for the caption it leads to the fixed line, for the title to a hold. |
| G4 | glm P1-5: replayed vs cached | Both are free (the 12:00 note): `total += 0 if med.get("replayed") or med.get("cached") else 1`. |
| G5 | glm P2s (the test rig's shapes; the fallback's m

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1300/C2_STEP.diff (409 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index ad2b892..94d6b2f 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -1479,7 +1479,7 @@ def medley(router, segs, ctx, writer_vendor, seed=7, writer_family=None):
   6 |      ok = own is not None and _line_ok(v["through_line"]) and min(v["clips"].values()) >= COHERENCE_MIN and \
   7 |          len(flagged) <= LY_MAX_BRIDGES
   8 |      return ok, dict(v, flagged=flagged, backend=r.backend, measured=True,
   9 | -                    replayed=bool(getattr(r, "replayed", False)))
  10 | +                    replayed=bool(getattr(r, "replayed", False)), cached=bool(getattr(r, "cached", False)))
  11 |  
  12 |  
  13 |  def last_clip_only(segs, med):
  14 | @@ -1590,6 +1590,156 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  15 |                     type="moments", angle=angle["angle"], style="medley", takeaway_budget=list(budget))
  16 |  
  17 |  
  18 | +WRITE_LINE = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  19 | +THE ANGLE (the point this video makes): "{angle}"
  20 | +The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
  21 | +in one conversation and never answer each other):
  22 | +
  23 | +{note}
  24 | +{lineup}
  25 | +
  26 | +The video's other lines are written and checked, and they stay exactly as they are:
  27 | +{kept}
  28 | +Your {slot} was refused: {refused}
  29 | +Write ONE new {slot} ({limit}) that carries the angle. It may say only what these clips themselves say (cite their
  30 | +ids) or your own commentary, which states no fact; never a claim the clips do not make. A line that names a show
  31 | +cites the clips it comes from.
  32 | +{style}
  33 | +Return ONLY this JSON object: {{"{slot}": {{"text": "...", "cites": []}}}}"""   # RULING 65: one line, alone
  34 | +LINE_WHY = {"VERDICT_NO": "the fact check found that the clips do not say it",
  35 | +            "VERDICT_UNCERTAIN": "the fact check could not find it in the clips",
  36 | +            "STYLE": "it breaks the house style"}
  37 | +LINE_LIMIT = {"caption": "at most 220 characters", "title": "at most 70 characters"}
  38 | +
  39 | +
  40 | +def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None):
  41 | +    """RULING 65: ONE more write for one line alone ("caption" or "title"): the angle, the line-up, the other lines kept
  42 | +    as gated, and the refused sentence(s) with why. A new prompt (WRITE_LINE), so a recorded reply is never replayed
  43 | +    into it. -> (reply, {"text", "cites"}); a reply out of contract raises (and is rejected)."""
  44 | +    from select_by_id import UNTRUSTED
  45 | +    from story_semantics import quote_data
  46 | +    q = lambda t, n: " ".join(quote_data(t, n).replace('"', "'").split())
  47 | +    kept = "\n".join(f'{s.upper()}: "{q(fields[s]["text"], 300)}"' for s in ("takeaway", "title", "caption")
  48 | +                     if s != slot and fields.get(s))
  49 | +    why = "; ".join(f'"{q(v.get("detail") or "", 200)}" ({LINE_WHY.get(v.get("rule"), v.get("rule"))})'
  50 | +                    for v in refused)
  51 | +    prompt = WRITE_LINE.format(angle=q(angle["angle"], 300), note=UNTRUSTED.replace("<sentences>", "the quotes"),
  52 | +                               lineup=_lineup_block(segs, ctx, a_by), kept=kept, slot=slot, refused=why,
  53 | +                               limit=LINE_LIMIT[slot], style=HS.PROMPT_RULES)
  54 | +    r = router.call("angle_write", prompt, 1500, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
  55 | +    try:
  56 | +        obj = json.loads(r.text.strip())
  57 | +        ids = [m["moment_id"] for m in segs]
  58 | +        ln = obj.get(slot) if isinstance(obj, dict) and set(obj) == {slot} else None
  59 | +        if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
  60 | +                not ln["text"].strip() or not isinstance(ln["cites"], list) or \
  61 | +                any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
  62 | +                len(ln["text"]) > (220 if slot == "caption" else 70):
  63 | +            raise ValueError(f"exactly {{'{slot}': {{'text', 'cites'}}}}, cites from the line-up's ids, "
  64 | +                             f"{LINE_LIMIT[slot]}")
  65 | +    except (ValueError, TypeError, AttributeError):
  66 | +        router.reject(r)
  67 | +        raise
  68 | +    return r, ln
  69 | +
  70 | +
  71 | +def lone_slot(violations):
  72 | +    """RULING 65: "caption" or "title" when EVERY violation is on that one line (the takeaway and the other line pass),
  73 | +    else None."""
  74 | +    slots = {v.get("slot") for v in violations}
  75 | +    return next(iter(slots)) if len(slots) == 1 and slots <= {"caption", "title"} else None
  76 | +
  77 | +
  78 | +def fixed_caption(fields, segs, ctx):
  79 | +    """RULING 65 (b): the caption that states no fact, written by code: the gated title in lowercase, a line break, then
  80 | +    the channel names in play order separated by ' / ', lowercase too (PBX's house style: a caption is all lowercase,
  81 | +    names too). It names every show, so it cites every clip."""
  82 | +    return {"text": fields["title"]["text"].strip().lower() + "\n" + " / ".join(_name(m, ctx).lower() for m in segs),
  83 | +            "cites": [m["moment_id"] for m in segs]}
  84 | +
  85 | +
  86 | +def merge_fid(fid, slot, one):
  87 | +    """RULING 65: the fidelity record after ONE line was replaced alone. The other lines keep their results as gated in
  88 | +    `fid` (whose only violations were on `slot`); the line's own come from `one` (its check, run on that line alone).
  89 | +    measured / replayed hold for both runs; the back-end names both."""
  90 | +    keep = lambda vs: [v for v in vs or [] if v.get("slot") != slot]
  91 | +    d0, d1 = fid["deterministic"], one["deterministic"]
  92 | +    det = dict(d0, violations=keep(d0["violations"]) + list(d1["violations"]))
  93 | +    det["ok"] = not det["violations"]
  94 | +    v0, v1 = fid.get("verdict") or {}, one.get("verdict") or {}
  95 | +    ver = dict(v0, violations=keep(v0.get("violations")) + list(v1.get("violations") or []),
  96 | +               claims=list(v0.get("claims") or []) + list(v1.get("claims") or []),
  97 | +               classes=dict(v0.get("classes") or {}, **{slot: (v1.get("classes") or {}).get(slot)}))
  98 | +    measured = bool(fid.get("measured")) and bool(one.get("measured"))
  99 | +    ver["ok"] = measured and not ver["violations"]
 100 | +    return dict(fid, deterministic=det, verdict=ver, violations=det["violations"] + ver["violations"],
 101 | +                ok=det["ok"] and ver["ok"], measured=measured, replayed=bool(fid.get("replayed") or one.get("replayed")),
 102 | +                backend=f"{fid.get('backend')}; the {slot} alone: {one.get('backend')} (ruling 65)")
 103 | +
 104 | +
 105 | +def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ctx, a_by, sources, levels, writers_v,
 106 | +                  writers_f, avoid_vendor=None, seed=7):
 107 | +    """RULING 65 (12:52): only `slot` ("caption" or "title") failed (`refused`: its violations); the takeaway and the
 108 | +    other line are kept as gated. ONE more write for that line alone (write_line), gated alone: the cheap checks on the
 109 | +    package with it (the deterministic fidelity layer and the house style), the blind fidelity verdict on that line
 110 | +    alone, and context integrity again on the package as it will be sealed (L-t: every audience text gated; L-j: the
 111 | +    gates on the bytes sent). If the caption's write fails any of it, the caption is the FIXED line (fixed_caption;
 112 | +    caption_fallback: true): code-written, no model, so no model verdict; its deterministic layer, the house style and
 113 | +    context integrity still run. A title that fails again is held (no fixed title without a ruling).
 114 | +    -> (pk, fid, cx, (cheap, det, dup, rt_ok, r4_res), record)."""
 115 | +    segs_v = fidelity_segments(pk, a_by)
 116 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": ctx.now.strftime("%Y-%m-%d")}
 117 | +    a_use = lambda p: {sg["label"]: a_by[sg["moment_id"]] for sg in p["segments"]}
 118 | +    order = [m["moment_id"] for m in segs]
 119 | +    rec = {"slot": slot, "refused": [{k: v.get(k) for k in ("rule", "detail")} for v in refused]}
 120 | +
 121 | +    def build_pk(line, why):
 122 | +        p = assemble_medley(order, by_id, dict(fields, **{slot: line}), ctx, f"{pk.get('vo_kind')}; {why}")
 123 | +        p["medley"] = pk.get("medley")
 124 | +        return p
 125 | +    try:
 126 | +        r, line = write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=seed,
 127 | +                             avoid_vendor=avoid_vendor)
 128 | +        rec.update(written=line["text"], writer=r.backend)
 129 | +        writers_v.add(r.vendor)                          # L-x: the line's verdict never comes from its writer
 130 | +        writers_f.add(r.family)
 131 | +        pk2 = build_pk(line, f"the {slot} rewritten alone (ruling 65 a)")
 132 | +        cheap2 = cheap_checks(pk2, a_by, levels, ctx.now)
 133 | +        if cheap2[0]:
 134 | +            raise ValueError("cheap gates: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in cheap2[0])[:300])
 135 | +        ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk2["lines"] if x["slot"] == slot]
 136 | +        one = VF.check(router, fidelity_segments(pk2, a_by), ln, writers_v, 7, man, levels, writers_f)
 137 | +        rec["verdict"] = {"ok": one["ok"], "violations": one["violations"], "backend": one.get("backend")}
 138 | +        if not one["ok"]:
 139 | +            raise ValueError("fidelity: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in one["violations"])[:300])
 140 | +        fid2 = merge_fid(fid, slot, one)
 141 | +        cx2 = CI.check_contexts(router, pk2, CI.contexts_from_sources(pk2, sources, ctx.now), writers_v, 7, a_use(pk2),
 142 | +                                writers_f, True)
 143 | +        if not (fid2["ok"] and cx2["ok"]):
 144 | +            raise ValueError("context integrity on the package with it: " +
 145 | +                             "; ".join(f"{v['rule']}" for v in cx2["violations"])[:200])
 146 | +        rec["passed"] = True
 147 | +        return pk2, fid2, cx2, cheap2, rec
 148 | +    except Exception as e:
 149 | +        rec.update(passed=False, why=f"{type(e).__name__}: {str(e)[:300]}")
 150 | +    if slot != "caption":                                # (c): a title that fails again is held
 151 | +        rec["why"] = f"the title failed alone twice: held (ruling 65 c): {rec['why']}"
 152 | +        return pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, a_by, levels, ctx.now), rec
 153 | +    line = fixed_caption(fields, segs, ctx)               # (b): the fixed caption, code-written, no model
 154 | +    pk3 = build_pk(line, "the fixed caption (ruling 65 b)")
 155 | +    pk3["caption_fallback"] = True
 156 | +    cheap3 = cheap_checks(pk3, a_by, levels, ctx.now)
 157 | +    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk3["lines"] if x["slot"] == "caption"]
 158 | +    one = {"deterministic": VF.check_deterministic(fidelity_segments(pk3, a_by), ln, man, levels),
 159 | +           "verdict": {"ok": True, "violations": [], "claims": [], "classes": {"caption": ["the fixed line: no fact"]}},
 160 | +           "measured": True, "replayed": False, "backend": "code, no model: the fixed caption (ruling 65 b)"}
 161 | +    fid3 = merge_fid(fid, "caption", one)
 162 | +    cx3 = CI.check_contexts(router, pk3, CI.contexts_from_sources(pk3, sources, ctx.now), writers_v, 7, a_use(pk3),
 163 | +                            writers_f, True)
 164 | +    rec.update(fallback=line["text"], caption_fallback=True)
 165 | +    return pk3, fid3, cx3, cheap3, rec
 166 | +
 167 | +
 168 |  def question_hook(segs):
 169 |      """Ruling 37: the hook ends on a question (its text ends with '?', the render's R1 test). Such a hook is allowed; the
 170 |      clips-alone verdict must find the join after it followable, since no bridge may follow a question."""
 171 | @@ -2191,7 +2341,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 172 |                      ok_m, med = medley(router, segs, ctx, writers_v, seed=7 + n_lineup + 10 * ai,
 173 |                                         writer_family=writers_f)
 174 |                      judged[key] = (ok_m, med)
 175 | -                    total += 0 if med.get("replayed") else 1    # 12:00: the budget counts JUDGED line-ups
 176 | +                    total += 0 if med.get("replayed") or med.get("cached") else 1   # 12:00: JUDGED line-ups
 177 |                  rec["medley"], rec["medley_ok"] = med, ok_m
 178 |                  labs_ = labels(len(segs))
 179 |                  bad_pairs |= {(segs[labs_.index(a)]["moment_id"], segs[labs_.index(b)]["moment_id"])
 180 | @@ -2341,7 +2491,7 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 181 |                          rec["why"] = f"exclusion / L-v 2 / CUTTABLE dropped {rec['lost_why']}: re-lined"
 182 |                          relined = True
 183 |                          break
 184 | -                    if cheap:
 185 | +                    if cheap and lone_slot(cheap) is None:     # ruling 65: a lone caption / title goes on
 186 |                          att["violations"] = cheap
 187 |                          take_failed += take["passed"] is False
 188 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 189 | @@ -2354,20 +2504,37 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 190 |                      fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 191 |                      out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 192 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 193 | -                    att["violations"] = fid["violations"] + cx["violations"]
 194 | +                    att["violations"] = cheap + fid["violations"] + cx["violations"]
 195 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 196 |                      log(f"    fidelity {'PASS' if fid['ok'] else 'FAIL'} (takeaway "
 197 |                          f"{'PASS' if take['passed'] else take['verdict_fail']}), context "
 198 |                          f"{'PASS' if cx['ok'] else 'FAIL'} ({time.time() - t0:.0f} s)")
 199 |                      take_failed += take["passed"] is False
 200 | -                    if not fid["ok"] or not cx["ok"]:
 201 | -                        if fid["ok"] and not framing:
 202 | +                    slot = lone_slot(cheap + fid["violations"]) if cx["ok"] and fid.get("measured") else None
 203 | +                    if slot:                                   # RULING 65: only the caption (or the title) fails
 204 | +                        pk, fid, cx, cheap_t, rw = rewrite_alone(
 205 | +                            router, slot, pk, fields, fid, [v for v in cheap + fid["violations"]], angle, segs, cleared,
 206 | +                            ctx, a_by, sources, levels, writers_v, writers_f, writer_avoid or None,
 207 | +                            seed=7 + w_used + 10 * ai + 100 * n_lineup)
 208 | +                        att["rewrite"] = rw
 209 | +                        cheap, det, dup, rt_ok, r4_res = cheap_t
 210 | +                        log(f"    the {slot} alone (ruling 65): " + ("PASS" if rw.get("passed") else
 211 | +                            "the fixed caption" if rw.get("caption_fallback") else "HELD") +
 212 | +                            f" ({time.time() - t0:.0f} s)")
 213 | +                        if not (fid["ok"] and cx["ok"]) or cheap:
 214 | +                            rec["why"] = rw.get("why") if not rw.get("caption_fallback") else \
 215 | +                                "the fixed caption did not pass its gates (ruling 65 b): " + "; ".join(
 216 | +                                    f"{v['rule']}" for v in cheap + fid["violations"] + cx["violations"])[:300]
 217 | +                            w_used = writes
 218 | +                            break
 219 | +                    if not fid["ok"] or not cx["ok"] or cheap:
 220 | +                        if fid["ok"] and not framing and not cheap:
 221 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 222 |                              w_used = writes
 223 |                              break
 224 | -                        extra = _redo(fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
 225 | -                                                            "detail": VO_FIX.get(v["rule"], v["detail"])}
 226 | -                                                           for v in framing])
 227 | +                        extra = _redo(cheap + fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
 228 | +                                                                    "detail": VO_FIX.get(v["rule"], v["detail"])}
 229 | +                                                                   for v in framing])
 230 |                          continue
 231 |                      att["exclusion"] = {mid: e for mid, (e, _) in got.items()}
 232 |                      att["second_pass"] = {mid: t for mid, (_, t) in got.items()}
 233 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 234 | index f2e4325..0573b1d 100644
 235 | --- a/pipeline/package_pin.py
 236 | +++ b/pipeline/package_pin.py
 237 | @@ -302,6 +302,7 @@ def to_pin(pk, run_name):
 238 |                                  "bridge": pk.get("bridge"),
 239 |                                  "supply_exception": pk.get("supply_exception"),
 240 |                                  "no_voice": pk.get("no_voice"),          # ruling 3 (22:40): why no VO line ships
 241 | +                                "caption_fallback": bool(pk.get("caption_fallback")),   # ruling 65 (b): a placeholder
 242 |                                  "gates": pk["gates"],
 243 |                                  **({"btc_screen": pk["btc_screen"]} if pk.get("btc_screen") is not None else {}),
 244 |                                  "checks": {"vo_fidelity_ok": True, "context_integrity_ok": True,
 245 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 246 | index c574b24..ea0699e 100644
 247 | --- a/tests/package/test_medley.py
 248 | +++ b/tests/package/test_medley.py
 249 | @@ -522,7 +522,8 @@ class Rig:
 250 |  
 251 |      def __init__(self, moments, angle_moments, medleys, writes, uncuttable=(), excluded=(), takeaways=None,
 252 |                   spend=None, no_hook=(), a_fail=None, unavailable=(), angle_from=None, write_from=None,
 253 | -                 trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None):
 254 | +                 trim_fail=(), hooks=None, hook_err=None, verdicts=None, follow_up=None, fids=None, lines=None,
 255 | +                 cached=False):
 256 |          import providers as P
 257 |          self.P, self.moments, self.medleys, self.writes = P, moments, list(medleys), list(writes)
 258 |          self.takeaways, self.spend = list(takeaways or []), spend
 259 | @@ -535,7 +536,9 @@ class Rig:
 260 |          self.screens, self.events, self.a_seen = [], [], []
 261 |          self.write_from = write_from or ("heimdall:deepseek", "heimdall", "deepseek")
 262 |          many = angle_moments if isinstance(angle_moments[0], list) else [angle_moments]
 263 | -        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}] + ([follow_up] if follow_up else []))
 264 | +        self.router = Canned(angle_write=[{"angles": [angle(a, a[0]) for a in many]}] + ([follow_up] if follow_up else [])
 265 | +                             + list(lines or []))                  # ruling 65: the replies for a line written alone
 266 | +        self.fids, self.cached = list(fids or []), cached     # ruling 65: the paid fidelity results, in order
 267 |          self.angle_hooks = {a[0] for a in many}           # ruling 59: by default only the canned angles' hooks pass
 268 |          call = self.router.call
 269 |  
 270 | @@ -592,7 +595,8 @@ class Rig:
 271 |          ok, flagged, ratings, line = self.medleys.pop(0)
 272 |          labs = PK.labels(len(segs))
 273 |          v = verdict(labs, flagged, ratings, line)
 274 | -        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False)
 275 | +        return ok, dict(v, flagged=list(flagged), backend="xai:grok", measured=True, replayed=False,
 276 | +                        cached=self.cached)
 277 |  
 278 |      def write(self, router, angle_, segs, ctx_, a_by, join=None, extra="", seed=7, avoid_vendor=None, other=()):
 279 |          if join is not None and not other and PK.bridge_budget(sum(m["duration_s"] for m in segs)) is None:
 280 | @@ -629,7 +633,7 @@ class Rig:
 281 |              "prescreen": self.prescreen,
 282 |              "current_levels": lambda *a, **k: [],
 283 |              "medley": self.medley, "write_takeaway": self.write,
 284 | -            "paid_gates": lambda *a, **k: (fid, cx),
 285 | +            "paid_gates": lambda *a, **k: (self.fids.pop(0) if self.fids else fid, cx),
 286 |              "exclusion_for": lambda router, m, *a, **k: {"verdict": "drop" if m["moment_id"] in self.excluded else
 287 |                                                           "keep", "measured": True, "replayed": False,
 288 |                                                           "backend": "xai:grok"},
 289 | @@ -1581,6 +1585,119 @@ class TestRulings6264Search(unittest.TestCase):
 290 |          self.assertTrue(out["tried"][1].get("verdict_again"))               # the second angle's: free
 291 |  
 292 |  
 293 | +class TestRuling65Caption(unittest.TestCase):
 294 | +    """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 295 | +    alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 296 | +    the FIXED caption (the gated title in lowercase, a line break, the channel names in play order), code-written,
 297 | +    caption_fallback: true. The title alone: one more write, then hold."""
 298 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 299 | +    OK = {"ok": True, "violations": [], "measured": True, "replayed": False, "backend": "xai:grok",
 300 | +          "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 301 | +          "verdict": {"ok": True, "violations": [], "classes": {"takeaway": ["commentary"], "title": ["fact"],
 302 | +                                                                "caption": ["fact"]}, "claims": []}}
 303 | +
 304 | +    def failing(self, slot, detail="it belongs to everyone who uses it.", rule="VERDICT_NO"):
 305 | +        v = {"slot": slot, "rule": rule, "detail": detail}
 306 | +        return dict(self.OK, ok=False, violations=[v], verdict=dict(self.OK["verdict"], ok=False, violations=[v]))
 307 | +
 308 | +    def run_rig(self, fids, lines, line_ok=True):
 309 | +        import context_integrity as CI
 310 | +        import vo_fidelity as VF
 311 | +        seen = []
 312 | +
 313 | +        def one(router, segs, lns, *a, **k):
 314 | +            seen.append([ln["text"] for ln in lns])
 315 | +            v = [] if line_ok else [{"slot": lns[0]["slot"], "rule": "VERDICT_UNCERTAIN", "detail": lns[0]["text"]}]
 316 | +            return {"ok": line_ok, "violations": v, "measured": True, "replayed": False, "backend": "xai:grok",
 317 | +                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 318 | +                    "verdict": {"ok": line_ok, "violations": v, "classes": {lns[0]["slot"]: ["commentary"]}, "claims": []}}
 319 | +        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
 320 | +        VF.check = one
 321 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 322 | +                                             "backends": {"B": "xai", "C": "xai"}}
 323 | +        CI.contexts_from_sources = lambda *a, **k: {}
 324 | +        try:
 325 | +            rig = Rig(self.MS, ["h", "x", "y"], [(True, [], None, Rig.LINE)], [None], fids=fids, lines=lines)
 326 | +            return rig, rig.run(), seen
 327 | +        finally:
 328 | +            VF.check, CI.check_contexts, CI.contexts_from_sources = saved
 329 | +
 330 | +    def test_only_the_caption_fails_and_its_own_write_passes(self):
 331 | +        new = "nobody holds the keys to these rules."
 332 | +        rig, out, seen = self.run_rig([self.failing("caption")], [{"caption": {"text": new, "cites": []}}])
 333 | +        pk = out["package"]
 334 | +        self.assertIsNotNone(pk)
 335 | +        lines = {x["slot"]: x["text"] for x in pk["lines"]}
 336 | +        self.assertEqual(lines["caption"], new)
 337 | +        self.assertEqual((lines["takeaway"], lines["title"]), (Rig.LINE, "Nobody bends the rules"))   # kept as gated
 338 | +        self.assertFalse(pk.get("caption_fallback"))
 339 | +        prompt = [p for r, p in rig.prompts if r == "angle_write"][-1]
 340 | +        self.assertIn("Your caption was refused", prompt)                   # a new prompt, never a replay
 341 | +        self.assertIn('"it belongs to everyone who uses it." (the fact check found that the clips do not say it)', prompt)
 342 | +        self.assertIn('TAKEAWAY: "' + Rig.LINE, prompt)
 343 | +        self.assertEqual(seen, [[new]])                                       # the verdict on that line alone
 344 | +        rw = out["tried"][0]["attempts"][0]["rewrite"]
 345 | +        self.assertEqual((rw["slot"], rw["passed"]), ("caption", True))
 346 | +        self.assertEqual(pk["gates"]["vo_fidelity_verdict"]["status"], "PASS")
 347 | +        self.assertEqual(len(rig.write_calls), 1)                            # no second full write was spent
 348 | +
 349 | +    def test_a_caption_that_fails_again_is_the_fixed_line(self):
 350 | +        rig, out, seen = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
 351 | +                                                                               "cites": []}}], line_ok=False)
 352 | +        pk = out["package"]
 353 | +        self.assertIsNotNone(pk)                                              # a caption never kills a package
 354 | +        cap = next(x for x in pk["lines"] if x["slot"] == "caption")
 355 | +        self.assertEqual(cap["text"], "nobody bends the rules\na / b / c")   # the title, lowercase; the channels
 356 | +        self.assertEqual(cap["cites"], ["h", "x", "y"])
 357 | +        self.assertTrue(pk["caption_fallback"])
 358 | +        self.assertTrue(out["tried"][0]["attempts"][0]["rewrite"]["caption_fallback"])
 359 | +        self.assertIn("ruling 65 b", pk["gates"]["vo_fidelity_verdict"]["by"])
 360 | +        self.assertEqual(pk["gates"]["house_style"]["status"], "PASS")
 361 | +        self.assertEqual(HS.lint("caption", cap["text"]), [])
 362 | +        bad_reply = self.run_rig([self.failing("caption")], [{"caption": "not an object"}])[1]   # the write fails
 363 | +        self.assertTrue(bad_reply["package"]["caption_fallback"])
 364 | +
 365 | +    def test_the_title_alone_gets_one_more_write_then_is_held(self):
 366 | +        rig, out, _ = self.run_rig([self.failing("title", "Bitcoin is owned by nobody at all")],
 367 | +                                   [{"title": {"text": "Rules nobody can bend", "cites": []}}])
 368 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"),
 369 | +                         "Rules nobody can bend")
 370 | +        rig, out, _ = self.run_rig([self.failing("title")], [{"title": {"text": "Rules nobody can bend", "cites": []}}],
 371 | +                                   line_ok=False)
 372 | +        self.assertIsNone(out["package"])                                     # no fixed title without a ruling
 373 | +        self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
 374 | +
 375 | +    def test_only_a_lone_caption_or_title_takes_the_path(self):
 376 | +        self.assertEqual(PK.lone_slot([{"slot": "caption"}, {"slot": "caption"}]), "caption")
 377 | +        self.assertEqual(PK.lone_slot([{"slot": "title"}]), "title")
 378 | +        for vs in ([], [{"slot": "takeaway"}], [{"slot": "caption"}, {"slot": "title"}], [{"slot": "-"}],
 379 | +                   [{"slot": "caption"}, {"slot": "-"}]):
 380 | +            self.assertIsNone(PK.lone_slot(vs), vs)
 381 | +        rig, out, _ = self.run_rig([dict(self.failing("caption"), violations=[
 382 | +            {"slot": "caption", "rule": "VERDICT_NO", "detail": "x"}, {"slot": "takeaway", "rule": "VERDICT_NO",
 383 | +                                                                      "detail": "y"}])], [])
 384 | +        self.assertNotIn("rewrite", out["tried"][0]["attempts"][0])          # the takeaway failed too: as before
 385 | +
 386 | +    def test_merge_keeps_the_other_lines_as_gated(self):
 387 | +        merged = PK.merge_fid(self.failing("caption"), "caption",
 388 | +                              {"deterministic": {"ok": True, "violations": []}, "measured": True, "replayed": False,
 389 | +                               "verdict": {"ok": True, "violations": [], "classes": {"caption": ["commentary"]},
 390 | +                                           "claims": []}, "backend": "heimdall:qwen"})
 391 | +        self.assertTrue(merged["ok"])
 392 | +        self.assertEqual(merged["verdict"]["classes"], {"takeaway": ["commentary"], "title": ["fact"],
 393 | +                                                        "caption": ["commentary"]})
 394 | +        self.assertIn("the caption alone: heimdall:qwen (ruling 65)", merged["backend"])
 395 | +        unmeasured = PK.merge_fid(self.OK, "caption", {"deterministic": {"ok": True, "violations": []},
 396 | +                                                       "measured": False, "verdict": {"ok": True, "violations": []}})
 397 | +        self.assertFalse(unmeasured["ok"])                                   # law L-m
 398 | +
 399 | +    def test_a_cached_clips_alone_verdict_is_free(self):
 400 | +        rig = Rig([pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)], ["h", "x", "y"],
 401 | +                  [(False, [], None, "none")], [None], cached=True)
 402 | +        out = rig.run()
 403 | +        self.assertEqual((len(rig.medley_calls), out["search"]["lineups"]), (1, 0))
 404 | +
 405 | +
 406 |  class TestOrder0622StepAFromBothVendors(unittest.TestCase):
 407 |      """ORDER 06:22: 45, step A from BOTH vendors on every cuttable clip before the angle step; 44, a failed re-screen
 408 |      after a write swaps out that clip only, and the line-up carries on."""
 409 | 
```

---

You are auditing a SMALL change on branch pp-selectid (Protocol Pulse: the L-y MEDLEY, sealed in a pin the integrator
renders). Your role: a strict reviewer of a gate path. Only state what you can verify from the diff; if uncertain, say
so; do not guess.

Background (static):
- A line-up that passes the clips-alone verdict gets at most WRITES (2) writes. Each write produces ONE takeaway (the
  VO line), ONE title and ONE caption (the post text).
- Each write runs the gates:
  - cheap_checks: the deterministic fidelity rules, house style, DUPLICATE, runtime, R4, the shape;
  - then the paid gates (paid_gates): the blind fidelity verdict on every line (VF.check), and context integrity
    (CI.check_contexts) on the package, whose view includes the title and caption.
  - A failure gets the whole write redone with the violations (_redo).
  - After the gates: coherence, then the sealed inventory (every required row exactly PASS; a replayed verdict is never
    deliverable, law L-j).
- In the 12:22 build, a line-up passed the clips alone and both writes' takeaway and title passed, but one caption
  sentence was refused each time (VERDICT_NO, then VERDICT_UNCERTAIN). No package came out.

The order this diff implements (ORCHESTRATOR RULING 65, 12:52 ET Nov 13, verbatim):
"65. A CAPTION NEVER KILLS A PACKAGE. The caption is the post text PBX reads and approves before anything is
published; the video does not carry it.
(a) When the takeaway and the title pass and ONLY the caption fails fidelity, the writer gets ONE more write for the
caption alone, told the refused sentence and why; the takeaway and title are kept as gated, not rewritten. The caption
stays under L-t (every audience text gated) and the house style lint.
(b) If that write fails too, the caption is the FIXED line, which states no fact: the gated title in lowercase, a line
break, then the channel names in play order separated by ' / '. Code-written, no model. It is recorded as
caption_fallback: true so I tell PBX the caption is a placeholder.
(c) Same principle for the title only if you ever see it: one more write alone, then hold (a title is burned into
nothing but is the YouTube title, so no fixed fallback without my ruling).
The identical-prompt replay must not trap this line-up: the caption-only write is a new prompt."
(And the 12:00 budget, made exact here: "The search budget of 8 line-ups counts JUDGED line-ups; cached verdicts for an
identical line-up are free.")

The change (pipeline/package.py, pipeline/package_pin.py, tests/package/test_medley.py):
1. lone_slot(violations) returns "caption" or "title" when EVERY violation is on that one line, else None.
2. In the write loop:
   - A cheap failure whose violations are all on the caption, or all on the title, no longer redoes the write at once.
     It goes on to the paid gates.
   - Then, when context integrity passed, the fidelity verdict was measured, and lone_slot(cheap + fidelity
     violations) is "caption" or "title", rewrite_alone() runs.
   - Otherwise the old redo runs, its instructions now including any cheap violations.
3. rewrite_alone(): ONE write for that line alone.
   - The prompt is a NEW one, WRITE_LINE: the angle, the line-up, the other lines quoted as kept, and the refused
     sentence(s) with why (LINE_WHY), under the house style rules.
   - The reply contract: exactly {slot: {text, cites}}, cites from the line-up's ids, within the length limit; a
     violation raises and is rejected. The line writer's vendor and family join the writers' sets (L-x).
   - The new line is gated alone:
     - cheap_checks on the package with it (its deterministic layer and the house style);
     - the blind fidelity verdict on THAT LINE ALONE (VF.check with one line);
     - context integrity again on the package as it will be sealed.
   - On a pass, merge_fid() gives the record: the other lines' results as gated, the line's own from its run. measured
     and replayed hold over both runs, and the back-end names both.
   - If the caption's write fails any of it (or raises), the caption becomes the FIXED line, fixed_caption(): the gated
     title in lowercase, "\n", the channel names in play order, lowercase too, joined by " / ", citing every clip.
     pk["caption_fallback"] = True. Its record is the deterministic layer only, with the verdict entry "code, no model"
     (no model judges a code-written line). The cheap checks (house style) and context integrity still run on it.
   - A title that fails again: held (the fidelity record is set to failed; the line-up stops), with no fixed title.
4. package_pin.to_pin carries moments_package.caption_fallback (outside the seal body, like no_voice).
5. The budget: medley() records Reply.cached (a live run served its recorded reply to the same bytes), and the line-up
   counts toward the 8 only when neither replayed nor cached.
6. Tests (TestRuling65Caption, 6):
   - the caption alone rewritten and passing, with the takeaway and title unchanged and one full write spent;
   - a caption failing again becomes the fixed line (house style PASS, caption_fallback) — including when the
     caption-only reply is out of contract;
   - the title rewritten once, then held;
   - only a lone caption or title takes the path;
   - merge_fid;
   - a cached verdict is free.
   test_medley 125 OK; all 11 suites OK.

Stated readings (say so if you read the ruling differently):
- K1: "fails fidelity" covers the deterministic layer and house style too (the cheap checks): a caption failing there
  alone takes the same path, because the principle is "a caption never kills a package".
- K2: PBX's house style makes a caption all lowercase, NAMES TOO, so the fixed line's channel names are lowercase as
  well as the title. Otherwise the house_style row (required) could never pass.
- K3: "code-written, no model" also means no model VERDICT on the fixed line (it states no fact). Its deterministic
  layer, house style and context integrity run.
- K4: context integrity runs again on the package as sealed, because its view includes the caption (L-j: the gates
  on the bytes sent). The takeaway and title's fidelity results stand as gated (not re-judged: ruling 61's lesson,
  judge noise).
- K5: the caption-only write does not count toward WRITES (it is the ruling's "ONE more write").

Check in particular:
- that no path seals a caption or title that was not gated (the merged record, the fallback);
- that the fixed line's format matches the ruling;
- L-x for the line writer;
- that a failure on the takeaway (or on both other lines) never takes this path;
- the title hold;
- any change to the old redo path;
- the budget fix.

Answer with P0/P1/P2 findings (file:line, concrete scenario), then "SHIP: yes / no / yes with conditions".


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
