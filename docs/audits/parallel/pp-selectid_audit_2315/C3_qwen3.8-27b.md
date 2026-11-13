# qwen3.8-27b (qwen/qwen3.8-27b) 57 s finish=stop usage in 19399 / out 3845 usd~0.116 (upper-bound price)

I’ll verify the claims strictly against the provided diff. I will not assume the behavior of `sentence_law.anchor`, `eligibility.Source`, `moments.judge/record`, `package.build`, or the ingest adapter beyond what the diff shows.

## Findings

### P0 — None found in the provided diff
I could not construct a concrete failure from the diff alone where a non-whole-sentence clip, a non-word-timed moment, an unverified record, or a delivered span is accepted. The code paths that would allow those are not visible in the diff (e.g., `SL.anchor`, `E.sentence_ready`, `M.judge`, `PK.build`), so I cannot verify a P0 from the provided text.

### P1 — `since` default may read too few lines (c)

**File:** `tests/package/proof_ledger.py:304`  
**Code:**
```python
since = datetime.fromisoformat(a.since.replace("Z", "+00:00")) if a.since else last
```
where `last` is the newest delivered pin’s `approved_at`.

**Ruling 2 wording:** “best_unused_moments since the last delivered video.”

**Problem:** The adapter contract says it returns “lines mined at or after `since` **or** published inside the 72 h window.” If a ledger row was mined *before* the last delivered pin’s `approved_at` but published within the 72 h window, it is included. But if a row was mined *before* `approved_at` and published *outside* the 72 h window, it is excluded. The question is whether “since the last delivered video” means “since the last delivered video was *approved*” or “since the last delivered video was *rendered/published*.” The diff uses `approved_at`, which is the pin’s approval time, not necessarily the video’s publish time. If a video was published at 10:00 and approved at 14:00, rows mined between 10:00 and 14:00 are excluded by the `since` default, even though they postdate the video’s publication. This could read too few lines.

**Concrete failure scenario:**
- Last delivered pin: published 2026-11-12T10:00:00Z, approved 2026-11-12T14:00:00Z.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-12T11:00:00Z.
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` and published outside the 72 h window (if `now` is 2026-11-12T15:00:00Z, the 72 h window starts 2026-11-09T15:00:00Z, so the row *is* inside the window). Wait — the row *is* inside the 72 h window, so it is included. Let me re-examine.

Actually, the adapter returns rows mined at or after `since` **OR** published inside the 72 h window. So a row mined before `since` but published inside the 72 h window is included. The only rows excluded are those mined before `since` AND published outside the 72 h window. If the 72 h window is wide enough, this is unlikely to be a problem. But if a row was published 73 h ago and mined before `since`, it is excluded. Is that correct? Ruling 2 says “since the last delivered video,” which is ambiguous. The diff’s choice is defensible but not clearly correct. I’ll downgrade this to P2.

### P2 — `since` default is ambiguous (c)

**File:** `tests/package/proof_ledger.py:304`

**Issue:** The default `since` is the newest delivered pin’s `approved_at`. Ruling 2 says “since the last delivered video.” It is unclear whether “last delivered video” means the video’s publish time, render time, or approval time. The diff uses `approved_at`, which is the pin’s approval time. If the intent was the video’s publish time, this could read too few or too many lines. The diff does not document this choice.

**Concrete failure scenario:**
- Last delivered pin: published 2026-11-12T10:00:00Z, approved 2026-11-12T14:00:00Z.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-12T11:00:00Z.
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` but published inside the 72 h window, so it is included. No failure.
- Ledger row: mined 2026-11-12T12:00:00Z, published 2026-11-10T12:00:00Z (72 h ago).
- `since` default = 2026-11-12T14:00:00Z.
- Row is mined before `since` and published at the edge of the 72 h window. If the adapter’s window is inclusive, it is included; if exclusive, it is excluded. The diff does not specify.

This is a minor ambiguity, not a clear defect.

### P2 — `SNAP_GUARD` may not catch all negations (d)

**File:** `pipeline/ledger_build.py:39-41`
```python
SNAP_GUARD = __import__("re").compile(r"^(not|no|never|none|nobody|nothing|neither|nor|cannot|can't|won't|don't|"
                                      r"doesn't|didn't|isn't|aren't|wasn't|weren't|shouldn't|wouldn't|couldn't|"
                                      r"\w+n't)$|\d", __import__("re").I)
```

