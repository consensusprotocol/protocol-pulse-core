# qwen3.8-27b (qwen/qwen3.8-27b) 146 s finish=stop usage in 18723 / out 10850 usd_reported=0.008607 usd~0.219 (upper-bound price)



# CYCLE 2 — FINAL REVIEW: pp-selectid / RULING 118 (4) STORY-FIRST LINE-UPS

## 1. WHAT DID THEY CATCH THAT I MISSED?

**Gemma:** Nothing I missed. Her Cycle 1 was thorough and correct. Her initial P1 (about `check_angles(..., 1, ...)`) was a misread of the `k` parameter (it's "how many angles this object may hold," not "minimum moments"), and the C1 consensus correctly identified this.

**Qwen:** Three P3s that I also see but would have ranked the same:
- Empty-string `moment_id` passes `read_stories` validation (line 72: `isinstance(m.get("moment_id"), str)` is true for `""`). Harmless today because `""` can never be a key in `cleared`, so it's filtered by `if x in cleared` in `story_angles`. One `and m["moment_id"]` away from airtight.
- `out["stories"]["angles"]` holds per-story diagnostic rows, not angle objects. Readability nit.
- The `story` lambda in `load_candidate` (line 151–152) evaluates `record.get("angles") or []` twice per call. Micro-fragility; the list is small and never mutated between reads.

I agree with all three. None rise above P3.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Reason |
|---|---|---|
| Gemma: no defects, all 5 checks pass | **Agree** | I independently traced every path; the story restriction is airtight. |
| Qwen P3: empty-string moment_id | **Agree** | Valid but zero-risk in the current pipeline. |
| Qwen P3: `stories.angles` misnomer | **Agree** | Purely a naming/readability concern. |
| Qwen P3: lambda re-reads angles list | **Agree** | Negligible; the pattern is slightly fragile but not wrong. |
| C1 consensus: Gemma's P1 was a misread | **Agree** | `k=1` in `check_angles` means "one angle in this object"; the 3–8 moments rule is internal and unconditional. |
| C1 consensus: 18/18 mutations killed | **Agree** | The test suite is comprehensive; I see no mutation that would survive. |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the full diff with the other models' analyses in hand, I traced every path one more time and found **no new P0–P2 issues**. Specifically I verified:

- **Hook-in-doomed safety:** The hook is always first in the angle's moments and `swap_lineup` uses `keep_hook=True`, so the hook can never enter `dropped`. The function-level `doomed` set (globally unavailable moments) is already excluded from `cleared`, so a story angle's hook (selected from `cleared ∩ passing`) can never be globally doomed.
- **`hrank` coverage:** Every story angle's hook is in `passing` (by construction in `story_angles`), so it is always a key in `hrank`. No `KeyError` path.
- **Writer-gateway invariant:** When the writer produces zero angles, `if not angles: return out` fires *before* the combined list is built. Story angles are never tried in isolation. The test `test_no_file_no_story_of_three_channels_or_no_writer_builds_as_before` pins this.
- **Candidate-build isolation:** `by_story` is `{}` when `candidate is not None` (the stories block is skipped), so `story_pool` returns `cleared` for the candidate's (writer) angle. No story leakage.
- **`pool_fill` with `hook_only=True`:** The fill draws from `sel` (the story's pool), and the hook is the angle's own hook (already in the story). No outside moment enters.
- **Atomic file read:** The stories file is replaced via temp+rename (per the writer's docstring), so `json.load` sees either the old or the new file, never a partial write.
- **`max_angles` as `k` in `story_angles`:** Capped at the same `max_angles` the writer uses. Total angles ≤ 2×`max_angles`, which is bounded by the orchestrator's per-angle budget.

One **P3** I add: the `STORIES` constant (line 38) hardcodes a production path. It's only used in `proof_ledger.py` (the test harness), and `build()` takes `stories_path` as a parameter, so the logic is not coupled to the path. But if the production path ever changes, the constant must be updated. This is a maintenance note, not a defect.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `read_stories` | Clean | Clean | All-or-nothing validation confirmed; empty-string moment_id is P3 (Qwen). |
| `story_angles` | Clean | Clean | Hook selection, channel-first ordering, `check_angles` contract, `k` cap all verified. |
| `story_pool` | Clean | Clean | Correctly returns story subset or full pool; filters to `cleared`. |
| `story_writers` / L-x | Clean | Clean | Vendor/family extraction from router back-ends; merged into `writers_v`/`writers_f`; test pins it. |
| `build()` integration | Clean | Clean | Story angles prepended; `sel` threaded through join/fill/swap; writer-gateway preserved; candidate path isolated. |
| `candidates.seed` / `load_candidate` | Clean | Clean | Story angles excluded from seeding and loading; both auto-pick and explicit-index paths guarded. |
| `angle_source` | Clean | Clean | Correct attribution in `pk["models"]["angle"]`. |
| Tests | Clean | Clean | 12 tests cover all 5 requested checks plus edge cases; 18/18 mutations killed. |

No score changes. Everything held up under the second pass.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 (nits, not blocking):**
1. `read_stories` line 72: add `and m["moment_id"]` to reject empty-string moment_ids. (Qwen)
2. `out["stories"]["angles"]` naming: consider `out["stories"]["per_story"]` or `out["stories"]["diagnostics"]`. (Qwen)
3. `load_candidate` lines 151–152: hoist `angles = record.get("angles") or []` to a local before the lambda. (Qwen)
4. `STORIES` constant (line 38): add a comment noting it must track the production path if it changes. (New, mine)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `sel = story_pool(angle, cleared, by_story)` line (diff line 250) is the entire safety mechanism in one expression: every downstream call (`join_moments`, `pool_fill`, both `swap_lineup` calls) receives `sel` instead of `cleared`, and `lineup_for`/`search_lineups` are structurally confined to the angle's own moments plus the join table — so the story boundary holds by construction with no per-call-site guard. If that one line were accidentally reverted to `cleared`, every story angle would silently pull from the full pool. The test `test_a_story_too_short_for_a_line_up_is_never_filled_from_outside_it` is the mutation that would catch it.

## 7. PRODUCTION READY?

**Yes.** No P0, P1, or P2 findings. The four P3s are cosmetic or defensive-hardening nits that do not affect correctness in the current pipeline. All five requested checks pass. The writer-gateway invariant is preserved. L-x is correctly extended. The candidate path is fully isolated. The test suite (12 new tests, 18/18 mutations killed) pins every behavioral contract.

P1_OR_WORSE: 0