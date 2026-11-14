# Heimdall audit

**Question:** Batch 43 cycle 3 = V1 second vision back-end, a second VENDOR route (law L-x). visual_check._call_any now also routes 'xai:<model>' to _call_xai: the JPEG base64 as an image_url data URI plus the checklist text, temperature 0, to https://api.x.ai/v1/chat/completions with the XAI_API_KEY read by name from the repo .env (never printed; a missing key raises RuntimeError, which the callers treat as a route error: retried, then no answer = HOLD). The reply's content goes through the SAME parsers as Heimdall's (fail closed: unparseable / missing lines are 'no answer'). The default panel is unchanged; no model is seated by this diff.
FIND: any way the Heimdall or local paths changed; a key leak; an xAI reply read as a pass when it is not one; a route error not retried / not held; tests that do not test what they claim. Reply with the JSON verdict; keep the reasoning short; at most 3 findings.

**Panel:** qwen27b, glm  |  **Cost:** $0.0006
## Consensus findings (majority of panel agrees)
- **[low] pipeline/visual_check.py:0** xAI reply content goes through the same parsers, but the diff shows no test that an unparseable/empty xAI reply yields 'no answer' (fail closed); the new test only asserts routing with a canned '{"answers": {}}'.
  - evidence: `VC._call_xai = lambda p, t, m, timeout: self.calls.append(("xai", m)) or ('{"answers": {}}', {})`
  - fix: Add a test where _call_xai returns garbage/empty content and assert the caller records 'no answer'.
  - raised by glm:F1; agree: qwen27b, glm

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
