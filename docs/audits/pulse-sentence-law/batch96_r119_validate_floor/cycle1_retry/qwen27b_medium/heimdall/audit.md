# Heimdall audit

**Question:** Review this diff: ruling 119 (1), a calibrated floor (3.0) for the stand-alone clip scorer at the render's validate. Report ONLY defects you can prove by quoting the diff's code. Keep each "issue" under 60 words. If every check holds, answer PASS with no findings.

FACTS (unchanged code, not in the diff):
- stand_alone.check_edl returns sa = {"ok", "rows", "rate_error", optional "medley_names_bitcoin" {"pass", ...}}. Each row = {"segment": "hook" or "clip_NN", "opener": {"pass", "why"}, "topic": {"pass", "why"}, optional "scorer": {"score", "reason", "fault"}, "pass": opener.pass and topic.pass}. sa["ok"] = all rows pass, and medley_names_bitcoin.pass when that key is present.
- stand_alone.opener(kind, text, score, fault, moments) -> (ok, why). For moments=True, the score test inside it is score >= 3.5 (CLIP_MIN_SCORE). Its other refusals do not depend on the score: an empty text, a hook opening on a conjunction. trimmed_opener(word, score, fault, moments) is the same for a trimmed segment.
- stand_alone_scorer.scorer_sha() hashes stand_alone.py + story_semantics.py. story_semantics.model_digest() returns the Ollama digest, or None.

CHECKS:
C1. apply() changes a row only if ALL of these hold:
    - the row's segment is one of the mark's segments;
    - the row's opener failed;
    - the row has a scorer verdict whose numeric, non-bool score is >= 3.0 and < 3.5;
    - asked again with score 3.5 and the same fault, opener (and trimmed_opener for a trimmed segment) passes.
    Can any row change otherwise?
C2. The floor applies only if:
    - the pin record's package_sha256 equals the EDL's moments_package_sha256;
    - the running scorer_sha equals MEASURED_SCORER_SHA exactly;
    - the running digest equals MEASURED_DIGEST exactly.
    Can it apply otherwise (for example a None digest, or a prefix)?
C3. mark() accepts only exactly the fields note, floor, scorer_sha, segments, ruling, with these values:
    - note: telegram's line;
    - floor: 3.0, a number, not a bool;
    - scorer_sha: the full measured sha;
    - ruling: "119";
    - segments: a non-empty list of distinct ints in [0, n).
    Anything else raises ValueError, which run_fresh turns into a Hold and check_pin_only refuses. Is any malformed mark accepted, or any error swallowed?
C4. After apply(), can sa["ok"] be True while some row fails, or while medley_names_bitcoin fails?
C5. write_verdicts: is each verdict's "digest" its own result entry's? Is the scorer block's "digest" the single digest shared by every scored verdict, and null otherwise?

**Panel:** qwen27b  |  **Cost:** $0.0047
## Consensus findings (majority of panel agrees)
- none

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
