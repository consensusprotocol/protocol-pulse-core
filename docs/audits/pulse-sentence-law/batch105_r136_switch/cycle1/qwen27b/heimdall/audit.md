# Heimdall audit

**Question:** Review this diff (orchestrator RULINGS 136 / 137, 11:00 / 11:05 ET Nov 17), verbatim in part: "TWO CLASSES. HARD gates still refuse: the words are not what the cut carries ..., wrong or unknown speaker credit, ..., a cut that breaks mid-word, a crop that cuts a face or burned text, channel count and runtime, spend stop. Every OTHER gate becomes SOFT: it scores and FLAGS, it does not refuse." and (137 (2)) "HARD: words, speaker credit, cut mid-word, crop through a face or burned text, layout that cannot render, runtime, attestation and the review-path delivery; SOFT: everything else, flagged in the note." and (137 (1)) "'altcoin / not about Bitcoin' is HARD". The never-empty SEAL's cap ("only if it has no more than 3 soft flags") is the builder's; the render lists every soft flag it finds. Nothing publishes without PBX: delivery is the review path to his Telegram.

FACTS (unchanged code, not in the diff):
- release_auth.INVENTORY[fmt] are the rows that decided release (exactly PASS with execution evidence); MONITORING rows are only reported; blockers() feeds attest() and authorise(); run_fresh's run verdict is computed from blockers().
- authorise() is the last check before telegram.deliver_run sends anything; it re-reads ATTESTATION.json, GATE_REPORT.json and the bound files.
- PINNED_DECISION.json holds the pin (written by pinned.prepare; not an attested file); the builder's sealed gates carry the flags and moments_package["review_flags"] is derived from them; edl.json's moments_package_sha256 is the sealed package's digest.
- edl_rules.validate_edl returns [{"rule", "pass", "reason"}] for rule_r1..rule_r11; stand_alone.check_edl returns rows with "opener" and "topic" results, "medley_names_bitcoin", "ok" and "rate_error".

Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

CHECKS:
H1. Can any HARD row (G18, G3b, G17, G12, G15, G20, G4s, G5, outro_locked) ever pass while not PASS, or without execution evidence?
H2. Is every SOFT row still required to be present with an exact verdict (missing or malformed = blocker), and is a SOFT row that failed or was never measured always said as a flag?
H3. Is PASS_WITH_FLAGS given only when nothing HARD failed, and are the attested flags exactly what authorise re-derives (the pin's bound by the package digest, the stages', the gates')?
H4. run_fresh: does a failing edl rule hold unless it is named SOFT (an unknown rule fails closed)? Does a topic or medley that is not about Bitcoin still hold? Do the takeaway, editorial laws and a stand-alone opener flag and go on?
H5. telegram: does a flagged run's note open with "REVIEW FLAGS: " and its flags, and is a clean run's note unchanged?
H6. Does anything else change behaviour?

**Panel:** qwen27b  |  **Cost:** $0.0122
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
