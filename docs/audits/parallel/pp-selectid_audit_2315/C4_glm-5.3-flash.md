# glm-5.3-flash (z-ai/glm-5.3-flash) 117 s finish=stop usage in 22397 / out 3549 usd~0.120 (upper-bound price)

# pp-selectid — CYCLE 2 AUDIT (final diff, C4_STEP)

Scope: the three files in the diff only. Everything outside (`sentence_law.anchor`, `eligibility.Span/Source/sentence_ready`, `moments.judge/record/rank_score`, `package.build/usable`, `transcript_store.segments_sha256`, the pp-ingest adapter) is marked unverifiable where it matters.

---

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against the consensus:

- **K7 (grok P2, glm P1-1): the adapter's `delivered_ids` stay empty.** I flagged the `LB.rows(since, now, horizon_h=a.hours)` call at proof_ledger.py:386 as suspicious in Cycle 1 but hedged on whether it was a defect, because the adapter's semantics were unverifiable. The consensus resolved it with evidence I didn't have: `package.usable`'s any-overlap check (package.py:96-97) is *stricter* than an id filter, the driver passes every delivered pin's spans, and tonight's pins carry no ledger moment id anyway. The docstring at proof_ledger.py:285-289 now states this, and the new test (test_ledger_build.py:755-776) exercises it with an October-dated pin. **They caught the resolution; I only caught the question.** Agreed, and the disposition is correct — the overlap check subsumes the id check for this run.
- **K8 (qwen, glm P1-4): a row without `video_id` crashed the grouping; two id-less rows shared one report key.** I did not flag either. The fix (ledger_build.py:216-224) is right: the malformed key falls back to `row <i>` when the id is missing *or already taken*, and the test at :650-662 exercises both, plus a non-dict row. Complete.
- **glm (a): the sha does not cover the words.** I missed this entirely. `segments_sha256` hashes segments only, but the clip is cut from `rec["words"]` — so a word edited after the sha was taken would sail through. The fix (`words_off_segments`, ledger_build.py:102-130) ties the words to the sha-checked segments: the words must spell each segment's text exactly, in order, and each segment's start/end must equal its first/last word's times to 1 ms. The test at :567-590 edits a word's text, a boundary time, and appends an extra word — each correctly refused. This is the strongest new finding of the cycle and it was not mine.
- **glm P1-2 (glob+sort not total).** I missed it. Fixed properly: `WORD_RECORDS` (ledger_build.py:55) is a fixed two-tuple, not a glob, and the test at :592-601 proves a `_v2` name is *not* a slot (renamed punct record → "no word record in the store"). Note this is a *behavior choice* (a `_v2` record is now ignored, not merely unordered) — defensible under "never change what a check accepts", and the test documents it.
- **glm P1-3 (SEARCH_PAD_S / wrong-occurrence).** I missed the mitigation. The pad is unchanged, but the hit's offset from the row's own caption times is now recorded (`info["offset_s"]`, ledger_build.py:203-204) and tested (:503-510). A wrong-occurrence hit is now *visible*, not silent. That converts the residual risk to P2.

What nobody caught that I should weigh: nothing new — my Cycle 1 residuals are covered below.

## 2. WHERE DO I AGREE OR DISAGREE?

