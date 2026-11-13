# glm-5.3-flash (z-ai/glm-5.3-flash) 159 s finish=stop usage in 14725 / out 5008 usd~0.119 (upper-bound price)

# pp-selectid — CYCLE 2 AUDIT (final review)

## 1. WHAT DID THEY CATCH THAT I MISSED?

Honest accounting against my Cycle 1 output (I flagged the vacuous-sha path, the silent fall-through, and the snap-meaning question; I did not flag the adapter's empty-read, the `rs[0]` channel-identity question, or the hard-coded delivered pins):

- **Grok's P0 (empty successful read is "quiet")** — I missed it entirely. I never examined what happens when the adapter returns `returncode=0` with zero rows. Grok's scenario is concrete and correct: a ledger where every row is delivered/opted-out yields `{"rows": [], "report": {"excluded": {...}}}` with no `"contract"` key → `rows()` returns `([], report)` → `build_inputs` produces 0 moments → `package.build` runs on nothing. Whether that's a bug depends on `package.build`'s contract (unseen), but the *docstring* at `ledger_build.py:66-67` promised "no rows is never read as a quiet ledger" — and the code does exactly the opposite for the empty case. Grok caught the docstring/behavior mismatch; I didn't.
- **Qwen's P1-1 (`rs[0]` channel identity)** — I missed it. `build_inputs` at `ledger_build.py:154` calls `word_source(rs[0], ...)` and then re-anchors *all* of `rs` against that one Source. If a video's rows disagree on `channel_id` (compilation, re-upload), the Source's channel identity comes from whichever row sorted first in `by_vid` insertion order. Qwen's credits-card scenario is plausible. I can't verify whether the ledger guarantees one channel per video (the ledger schema is unseen), so this stays "flagged, unproven" — but it's a real gap in my Cycle 1.
- **Qwen's P1-3 (hard-coded `DELIVERED_PINS`)** — I missed it. `proof_ledger.py:231-232` hard-codes two absolute paths under `HERE/proof/fresh_20261112_050611/`. If that directory is cleaned or the run is re-run on a different checkout, `delivered_spans()` raises `FileNotFoundError` (uncaught, at `proof_ledger.py:239` — no try/except around `json.load(open(p))`). The consensus note says this was "IMPLEMENTED: --delivered PIN ... (default: tonight's two delivered pins); a missing or broken pin file stops the run (fail closed)" — but I see no try/except in `delivered_spans` or `main` that would *catch* the FileNotFoundError and report it; it just propagates as a traceback. Fail-closed, yes, but ugly and uncounted. Partially implemented as claimed.
- **Grok's P1 (snap enlarges the span, `mined.ledger_text` retains the shorter string)** — I flagged the meaning-change question but didn't note that `mined.ledger_text` (line 173) preserves the *ledger's* shorter text while `rec["text"]` becomes the *record's* longer text. Grok's framing — "words that were never in the mined ledger row" — is sharper than mine. The consensus's SNAP_GUARD mitigation (negations/digits only) is a reasonable, tested answer; I accept it.

What nobody caught that I should have: **`word_source`'s `why` variable is overwritten, not accumulated** — see new finding N-1 below.

## 2. WHERE DO I AGREE OR DISAGREE?

