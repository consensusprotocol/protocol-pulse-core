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
- **glm P2-7** (write_calls == 2 against "then the line alone"): Rig.write_calls counts the full writes
  (write_takeaway's stub). The takeaway alone goes through write_line, so the router; the test counts it through the
  spy.

## Recorded (cosmetic or intended), no change

- glm P2-1: 240 characters vs the word budget. Fail-closed; the cheap gates judge the words.
- glm P2-2: a COHERENCE refusal's detail differs from a verdict's. Prompt length only.
- glm P2-3: words in both the takeaway and the bridge make it not alone. Intended: never rewrite a line that would
  not fix it.
- glm P2-4: `now` None in takeaway_alone_gates. The same guard as paid_gates; build always passes ctx.now.
- glm P2-5: the AGAIN entry may carry a package-level reason. Prompt wording only.
- glm P2-6: the takeaway_alone counter on a "no length lands it" break. Record wording only.
- WRITE_LY.format has one caller (package.py:1574, verified by grep).

## Suites (scratch copy at HEAD 94b367e1 + this diff)

All 14 OK (medley 150, candidates 10, ledger_build 35, visual_pin 11, attest 7, speakers 23, providers 16, gates 18,
angles 28, moments 7, eligibility 30, hook_onset 9, house_style 23, select_by_id 27).
