# pp-selectid audit 1112 (RULINGS 58 + 59: every candidate at step A, cached; HOOK FIRST): cycle 1 consensus

**Run:**
- grok: "SHIP: yes", no P0 or P1.
- qwen: "SHIP: No", on one P0 (refuted below).
- glm: "None found" for P0. Its 39 numbered "P1" items mostly close themselves ("Good", "Correct", "consistent"). It
  stopped at its 24,000-token limit.

No P0 or P1 holds. Nothing changes in the code; cycle 2 reviews the same diff.

## REFUTED (with evidence)

| # | claim | the code |
|---|---|---|
| R1 | qwen P0: "build does not filter cleared moments based on second_screen results" | The filter is there, unchanged, just outside the diff's context. pipeline/package.py:1708 (the scratch copy; HEAD's line ~1514) reads `cleared = {mid: m for mid, m in cleared.items() if mid in a_two}`, right after the second screen's record. qwen's own text says the diff does not show it. Ruling 59's re-check of the passing hooks reads this filtered set. |
| R2 | glm P1-5: the router may not be thread-safe under parallel step-A batches | The router's spend ledger is reserved and settled under an fcntl file lock (pipeline/providers.py:536-541, `_lock`, used at 581 / 615 / 624 / 640). Replies are recorded at content-addressed paths (`_path`, 531-533). The build already called the router concurrently before this diff: L-v 2's 8 workers (package.py:1483) and the second screen's parallel groups (:476). |
| R3 | glm P1-8: the "no hook" early return leaves out["search"] unset, so a caller doing out["search"][...] raises | out["search"] is set only at the end of the line-up loop (package.py:1931 in HEAD). Every earlier return already leaves it unset: fewer than 3 channels, no work_dir, no readable angles. The driver (tests/package/proof_ledger.py) never reads "search". |
| R4 | glm P1-7: hook_ratings does not reject a reply on ProviderError / SpendLimit | `r = None` at the top of each attempt. Only `router.call` raises those, and when it raises no reply was returned, so `r` is still None and there is nothing to reject. A reply that arrives and fails the contract is rejected (ValueError / TypeError / KeyError). |

## Recorded (P2, no change)

| # | finding | why no change |
|---|---|---|
| G1 | grok: CACHE_LOCK is per process, so two builds at once could lose a cache update | Builds run one at a time. A lost update loses only a saving: the entry is asked again and paid for again. A cached entry is keyed by content, so it can never be the wrong verdict. |
| G2 | grok: the hook cache key has no show date | The hook question carries only the clip's words and its channel's name: no date, title or window (HOOKS_PROMPT). The judge never sees a date, so its rating cannot depend on one (qwen reached the same reading). |
| G3 | glm P1-36: the channel name shown to the hook judge is not in the hook cache key | A renamed channel would keep a rating made under its old name. The rating judges the words; recorded for the next change to the hook key. |
| G4 | glm P1-1: this build's ledger (step_a.json) now also lists the verdicts served from the cache | Intended, and tested: the ledger records the verdicts this build USED. Spend is the router's ledger (SPEND_LY.json), never this file. |
| G5 | glm P1-2 / P1-6: the cache can hold two vendors' verdicts for one key, and a fresh build takes the first eligible in back-end order | Each screen only takes a verdict off the vendor and family it must avoid, so the first and second screens still come from two vendors. The first screen avoids the writers (Heimdall), and the second avoids the first's vendor (xai). The pick is deterministic (sorted). |
| G6 | glm P1-3: one stray id in the hook reply rates nothing | Intended. A reply out of contract is asked once more, then nothing is rated and the build stops with the error in its why (law L-m). Tested. |
| G7 | glm P1-18: out["hook_pool"]["passing"] is the list from before the second screen | Intended for the record: it is the list the second screen was asked about. The gate reads the list recomputed after the second screen, and the why of a stop after it names each hook's second-screen result. |
| G8 | glm P1-26: with no rating at all, the why ends "the best: " with no hook after it | The why still carries "(N not rated: <error>)". Cosmetic; recorded. |
| G9 | glm P1-35: a moment whose context is unavailable now fails even when a ledger verdict exists | This build's ledger starts empty (a new file per build), and a cache hit requires the same context sha. So this only makes "no context, no verdict" explicit (law L-s); it removes no reachable pass. |
| G10 | glm P1-19: the angle call re-asks on any error, while hook_ratings re-asks only on a reply out of contract | Unchanged: the angle loop's two tries predate this diff. hook_ratings follows law L-m (an unavailable call is no verdict). |
| G11 | glm P1-24: json.dumps of the context could raise on an exotic type | The context dict holds strings and the window CI._window_text returns: two sentence indices (ints, context_integrity.window), or for a caption record the seconds it covers (two rounded floats, caption_parts' `covered`). Both serialize. |

## Verification

- test_medley 105 OK; all 11 suites OK (the scratch copy dev18, base 635bc4f9).
