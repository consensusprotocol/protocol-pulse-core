# glm-5.3-flash (z-ai/glm-5.3-flash) 25 s finish=stop usage in 7550 / out 1382 usd_reported=0.000660 usd~0.043 (upper-bound price)

# CYCLE 2 REVIEW — pp-selectid, RULING 155 (1) hardened diff

## 1. WHAT DID THEY CATCH THAT I MISSED?

- **qwen's KeyError P1** was the real catch: the `_MANY` dicts could drift from the canonical `STEP_A_SOFT` / `EDGE_WORDS`. I missed the two-dict duplication as a drift hazard. The fix (line 37: four-step `or`-fallback ending in `or c`) closes it — and the consensus's "unreachable today" analysis is right, since `context_a` only emits codes already in `STEP_A_SOFT` and `soft_edges` only yields EDGE_IN/EDGE_OUT. Correctly hardened, correctly classified.
- **qwen's 6-clip COUNT_WORDS finding**: I missed that `COUNT_WORDS` tops out at 5. But the consensus's rebuttal is sound — a medley is hook + 2–4 clips (≤5 segments), so 6 never occurs. Agree: no change needed, though the `str(len(lbs))` fallback makes it harmless anyway.
- **gpt-oss's P1** (cap counts kinds, still passes): consensus disproved it correctly — the rule IS kinds, and `test_the_cap_counts_kinds` pins it. I agree with the disproof.
- **qwen's FLAGGED-row filter**: consensus's disproof is right — `review_flags_of` reads only FLAGGED rows too, so `content_flags` and the sealed-flags equality check stay consistent. No behavioural divergence.

## 2. AGREE / DISAGREE

| Finding | Verdict |
|---|---|
| qwen P1 KeyError | Agree (was real); now fixed correctly; "unreachable today" also agreed |
| qwen 6-clip COUNT_WORDS | Disagree (non-issue; ≤5 segments; fallback is graceful) |
| qwen FLAGGED filter | Disagree (matches `review_flags_of`; consistent) |
| gpt-oss P1 cap | Disagree (consensus disproof correct) |
| gpt-oss P2 sentence collapse | Agree it's intended — one kind, one sentence |
| qwen P3 `_CLIP_REF` "first" | Agree, P3; note the merged form uses "N clips" and singles use "The second/third…", so "first" never occurs today |

## 3. NEW FINDINGS (Cycle 2)

- **[P2] `seg_marks` hook term can double-count the hook's step-A flag.** Line 52–54: the hook's step-A codes are counted in the distinct-`step_a_flags` set, *and* `hook_own(segs[0]).flagged` adds 1. If the hook's medley-row flag is the *same doubt* (under-bar) it's a distinct kind — fine — but if the hook's step-A code and its hook-own flag are meant as one kind under 155 (1), the search's count diverges from `content_flags`'s. The two counters should agree by construction; today they agree only by accident of which flags co-occur. Add a comment or a cross-check test.
- **[P2] `flag_kind` strips the clip ref but not the channel list inside the merged sentence's parens — actually it does (`\([^)]*\)`), but only the FIRST paren group.** A sentence like `"Three clips (A, B): the checker doubted this is the speaker's own sincere view (they may be quoting someone or joking)."` — the second parenthetical survives, which is *desired*; but a flag whose doubt text itself begins with a parenthesised clip-like prefix would be partially stripped. Currently no such sentence exists. [P3] in practice; note it.
- **[P3] `kind_sentences` dedupes labels per code but preserves first-seen code order — good — yet the merged sentence's channel order follows label order (`hook, clip_01, clip_02`), while the test's `MERGED` expects "Natalie Brunell, Strategy, Yahoo Finance" (hook first).** Consistent, but the note's example in the ruling ("Strategy, Natalie Brunell, Yahoo Finance") orders differently. Cosmetic; the ruling's example is not normative. No change.
- **[P3] `content_flags` silently returns 0 for a non-dict `gates`** — previously the old code also effectively returned 0 via the exc-guard; consistent. Fine.

## 4. REVISED SCORES

| Subsystem | C1 | C2 | Why |
|---|---|---|---|
| package.kind_sentences | 8 | 9 | KeyError hardened; fallback chain correct |
| package.seg_marks | 8 | 8 | kinds counted, but hook/step-A overlap untested |
| package_pin.content_flags / flag_kind | 8 | 9 | FLAGGED filter consistent; PER_CLIP_KIND preserves integrator's prefix match |
| Tests | 7 | 8.5 | 5/5 mutations killed; missing: hook+step-A co-occurrence, non-`_MANY` code (consensus's P3, still open) |

## 5. FINAL PRIORITY LIST

- **[P2]** `pipeline/package.py:52–54` — seg_marks: document/verify the hook-own +1 vs the hook's step-A codes are distinct kinds; add a co-occurrence test.
- **[P2]** tests: add the non-`_MANY`-code regression (qwen's P3, still unaddressed) — one line exercising the new `or c` fallback.
- **[P3]** `package_pin.py:98` — `_CLIP_REF` only strips the first paren group; fine today, add a comment.
- **[P3]** `package.py:9` — COUNT_WORDS: harmless; optionally note the ≤5-clip invariant.

## 6. SINGLE HIGHEST-LEVERAGE CHANGE

Add the regression test for a code with no `_MANY` wording — it pins the hardened fallback that is currently the only path with no test coverage.

## 7. PRODUCTION READY?

**Yes with conditions:** (a) the non-`_MANY`-code fallback test, (b) the seg_marks hook/step-A co-occurrence test. Both are one-line additions; the logic itself is correct.

P1_OR_WORSE: 0