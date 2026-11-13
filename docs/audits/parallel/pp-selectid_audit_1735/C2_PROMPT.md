# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-1735
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 271 s finish=stop usage in 18660 / out 7476 usd~0.168 (upper-bound price)

# Audit — pp-selectid: RULING 66 amended (takeaway/title written alone)

Scope: I can only see the diff (package.py, test_medley.py). Everything below is verified against the diff text; where the diff doesn't show a callee, I say so.

## P0

None found.

## P1

**P1-1 — `rewrite_alone` (title path): the loop can run its second write even when the first write never produced a line, and the "AGAIN" told-entry can carry a `None`-model avoidance; more importantly the second write's `avoid_model` uses the *backend* of the last reply, not the *model*, so "the other writer model" is only as good as `router.call`'s `avoid_model` semantics.**
File: package.py, diff lines 188–221 (`rewrite_alone`), 58–88 (`write_line`).
Scenario: the first `write_line` raises inside `router.call` (network/LLMParseError). Then `r is None`, `by` stays `None`, and the second iteration calls `write_line(..., avoid_model={None} if by else None)` → `avoid_model=None` → the `**{...}` spread passes nothing, so the second attempt may land on the *same* model. The order says "the second attempt on the other writer model". With only two Heimdall models this is a soft violation: the second write can repeat the first's model whenever the first attempt failed at the call/parse layer rather than at a gate. Same pattern in the takeaway-alone branch (diff line 271: `avoid_model={alone_by} if alone_by else None`), where `alone_by = wr.backend` is only set after a successful call — an exception on attempt 1 (diff lines 273–276, `continue`) leaves `alone_by` as its previous value (or `None`), so attempt 2 can reuse the same model. Concrete: attempt 1 raises `LLMParseError` from deepseek → attempt 2's `avoid_model` is `None` → deepseek is picked again. The order's "second attempt on the other writer model" is then not guaranteed. Note the test `test_the_second_takeaway_alone_is_on_the_other_writer_model` only exercises the success-then-avoid path (`avoid == {"takeaway": [None, {"fake:angle_write"}]}`), so this is untested. Fix: track the *attempted* model (from the router's tried list or the role's model rotation) even when the call raises, or treat a raised call as having consumed that model. Severity: P1 (order compliance, not correctness of gating).

**P1-2 — `takeaway_refusal`: a RUNTIME/R4 violation on slot `"-"` is attributed to the takeaway even when the *bridge* (also kept, also length-bearing) is what moved the runtime.**
File: package.py, diff lines 117–141, used at 330–332 and 355–357.
Scenario: the last full write fails only RUNTIME on `"-"`. `takeaway_refusal` returns `alone=True` (diff line 130: `own = v.get("slot") == "takeaway" or (v.get("slot") == "-" and rule in ("RUNTIME", "R4"))`). But the kept lines include the BRIDGE (diff lines 74–76: the bridge is among the kept lines and is told to the writer). If the bridge's length is what pushed the video past 70 s, the takeaway-alone write is told the refusal, writes a shorter/longer takeaway, and the package can still fail RUNTIME — burning both takeaway-alone writes on a failure the takeaway cannot fix. The docstring (diff lines 118–123) asserts "with the other lines kept only the takeaway's length moves" — but the bridge is kept too and is not length-fixed (it was written by the last full write; nothing in the diff shows the bridge's length is frozen). If the bridge is genuinely fixed once the line-up and join are fixed, this is P2; the diff does not show it, so I flag it as P1-uncertain. Related: `takeaway_budget` is recomputed at diff line 262 from `sum(m["duration_s"] ...)` and `written` — if `written` (the bridge) changed, the budget differs from the full-write's budget, which is consistent, but the *refusal* told to the writer (RUNTIME) may be unfixable by the takeaway. Mitigation in code: the `b is None` break (diff lines 263–266) catches the "no length lands it" case — good — but only when *no* length lands it, not when the *told* refusal was the bridge's fault.

**P1-3 — `takeaway_alone_gates` merges the kept lines' verdicts via `merge_fid(fid, "takeaway", one)` where `fid` is `last_fid` — the *previous* write's fid — but the previous write's fid was computed on a *different package* (different takeaway text, possibly different bridge).**
File: package.py, diff lines 144–153, 342–344.
Scenario: full write #2's paid gates ran (fid2 on package with takeaway T2). Takeaway alone fails → takeaway-alone write produces T3. `takeaway_alone_gates` runs VF.check on the takeaway alone (T3) and CI on the whole package, then `merge_fid(last_fid, "takeaway", one)`. The title/caption/bridge verdicts inside `last_fid` were judged as part of the *blind fidelity verdict on the whole package* (all lines) in the previous write. Two concerns: (a) the kept lines' *text* is identical (they are kept), so their verdicts plausibly transfer — but the diff does not show `merge_fid`'s precondition ch

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 46 s finish=stop usage in 18510 / out 274 usd~0.099 (upper-bound price)

**P0: None** (loop terminates: w_used only increments on full writes up to WRITES, alone_n only increments on lone path up to LINE_ONLY_WRITES=2, over_budget/ai break, explicit break on failed lone condition at 236-239, success paths break after package append; no path exceeds WRITES+2 writes verifiable in diff).  
**P1: None** (takeaway-alone never bypasses gates: lone path still does cheap_checks + VF.check on takeaway + CI.check_contexts on full pk + coherence + merge only when last_fid set from prior t_alone=True path; no judge code, prompts, or thresholds touched; ruling-65 caption path byte-identical, title exactly 2 writes then held per 190 and test at 521-525; writer-only change per 17:20 order).  
**P2: None** (takeaway_refusal attribution verifiable as conservative: false-positive "not alone" only drops a retry (e.g. clip_02 POLARITY or <2 tokens at 554-562), never rewrites wrong line; merge_fid precondition holds when used because last_fid only set on t_alone=True paths from takeaway_refusal at 330/356; all new behaviours covered by added tests that mutate to fail if removed).  

SHIP: yes

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 46 s finish=stop usage in 20385 / out 2649 usd~0.101 (upper-bound price)

I have reviewed the diff for `pipeline/package.py` and `tests/package/test_medley.py` against the governing laws and the specific orders (Ruling 66 Amended, 17:20).

### P0 Findings (Blockers)

**1. `takeaway_refusal` fails closed on missing context data (M12 Violation)**
*   **File:** `pipeline/package.py` (in `takeaway_refusal`)
*   **Line:** ~131-136 (logic for `STRONGER`/`NOT_ENTAILED`)
*   **Scenario:** If a `STRONGER` violation occurs but the `cx` (context integrity) object is `None` or does not contain the specific segment key (e.g., due to a partial failure or a different gate ordering), `cseg` will be `{}`. `cseg[v["segment"]]` will raise a `KeyError` or return `None`.
    *   If `cseg[v["segment"]]` is `None`, `(cseg[v["segment"]] or {}).get("C")` handles it.
    *   However, if `v["segment"]` is not in `cseg` at all, `cseg[v["segment"]]` raises `KeyError`.
    *   **Impact:** An unhandled exception in `takeaway_refusal` propagates up to `build`. While `build` might catch it, this prevents the "alone" determination. More critically, if `cx` is passed as `None` (which happens in the first call at line 330: `takeaway_refusal(fields, cheap)` where `cx` defaults to `None`), and a `STRONGER` violation is present in `cheap` (which is unlikely as `STRONGER` is a paid gate, but `NOT_ENTAILED` might be deterministic?), the code attempts to access `cseg` which is `{}`.
    *   **Correction:** `STRONGER` and `NOT_ENTAILED` are typically paid gates (context integrity). In the first call (line 330), only `cheap` violations are passed. `cheap` contains deterministic checks. If `STRONGER` is not in `cheap`, this path isn't hit. However, in the second call (line 355), `cx` is passed. If `cx` is `None` (e.g., if `paid_gates` failed before returning `cx`?), `cseg` is `{}`.
    *   **Actual Risk:** The code `cseg = (cx or {}).get("segments") or {}`. If `v["segment"]` is not in `cseg`, `cseg[v["segment"]]` raises `KeyError`. This violates M12 (Fail Closed) because it crashes the build loop instead of gracefully determining "not alone".
    *   **Fix:** Use `cseg.get(v["segment"])` instead of `cseg[v["segment"]]`.

