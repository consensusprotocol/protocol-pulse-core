# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 35 s finish=stop usage in 17769 / out 1584 usd~0.128 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1441 (post-C2 diff with “no-variant on unrelievable hold”)**

**1. WHAT DID THEY CATCH THAT YOU MISSED?**
- **qwen’s P1 “doomed variant” (first-sentence hold + ceiling)**: I noted the held-word placement logic but did not trace the path where a current hold cannot be relieved *and* the parent is also over ceil_s; the original for_pool would still emit a ceiling variant that kept the held word. The added `continue` (tail_variant.py:152-155) plus the explicit test (test_ruling_104.py:418-421) closes it. Missed in my Cycle 1.
- **grok’s floating-point ceiling note**: I verified the ks list but did not flag that `for_pool` never re-measures the *actual* `v["duration_s"]` produced by `variant()` / `M.record`. A token end time that rounds such that `end - t0 > ceil_s` after Span construction would still be emitted (and scored). Concrete sequence: parent duration_s=22.94, ceil_s set to sentence[2] end exactly, token["end"] float epsilon makes variant 35.0000000004 s. Grok surfaced it; I had not.
- GLM’s own Cycle 1 truncated argument on repeated held token is now fully covered by the first-occurrence canon_spans + `src.sentences[k][1] < i` filter + test_an_insert_before_the_hold_cannot_be_placed_so_no_variant.

**2. WHERE DO YOU AGREE OR DISAGREE?**
- **grok <high> (medley ordering) → AGREE, resolved.** Replacement via `replaced` set (proof_ledger.with_variants:204, for_pool:167) removes the parent from the pool entirely when a current hold exists. No ordering hack remains; parent and variant never compete in medley, spotlight finalists, or line-ups. TestThePool.test_the_ledger_build_replaces_a_held_parent_and_keeps_one_over_the_ceiling exercises both cases.
- **grok <medium> (inherited ALONE / cached verdicts) → AGREE with refutation.** `variant()` supplies fresh `M.judge(sp, ctx)` (tail_variant.py:74) and a new `moment_id` + new `text` (therefore new text_sha256). Copied `m["scores"]` only feeds `rank_score` (line 76). `spotlight.alone_score` and lock_precheck both key on the moment’s own id/window/text; parent verdict cannot match. Test line 306 confirms eligibility is judged afresh.
- **qwen <medium> (boundary convention / ks list) → AGREE.** `E.Span(src, 0, 2)` + `v["sentences"] == [0, 2]` + text `SENTENCES[:3]` (test:295-296) pins that the end index is inclusive of sentence 2. The filter `src.sentences[k][1] < i` (line 147) guarantees the held word at sentence 3 is excluded. No off-by-one.
- **GLM (b) repeated token / first-occurrence → AGREE, closed.** `held_word` returns index of *first* match via `canon_spans` on parent slice (lines 108-118). Variant ends before that sentence; later repeats are automatically left out. The “insert before the hold” test returns None, preventing any variant that would keep a later held token.
- **Consensus on snap guard, derived_from recording, current-decoder-only holds() → AGREE.** spotlight.py:9-11, package_for:20-21, holds():91 (LP.answer with current DECODER/RULES), TestTheHolds:349-373 all verify. No stale holds, no snap that re-inserts left_out words, derived_from present on moment, mined record, and spotlight pin.

**3. NEW FINDINGS FROM THIS REVIEW**
<medium> pipeline/tail_variant.py:158 (`ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]`).  
Concrete sequence: parent start=0.0, sentence[2] token end=35.0 (exactly), floating-point addition in eligibility.Span or M.record yields duration_s=35.0000000004. `for_pool` accepts it (no post-variant duration re-check), writes it to inputs["ruling_104"], runs it through clip scorer / ALONE / lock pre-check, then spotlight.pool drops it for exceeding SPOT_S[1]. Wastes compute; test at 403 only guards with +0.01 and does not assert final `v["duration_s"] <= ceil_s`. (Uncertain whether real token times can produce > ceil_s given how Span normalizes; therefore medium, not high.)

No criticals or highs. All vectors (a)-(i) are covered by the replacement logic, current-decoder holds(), the unrelievable-hold `continue`, snap guard, fresh judge(), and the 14-test suite (including mutation that restores the old “doomed variant” behaviour).

**4. REVISED SCORES**
| Subsystem                    | Cycle 1 | Cycle 2 | Why changed |
|------------------------------|---------|---------|-------------|
| Ordering / replacement       | high    | none    | Replacement (for_pool:167, with_variants:204) + current-only holds() eliminates competition entirely. |
| ALONE / verdict freshness    | medium  | none    | New span id + text_sha256 + fresh M.judge() + test:306 close the inheritance path. |
| Held-word placement / boundaries | medium | medium  | First-sentence + unrelievable-hold case now explicitly tested and blocked; new floating-point ceiling edge surfaced. |
| Snap / derived_from / gates  | low     | none    | Explicit guards and test coverage verified. |

**5. FINAL PRIORITY LIST**
P2 MEDIUM — pipeline/tail_variant.py:158 (ceiling ks comprehension): after building `ks`, add `if not ks: …` already present, but after `v = variant(...)` insert `if float(v["duration_s"]) > ceil_s: …` (or let spotlight.pool silently drop it and document). Also document the +0.01 test guard.  
No P0 CRITICAL or P1 HIGH items. All ruling-104 requirements, SENTENCE LAW, SELECTION LOCK, current-decoder isolation, and attack vectors (a)-(i) are satisfied.

**6. THE SINGLE HIGHEST-LEVERAGE CHANGE**
Replacing the held parent entirely (for_pool:167, proof_ledger.with_variants:204, inputs["ruling_104"]["replaced"]) so parent and variant never coexist in any pool, while only emitting a variant after a *current-decoder* hold that can be relieved, enforces the orchestrator’s “FIRST the re-listen; if it holds, the variant” rule structurally.

**7. PRODUCTION READY?**
Yes with conditions: (1) the floating-point ceiling edge must be either hardened or explicitly documented as acceptable (spotlight.pool will drop any overshoot); (2) lock_precheck.answer must continue to select only the current decoder/rules file (verified in test but not enforced inside tail_variant); (3) the build’s RULING 104 line must be read on STATE line 1 of the first production run.

SHIP: yes with conditions