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
  - Mutation M23 (no_voice builds another order than the plan) is killed by 3 tests.
- When no no-voice line-up exists, the reason is recorded on the line-up: rec["no_voice_plan"] = {why_not,
  registered_skipped}. Mutation M22 is killed.
- glm P2 (the ruling-66 registry on ruling 91's path):
  test_a_value_loss_leaves_a_registered_line_up_to_the_registry.
  - The only clip that lands the seconds forms a registered line-up, so it is left to the registry.
  - The recorded plan names it, h+x+y+z is never judged, and the one rewrite ships.
- qwen P2 (comments): added at the check ("fid and cx are bound: every exit above returns None"; ruling 65's own
  trigger, context integrity on its own).

## Verified, no change

- glm P2 (the vo_kind note string): unchanged. rewrite_alone passes why = "the fixed caption (ruling 65 b)" and the
  helper writes f"{pk.get('vo_kind')}; {why}", exactly as build_pk did.
- grok P2 (a measured=False context stub on the ruling-3 path): the fixed caption's context failure is tested
  (test_c_the_fixed_caption_still_passes_its_own_gates_or_the_line_up_ends). An unmeasured run is not ok, and the same
  `not cx["ok"]` check ends it. One code path for both rulings.
- qwen conditions: a_use is the same dict (C1); no caller of no_voice_fits (C1 grep).

Mutation check: 18 of 18 killed. 19 suites, 546 tests.
