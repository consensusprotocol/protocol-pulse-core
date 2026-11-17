# Batch 105 (rulings 136 / 137, the render-side HARD / SOFT switch): consensus

Heimdall only. One seat per invocation at medium; cycles 1 and 2 ran in parallel.

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (checks H1-H6) | PASS, 16,647 tokens | F1 "soft rows are not required to be present", judged NOT a defect (below) |
| 2 (break-it T1-T4) | PASS, 17,864 tokens | no JSON verdict (token cap). Its trace walked T1-T4 and judged each part fine, then looped on authorise's checks. |

**gpt-oss c1 F1, judged NOT a defect.**
- In blockers(), every INVENTORY row, SOFT included, still goes through `if v is None: bad[k] = "required gate row missing"` and `elif not isinstance(v, str) or v not in VERDICTS: bad[k] = ...`.
- Only the third branch (a well-formed non-PASS verdict) skips SOFT rows.
- The unchanged test_every_required_row_deleted_holds deletes each INVENTORY row, SOFT rows included, and every deletion still HOLDs.
- The quoted evidence is a garbled mix of diff lines.

**Consensus:** no defect. Nothing to implement.

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: 12 failing results on the old code; the two controls pass (a hard row still holds; a clean note is unchanged).
- MUTATIONS.log: 10 of 10 killed. F3 and F9 were killed only after the reworded-flag and not-Bitcoin-medley tests were added.