**2. `merge_fid` precondition violation risk**
*   **File:** `pipeline/package.py` (in `build` loop)
*   **Line:** ~342-344
*   **Scenario:** `takeaway_alone_gates` is called when `lone` is True and `last_fid` is not None. It merges `last_fid` (the verdict from the *previous* full write) with the new takeaway verdict.
    *   The law states: "the kept lines' verdicts are only merged when that write's lines were judged".
    *   `last_fid` is set at line 357: `last_fid, last_rw65 = fid, bool(att.get("rewrite"))`. This `fid` is the result of `paid_gates` for the *current* full write.
    *   If the current full write failed on the takeaway *alone*, `fid` contains violations for the takeaway. The other lines (title, caption) passed.
    *   `takeaway_alone_gates` runs `VF.check` on the *new* takeaway and `CI.check_contexts` on the *whole* package.
    *   It returns `merge_fid(fid, "takeaway", one)`.
    *   **Issue:** `merge_fid` assumes `fid` is a valid verdict object. If `fid` was from a write that *didn't* reach paid gates (e.g., failed cheap checks), `last_fid` would be `None` (initialized at line 234, only set at 357 after paid gates). So `last_fid` is only non-None if the previous write reached paid gates.
    *   **However:** `takeaway_alone_gates` re-runs `CI.check_contexts` on the *new* package. The `fid` being merged is the *old* fidelity verdict. The new `one` is the new fidelity verdict for the takeaway.
    *   **Critical Check:** Does `merge_fid` correctly handle the case where the *old* `fid` had a violation on the takeaway, and the *new* `one` passes? Yes, that's the point.
    *   **Potential Bug:** `takeaway_alone_gates` does *not* re-run the fidelity check on the *kept* lines (title, caption). It relies on `last_fid` for them. This is correct *if* `last_fid` is valid.
    *   **But:** `last_fid` is the verdict from the *last full write*. If the last full write failed on the takeaway, `last_fid` contains the takeaway violation. The kept lines passed. Merging `last_fid` (with takeaway violation) with `one` (new takeaway pass) should result in a pass for the takeaway and keep the pass for the others.
    *   **Law Check:** "No gate accepts more than before". The kept lines are *not* re-judged. They are trusted from the previous write. This is allowed by Ruling 66 ("passing lines kept as gated").
    *   **Verdict:** This logic seems sound, *provided* `last_fid` is indeed the verdict from a write where the kept lines passed. Since `takeaway_refusal` returned `alone=True`, it implies the only failures were on the takeaway (or global runtime). Thus, the kept lines *did* pass in `last_fid`.

**3. `avoid_model` logic in `write_line`**
*   **File:** `pipeline/package.py` (in `write_line`)
*   *

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 1735 (ruling 66 amended + 17:20: the takeaway / title written alone; the takeaway writer told the refused patterns): cycle 1 consensus

(Started 17:22 ET; the label 1735 was typed, not read from the clock.)

- **grok:** "SHIP: yes". No P0, P1 or P2.
- **qwen:** "SHIP: No" on two items, both refuted below with the code.
- **glm:** "SHIP: yes with conditions". One verified defect (P1-1, implemented); the rest refuted or recorded.

## Implemented

**C1 (glm P1-1, verified by tracing): an out-of-contract first write could leave the second write on the same model.**
- write_line raises after router.reject(r) when a reply is out of contract, so the loop never learned the reply's
  backend.
- `alone_by` (the takeaway) and `by` (the title) stayed unset, and the second attempt had no model to avoid. That
  breaks the 17:02 / 17:20 "the second attempt on the other writer model".
- Fixed:
  - write_line sets `e.backend = r.backend` on the exception it re-raises;
  - both loops read it (`getattr(e, "backend", None) or ...`).
  A provider failure with no reply still leaves the model unknown; that call never produced a line.
- Test: test_a_reply_out_of_contract_still_sends_the_second_write_to_the_other_model (the takeaway and the title).
  It fails with the fix removed (mutation run, no network).

## Refuted (evidence from the code)

- **qwen P0-1** (`cseg[v["segment"]]` raises KeyError): no. The index is reached only after `v.get("segment") in cseg`
  (takeaway_refusal: `if not own and v.get("segment") in cseg and (...)`). A cx of None gives `cseg = {}`, hence not
  own, hence not alone.
- **qwen P1** (Router.call may not accept avoid_model): it does. `providers.Router.call(self, role, prompt,
  max_tokens=2000, seed=7, system=None, avoid_vendor=None, avoid_model=None, avoid_family=None, deadline_s=None)`.
  `_skip` refuses `name in am` (backend names, which is what is passed).
- **glm P1-3** (the cheap-fail path never sets t_alone): it does. `own, t_alone = takeaway_refusal(fields, cheap)` is
  a tuple assignment. test_the_no_voice_fallback_comes_after_the_takeaway_alone shows it: STYLE plus RUNTIME, cheap
  only, then two takeaway-alone writes.
