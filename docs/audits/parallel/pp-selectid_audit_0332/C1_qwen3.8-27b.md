# qwen3.8-27b (qwen/qwen3.8-27b) 89 s finish=stop usage in 18936 / out 3019 usd~0.102 (upper-bound price)

# Audit: pp-selectid-0332 (Ruling 32 — Snap Outward)

## P0 Findings
None. The core logic correctly implements Ruling 32: it snaps outward to whole sentences, enforces the 20s limit, checks for speaker markers, and records added words. It does not violate the "fail closed" or "verbatim whole sentences" laws.

## P1 Findings

**1. `pipeline/ledger_build.py` (approx. line 115 in diff): `marker_inside` uses `startswith` on a tuple of strings.**
*   **Scenario:** The code `str(t.get("word") or "").lstrip().startswith(SPEAKER_MARKERS)` relies on `str.startswith` accepting a tuple. While valid in Python, it is brittle if `SPEAKER_MARKERS` is ever modified to include non-string elements or if the logic is refactored. More importantly, `lstrip()` removes *all* leading whitespace, but `startswith` checks the beginning. If a token is `"  >>"`, `lstrip` makes it `">>"`, which matches. This is correct. However, if a token is `">> something"`, it matches. This is likely intended.
    *   *Correction:* This is actually fine. `str.startswith(tuple)` is standard. No P1 here.

**2. `pipeline/ledger_build.py` (approx. line 110-114 in diff): Edge time measurement for `SNAP_MAX_S`.**
*   **Scenario:** The code calculates `a` and `b` as:
    ```python
    a, b = num(src.tokens[s0].get("start")), num(src.tokens[s1].get("end"))
    ```
    It checks `if a is None or b is None: return None, ...`.
    It then checks `if b - a > SNAP_MAX_S`.
    *   **Risk:** `s0` is the start index of the *first* sentence in the snapped span, and `s1` is the end index of the *last* sentence. `src.tokens[s0]` is the first word of the first sentence. `src.tokens[s1]` is the last word of the last sentence.
    *   **Verification:** This correctly measures the duration of the *entire* snapped span (from the start of the first added/kept word to the end of the last added/kept word). This aligns with "the snapped span runs more than 20 s".
    *   **Potential Issue:** Does `SNAP_MAX_S` (20.0) match `package.SEG_MAX_S`? The comment says `= package.SEG_MAX_S`. If `package.SEG_MAX_S` is defined as 20.0, this is consistent. If it changes, this constant is hardcoded. This is a minor maintainability issue, not a logic bug, unless the law requires dynamic lookup. The prompt says "at most 20 s per clip (L-u, package.SEG_MAX_S)". Hardcoding 20.0 is acceptable if it matches the constant, but referencing the constant would be safer. I will flag this as P2.

**3. `pipeline/ledger_build.py` (approx. line 115 in diff): `marker_inside` logic.**
*   **Scenario:** `marker_inside` checks if a marker is *strictly* inside `[a, b]` with a margin of `MARKER_EDGE_S` (1.0s).
    ```python
    if isinstance(s, (int, float)) and a + MARKER_EDGE_S < float(s) < b - MARKER_EDGE_S:
    ```
    *   **Risk:** If a speaker change happens *exactly* at the boundary of the snapped span (e.g., the last word of the previous sentence is spoken by Speaker A, and the first word of the snapped span is Speaker B), the marker might be at time `a` (start of snapped span). The condition `a + 1.0 < s` would be false if `s == a`. Thus, it would *not* reject the snap.
    *   **Law Check:** The prompt says: "A marker within 1.0 s of an edge... is not a measurement at this stage; L-v 2 decides on the audio."
    *   **Conclusion:** This behavior is **correct** per the prompt's description. The code intentionally ignores markers near the edges, deferring to L-v 2.

