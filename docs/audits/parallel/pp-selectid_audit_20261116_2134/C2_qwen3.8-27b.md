# qwen3.8-27b (qwen/qwen3.8-27b) 180 s finish=stop usage in 8528 / out 7040 usd_reported=0.006540 usd~0.131 (upper-bound price)



# CYCLE 2 — FINAL REVIEW: pp-selectid-20261116_2134 (RULING 127 (2))

## 1. WHAT DID THEY CATCH THAT I MISSED?

In Cycle 1 I (like the other models) confirmed the four guards are correct and the tests are sound. Reviewing their outputs:

- **Gemma** correctly noted that the `continue` in prescreen ensures local verdicts "never enter `a_by`," which is the critical invariant. I reached the same conclusion but Gemma's phrasing made the dependency chain (a_by → cache/store writes → seal) more explicit.
- **Qwen** produced the most thorough path-by-path table and correctly identified that the `second_screen` guard is the *primary* guard for the second screen (not merely defence-in-depth), because `second_screen` makes its own independent backend calls. I had framed it as "belt-and-suspenders" in Cycle 1, which understated its role.
- **Qwen's P3** (the `local_held` f-string is 4 lines and dense) is fair. I didn't flag it in Cycle 1. It's a readability nit, not a defect.

Nothing material was missed by the group. All three independently reached P1_OR_WORSE: 0, and the mutation-kill (5/5) and 850-test suite confirm the guards are load-bearing.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | My position |
|---|---|
| No path can seal or cache on a local verdict | **Agree.** I re-traced all five write/read paths (post-call, pick, db-read, second_screen, last_resort_of) and confirmed each is guarded. The `continue` is before any state mutation; `pick` and `db`-read filters are independent of `off`; `second_screen`'s `elif` is the primary gate for that screen. |
| A local verdict is HELD, never a refusal | **Agree.** `local_held` always returns a string starting with `HELD`. The refuse reasons appear *inside* the HELD text as informational context. `is_held()` checks `startswith(HELD)` on every element. Tests pin both the prefix and the "local, provisional" substring. |
| Nothing changed for other legs | **Agree.** Every new line is gated on `startswith(LAST_RESORT)`. For non-local backends, the added conditions evaluate to `True` (no-op) and the new `elif`/`if` blocks are never reached. The failover chain order, `off` lambda, `time_sensitive` fallback, and `STEP_A_SAME_VENDOR` check are untouched. |
| Tests are correct and sufficient | **Agree.** Each of the four guards has at least one test that would fail if the guard were removed (confirmed by 5/5 mutation kill). The build-level test correctly asserts `out["package"] is None` and `last_resort_87 == {}`. |
| Qwen's P3 (f-string density) | **Agree.** It's a nit. The string is correct, tests pin it, and splitting it would add a line without improving correctness. |

No disagreements.

## 3. NEW FINDINGS FROM THIS REVIEW

After re-reading the diff with the benefit of the other models' analyses, I looked for edge cases they didn't explicitly address:

**[P3] `str(rec.get("backend"))` when backend is `None`.** In the store-read guard (line 38), if a legacy store record has no `backend` key, `str(None)` → `"None"`, which doesn't start with `"local_judge:"`. The record then fails the `off(None)` check (because `router.backends.get(None)` is `None`, making `b is not None` false), so it's rejected by the existing `off` guard. No new risk, but the interaction is worth noting for future maintainers.

**[P3] `str(a2.get("backend") or "")` in second_screen (line 57).** The `or ""` handles `None` backend. A verdict with no backend falls through to the `b2 is None` branch (existing same-vendor failure). This is pre-existing behaviour, not a regression.

**[P3] The `local_held` f-string (lines 14–16) embeds `a.get('backend')` directly.** If for some reason the backend name contained characters that would be confusing in a log line (e.g., a newline), the HELD reason would be malformed. In practice, backend names are identifiers like `"local_judge:gemma3:27b"`, so this is theoretical. The tests pin the format.

No P0, P1, or P2 findings.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `local_held` helper | Pass | Pass | No change. Correct, tested, minimal. |
| Prescreen post-call guard | Pass | Pass | No change. `continue` before any mutation. |
| Prescreen cache/store read guards | Pass | Pass | No change. Independent of `off`, correct prefix check. |
| Second-screen guard | Pass | Pass | No change. Primary gate for that screen, correct ordering. |
| `last_resort_of` / `last_resort_note` | Pass | Pass | Now inert (local verdicts never in `a_by`). Left as-is per smallest-diff. |
| Tests | Pass | Pass | No change. 5/5 mutation kill, 850 tests, all four guards covered. |
| Other-leg regression risk | Pass | Pass | No change. All new code gated on `LAST_RESORT` prefix. |

No score changes.

## 5. FINAL PRIORITY LIST

| Priority | Finding | Location |
|---|---|---|
| — | None. No P0, P1, or P2 findings. | — |
| P3 | `local_held` f-string is 4 lines and dense; a future reader must parse the nested conditional. Consider a short comment or a two-line split. | `pipeline/package.py:14–16` |
| P3 | `str(rec.get("backend"))` on a `None` backend produces `"None"`; harmless (rejected by `off`) but slightly opaque. | `pipeline/package.py:38` |

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

The `continue` at line 49 (immediately after the `LAST_RESORT` check in prescreen) is the single most important line in this diff: it is the one point that simultaneously prevents cache writes, store writes, `a_by` insertion, and vendor/family tracking for local judge verdicts, and every other guard (cache read, store read, second screen) is a secondary confirmation of the invariant that this `continue` establishes.

## 7. PRODUCTION READY?

**Yes.**

Conditions (all already satisfied by the diff and test suite):
1. The 5/5 mutation kill is reproduced on the target environment (dev50, confirmed in Cycle 1 consensus).
2. The 850-test suite passes by exit code (confirmed in Cycle 1 consensus).
3. This diff is applied on top of RULING 126 (1) (audit 20261116_2005, cleared, not yet landed) — the two must land together or 126 (1) first.

No further code changes are required.

P1_OR_WORSE: 0