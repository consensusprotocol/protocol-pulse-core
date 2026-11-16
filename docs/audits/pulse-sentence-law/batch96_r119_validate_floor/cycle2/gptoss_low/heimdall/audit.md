# Heimdall audit

**Question:** Try to BREAK this diff: ruling 119 (1), a calibrated floor (3.0) for the stand-alone clip scorer at the render's validate. For each attempt, give the exact inputs (the pin record PINNED_DECISION.json, the EDL row, the scorer verdict, the running scorer sha and digest) and the code path it takes. Report ONLY the attempts that succeed, as findings with the quoted lines that let them through. If none succeeds, answer PASS with no findings.

GOALS (any one is a finding):
G1. Make apply() lift a row that must stay refused. Such rows include:
    - a segment the mark does not list;
    - a score under 3.0, or NaN, or a bool;
    - a row with no scorer verdict;
    - an opener refused for a reason other than its score (an empty text, a hook opening on a conjunction);
    - a trimmed segment whose trimmed_opener refuses.
G2. Make the floor apply when it must not:
    - another scorer code, or other weights;
    - a None or prefix digest;
    - the mark on a package other than the EDL's;
    - a malformed mark.
G3. Make sa["ok"] True while a row fails or the medley rule (medley_names_bitcoin) fails.
G4. Make check_pin_only call a pin READY whose stand_alone_bar validate would refuse. Or make validate HOLD an UNMARKED pin because of this change.
G5. Make the release caption print the floor's line for a pin that does not carry a valid mark. Or make a review drop print it.

FACTS (unchanged code, not in the diff):
- stand_alone.check_edl returns sa = {"ok", "rows", "rate_error", optional "medley_names_bitcoin" {"pass"}}. A row = {"segment", "opener" {"pass", "why"}, "topic" {"pass", "why"}, optional "scorer" {"score", "reason", "fault"}, "pass" = opener and topic}.
- stand_alone.opener(kind, text, score, fault, moments=True) affirms on score >= 3.5. It refuses without regard to the score for an empty text, and for a hook opening on a conjunction or reply word. trimmed_opener is the same for a trimmed segment.
- run_fresh.stage_validate raises Hold when sa["ok"] is False. A Hold stops the run before anything is cut or rendered.
- telegram.bar_lines is called only by build_caption, which is the release caption of an authorised run. The review drop never calls it.

**Panel:** gptoss  |  **Cost:** $0.0005
## Consensus findings (majority of panel agrees)
- **[medium] pipeline/stand_alone_floor.py:112** The function apply() sets rec['not_applied'] when the running scorer code or weights do not match the measured values, but still returns the original sa without altering sa['ok']. This allows a run to pass validation (sa['ok'] remains True) even though the calibrated floor was not applied, violating the intended gating logic.
  - evidence: `        if code != MEASURED_SCORER_SHA or weights != MEASURED_DIGEST:
            rec["not_applied"] = (f"the running scorer is not the measured one (code {str(code)[:12]}, weights "
                 `
  - fix: After setting rec['not_applied'], the function should also set sa['ok'] = False (or otherwise prevent the run from succeeding) before returning. For example:

            if code != MEASURED_SCORER_SHA or weights != MEASURED_DIGEST:
                rec["not_applied"] = (...)
                sa["ok"] = False
                return sa
  - raised by gptoss:F1; agree: gptoss

## Raised but not agreed
- none

## Added in cross-examination (not voted on)
- none
