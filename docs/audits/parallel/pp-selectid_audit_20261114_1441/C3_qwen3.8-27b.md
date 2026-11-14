# qwen3.8-27b (qwen/qwen3.8-27b) 102 s finish=stop usage in 19695 / out 3533 usd~0.112 (upper-bound price)

# CYCLE 2 AUDIT — pp-selectid-20261114_1441 (ruling 104, the tail-side twin)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **grok's <high> (medley ordering)**: I noted the ordering question only obliquely — I verified the spotlight's finalist order but did not trace the medley path (`package.build`) separately. grok's point that `parents_first` only reordered the spotlight's finalists while the medley used `rank_key` directly was a real gap in my review. **Caught by grok, missed by me.**
- **grok's <medium> (inherited ALONE score)**: I flagged that `variant()` copies `m["scores"]` (tail_variant.py:72-74) but concluded it was "by design, not a violation" — which is right as far as it goes, but I didn't chase the question of whether the *scorer's* verdict (as opposed to the miner's scores) could leak. grok's framing was sharper. However, the consensus refutation (the ALONE gate reads the clip scorer's verdict keyed by the moment's own id and text_sha256, and `M.record` copies no scorer_verdict) answers it — the variant has its own id and text, so it can only ever see its own verdict. **grok raised it; the consensus resolved it; I partially missed the resolution's force.**
- **qwen's <medium> (index convention in `for_pool`)**: I worked through the `<` boundary logic in Cycle 1 and concluded it was correct (my (b) section, which I then partially withdrew mid-argument). qwen's winding verification ends at the same place the test does: `E.Span(src, 0, 2)` + `SENTENCES[:3]` at test line 295-296 pins the convention. **qwen's finding was a question, not a defect; I agree with its own self-resolution.**
- **glm's (b) (repeated held token)**: I raised this myself in Cycle 1 and got cut off mid-argument. The consensus refutation ("the variant is a PREFIX ending before the f[irst occurrence]") is correct: `held_word` returns the *first* occurrence's index (tail_variant.py:116-118, `for i in range(len(toks) - len(want) + 1)`), and `for_pool` ends the variant at the last boundary *before* that first occurrence (tail_variant.py:147), so a later repeated occurrence is left out too. The variant cannot contain the held occurrence. **I raised it; the consensus closed it; my Cycle 1 answer was truncated.**

What nobody caught, including me, in Cycle 1 — see §3.

## 2. WHERE DO I AGREE OR DISAGREE?

**grok <high> (medley ordering) — AGREE, now moot.** The finding was correct against the Cycle 1 diff. The rework removes `parents_first`/`finalist_order` entirely and instead *replaces* held parents in the pool (proof_ledger.py:203: `[m for m in moments if m["moment_id"] not in replaced] + variants`), so parent and variant never compete anywhere — spotlight, medley, or otherwise. This is a stronger fix than ordering: it makes the 14:12 order ("FIRST the re-listen; if it holds, the variant") structural rather than ordinal. The full clip is honoured because the variant only exists once the current pre-check, re-listen included, has held the full clip (holds() reads only current-decoder/current-rules answers, tail_variant.py:83-94). Verified: test lines 433-448 exercise `with_variants` directly and the held parent is dropped. **Resolved.**

**grok <medium> (inherited ALONE) — AGREE with the refutation.** `variant()` (tail_variant.py:72-75) passes `{"scores": m["scores"], ...}` to `M.record` — the *miner's* scores, which feed `rank_score` (line 76) only. The ALONE gate reads the clip scorer's verdict for the moment's own id, and (per the consensus, which I adopt) `package.with_verdict` requires the verdict's `text_sha256` to equal the moment's text's. The variant's text differs from the parent's (test line 295: `SENTENCES[:3]` vs. all five), so a parent's verdict cannot satisfy it. No cached-ALONE path. **Not a defect.**