**Issue:** The guard catches a fixed list of negations and any word with a digit. It does not catch negations like “hardly,” “scarcely,” “barely,” “rarely,” “seldom,” “infrequently,” “un-” prefixes, or “non-” prefixes. If a snap adds one of these, it could flip or add a claim the ledger never judged.

**Concrete failure scenario:**
- Word record sentence: “Hardly anyone can stop Bitcoin from settling a payment.”
- Ledger row text: “anyone can stop Bitcoin from settling a payment.”
- Snap adds “Hardly” at the left edge.
- `SNAP_GUARD` does not match “Hardly” (it is not in the list and has no digit).
- The snap is allowed, but the claim is flipped from “anyone can stop” to “hardly anyone can stop.”

This is a real gap, but the diff’s comment says “a word the snap would ADD may not be a negation or carry a digit,” and the guard is a heuristic. The diff does not claim to catch all negations, only the common ones. I’ll note it as a P2.

### P2 — `word_source` may read a record with a mismatched `transcript_method` (a)

**File:** `pipeline/ledger_build.py:117-124`
```python
if rec.get("transcript_sha256") != ts.segments_sha256(rec.get("segments") or []):
    passed_over.append(f"{name}: its segments do not match its transcript_sha256")
    continue
timing, toks = S.tokens_from_record(rec)
src = E.Source(vid, row.get("channel_id"), reg.get("display_name") or row.get("channel_name"),
               row.get("published_at"), rec.get("transcript_sha256"), rec.get("transcript_method"), toks,
               timing=timing, title=row.get("title") or "", file_head=True, vod=True)
if E.sentence_ready(src):
    return src, p, passed_over
```

**Issue:** The code checks the SHA and `sentence_ready`, but it does not verify that the `transcript_method` is one of the expected methods (e.g., `whisper_words_punct` or `whisper_words`). If a record has a different method (e.g., `whisper_segments`), it may still pass `sentence_ready` if the method is not checked. The diff does not show `E.sentence_ready`’s implementation, so I cannot verify this.

**Concrete failure scenario:**
- Record: `transcript_method = "whisper_segments"`, SHA matches, `sentence_ready` returns True.
- The record is used, but it is not a word-timed record.
- A moment is created from a non-word-timed record, violating L-e.

This is a potential issue, but it depends on `E.sentence_ready`’s implementation, which is not in the diff. I’ll note it as a P2 with uncertainty.

### P2 — `reanchor` may allow a snap that adds a word with a digit in the middle (d)

**File:** `pipeline/ledger_build.py:154-159`
```python
added = ["".join(APOSTROPHES.get(c, c) for c in t["word"]).strip(".,!?;:\"'()\u201c\u201d\u2014\u2026")
         for t in list(src.tokens[src.sentences[k0][0]:i0]) + list(src.tokens[i1 + 1:src.sentences[k1][1] + 1])]
risky = [w for w in added if SNAP_GUARD.search(w)]
```

**Issue:** `SNAP_GUARD` uses `search`, not `match`. The regex is `^(...)$|\d`, so it matches if the word is a negation OR contains a digit. But `search` will find a digit anywhere in the word, including in the middle. This is correct for catching digits, but it may also catch words like “2009” (which is intended) and “1st” (which may not be intended). The diff does not specify whether “1st” should be caught.

**Concrete failure scenario:**
- Word record sentence: “In 2009 Bitcoin started as a quiet experiment.”
- Ledger row text: “Bitcoin started as a quiet experiment.”
- Snap adds “In 2009” at the left edge.
- `SNAP_GUARD` matches “2009” (digit), so the snap is refused. Correct.
- Word record sentence: “The 1st Bitcoin block was mined in 2009.”
- Ledger row text: “Bitcoin block was mined in 2009.”
- Snap adds “The 1st” at the left edge.
- `SNAP_GUARD` matches “1st” (digit), so the snap is refused. This may be too strict, but it is fail-closed.

This is not a defect, but a note.

### P2 — `build_inputs` may not handle a row with a missing `moment_id` (b)

