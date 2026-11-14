# Audit 20261114_1349 (ruling 102; the $19 stop; glm's H1 and M2 from audit 20261114_1246), cycle 2: consensus

Reviewers:
- grok-4.20: SHIP yes. No P0, no P1.
- qwen3.8-27b: yes with conditions. No P0, no P1. It withdraws its cycle-1 <critical> (the diff computes both
  exclusion sets by vendor).
- glm-5.3-flash: yes with conditions. No P0, no P1. Both of its conditions are tests, not code.

All three agree that the ruled four-leg order is enforced and tested leg by leg; no answer is HELD on every path and
never cached; the local judge is recorded on both pin types without moving any existing seal; the confirm-ahead is
Grok-only, proven end to end; the $19 stop holds at its boundary.

## Taken after this cycle (tests only; no line of code changed)

- **glm P2-1: a real step_a failure, not a mock, must land HELD.**
  test_every_leg_answering_out_of_contract_is_held_through_the_real_step_a:
  - every leg ANSWERS out of contract, so the real step_a skips each (failover) and the chain is spent;
  - the moments are HELD, each leg was asked exactly once, and nothing is cached;
  - the next build asks again and glm's in-contract answer gives the verdict.
  test_ruling_102.py now holds 18 tests.

## Documented, no change

- **glm P2-2, "the medley's and the spotlight's held_102 are not proven disjoint".** They are not disjoint, and the
  line never sums them. One moment can be asked at both second screens in one build. proof_ledger.ruling_102_line
  names each population separately ("N at the medley's second screen [...], M at the spotlight's [...]"), with its ids.
- **glm P2-3, a first-screen judge verdict on the pin.** last_resort_of filters the moment's verdicts the same way
  whichever screen gave them, and the note's words (cycle 1, taken) hold for both. The first screen reaches the judge
  only through Plan B's chain (ruling 87).
- **glm P2-4, the note's keys.** The medley's pin keys the note by segment label, the key its gate rows use. The
  spotlight has one segment and keys it by moment id. Each matches its own pin's rows.
- **qwen: escalate a moment held over and over; watch the confirm-ahead's spend.**
  - Every build's RULING 102 line names the held moments in capitals on STATE line 1. A repeat is visible there, and I
    will flag any moment held three builds running.
  - The confirm-ahead's spend is printed per build (ruling 101's line). It runs only when the plan finds a usable Grok
    leg and a Heimdall lead.

SHIP: yes. The code committed is the code cycle 2 reviewed. FINAL.diff differs from C2_STEP.diff only by the one test
above.
