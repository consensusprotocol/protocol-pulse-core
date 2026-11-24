# Heimdall audit

**Question:** TASK: cycle 2 of the audit of batch 125 (Protocol Pulse, Python): V1's new checklist line "no_on_screen_advertising" (ruling 158 (2), the render's side). The same diff. Cycle 1: qwen PASS, glm PASS; gemma's finding (the show's own graphics should fail) was a misreading: the ruling makes the show's own graphics a SOFT 16:9 review flag carried by the pin, and ADVERTISING the hard refusal. Only state what you can verify from the diff. If uncertain, say so. Do not guess.

TRACE AND ANSWER:
T1. Write the three hardest stills for this line: (a) a real ad that a model could plausibly call the show's own graphic; (b) the show's own graphic a model could plausibly call an ad; (c) an ad visible on only one still of the sheet. For each, say what the line's wording makes the model answer, and whether that is the ruling's outcome.
T2. The line says "Answer 'yes' only if there is none". Is there any wording that makes "yes" mean an ad was seen, or "no" mean none (a double negative a model could invert)?
T3. Any other defect.

OUTPUT: for each finding, severity (critical|high|medium|low), the concrete failure, the fix. If none, say NONE.
REMINDER: only what the diff shows; say when uncertain.

**Panel:** gemma  |  **Cost:** $0.0004
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