- **glm P1-4** (the success path's break is not in the diff): unchanged code, package.py:
  `out["packages"].append(pk)`, `rec["result"] = "PACKAGE"`, `break`. A takeaway-alone write that passes ends the
  loop.
- **glm P1-2** (RUNTIME on "-" may be the bridge's fault): the bridge is a kept line, its text fixed. The takeaway
  alone is written to `takeaway_budget(content, [bridge])`, the word range that lands 60-70 s WITH that bridge. When
  no length lands it (the bridge's fault), the budget is None and the attempt breaks before any write.
- **glm (merge precondition on the coherence path)**: coherence runs only after
  `if not fid["ok"] or not cx["ok"] or cheap:` let the write through, so fid there has no violation at all.
  merge_fid's precondition holds trivially.
- **glm P2-7** (write_calls =

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_1735/C2_STEP.diff (590 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 80a8185..a0c1526 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -689,6 +689,10 @@ def hook_ratings(router, ms, ctx, writer_vendor, writer_family=None, cache=None,
   6 |          return out, None
   7 |      return out, err
   8 |  
   9 | +TAKEAWAY_SAID = ("The takeaway may characterise what the clips SAID, never what WILL happen. Two kinds were refused: a "
  10 | +                 "forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.'), and a superlative that "
  11 | +                 "upgrades a speaker's hedged view to a settled claim (\"Bitcoin's apolitical design is the real "
  12 | +                 "productivity story.\" after a speaker's 'I think Bitcoin will outperform').")   # orchestrator 17:20
  13 |  WRITE_LY = """You are PBX MAX, the host of a 60-second Bitcoin video made of other channels' own words.
  14 |  THE ANGLE (the point this video makes): "{angle}"
  15 |  The clips play BACK TO BACK as a medley, with no narration between them (verbatim, in play order; the channels were not
  16 | @@ -701,6 +705,7 @@ After the last clip you speak ONE closing line, the TAKEAWAY; then a sign-off cr
  17 |  {bridge}Write:
  18 |  - "takeaway": {lo}-{hi} words in short declarative sentences: the point the medley adds up to, as YOUR OWN
  19 |    commentary (your opinion or conclusion), a point and not a summary, never a restatement of any clip.
  20 | +  {said}
  21 |  - "title": ONE title, at most 70 characters; "caption": ONE caption, at most 220 characters. Both carry the angle.
  22 |  Every line gives "cites": the ids of the clips it relies on (none for your own commentary).
  23 |  RULES (a line that breaks one is rejected):
  24 | @@ -1568,7 +1573,8 @@ def write_takeaway(router, angle, segs, ctx, a_by, join=None, extra="", seed=7,
  25 |      angle_text = " ".join(quote_data(angle["angle"], 300).replace('"', "'").split())     # M9: escaped, one line
  26 |      prompt = WRITE_LY.format(angle=angle_text, note=UNTRUSTED.replace("<sentences>", "the quotes"),
  27 |                               lineup=_lineup_block(segs, ctx, a_by), bridge=ask, lo=budget[0], hi=budget[1],
  28 | -                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES)
  29 | +                             extra=(extra + "\n") if extra else "", bridge_shape=shape, style=HS.PROMPT_RULES,
  30 | +                             said=TAKEAWAY_SAID)
  31 |      r = router.call("angle_write", prompt, 3000, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
  32 |      try:
  33 |          obj = json.loads(r.text.strip())
  34 | @@ -1614,27 +1620,48 @@ ids) or your own commentary, which states no fact; never a claim the clips do no
  35 |  cites the clips it comes from.
  36 |  {style}
  37 |  Return ONLY this JSON object: {{"{slot}": {{"text": "...", "cites": []}}}}"""   # RULING 65: one line, alone
  38 | -LINE_WHY = {"VERDICT_NO": "the fact check found that the clips do not say it",
  39 | +LINE_WHY = {"AGAIN": "your first rewrite of it was refused too",   # 17:20: a title's second write is told
  40 | +            "VERDICT_NO": "the fact check found that the clips do not say it",
  41 |              "VERDICT_UNCERTAIN": "the fact check could not find it in the clips",
  42 |              "STYLE": "it breaks the house style"}
  43 |  LINE_LIMIT = {"caption": "at most 220 characters", "title": "at most 70 characters"}
  44 | -
  45 | -
  46 | -def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None):
  47 | +LINE_CHARS = {"caption": 220, "title": 70, "takeaway": 240}
  48 | +LINE_ONLY_WRITES = 2                  # RULING 66 amended (17:02 Nov 13): "up to TWO fresh writes of the failed line only"
  49 | +TAKEAWAY_LIMIT = ("{lo}-{hi} words, one or two sentences: host commentary attributed to nobody that states no fact, no "
  50 | +                  "speaker's view, no advice or prediction and no accusation, and that no viewer could take for a "
  51 | +                  "speaker's words")
  52 | +TAKEAWAY_WHY = dict(VO_FIX, **LINE_WHY, COMMENTARY="as host commentary it must state no fact, no speaker's view, no "
  53 | +                    "advice or prediction and no accusation, and must not sound like a speaker",
  54 | +                    COHERENCE="a blind viewer did not find its point supported by the clips",
  55 | +                    RUNTIME="with it the video does not land 60-70 s")
  56 | +
  57 | +
  58 | +def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, avoid_vendor=None, avoid_model=None,
  59 | +               limit=None):
  60 |      """RULING 65: ONE more write for one line alone ("caption" or "title"): the angle, the line-up, the other lines kept
  61 |      as gated, and the refused sentence(s) with why. A new prompt (WRITE_LINE), so a recorded reply is never replayed
  62 | -    into it. -> (reply, {"text", "cites"}); a reply out of contract raises (and is rejected)."""
  63 | +    into it. -> (reply, {"text", "cites"}); a reply out of contract raises (and is rejected).
  64 | +    RULING 66 amended (17:02): the takeaway alone too. Each refused entry carries the refused sentence ("text") and why
  65 | +    (its rule in plain words, and the gate's detail); the bridge is among the kept lines; `limit` gives its words;
  66 | +    avoid_model puts the second attempt on the other writer model. Ruling 65's prompts are unchanged byte for byte."""
  67 |      from select_by_id import UNTRUSTED
  68 |      from story_semantics import quote_data
  69 |      q = lambda t, n: " ".join(quote_data(t, n).replace('"', "'").split())
  70 |      kept = "\n".join(f'{s.upper()}: "{q(fields[s]["text"], 300)}"' for s in ("takeaway", "title", "caption")
  71 |                       if s != slot and fields.get(s))
  72 | -    why = "; ".join(f'"{q(v.get("detail") or "", 200)}" ({LINE_WHY.get(v.get("rule"), v.get("rule"))})'
  73 | -                    for v in refused)
  74 | +    if slot == "takeaway":                               # ruling 66 amended: the sentences it may not repeat
  75 | +        if (fields.get("bridge") or {}).get("text"):
  76 | +            kept += f'\nBRIDGE (spoken between two clips): "{q(fields["bridge"]["text"], 300)}"'
  77 | +        why = "; ".join(f'"{q(v.get("text") or "", 300)}" ({TAKEAWAY_WHY.get(v.get("rule"), v.get("rule"))}: '
  78 | +                        f'{q(v.get("detail") or "", 240)})' for v in refused) + ". " + TAKEAWAY_SAID
  79 | +    else:
  80 | +        why = "; ".join(f'"{q(v.get("detail") or "", 200)}" ({LINE_WHY.get(v.get("rule"), v.get("rule"))})'
  81 | +                        for v in refused)
  82 |      prompt = WRITE_LINE.format(angle=q(angle["angle"], 300), note=UNTRUSTED.replace("<sentences>", "the quotes"),
  83 |                                 lineup=_lineup_block(segs, ctx, a_by), kept=kept, slot=slot, refused=why,
  84 | -                               limit=LINE_LIMIT[slot], style=HS.PROMPT_RULES)
  85 | -    r = router.call("angle_write", prompt, 1500, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S)
  86 | +                               limit=limit or LINE_LIMIT[slot], style=HS.PROMPT_RULES)
  87 | +    r = router.call("angle_write", prompt, 1500, seed, avoid_vendor=avoid_vendor, deadline_s=WRITER_DEADLINE_S,
  88 | +                    **({"avoid_model": avoid_model} if avoid_model else {}))
  89 |      try:
  90 |          obj = json.loads(r.text.strip())
  91 |          ids = [m["moment_id"] for m in segs]
  92 | @@ -1642,11 +1669,12 @@ def write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=7, av
  93 |          if not isinstance(ln, dict) or set(ln) != {"text", "cites"} or not isinstance(ln["text"], str) or \
  94 |                  not ln["text"].strip() or not isinstance(ln["cites"], list) or \
  95 |                  any(not isinstance(c, str) or c not in ids for c in ln["cites"]) or \
  96 | -                len(ln["text"]) > (220 if slot == "caption" else 70):
  97 | +                len(ln["text"]) > LINE_CHARS[slot]:
  98 |              raise ValueError(f"exactly {{'{slot}': {{'text', 'cites'}}}}, cites from the line-up's ids, "
  99 | -                             f"{LINE_LIMIT[slot]}")
 100 | -    except (ValueError, TypeError, AttributeError):
 101 | +                             f"at most {LINE_CHARS[slot]} characters")
 102 | +    except (ValueError, TypeError, AttributeError) as e:
 103 |          router.reject(r)
 104 | +        e.backend = r.backend                            # audit 1735 C1: the next attempt avoids this model too
 105 |          raise
 106 |      return r, ln
 107 |  
 108 | @@ -1658,6 +1686,54 @@ def lone_slot(violations):
 109 |      return next(iter(slots)) if len(slots) == 1 and slots <= {"caption", "title"} else None
 110 |  
 111 |  
 112 | +def _words_in(words, text):
 113 | +    """A verbatim run (>= 2 canonical tokens) of `words` in `text` (as context_integrity.raising_words_ok matches)."""
 114 | +    import canon
 115 | +    if not isinstance(words, str) or not isinstance(text, str):
 116 | +        return False
 117 | +    wt, tt = canon.canon_tokens(words), canon.canon_tokens(text)
 118 | +    return len(wt) >= 2 and any(tt[i:i + len(wt)] == wt for i in range(len(tt) - len(wt) + 1))
 119 | +
 120 | +
 121 | +def takeaway_refusal(fields, violations, cx=None):
 122 | +    """RULING 66 amended (17:02): one write's failures that are the TAKEAWAY's own -> (entries, alone). An entry
 123 | +    {"text": the refused takeaway, "rule", "detail"} is a violation on its slot; RUNTIME or R4 on the whole video ("-"),
 124 | +    which with the other lines kept only the takeaway's length moves; or a context failure the video's words caused
 125 | +    (STRONGER: step C's raising_words; NOT_ENTAILED: its added_by) when those words are a run of the takeaway and of no
 126 | +    other line. alone: every failure of the write is such an entry (none on another line, none a clip's own, none that
 127 | +    no line's words caused), so the takeaway alone may be written again."""
 128 | +    t = ((fields or {}).get("takeaway") or {}).get("text") or ""
 129 | +    others = [((fields or {}).get(s) or {}).get("text") or "" for s in ("title", "caption", "bridge")]
 130 | +    cseg = (cx or {}).get("segments") or {}
 131 | +    entries, alone = [], bool(violations) and bool(t.strip())
 132 | +    for v in violations or []:
 133 | +        rule, detail = v.get("rule"), str(v.get("detail") or "")
 134 | +        own = v.get("slot") == "takeaway" or (v.get("slot") == "-" and rule in ("RUNTIME", "R4"))
 135 | +        if not own and v.get("segment") in cseg and (
 136 | +                (rule == "STRONGER" and detail.startswith("stronger certainty: the video's words")) or
 137 | +                (rule == "NOT_ENTAILED" and detail.startswith("the video's words"))):
 138 | +            c = (cseg[v["segment"]] or {}).get("C") or {}
 139 | +            w = c.get("raising_words") if rule == "STRONGER" else c.get("added_by")
 140 | +            own = _words_in(w, t) and not any(_words_in(w, o) for o in others)
 141 | +        if own:
 142 | +            entries.append({"text": t, "rule": rule, "detail": detail[:300]})
 143 | +        else:
 144 | +            alone = False
 145 | +    return entries, alone
 146 | +
 147 | +
 148 | +def takeaway_alone_gates(router, pk, fid, sources, a_by, levels, now, writers_v, writers_f):
 149 | +    """RULING 66 amended (17:02): the paid gates of a package whose takeaway alone was written again, the other lines
 150 | +    kept as gated (their verdicts in `fid`, the write they came from): the blind fidelity verdict on the takeaway ALONE,
 151 | +    merged (merge_fid), and context integrity on the package as it will be sealed. -> (fid, cx)."""
 152 | +    man = {"channels": [sg["channel"] for sg in pk["segments"]], "date": now.strftime("%Y-%m-%d") if now else None}
 153 | +    ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"] if x["slot"] == "takeaway"]
 154 | +    one = VF.check(router, fidelity_segments(pk, a_by), ln, writers_v, 7, man, levels, writers_f)
 155 | +    a_use = {sg["label"]: a_by[sg["moment_id"]] for sg in pk["segments"]}
 156 | +    cx = CI.check_contexts(router, pk, CI.contexts_from_sources(pk, sources, now), writers_v, 7, a_use, writers_f, True)
 157 | +    return merge_fid(fid, "takeaway", one), cx
 158 | +
 159 | +
 160 |  def fixed_caption(fields, segs, ctx):
 161 |      """RULING 65 (b): the caption that states no fact, written by code: the gated title in lowercase, a line break, then
 162 |      the channel names in play order separated by ' / ', lowercase too (PBX's house style: a caption is all lowercase,
 163 | @@ -1705,33 +1781,43 @@ def rewrite_alone(router, slot, pk, fields, fid, refused, angle, segs, by_id, ct
 164 |          p = assemble_medley(order, by_id, dict(fields, **{slot: line}), ctx, f"{pk.get('vo_kind')}; {why}")
 165 |          p["medley"] = pk.get("medley")
 166 |          return p
 167 | -    try:
 168 | -        r, line = write_line(router, angle, segs, ctx, a_by, slot, fields, refused, seed=seed,
 169 | -                             avoid_vendor=avoid_vendor)
 170 | -        rec.update(written=line["text"], writer=r.backend)
 171 | -        writers_v.add(r.vendor)                          # L-x: the line's verdict never comes from its writer
 172 | -        writers_f.add(r.family)
 173 | -        pk2 = build_pk(line, f"the {slot} rewritten alone (ruling 65 a)")
 174 | -        cheap2 = cheap_checks(pk2, a_by, levels, ctx.now)
 175 | -        if cheap2[0]:
 176 | -            raise ValueError("cheap gates: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in cheap2[0])[:300])
 177 | -        ln = [{k: x[k] for k in ("slot", "text", "cites")} for x in pk2["lines"] if x["slot"] == slot]
 178 | -        one = VF.check(router, fidelity_segments(pk2, a_by), ln, writers_v, 7, man, levels, writers_f)
 179 | -        rec["verdict"] = {"ok": one["ok"], "violations": one["violations"], "backend": one.get("backend")}
 180 | -        if not one["ok"]:
 181 | -            raise ValueError("fidelity: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in one["violations"])[:300])
 182 | -        fid2 = merge_fid(fid, slot, one)
 183 | -        cx2 = CI.check_contexts(router, pk2, CI.contexts_from_sources(pk2, sources, ctx.now), writers_v, 7, a_use(pk2),
 184 | -                                writers_f, True)
 185 | -        if not (fid2["ok"] and cx2["ok"]):
 186 | -            raise ValueError("context integrity on the package with it: " +
 187 | -                             "; ".join(f"{v['rule']}" for v in cx2["violations"])[:200])
 188 | -        rec["passed"] = True
 189 | -        return pk2, fid2, cx2, cheap2, rec
 190 | -    except Exception as e:
 191 | -        rec.update(passed=False, why=f"{type(e).__name__}: {str(e)[:300]}")
 192 | +    told, by = list(refused), None                      # 17:20: a title's second write, on the other writer model
 193 | +    for k in range(LINE_ONLY_WRITES if slot == "title" else 1):
 194 | +        r, line = None, None
 195 | +        try:
 196 | +            r, line = write_line(router, angle, segs, ctx, a_by, slot, fields, told, seed=seed,
 197 | +                                 avoid_vendor=avoid_vendor, avoid_model={by} if by else None)
 198 | +            rec.update(written=line["text"], writer=r.backend)
 199 | +            writers_v.add(r.vendor)                      # L-x: the line's verdict never comes from its writer
 200 | +            writers_f.add(r.family)
 201 | +            pk2 = build_pk(line, f"the {slot} rewritten alone (ruling 65 a)")
 202 | +            cheap2 = cheap_checks(pk2, a_by, levels, ctx.now)
 203 | +            if cheap2[0]:
 204 | +                raise ValueError("cheap gates: " + "; ".join(f"{v['rule']}: {v['detail']}" for v in cheap2[0])[:300])
 205 | +            ln = [{k_: x[k_] for k_ in ("slot", "text", "cites")} for x in pk2["lines"] if x["slot"] == slot]
 206 | +            one = VF.check(router, fidelity_segments(pk2, a_by), ln, writers_v, 7, man, levels, writers_f)
 207 | +            rec["verdict"] = {"ok": one["ok"], "violations": one["violations"], "backend": one.get("backend")}
 208 | +            if not one["ok"]:
 209 | +                raise ValueError("fidelity: " + "; ".join(f"{v['rule']}: {v['detail']}"
 210 | +                                                          for v in one["violations"])[:300])
 211 | +            fid2 = merge_fid(fid, slot, one)
 212 | +            cx2 = CI.check_contexts(router, pk2, CI.contexts_from_sources(pk2, sources, ctx.now), writers_v, 7,
 213 | +                                    a_use(pk2), writers_f, True)
 214 | +            if not (fid2["ok"] and cx2["ok"]):
 215 | +                raise ValueError("context integrity on the package with it: " +
 216 | +                                 "; ".join(f"{v['rule']}" for v in cx2["violations"])[:200])
 217 | +            rec["passed"] = True
 218 | +            return pk2, fid2, cx2, cheap2, rec
 219 | +        except Exception as e:
 220 | +            rec.update(passed=False, why=f"{type(e).__name__}: {str(e)[:300]}")
 221 | +            rec.setdefault("tries", []).append({"written": (line or {}).get("text"),
 222 | +                                                "writer": r.backend if r is not None else None, "why": rec["why"]})
 223 | +            by = r.backend if r is not None else (getattr(e, "backend", None) or by)   # audit 1735 C1
 224 | +            if line is not None:
 225 | +                told = told + [{"rule": "AGAIN", "detail": f"{line['text']}: {str(e)[:200]}"}]
 226 |      if slot != "caption":                                # (c): a title that fails again is held
 227 | -        rec["why"] = f"the title failed alone twice: held (ruling 65 c): {rec['why']}"
 228 | +        rec["why"] = (f"the title failed alone {1 + len(rec.get('tries') or [])} times (its second write on the other "
 229 | +                      f"writer model, 17:20): held (ruling 65 c): {rec['why']}")
 230 |          return pk, dict(fid, ok=False), {"ok": True, "violations": []}, cheap_checks(pk, a_by, levels, ctx.now), rec
 231 |      line = fixed_caption(fields, segs, ctx)               # (b): the fixed caption, code-written, no model
 232 |      pk3 = build_pk(line, "the fixed caption (ruling 65 b)")
 233 | @@ -2577,27 +2663,53 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 234 |                      rec["why"] = "ruling 70: " + "; ".join(f"{k}: {v}" for k, v in vbad.items())[:400] + ": re-lined"
 235 |                      relined, w_used = True, writes      # no write is paid
 236 |                  take_failed, last_fields = 0, None         # ruling 3 (22:40): the no-voice fallback reads these
 237 | -                while w_used < writes:
 238 | +                alone_n, alone_by, t_refused, t_alone, last_fid, last_rw65 = 0, None, [], False, None, False
 239 | +                while True:                                # RULING 66 amended (17:02): the writes; then, when the
 240 | +                    lone = w_used >= writes                # takeaway alone failed, the takeaway ALONE, up to twice
 241 | +                    if lone and not (alone_n < LINE_ONLY_WRITES and t_alone and last_fields is not None and
 242 | +                                     not last_rw65):
 243 | +                        break
 244 |                      if over_budget(ai):
 245 |                          break
 246 |                      w_over = package_over(line)
 247 |                      if w_over:
 248 |                          rec["why"], rec["budget"] = w_over, True      # ruling 66: a budget, not an outcome
 249 |                          break
 250 | -                    w_used += 1
 251 | -                    try:
 252 | -                        wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 253 | -                                                    seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 254 | -                                                    avoid_vendor=writer_avoid or None, other=written)
 255 | -                    except NoBridgeFits as e:                  # the seconds rule it out: re-line, no write is paid
 256 | -                        if join is not None:
 257 | -                            dropped.add(segs[join[0] + 1]["moment_id"])
 258 | -                        rec["why"] = f"{e}: re-lined"
 259 | -                        relined = join is not None
 260 | -                        break
 261 | -                    except Exception as e:
 262 | -                        rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 263 | -                        continue
 264 | +                    if lone:                               # the other lines kept as gated; told each refusal and why
 265 | +                        alone_n += 1
 266 | +                        b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 267 | +                        if b is None:
 268 | +                            rec["attempts"].append({"writer_error": "no takeaway length lands 60-70 s with the kept "
 269 | +                                                                    "lines", "takeaway_alone": alone_n})
 270 | +                            break
 271 | +                        try:
 272 | +                            wr, tl = write_line(router, angle, segs, ctx, a_by, "takeaway", last_fields, t_refused,
 273 | +                                                seed=7 + w_used + alone_n + 10 * ai + 100 * n_lineup + wseed,
 274 | +                                                avoid_vendor=writer_avoid or None,
 275 | +                                                avoid_model={alone_by} if alone_by else None,   # the other model
 276 | +                                                limit=TAKEAWAY_LIMIT.format(lo=b[0], hi=b[1]))
 277 | +                        except Exception as e:
 278 | +                            rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}",
 279 | +                                                    "takeaway_alone": alone_n})
 280 | +                            alone_by = getattr(e, "backend", None) or alone_by   # its reply out of contract: avoided
 281 | +                            continue
 282 | +                        alone_by = wr.backend
 283 | +                        fields = dict(last_fields, takeaway=tl, takeaway_budget=list(b))
 284 | +                    else:
 285 | +                        w_used += 1
 286 | +                        try:
 287 | +                            wr, fields = write_takeaway(router, angle, segs, ctx, a_by, join, extra,
 288 | +                                                        seed=7 + w_used + 10 * ai + 100 * n_lineup + wseed,
 289 | +                                                        avoid_vendor=writer_avoid or None, other=written)
 290 | +                        except NoBridgeFits as e:              # the seconds rule it out: re-line, no write is paid
 291 | +                            if join is not None:
 292 | +                                dropped.add(segs[join[0] + 1]["moment_id"])
 293 | +                            rec["why"] = f"{e}: re-lined"
 294 | +                            relined = join is not None
 295 | +                            break
 296 | +                        except Exception as e:
 297 | +                            rec["attempts"].append({"writer_error": f"{type(e).__name__}: {str(e)[:200]}"})
 298 | +                            continue
 299 |                      writers_v.add(wr.vendor)
 300 |                      writers_f.add(wr.family)
 301 |                      for m in segs:                             # item 45: the verdict off every writer, when one exists
 302 | @@ -2639,19 +2751,24 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 303 |                                                           "backend": med.get("backend")}
 304 |                      fields["supply_exception"] = exception
 305 |                      pk = assemble_medley([m["moment_id"] for m in segs], cleared, fields, ctx,
 306 | -                                         f"medley (L-y), written, attempt {w_used}")
 307 | +                                         f"medley (L-y), written, attempt {w_used}" +
 308 | +                                         (f", the takeaway alone {alone_n} (ruling 66, 17:02)" if lone else ""))
 309 |                      pk["medley"] = med
 310 |                      written = [fields["bridge"]["text"]] if fields.get("bridge") else ()   # a redo budgets with it
 311 |                      cheap, det, dup, rt_ok, r4_res = cheap_checks(pk, a_by, levels, ctx.now)
 312 |                      att = {"writer": wr.backend, "writer_tried": [list(x) for x in getattr(wr, "tried", [])],   # ruling 5
 313 |                             "runtime": pk["runtime_s_estimate"], "bridge": pk["bridge"],
 314 |                             "takeaway_budget": fields.get("takeaway_budget"),
 315 | -                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]]}
 316 | +                           "lines": [{k: x[k] for k in ("slot", "text", "cites")} for x in pk["lines"]],
 317 | +                           **({"takeaway_alone": {"attempt": alone_n, "refused": [dict(x) for x in t_refused]}}
 318 | +                              if lone else {})}
 319 |                      rec["attempts"].append(att)
 320 | -                    take = _takeaway_record(ai, n_lineup, w_used, pk, cheap)
 321 | +                    take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap)
 322 |                      out["takeaways"].append(take)
 323 |                      last_fields = fields
 324 | -                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used} ({wr.backend}, takeaway {take['words']} "
 325 | +                    log(f"  angle {ai + 1} line-up {n_lineup} write {w_used + alone_n}" +
 326 | +                        (" (the takeaway alone, ruling 66 17:02)" if lone else "") +
 327 | +                        f" ({wr.backend}, takeaway {take['words']} "
 328 |                          f"words, {pk['runtime_s_estimate']} s): " +
 329 |                          ("cheap gates fail " + ", ".join(sorted({v["rule"] for v in cheap})) if cheap else "cheap PASS")
 330 |                          + f" ({time.time() - t0:.0f} s)")
 331 | @@ -2672,6 +2789,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 332 |                      if cheap and lone_slot(cheap) is None:     # ruling 65: a lone caption / title goes on
 333 |                          att["violations"] = cheap
 334 |                          take_failed += take["passed"] is False
 335 | +                        own, t_alone = takeaway_refusal(fields, cheap)          # ruling 66 amended (17:02)
 336 | +                        t_refused += [e for e in own if e not in t_refused]
 337 | +                        last_fid, last_rw65 = (last_fid if lone else None), False   # a write's own lines: unjudged
 338 |                          b = takeaway_budget(sum(m["duration_s"] for m in segs), written)
 339 |                          extra = _redo([dict(v, detail=v["detail"] + (f" (a takeaway of {b[0]}-{b[1]} words lands it)"
 340 |                                                                       if b else " (no takeaway length lands it with this "
 341 | @@ -2679,8 +2799,12 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 342 |                                                                       else " (no takeaway length lands it)"))
 343 |                                         if v["rule"] == "RUNTIME" else v for v in cheap])
 344 |                          continue
 345 | -                    fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 346 | -                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used, pk, cheap, fid, cx)
 347 | +                    if lone and last_fid is not None:      # ruling 66 amended: the kept lines keep their verdicts
 348 | +                        fid, cx = takeaway_alone_gates(router, pk, last_fid, sources, a_by, levels, ctx.now,
 349 | +                                                       writers_v, writers_f)
 350 | +                    else:
 351 | +                        fid, cx = paid_gates(router, pk, sources, a_by, levels, ctx.now, writers_v, writers_f, pool)
 352 | +                    out["takeaways"][-1] = take = _takeaway_record(ai, n_lineup, w_used + alone_n, pk, cheap, fid, cx)
 353 |                      framing = [v for v in cx["violations"] if v["rule"] in VO_DEPENDENT]
 354 |                      att["violations"] = cheap + fid["violations"] + cx["violations"]
 355 |                      att["verdict_classes"] = (fid.get("verdict") or {}).get("classes")
 356 | @@ -2710,6 +2834,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 357 |                              rec["why"] = "context integrity failed on something the VO cannot fix"
 358 |                              w_used = writes
 359 |                              break
 360 | +                        own, t_alone = takeaway_refusal(fields, cheap + fid["violations"] + cx["violations"], cx)
 361 | +                        t_refused += [e for e in own if e not in t_refused]   # ruling 66 amended: what it is told
 362 | +                        last_fid, last_rw65 = fid, bool(att.get("rewrite"))
 363 |                          extra = _redo(cheap + fid["violations"] + [{"slot": v["segment"], "rule": v["rule"],
 364 |                                                                      "detail": VO_FIX.get(v["rule"], v["detail"])}
 365 |                                                                     for v in framing])
 366 | @@ -2738,6 +2865,10 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 367 |                              extra = _redo([{"slot": "takeaway", "rule": "COHERENCE", "detail":
 368 |                                              f"a blind viewer rated the takeaway's point {coh['vo_point']} of 5 for "
 369 |                                              f"being supported by the clips: land the point the clips make together"}])
 370 | +                            ref = {"text": ((fields.get("takeaway") or {}).get("text") or ""), "rule": "COHERENCE",
 371 | +                                   "detail": f"a blind viewer rated its point {coh['vo_point']} of 5"}   # ruling 66
 372 | +                            t_refused += [ref] if ref not in t_refused else []
 373 | +                            t_alone, last_fid, last_rw65 = True, fid, bool(att.get("rewrite"))
 374 |                              continue                          # the clips hold; only the takeaway's point is weak
 375 |                          weak = {sg["moment_id"] for sg in pk["segments"][1:]
 376 |                                  if (coh.get("clips") or {}).get(sg["label"], COHERENCE_MIN) < COHERENCE_MIN}
 377 | @@ -2771,7 +2902,9 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 378 |                  if not out["packages"] and not rec.get("why") and not rec.get("result"):
 379 |                      last = (rec.get("attempts") or [{}])[-1]
 380 |                      rules = sorted({str(v.get("rule")) for v in last.get("violations") or []})
 381 | -                    rec["why"] = f"{w_used} write(s) failed their gates" + (f" ({', '.join(rules)})" if rules else "")
 382 | +                    rec["why"] = (f"{w_used} write(s)" + (f" and {alone_n} of the takeaway alone (ruling 66, 17:02)"
 383 | +                                                          if alone_n else "") + " failed their gates" +
 384 | +                                  (f" ({', '.join(rules)})" if rules else ""))
 385 |                  if out["packages"] or not relined:
 386 |                      break
 387 |              if out["packages"] or out.get("budget_stop") or over_budget(ai):
 388 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 389 | index a002883..d084147 100644
 390 | --- a/tests/package/test_medley.py
 391 | +++ b/tests/package/test_medley.py
 392 | @@ -11,6 +11,7 @@
 393 |  - The pin of a medley: intro null, the takeaway after the last clip, the two medley rows required.
 394 |  """
 395 |  import json
 396 | +import re
 397 |  import os
 398 |  import sys
 399 |  import unittest
 400 | @@ -1856,6 +1857,189 @@ class TestRuling66Candidate(unittest.TestCase):
 401 |          self.assertEqual(rig.medley_calls, [["h", "x", "y", "z"]])
 402 |  
 403 |  
 404 | +class TestRuling66Amended(unittest.TestCase):
 405 | +    """RULING 66 amended (17:02 Nov 13): a line-up whose clips pass and whose takeaway alone failed gets, at once, up to
 406 | +    TWO writes of the takeaway ALONE (told each refused sentence and why; the second on the other writer model), the
 407 | +    other lines kept as gated; then ruling 3's no-voice fallback when its seconds allow, else the line-up rests."""
 408 | +    MS = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0)]
 409 | +    WHY = "host commentary 'Nobody gets to bend these rules' fails imperative_or_prediction"
 410 | +
 411 | +    def failing(self, slot="takeaway", detail=WHY, rule="COMMENTARY"):
 412 | +        return TestRuling65Caption.failing(TestRuling65Caption(), slot, detail, rule)
 413 | +
 414 | +    def run_rig(self, fids, lines, alone_ok=(True,), ms=None, takeaways=None, medleys=None):
 415 | +        import context_integrity as CI
 416 | +        import vo_fidelity as VF
 417 | +        seen, ok_q, avoid = [], list(alone_ok), {}
 418 | +
 419 | +        def one(router, segs, lns, *a, **k):
 420 | +            seen.append([ln["text"] for ln in lns])
 421 | +            ok = ok_q.pop(0) if ok_q else True
 422 | +            v = [] if ok else [{"slot": lns[0]["slot"], "rule": "COMMENTARY", "detail": f"'{lns[0]['text']}' fails x"}]
 423 | +            return {"ok": ok, "violations": v, "measured": True, "replayed": False, "backend": "xai:grok",
 424 | +                    "deterministic": {"ok": True, "violations": [], "price_now_measured": True},
 425 | +                    "verdict": {"ok": ok, "violations": v, "classes": {lns[0]["slot"]: ["commentary"]}, "claims": []}}
 426 | +        saved = (VF.check, CI.check_contexts, CI.contexts_from_sources)
 427 | +        VF.check = one
 428 | +        CI.check_contexts = lambda *a, **k: {"ok": True, "violations": [], "measured": True, "replayed": False,
 429 | +                                             "backends": {"B": "xai", "C": "xai"}}
 430 | +        CI.contexts_from_sources = lambda *a, **k: {}
 431 | +        try:
 432 | +            rig = Rig(ms or self.MS, ["h", "x", "y", "z"] if ms else ["h", "x", "y"],
 433 | +                      medleys or [(True, [], None, Rig.LINE)], [None, None], fids=fids, lines=lines,
 434 | +                      takeaways=takeaways)
 435 | +            inner = rig.router.call
 436 | +
 437 | +            def spy(role, prompt, *a, **k):
 438 | +                m = re.search(r"Your (\w+) was refused", prompt) if role == "angle_write" else None
 439 | +                if m:                                          # each line written alone: the model it avoided
 440 | +                    avoid.setdefault(m.group(1), []).append(k.get("avoid_model"))
 441 | +                return inner(role, prompt, *a, **k)
 442 | +            rig.router.call = spy
 443 | +            return rig, rig.run(), seen, avoid
 444 | +        finally:
 445 | +            VF.check, CI.check_contexts, CI.contexts_from_sources = saved
 446 | +
 447 | +    def test_both_writes_refuse_the_takeaway_then_the_takeaway_alone_passes(self):
 448 | +        new = "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."   # 18 words: the budget of 39 s of clips
 449 | +        rig, out, seen, avoid = self.run_rig([self.failing(), self.failing()], [{"takeaway": {"text": new,
 450 | +                                                                                              "cites": []}}])
 451 | +        pk = out["package"]
 452 | +        self.assertIsNotNone(pk)
 453 | +        lines = {x["slot"]: x["text"] for x in pk["lines"]}
 454 | +        self.assertEqual(lines["takeaway"], new)
 455 | +        self.assertEqual((lines["title"], lines["caption"]), ("Nobody bends the rules", "nobody bends these rules"))
 456 | +        prompt = [p for r, p in rig.prompts if r == "angle_write"][-1]
 457 | +        self.assertIn("Your takeaway was refused", prompt)                    # told the refused sentence and why
 458 | +        self.assertIn(f'"{Rig.LINE}" (as host commentary it must state no fact', prompt)
 459 | +        self.assertIn("fails imperative_or_prediction", prompt)
 460 | +        self.assertIn('TITLE: "Nobody bends the rules"', prompt)              # the other lines, kept as gated
 461 | +        self.assertNotIn('TAKEAWAY: "', prompt)
 462 | +        self.assertEqual(seen, [[new]])                                        # the verdict on the takeaway alone
 463 | +        self.assertEqual(len(rig.write_calls), 2)                              # the two writes, then the line alone
 464 | +        att = out["tried"][0]["attempts"][2]
 465 | +        self.assertEqual((att["takeaway_alone"]["attempt"], len(att["takeaway_alone"]["refused"])), (1, 1))
 466 | +        self.assertEqual(prompt.count(f'"{Rig.LINE}"'), 1)                    # the same refusal told once
 467 | +        self.assertEqual(pk["gates"]["vo_fidelity_verdict"]["status"], "PASS")
 468 | +        self.assertEqual(avoid, {"takeaway": [None]})
 469 | +        self.assertEqual([t["write"] for t in out["takeaways"]], [1, 2, 3])
 470 | +        self.assertIn(PK.TAKEAWAY_SAID, prompt)                                # 17:20: the patterns refused today
 471 | +
 472 | +    def test_the_second_takeaway_alone_is_on_the_other_writer_model(self):
 473 | +        a1, a2 = "Rules nobody can bend are rules that work the same way for every single person who holds them.", "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
 474 | +        rig, out, seen, avoid = self.run_rig([self.failing(), self.failing()],
 475 | +                                             [{"takeaway": {"text": a1, "cites": []}},
 476 | +                                              {"takeaway": {"text": a2, "cites": []}}], alone_ok=(False, True))
 477 | +        self.assertEqual(avoid, {"takeaway": [None, {"fake:angle_write"}]})   # the first one's model avoided
 478 | +        self.assertEqual(seen, [[a1], [a2]])
 479 | +        prompts = [p for r, p in rig.prompts if r == "angle_write" and "Your takeaway was refused" in p]
 480 | +        self.assertIn(f'"{a1}"', prompts[1])                                   # its own refusal told too
 481 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "takeaway"), a2)
 482 | +
 483 | +    def test_both_takeaway_alone_writes_fail_and_the_line_up_rests(self):
 484 | +        rig, out, seen, _ = self.run_rig([self.failing(), self.failing()],
 485 | +                                         [{"takeaway": {"text": "Rules nobody can bend are rules that work the same way for every single person who holds them.", "cites": []}},
 486 | +                                          {"takeaway": {"text": "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere.", "cites": []}}],
 487 | +                                         alone_ok=(False, False))
 488 | +        self.assertIsNone(out["package"])
 489 | +        self.assertEqual(len(seen), 2)                                         # up to TWO, never more
 490 | +        self.assertIn("2 write(s) and 2 of the takeaway alone (ruling 66, 17:02) failed", out["tried"][0]["why"])
 491 | +        self.assertIn("no one clip of the angle lands", out["tried"][0]["no_voice"]["why_not"])   # then rest
 492 | +
 493 | +    def test_a_failure_on_another_line_gets_no_takeaway_alone_write(self):
 494 | +        both = dict(self.failing(), violations=[{"slot": "takeaway", "rule": "COMMENTARY", "detail": self.WHY},
 495 | +                                                {"slot": "caption", "rule": "VERDICT_NO", "detail": "x"}])
 496 | +        both["verdict"] = dict(both["verdict"], violations=both["violations"])
 497 | +        rig, out, seen, avoid = self.run_rig([both, both], [{"takeaway": {"text": "never asked", "cites": []}}])
 498 | +        self.assertIsNone(out["package"])
 499 | +        self.assertEqual((seen, avoid), ([], {}))
 500 | +
 501 | +    def test_the_no_voice_fallback_comes_after_the_takeaway_alone(self):
 502 | +        bad = ["Ultimately the network decides what it is worth.", "In the end the rules decide everything here."]
 503 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0)]
 504 | +        rig, out, seen, avoid = self.run_rig([], [{"takeaway": {"text": "Ultimately nobody bends the rules.",
 505 | +                                                                "cites": []}},
 506 | +                                                  {"takeaway": {"text": "In the end nobody bends them.", "cites": []}}],
 507 | +                                             ms=ms, takeaways=bad,
 508 | +                                             medleys=[(True, [], None, Rig.LINE), (True, [], None, Rig.LINE)])
 509 | +        self.assertEqual(len(avoid["takeaway"]), 2)                            # the takeaway alone, twice (STYLE)
 510 | +        self.assertEqual(out["tried"][0]["result"], "PACKAGE (no voice, ruling 3)")   # then ruling 3
 511 | +        self.assertEqual(rig.medley_calls[-1], ["h", "x", "y", "z"])
 512 | +
 513 | +    def test_a_title_refused_alone_gets_its_second_write_on_the_other_model_then_is_held(self):
 514 | +        """17:20: YES, the second attempt applies to a failed title too (two writes of the title alone, the second on
 515 | +        the other writer model), then hold as ruling 65 says."""
 516 | +        t1, t2 = "Rules nobody can bend", "Nobody bends these rules"
 517 | +        refused = self.failing("title", "Bitcoin is owned by nobody at all", "VERDICT_NO")
 518 | +        replies = [{"title": {"text": t1, "cites": []}}, {"title": {"text": t2, "cites": []}}]
 519 | +        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, True))
 520 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"), t2)
 521 | +        self.assertEqual(avoid, {"title": [None, {"fake:angle_write"}]})
 522 | +        second = [p for r, p in rig.prompts if r == "angle_write" and "Your title was refused" in p][1]
 523 | +        self.assertIn(f'"{t1}: ', second)                                       # told the first rewrite's refusal
 524 | +        self.assertIn("(your first rewrite of it was refused too)", second)
 525 | +        self.assertEqual(len(out["tried"][0]["attempts"][0]["rewrite"]["tries"]), 1)
 526 | +        rig, out, seen, avoid = self.run_rig([refused], replies, alone_ok=(False, False))
 527 | +        self.assertIsNone(out["package"])                                      # then held (ruling 65 c)
 528 | +        self.assertEqual(len(seen), 2)                                          # two writes of the title, no more
 529 | +        self.assertIn("the title failed alone 3 times", out["tried"][0]["why"])
 530 | +        self.assertIn("held (ruling 65 c)", out["tried"][0]["why"])
 531 | +        rig, out, seen, avoid = self.run_rig([self.failing("caption")], [{"caption": {"text": "anyone can join it.",
 532 | +                                                                                      "cites": []}}],
 533 | +                                             alone_ok=(False,))
 534 | +        self.assertEqual((len(seen), avoid), (1, {"caption": [None]}))          # the caption: one, then the fixed line
 535 | +        self.assertTrue(out["package"]["caption_fallback"])
 536 | +
 537 | +    def test_a_reply_out_of_contract_still_sends_the_second_write_to_the_other_model(self):
 538 | +        """Audit 1735 C1 (glm P1-1): the first write of the line alone answered out of contract (no line, so no gate):
 539 | +        its model is still known, and the second write avoids it."""
 540 | +        a2 = "Nobody bends these rules, and that is exactly why they keep working for everyone who holds them anywhere."
 541 | +        rig, out, seen, avoid = self.run_rig([self.failing(), self.failing()],
 542 | +                                             [{"takeaway": "not an object"}, {"takeaway": {"text": a2, "cites": []}}])
 543 | +        self.assertEqual(avoid, {"takeaway": [None, {"fake:angle_write"}]})
 544 | +        self.assertEqual(seen, [[a2]])                                          # only the second reached a gate
 545 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "takeaway"), a2)
 546 | +        self.assertEqual(rig.router.rejected, ["fake:angle_write"])             # the bad reply was rejected
 547 | +        rig, out, seen, avoid = self.run_rig([self.failing("title", "Bitcoin is owned by nobody at all", "VERDICT_NO")],
 548 | +                                             [{"title": "not an object"},
 549 | +                                              {"title": {"text": "Nobody bends these rules", "cites": []}}])
 550 | +        self.assertEqual(avoid, {"title": [None, {"fake:angle_write"}]})
 551 | +        self.assertEqual(next(x["text"] for x in out["package"]["lines"] if x["slot"] == "title"),
 552 | +                         "Nobody bends these rules")
 553 | +
 554 | +    def test_both_takeaway_prompts_name_the_two_refused_patterns(self):
 555 | +        """17:20: the takeaway writer is told the two patterns refused today, and that the line may characterise what
 556 | +        was SAID, not what WILL happen: in the full write's prompt and in the takeaway written alone."""
 557 | +        self.assertIn("SAID, never what WILL happen", PK.TAKEAWAY_SAID)
 558 | +        self.assertIn("a forecast or a permanence claim stated as fact ('Bitcoin outlasts politics.')", PK.TAKEAWAY_SAID)
 559 | +        self.assertIn("a superlative that upgrades a speaker's hedged view to a settled claim", PK.TAKEAWAY_SAID)
 560 | +        r = Canned(angle_write=[{"takeaway": {"text": "No ruler, just rules.", "cites": []}, "bridge": None,
 561 | +                                 "title": {"text": "No ruler.", "cites": ["h"]},
 562 | +                                 "caption": {"text": "three clips", "cites": []}}])
 563 | +        prompts, inner = [], r.call
 564 | +        r.call = lambda role, prompt, *a, **k: (prompts.append(prompt), inner(role, prompt, *a, **k))[1]
 565 | +        PK.write_takeaway(r, angle(["h", "x", "y"], "h"), TestWriteTakeaway.SEGS, E.Context(NOW, REG), {})
 566 | +        self.assertIn(PK.TAKEAWAY_SAID, prompts[0])
 567 | +
 568 | +    def test_which_failures_are_the_takeaways_own(self):
 569 | +        f = {"takeaway": {"text": "Bitcoin's apolitical design is the real productivity story."},
 570 | +             "title": {"text": "Apolitical money"}, "caption": {"text": "a steadier design"}, "bridge": None}
 571 | +        strong = {"segment": "clip_02", "rule": "STRONGER",
 572 | +                  "detail": "stronger certainty: the video's words 'x' make the clip sound likely"}
 573 | +        cx = lambda w: {"segments": {"clip_02": {"C": {"raising_words": w}}}}
 574 | +        own, alone = PK.takeaway_refusal(f, [strong], cx("the real productivity story"))
 575 | +        self.assertEqual((alone, own[0]["text"], own[0]["rule"]), (True, f["takeaway"]["text"], "STRONGER"))
 576 | +        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("Apolitical money"))[1], False)       # the title's
 577 | +        self.assertEqual(PK.takeaway_refusal(f, [strong], cx("apolitical"))[1], False)             # < 2 tokens
 578 | +        unsure = dict(strong, detail="stronger certainty: uncertain")
 579 | +        self.assertEqual(PK.takeaway_refusal(f, [unsure], cx("the real productivity story"))[1], False)
 580 | +        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "RUNTIME", "detail": "72 s"}])[1], True)
 581 | +        self.assertEqual(PK.takeaway_refusal(f, [{"slot": "-", "rule": "LY_SHAPE", "detail": "x"}])[1], False)
 582 | +        self.assertEqual(PK.takeaway_refusal(f, [])[1], False)                                     # no failure
 583 | +        self.assertEqual(PK.takeaway_refusal(f, [{"segment": "clip_02", "rule": "POLARITY", "detail": "x"}],
 584 | +                                             cx("the real productivity story"))[1], False)        # a clip's own
 585 | +
 586 | +
 587 |  class TestRuling65Caption(unittest.TestCase):
 588 |      """RULING 65 (12:52): A CAPTION NEVER KILLS A PACKAGE. Only the caption fails fidelity: ONE more write for the caption
 589 |      alone (a new prompt, told the refused sentence and why; the takeaway and title kept as gated); if that fails too,
 590 | 
```

---

You are auditing a change to the medley package builder on branch pp-selectid (Protocol Pulse: the builder of sealed
medley pins). Only state what you can verify from the diff; if uncertain, say so; do not guess.

Background (static):
- package.build: for a line-up whose clips pass the clips-alone verdict, a writer model writes the lines in one full
  write (write_takeaway: the TAKEAWAY, host commentary after the last clip; the TITLE; the CAPTION; a BRIDGE only at a
  join the verdict flagged). Each write is gated:
  - cheap_checks (deterministic: house style, runtime 60-70 s, R4, the deterministic fidelity layer);
  - paid_gates: the blind fidelity verdict on every line, and context integrity per clip, whose step C can find that
    the video's words make a speaker sound more certain (STRONGER);
  - coherence (the takeaway's point).
  Up to WRITES = 2 full writes.
- Writers are two Heimdall models (deepseek, qwen; vendor heimdall); judges are never the writer's vendor (law L-x).
- RULING 65 (12:52): when only the caption or the title fails, ONE write of that line alone (write_line, a new prompt
  told the refused sentence and why; the other lines kept as gated, their verdicts merged by merge_fid). Then: a
  caption gets a FIXED caption, a title is held.
- RULING 3: when the takeaway fails both writes and the clips need no bridge, the no-voice fallback may ship the clips
  with no VO line (adding one clip to land the seconds).

The orders being implemented:
- RULING 66 AMENDED (orchestrator 17:02): "a candidate whose clips pass and whose LINE failed gets, at once, up to TWO
  fresh writes of the failed line only (the writer told the refused sentence and why; the second attempt on the other
  writer model), the passing lines kept as gated ... If the takeaway still fails both, L-y's no-voice fallback applies
  if the clips meet its seconds, else rest."
- 17:20:
  - "YES, the second attempt applies to a failed title as well (two fresh writes of the failed line alone, the second
    on the other writer model), then hold as ruling 65 says."
  - "NO CHANGE to either judge." The fix is on the writer's side: "tell the takeaway writer, in its prompt, the two
    patterns that were refused today (a forecast or permanence claim stated as fact; a superlative that upgrades a
    speaker's hedged view) and that the line may characterise what was SAID, not what WILL happen."

The change (pipeline/package.py; tests in tests/package/test_medley.py):
1. The write loop is `while True`. After the full writes are spent, if the LAST write failed on the takeaway ALONE, up
   to LINE_ONLY_WRITES = 2 writes of the takeaway alone follow (write_line slot "takeaway"):
   - each is told every refused takeaway of this line-up with why (deduplicated) plus TAKEAWAY_SAID;
   - the second avoids the first's model (avoid_model = the first one's backend name);
   - the other lines (title, caption, bridge) are kept from the last write;
   - the kept lines' verdicts are kept via merge_fid when that write reached the paid gates (takeaway_alone_gates:
     the verdict on the takeaway alone, plus context integrity on the whole package); otherwise every line is judged
     (paid_gates);
   - cheap checks, coherence, the inventory and package_pin.gate_problems all run as before;
   - ruling 3's no-voice fallback runs after the loop, so after these writes.
2. takeaway_refusal(fields, violations, cx) decides "the takeaway alone". Its own failures are:
   - a violation on its slot;
   - RUNTIME or R4 on "-" (with the other lines kept, only its length moves them);
   - STRONGER / NOT_ENTAILED whose step-C cited words (raising_words / added_by) are a run of >= 2 canonical tokens
     of the takeaway and of no other line, and only when the violation's detail shows the words path.
   Anything else (another line, a clip's own failure, POLARITY, "stronger certainty: uncertain", LY_SHAPE, RECENCY)
   makes it not alone. No takeaway-alone write follows a write whose caption / title went through ruling 65's rewrite
   (last_rw65), and none when no takeaway length lands the seconds (takeaway_budget None).
3. Ruling 65's rewrite_alone, for a TITLE only:
   - up to LINE_ONLY_WRITES writes;
   - the second avoids the first's model and is told the first rewrite's refusal (rule "AGAIN");
   - then held as before, with the count in the why.
   The caption keeps one write, then the fixed caption. Ruling 65's prompts are unchanged byte for byte (the takeaway
   prompt pieces are added only for slot "takeaway").
4. TAKEAWAY_SAID, the 17:20 sentence with today's two refused examples, is in the full write's prompt (WRITE_LY) and
   in the takeaway-alone prompt.
5. Records: each takeaway-alone attempt carries "takeaway_alone" {attempt, refused}; out["takeaways"] numbers it 3, 4;
   the line-up's why counts the takeaway-alone writes; the title's rewrite record carries "tries".
6. Tests: the takeaway alone passing on attempt 1; attempt 2 on the other model; both failing (then no-voice is tried,
   else rest); another line failing (no takeaway-alone write); no-voice after the takeaway-alone writes; which failures
   are the takeaway's own; the title's second write on the other model then held (and the caption unchanged); both
   prompts carry TAKEAWAY_SAID. Mutation runs: each new behaviour removed fails its test. All 14 suites OK (medley 149).

Check, against the diff:
- that the loop always terminates (every iteration spends a write or a takeaway-alone attempt, or breaks) and never
  writes more than WRITES full writes + 2 takeaway-alone writes;
- that the takeaway-alone path can never seal a line that did not pass every gate (no gate accepts more than before:
  law: never change what a check accepts to make something pass);
- that the kept lines' verdicts are only merged when that write's lines were judged, and that merge_fid's precondition
  (the kept write's violations only on the takeaway) holds whenever it is used;
- the attribution in takeaway_refusal (false "alone" would rewrite the wrong line; false "not alone" only loses a try);
- that ruling 65's caption path and prompts are unchanged, and that the title gets exactly two writes;
- that the writer, not the judges, is what changed (no judge prompt or threshold touched).

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
