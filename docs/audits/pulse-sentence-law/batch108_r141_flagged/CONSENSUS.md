# Batch 108 (ruling 141: a builder-sealed row FLAGGED with its flags counts where the render requires a live PASS): consensus

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (H1-H4) | PASS (0.95) | PASS (1.0) |
| 2 (break-it T1-T3) | PASS (0.92) | no verdict: token cap. Its trace considered each target and found nothing ("So no", "Good"), then looped. |

**Consensus:** no defect.

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: the 6 new tests fail on f4d00826. The protected-references test fails there only because the scratch tree had no references.
- MUTATIONS.log: 6 of 6 killed (the control passes with the reference EDLs copied in).
