# claude-opus-5-5 (effort high) 236 s stop_reason=end_turn usage=in 67380 / out 23371

# PROTOCOL PULSE: Cycle 2 audit of pp-selectid-p2, chunk A2_core (fixed diff)

**Reviewer:** Claude (Anthropic).

**Two scope notes before the review:**

1. **My Cycle 1 text is missing.** The package says "[See below — you wrote this]", but nothing follows. I cannot honestly list what *I* missed. I use the union of the four Cycle 1 reviews and the Cycle 1 consensus as the baseline, and the "Cycle 1" score column shows the panel's chunk-A range, not my own number.
2. **A2_core contains only five files:** `context_integrity.py`, `moments.py`, `transcript_truth.py`, `trend_brief.py` and `vo_fidelity.py`. These files are **not** in this chunk:
   - `package.py`, `package_pin.py`, `providers.py`, `moments_gate_adapter.py`, `model_providers.json`
   - tests and R7

   So the headline consensus fix (C1: sealed gate inventory, `package.seal()`, R7 recompute) **cannot be verified at all**. Neither can the wiring of C3 (exclusion), the `truth_dir` optionality, the plain-VO path, the runtime arithmetic or `Router.down`.

---

## 1. What the panel caught, and how the fixes landed in this chunk

### Fixed and verified in the code shown

| Cycle 1 finding | Status in A2 | Evidence |
|---|---|---|
| `{"claims": []}` passes the blind verdict (C2) | **Partly fixed** | `VERDICT_INCOMPLETE` per sentence, L1923-1933. Residual holes are in §3. |
| Step B may omit relation pairs (C5) | **Fixed** | Exact pair set, no duplicates, enum checked, L408-418 |
| Second-pass compare is one-directional and set-based (C4) | **Fixed** | `Counter` in both directions, L993-995; names both ways, L998-999 |
| "Not measured" speaker passes | **Fixed** in `verify_segment` | `turn_change_inside is False`, L1046 |
| Second pass hard-codes the OpenAI model and URL (L-x) | **Fixed** in this file | `router.transcribe("transcribe", wav)`, L965 |
| Title Case suppresses NAME | **Fixed** | `names_of` scans every token, L1523-1539 |
| Attribution verb is case-sensitive | **Fixed** | `(?i:…)` verb group, L1554 |
| `"X: …"` colon attribution is unbound | **Recognised**, but see the new P1 below | L1561-1562 |
| Speaker always equals the channel | **Partly addressed** | `speaker_is` and verbatim `speaker_evidence`, L125-127 and L261-270 |
| Context window was "at most" 90/60 s (C11) | **Fixed**, except when timing is missing | L48-76 |
| Fact claims could cite the manifest | **Fixed** | Production claims cite only `manifest`; attribution and fact claims cite only the line's cites, L1909 |
| Exclusion verdict ran on the miner's own model (C3) | **Partly fixed** | `avoid_model`, L871/889. Wiring into `build` is not visible. |
| Failed trend brief was cached | **Fixed** | L1207 |

### Not verifiable here (must be in the next chunk)

- C1 seal and gate inventory, and the `package_pin` literals
- The R7 patch
- Whether `exclusion_verdict` is called on every packaged moment, rather than the miner's self-reported `excluded` (L791 is unchanged)
- Whether `truth_dir` is still optional
- The plain-VO truth pass
- The runtime double-subtraction
- `Router.down` permanence
- The `"openai"` fallback in `_writer_vendor`

---

## 2. Agreement and disagreement with the panel

