# Heimdall audit

**Question:** Batch 25 = EDL rule R4 for packages of type "moments" ONLY (orchestrator order 2026-11-12 '06:00', PBX's instruction; law L-q: under moments-first the host makes points, so R4 written for the story-first product, where the VO was glue, is re-set for this product; a TASTE rule, recorded under L-o / L-q; every INTEGRITY rule unchanged). The order: VO share limit 40 %; a VO line is allowed after the hook (intro), after each clip, and after the LAST clip (takeaway); total runtime 60-70 s stays hard; story-type pins keep the old R4; must-fail tests: VO share 41 % rejected, runtime 59.9 and 70.1 rejected, a VO line with no slot rejected.
Verified by reading the renderers (not in the diff): render16.py (segments: hook, vo_intro, then each clip followed by the bridge whose after_clip is that clip, then shoutout, then outro) and render_vertical.py (the same interleave, :894-930) place a bridge with after_clip == the last clip AFTER the last clip and BEFORE the shout-out; both render a VO line as a still background frame + 1.0 s PRE_ROLL + the full VO wav (render_vo_visual / render_vo_visual_vert), so the intro slot carries any length. Both key bridges by after_clip in a dict, so two lines on one slot would silently drop one: hence one line per slot, strictly increasing.
The change: edl_rules.rule_r4 dispatches an EDL with package_type == "moments" to _r4_moments: word caps unchanged (intro <= 30, bridge <= 20); every bridge's after_clip an int that is a clip index, strictly increasing (one line per slot, after the last clip allowed); VO seconds = sum over intro and bridges of words / 2.5 + 1.0 (R4's own estimate; 1.0 s = the renderers' PRE_ROLL); share = VO / (hook + clips + VO) <= 0.40; estimated runtime = hook + clips + VO + 14.30 s (FINAL_TAIL_S: what the approved preview's finals added to their word spans: credits card with the sign-off, outro, leads / tails, pads; 71.08 - 56.78), rounded to 0.01 s, inside 60-70. The sign-off is generated at the voice stage from the credits (in the tail, not in the share). pinned.moments_vo allows after_clip == last only when the package's type is exactly "moments"; pinned.build_edl records package_type. Mutations checked: limit 0.41, no runtime check, no slot check, moments rule for every EDL: each fails a test.
FIND: any EDL that is not a moments package and now gets the new rule; any way a VO line without a renderer slot passes; any boundary error (40 %, 60.0, 70.0); anything that weakens an INTEGRITY rule; tests that do not test what they claim. Quote file and line; if uncertain, say so; do not guess. At most 5 findings.

**Panel:** deepseek, qwen27b  |  **Cost:** $0.0088
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
