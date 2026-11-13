# glm-5.3-flash (z-ai/glm-5.3-flash) 88 s finish=stop usage in 5257 / out 2409 usd~0.052 (upper-bound price)

# pp-selectid-0335 — CYCLE 2 AUDIT (final review)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output:

- **The `targets` scope question (qwen's P1).** I inferred from the test that `targets` must be a local alias for `facts["targets_missed"]` and moved on. I did not flag it as needing verification. The consensus (K1) resolved it: `eligibility.py:425` binds `targets = facts.setdefault("targets_missed", [])` in the same branch, before T7/T8/T9. I missed that this was worth an explicit verification step rather than an assumption — qwen's "P1 due to inability to verify" framing was the more disciplined posture, even though the answer turned out benign.
- **The `select_by_id.PLAIN:591` consumer.** I noted that `eligibility.py:621` appends to `targets_missed` and that I couldn't see it, but I never asked whether the *retired reason string* "too_many_sentences" is referenced anywhere else. The consensus grep found the reason-to-plain-words table in `select_by_id.PLAIN:591` — a consumer I didn't think to look for. That's the strongest catch by the group that I missed: a retired reason can leave dead entries in a downstream lookup table, and the "KEPT, flagged" disposition (K2 law: not silently deleted) is the right call.
- **The 3-sentence boundary test.** I identified the gap (my P2-2) but only diagnosed it; the consensus *implemented* it (test lines 39–40). Credit where due — they converted my note into a pinned assertion.

What nobody missed, credit to glm: the observation that the retired entry now shares the `targets_missed` channel with *live* governing targets (glm P2-1) — a real semantic cost, correctly dispositioned as note-don't-fix.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Verdict | Why |
|---|---|---|
| qwen P1 — `targets` scope | **Agree, now resolved** | Consensus verified `eligibility.py:425` binds it before the T9 append; the passing test proves the append ran. Condition satisfied; no residual risk. |
| glm P1-1→P2 — brittle literal "3" in test | **Agree, resolved** | The C2 diff (test lines 37–38) now builds the expected string from `E.MAX_WINDOW_SENTENCES`. Exactly the fix I suggested. Note the "4" is still hard-coded, but that's the fixture's own sentence count — legitimate. |
| glm P2-1 — retired + live targets share `targets_missed` | **Agree, correctly kept** | The string self-identifies ("T9, retired by ruling 35") and nothing ranks on the list. A separate `facts["retired_targets"]` key would exceed the "smallest diff" mandate. Note, don't fix — correct. |
| glm P2-2 — 3-sentence boundary untested | **Agree, resolved** | Test lines 39–40: a 3-sentence span (at the cap) asserts no "T9" entry in `targets_missed`. This also pins the `elif` (not bare `if`) — the exact regression I worried about. |
| qwen P2 — wording fragility of the assertion | **Partially agree** | It's a substring `in` match, so trailing wording changes are tolerated; only the prefix is pinned. Standard practice, not worth a change. |
| qwen P2 — policy rationale embedded in the data string | **Agree, no action** | Compliant with "recorded only"; the parenthetical is documentation, not logic. |
| Consensus K2 — `select_by_id.PLAIN:591` dead entry | **Agree with disposition** | Keeping the table entry flagged (not deleted) is right: the older selector's model-feedback path is out of this diff's scope, and silently deleting it would violate the stated K2 law. |

No disagreements of substance. Every open condition from Cycle 1 was closed in C2.

## 3. NEW FINDINGS FROM THIS REVIEW

**N1 (P2) — `tests/eligibility/test_eligibility.py:39–40`: the 3-sentence boundary test constructs its context from a *different* Span than the one under test.**
Line 39 reads: `three = E.eligible(E.Span(four, 0, 2), ctx("hook", story=statements(E.Span(four, 0, 2))))`. The `Span(four, 0, 2)` is constructed twice — once as the span, once inside `ctx(...)` for the story. If `statements(...)` derives the story from the *span's* sentences, this is fine; but if it derives it from the full source, the two constructions are redundant yet harmless. I cannot verify `statements()`'s behavior from the diff. Either way the assertion (no "T9" in `targets_missed`) holds, because the *span* passed to `eligible` is the 3-sentence one. Cosmetic duplication, not a defect. Nobody caught this in Cycle 1 because the test didn't exist yet.

**N2 (P2) — the doubled `Span(four, 0, 2)` construction also means the 3-sentence case's `facts["n_sentences"]` is never asserted.** The 4-sentence case implicitly proves `n_sentences = 4` via the recorded string; the 3-sentence case proves only the *absence* of a T9 entry, which would also pass if `n` were computed as 0 (no_content path) or if the `elif` were skipped entirely for an unrelated reason. A one-line `self.assertEqual(three.facts["n_sentences"], 3)` would close it. Minor; the `elif`-vs-`if` regression — the thing the boundary test exists to pin — is nevertheless covered, because a bare `if` after `if n == 0: ... elif` would still append for n=3 only if the chain were restructured. I'm ~90% sure the test pins what it claims; the residual 10% is unverifiable from the diff.

**N3 (P2, note) — the C2 diff's eligibility.py hunk (lines 20–22) wraps the recorded string across two physical lines with an f-string continuation.** Both fragments are f-strings; the concatenation is implicit. This is correct Python, but it means the recorded string's exact whitespace at the seam ("...the 20 s clip limit and " + "the per-source limit...") depends on the trailing space in line 21's fragment. The test's assertion prefix ends at "ruling 35", *before* the seam, so the test does not pin the seam. If someone later edits one fragment and drops the trailing space, the recorded string gains "andthe" — no test would notice. Purely cosmetic; noting for completeness.

None of these rise above P2. Nothing in the combined analysis changed the risk picture.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| eligibility.py behavioral change (T9 retirement) | 9/10 | 9.5/10 | `targets` scope verified (K1); the only remaining uncertainty — the seam whitespace in the wrapped f-string — is cosmetic. |
| Test coverage of the change | 7/10 | 9/10 | Boundary case now pinned (test:39–40); expected string built from the constant (test:37). Residual: `n_sentences` not asserted on the 3-sentence case (N2). |
| Compliance with ruling 35 (nothing-else-changes, no hard-rule dependence, information-only) | 9/10 | 9.5/10 | The `select_by_id.PLAIN:591` dead entry is now *known and flagged* rather than unknown; the 20 s / 60–70 s hard rules are untouched by the diff. |
| Overall | 8.5/10 | 9.3/10 | All Cycle 1 conditions closed; only P2 notes remain. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (qwen's conditional — verify `targets` scope — was the only P1-class item, and it is resolved by the consensus verification at eligibility.py:425.)

**P2 MEDIUM**
1. `tests/eligibility/test_eligibility.py:39–40` — (N1) the 3-sentence case constructs `Span(four, 0, 2)` twice (span and inside `ctx`); harmless but redundant, and (N2) `facts["n_sentences"] == 3` is never asserted, so the boundary test's diagnostic power rests entirely on the absence of a "T9" substring. Add one `assertEqual` if you touch this test again.
2. `pipeline/eligibility.py:21–22` — (N3) the wrapped f-string's seam whitespace ("...limit and " / "the per-source...") is unpinned by the test, whose assertion prefix ends at "ruling 35". Cosmetic; note only.
3. `pipeline/eligibility.py` (select_by_id.PLAIN:591, outside this diff) — the retired reason's entry in the older selector's plain-words table is now dead. Correctly KEPT and flagged per K2; carry the flag forward so it isn't silently resurrected or silently deleted.

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Nothing needs to change — but if one thing matters most, it's that the *verification* of the `targets` binding (eligibility.py:425) and the *grep* for other consumers of "too_many_sentences" (select_by_id.PLAIN:591) are now recorded facts rather than assumptions; preserve that paper trail, because the retired rule's only remaining footprint is exactly the kind of thing a future cleanup silently breaks.

## 7. PRODUCTION READY?

**SHIP: yes.**

No conditions. All Cycle 1 conditions are closed: `targets` is verified bound at eligibility.py:425 before the T9 append (qwen's condition); the only other consumer of the retired reason string is a dead table entry, kept and flagged (glm's condition); the brittle literal and the untested boundary — my own findings — are both fixed in this diff (test lines 37–40). The diff touches exactly the two stated files, changes only the T9 branch and its test, leaves the 20 s (SEG_MAX_S, package.usable) and 60–70 s (RUNTIME_S, L-o) hard rules untouched, and `targets_missed` remains information-only: its readers (moments.py copy, eligibility.py:621 append) neither rank nor reject on it. The three P2 notes above are for the next pass, not this ship.