**qwen <medium> (boundary convention) — AGREE, resolved by the test.** `E.Span(src, 0, 2)` producing `SENTENCES[:3]` (test lines 294-296) and `v["sentences"] == [0, 2]` (line 296) fixes the convention: the second argument is the last sentence *index included*... wait, no — `variant()` at tail_variant.py:64-67 requires `k0 <= k < k1` and builds `E.Span(src, k0, k)`, and the test at line 296 asserts `v["sentences"] == [0, 2]` for `k=2` with text `SENTENCES[:3]` (sentences 0, 1, 2). So `E.Span(src, 0, 2)` includes sentences 0..2 — the second argument is *inclusive* of sentence 2, i.e. it's the last sentence, and `sentences[k][1]` is that sentence's last word. Then `for_pool`'s filter (line 147) `src.sentences[k][1] < i` selects sentences whose last word precedes the held word, and `ks[-1]` is the latest such. With the held word "401k." at `src.sentences[3][0] + 4` (test line 317), sentences 0-2 qualify, variant = [0,2], held word excluded. Correct. **No defect.**

**glm's withdrawn (a) note and its 12 s floor note — AGREE, not defects.** The variant enters the pool before the free pool (proof_ledger.py:214, before `inputs.json` is written and before the clip scorer/medley/spotlight run), so the 12 s floor and every other free rule apply to it exactly as to any moment. The snap guard (spotlight.py:9-11) only blocks *outward* snapping; a variant under 12 s is simply not usable, which is the same as any short moment. **No defect.**

**qwen's P1 "doomed variant" — AGREE, and the fix is in the diff.** The Cycle 2 diff at tail_variant.py:152-155 is exactly the consensus's one-line fix: when `e is not None` and `ks` is empty (held word unplaceable or in the first sentence), `for_pool` does `continue` — no variant, no ceiling trigger, no replacement. Test lines 413-421 verify both the first-sentence case and the first-sentence-plus-ceiling case, and the mutation (P6) is killed. **Resolved.**

**grok's new <medium> (ceiling floating-point, tail_variant.py:156-158) — PARTIALLY AGREE, downgrade to low.** grok's concern: `ks = [k for k in range(k0, k1) if float(src.tokens[src.sentences[k][1]]["end"]) - t0 <= ceil_s]` could, in principle, pick a `k` whose variant duration exceeds `ceil_s` due to token-end rounding. But: (1) the variant's `duration_s` is computed by `M.record` from the same `src.tokens` end times, so the variant's duration *is* `float(src.tokens[src.sentences[k][1]]["end"]) - t0` (the span's start is the parent's start, unchanged). The filter guarantees this is `<= ceil_s`. (2) Even if a floating-point edge produced a variant marginally over the ceiling, the free pool (spotlight.pool) would drop it — it would never reach a pin. (3) The test at line 403 uses `+0.01` guard, which is the right test for the boundary. The only cost is a wasted ALONE call on a variant that the free pool would reject. **Not a defect; at most a minor efficiency note. I do not agree it is <medium>.**

## 3. NEW FINDINGS FROM THIS REVIEW

**<low> tail_variant.py:147 — `held_word` returns the index of the *last* word of the held token, not the first.** `held_word` at line 118 returns `w0 + spans[i][1]`, where `spans[i][1]` is the *last* word index of the matched token sequence. The filter at line 147 is `src.sentences[k][1] < i`, i.e. "sentence k's last word is before the held token's *last* word." Consider a held token that spans a sentence boundary: e.g. the held token is "a 401k" where "a" is the last word of sentence 2 and "401k" is the first word of sentence 3. Then `i` = index of "401k" (the last word of the token). Sentence 2's last word is "a", which is at index `i - 1 < i`, so sentence 2 *qualifies* and the variant would end at sentence 2 — but sentence 2 contains "a", which is part of the held token. The variant would contain the first word of the held difference.

However: this requires the held token to span a sentence boundary, which means the second recogniser's reading differs from the approved text *across* a sentence break. In practice, `class_84` operates on the full text string, and a token spanning a sentence boundary would be unusual (sentences are delimited by punctuation, and a "token" in the canon sense is a word or multi-word phrase within a sentence). The test suite does not cover this case. **Flagging as <low> because the concrete sequence is contrived and the ruling-84 class is unlikely to produce a cross-sentence token, but it is a real gap in the logic if it could occur.**

