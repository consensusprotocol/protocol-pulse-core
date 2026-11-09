**Q1 (D1):** Yes. `grounded_event_date()` (story_semantics.py:391-432) sets `authority="source publish metadata"` when `source_published` is present and uses the model date only as a tiebreaker (lines 408, 422). A model date older than the publish date is marked `model_date_discarded=True` (lines 399-402). The 72 h + 7 d window is unchanged (`STALE_GRACE_DAYS=7`, `start = now - timedelta(hours=window_hours) - timedelta(days=STALE_GRACE_DAYS)`). `_story_published()` returns `None` on missing/unparseable fields (editorial_select.py:84-86), never treating them as fresh. `transcript_currentness()` still requires verified `CURRENT_EVENT` evidence (story_semantics.py:435-457). No path lets a genuinely stale story through.

**Q2 (D2):** Yes. `second_verified_quote()` (editorial_select.py:291-311) runs independent `adjudicate()` on non-overlapping excerpts and requires `counted_as_same_event` (CURRENT_EVENT + verbatim + valid chunk + SUPPORTS). R2 is enforced by passage exclusion + overlap dedupe + `MAX_VERIFIED_QUOTES_PER_VIDEO=2` (lines 349-351, 770-773). Malformed output or failed adjudication returns `(None, reason)` and produces no window (lines 306-307, 362). No more than two windows per video are ever chosen.

**Q3 (D3):** Yes. `repair_window()` (editorial_select.py:314-362) is gated on `clip_fault in BOUNDARY_FAULTS` only (line 822). Floors (4.0/3.5) and durations (8-12 s / 13-25 s) are constants. Each added sentence is checked by the same `on_event` verifier; a failure closes the direction (lines 345-348). The window is re-rated once and rejected if still below floor (lines 831-836). Off-topic/other/unspecified faults are never repaired.

**Q4 (FAIL-CLOSED):** All exception paths, empty inputs, and malformed LLM output produce recorded rejections (LLMParseError, missing data, `None` verdicts) and never a window/count/pass. No regressions outside D1-D3.

**Q5 (TESTS):** The new tests (TestD2TwoVerifiedWindowsPerVideo, TestD3BoundaryRepair, TestE9TranscriptCurrentness, TestE9Orchestration) cover positive and negative cases for each rule and would fail on reversion. One minor untested branch: `_parse_ts` on non-ISO strings that still parse under `fromisoformat` after Z replacement (harmless, does not affect D1 logic).

<critical>
None.
</critical>
<high>
None.
</high>
<medium>
None.
</medium>
<low>
None.
</low>

SCORE: 98/100  
VERDICT: MERGE