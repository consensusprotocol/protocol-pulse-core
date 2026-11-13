# qwen3.8-27b (qwen/qwen3.8-27b) 71 s finish=stop usage in 13298 / out 2466 usd~0.077 (upper-bound price)

# Code Audit: pp-selectid-2315 (C1_STEP.diff)

## P0 Findings

### P0-1: `word_source` returns the first *any* matching record, not necessarily the punctuated one
**File:** `pipeline/ledger_build.py:81-96`

The glob sorts with `key=lambda p: "punct" not in p`, which places files *without* "punct" in the name first (False=0 < True=1). The loop then returns the **first** record that passes the SHA check and `E.sentence_ready()`. If a non-punctuated `transcript.whisper_words.json` exists alongside `transcript.whisper_words_punct.json` and both have valid SHAs, the non-punctuated record is returned first.

**Failure scenario:** A video has both `transcript.whisper_words.json` (verbatim, unpunctuated) and `transcript.whisper_words_punct.json`. The verbatim record's segments SHA is valid. `E.sentence_ready()` may pass if the verbatim record happens to have sentence boundaries from a prior pass. The builder uses the verbatim record, violating **Law L-e** ("Every word transcript the sentence law reads… has its sentence punctuation restored from a prompted second decode… before any sentence is read"). The docstring explicitly states "punctuated first" but the sort order is inverted.

**Fix:** `key=lambda p: "punct" in p` (True=1 sorts first) or explicitly prefer the punct file.

---

### P0-2: `reanchor` does not verify the snapped span is sentence-ready
**File:** `pipeline/ledger_build.py:100-119`

`reanchor` snaps the anchored word range to `src.sentences[k0]` and `src.sentences[k1]`, then constructs `E.Span(src, k0, k1)`. It never calls `E.sentence_ready()` on the resulting span. The `word_source` function checks `E.sentence_ready(src)` on the *Source*, but the Source-level check may not guarantee that the specific sentence range `[k0, k1]` is sentence-ready (e.g., if the record has a mix of punctuated and unpunctuated stretches, or if `sentence_ready` is a per-record flag that doesn't validate every sentence boundary).

**Failure scenario:** A word record is marked sentence-ready at the record level, but sentence `k1` ends without terminal punctuation (an unpunctuated stretch at the tail). The snap extends to include that sentence. The clip's last word is not the last word of a sentence, violating the **SENTENCE LAW**. The gate would catch it at render time, but the builder should fail closed at selection time.

**Note:** If `E.sentence_ready(src)` is a per-record boolean that guarantees *all* sentences are punctuated, this is not a bug. I cannot verify this from the diff alone. Flagging as P0 pending confirmation.

---

## P1 Findings

### P1-1: `build_inputs` uses `rs[0]` for `word_source` but iterates all rows for re-anchoring
**File:** `pipeline/ledger_build.py:132-133`

```python
for vid, rs in by_vid.items():
    src, path = word_source(rs[0], ctx, store)
```

`word_source` is called with `rs[0]` (the first row for that video). If `rs[0]` has a `channel_id` that differs from other rows in `rs` (e.g., a re-upload or a multi-channel video), the `Source` is constructed with `rs[0]`'s channel identity. The other rows in `rs` are re-anchored against this Source, but their own `channel_id` is not used.

**Failure scenario:** A video has two ledger rows: one from channel "DataDash" and one from "Coin Bureau" (e.g., a compilation video). `rs[0]` is the DataDash row. The Source is built with DataDash's identity. The Coin Bureau row is re-anchored and recorded with DataDash's channel in the Source, but the moment's `mined.ledger_moment_id` preserves the original row. The credits card (Law CREDITS) would show DataDash for a clip that is actually Coin Bureau's statement.

**Mitigation:** This may be impossible if the ledger guarantees one channel per video. Flagging as P1 pending confirmation.

---

### P1-2: `SEARCH_PAD_S = 30.0` may be insufficient for long captions
**File:** `pipeline/ledger_build.py:39, 104-106`

The anchor search window is `[t0 - 30, t1 + 30]`. If a ledger row's caption times are significantly off (e.g., the caption clock is 40 seconds ahead of the word record's clock due to a different timebase), the anchor will fail and the row is dropped.

