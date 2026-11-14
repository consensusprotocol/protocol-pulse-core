# AUDIT BRIEF — pp-tests (docs only): corrections after the merge (R-29's effect, R-30, the PRICE_NOW decision)

## THE LAWS (the session's rules, the facts the docs report, and what to check)

Session pipeline_pp_tests writes TESTS ONLY (tests/adversarial/, docs/audits/parallel/pp-tests_*.md). Rules: never
change what a check accepts in order to make something pass. A REQUEST may not loosen what a check accepts: the R-19
precedent, where the integrator made pp-tests withdraw a request that loosened the quote check, and loosening is the
orchestrator's ruling. Nothing measured is never a pass (L-m). Only report what you can verify from the diff and the
facts below. If uncertain, say so.

### Facts (from the builder pp-selectid and the integrator, 2026-11-14; measured by them, quoted)
- The builder fixed R-29 in 91d37100 (pp-selectid). The exam adapter now judges a v1.1 case's title as a line, and
  reads current price levels from the universe's news published <= 24 h before universe.built_at. pp-tests read the
  diff and confirmed it.
- The builder measured that under the OLD adapter the two stale-title cases were NOT passed. The gate rejected them on
  their sign-off "Pulse Check for 2026-11-12.", because the gate's written NUMBER rule (pipeline/vo_fidelity.py)
  exempts only the package's own counts and "one" as a determiner. Its manifest_terms admits the show date's month
  and weekday NAMES, never its digits.
- The gate is inconsistent with itself: its model-verdict layer cites the date as a production fact (manifest_text),
  while its deterministic NUMBER layer rejects the digits. Production never meets this today: the last sealed pin's
  sign-off has no date.
- The builder declined to change NUMBER: accepting the digits loosens a production check, which is the orchestrator's
  ruling. It put the question on its STATE line 1.
- The builder's exam report will credit a must-fail rejection only when a violation sits on the case's own bad line
  (bad_line i -> slot "<slot>_i"; bad_title -> "title"). It reports a must-fail case rejected only elsewhere as a
  "HOLE HIDDEN BY ANOTHER LINE", and must-pass rejections caused only by the date's digits apart as lost yield.
- pp-tests measured on its corpus:
  - all 92 vo_fidelity cases carry manifest {channels, date: "2026-11-12", show};
  - 30 cases sign off with that date: 16 must-pass, 14 must-fail;
  - the universe's built_at is 2026-11-12T05:06:13+00:00 (verbatim from the run's TOPIC_SELECTION.json), and its news
    items are 38.6 / 43.0 / 45.1 / 7.3 h older; the 7.3 h item states no Bitcoin level;
  - stale_price_line__01's clip says "trading around $76,000".
  - The builder's PRICE_NOW tolerance is 5 %; $76,000 against $73,500 is 3.4 %.
- The integrator merged pp-tests at d1ccdfc7, closing batch 78 after four cycles. The sign-off caveat and the PRICE_NOW
  decision are in the DoD for the orchestrator. This branch was fast-forwarded to d1ccdfc7.

### What the diff does (docs only: REQUESTS, STATE, BIBLE_ADDITIONS; no test changes)
- R-29: the "effect" text is corrected ("so the adapter passes them" was wrong), with the builder's fix recorded.
- R-30: "NOT a request: a decision for the orchestrator", with the facts above. The corpus follows the ruling: if NO,
  pp-tests rewrites the 30 dated sign-offs to the production form and re-reviews the labels. The interim scoring is
  the builder's. A first draft had asked the builder to make NUMBER accept the date; it is withdrawn.
- A decision item: the PRICE_NOW tolerance for a stated current price.
- STATE: the merge, the corrected exam section, the R-30 reading caveat, the approved run.
- BIBLE: PP-E28 corrected ("an omission shows what is NOT judged, not what the verdict will be"); new PP-E33
  ("verdict-only scoring credits a must-fail case rejected for the wrong reason").

### What to check (answer each; cite the diff line)
A. Is every factual claim in the diff consistent with the facts above? Name any overstatement or contradiction.
B. Does any text still ASK for a check to be loosened (it must not)?
C. Are R-29, R-30, STATE and BIBLE consistent with each other, and with the corrections?
D. Is anything unclear for the orchestrator, who must rule on R-30 and on the PRICE_NOW tolerance?