**<low> tail_variant.py:158 — ceiling trigger uses `m["start"]` but the variant's start is the parent's start.** This is correct by design (the variant is a prefix of the parent), but it means the ceiling check is `end_of_sentence_k - parent_start <= ceil_s`. If the parent's start is not 0 (it isn't, in general), this is the correct duration. No issue.

**<low> proof_ledger.py:203 — `with_variants` appends variants after all non-replaced moments.** The order in the returned list is `[non-replaced moments in original order] + [variants in for_pool order]`. The medley and spotlight sort by `rank_key` anyway, so list order is irrelevant to selection. The only consumer that cares about order is the `inputs.json` dump (line 217), which is a record, not a selection. **No defect.**

**<low> spotlight.py:9-11 — the snap guard checks `m.get("derived_from")` but `derived_from` is a dict, not a string.** The check is `(m.get("derived_from") or {}).get("ruling") == 104`. This is correct: `derived_from` is set to a dict (tail_variant.py:68-71, 79), and `.get("ruling")` on that dict returns 104. A non-variant moment has no `derived_from` key, so `m.get("derived_from")` is `None`, `or {}` gives `{}`, and `.get("ruling")` is `None != 104`. **Correct.**

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| Ordering / replacement | high | none | Replacement (for_pool:166-167, with_variants:203) + current-decoder-only holds() fully resolves competition. The 14:12 order is structural. |
| ALONE / verdict freshness | medium | none | text_sha256 + own-moment_id isolation confirmed. Copied scores are miner's only. |
| Held-word placement / boundaries | medium | low | Repeated-token and first-sentence cases tested. New <low> on cross-sentence token (contrived). Ceiling FP edge is not a defect. |
| Snap / derived_from recording | low | none | Explicit snap guard and pk["spotlight"] addition verified. |
| Doomed variant (qwen P1) | — | none | Fixed in diff (tail_variant.py:152-155). Test + mutation. |
| Stale holds (older decoder/rules) | — | none | holds() uses lock_precheck.answer which filters by current decoder/rules. Test lines 346-373. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL:** None.

**P1 HIGH:** None.

**P2 MEDIUM:** None.

**P3 LOW (informational, no change required):**
- tail_variant.py:147 — cross-sentence held token would not be fully excluded. Contrived; ruling-84 tokens are within-sentence. No test needed unless cross-sentence tokens are possible in practice.
- tail_variant.py:158 — ceiling FP edge could waste an ALONE call on a variant the free pool rejects. Not a correctness issue.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Replacing the held parent entirely (for_pool:166-167, proof_ledger.with_variants:203) so the two never compete, while only triggering after a current-decoder hold, enforces the orchestrator's 14:12 order without any ordering hack — this is the change that turned a <high> into a non-issue.

## 7. PRODUCTION READY?

**Yes with conditions:**

1. **lock_precheck.answer** (used by holds:91) must strictly select only the current decoder's file under the current rules. This is unchanged code (`result_file(seg, results_dir, decoder=DECODER)` and `_matches` checking `rules == RULES`), and test_ruling_104 verifies it through holds() (lines 346-373: older decoder and older rules entries are not read). **Condition met by existing code + test.**

2. **The first production build's ruling-104 notes** should be read on STATE line 1 after the build, to confirm the Blockware 06d34e15 case produces the expected variant ending "...I still don't use my Roth IRA." and that the parent is replaced. **Condition: operational, not code.**

3. **The cross-sentence held-token edge** (P3 low) should be confirmed impossible in practice: verify that `canon.canon_spans` and `class_84` never produce a token that spans a sentence boundary. If they can, add a guard in `held_word` to return None when the matched token spans a sentence boundary. **Condition: confirm or guard.**

All ruling-104 requirements, SENTENCE LAW, SELECTION LOCK, and attack vectors (a)-(i) are satisfied by the diff + facts + tests. The 20/20 mutation pass and 14 tests (15 with the fix's assertion) confirm coverage.