| Finding | Position | Why |
|---|---|---|
| Fable, Opus, Sonnet: verdict passes on empty or partial claims | **Agree.** Still **partially open.** | Empty now fails. "One token of each sentence" still passes (§3, N1). |
| All three Claudes: second pass optional, partial, one-directional | **Agree.** Direction is fixed here. | Optionality and the trigger live in `package.py`, which is unseen. |
| Fable, Sonnet: exclusion gate not run in production | **Agree, unresolved in this chunk.** | L791 still derives `excluded` from the miner's `risk`. |
| Fable P1-2: speaker equals channel | **Partially agree that it is fixed.** | The evidence is verified as *somewhere in the excerpt*, not as the speaker of the selected words (N4). |
| Opus: hard-coded transcribe vendor | **Agree; fixed here.** | Independence from the *first* Whisper pass is still not enforced (N10). |
| Sonnet: `Router.down` permanent | **Cannot verify** | `providers.py` is absent. |
| Sonnet: runtime double-subtraction | **Cannot verify** | `package.py` is absent. |
| Grok Q1 72 / Q3 93: "no hole except an uncaught exception" | **Disagree** | Grok missed the empty-claims and partial-pairs holes that every other reviewer reproduced. Its scores are not credible as a safety signal. |
| Grok: "both agree" false-rejects same-video speakers | **Partially agree** | It fires only when the package has ≥2 source videos. `PARTY_WORDS` then adds *every* video id (L1747-1748), so two same-video clips are rejected. Fail-closed, so P2. |
| Grok: PRICE_NOW 5% tolerance false-passes 74000 vs 74210 | **Disagree** | 0.3% is honest rounding, not a misleading claim. |

---

## 3. New findings (not raised in Cycle 1, or introduced by the fixes)

### N1 (P0). The coverage check accepts a one-token fragment as "covering" a sentence
**Where:** `vo_fidelity.check_verdict`, L1932: `any(x < b and y > a …)`.