**Failure scenario:** A video's caption track has a 35-second offset from the audio. The row's `start` is 100s, `end` is 110s. The search window is [70, 140]. The actual words in the word record are at 135-145s. The anchor fails. The row is dropped with "does not anchor." This is fail-closed (correct behavior), but it may silently drop valid moments if the offset exceeds 30s. The report counts these as `not_anchored`, so they are not *silently* dropped, but the 30s pad is a magic number with no documented rationale.

**Severity:** P1 because it is fail-closed and counted, but the pad may be too small for real-world caption drift.

---

### P1-3: `proof_ledger.py` hardcodes `DELIVERED_PINS` paths
**File:** `tests/package/proof_ledger.py:204-205`

```python
DELIVERED_PINS = (os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN.json"),
                  os.path.join(HERE, "proof", "fresh_20261112_050611", "MOMENTS_PIN_LY.json"))
```

These are hardcoded to a specific run's output directory. If the pins are moved, renamed, or if a new pin is delivered, this list is stale. The `delivered_spans()` function will either fail (file not found) or miss the new pin, allowing duplicate clips.

**Failure scenario:** A new pin is delivered on 2026-11-13. `proof_ledger.py` is run again. The new pin's spans are not in `DELIVERED_PINS`, so `package.usable` does not see them as delivered. A moment that overlaps the new pin's clips is included in the new package, violating the novelty requirement (L-p).

**Fix:** Discover delivered pins dynamically (e.g., glob `proof/*/MOMENTS_PIN*.json`) or read from a manifest.

---

### P1-4: `rows()` subprocess timeout is 300s with no retry
**File:** `pipeline/ledger_build.py:57, 67-68`

The subprocess has a 300-second timeout. If the ledger adapter is slow (large ledger, slow disk), it may time out. The `RuntimeError` is raised, which is fail-closed, but there is no retry or backoff. In a production pipeline, a transient I/O stall would abort the entire build.

**Severity:** P1 because it is fail-closed, but the lack of retry may cause unnecessary build failures.

---

## P2 Findings

### P2-1: `word_source` opens files without `with` statement
**File:** `pipeline/ledger_build.py:86`

```python
rec = json.load(open(p))
```

The file handle is not explicitly closed. In CPython, the reference count drops to zero and the file is closed, but this is an implementation detail. In a long-running process with many videos, this could exhaust file descriptors.

**Fix:** Use `with open(p) as f: rec = json.load(f)`.

---

### P2-2: `build_inputs` does not validate that `row["scores"]` is present
**File:** `pipeline/ledger_build.py:147`

```python
m = {"scores": r["scores"], ...}
```

If a ledger row is missing the `scores` key, this raises a `KeyError`. The adapter is expected to always include `scores`, but there is no defensive check. A malformed row would crash the entire build.

**Fix:** Use `r.get("scores", {})` or validate the row schema before processing.

---

### P2-3: `proof_ledger.py` uses `logf = open(..., "a")` without `with`
**File:** `tests/package/proof_ledger.py:226`

The log file is opened in append mode and closed at the end of `main()`. If an exception occurs before `logf.close()`, the file handle leaks. The `say` lambda writes to the file, but if `json.dump` or `PK.build` raises, the log is not flushed/closed.

**Fix:** Use a `with` statement or a `finally` block.

---

### P2-4: `reanchor` does not handle the case where `i0 == i1` (single-word anchor)
**File:** `pipeline/ledger_build.py:109-111`

If the anchored text is a single word, `i0 == i1`. The code finds `k0` and `k1` (which are the same sentence). The snap logic works, but the resulting span is a single word, which is not a whole sentence. The `SNAP_WORDS` check would pass (0 words outside), but the span is not a valid clip.

**Failure scenario:** A ledger row's text is a single word that appears in the word record. The anchor succeeds, the snap produces a single-word span, and the moment is recorded. The clip is not a whole sentence, violating the **SENTENCE LAW**.

**Fix:** Reject spans where `k0 == k1` and the span is not the entire sentence, or require a minimum span length.

---

## Verdict

**SHIP: no**

**Blocking issues:**
1. **P0-1** (inverted sort order) must be fixed: the builder may use a non-punctuated record, violating Law L-e.
2. **P0-2** (no per-span sentence-ready check) must be confirmed or fixed: the builder may produce a clip that is not a whole sentence, violating the SENTENCE LAW.

**Recommended before ship:**
- Fix P1-1 (channel identity) if multi-channel videos are possible.
- Fix P1-3 (hardcoded pins) to prevent duplicate clips in future runs.
- Fix P2-4 (single-word span) to prevent non-sentence clips.