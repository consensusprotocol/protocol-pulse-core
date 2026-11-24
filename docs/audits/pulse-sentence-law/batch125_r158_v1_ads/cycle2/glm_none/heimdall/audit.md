# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 125 (Protocol Pulse, Python): V1's new checklist line "no_on_screen_advertising" (ruling 158 (2), the render's side). The same diff. Cycle 1: qwen PASS, glm PASS; gemma's finding (the show's own graphics should fail) was a misreading: the ruling makes the show's own graphics a SOFT 16:9 review flag carried by the pin, and ADVERTISING the hard refusal. Only state what you can verify from the diff. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Write the three hardest stills for this line: (a) a real ad that a model could plausibly call the show's own graphic; (b) the show's own graphic a model could plausibly call an ad; (c) an ad visible on only one still of the sheet. For each, say what the line's wording makes the model answer, and whether that is the ruling's outcome.
T2. The line says "Answer 'yes' only if there is none". Is there any wording that makes "yes" mean an ad was seen, or "no" mean none (a double negative a model could invert)?
T3. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff shows; say when uncertain.

**Panel:** glm  |  **Cost:** $0.0002
## Consensus findings (majority of panel agrees)
- **[low] pipeline/visual_check.py:55** The 'yes'/'no' polarity of the checklist line is inverted relative to the other lines in CHECKLIST and relative to the field name, which a model can plausibly invert; the wording does mitigate it, but the convention break is real and verifiable in the diff.
  - evidence: `("no_on_screen_advertising", "... Answer 'yes' only if there is none; when you cannot tell an ad from the show's own graphic, answer 'no'. ...") — every neighbouring line is phrased as a positive pres`
  - fix: Either rename the key to 'on_screen_advertising' with 'Answer yes if any still shows ...' (matching the positive-presence convention of the other keys), or keep the key and add an explicit 'yes = no advertising seen' gloss; the former is the smaller, convention-consistent change.
  - raised by glm:F1; agree: glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