| Finding | Disposition | Why |
|---|---|---|
| Grok P0 (empty read quiet) | **Agree, but reframed** — the consensus's reframe is right | A failure/refusal raises (tested at `test_ledger_build.py:441-452`); an empty successful read is a *real* result, and the report's `excluded` counts say why. The docstring at lines 66-67 now says exactly this. Grok's original P0 was correct against the *old* docstring; the fixed diff resolves it. The test at lines 456-460 covers it. Resolved. |
| Grok P1 (snap changes meaning) | **Agree, resolved by SNAP_GUARD** | The guard at `ledger_build.py:39-43` refuses a snap that would add a negation or a digit — the two word classes that flip or add a claim. Tested at `test_ledger_build.py:357-364` with both concrete cases ("Nobody", "2009"). The 3-word boundary is tested at lines 348-355 (3 snaps, 4 refused). This is a genuine, tested mitigation. Residual: a snap can still add *non-guarded* words (e.g. "Actually" or "Also") that subtly shift emphasis — but those don't flip a claim, and the ledger's scores are discovery, not the render's judgment. Accept. |
| Qwen P0-1 (punctuated not read first) | **Disagree with the original, agree with the consensus** | `key=lambda p: "punct" not in p` gives the punctuated file `False` (0), which sorts *before* `True` (1). Qwen's claim that the sort is "inverted" is wrong. The consensus refuted it correctly, and the new test at lines 406-417 proves it. Resolved. |
| Qwen P0-2 (snapped span not sentence-ready) | **Agree with the consensus's refutation** | `E.sentence_ready(src)` is checked on the *record* at `ledger_build.py:104`, and the Span is constructed from whole sentences `k0..k1` of that record by construction (`E.Span(src, k0, k1)` at line 139). If the record is sentence-ready, its sentences are punctuated. Qwen's own caveat ("if sentence_ready is a per-record flag... this is not a bug") applies. Resolved. |
| Qwen P1-1 (`rs[0]` channel identity) | **Partially agree — still open** | The mechanism is real (line 154 uses `rs[0]`'s channel for the whole video's rows). But whether it *matters* depends on whether the ledger guarantees one channel per video — I cannot verify from the diff. If it can't happen, it's a P2 documentation note; if it can, the credits card (Law CREDITS) shows the wrong channel. Flag as P1-until-confirmed. |
| Qwen P1-2 (SEARCH_PAD_S=30 magic number) | **Agree, P2** | Fail-closed and counted (`not_anchored`), so it's not silent. But 30 s is undocumented; the comment at line 44 says what it does, not why 30. P2. |
| GLM P0-1 (missing `transcript_sha256` passes vacuously) | **Disagree — the consensus's refutation is correct** | `rec.get("transcript_sha256")` is `None` when absent; `None != segments_sha256(...)` unless `segments_sha256` also returns `None`. GLM hedged ("I cannot prove it never returns None") — fair, but the test at lines 389-404 covers the wrong-sha and edited-after-sha cases, and the consensus states the refutation plainly. If `segments_sha256([])` returned `None`, then `None != None` → False → not skipped → `tokens_from_record({})` — but that's a hypothetical about unseen code. I'll note it as a P2 "add a missing-sha test" rather than a P0. |
| GLM P0-2 (silent fall-through, uncounted preferred-source degradation) | **Agree, P2** | The report records only the *winner* (`word_records[vid]` at line 159); a rejected punctuated record leaves no trace beyond the final `why` string. The diff's own header promises "every drop counted" — a rejected *preferred* record is a drop. P2. |
| GLM P1-1 (snap changes meaning, scores kept) | **Agree, resolved by SNAP_GUARD** | Same as Grok P1 above. |

## 3. NEW FINDINGS FROM THIS REVIEW

