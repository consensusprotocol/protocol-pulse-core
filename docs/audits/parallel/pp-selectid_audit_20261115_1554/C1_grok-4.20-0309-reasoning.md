# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 38 s finish=stop usage in 24041 / out 762 usd_reported=0.043174 usd~0.139 (upper-bound price)

**CODE AUDIT: pp-selectid-20261115_1554 (RULING 116 / lineup calibration)**

**Summary**  
The patch implements Ruling 116 exactly as ordered: a per-rater calibrated floor derived from the lowest rating PBX gave any approved line-up (never below 3), applied only to the calibrated rater (Grok), with all other back-ends and any invalid calibration falling back to the stricter STANDARD_LINEUP (COHERENCE_MIN=4). The hook slot remains on its own calibrated bar (Ruling 115). All sites that compute `min(...)` over clip ratings now correctly exclude the hook and read the verdict-specific floor. The mark is emitted only when both verdicts used the calibrated bar and is placed outside the seal. Tests are comprehensive, mutation coverage is complete, and the live calibration file is validated against its source data.

The change is orthogonal to SENTENCE LAW, SELECTION LOCK, SNAP LIMIT, NEIGHBOUR, ONSET/TAIL, CREDITS, L-a through L-l, M2, M12, and LAW 22. No renderer, selector, or release-auth path is touched. GPU0-only and smallest-diff constraints are satisfied (the new module is the direct analogue of `hook_bar.py`).

**Findings**

[P2] `lineup_bar.bar()` performs a `datetime.fromisoformat` followed by manual `tzinfo` check, then a separate future-date check using `HB.SKEW_MIN`. This duplicates logic already present in `hook_bar.py`. A shared helper would reduce maintenance surface. (Does not affect correctness or fail-closed behavior.)

[P2] `lineup_calibration.json` embeds full `through_line` strings, story IDs, and pin paths for four specific packages. While the test in `TestTheLiveCalibration` proves the floors match the source runs, the file is now a de-facto content dependency. Any future prompt change (new `MEDLEY_VERSION` / `COHERENCE_VERSION`) forces a full re-calibration run even if the underlying rating distribution is unchanged. Consider storing only the minimal rating vectors + seed list.

[P3] Repeated parenthetical "(ruling 116 (Q3, ruling 106's default APPLY))" appears 12 times across comments, docstrings, and test strings. After the first explanatory block the qualifier can be shortened to "(R116)" without loss of traceability.

[P3] `TestRuling116LineupBar.test_ruling_63_reorders_a_line_up_whose_hook_sits_at_its_floors` and the takeaway test use `mock.patch.object(PK, "_live_lineup_bar", ...)` on one code path and `mock.patch.object(PK, "COHERENCE_MIN", ...)` on the other. The two patching styles are inconsistent and make the "standard bar" case harder to read. A single context manager or fixture parameter would improve clarity.

[P3] Nit: `floors_for()` returns a tuple `(floors_dict, which_str, sha_or_None)`. The call sites immediately unpack into three variables, but the third is only used when `which == "calibrated"`. A small namedtuple or dataclass would make the data flow self-documenting.

No violations of fail-closed rules (M12), no gate reclassification outside the explicit Ruling 116 calibration, no leakage of hook rating into post-hook `min()` after the fixes, and no impact on protected preview / v2f byte-identity. All must-fail/must-pass cases listed in the governing laws remain satisfied because this patch does not touch sentence law, punctuation restoration, channel clustering, canon, or release authorization.

P1_OR_WORSE: 0