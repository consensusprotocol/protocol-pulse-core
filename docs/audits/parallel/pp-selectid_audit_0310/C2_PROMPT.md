# PROTOCOL PULSE — CYCLE 2 CODE AUDIT
# Feature: pp-selectid-0310
# You are performing your SECOND review of this code.
# You now have access to what the other AI models said in Cycle 1.

---

## YOUR CYCLE 1 OUTPUT (what you said before)
[See below — you wrote this]

## WHAT THE OTHER MODELS SAID (Cycle 1)
## GLM-5.3-FLASH — CYCLE 1 OUTPUT
# glm-5.3-flash (z-ai/glm-5.3-flash) 79 s finish=stop usage in 11202 / out 2240 usd~0.067 (upper-bound price)

# Audit: pp-selectid — STAND_ALONE at the pin stage

## P0

None found.

## P1

**P1-1 — `stand_alone_check` builds the EDL with keys the render's EDL may not have; fidelity to the render's call is asserted, not proven.** `pipeline/package.py:17-20` (diff lines 17–20). The EDL passed to `SA.check_edl` is `{"hook": {"text", "channel"}, "clips": [{"index", "text", "channel", "duration"}]}`. Whether `check_edl` reads `channel`/`duration` (and whether their absence or a different key name in the render's real EDL changes the opener/topic verdicts) cannot be verified from this diff — `stand_alone.py` is not shown. The claim "reproduces the render's check_edl call exactly" rests on the module being byte-identical (stated, not in the diff) and on the test at diff lines 194–200, which pins the held pin's verdicts — good, but that test exercises only the `text`-only path. Scenario: if `check_edl`'s topic check reads a field this EDL omits (e.g. a per-clip `subject` override), the pin-stage row could PASS a line-up the render holds — violating the stated invariant. **Condition: confirm (or add a test) that `check_edl`'s verdict depends only on `text` (+ the passed `subject`/`rate`) for this EDL shape.** Uncertain; flagged, not asserted.

**P1-2 — `no_role_on_screen`'s "no role" rule is stricter than the render's, and the diff does not prove the dropped moment could not have been the hook.** `pipeline/package.py:23-30` + `61-62`. A moment is dropped when it fails `SA.opener("clip", …)` **and** `SA.opener("hook", …)`. But the render's `check_edl` (per the held-pin output) evaluates the hook's opener **and** its topic; `no_role_on_screen` checks the hook's *opener only*, not whether the moment would pass the hook's topic check. That direction is safe (dropping more than the render would hold is the stricter, allowed direction). However, the clip-side check uses `SA.opener("clip", …)` alone, while the render's clip FAIL also cites the scorer ("the clip scorer does not affirm it", 3.0). With `rate=None` the scorer never affirms, so opener-only is the *correct* fail-closed reading — but this equivalence (opener-fail ⇒ check_edl-fail when rate=None) is asserted in the docstring, not demonstrated in the diff. If `check_edl` with `rate=None` ever passes a conjunction opener by another path, `no_role` would drop a usable moment (over-strict, P2-territory) — or, worse, if `opener`'s PASS is weaker than `check_edl`'s clip verdict, a moment could survive `no_role` yet fail the sealed `stand_alone` row later; that case is caught by the gate, so it fails closed. Acceptable; noted.

**P1-3 — `inventory`'s `stand` row: `stand.get("ok") is True` is correct fail-closed, but the evidence rows read `r['opener']['why']` and `r['topic']['why']` unguarded.** `pipeline/package.py:135-136` (diff lines 133–137). `rows=[f"…{r['opener']['why']} | topic: {r['topic']['why']}"…]` — if `check_edl`'s row for a failing segment omits `opener` or `topic` (shape not shown in this diff), this raises inside `inventory`, i.e. inside `build()`. Under M12 fail-closed an exception rejects, so it is not a silent pass, but it converts a measurable FAIL into a crash rather than a FAIL row. The test at diff lines 226–236 only covers the all-PASS path (`len(g["rows"]) == 3`, status PASS); **no test exercises the FAIL-row evidence path** (the test at 238–244 builds the gates dict by hand, bypassing `inventory`). Condition: one test where `stand_alone_check` returns a failing row and `inventory` still produces a well-formed FAIL row.

## P2

**P2-1 — `MEDLEY_GATES` grows, but `required_gates(pk)` gating is unverified for non-medley shapes.** `pipeline/package_pin.py:153`. `MEDLEY_GATES` now includes `"stand_alone"`; the test (diff 166–167, 174–178) asserts the last five entries and that each missing row refuses the pin. But whether `required_gates` returns `MEDLEY_GATES` only for `shape == "medley"` (and what it returns otherwise) is not in the diff. If some other shape accidentally inherits MEDLEY_GATES, older non-medley pins would newly require a `stand_alone` row. The stated intent ("the integrator's recompute checks REQUIRED_GATES only, so older pins still recompute") suggests this is handled, but it is not verifiable here. Low risk.

**P2-2 — `no_role` filtering happens before `prescreen`, changing `out["usable"]` semantics.** `pipeline/package.py:61-67, 72-74`. `ms` is filtered, then `out["usable"] = len(ms)` counts only post-`no_role` moments, while the log line reports "N usable (M more left out…)" — the count semantics changed (previously `usable` = post-`usable()`; now = post-`usable()` minus `no_role`). Any downstream consumer of `out["usable"]` (dashboards, budget math, tests) that assumed the old meaning will see a smaller number. Also `no_role` is a dict keyed by `moment_id` built via the `for r in [no_role_on_screen(m)]` trick — correct but de

## GROK-4.20-0309-REASONING — CYCLE 1 OUTPUT
# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 97 s finish=stop usage in 11249 / out 574 usd~0.071 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:17 (stand_alone_check): edl construction and call to SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin")) exactly matches the render's validate-stage call (hook first, then ordered clips with index/labeling implied by check_edl, rate=None, bitcoin subject). Reproduces the exact PASS/FAIL/FAIL verdicts on the held pin d2657bbe texts (test:195).
- pipeline/package.py:28 (no_role_on_screen): calls both SA.opener("clip", ...) and SA.opener("hook", ...) with rate=None semantics; returns non-None (drops) *only* for conjunction/reply-fragment openers that fail both roles. Pronoun openers that fail hook but pass clip return None (test:205). Matches "drops ONLY moments that can be neither".
- pipeline/package.py:52,93,107 and inventory:134: stand_alone_check result is threaded into every medley package's gates row (PASS only if ["ok"] is True; rows evidence captured; unmeasured/missing/FAIL never produces PASS). package_pin.py:153 and test:166 confirm required_gates now includes "stand_alone"; missing row or FAIL refuses pin (test:244).
- pipeline/package.py:61,92,96 and build(): no_role filter runs immediately after usable(), before prescreen/angle/vendor calls (test:233 verifies bad moment never reaches angle_write). lineup_for(need_stand_alone=True) skips any candidate that fails the check (including pronoun-hook fallback and no-Bitcoin-subject cases); never seals a lineup the render's check_edl(rate=None) would reject.
- All existing checks (usable, prescreen, coherence, hook_onset, etc.) and acceptance criteria are untouched; this is strictly additive stricter pre-filter + gate (complies with "never change what an EXISTING check accepts", L-m, L-j, "pin must never seal a lineup render would hold").
- tests/package/test_medley.py:194-257: new TestStandAloneAtThePinStage exercises every stated behavior, the held-pin reproduction, no_role rule, lineup selection change, build() filtering, gate row, and pin refusal on FAIL. Existing tests updated only for the new required gate.

No violations of any listed governing law visible in the diff (L-a through L-l, M2, M12, LAW 20/22, pin-stage rules). Hard-coded bitcoin subject matches the provided "for a pinned moments package labelled 'bitcoin'" context; no other subjects appear in diff. Imports inside functions and "smallest diff" constraints followed. No renderer/compositor/selector changes.

**SHIP: yes**

## QWEN3.8-27B — CYCLE 1 OUTPUT
# qwen3.8-27b (qwen/qwen3.8-27b) 47 s finish=stop usage in 12199 / out 1521 usd~0.059 (upper-bound price)

# Audit: pp-selectid-0310 (C1_STEP.diff)

## P0 Findings
None.

## P1 Findings

**1. `pipeline/package.py:10-20` — `stand_alone_check` hardcodes the subject, violating the "reproduce the render's call exactly" requirement.**
The function calls `SA.subject_terms("", "bitcoin")` with a hardcoded `"bitcoin"`. The render's `run_fresh.stage_validate` derives the subject from the package's label (e.g., `run_fresh.stand_alone_subject`). If a future package is labeled with a different subject (e.g., `"etf"`, `"macro"`), the pin-stage check will test against `{bitcoin, btc}` while the render tests against the actual subject. This creates a divergence where:
- A line-up that passes the render's topic check (names the actual subject) but fails the pin's topic check (doesn't name "bitcoin") will be **refused at pin** even though the render would accept it. This is a false negative (overly strict), which is safe but breaks the "reproduce exactly" contract.
- Conversely, if the render's subject logic changes, the pin won't track it.

**Mitigation:** The current codebase appears to only produce "bitcoin"-labeled packages, so this is latent. However, the docstring claims it reproduces the render's call "exally," which is false for non-bitcoin subjects. Either parameterize the subject or document the limitation explicitly.

**2. `pipeline/package.py:23-30` — `no_role_on_screen` may over-drop moments due to asymmetric hook/clip opener rules.**
The function drops a moment if it fails **both** `SA.opener("clip", text)` and `SA.opener("hook", text)`. The test at line 205-206 confirms that pronoun openers (e.g., "It is Bitcoin.") pass as clips but fail as hooks, so they are **not** dropped. This is correct. However, the logic assumes that `SA.opener` with `rate=None` is deterministic and that the clip/hook rules are the only factors. If `SA.opener` has other failure modes (e.g., length, punctuation) that differ between clip and hook roles, a moment could be dropped even though it would pass in one role under the render's scorer. The render's scorer (`rate` parameter) can affirm a clip that fails the no-scorer check, so `no_role_on_screen` is **stricter** than the render. This is safe (fail-closed) but may reduce available moments unnecessarily.

**3. `pipeline/package.py:52-53` — `lineup_for` with `need_stand_alone=True` may skip valid line-ups due to the stricter no-scorer check.**
When `need_stand_alone=True`, a candidate line-up is skipped if `stand_alone_check` fails. Since `stand_alone_check` uses `rate=None`, it is stricter than the render (which may use a scorer to affirm a conjunction opener). This means the pin stage may refuse a line-up that the render would accept. This is safe (fail-closed) but may reduce the number of valid line-ups. The test at line 213-214 confirms this: the old pick `["h", "b", "x"]` (where "b" opens with "But") is replaced by `["h", "x", "y"]` when `need_stand_alone=True`. This is the intended behavior, but it means the pin stage is **more restrictive** than the render, which is a divergence from "reproduce exactly."

## P2 Findings

**4. `pipeline/package.py:133-137` — The `stand_alone` gate row's evidence format is verbose and may be hard to parse.**
The `rows` field is a list of strings like `"clip_01: FAIL opener: clip opens on 'but' | topic: names the subject (bitcoin)"`. This is human-readable but not machine-parseable. If downstream tools need to extract per-segment pass/fail status, they must parse the string. Consider using a structured format (e.g., a list of dicts) for the evidence.

**5. `pipeline/package_pin.py:153` — `MEDLEY_GATES` now includes `"stand_alone"`, but `REQUIRED_GATES` does not.**
This is correct: `stand_alone` is only required for medleys, not for all packages. However, the comment at line 150-152 is dense and may be hard to maintain. Consider splitting the comment into separate lines for each gate.

**6. `tests/package/test_medley.py:194-200` — The test hardcodes the render's `run_log.txt` lines 47-49.**
The test asserts that `stand_alone_check` produces the same verdicts as the render's log. This is a good regression test, but it couples the test to the specific log file. If the render's log format changes, the test will break. Consider extracting the expected verdicts into a fixture or constant.

**7. `tests/package/test_medley.py:226-236` — The test `test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row` uses a `Rig` class that is not defined in the diff.**
The test references `Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])` and `rig.run()`, but the `Rig` class is not shown in the diff. This is likely defined elsewhere in the test file, but it is not clear from the diff alone. If `Rig` is a new helper, it should be included in the diff for auditability.

## SHIP: yes with conditions

**Conditions:**
1. **Parameterize th

## CLAUDE'S CYCLE 1 CONSENSUS
# pp-selectid audit 0310 (the render's STAND_ALONE at the pin stage): cycle 1 consensus

Synthesis by the pp-selectid session, 03:13 ET Nov 13, written before cycle 2.

**Run.** C1_STEP.diff covers package.py, package_pin.py and test_medley.py. No P0. Verdicts:
- grok-4.20-0309-reasoning (xAI): no P0 and no P1, "SHIP: yes";
- qwen/qwen3.8-27b (Heimdall, effort none): "SHIP: yes with conditions";
- z-ai/glm-5.3-flash (Heimdall, effort none): "SHIP: yes with conditions".

## Consensus

| # | finding (reviewers) | disposition |
|---|---|---|
| K1 | Is stand_alone_check an exact copy of the render's call? Do the EDL shape and the fixed subject match (glm P1-1, qwen P1-1)? | VERIFIED, and stated in the docstring. pipeline/stand_alone.py is byte-identical to main's at 5be6f301 (`diff` exit 0). check_edl (stand_alone.py:99-123) passes `s.get("text")` to opener() and topical(). Channel and duration go only into the scorer's passages, which are unused with rate=None. The labels come from the order (`clip_{index:02d}`). The subject: main run_fresh.stand_alone_subject returns subject_terms("", "bitcoin") for a bound pinned moments EDL labelled 'bitcoin', and package_pin.to_pin sets "label": "bitcoin" for every moments pin (package_pin.py:179). The reproduction test pins the render's own verdicts on the held pin (run_log.txt lines 47-49). |
| K2 | No test drives the FAIL path through inventory()'s evidence rows (glm P1-3) | IMPLEMENTED: test_inventory_writes_a_FAIL_row_with_its_evidence. inventory(stand=<failing check>) writes a FAIL row with one evidence line per segment; with stand=None the row is absent, which refuses the pin. check_edl always gives every row an "opener" and a "topic" dict, each with "why" (stand_alone.py:116-121), so the evidence lines cannot raise. |
| K3 | Is `import stand_alone` GPU-free (glm P2-4)? | VERIFIED. stand_alone.py imports only `re` at module level, and canon lazily inside _words(). The GPU scorer lives in story_semantics.LocalLLM, which stand_alone never imports; only the render's rate() closure in run_fresh imports it. |
| K4 | out["usable"] changed meaning (glm P2-2) | IMPLEMENTED: out["usable"] is again the count after usable(). The moments left out are counted in out["no_role"] and on the log line ("N usable, M of them left out ..."). |

## Unique findings: answered or kept

- **qwen P1-2 and P1-3 (stricter than the render):** KEPT, as intended and stated in the docstrings. With no scorer, a conjunction or reply-fragment opener fails closed, so the pin stage never seals a line-up that the render's scorer would have to rescue. A pronoun opener stays in play, and test_a_moment_opening_on_a_conjunction_or_reply_fragment_has_no_role covers that.
- **qwen P2-4 (machine-parseable rows):** KEPT as text. The row's "status" is what is machine-checked (gate_problems); the rows are human evidence in the render's own wording.
- **qwen P2-5 (the comment is dense):** DONE. The MEDLEY_GATES comment is three lines, one per origin.
- *

---

## THE CODE NOW: the FIXED diff
## THE CODE (every new and modified file)

### File: docs/audits/parallel/pp-selectid_audit_0310/C2_STEP.diff (278 lines)
```
   1 | diff --git a/pipeline/package.py b/pipeline/package.py
   2 | index 74ea177c..34d800de 100644
   3 | --- a/pipeline/package.py
   4 | +++ b/pipeline/package.py
   5 | @@ -553,7 +553,34 @@ def check_angles(obj, by_id, k=MAX_ANGLES):
   6 |      return out
   7 |  
   8 |  
   9 | -def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False):
  10 | +def stand_alone_check(segs):
  11 | +    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) on one line-up, at the pin stage
  12 | +    (the integrator held pin d2657bbe on it, 03:00 ET Nov 13): the hook, then the clips in play order (clip_01, ...), the
  13 | +    subject Bitcoin (run_fresh.stand_alone_subject for a pinned moments package labelled 'bitcoin'), and NO clip scorer.
  14 | +    The render's scorer is a local model on GPU0, which this stage may not use, so a clip that opens on a conjunction or
  15 | +    a reply fragment fails closed here, as check_edl does without one: never sealed for the scorer to rescue.
  16 | +    check_edl's verdict reads only each segment's text, the subject and rate (channel and duration feed only the
  17 | +    scorer's passages, unused with rate=None; the labels come from the order). The subject is fixed because
  18 | +    package_pin.to_pin labels every moments pin 'bitcoin' (audit 0310 C1, glm P1-1 / qwen P1-1)."""
  19 | +    import stand_alone as SA
  20 | +    edl = {"hook": {"text": segs[0]["text"], "channel": segs[0].get("channel_name")},
  21 | +           "clips": [{"index": i, "text": m["text"], "channel": m.get("channel_name"), "duration": m.get("duration_s")}
  22 | +                     for i, m in enumerate(segs[1:], 1)]}
  23 | +    return SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin"))
  24 | +
  25 | +
  26 | +def no_role_on_screen(m):
  27 | +    """Why a moment can take NO place in a line-up under the render's STAND_ALONE opener rule with no clip scorer (it
  28 | +    opens on a conjunction or a reply fragment: the clip role fails closed without the scorer, the hook role fails on
  29 | +    it), else None. build() leaves such moments out before any vendor call."""
  30 | +    import stand_alone as SA
  31 | +    c_ok, c_why = SA.opener("clip", m.get("text"))
  32 | +    h_ok, h_why = SA.opener("hook", m.get("text"))
  33 | +    return None if (c_ok or h_ok) else f"the render's STAND_ALONE with no clip scorer at the pin stage: {c_why}; {h_why}"
  34 | +
  35 | +
  36 | +def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, repeat_ok=False, need_onset=False,
  37 | +               need_stand_alone=False):
  38 |      """The hook + clips[0]..clips[1] clips for one angle, in the PROPOSER'S PLAY ORDER (L-y 3: the order carries a
  39 |      medley): the proposer's hook (else the angle's best hook-eligible moment by its first 2 s), the clips from the
  40 |      angle's other moments, every segment from a different channel (L-u), at most PRICE_PREDICTIONS_MAX price
  41 | @@ -563,7 +590,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  42 |      seconds nearest the middle of crange. repeat_ok (L-y 4, only when one clip per channel cannot fill the runtime):
  43 |      ONE channel may give two clips, from two different videos. need_onset (build() sets it): a moment opens the
  44 |      medley only if its hook onset was measured and passed (hook_onset_for, G17a at the pin stage); the proposer's hook
  45 | -    gives way to the angle's next one that did. None if impossible."""
  46 | +    gives way to the angle's next one that did. need_stand_alone (build() sets it): every line-up must pass the render's
  47 | +    STAND_ALONE (stand_alone_check). None if impossible."""
  48 |      lo, hi = crange or medley_content_range()
  49 |      pos = {m: i for i, m in enumerate(angle["moments"])}
  50 |      ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]
  51 | @@ -588,6 +616,8 @@ def lineup_for(angle, by_id, dropped=frozenset(), clips=LY_CLIPS, crange=None, r
  52 |                  dur = h["duration_s"] + sum(m["duration_s"] for m in order)
  53 |                  if not lo <= dur <= hi:
  54 |                      continue
  55 | +                if need_stand_alone and not stand_alone_check([h] + order)["ok"]:
  56 | +                    continue
  57 |                  key = (-sum(pos[m["moment_id"]] for m in order), -abs(dur - (lo + hi) / 2))
  58 |                  if best is None or key > best[0]:
  59 |                      best = (key, [h] + order)
  60 | @@ -991,15 +1021,20 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  61 |      t0 = time.time()
  62 |      usd0 = _spent(spend)
  63 |      ms, why = usable(moments, ctx, delivered, optout)
  64 | +    n_usable = len(ms)                                 # out["usable"] keeps its meaning (audit 0310 C1, glm P2-2)
  65 | +    no_role = {m["moment_id"]: r for m in ms for r in [no_role_on_screen(m)] if r}
  66 | +    ms = [m for m in ms if m["moment_id"] not in no_role]
  67 |      wv, wf = _writers(router)
  68 |      a_by, fails, a_vendors, a_families = prescreen(router, ms, sources, ctx, wv, wf, store=store, log=log)
  69 |      cleared = {m["moment_id"]: m for m in ms if m["moment_id"] in a_by and not fails.get(m["moment_id"])}
  70 |      levels = current_levels(sources.values(), ctx)
  71 | -    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": len(ms), "current_levels": levels,
  72 | +    out = {"shape": "medley", "packages": [], "tried": [], "unusable": why, "usable": n_usable, "current_levels": levels,
  73 | +           "no_role": no_role,
  74 |             "prescreen": {"screened": len(fails), "cleared": len(cleared),
  75 |                           "failed": {mid: f for mid, f in fails.items() if f}}, "angles": [], "takeaways": [],
  76 |             "package": None}
  77 | -    log(f"  {len(ms)} usable, {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  78 | +    log(f"  {n_usable} usable, {len(no_role)} of them left out (they open on a conjunction or reply fragment, which "
  79 | +        f"the render's STAND_ALONE fails with no clip scorer), {len(cleared)} cleared step A ({time.time() - t0:.0f} s)")
  80 |      if len({m["channel_id"] for m in cleared.values()}) < 3:
  81 |          out["why_none"] = f"{len(cleared)} moments cleared step A from fewer than 3 channels"
  82 |          return out
  83 | @@ -1144,7 +1179,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  84 |          pk["gates"] = inventory(fid, dup, rt_ok, r4_res, cx, a_lab, {k: v for k, (v, _) in got.items()},
  85 |                                  {k: v for k, (_, v) in got.items()}, True, coh, medley=(True, nv_med),
  86 |                                  shape=ly_shape(pk), style=HS.lint_lines(pk["lines"]),
  87 | -                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
  88 | +                                hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
  89 | +                                stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
  90 |          import package_pin
  91 |          problems = package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk))
  92 |          if problems:
  93 | @@ -1167,9 +1203,11 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
  94 |              while n_lineup < lineups and not out["packages"] and not out.get("budget_stop"):
  95 |                  if over_budget(ai):
  96 |                      break
  97 | -                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True), None
  98 | +                segs, exception = lineup_for(angle, cleared, frozenset(dropped | doomed), need_onset=True,
  99 | +                                             need_stand_alone=True), None
 100 |                  if segs is None:                          # L-y 4: one clip per channel unless the supply forces otherwise
 101 | -                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True)
 102 | +                    segs = lineup_for(angle, cleared, frozenset(dropped | doomed), repeat_ok=True, need_onset=True,
 103 | +                                     need_stand_alone=True)
 104 |                      if segs is not None:
 105 |                          rep = [c for c in dict.fromkeys(m["channel_id"] for m in segs)
 106 |                                 if sum(m["channel_id"] == c for m in segs) > 1]
 107 | @@ -1319,7 +1357,8 @@ def build(router, moments, sources, ctx, delivered=(), optout=frozenset(), log=p
 108 |                                              {k: v for k, (v, _) in got.items()}, {k: v for k, (_, v) in got.items()},
 109 |                                              ok_c, coh, medley=(ok_m, med), shape=ly_shape(pk),
 110 |                                              style=HS.lint_lines(pk["lines"]),
 111 | -                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"))
 112 | +                                            hook=(cleared.get(pk["segments"][0]["moment_id"]) or {}).get("hook_onset"),
 113 | +                                            stand=stand_alone_check([cleared[sg["moment_id"]] for sg in pk["segments"]]))
 114 |                      if not ok_c:
 115 |                          tl = coh.get("through_line") if isinstance(coh.get("through_line"), str) else ""
 116 |                          if coh.get("measured") and type(coh.get("vo_point")) is int and \
 117 | @@ -1378,12 +1417,14 @@ def _spent(spend):
 118 |  
 119 |  
 120 |  def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medley=None, shape=None, style=None,
 121 | -              hook=None):
 122 | +              hook=None, stand=None):
 123 |      """The sealed GATE INVENTORY (audit p2 C1; package_pin.required_gates): one row per hard gate, each
 124 |      {"status": "PASS" | "FAIL" | "NOT RUN", "by", "replayed", "n"}. Nothing measured is never a PASS (law L-m).
 125 |      A medley (L-y) adds two rows: "medley" (the blind clips-alone verdict, medley=(ok, verdict)) and "ly_shape"
 126 |      (shape=(ok, [why]) from ly_shape()). hook: the hook moment's hook_onset record -> the "hook_onset" row (G17a at
 127 | -    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin."""
 128 | +    the pin stage, required for a medley: package_pin.MEDLEY_GATES); None leaves it out, which refuses the pin.
 129 | +    stand: stand_alone_check() of the package's segments in play order -> the "stand_alone" row (the render's
 130 | +    STAND_ALONE at the pin stage, required for a medley); None leaves it out, which refuses the pin."""
 131 |      row = lambda ok, by, replayed=False, n=1, measured=True: {
 132 |          "status": "NOT RUN" if not measured or n < 1 else ("PASS" if ok else "FAIL"), "by": by,
 133 |          "replayed": replayed if isinstance(replayed, bool) else None, "n": n}     # None (unstated) refuses the pin
 134 | @@ -1443,4 +1484,9 @@ def inventory(fid, dup, rt_ok, r4_res, ctx_, a_by, exc, truth, coh_ok, coh, medl
 135 |                                     "on the source audio: G17a at the pin stage)", measured=hook.get("measured") is True),
 136 |                                 lead_ms=hook.get("lead_ms"), cut_in=hook.get("cut_in"), why=hook.get("why"))}
 137 |             if hook is not None else {}),
 138 | +        **({"stand_alone": dict(row(stand.get("ok") is True, "stand_alone.check_edl (the render's STAND_ALONE at the pin "
 139 | +                                    "stage; no clip scorer, so a conjunction or reply-fragment opener fails closed)"),
 140 | +                                rows=[f"{r['segment']}: {'PASS' if r['pass'] else 'FAIL'} opener: {r['opener']['why']} | "
 141 | +                                      f"topic: {r['topic']['why']}" for r in stand.get("rows") or []])}
 142 | +           if stand is not None else {}),
 143 |      }
 144 | diff --git a/pipeline/package_pin.py b/pipeline/package_pin.py
 145 | index d975d12f..6c15c3b0 100644
 146 | --- a/pipeline/package_pin.py
 147 | +++ b/pipeline/package_pin.py
 148 | @@ -26,9 +26,10 @@ from datetime import datetime, timezone
 149 |  SCHEMA = "protocol_pulse.pinned_story.v1"
 150 |  REQUIRED_GATES = ("vo_fidelity_deterministic", "vo_fidelity_verdict", "duplicate", "price_now", "runtime", "r4",
 151 |                    "context_a", "context_b", "context_c", "exclusion", "second_pass", "cuttable", "coherence")
 152 | -MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset")   # hook_onset: G17a at the pin stage, after
 153 | -                                                                      # batch pin #1's render hold (01:39 ET Nov 13)   # L-y (20:30): the clips-alone verdict, the medley's shape;
 154 | -                                                         # ruling 6 (22:40): PBX's copy rules on every line
 155 | +# L-y (20:30): the clips-alone verdict and the medley's shape; ruling 6 (22:40): PBX's copy rules on every line;
 156 | +# hook_onset: G17a at the pin stage, after batch pin #1's render hold (01:39 ET Nov 13); stand_alone: the render's
 157 | +# STAND_ALONE at the pin stage, after pin d2657bbe's hold at the integrator's validate (03:00 ET Nov 13)
 158 | +MEDLEY_GATES = ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone")
 159 |  
 160 |  
 161 |  def required_gates(pk):
 162 | diff --git a/tests/package/test_medley.py b/tests/package/test_medley.py
 163 | index 6501f65f..0193b7a9 100644
 164 | --- a/tests/package/test_medley.py
 165 | +++ b/tests/package/test_medley.py
 166 | @@ -368,14 +368,15 @@ class TestMedleyPackageAndPin(unittest.TestCase):
 167 |  
 168 |      def test_the_pin_requires_the_medley_rows_and_carries_intro_null(self):
 169 |          pk = self.build()
 170 | -        self.assertEqual(package_pin.required_gates(pk)[-4:], ("medley", "ly_shape", "house_style", "hook_onset"))
 171 | +        self.assertEqual(package_pin.required_gates(pk)[-5:], ("medley", "ly_shape", "house_style", "hook_onset",
 172 | +                                                               "stand_alone"))
 173 |          pk["gates"] = self.gates(pk)
 174 |          pin = package_pin.to_pin(spk(pk), "test")
 175 |          mp = pin["moments_package"]
 176 |          self.assertEqual(mp["edl_vo"], {"intro": None, "bridges": [{"text": pk["vo"]["bridges"][0], "after_clip": 2}]})
 177 |          self.assertEqual(mp["vo_jobs"], {"takeaway": "takeaway"})
 178 |          self.assertEqual(mp["shape"], "medley")
 179 | -        for missing in ("medley", "ly_shape", "house_style", "hook_onset"):
 180 | +        for missing in ("medley", "ly_shape", "house_style", "hook_onset", "stand_alone"):
 181 |              g = self.gates(pk)
 182 |              g.pop(missing)
 183 |              with self.assertRaises(package_pin.PinRefused):
 184 | @@ -643,6 +644,83 @@ class TestBuildLoop(unittest.TestCase):
 185 |          self.assertEqual(pk["gates"]["ly_shape"]["status"], "PASS")
 186 |  
 187 |  
 188 | +class TestStandAloneAtThePinStage(unittest.TestCase):
 189 | +    """The render's STAND_ALONE (main run_fresh.stage_validate -> stand_alone.check_edl) at the pin stage, after the
 190 | +    integrator held pin d2657bbe on it (03:00 ET Nov 13): no clip scorer here (it is a local model on GPU0), so a clip
 191 | +    opening on a conjunction or reply fragment fails closed, and no line-up the render would hold is sealed."""
 192 | +
 193 | +    HOOK = ("Bitcoin is the one piece of open source technology that can't be shut down, silenced or removed. If Bitcoin "
 194 | +            "wins, open source wins.")
 195 | +    BUT1 = "But we have very rarely in Bitcoin's history seen six negative weeks back to back. I think that was six."
 196 | +    BUT2 = ("But then if someone doesn't understand Bitcoin and you drop 25 % of their portfolio in Bitcoin and Bitcoin "
 197 | +            "goes down 50%. You get fired and they sell their Bitcoin.")
 198 | +
 199 | +    def test_it_gives_the_renders_verdicts_on_the_held_pin_d2657bbe(self):
 200 | +        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": self.BUT1}, {"text": self.BUT2}])
 201 | +        self.assertFalse(r["ok"])
 202 | +        self.assertEqual([(x["segment"], x["pass"]) for x in r["rows"]],     # the render's run_log.txt lines 47-49
 203 | +                         [("hook", True), ("clip_01", False), ("clip_02", False)])
 204 | +        self.assertIn("clip opens on 'but'", r["rows"][1]["opener"]["why"])
 205 | +        self.assertEqual(r["subject"], ["bitcoin", "btc"])
 206 | +
 207 | +    def test_a_moment_opening_on_a_conjunction_or_reply_fragment_has_no_role(self):
 208 | +        for t in (self.BUT1, "And Bitcoin is money.", "Yeah, Bitcoin is money.", "Well, Bitcoin is money."):
 209 | +            self.assertIn("STAND_ALONE", PK.no_role_on_screen({"text": t}) or "", t)
 210 | +        for t in ("I think Bitcoin is money.", "Bitcoin is money.", "It is Bitcoin."):   # a pronoun opens a clip
 211 | +            self.assertIsNone(PK.no_role_on_screen({"text": t}), t)
 212 | +
 213 | +    def test_no_line_up_holds_a_clip_the_render_would_hold(self):
 214 | +        by = {m["moment_id"]: m for m in (dict(pm("h", "A", 12.0), text=self.HOOK), dict(pm("b", "B", 14.0), text=self.BUT1),
 215 | +                                          dict(pm("x", "C", 13.0), text="Bitcoin x."),
 216 | +                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
 217 | +        a = angle(["h", "b", "x", "y"], "h")
 218 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by)], ["h", "b", "x"])     # the old pick
 219 | +        self.assertEqual([m["moment_id"] for m in PK.lineup_for(a, by, need_stand_alone=True)], ["h", "x", "y"])
 220 | +        no_subject = dict(by, y=dict(by["y"], text="Gold is money."), x=dict(by["x"], text="Gold x."))
 221 | +        self.assertIsNone(PK.lineup_for(a, no_subject, need_stand_alone=True))   # topical: no clip names Bitcoin
 222 | +
 223 | +    def test_a_pronoun_hook_gives_way_to_the_next_hook(self):
 224 | +        by = {m["moment_id"]: m for m in (dict(pm("p", "A", 12.0), text="It is the hardest money. Bitcoin is."),
 225 | +                                          dict(pm("h", "B", 12.0), text=self.HOOK), dict(pm("x", "C", 14.0), text="Bitcoin x."),
 226 | +                                          dict(pm("y", "D", 13.0), text="Bitcoin y."))}
 227 | +        a = angle(["p", "h", "x", "y"], "p")
 228 | +        self.assertEqual(PK.lineup_for(a, by)[0]["moment_id"], "p")
 229 | +        self.assertEqual(PK.lineup_for(a, by, need_stand_alone=True)[0]["moment_id"], "h")
 230 | +
 231 | +    def test_build_leaves_no_role_moments_out_before_the_angle_and_seals_the_row(self):
 232 | +        ms = [pm("h", "A", 12.0), pm("x", "B", 14.0), pm("y", "C", 13.0), pm("z", "D", 13.0),
 233 | +              dict(pm("b", "E", 13.0), text=self.BUT1)]
 234 | +        rig = Rig(ms, ["h", "x", "y", "z"], [(True, [], None, Rig.LINE)], [None])
 235 | +        out = rig.run()
 236 | +        self.assertEqual(list(out["no_role"]), ["b"])
 237 | +        self.assertIn("clip opens on 'but'", out["no_role"]["b"])
 238 | +        self.assertFalse(any("id=b " in p for role, p in rig.prompts if role == "angle_write"))
 239 | +        g = out["package"]["gates"]["stand_alone"]
 240 | +        self.assertEqual(g["status"], "PASS")
 241 | +        self.assertEqual(len(g["rows"]), 3)
 242 | +
 243 | +    def test_inventory_writes_a_FAIL_row_with_its_evidence(self):     # audit 0310 C1, glm P1-3
 244 | +        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": "Bitcoin x."}, {"text": self.BUT2}])
 245 | +        fid = {"deterministic": {"ok": True, "violations": [], "price_now_measured": True}, "verdict": {"ok": True},
 246 | +               "backend": "x", "replayed": False, "measured": True}
 247 | +        g = PK.inventory(fid, [], True, (True,), {"ok": True, "measured": True, "replayed": False}, {}, {}, {}, True,
 248 | +                         {"measured": True, "replayed": False}, stand=r)["stand_alone"]
 249 | +        self.assertEqual(g["status"], "FAIL")
 250 | +        self.assertEqual([x.split(":")[0] for x in g["rows"]], ["hook", "clip_01", "clip_02"])
 251 | +        self.assertIn("clip_02: FAIL opener: clip opens on 'but'", g["rows"][2])
 252 | +        self.assertNotIn("stand_alone", PK.inventory(fid, [], True, (True,), {"ok": True, "measured": True,
 253 | +                                                                                 "replayed": False}, {}, {}, {}, True,
 254 | +                                                         {"measured": True, "replayed": False}))
 255 | +
 256 | +    def test_the_row_fails_and_the_pin_is_refused_when_a_clip_opens_on_a_conjunction(self):
 257 | +        r = PK.stand_alone_check([{"text": self.HOOK}, {"text": "Bitcoin x."}, {"text": self.BUT2}])
 258 | +        self.assertFalse(r["ok"])
 259 | +        pk = {"shape": "medley"}
 260 | +        gates = {k: {"status": "PASS", "by": "x", "replayed": False, "n": 1} for k in package_pin.required_gates(pk)}
 261 | +        gates["stand_alone"] = {"status": "PASS" if r["ok"] else "FAIL", "by": "x", "replayed": False, "n": 1}
 262 | +        self.assertEqual(package_pin.gate_problems(gates, package_pin.required_gates(pk)), ["stand_alone: FAIL"])
 263 | +
 264 | +
 265 |  class TestNoVoiceRealGates(unittest.TestCase):
 266 |      """Audit 2240 C2 (glm N8): a no-voice package through the REAL VO-fidelity and context-integrity decisions (canned
 267 |      model replies, no stubbed gate): every required row, the medley rows included, exactly PASS, and the pin is
 268 | @@ -692,7 +770,8 @@ class TestNoVoiceRealGates(unittest.TestCase):
 269 |          coh = dict(med, vo_point=None, note="no VO line: the clips-alone verdict is the coherence verdict (ruling 3)")
 270 |          pk["gates"] = PK.inventory(fid, dup, rt_ok, r4_res, cx, a_lab, exc, tru, True, coh, medley=(True, med),
 271 |                                     shape=PK.ly_shape(pk), style=HS.lint_lines(pk["lines"]),
 272 | -                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"})
 273 | +                                   hook={"pass": True, "measured": True, "lead_ms": 200, "cut_in": 1.0, "why": "ok"},
 274 | +                                   stand=PK.stand_alone_check(pk["segments"]))
 275 |          self.assertEqual(package_pin.gate_problems(pk["gates"], package_pin.required_gates(pk)), [])
 276 |          mp = package_pin.to_pin(spk(pk), "test")["moments_package"]
 277 |          self.assertEqual((mp["edl_vo"], mp["no_voice"]["added_clip"]), ({"intro": None, "bridges": []}, None))
 278 | 
```

---

You are auditing a diff on branch pp-selectid (Protocol Pulse: moments-first packaging, the L-y MEDLEY of real clips:
a hook and 2-4 clips from other channels, played back to back, then one spoken takeaway). This branch BUILDS sealed
"pins"; another session (the integrator) renders them with the main pipeline, whose validate stage runs extra checks.

Only state what you can verify from the diff provided. If uncertain, say so; do not guess.

Why this change: the integrator HELD pin d2657bbe at its validate stage (03:00 ET Nov 13), before any render, on the
main pipeline's STAND_ALONE check (main pipeline/run_fresh.py stage_validate -> stand_alone.check_edl):
  STAND_ALONE hook:    [PASS] opener: opens on 'bitcoin' | topic: names the subject (bitcoin)
  STAND_ALONE clip_01: [FAIL] opener: clip opens on 'but'; the clip scorer does not affirm it stands alone (3.0, fault other)
  STAND_ALONE clip_02: [FAIL] opener: clip opens on 'but'; the clip scorer does not affirm it stands alone (3.0, fault other)
This branch's pin-stage gates did not run that check. pipeline/stand_alone.py on this branch is byte-identical to the
main pipeline's at the render's commit. In the render, check_edl gets rate = a CLIP SCORER that is a local model on
the GPU (Ollama, GPU0); this branch's session may not use any GPU. check_edl with rate=None fails closed: a clip that
opens on a conjunction or a reply fragment FAILS when no scorer verdict is available. The render's subject for a
pinned moments package labelled 'bitcoin' is stand_alone.subject_terms("", "bitcoin") = {bitcoin, btc}.

Standing laws:
- nothing measured is never a pass (L-m); fail closed (L-j);
- never change what a check accepts in order to make something pass (adding a stricter pre-check is allowed);
- the pin stage must never seal a line-up that the render's own checks would hold.

The change:
1. pipeline/package.py:
   - stand_alone_check(segs): stand_alone.check_edl on the line-up (hook, then clip_01.. in play order), rate=None,
     subject {bitcoin, btc}. With no scorer, a conjunction or reply-fragment clip opener fails closed: stricter than
     the render, which may let its scorer affirm such a clip.
   - no_role_on_screen(m): a moment whose opener fails BOTH as a clip (no scorer) and as a hook (stand_alone.opener)
     can take no place in any line-up. build() leaves such moments out right after usable(), before step A or any
     other vendor call, and records them in out["no_role"] with the reason.
   - lineup_for(..., need_stand_alone=False): when True, a candidate line-up that fails stand_alone_check is skipped
     (the proposer's hook gives way to the next hook, as with need_onset). build() passes need_stand_alone=True at
     both call sites.
   - inventory(..., stand=None): a sealed "stand_alone" gate row (PASS only when check_edl's ok is True), with the
     per-segment rows as evidence. Both inventory call sites pass stand_alone_check of the package's segments.
2. pipeline/package_pin.py: MEDLEY_GATES gains "stand_alone", so write_pin refuses a medley without a PASS row. The
   integrator's recompute (check_pin_only) checks REQUIRED_GATES only, so older pins still recompute.
3. tests/package/test_medley.py:
   - the held pin's three texts give the render's PASS / FAIL / FAIL;
   - the no-role rule: conjunction and reply-fragment openers have no role; pronoun openers can still be clips;
   - lineup_for never picks a "But" clip with need_stand_alone; a line-up with no clip naming Bitcoin is refused;
   - a pronoun hook gives way;
   - build() leaves a "But" moment out before the angle step and seals a PASS row;
   - a FAIL row refuses the pin;
   - the two existing tests are updated for the new required row.

Check in particular:
- that stand_alone_check reproduces the render's check_edl call exactly (segment order, labels clip_01..,
  rate=None, subject), and that nothing here can PASS a line-up the render would hold;
- that no_role_on_screen drops ONLY moments that can be neither a clip nor a hook under check_edl with no scorer
  (a pronoun opener must stay: it fails as a hook but passes as a clip);
- the gate row: unmeasured or failing never PASS; a missing row refuses the pin;
- anything that changes what an EXISTING check accepts.

Answer with P0/P1/P2 findings (file:line, scenario), then "SHIP: yes / no / yes with conditions".


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