**The hole:**
- A sentence counts as covered if any claim span overlaps it by a single token.
- Combined with the commentary path (tests all "no", plus `strict_features` evaluated only on the claim's *words*, L1893), the rest of the sentence is never judged.

**Failing input:**
- VO line: `"Self-custody is about to be banned."`, with no cites.
- Deterministic layer: no number, name, quote, time word or attribution, so NEEDS_SOURCE is silent.
- Verdict reply: one claim, `words: "Self-custody"`, `class: "commentary"`, all five tests `"no"`.
- `strict_features("Self-custody")` is empty, the sentence is "covered", and `ok: True`.

**Fix:** the union of claim spans must cover every non-stopword token of every sentence, and `strict_features` must run on the whole sentence, not the fragment.

### N2 (P1). Unlocatable sentences are skipped instead of failing
**Where:** L1927-1929, `if at is None: continue`.

**The hole:** if a sentence's canonical tokens do not reappear in the line's canonical tokens, the sentence is silently treated as covered. This can happen with context-sensitive canonicalisation of numbers or abbreviations at a `_sentences` split.

**Fix:** append `VERDICT_INCOMPLETE` instead of `continue`.

### N3 (P1). "production" is an unguarded escape class
**Where:** L1904-1922.

**The hole:**
- Commentary gets `strict_features`. Production gets nothing.
- Any fact relabelled "production" passes with a ≥3-word support copied from `manifest_text`, e.g. `"contains clips from"` or `"Links to every"`.

**Failing input:** the claim `"BlackRock is selling"` with class `production` and support `{"segment":"manifest","words":"Links to every"}` gives `ok`. NAME catches "BlackRock" deterministically, but an unnamed fact such as "the ban passes next week" does not trip NAME.

**Fix:** apply `strict_features`, minus production nouns and counts, to production claims.

### N4 (P1). Speaker verification proves the evidence exists, not who spoke the selection
**Where:** `speaker_verified`, L261-270.

**The hole:**
- The host's `"welcome back to my channel"` 90 s earlier, followed by the guest speaking the selected words, verifies "host" if step A mislabels it.
- That verified name then licenses `"Natalie Brunell says …"` in `vo_fidelity`.

**Fix:** require the evidence span and the selection to share one diarisation label in the second pass, or require the evidence to lie inside the selected sentences.

### N5 (P1). Colon and "according to" forms bypass L-v 1
**Where:** L1708, `if form == "speech" and person_like(...)`.

**The hole:**
- The title `"Natalie Brunell: the AI bubble is about to pop"` binds `by_show` with form `colon`. No ATTRIBUTION violation fires, although the speaker is unverified.
- STEP_B itself (L140) says `"X: Y"` tells the viewer that X asserts Y. "according to Natalie Brunell" behaves the same way.
- HEDGE is also skipped for these forms (`_speech_verb` returns None, L1630).

**Fix:** apply the person-like check to the `speech`, `colon` and `according` forms.

### N6 (P1). `attributes_to` disagrees with `vo_fidelity._match` on partial names
**Where:** L346-356 versus L1576-1578.

**The hole:**
- A surname-only attribution such as `"Brunell warns the bubble will pop"` is bound by `vo_fidelity` to Natalie Brunell.
- `context_integrity` requires the full name run, so step C's `added_by` downgrades to a NOTE. The added claim is never NOT_ENTAILED.

**Fix:** use `vo_fidelity._match` semantics in `attributes_to`.

### N7 (P1). Step C enum values are never validated
**Where:** `_strict` (L202-212) checks keys only, and `YNU` (L45) is defined but unused.

**The hole:**
- `entails: "No"` or `"partially"` falls into the NOTE branch (L466-469) unless the limit is verbatim.
- `stronger_certainty: "slightly"` falls into the NOTE branch (L483-497).
- Out-of-contract answers become passes, which violates L-m/L-l.

**Fix:** validate every Step C field against `YNU` and reject the reply otherwise.

### N8 (P1). Step B and Step C can be shown a different VO from the one rendered
**Where:** `package_view` (L189-196) and `vo_words` (L313-314).

**The holes:**
- **Truncation:** `zip(after, bridges)` silently drops bridges when `len(bridges_after_clip) < len(bridges)`.
- **Duplicates collapse:** the `by_clip` dict keeps only the last bridge for a given `after_clip`, so step B never sees the earlier one.
- **Hook and out-of-range bridges vanish:** a bridge with `after_clip=0` or `≥ len(segments)` is never shown to step B.

**Failing input:** `bridges=["Both of them agree", "…"]` with `bridges_after_clip=[2, 2]`. Step B never sees "Both of them agree", so FALSE_RELATION cannot fire.

**Fix:** reject (CONTEXT_UNAVAILABLE) unless the after-clip list is the same length as the bridges, distinct, and every index is in the renderer's valid range.

### N9 (P1). `check_contexts` returns ok on a subset of segments
**Where:** L372 and L376.

**The hole:** `labels` holds only segments that have a context. A caller passing partial contexts gets `ok: True` with segments never judged by steps A and C. `judged` is recorded, but nothing here fails on it.

**Fix:** fail unless `set(labels) == set(all_labels)`.

### N10 (P1). The context window collapses to the selection when timing is missing
**Where:** L56 and L71, `and t0 is not None` / `and t1 is not None`.

**The hole:** with no token times, the window is `(k0, k1)`. Step A sees no before or after context, so a retraction or a referent outside the clip cannot be seen.

**Fix:** fall back to N sentences each side, or raise CONTEXT_UNAVAILABLE.

### N11 (P1). `check()` drops `now`, so time words are judged without the show date
**Where:** L229 calls `contexts_from_sources(package, sources)` with no `now`.

**The hole:** `show_date` becomes `"unknown"` (L242), so L-v 3 STALE_TIME is judged blind. This matters if `check()` is still "the pipeline's entry".

**Fix:** thread `now` through `check()`.

### P2 findings

- **N12. Name fold uses `rstrip("'’s")` as a character set** (L996-999).
  - `"Hess"` becomes `"he"`, which is almost always in the canonical tokens, so a dropped name falsely matches.
  - `"Ross"` becomes `"ro"`, which causes false rejects.
  - Fix: use `re.sub(r"['’]s$", "")`.
- **N13. B0 ("clips alone") runs with no `avoid_vendor`/`avoid_family`** (L392-393). Its `"certain"` can suppress a STRONGER failure (L485-486), so it is a writer-vendor input that can turn a fail into a NOTE.
- **N14. `exclusion_verdict` avoids only the miner's model** (L889), not its vendor or family (local gemma versus heimdall gemma). It also calls `router.reject(r)` without the `hasattr` guard used elsewhere (L898).
- **N15. False rejects and misses in the regexes:**
  - IMPERATIVE `(?:don't|never)…miss` (L1308) rejects `"Don't miss what's next"`.
  - AD_MARKERS `sponsor(ed)?\b` (L563) misses `"our sponsors"`.
- **N16. `check_brief` raises an uncaught TypeError on an unhashable topic** (L1168; the except at L1204 omits TypeError). A malformed trend reply crashes the cycle, although trend is "never a gate". A corrupt cache file (L1194) does the same.
- **N17. The signoff is excluded from `vo_words` and `raising_words_ok`** (L311-314, L326). A signoff attribution is invisible to step C.
- **N18. Second-pass independence is not enforced.** No `avoid_model` excludes the first-pass Whisper (L965), so a "transcribe" chain falling back to the same Whisper is not independent.

---

## 4. Revised scores (chunk A2_core only)

| Q | Cycle 1 (panel range, chunk A) | Cycle 2 | Why changed |
|---|---|---|---|
| Q1 fail-open | 35–40 (Grok 72) | **55** | Empty claims, missing pairs, one-way compare and "None passes" are fixed. Open: N1, N2, N7, N9, N10, and the unverifiable `truth_dir` and plain path. |
| Q2 vendor / L-x | 66–72 (Grok 88) | **75** | Transcribe goes through the router and `avoid_family` was added. Open: N13, N14, N18, and `package.py` unseen. |
| Q3 verbatim | 58–80 (Grok 93) | **78** | Clip text is still by id. Speaker naming is now evidence-based but weak (N4, N5). |
| Q4 deterministic | 35–40 (Grok 55) | **50** | Title Case and case-sensitivity are fixed. Open: N5, N6, N12, N15, and the `PARTY_WORDS` false reject. |
| Q5 tests / R7 | 10–30 (Grok 45) | **15** | Still no tests in this chunk, and C1 cannot be verified. |

---

## 5. Final priority list

### P0 (critical)

1. **Full-token claim coverage.**
   - Replace overlap-coverage in `check_verdict` (L1932) with full non-stopword token coverage per sentence (N1).
   - Run `strict_features` on the uncovered remainder.
   - Fail on unlocatable sentences (N2, L1928-1929).
2. **Prove C1.** Put `package.py`, `package_pin.py` and the R7 `pinned.py` in the next audited chunk, with tests showing that:
   - the seal is recomputed;
   - every inventory row must be PASS, measured and not replayed;
   - the `exclusion` row comes from `exclusion_verdict`, not from L791;
   - the `second_pass` row covers *every* segment, including the plain path, and is not optional.

### P1 (high)

3. Guard production claims with `strict_features` (N3, L1904-1909).
4. Validate step C enums against `YNU` (N7, L202-212, L463-497).
5. `package_view` / `vo_words`: refuse mismatched, duplicate or out-of-range `bridges_after_clip` (N8, L189-196, L313).
6. `check_contexts`: fail unless every segment is judged (N9, L372).
7. Apply the person-like L-v 1 check to the `colon` and `according` forms, and run HEDGE on them (N5, L1708, L1630).
8. Tie speaker evidence to the selected words via diarisation (N4, L261-270).
9. Unify `attributes_to` with `_match` (N6, L346-356).
10. Make the window fall back to sentence counts or fail when timing is missing (N10, L56/L71). Thread `now` through `check()` (N11, L229).

### P2 (medium)

11. Fix the name folding in `compare` (N12, L996-999).
12. Add vendor and family avoidance:
    - B0 with `avoid_vendor` (N13);
    - `exclusion_verdict` with `avoid_vendor` and `avoid_family` (N14);
    - the second pass avoiding the first-pass model (N18).
13. Regex false rejects and misses:
    - drop `miss` from IMPERATIVE (N15);
    - change AD_MARKERS to `sponsors?|sponsored` (N15);
    - scope `PARTY_WORDS` to cited segments (L1747).
14. Catch TypeError in `grok_brief` and on cache reads (N16). Include the signoff in step C's video words (N17).

---

## 6. Single highest-leverage change

Make every gate's code decision require **complete coverage of what it certifies**: every token of every line, every segment in context, every segment's second pass. Prove it with the sealed inventory and R7 tests in the next chunk, because every remaining P0 is a gate that returns `ok` after judging only part of its input.

## 7. Production ready?

**No.** Conditions for "yes with conditions":

1. P0-1 (full-token verdict coverage) and P1 items 3–7 are merged, each with a regression test reproducing the failing input given above.
2. `package.py`, `package_pin.py`, `providers.py`, the R7 patch and the tests are submitted and audited. They must show:
   - the pin is refused unless every inventory row is PASS, measured, not replayed, and the seal recomputes;
   - `exclusion_verdict` and the second pass run on every shipped segment (plain path included) with no optional bypass.
3. A dry run on a recorded cycle shows at least one package passing all gates and at least one adversarial package failing each new check.