**4. `pipeline/ledger_build.py` (approx. line 118 in diff): `info["added"]` calculation.**
    ```python
    info["added"] = {"before": E.spoken(src.tokens[s0:i0]), "after": E.spoken(src.tokens[i1 + 1:s1 + 1])}
    ```
    *   **Scenario:** `i0` and `i1` are the indices of the first and last words of the *anchored* text (the row's text). `s0` and `s1` are the indices of the first and last words of the *snapped* span (whole sentences).
    *   **Verification:**
        *   `before`: Words from `s0` to `i0-1`. These are the words added *before* the anchored text. Correct.
        *   `after`: Words from `i1+1` to `s1`. These are the words added *after* the anchored text. Correct.
    *   **Edge Case:** If `i0 == s0`, `src.tokens[s0:i0]` is empty. `E.spoken([])` should return `""`. The test `test_a_caption_text_snaps_outward...` asserts `info["added"] == {"before": "Bitcoin", "after": ""}`. This implies `E.spoken` handles empty lists correctly.

**5. `pipeline/ledger_build.py` (approx. line 128 in diff): `snap_risk` usage.**
    ```python
    "risk": snap_risk(sp.text, info, r.get("risk")),
    ```
    *   **Scenario:** `sp.text` is the text of the *snapped* span (whole sentences). `info` contains `snapped_words`. `r.get("risk")` is the original risk from the ledger row.
    *   **Logic:** `snap_risk` adds `"price_prediction"` if `info["snapped_words"]` is non-empty AND `sp.text` contains a future price mention.
    *   **Risk:** Does `sp.text` include the added words? Yes, `sp` is `E.Span(src, k0, k1)`, which covers the whole sentences. `sp.text` is derived from `src.tokens[sp.w0:sp.w1+1]`. So `sp.text` includes the added words.
    *   **Conclusion:** Correct. The risk is calculated on the full snapped text.

**6. `pipeline/ledger_build.py` (approx. line 142 in diff): `caption_source` lookup.**
    ```python
    caps_v[sha] = caption_source(r, ctx, store, ledger_store)[0]
    ```
    *   **Scenario:** This is called for every row `r` in `irs` (input rows). It caches by `sha` (transcript_sha256).
    *   **Risk:** `caption_source` might be expensive. Caching is good. However, `caption_source` returns a tuple, and `[0]` is taken. The docstring for `reanchor` says `cap` is "the caption record the row was mined from".
    *   **Verification:** The prompt says "the full-video path now looks up the row's caption record... and passes it to reanchor". This matches.

## P2 Findings

**1. `pipeline/ledger_build.py` (line 40 in diff): Hardcoded `SNAP_MAX_S = 20.0`.**
*   **Issue:** The constant is hardcoded. The prompt mentions `package.SEG_MAX_S`. If `package.SEG_MAX_S` is the source of truth, this should be imported or referenced to avoid drift.
*   **Recommendation:** Import `SEG_MAX_S` from `package` or define it in a shared config module.

**2. `tests/package/funnel.py` (line 168 in diff): Hardcoded paths.**
*   **Issue:** `LEDGER = "/home/ultron/worktrees/pp-ingest/data/editorial/moments/moment_ledger.jsonl"` and `LV2 = "/tmp/claude-1000/..."` are hardcoded.
*   **Recommendation:** These should be configurable via environment variables or command-line arguments to make the tool portable and testable in CI.

**3. `tests/package/funnel_pre_edge.py` (line 414 in diff): Hardcoded `LV2` path.**
*   **Issue:** Same as above.

**4. `pipeline/ledger_build.py` (line 48 in diff): `SPEAKER_MARKERS` tuple.**
*   **Issue:** `SPEAKER_MARKERS = (">>", "&gt;&gt;")`. The code uses `startswith(SPEAKER_MARKERS)`. This works, but it's slightly obscure. A list comprehension or explicit check might be clearer, but this is a style nit.

## Verification of Specific Checks

1.  **Removing SNAP_GUARD:**
    *   The prompt asks: "whether removing SNAP_GUARD leaves any risk that NO downstream gate judges, for words the ledger never saw".
    *   **Analysis:** The added words are now part of the moment's text (`sp.text`).
        *   `package.usable()` checks the text for time-sensitive words.
        *   `step A (L-s)` judges the moment's view, referents, etc., on the full text.
        *   `exclusion_verdict` screens the MOMENT TEXT for hard risks.
        *   `L-v 2` verifies numbers and negations against an independent recogniser.
    *   **Conclusion:** All downstream gates operate on the *snapped* text, which includes the added words. Therefore, the added words *are* judged. The risk is mitigated.

2.  **Edge times `a` and `b` and marker window:**
    *   `a` is the start of the first word in the snapped span. `b` is the end of the last word.
    *   `marker_inside` checks for markers strictly inside `[a + 1.0, b - 1.0]`.
    *   This matches the prompt's description: "A marker within 1.0 s of an edge... is not a measurement at this stage".

3.  **Row whose text does not anchor:**
    *   `reanchor` returns `(None, why)` if `k0 is None or k1 is None` (anchored words fall outside sentences) or if the text doesn't match.
    *   The prompt says: "Rows where the text does not anchor at all stay out."
    *   **Conclusion:** Correct.

4.  **Snapped moment's text, start, end, and words:**
    *   `sp = E.Span(src, k0, k1)`.
    *   `sp.text` is derived from `src.tokens`.
    *   The start/end times are derived from `src.tokens`.
    *   **Conclusion:** Correct. The moment is based on the word record.

5.  **Dedup and window path unchanged:**
    *   The diff shows changes to `reanchor` and `build_inputs`.
    *   `build_inputs` now passes `cap` to `reanchor`.
    *   The dedup logic (not shown in diff) is presumably unchanged.
    *   The window path (not shown in diff) is presumably unchanged, except that it now also benefits from the new `reanchor` logic if it calls it. The prompt says "The window path already attached it [the caption record]". This implies the window path was already passing `cap` or had access to it. The diff shows `build_inputs` (full-video path) now fetching it.
    *   **Conclusion:** Likely correct, but I cannot verify the window path code as it's not in the diff.

6.  **`snap_risk` cannot remove a flag:**
    *   `snap_risk` does `out = list(risk or [])` and then `out.append("price_prediction")`.
    *   It never removes any existing flags.
    *   **Conclusion:** Correct.

## SHIP: Yes with conditions

**Conditions:**
1.  **Refactor `SNAP_MAX_S`:** Replace the hardcoded `20.0` with a reference to `package.SEG_MAX_S` or a shared constant to ensure consistency with the 20s clip limit law.
2.  **Parameterize Test Paths:** Update `tests/package/funnel.py` and `tests/package/funnel_pre_edge.py` to accept the ledger path and LV2 path as arguments or environment variables, rather than hardcoding them. This is critical for CI/CD and portability.
3.  **Verify `E.spoken` Behavior:** Ensure `E.spoken([])` returns an empty string `""` as expected by the tests. If it returns `None` or raises an error, the `info["added"]` logic will break. (The tests assert `""`, so this is likely fine, but worth a quick check).
4.  **Confirm `caption_source` Return Type:** Ensure `caption_source` returns a tuple where the first element is the caption record object with a `tokens` attribute, as expected by `marker_inside`.

If these conditions are met, the change is safe and correctly implements Ruling 32.