**N-1 (P1): `word_source`'s `why` is overwritten, not accumulated — the report can misattribute the drop reason.**
`ledger_build.py:90-106`:
```python
why = "no word record in the store" if not paths else None
for p in paths:
    try:
        rec = json.load(open(p))
    except (OSError, ValueError):
        why = why or "a word record that cannot be read"
        continue
    if rec.get("unverified") ...:
        why = "a word record whose segments do not match its transcript_sha256"   # OVERWRITES, no `or`
    ...
    if E.sentence_ready(src):
        return src, p
    why = "a word record that is not sentence-ready (law L-e)"                    # OVERWRITES, no `or`
```
Concrete scenario: the punctuated record fails its sha check (`why` = "segments do not match..."), the loop falls through to the verbatim record, which is *not sentence-ready* → `why` is overwritten to "not sentence-ready (law L-e)". The report now says the video waits because of L-e, when the *primary* cause was the sha mismatch on the preferred record. This is exactly the "silent, uncounted degradation" GLM's P0-2/P1-2 complained about — the *count* exists but the *reason* is the last failure, not the first or the most important. Fix: accumulate (`why = why or "..."` on every assignment, or collect a list). One-line fix, and it's the difference between "the report tells you why" (the diff's promise) and "the report tells you the last thing that happened."

**N-2 (P2): `build_inputs`'s duplicate check keys on `(vid, sp.k0, sp.k1)` but `seen.add` happens *after* the malformed-rows try/except — a malformed row's span is never added to `seen`, so a later good row on the same span is kept.** Wait — actually, reading again: the `seen.add((vid, sp.k0, sp.k1))` at line 179 happens only after `M.record` succeeds (line 174-175). So a malformed row (L5 in the test) does *not* reserve its span, and a subsequent good row on the same span *would* be kept. Is that wrong? Arguably correct (the malformed row produced no moment, so the span is free). But the test at lines 419-437 has L1 and L2 as the *first two* rows, both good — the malformed row L5 is on `SENTS[3]`, a different span. The interaction "malformed row frees its span for a later duplicate" is untested. Minor; P2.

**N-3 (P2): `reanchor`'s `added`-words guard strips punctuation with `strip(".,!?;:\"'()")` but not other characters** — e.g. "—", "…", "’" (curly apostrophe). `SNAP_GUARD`'s `\w+n't$` alternative requires ASCII `n't`; a curly-apostrophe "don’t" (U+2019) matches neither the literal `don't` alternative nor `\w+n't` (since `’` is not `\w` in... actually, in Python 3, `\w` matches `’`? No — `’` is punctuation, not word. Actually, in Python 3, `re.match(r'\w', '’')` → None. So "don’t" → the `\w+n't` pattern requires literal `'` — "don’t" has `’` not `'` — so it does NOT match `\w+n't`. And the literal `don't` alternative also fails. So a curly-apostrophe "don’t" added by a snap is NOT guarded.** Concrete: the record's sentence 0 ends "...don’t" (curly), the anchored text starts at "stop" — the snap adds "don’t", which is a negation, and SNAP_GUARD misses it. The ledger's scores never saw the negation. This is exactly the class of bug the guard exists for. Whether the store's records use curly apostrophes depends on the whisper/normalization pipeline (unseen) — flag as P2, verify-then-fix: either normalize apostrophes in `added` before the guard, or add `’` to the strip set and the `n’t` alternative to the regex.

**N-4 (P2): `proof_ledger.py:239` — `json.load(open(p))` with no error handling; a missing/broken delivered pin raises an uncaught `FileNotFoundError`/`JSONDecodeError` with a traceback, not a counted, logged failure.** The consensus claims "a missing or broken pin file stops the run (fail closed)" — true, but it stops with a *traceback*, after `out_dir` was created and `package.log` opened (line 255), leaving a half-written proof directory. Fail-closed but not fail-*clean*. P2.

**N-5 (P2): `rows()`'s `timeout=300` — a `subprocess.TimeoutExpired` is not caught and converted to RuntimeError.** `ledger_build.py:73-74`: `subprocess.run(..., timeout=timeout)` raises `subprocess.TimeoutExpired` (a subclass of `SubprocessError`, not RuntimeError). The docstring at lines 65-67 promises "Raises RuntimeError when the adapter FAILS or REFUSES" — a timeout raises a *different* exception type, so a caller catching RuntimeError (as the docstring implies) misses it. In `proof_ledger.py:260` there's no catch at all, so it propagates as a traceback. Fail-closed, but the exception contract in the docstring is inaccurate. P2.

**N-6 (P2): `build_inputs`'s `report["word_records"][vid]` is set even when *no* row on that video produces a moment** (all rows fail to anchor or are malformed). The report then shows a word record "used" that produced nothing. Cosmetic; the `moments`/`videos` counts are computed from actual results (lines 182), so the summary is honest. P2, cosmetic.

Wait, actually — `report["videos"] = len(sources)` at line 182, and `sources[vid] = src` at line 181 is only reached when a moment is successfully built. So `videos` counts only videos with ≥1 moment. But `word_records[vid]` is set at line 159 regardless. So the report can show 3 word records and 1 video. Not a bug, but the report's `word_records` key means "records consulted", not "records used". Naming, not behavior. P2.

## 4. REVISED SCORES

| Subsystem | Cycle 1 | Cycle 2 | Why changed |
|---|---|---|---|
| `rows()` adapter isolation | 8/10 | 8.5/10 | Grok's P0 resolved by the docstring reframe + the empty-read test (lines 456-460); the failure/refusal raises are tested. Residual: N-5 (timeout exception type) and the subprocess-JSON-parse of `p.stdout` (line 77: `json.loads(p.stdout)` — a truncated/empty stdout with returncode 0 raises `JSONDecodeError`, not RuntimeError; same class of issue as N-5). |
| `word_source` | 7/10 | 7.5/N-1 | The sha/edited-after-sha tests (lines 389-404) and the punctuated-first test (lines 406-417) close GLM's and Qwen's P0s. But N-1 (why overwritten) means the report's reason can be wrong — the diff's own promise. |
| `reanchor` + SNAP_GUARD | 7/10 | 8/10 | The guard + tests (lines 348-364) genuinely answer the "can a snap change the meaning" question. Residual: N-3 (curly apostrophes) and the untested malformed-frees-span interaction (N-2). |
| `build_inputs` | 7.5/10 | 8/10 | Counted drops, malformed-rows-never-crash (lines 176-177, tested at 419-437), duplicate spans. Residual: Qwen's `rs[0]` channel-identity question, still unproven either way. |
| `proof_ledger.py` driver | 7/10 | 7/10 | The `--delivered` flag exists (line 249), but N-4 (uncaught pin-read errors, half-written proof dir) and the hard-coded defaults remain. The render-clock `now` (line 252) is correct per ruling 1. |
| Tests | 7.5/10 | 8/10 | The new tests are targeted and concrete (the "Nobody"/"2009" cases are exactly right). Missing: missing-sha/empty-segments, the why-accumulation behavior, curly-apostrophe guard, timeout/JSONDecodeError. |

## 5. FINAL PRIORITY LIST

**P0 CRITICAL** — none. Every Cycle 1 P0 is either resolved (Grok's, via the reframe + test) or refuted with a test (Qwen's, via the punctuated-first test). I can verify this from the diff.

**P1 HIGH**
1. **N-1** — `ledger_build.py:98,106`: `why` overwritten, not accumulated; the report's drop reason can be the *last* failure, not the cause. One-line fix (`why = why or "..."`), directly serves the diff's "every drop counted" promise. (Also folds in GLM's P0-2/P1-2, which the consensus only partially addressed.)
2. **Qwen P1-1** — `ledger_build.py:154`: `word_source(rs[0], ...)` — the whole video's rows are re-anchored against `rs[0]`'s channel identity. Confirm the ledger guarantees one channel per video; if not, the credits card shows the wrong channel (Law CREDITS). If confirmed, downgrade to P2/doc.

**P2 MEDIUM**
3. **N-3** — `ledger_build.py:39-41,134`: SNAP_GUARD misses curly-apostrophe negations ("don’t"); add `’` handling or normalize. Verify whether the store's records contain U+2019.
4. **N-5** — `ledger_build.py:73-77`: a `TimeoutExpired` or a `JSONDecodeError` on `p.stdout` escapes the documented "Raises RuntimeError" contract; wrap both in RuntimeError (fail-closed, but the *type* is part of the contract).
5. **N-4** — `proof_ledger.py:239`: `json.load(open(p))` uncaught; a missing/broken delivered pin leaves a half-written proof dir with a traceback. Wrap, log, exit non-zero.
6. **N-2** — `ledger_build.py:165-179`: a malformed row frees its span for a later duplicate; untested. Add a test or document.
7. **GLM P0-1 residual** — `ledger_build.py:97`: add a missing-`transcript_sha256` / empty-segments test to close the "does `segments_sha256([])` return None" question about unseen code.
8. **Qwen P1-2** — `ledger_build.py:44`: document why SEARCH_PAD_S=30 (caption-clock drift bound?).

##  Cycle 2 — what the combined analysis revealed that nobody caught in Cycle 1

**The report's `why` is the last failure, not the cause (N-1).** Three reviewers (GLM, and the consensus's "IMPLEMENTED: word_source returns why") treated the report's reason as *the* reason. Nobody noticed that the reason is overwritten on every loop iteration, so when the punctuated record fails its sha check and the verbatim record fails L-e, the report says "not sentence-ready (law L-e)" — the *secondary* cause — while the *primary* cause (the sha mismatch on the preferred record) is invisible. This is the mechanism *behind* GLM's P0-2/P1-2: the count exists, the reason is wrong. It's a one-line fix (`why = why or "..."` on lines 98 and 106) and it's the difference between "the report tells you why" (the diff's own promise, line 146: "each counted with why") and "the report tells you the last thing that happened."

## 6. THE SINGLE HIGHEST-LEVERAGE CHANGE

**Fix the `why`-overwriting in `word_source` (`ledger_build.py:98,106` → `why = why fallthrough`... i.e. `why = why or "..."`), because the entire design's accountability rests on the report's reasons being true, and right now the report can lie about *why* a video's rows were dropped.**

## 7. PRODUCTION READY?

**Yes with conditions.**

Conditions, precisely:
1. **`ledger_build.py:98,106`** — accumulate `why` (`why = why or "..."`), so the report's drop reason is the *first/primary* failure, not the last. Add a test: punctuated record fails sha + verbatim record not sentence-ready → report says "sha", not "L-e".
2. **`ledger_build.py:154`** — confirm (or assert) the ledger guarantees one channel per video; if it doesn't, use each row's own channel identity or document why `rs[0]`'s is authoritative. If confirmed, this condition drops to a doc note.
3. **`ledger_build.py:73-77`** — wrap `subprocess.run`'s `TimeoutExpired` and `json.loads(p.stdout)`'s `JSONDecodeError` in RuntimeError, matching the docstring's exception contract at lines 65-67.
4. **`proof_ledger.py:239`** — wrap the delivered-pin reads; on failure, log to `package.log` and exit non-zero, not a traceback.

Everything else (N-2, N-3, N-6, the SEARCH_PAD_S rationale, the missing-sha test) is P2 and can ship after, tracked.

---

**SHIP: yes with conditions**