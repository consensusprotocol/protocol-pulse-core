# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 28 s finish=stop usage in 16586 / out 1248 usd~0.114 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-20261114_1441 (fixed diff after rework)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
Grok's <high> on parents_first only reordering spotlight finalists (not medley rank_key path) was missed in my Cycle 1; I focused on variant vs parent competition but did not trace the concrete medley selection sequence that could seal a variant before the full clip. Grok's <medium> on copied scores/ALONE was also missed — I accepted M.record + fresh judge() at face value without verifying text_sha256 + own-moment_id isolation. GLM's repeated-held-token prefix issue (ending before first occurrence, potentially keeping the actual held later token) was overlooked; the Cycle 1 consensus correctly flagged it even though the original test_blockware_held_on_401k passed.

2. WHERE DO YOU AGREE OR DISAGREE?
- Grok <high> (ordering/medley): Agree. The original design allowed competition; the fixed rework (holds() + replaced set + proof_ledger:203 filter) eliminates it entirely. The parent is dropped before medley/spotlight see the pool, so "tried first (14:12 order)" is now structural.
- Grok <medium> (score inheritance): Disagree on the fixed version. Facts + test_ruling_104:306 ("eligibility judged afresh"), spotlight.alone_score (requires text_sha256 match on own id), and M.record(..., M.judge(sp, ctx)) confirm the variant cannot inherit parent's ALONE or cached step-A verdicts. The copied m["scores"] are only for rank_score.
- Qwen <medium> (boundary off-by-one in for_pool:147): Partially agree on the original diff's ks + E.Span(k0, k) ambiguity, but the fixed tests (lines 295-296, 388-390, 402-405, 415-416) plus explicit SENTENCES[:3] assertions and src.sentences[k][1] < i logic now verify correctness for both first-word and last-word held cases. No off-by-one remains.
- GLM (b) (repeated token + first-occurrence): Agree. The fixed held_word:108-118 (canon_spans + first match of want tokens) plus test_an_insert_before_the_hold_cannot_be_placed_so_no_variant (lines 325-330) close the loophole; an earlier insert that cannot be excluded yields None, preventing a variant that keeps the later held word.
- GLM (a) & Qwen on gates/snap/derived_from: Fully agree — the fixed snap:9-11, package_for:20-21, variant:68-79, and "faces every gate again" facts confirm no shortcuts.

3. NEW FINDINGS FROM THIS REVIEW
<medium> pipeline/tail_variant.py:156 (ceiling ks list) + :164 (min k). Concrete sequence: parent 22.94 s with sentences [0,4], ceil_s set so only k=2 fits by token["end"] but floating-point token end times (or a sentence whose cumulative duration rounds to exactly ceil_s + epsilon) produces a variant whose own duration_s > ceil_s. for_pool does not re-check duration after variant() creation; spotlight.pool would later drop it, but the variant is still written to inputs["ruling_104"] and scored, wasting an ALONE call. Test at 402-404 uses +0.01 guard but does not cover token-end rounding. (Uncertain whether token times can actually produce > ceil_s given eligibility.Span, therefore flagged medium.)

No criticals or highs. All Cycle 1 attack vectors (a)-(e) plus new (f)-(g) are closed by the replacement logic, current-decoder-only holds(), test coverage of older-decoder/pass cases (TestTheHolds:348-362), and "no variant" notes.

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| Ordering / replacement | high    | none    | Replacement (for_pool:166, with_variants:203) + current-decoder holds() fully resolves competition and "FIRST the re-listen" that I only partially saw before. |
| ALONE / verdict freshness | medium | none    | Facts + test:306 + text_sha256 requirement eliminate inheritance concern. |
| Held-word placement / boundaries | medium | medium  | Repeated-token and first-sentence cases now explicitly tested; new minor ceiling floating-point edge surfaced. |
| Snap / derived_from recording | low     | none    | Explicit snap guard and pk["spotlight"] addition verified. |

5. FINAL PRIORITY LIST
P2 MEDIUM — pipeline/tail_variant.py:157 (after ks list for ceiling): add `if float(src.tokens[src.sentences[k][1]]["end"]) - t0 > ceil_s: continue` (or post-variant duration check) before appending.  
No P0 CRITICAL or P1 HIGH items. All ruling-104 requirements, SENTENCE LAW, SELECTION LOCK, and attack vectors (a)-(g) are satisfied by the diff + facts + tests.

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
Replacing the held parent entirely (for_pool:166, proof_ledger.with_variants:203, inputs["ruling_104"]["replaced"]) so the two never compete, while only triggering after a current-decoder hold, enforces the orchestrator's 14:12 order without any ordering hack.

7. PRODUCTION READY?
Yes with conditions: (1) lock_precheck.answer (used by holds:91) must strictly select only the current decoder/rules file as the tests assume (LP code not in diff — verify before merge); (2) first production build's ruling_104 notes must be checked for any real Blockware-like held cases that fall into "cannot be placed" or ceiling rounding paths. With those confirmed, ship.