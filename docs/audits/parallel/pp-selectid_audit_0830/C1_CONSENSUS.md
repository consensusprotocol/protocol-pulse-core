# pp-selectid audit 0830 (RULING 54: the pool completes an unformable angle; the proposer is told each clip's limits): cycle 1 consensus

**Run.** Verdicts:
- grok: no P0 / P1, "SHIP: yes";
- qwen: no P0 / P1, "SHIP: yes";
- glm: no P0; its review was cut at its 24,000-token limit (finish=length). Its P1s are answered below; two hold.

## IMPLEMENTED

| # | finding | change |
|---|---|---|
| F1 | glm P1-4: the fill can return a line-up made almost entirely of pool clips, which is not "completing" the angle | A filled line-up keeps at least HALF of its segments from the angle's own moments, as my stated scope said: the pool fills the MISSING places. The rule is checked INSIDE the search: lineup_for takes an optional accept(segs) (default None: behaviour unchanged), so it never discards a valid line-up that meets it in favour of one that does not. Tested: an angle whose own moments cannot reach half gets no fill. The 07:14 measurement (3 own + 1 pool in each angle) still fills. |
| F2 | glm P1-5: the extended list is unbounded (the whole cleared pool) | The pool adds at most SWAP_TOP (10) candidates, the best by score, as ruling 41's swap reads them. Dropped and doomed moments are excluded from that list too. |

## Answered (verified from the code)

| # | claim | the code |
|---|---|---|
| A1 | glm P1-1: dropped / doomed are excluded only by the caller | lineup_for itself drops them: `ms = [by_id[m] for m in angle["moments"] if m in by_id and m not in dropped]`, and build() passes frozenset(dropped \| doomed). F2 also excludes them before the cap. |
| A2 | glm P1-2: `filled` may be wrong | filled = the line-up's ids that are not the angle's own (in the pool); computed once, after the search. |
| A3 | glm P1-3: placement()'s truthiness differs (hook ok truthy, onset `is True`) | It is exactly lineup_for's own hook condition: `(m.get("eligibility") or {}).get("hook", {}).get("ok") and (m.get("hook_onset") or {}).get("pass") is True`. |
| A4 | glm P1-6: `exception` may be stale | The fill path sets exception from the filled line-up (or None) itself. The non-fill paths are unchanged code. |

## Verification

- test_medley 89 OK; every other suite OK.
- Limit recorded: the test of F1's in-search check shows the invariant (every returned fill has at least half its own);
  it does not construct the case where the preferred line-up fails the rule. The mechanism is one `continue` in
  lineup_for's combination loop.
