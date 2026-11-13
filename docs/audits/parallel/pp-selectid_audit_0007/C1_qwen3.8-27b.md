# qwen3.8-27b (qwen/qwen3.8-27b) 67 s finish=stop usage in 21977 / out 2042 usd~0.097 (upper-bound price)

# Code Audit: pp-selectid-0007 (Speaker Attribution & Batch Build)

## Findings

### P1: `speaker_problems` validation is incomplete; a named speaker can reach a pin with a fabricated `line`
**File:** `pipeline/package_pin.py` (lines 49–62 in diff)

The `speaker_problems` function validates that a named speaker has a non-empty `line` and `basis` string, but it does **not** verify that the `line` actually exists in the source metadata or that the `basis` is a substring of the transcript. The `check()` function in `speakers.py` performs these verifications, but `to_pin` calls `speaker_problems` directly on the segment data without re-running `check()`.

**Failure Scenario:**
1. A model reply is out of contract or the `check()` function is bypassed (e.g., via a direct JSON injection into the package before `to_pin`).
2. The segment contains: `{"speaker": {"name": "Jeff Booth", "line": "FAKE LINE", "basis": "FAKE BASIS", "people": [], "measured": true}}`.
3. `speaker_problems` sees `name` is not "unknown", `line` is a non-empty string, `basis` is a non-empty string, `people` is a list, `measured` is a bool. It returns `[]` (no problems).
4. `to_pin` proceeds to seal the pin with a speaker name that has no textual evidence in the source or transcript.

**Mitigation in current flow:** In the normal flow, `attribute_package` calls `attribute` which calls `check()`, so the `line` and `basis` are verified before being stored in the segment. However, `to_pin` is a public API that can be called with arbitrary package data. The seal is only as strong as the data passed to it. If any code path constructs a package without going through `attribute_package`, a fake speaker can be sealed.

**Recommendation:** `speaker_problems` should either re-verify the `line` against the source metadata (if available) or the pin should be sealed with a hash of the source metadata so that a mismatch can be detected later. Alternatively, `to_pin` should require that the speaker record was produced by `speakers.attribute` (e.g., by checking a signature or a specific structure that only `check()` produces).

---

### P1: `check()` basis verification uses `_norm` which may allow false positives
**File:** `pipeline/speakers.py` (lines 159–161, 222)

The `_norm` function strips all non-alphanumeric characters (except apostrophes) and lowercases. The basis is checked with `nb in _norm(clip) or nb in _norm(around)`. This is a substring match on normalized text.

**Failure Scenario:**
1. The clip text is: "I wrote a book about deflation."
2. The model proposes a basis: "I wrote a book about deflation" (correct).
3. But also consider: clip text is "I wrote a book. About deflation, I said."
4. The model proposes a basis: "I wrote a book about deflation" (not a contiguous substring in the original, but after normalization, "i wrote a book about deflation" is a substring of "i wrote a book about deflation i said").
5. This is a false positive: the basis is not a verbatim quote from the transcript, but a re-ordered or re-combined phrase.

**Impact:** A speaker can be named based on a basis that is not actually a contiguous quote from the transcript. This violates the law that "the basis is verbatim in the clip or the transcript around it."

**Recommendation:** The basis should be checked as a contiguous substring of the *original* (unnormalized) text, or the normalization should be more conservative (e.g., only case-folding, not stripping punctuation).

---

### P2: `source_lines` may include description lines that are not actually naming people
**File:** `pipeline/speakers.py` (lines 174–185)

The `source_lines` function includes all non-link description lines. The `check()` function then checks if a person's `line` is a substring of one of these lines. However, a description line might mention a person's name in a context that does not name them as a participant (e.g., "This video is dedicated to the memory of John Doe").

**Failure Scenario:**
1. Description line: "In memory of John Doe, who passed away last year."
2. The model proposes a person: `{"name": "John Doe", "line": "In memory of John Doe, who passed away last year."}`.
3. `check()` sees that the line is in the source lines and the name is in the line. It accepts John Doe as a person.
4. John Doe is not a speaker or participant in the video, but is listed in `people` for tagging.

**Impact:** Incorrect people are tagged. This is a lower-severity issue because it does not affect the speaker name, but it affects the `people` list used for tagging.

**Recommendation:** The `check()` function should require that the person's name appears in a context that suggests they are a participant (e.g., "host", "guest", "with", "featuring"). This is difficult to do reliably with text matching, so it may be acceptable to leave as is, but the risk should be documented.

---

### P2: `proof_batch.py` `build` function does not verify that the delivered spans are actually from the same universe
**File:** `tests/package/proof_batch.py` (lines 338–367)

The `build` function takes `delivered` spans and passes them to `PK.build`. It does not verify that these spans are from the same universe (i.e., the same set of source videos) as the moments being built. If a delivered span is from a different universe, it may not be correctly excluded.

**Failure Scenario:**
1. The batch is built from universe A (videos X, Y, Z).
2. A delivered pin is from universe B (video W).
3. The delivered span for video W is passed to `PK.build`.
4. `PK.build` may not correctly exclude the span because video W is not in the universe A moments.

**Impact:** A moment from video W might be reused, violating L-p (no clip span already delivered is used again).

**Recommendation:** The `build` function should verify that all delivered spans are from videos in the current universe, or `PK.build` should handle spans from videos not in the universe gracefully (e.g., by ignoring them).

---

### P2: `test_speakers.py` does not test the case where the basis is a non-contiguous substring
**File:** `tests/package/test_speakers.py`

The tests do not cover the case where the basis is a re-ordered or re-combined phrase that is a substring of the normalized text but not a contiguous quote from the original text. This is the false positive scenario described in P1.

**Recommendation:** Add a test case where the basis is not a contiguous substring of the original text but is a substring of the normalized text.

---

## Verdict on Specific Questions

**(a) Can a WRONG speaker name reach a pin?**
Yes, if the package is constructed without going through `attribute_package` (see P1). In the normal flow, `check()` prevents most wrong names, but the basis verification can have false positives (see P1).

**(b) Is any failure silent or counted as a pass?**
No. A failed call results in `measured: false` and `name: "unknown"`. `speaker_problems` refuses a segment without a speaker record. A named speaker without a `line` or `basis` is refused.

**(c) Is the speaker record really inside the seal, and does `to_pin` refuse every malformed record?**
Yes, the speaker record is inside the seal (line 41 in `package_pin.py`). `to_pin` refuses a segment without a speaker record, or a named speaker without a `line` and `basis`. However, it does not verify that the `line` and `basis` are actually in the source/transcript (see P1).

**(d) Does the batch build keep delivered spans and the batch's kept spans out, on the render clock?**
Yes, the `build` function passes `delivered` spans to `PK.build`, which excludes them. The render clock is used for recency checks. However, there is a potential issue with delivered spans from different universes (see P2).

**(e) Do the tests fail on the defect each one names?**
The tests cover the main scenarios, but they do not cover the false positive basis scenario (see P2).

## SHIP: yes with conditions

**Conditions:**
1. Fix the basis verification in `check()` to require a contiguous substring of the original text (P1).
2. Add a test case for the non-contiguous basis false positive (P2).
3. Document the risk of incorrect people in the `people` list (P2).
4. Verify that `PK.build` correctly handles delivered spans from videos not in the current universe (P2).