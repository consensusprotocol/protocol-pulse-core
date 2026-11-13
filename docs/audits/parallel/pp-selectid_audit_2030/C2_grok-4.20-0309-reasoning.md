# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 31 s finish=stop usage in 44320 / out 1642 usd~0.263 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-2030 (L-y Medley)**

1. **WHAT DID THEY CATCH THAT YOU MISSED?**  
   - GLM's P0-3 / P1 on `takeaway_budget` + bridge-seconds drift (the first-write budget used `LY_BRIDGE_WORDS=12` while `lineup_for` used `medley_content_range(n_bridges=0)`; a 20-word bridge could push a marginal lineup over the runtime gate). Cycle 1 I only noted the fallback-to-(8,30) path.  
   - Grok's P2-2 on `bridge_slots` / hook-join intro handling and P2-3 on inventory `measured=False` rows (the exact `NOT RUN` vs `FAIL` interaction with `required_gates`). I had flagged inventory but not the precise `ly_shape` row emission when `medley["measured"]=False`.  
   - Qwen's concrete epsilon/rounding example in `takeaway_budget` (29.25 → 29 vs 30). Consensus later refuted it with the test sweep, but the numeric edge was invisible to me in Cycle 1.  
   - The `_redo` prompt now carrying the *exact* computed range (or "no takeaway length lands it") was added after Cycle 1; I had not anticipated that specific diagnostic.

2. **WHERE DO YOU AGREE OR DISAGREE?**  
   - **K1 (takeaway length vs runtime gate)**: Fully agree with consensus. The fixed `if join and not other: other = ["word"]*LY_BRIDGE_WORDS`, the redo that recomputes `takeaway_budget(..., written)` with the *actual* bridge text, and the test sweep (`test_the_takeaway_budget_lands_the_estimate...`) close the loop. Qwen's 29-vs-30 case is refuted by Python `math.ceil(29.25-1e-9)==30` and the explicit RUNTIME redo message.  
   - **K2 (test gaps)**: Agree. `TestBuildLoop` + `Rig` now exhaustively covers: no-write on clips-alone fail, weak-clip drop, null-bridge re-line, given-bridge path, supply-exception recording. The 30-word takeaway R4 fail and hook-join bridge pin are explicitly tested.  
   - **K3 (inventory medley/ly_shape rows)**: Agree. When `medley["measured"]=False` the medley row is `NOT RUN`, ly_shape is `FAIL`; both block `gate_problems`. `inventory(..., medley=(ok,verdict), shape=ly_shape(pk))` is now called unconditionally on the final package.  
   - **K4 (bridge after hook)**: Agree. `assemble_medley(k==0)` puts text in `vo["intro"]`, `bridge_slots` returns `["takeaway"]`, `line_problems` treats intro separately, and the pinned `edl_vo` correctly carries `intro: "bridge text"`. Grok's `[0,2]` scenario is unreachable.  
   - GLM P0-1 (old non-medley shape reaching `ly_shape`): Agree it is now latent only; `build` always emits shape="medley" and `proof_ly.py` only exercises the new path.  
   - Grok P2-1 (null-bridge re-line): Agree fixed — explicit `if fields["bridge"] is None: dropped.add(...); relined=True`.

3. **NEW FINDINGS FROM THIS REVIEW**  
   - **P2: pipeline/package.py:773** (`extra = _redo(...)` after cheap fail). The recomputed `b = takeaway_budget(..., written)` can return `None` (clips too long once real bridge length is known). The redo prompt says "shorten the bridge" but the writer has already returned a bridge of that length; the only remaining action is to drop the line-up. No infinite retry because `w_used` is bounded, but the diagnostic is misleading. Concrete: 51.4 s clips + 20-word bridge → `takeaway_budget` returns None on redo → writer is told "change the takeaway's length (no takeaway length lands it: shorten the bridge)" even though the bridge length is already fixed.  
   - **P2: pipeline/package.py:362** (`lineup_for(..., crange=None)` defaults to `medley_content_range()` i.e. n_bridges=0). When a flagged join exists the first `write_takeaway` forces a 12-word bridge placeholder, but the lineup may sit at the extreme hi edge (51.5 s). A real bridge >12 words can then fail runtime on *first* write (wasted model call). The test sweep covers the arithmetic but not the concrete first-write failure path under real writer output. Minor because `_redo` will correct the budget on retry.  
   - No new P0/P1. Ledger changes (`_reported`, `usd_reported` vs `usd_unreported_estimate`) are clean; guard still uses estimate. `ly_shape` must-fail matrix in `test_medley.py` is exhaustive.

4. **REVISED SCORES**

   | Subsystem              | Cycle 1 | Cycle 2 | Why changed |
   |------------------------|---------|---------|-------------|
   | Budget / runtime gate  | P1      | P2      | Redo logic now recomputes with actual bridge; test sweep refutes rounding bug; residual first-write waste is edge-case only |
   | Build loop control     | P2      | P2      | `TestBuildLoop` + `Rig` now complete; null-bridge drop, weak-clip drop, measured=False paths all exercised |
   | ly_shape / shape gates | P1      | P2      | All must-fail cases proven; old-shape path truly latent |
   | Inventory + pinning    | P2      | P2      | `required_gates(pk)` conditional on shape, `bridge_slots`, `NOT RUN` handling all verified by tests |
   | Ledger / spend guard   | P2      | P2      | `_reported` helper and unreported_estimate logic cannot bypass limit_usd (still estimate-based) |

5. **FINAL PRIORITY LIST**  
   **P0 CRITICAL** — none.  
   **P1 HIGH** — none.  
   **P2 MEDIUM**  
   - pipeline/package.py:773 — misleading redo prompt when `takeaway_budget` returns None on a real bridge (file the "shorten the bridge" message only when a bridge length can still be reduced).  
   - pipeline/package.py:362 + 473 — first-write runtime risk on marginal lineups that become illegal once a >12-word bridge is materialized; either tighten `lineup_for` to `medley_content_range(n_bridges=1)` when a flagged join exists, or accept the retry cost.  
   All Cycle 1 P0/P1 items are resolved.

6. **THE SINGLE HIGHEST-LEVERAGE CHANGE**  
   Forcing the blind clips-alone `medley()` verdict *before any write* (and dropping line-ups that need >1 bridge) eliminates the largest class of wasted model calls while making selection carry the coherence burden exactly as L-y 2/3 require.

7. **PRODUCTION READY?**  
   **Yes with conditions**: (a) run `proof_ly.py --runs fresh_...` on the newest universe to confirm takeaway first-write pass rate ≥70 % and zero runtime-gate failures on first write; (b) the two P2 redo-diagnostic cases above must be tightened before the next orchestrator rollout (one-line change each). After those, the medley shape, gates, ledger, and test coverage satisfy every clause of L-y, L-m, L-j, L-x.

**SHIP: yes with conditions**