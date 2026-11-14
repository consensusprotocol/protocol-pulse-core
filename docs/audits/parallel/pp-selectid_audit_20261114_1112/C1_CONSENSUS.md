# Audit 1112 (the orchestrator's 10:48 rulings (2) the snap ceiling, (3) NUMBER and the show date), cycle 1: consensus

**Folder:** this audit ran as label 1112 into docs/audits/parallel/pp-selectid_audit_1112, which already held the Nov 13 11:12 audit of rulings 58 + 59 (commit 5cb00867). The labels are times of day, so they collide across days. Its tracked files were restored from git before anything was committed, and this audit moved here under a dated label. Cycle 1's prompt and diff name the old path as they were sent.

Reviewers:
- grok-4.20: SHIP no. One <critical> (refuted: the change is the ruling) and one <medium> (answered from the code).
- qwen3.8-27b: SHIP yes with conditions. One <high> (refuted), two <medium> that verify the regex and strict_features
  as correct.
- glm-5.3-flash (466 s): SHIP yes with conditions:
  - the locale of the month names (implemented);
  - no third reader of SNAP_MAX_S (verified);
  - the manifest date's format (verified);
  - the medley's downstream with a 21-35 s moment (answered: it never reaches one).
  Its H1-H6 resolve inside its own text, and M1-M4 are recorded below.

Upper-bound cost: about $0.39 ($0.050 + qwen's + $0.224). Outside SPEND_LY.json.

## Implemented

- glm M2: without_manifest_date built its month pattern with strftime('%B') / ('%b'), which follow the process locale.
  Under a non-English LC_TIME, 'November 12' would no longer be taken out, and the 30 dated sign-offs would fail again.
  Now a literal English table (vo_fidelity.MONTHS) gives the month and its 3-letter form, whatever the locale. The 9
  mutations are still all killed. 57 tests in the two suites pass.

## Verified from the code (glm's and grok's conditions)

- "No other reader of SNAP_MAX_S assumes 20 s" (glm, grok <medium>): grep over pipeline/, tests/ and scripts/ finds it
  only in ledger_build.py (the docstring, the constant, the check and its reason) and test_ledger_build.py.
- "Can a 21-35 s moment reach a MEDLEY?" (grok <medium>, glm): no.
  - package.usable(..., seg_max=SEG_MAX_S) (package.py:162; SEG_MAX_S = 20.0 at :67) drops any moment over 20 s before
    any medley stage: angles, step A, cut, hook rule, scorer candidates.
  - The spotlight already takes 12-35 s moments by ruling 90: usable(..., seg_max=SPOT_S[1]) at spotlight.py:196, :217.
    Its stages (cut, onset, ALONE scorer, layout) have run on moments up to 35 s since 22:40 Nov 13.
  - The first build after this lands is the live check: its log shows what snapped past 20 s and where it stopped.
- The manifest date's format (glm H1, M3): the packager's manifest and every exam case carry "YYYY-MM-DD". A date that
  date.fromisoformat cannot read leaves the text as it is, which is the stricter old behaviour (its digits are numbers
  again), never a looser one. (This machine runs Python 3.10, whose fromisoformat reads only YYYY-MM-DD.)

## Refuted, with evidence

- grok <critical>: "LAW 20 / M2: never change what a check accepts to make a render pass".
  - The change is the orchestrator's ruling (3), verbatim in QUESTION.txt: "vo_fidelity's NUMBER rule accepts the
    manifest's own show date as production metadata, the WHOLE date only ... and only when it equals the manifest's
    date".
  - The law forbids the BUILDER loosening a gate to get a pin through. This is the law's own authority ruling on what
    the gate measures. It was asked on STATE line 1 (10:06), with the facts both ways, and ruled at 10:48.
  - It is applied exactly as ruled: the whole date only, never a bare number, only the manifest's own date. Each
    narrowing is a test, and 9 mutations are each killed.
- qwen <high>: "SNAP_MAX_S should import spotlight.SPOT_S[1], not repeat 35.0".
  - spotlight imports ledger_build (spotlight.py:122). The ledger read importing the spotlight, and through it package,
    package_pin and vo_fidelity, would invert that dependency.
  - The pattern here is a literal plus a drift test. The old test held SNAP_MAX_S equal to package.SEG_MAX_S the same
    way. test_the_snap_ceiling_is_the_spotlights_and_the_medley_keeps_its_own_20_s fails the moment the two part (and
    pins the medley's 20 s), and mutation S1 is killed by it.
- glm H2 (on 'November 120'), resolved by qwen's trace and pinned by a test: the lookahead refuses the written match
  before a further digit, so '120' stays whole and NUMBER names '120'. Mutation N7 is killed by that test.
- glm M1 ("a constants test"): the medley's 20 s holds by construction (package.py is not in the diff). The test pins
  the three numbers so that any change to one of them is seen.