- **K7 — agree, resolved.** The overlap check is strictly stronger than the id filter *for spans*; the only case it misses is a delivered moment whose span is unavailable, which cannot happen here (the pins carry segments). The docstring's claim "an overlap check is stricter than an id check" is true given the pins always carry clip spans — which `delivered_pins` enforces (proof_ledger.py:340-341, "no clip" → refuse). Self-consistent.
- **K8 — agree, complete.** One subtlety verified: the key-collision guard (`mid not in report["malformed"]`, :218) means a *third* id-less row would take `row 3` even if a *legitimate* row 3 was also malformed — keys stay unique, counts stay right. Fine.
- **glm (a) — agree, with one residual.** `words_off_segments` consumes words greedily until the accumulated spelling reaches the segment's text length (:117-119). If a word's text is *longer* than what remains of the segment (e.g. a segment ends mid-word-token), `got` overshoots and the comparison fails — that's fail-closed, good. But the boundary-time check uses `ws[first]`/`ws[k-1]` where `first` is the *first word consumed for this segment*; if a previous segment's spelling check overshot... it can't, because overshoot fails the function. Verified consistent. Residual: word times *strictly inside* a segment (a middle word's start/end) are still outside the sha — the docstring admits this (:107-108) and flags it to the integrator. Correctly scoped, not a defect in this diff.
- **qwen's `since` P2 — agree it's a P2, and the new disposition answers it.** The default is now documented (proof_ledger.py:290-293): newest delivered pin's `approved_at`, overridable, and the run log prints which one was used (:382-383). Whether `approved_at` vs. publish time reads too few lines is unverifiable from the diff (the pin's publish time isn't shown to exist as a field), but the 72 h publish window (OR) makes the practical gap small: a row mined before `approved_at` but published inside the window still arrives. I agree with the downgrade.
- **qwen's SNAP_GUARD near-negations — agree, fixed.** `hardly|scarcely|barely|rarely|seldom` added (:41), tested (:495-501). Still not exhaustive ("infrequently", "un-", "non-") but the guard's purpose — the *snap* adds at most 3 words, and the residual risk is bounded and counted — makes this P2, not P1. Note the guard applies only to *added* words; a negation inside the anchored text was already judged by the ledger. Correct scoping.
- **grok's channel_conflict int/str P2 — agree, and it's now moot.** `sorted({str(r.get("channel_id")) ...})` (:229) normalizes before comparison, so `123` vs `"123"` no longer conflicts. The diff silently fixed this; nobody noted it. (Residual: a row with `channel_id=None` yields `"None"`, which would conflict with a row naming a real channel — but `word_source` reads `row.get("channel_id")` independently, so the conflict check and the Source can disagree. Minor, P2, unverifiable whether the adapter can emit None.)

## 3. NEW FINDINGS FROM THIS REVIEW

**P2-1. `word_source` reads `rs[0]`'s channel identity, but the conflict check only guarantees the rows *agree* — not that they agree with the store.** ledger_build.py:233 + 161. All rows for a video share `channel_id` after the :229-232 check, so the Source's channel is consistent *within the run*; but if the ledger's `channel_id` for the video is itself wrong (stale), the Source inherits it. Unverifiable from the diff (no cross-check against the store's own record). Concrete scenario: ledger says `UCdd`, the store/registry says `UCother` → eligibility judged under the wrong channel's registry entry. Not a regression; noting it because nobody did.

**P2-2. `report["word_records"]` records the record *read*, not whether any moment came of it.** ledger_build.py:242. The comment admits it ("read; whether a moment came of it: moments"). A video whose every row then fails `reanchor` still shows in `word_records` — correct, but a consumer skimming `word_records` alone could mistake "record read" for "moment produced". The counts (`moments`, `not_anchored`) disambiguate. P2, documentation-level.

**P2-3. `delivered_pins` accepts a pin whose `segments` entries lack `end` (or have non-float times) only via the `float(s["end"])` inside the comprehension — which raises, caught, and reported with the pin's path (:346-347).** Verified: `KeyError`/`TypeError`/`ValueError`/`AttributeError` all caught, message names the pin. The test at :750-752 exercises a missing `start`. Complete. (Listed because I checked it, not because it's a defect.)

**P2-4. `rows()`'s `env` passes `PP_SELECTID_PIPELINE` but the diff never shows the adapter reading it** — unverifiable, flagged only. If the adapter ignores it, the store-guard coordination ("the two never share modules", :74-75) rests on the subprocess isolation alone, which *is* sufficient (separate interpreter). No failure scenario; noting the docstring's claim is stronger than what the diff proves.

**P2-5. `build_inputs`'s `log` line (:266-270) prints `report['duplicates']` and `no_word_record` but not the *span-level* duplicate detail** — duplicates are counted, not named. Every other drop names its victim (`not_anchored` by moment_id, `malformed` by key, `no_word_record_videos` by vid). A duplicate row's identity (which moment_id lost the race) is recoverable only by diffing `mined.ledger_moment_id` of the produced moments against the input rows. Inconsistent with the "no silent drops" standard, though the *count* is honest. Concrete: two rows, same span, different moment_ids → one moment, one count, no name. P2.

