# gpt-oss-20b (openai/gpt-oss-20b) 72 s finish=stop usage in 11028 / out 11342 usd_reported=0.001240 usd~0.203 (upper-bound price)

**Answers to the four questions**

1. **Can any words of the clip itself that belong to an ad read reach a sealed package?**  
   No. `exclusion_verdict` will exclude any moment that contains an ad‑read marker in its own words (`ad_read_marker(moment_text)` is non‑None), regardless of the `before_marker_soft` flag. Thus no ad‑read words can survive into a sealed package.

2. **Can the clean pass, or a cached verdict from the other pass, let a marked moment in?**  
   No. The clean pass calls `exclusion_verdict` with `before_marker_soft=False`, so a marker only in the sentence before the moment causes an exclusion. Cached verdicts from the other pass are keyed with `"ad_before"` and therefore are not reused by the clean pass.

3. **Is the flag right (one per kept marked clip, counted toward the cap of 3)?**  
   Yes. `inventory` creates a single flag per kept marked clip (`e.get("ad_before")` and `e.get("verdict") == "keep"`). The test `TestRuling146SponsorBefore` confirms that exactly one flag is produced per kept clip and that it is counted correctly.

4. **Does the `gate_problems` addition refuse anything a live pin legitimately carries?**  
   No. The new check only flags rows that are not in the required set, are `FLAGGED`, and are not a soft gate with flags (`flagged_ok`). Since the sponsor gate is soft and its flags are present, it passes the check. The test `test_an_extra_flagged_row_stands_only_on_a_soft_gate_with_flags` demonstrates that legitimate flagged rows are not rejected.

**Findings**

| Severity | Finding | Comment |
|----------|---------|---------|
| **P0** | None | All logic paths behave as intended; no data loss or gate bypass. |
| **P1** | None | No critical defects requiring pre‑merge fix. |
| **P2** | None | No minor improvements needed. |
| **P3** | None | No nitpicks. |

**P1_OR_WORSE: 0**