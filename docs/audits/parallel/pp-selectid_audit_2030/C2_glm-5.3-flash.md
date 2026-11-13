# glm-5.3-flash (z-ai/glm-5.3-flash) 35 s finish=stop usage in 45207 / out 1816 usd~0.163 (upper-bound price)

# CYCLE 2 — FINAL REVIEW (pp-selectid, L-y medley)

## 1. What they caught that I missed

- **glm's bridge-seconds budget bug (P0-3)**: `write_takeaway` budgeted the takeaway without the bridge's seconds; a 20-word bridge shifts the needed clip seconds by ~3.2 s and can push a dur near the `hi` edge out of 60-70, and the redo prompt repeated the same budget — a retry that cannot succeed. I traced the no-bridge case and stopped. The fix (budget with LY_BRIDGE_WORDS when a bridge is asked; every redo budgets with the actually-written bridge; the RUNTIME redo carries the exact word range, lines 473-475, 773-777) is correct and tested (`test_a_takeaway_over_30_words...` covers the pin side; the redo wording is exercised only indirectly).
- **grok's null-bridge re-line (P2)**: writer declines the bridge → clip after the flagged join dropped and re-lined, even though L-y 2 allows "followable without narration" to pass. I had this as intended behavior; grok's reading is defensible but the code's choice (re-line, LY_LINEUPS=2) is a legitimate interpretation, and the test `test_a_declined_bridge_drops_the_clip_after_the_flagged_join` pins it. Agree to disagree — it's a design choice, not a bug.
- **grok's bridge_slots/line_problems for k=0**: I had traced this as consistent; the consensus's REFUTED-by-test (the hook-join bridge pins as `intro`, `test_a_takeaway_over_30_words...` second half) matches my trace. Grok's concrete scenario (`bridges_after_clip: [0, 2]`) is indeed a shape the code never builds.

## 2. Agree / disagree

- **glm P0-1→P1 (old-shape package reaching `ly_shape` via `inventory` in `build`)**: agree, latent-only; `build` only produces medleys, and `cheap_checks` gates `ly_shape` on `shape == "medley"`. Correctly downgraded.
- **glm's own self-refutation of its P0-2**: agree — the arithmetic checks out; `ceil(29.25 - 1e-9)` is 30, and the sweep test covers 30.0-55.9 s in 0.1 s steps. Qwen's P0-2 is refuted on the numbers.
- **qwen P0-3 (lineup_for repeat_ok)**: agree it's sound; the `n+1`-distinct-videos requirement correctly forces two clips of one channel to come from different videos, and `test_a_channel_twice_only...` proves both directions.
- **Consensus K3 (inventory rows)**: agree with REFUTED. `row()` gives ly_shape status/by/replayed/n; NOT RUN + FAIL both refuse the pin; `build` never assembles after an unmeasured verdict. Grok's P2-3 was wrong about the consequence.
- **Consensus K1 (qwen's rounding)**: agree, refuted.

## 3. New findings (this cycle)

- **P2 — `providers.py` ledger, `usd_reported` at the run level (line ~1001)**: `d["usd_reported"]` accumulates globally, but `proof_ly.ledger()` computes `best = usd_reported + usd_unreported_estimate` from the *top-level* keys. If a call reports cost, its price-table estimate is *also* still added to `usd_estimate` (line 995-996 runs unconditionally) — correct, the guard reads the estimate. But `usd_unreported_estimate` only accumulates when `_num(usage.get("usd_reported"))` is false; a call whose reported figure exists but whose *estimate* was 0 (a role priced at 0) contributes 0 to unreported — fine. No corruption found; the guard reads the upper-bound estimate throughout. Verified: no way to pass the guard. (Stating this because nobody closed the loop in Cycle 1.)
- **P2 — `proof_ly.py` `run_one` (line ~1123)**: `spend=lambda: ledger()[0]` returns the *estimate*; the guard is the estimate — consistent with the docstring. But `res["usd_best_known"]` mixes reported + unreported-estimate, which is a *lower* figure than the estimate; the table labels it "best known" — honest, but a reader could mistake it for the guard figure. Documentation nit only.
- **P2 — `write_takeaway` (line 475)**: when `takeaway_budget` returns None the fallback `(8, 30)` can still be emitted in the prompt; the RUNTIME redo now carries "no takeaway length lands it: shorten the bridge" (line 774-776), which closes glm's infinite-retry concern *only when the failure is RUNTIME*. If the failure is R4 (share) with the same root cause, the redo says nothing about the bridge. Narrow, bounded by WRITES; P2.
- **P2 — `ly_shape` (line 553)**: the bridge's `cites` are never checked to reference the flagged join's clips (glm's P1-1, self-graded P2). Agree, P2.

Nothing rises to P0 in the fixed diff. The Cycle-1 P0s were either fixed (bridge-seconds budgeting) or correctly refuted (rounding, inventory rows, hook-join pin).

## 4. Revised scores

| Subsystem | C1 | C2 | Why |
|---|---|---|---|
| package.build loop | 8 | 9 | bridge-seconds budgeting fixed; redo carries the word range; loop control now tested (TestBuildLoop) |
| ly_shape | 8 | 8.5 | must-fail table comprehensive; cites-not-checked remains (P2) |
| medley() | 9 | 9 | contract strict; prompt verified narration-free by test |
| write_takeaway / budgets | 7 | 9 | the P0 (bridge seconds) fixed and swept |
| package_pin | 8 | 9 | bridge_slots/required_gates correct; hook-join pin proven by test |
| providers ledger | 8 | 8.5 | reported-vs-estimate separation verified; no guard bypass |
| proof_ly | 7 | 7.5 | sound; "best known" labeling could mislead |
| tests | 7 | 9 | 30 tests; the C1 gaps (30-word takeaway, loop control) closed |

## 5. Final priority list

- **P0**: none.
- **P1**: none.
- **P2**:
  1. `package.py:553` — bridge `cites` not tied to the flagged join's clips (glm P1-1).
  2. `package.py:773-777` — the redo's word-range hint fires only for RUNTIME; an R4-share failure with the same root cause gets no bridge-shortening hint.
  3. `package.py:475` — the `(8, 30)` fallback when `takeaway_budget` is None is unreachable for the no-bridge case but reachable with a long bridge; harmless now that the redo explains it, but the fallback could return None-shaped honesty instead.
  4. `proof_ly.py:1106` / table — "best known" mixes reported + unreported-estimate; label it.

## 6. Single highest-leverage change

Tie the bridge's `cites` (and its redo hint) to the flagged join — it is the only remaining place where a package can pass L-y's gates while the bridge's justification is unverified against the clips it bridges.

## 7. Production ready?

**Yes with conditions**: (a) add the bridge-cites check or record it as a known gap in the inventory's `ly_shape.why`-style note; (b) extend the RUNTIME/R4 redo hint to cover the R4-share case; (c) re-run proof_ly's table after the fixes. Everything else — the loop control, the budget arithmetic, the pin gates, the ledger — is proven by test and trace.

SHIP: yes with conditions