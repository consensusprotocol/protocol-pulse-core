# glm-5.3-flash (z-ai/glm-5.3-flash) 77 s finish=stop usage in 13581 / out 2209 usd~0.074 (upper-bound price)

# Audit: pp-selectid-1545 — speakers.py ruling 69/70

## P0

None found. Every naming path I traced requires the turn structure plus a code-verified address or self-introduction; I could not construct a scenario where a name lands on less.

## P1

**P1-1 — `turn_of` backchannel merge can chain across multiple interjections and join genuinely different speakers.**
`pipeline/speakers.py:127-135` (diff lines). The while-loops merge *every* gap of ≤3 words, repeatedly, in both directions. Scenario: A speaks, B interjects "Yeah." (1 word), A continues, then B interjects "Right." (1 word), then B actually takes the floor with a 3-word question, then A resumes. All gaps are ≤3 words, so all are merged into one "turn of A" — but the 3-word B question is now inside A's turn, and the model may quote it as A's address/self-intro. `check_turn` verifies the quote is *in the turn* and *holds a name*, but nothing verifies the quoted words are on A's side of a marker (they can't be — the markers were consumed). The ruling says "at most BACKCHANNEL_WORDS words" for *an* interjection; chaining N interjections plus a 3-word floor-taking is a defensible but stronger reading. Concrete risk: a wrong name sealed in the pin — exactly the failure mode this review guards. Mitigation exists (conflict → "unknown"), but only when the basis rule independently disagrees. **Say so if you read the ruling as permitting chains; the test only exercises one interjection.**

**P1-2 — `decide()` address rule: `others` computed but the two-people constraint can pass with the addressed person not among `people`.**
`pipeline/speakers.py:174-177`. `others = [p for p in people if _norm(p["name"]) != _norm(turn_ev["address"]["name"])]`. If `check_turn` kept the address, the addressed person *is* in `people` (it's checked there), so this is safe — but only via that coupling. If `check_turn`'s `who` lookup and `decide`'s ever diverge (e.g. one uses `_within`, the other `_norm` equality — they do: `check_turn` matches the *model's* name string to a person by `_norm` equality, while the lower-third path at line 187 uses `_within` per word), the invariant "addressed ∈ people" is implicit, not enforced in `decide`. Currently consistent; flagging as fragile, not broken.

**P1-3 — `captions()` returns the first store with *any* marker, not the best copy.**
`pipeline/speakers.py:84-105`. If the main tree holds a truncated/partial `transcript.yt_auto.json` that happens to contain one stray `>>` (e.g. from a description leak into the caption text), it wins over pp-ingest's complete copy. The `if any(u[2] for u in units)` guard only checks ≥1 marker exists. No completeness check (e.g. last unit's time vs. video duration). For the 13:38 pin this is fine; for a live episode where the main tree's copy is a partial ingest, the turn could be silently truncated and `turn_of` returns "no speaker-change marker before the clip" — fail-closed, so it's a P1 not P0. But a *partial* copy that has the clip's turn but misses a later marker yields a too-long turn, which only risks prompt bloat (TURN_MAX_CHARS cuts it). Downgrade-able to P2 if you trust the store discipline.

## P2

**P2-1 — Marker-inside-clip tolerance uses the same `tol` for both edges asymmetrically.**
`pipeline/speakers.py:116`: `start + tol < units[i][0] < end - tol`. A marker at exactly `start + 0.5` (the caption's *display* start, not the word onset) is treated as outside the clip. Since caption timings are display times and the clip bounds are word timings, a 0.5 s tolerance is a guess. If a marker legitimately falls at 0.6 s inside the clip (the clip catches the tail of the previous speaker's "Yeah"), the whole turn evidence is refused — fail-closed, "unknown" where ruling 69 would name. Conservative, acceptable, but note it.

**P2-2 — `check_turn` name-word match: `len(w) > 1` drops single-letter name words.**
`pipeline/speakers.py:160`. A person recorded as "A. Smith" (line: "A. Smith joins...") — the token "a" (after `_norm` presumably lowercases) is 1 char and excluded. If the *only* name word in the quote is the initial, the evidence is dropped. Edge case; TWO-people test data uses full names. Also: the same filter at line 187 uses `len(w) > 2`, so a 2-letter name word ("Bo") works in `check_turn` but not in the lower-third match. Inconsistent thresholds, no stated reason.