**File:** `pipeline/ledger_build.py:192-206`
```python
if sp is None:
    report["not_anchored"][r["moment_id"]] = info
    continue
...
except (KeyError, TypeError, ValueError) as e:     # counted, never a crash (glm C1 P1-8)
    report["malformed"][r.get("moment_id")] = f"{type(e).__name__}: {str(e)[:120]}"
    continue
```

**Issue:** If a row has a missing `moment_id`, `r["moment_id"]` raises `KeyError`, which is caught and recorded in `report["malformed"]` with `r.get("moment_id")` (which is `None`). This is fail-closed, but the key `None` may collide with other rows that also have a missing `moment_id`. The diff does not specify how to handle this.

**Concrete failure scenario:**
- Two rows with missing `moment_id`.
- Both are recorded in `report["malformed"]` with key `None`.
- The second overwrites the first, so only one is counted.

This is a minor issue, but it could lead to undercounting.

### P2 — `proof_ledger.py` may not handle a pin with a missing `story_id` (d)

**File:** `tests/package/proof_ledger.py:284-288`
```python
spans += [{"video_id": str(s["video_id"]), "start": float(s["start"]), "end": float(s["end"]),
           "pin": pin["story_id"]} for s in segs]
newest = at if newest is None or at > newest else newest
pins.append({"path": os.path.relpath(os.path.abspath(p), REPO), "story_id": pin["story_id"],
             "approved_at": at.isoformat(), "clips": len(segs)})
```

**Issue:** If a pin has a missing `story_id`, `pin["story_id"]` raises `KeyError`, which is caught in `main` and the run is refused. This is fail-closed, but the error message may not be clear.

**Concrete failure scenario:**
- Pin: `{"approved_at": "2026-11-13T03:01:09+00:00", "segments": [{"video_id": "vidA", "start": 0, "end": 10}]}`.
- `pin["story_id"]` raises `KeyError`.
- The run is refused with “REFUSED: the delivered pins or 'since' cannot be read (KeyError: 'story_id')”.

This is acceptable, but the error message could be clearer.

### P2 — `test_ledger_build.py` may not test a row with a missing `scores` (e)

**File:** `tests/package/test_ledger_build.py:540`
```python
{k: v for k, v in row(SENTS[3], mid="L5").items() if k != "scores"}   # malformed: counted
```

**Issue:** The test removes `scores` from a row and expects it to be counted as malformed. But `build_inputs` does `dict(r["scores"])`, which raises `KeyError` if `scores` is missing. This is caught and recorded in `report["malformed"]`. The test verifies this. However, the test does not verify that the row is not used in the moments. It only checks `rep["malformed"]`.

**Concrete failure scenario:**
- Row with missing `scores`.
- `build_inputs` records it in `report["malformed"]` and does not add it to `moments`.
- The test checks `rep["malformed"]` but not `moments`.

This is a minor gap in the test, but the code is correct.

### P2 — `test_ledger_build.py` may not test a row with a missing `video_id` (e)

**File:** `tests/package/test_ledger_build.py`

**Issue:** The tests do not include a row with a missing `video_id`. If a row has a missing `video_id`, `by_vid.setdefault(r["video_id"], []).append(r)` raises `KeyError`, which is not caught in `build_inputs`. This would crash the build.

**Concrete failure scenario:**
- Row: `{"moment_id": "L1", "text": "Bitcoin is a global free market."}` (missing `video_id`).
- `build_inputs` raises `KeyError: 'video_id'`.
- The build crashes.

This is a real gap. The diff does not show a test for this, and the code does not handle it.

## Verdict

**SHIP: no**

**Reasons:**
1. **P2:** `build_inputs` does not handle a row with a missing `video_id`, which would crash the build. This is a fail-open defect.
2. **P2:** `SNAP_GUARD` may not catch all negations (e.g., “hardly,” “scarcely,” “barely”), which could allow a snap that flips a claim.
3. **P2:** `word_source` may read a record with a mismatched `transcript_method` if `E.sentence_ready` does not check it. This is uncertain but a potential L-e violation.
4. **P2:** `since` default is ambiguous (approved_at vs. publish time), which could read too few or too many lines.

The first issue is the most serious: a missing `video_id` would crash the build, which is fail-open. The other issues are less severe but still worth addressing.