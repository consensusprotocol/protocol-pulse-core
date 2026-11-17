# Heimdall audit

**Question:** Review this diff to pipeline/run_fresh.py (the render's validate stage). ORCHESTRATOR RULING 141 (2) (13:40 ET Nov 17), verbatim in part: "STAND_ALONE becomes SOFT in lockstep on both sides ... (a flag: 'The clip (X) may not stand alone: <the scorer's reason>')". RULING 138 (3): "each flag is one plain sentence PBX can judge in five seconds (what the checker doubted, about which clip), no codes." The builder's sealed pin carries its own flags in moments_package["review_flags"], with the exact prefix "The clip (<channel>) may not stand alone:" for this case; the render must not say a second sentence about a clip the pin already flags, and must still flag every other clip.

FACTS (unchanged code): stand_alone.check_edl returns rows {"segment", "channel", "first_words", "opener": {"pass", "why"}, "topic": {"pass", "why"}, "scorer": {"score", "reason", "fault"} (only when the scorer was asked), "pass"} plus "rate_error" (the scorer raised; no verdict). The topic rule, the medley rule and a malformed floor mark HOLD before this code (unchanged). release_auth.pin_review_flags(run_dir) returns the pin's review_flags list ([] for no pin; None when unreadable or bound to another package). flag(run, text, detail) appends one flag. The opener's "why" strings look like "clip opens on 'but'; the clip scorer does not affirm it stands alone (2.0, fault starts_mid_thought)", "'but' trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)", "hook opens on the demonstrative 'this': nothing is heard before a hook".

Cycle 2: try to BREAK it. Report ONLY a defect you can show with a CONCRETE state (rows, rate_error, the pin's flags) traced through the diff's code. Keep each "issue" under 80 words. If you cannot break it, answer PASS with no findings.
TARGETS:
T1. An opener failure that reaches PBX with no flag at all.
T2. A flag that carries a code, misstates the scorer's verdict, or names the wrong clip.
T3. An exception in the validate stage from this code.

**Panel:** gptoss  |  **Cost:** $0.0015
## Consensus findings (majority of panel agrees)
- **[high] pipeline/run_fresh.py:0** The function alone_reason uses the re module, but re is not imported in this file. This will raise a NameError during validation, causing an exception in the validate stage.
  - evidence: `def alone_reason(r, rate_error=None):
    ...
    why = re.sub(r"\s*\([^()]*\b(?:fail closed|ruling|fault)\b[^()]*\)", "",
                 str((r.get("opener") or {}).get("why") or ""))
    return wh`
  - fix: Add an import statement at the top of the file: import re
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
