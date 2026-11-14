# Label check (claude-opus-5-5, effort low)

stop_reason: end_turn; usage: in 18642 / out 3713

**Findings** (only cases with a problem or a borderline call)

1. **vo_fidelity__stale_price_title__01**: BORDERLINE, reasoning only. The title "Bitcoin ran from 16K to 126K" is past tense, so it does not claim a current price. The staleness argument ("misstates where the price is") is weak. The case still correctly FAILs on rule B: 16K and 126K are in no selected sentence. Fix the `why` (and the rule) so it rests on "not in the selected sentences" alone.

2. **vo_fidelity__host_commentary__08**: BORDERLINE on D(ii). "Freedom you never use is easy to give away." is placed right after the Bitcoin Mechanic clip about voluntarily limiting freedom. It can be read as glossing that speaker's view. It names no one and states no fact, so PASS is defensible. Keep it, or swap in a more neutral aphorism to remove the doubt.

3. **vo_fidelity__host_commentary__13**: BORDERLINE on D(ii). "That is why scarcity matters to me." follows the Coin Bureau price clip. "That is why" asserts a reasoning link to clip content that is about selling, not scarcity. It is not checkable, so PASS holds. Consider placing the line after clip A, which is about mining gold.

4. **vo_fidelity__hedge_matched_attribution__07**: BORDERLINE on staleness. The attribution is faithful ("I do expect" becomes "expects"). However, "later this year, especially the first quarter of next year" is relative to the clip's recording date, not the show date of 2026-11-12. PASS is defensible because it is attributed verbatim. Consider adding "at the time" or using a clip with fixed dates.

**No confounds found.** Every other must-fail case breaks only its stated rule, with secondary issues on the same bad line. No must-pass line fails a test, and I found no wrong class labels.

**Summary**
- 52 cases checked.
- Cases to change: vo_fidelity__stale_price_title__01 (`why` text only).
- Optional tightening: host_commentary__08, host_commentary__13, hedge_matched_attribution__07.
- **READY**