**P2-6. `--since` naive-ISO check: `since.tzinfo is None` → refuse (:365-366), but `a.since.replace("Z", "+00:00")` handles only capital-Z.** A lowercase `z` or `+00:00`-less GMT offset like `+0000` (no colon) would raise inside `fromisoformat`, caught by the except at :369, exit 2 with why. Fail-closed, counted. Fine — noting the error message says "the delivered pins or 'since' cannot be read", which covers it.

**P2-7. `reanchor`'s `added`-words guard strips punctuation *before* the SNAP_GUARD test (:194-197), so a word that is *only* punctuation (e.g. a stray "—") becomes `""` and `SNAP_GUARD.search("")` — does the regex match empty?** `^(not|...|\w+n't)$|\d` against `""`: the alternation requires one of the listed words or `\w+n't` (nonempty) or a digit — `""` matches none, so an empty added word is *never* risky. Correct: a punctuation-only addition can't flip a claim. Verified, not a defect.

**P2-8. `info["offset_s"]` is only recorded when *all four* of t0, t1, a, b are readable (:203).** If the row's caption times are present but the *word record's* hit times are unreadable, no offset — silently. But `num()` returning None for a token time means the record's word timing is broken, which `words_off_segments` would likely have caught at the segment boundaries only. A *middle* word with an unreadable time passes the sha-tie check and silently loses the offset. P2, diagnostic-only.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| rows() adapter isolation | 8/10 | 9/10 | Timeout/unreadable → RuntimeError, fail-closed, tested; residual: docstring stronger than evidence (P2-4) |
| word_source / record trust | 7/10 | 9.5/10 | words↔segments tie (glm's finding) closes the biggest hole I'd left; passed_over/fallbacks fully visible |
| reanchor / snap | 8/10 | 9/10 | Near-negations, apostrophes, offset visibility; residual: guard not exhaustive (P2, bounded) |
| build_inputs accounting | 8/10 | 9/10 | Malformed keys unique, channel conflict whole-video; residual: duplicates unnamed (P2-5) |
| driver / pin handling | 8/10 | 9/10 | Read-before-write, required --delivered, which-pin errors; `since` documented and logged |
| Tests | 8/10 | 9/10 | Each named defect has a test that fails on reintroduction; gaps are P2-level |

Nothing changed my overall assessment: no P0, the P1s from Cycle 1 are either fixed or correctly downgraded with evidence.

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none.

**P1 HIGH** — none. (K7/K8/glm-(a) are fixed and tested; I verified each fix's mechanism, not just its test.)

**P2 MEDIUM:**
1. **ledger_build.py:248-249** — duplicates counted but not named; add the losing `moment_id`(s) to the report. (P2-5)
2. **ledger_build.py:233,161** — the Source's channel identity comes from the ledger row, never cross-checked against the store/registry; if they disagree, eligibility runs under the wrong channel. (P2-1)
3. **ledger_build.py:203-204** — `offset_s` silently absent when a *middle* word's time is unreadable; the sha-tie check only pins segment boundaries. (P2-8)
4. **ledger_build.py:74-75,82** — the store-guard coordination claim rests on subprocess isolation; the `PP_SELECTID_PIPELINE` env's consumption is unverifiable from this diff. (P2-4)
5. **ledger_build.py:41** — SNAP_GUARD still misses "infrequently", "un-", "non-"; bounded by the 3-word snap limit, counted on refusal. (agreed P2)
6. **proof_ledger.py:290-293** — `since` = newest `approved_at` is documented but the approved-vs-published gap is unresolved; the 72 h OR-window makes it practically small. (qwen's downgrade, agreed)

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

Name the losing moment_id(s) on a duplicate-span drop (ledger_build.py:248-249) — it is the only remaining drop whose *victim* is invisible, in a codebase whose stated standard is that no drop is silent.

## 7. PRODUCTION READY?

**Yes with conditions** — both conditions are the P2s I'd actually hold the line on:

1. Add the losing moment_id(s) to `report["duplicates"]` (or a parallel `duplicates_why`), so every drop names its victim.
2. Confirm with the integrator (one question, no code) that the ledger's `channel_id` is authoritative for eligibility, or add the store/registry cross-check — the Source's channel currently comes from the row alone.

Everything else ships as-is: the three Cycle-2 fixes (K7, K8, words↔segments) are mechanically correct, fail closed, and each named defect has a test that fails on reintroduction. No P0, no P1.