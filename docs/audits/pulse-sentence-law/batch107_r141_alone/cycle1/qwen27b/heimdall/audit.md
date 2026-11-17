# Heimdall audit

**Question:** Review this diff to pipeline/run_fresh.py (the render's validate stage). ORCHESTRATOR RULING 141 (2) (13:40 ET Nov 17), verbatim in part: "STAND_ALONE becomes SOFT in lockstep on both sides ... (a flag: 'The clip (X) may not stand alone: <the scorer's reason>')". RULING 138 (3): "each flag is one plain sentence PBX can judge in five seconds (what the checker doubted, about which clip), no codes." The builder's sealed pin carries its own flags in moments_package["review_flags"], with the exact prefix "The clip (<channel>) may not stand alone:" for this case; the render must not say a second sentence about a clip the pin already flags, and must still flag every other clip.

FACTS (unchanged code): stand_alone.check_edl returns rows {"segment", "channel", "first_words", "opener": {"pass", "why"}, "topic": {"pass", "why"}, "scorer": {"score", "reason", "fault"} (only when the scorer was asked), "pass"} plus "rate_error" (the scorer raised; no verdict). The topic rule, the medley rule and a malformed floor mark HOLD before this code (unchanged). release_auth.pin_review_flags(run_dir) returns the pin's review_flags list ([] for no pin; None when unreadable or bound to another package). flag(run, text, detail) appends one flag. The opener's "why" strings look like "clip opens on 'but'; the clip scorer does not affirm it stands alone (2.0, fault starts_mid_thought)", "'but' trimmed and no clip-scorer verdict on the trimmed text (fail closed, ruling 33 part 2)", "hook opens on the demonstrative 'this': nothing is heard before a hook".

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.
CHECKS:
H1. Is every opener-only failure still flagged (never silently dropped) unless the pin already carries "The clip (<that channel>) may not stand alone:"? Can a pin flag for one clip silence another clip's flag?
H2. Does the flag follow the ruled words, give the scorer's reason in plain words (no snake_case, no "ruling", no "fault"/"fail closed" parentheticals), and say plainly when the scorer gave no answer?
H3. Can any row shape (missing scorer, a non-numeric or bool score, a None reason, a missing channel) or an unreadable pin record raise in this code?
H4. Does anything else change behaviour (a HOLD that now passes, a pass that now holds)?

**Panel:** qwen27b  |  **Cost:** $0.0063
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
