# Audit 0915 (the orchestrator's 09:03 rulings: R-29 and ruling 92 amended), cycle 2: consensus

Reviewers:
- grok-4.20: SHIP no. It repeats cycle 1's <critical> (ValueError, not GateNotMeasured) and <high> (the build's
  float(m["start"])). It adds the private E._parse_time as a second <critical>. It does not engage with cycle 1's
  evidence (the decorator).
- qwen3.8-27b: no SHIP line. It scores R-29 at 5/10 on the same ValueError claim, now with KeyError too (its N1 and
  N2). New: N8, a news item that is not a dict.
- glm-5.3-flash: SHIP yes with conditions:
  - (1) cite or add the conversion, and show the test passing;
  - (2) confirm the Router's replay passes over a leg with no recording;
  - (3) non-blocking: the float guard, and E._parse_time's contract.

Upper-bound cost: about $0.40 ($0.138 + $0.136 + $0.123), outside SPEND_LY.json. Audit 0915 in all: about $1.15.

Cycle 2 needs no code change. The code as it stands meets every condition; the evidence follows.

## glm's conditions, met

1. The conversion is `@_measured` (moments_gate_adapter.py:93-103).
   - It wraps vo_fidelity (applied at :146), as it wraps context_integrity (:106) and exclusion (:177).
   - It catches KeyError, TypeError, ValueError, IndexError and AttributeError, and raises GateNotMeasured("the case
     cannot be read: ...").
   - It predates this change, so the diff shows only its use.
   - Run on the scratch copy, test_an_unreadable_case_is_the_harness_error_never_a_guess: 1 passed.
   - vo_fidelity on four unreadable cases raised exactly this:
     - title "": `GateNotMeasured | the case cannot be read: ValueError: the case's title is not a non-empty string`
     - a zoneless built_at: `GateNotMeasured | the case cannot be read: ValueError: the universe's clock
       built_at='2026-11-12T05:06:13' is not a zoned time`
     - a universe with no built_at (qwen N1): `GateNotMeasured | the case cannot be read: KeyError: 'built_at'`
     - a universe with no news (qwen N2): `GateNotMeasured | the case cannot be read: KeyError: 'news'`
   - qwen N8, a news item that is not a dict: item.get raises AttributeError, which the same decorator catches. The
     harness's ERROR, never a verdict.
2. The replay walk is Router.call (providers.py:1146-1172).
   - It walks the role's chain. A leg with a recording on disk is served, live or in replay.
   - In replay, a leg with no recording is noted "replay: not recorded", and the walk goes on to the next leg.
   - When no leg has a recording it raises ReplayMiss (:1246-1247). vo_fidelity turns that into GateNotMeasured: the
     harness's ERROR, never a verdict.
   - The exam's recording pins no chains: make_router gets chains None in the recorder and in the harness. So both
     walk the same heimdall_first lists.
3. Non-blocking:
   - The float guard is refuted below.
   - E._parse_time's contract (eligibility.py:309-317): aware ISO-8601 only. A time that is missing, not a string,
     unparseable or zoneless gives None. The adapter raises on None, and mutation R9 is killed by that test.
   - The same parser reads every news item's time through E.age_hours (eligibility.py:327-329). moments.py:92 also
     uses it inside the package.

## Refuted, with evidence from the code

- grok <critical>, qwen P0, and glm's open question: "vo_fidelity raises ValueError or KeyError, not GateNotMeasured;
  the test will fail". Refuted by the decorator and the run above.
- grok <high>, qwen N4, glm P2: "the build's float(m['start']) at the source test (stage 8) crashes on a None start".
  - Every moment at stage 8 has passed stage 2.
  - Stage 2 runs P.truth_for on every moment that cleared step A (spotlight.py:846). truth_for float()s the same start
    and end inside its own try (package.py:2159-2162, :2173-2177).
  - A start that is not a number is stopped there: "L-v 2 / CUTTABLE: NOT MEASURED: ..." (spotlight.py:850-857).
  - Nothing between stage 2 and stage 8 sets start or end. So the float() at stage 8 has already succeeded once on the
    same values.
- grok <critical> 2: "E._parse_time is private". Not a defect.
  - It is a helper inside the package, used for exactly its contract (above), and it reads the clock and the items
    alike.
  - A change to it is caught by the adapter's tests (R9).
- grok <medium> and glm P2: "'None speaker turns a minute' reaches the judge when the record spans 0 minutes".
  - Cosmetic; both call it harmless. The refusal does not read turns_per_min. Not changed.

## Final

The fixed diff is C2_STEP.diff. FINAL.diff is written from the worktree after the copy, and must equal it.