**P2-3 — `decide()` lower-third agreement appends to `basis` but the earlier conflict path (line 182-183) returns before the lower-third is consulted.**
`pipeline/speakers.py:181-193`. When the basis rule and the turn rule disagree, the function returns early with "unknown" and the lower third — which might have adjudicated (ruling 70: "one more piece of evidence") — is never read. Reading ruling 70 as "one more piece of evidence" suggests it *could* break a tie. Your K4 says "confirm or veto, never make" — under K4 the early return is correct. Stating my reading: I'd have expected the lower third to adjudicate a two-way disagreement, but K4 as stated supports the code. Not a defect under the stated reading; flagging the reading-dependence.

**P2-4 — `attribute()`'s `rec["turn"]` dict-splat ordering.**
`pipeline/speakers.py:230-233`: `**({"source": cap_src, ...} if turn else {})` — when `turn` is None, `cap_src` may still be a non-None... no, checked: `caps if caps else (None, None)` — if `caps` is `(None, None)` (falsy? no — a 2-tuple of Nones is *truthy*). **Correction: `caps if caps else (None, None)` — when the caller passes `caps=(None, None)` (as `captions()` returns on failure), the tuple is truthy, so `units, cap_src = (None, None)`, then `turn_of` is skipped via `if units`, and `rec["turn"] = {"read": False, "why": ...}` — correct.** But when `caps` is `None` (the default, test path line 370), same. Withdrawn — no defect, noting the truthiness of `(None, None)` is relied upon implicitly.

**P2-5 — Test coverage: no test for a bare `>>` (pending flag) producing a turn, no test for `>>` inside a line mid-text, no test for the TURN_MAX_CHARS cut.**
`tests/package/test_speakers.py:268-373`. The `pending` logic (`pipeline/speakers.py:100`: `pending = opens and not part`) and the 12 000-char cut (lines 138-142) are untested. The cut's `mid` computation (`next((n for n, k in enumerate(idx) if units[k][0] >= start - tol), 0)`) — if no unit starts at/after `start - tol` (clip before the first unit's time, possible with timing skew), `mid=0`, `lo=0`, and the cut keeps the *head* of the turn, potentially dropping the clip's words from the prompt. Concrete: clip at 690.0, first unit at 694.40, turn >12 000 chars → the clip's own words may be cut out of THE CLIP'S TURN. The model then can't quote the address; fail-closed to "unknown" but ruling 69 silently defeated. This is the strongest P2.

**P2-6 — `turn_of`'s `end` of the turn is the *start* of the last unit, not its end.**
`pipeline/speakers.py:143`: `"end": units[idx[-1]][0]`. The recorded turn end (945.28 in the test) is the last unit's *start* time. Cosmetic/telemetry only — nothing gates on it — but the recorded evidence's "end" understates by the last line's duration. If ruling 70's later work or an audit reads this as the turn's true end, it's misleading.

## Ruling-compliance summary

- Naming paths: self-intro → its speaker; address → other-of-exactly-two; both require code-verified quote (≥3 words, verbatim in turn, holds a name word, person ∈ people). ✔
- Backchannel: ≤3 words, both directions, recorded. ✔ (chain concern = P1-1)
- Lower third: never alone, veto→unknown, agree→basis. ✔ (matches K4)
- Fail-closed: no markers, marker inside clip, no prior marker, failed call → "unknown"/measured-false. ✔ (M12)
- One verdict, one call, retry-once-with-new-seed preserved. ✔

## SHIP: yes with conditions

1. Add the TURN_MAX_CHARS cut test (P2-5) — the clip-words-dropped scenario is silent and defeats ruling 69 on long turns.
2. Confirm the chain-merge reading (P1-1) with the orchestrator, or cap the merge at one interjection per side.
3. Align the name-word length thresholds (`>1` vs `>2`) or comment why they differ (P2-2).