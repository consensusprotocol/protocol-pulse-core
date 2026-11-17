# Batch 112 (on batch 110, ruling 142: canon_spans reads '-7' word by word as the text does; the contraction is a word form): consensus

| Cycle | qwen27b | gpt-oss |
|---|---|---|
| 1 (H1-H4) | FAIL: F1, NOT a defect | PASS |
| 2 (break-it T1-T3) | PASS (0.72) | no verdict (token cap). Its trace found nothing ("So not a defect"). |

**qwen c1 F1, NOT a defect.**
- The claim: the lone-hyphen case ['24', '-', '7,'] reads 3 tokens word by word but 2 as text, because _NUM_HYPHEN fires on "24 - 7,".
- Why not: _NUM_HYPHEN is `(\d\s+)-(?=\d)`, so it needs the digit IMMEDIATELY after the hyphen and never fires on "24 - 7". Both paths read the range "24 7", as they already did for "70 - 75". Measured, spans == text in every case:
  - ['24', '-', '7,']: 24 7 / 24 7
  - ['available', '24', '-', '7,', '365']: available 24 7 365 (both)
  - ['24', '-7,', '365']: 24 7 365 (both)
  - ['24', '-', '7']: 24 7 (both)
- The lone-hyphen text is now in TestRuling142Spans as a record.

**Consensus:** no defect.

**Own evidence:**
- MUST_FAIL_OLD_CODE.log: the 4 new tests fail on e3bdaf6e (batch 110): Yahoo f0a51c45 and Natalie feb4b72f hold, the spans differ, and the contraction is not a word form.
- MUTATIONS.log: 5 of 5 killed.
