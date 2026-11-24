# Batch 125 (ruling 158 (2), V1's advertising line), cycle 1
Seats: qwen27b (medium) PASS 0.72; glm PASS 0.6 (3 low notes); gemma FAIL (1 high).
- gemma (high), "the ruling says the show's own branding, ticker and lower third are 'still a flag in 16:9', so the
  line must fail on them": DISPROVED, a misreading. "Still a flag in 16:9 as ruled" is ruling 146 (1)'s SOFT review
  flag for the show's own graphics in a 16:9-only package. The builder's pin carries it in review_flags. It is not a
  refusal. The ruling's HARD part is advertising, and this line asks about advertising only. The live control (the
  published 13 Nov video, CNBC's own ticker and lower thirds) got "yes" from both models, as the ruling wants.
- qwen (low): the same reading, resolved by the live control.
- glm (low x3): the verdict rule and the n/a rule are outside the hunk (they are tested: tests and mutations V2/V3);
  the line's length is fine (live, both models answered every line on 6 sheets and frames); the verify pack takes its
  keys from CHECKLIST (verify_pack.py:121), so the new key is listed.
