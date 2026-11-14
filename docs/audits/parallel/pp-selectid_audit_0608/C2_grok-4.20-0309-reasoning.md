# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 18 s finish=stop usage in 24015 / out 1418 usd~0.156 (upper-bound price)

**CYCLE 2 AUDIT — pp-selectid-0608 (Ruling 91 Medley Half)**

1. WHAT DID THEY CATCH THAT YOU MISSED?
   GLM's replayed=True gate analysis (package.py:263–268 and package_pin.py:421–431) and the exact test at lines 739–740 that exercises {"text": t, "replayed": True} → PinRefused. Grok's concrete (f)-edge scenario (value loss + lone caption VO-fidelity fail on the ruling-91 break path, package.py:278–279). Qwen's stale-verdict mutation after ruling-65 rewrite (package.py:261 + 284). I had flagged the value-loss / take_failed interaction but missed the precise lone_slot guarantee that takeaway text never changes on that rewrite (lone_slot:87–89 returns only "caption" or "title").

2. WHERE DO YOU AGREE OR DISAGREE?
   - GLM replay point: fully agree — takeaway_problems explicitly checks row["text"] == t and the test at 767–772 confirms replayed=True (or missing text/status) raises PinRefused; gate_problems + required_gates path is also exercised.
   - Grok <high> on value loss never incrementing take_failed: agree — this matches the ruling text ("a value loss never counts toward ruling 3's two failures") and is pinned by test_a_value_loss_never_counts_toward_ruling_3s_two_failures (lines 639–650); the 11-mutation check killed the counter-mutation.
   - Qwen <high> stale verdict after ruling-65: disagree — lone_slot only rewrites caption/title (lines 87–89), val is overwritten after every write (line 261 and 294), and test at 592–594 confirms the rewrite's NEW text receives its own value call and row binding. The consensus refutation holds.
   - All three on (f)-edge: partially agree — it is a real regression vs old ruling-3 path (caption that would have been lone_slot-rewritten now fails closed in no_voice:191–193) but is acceptable per L-m ("gates must pass on final bytes") and the ruling-91 text that privileges "its OWN clips meet the seconds".
   - Backward-compatibility: agree with consensus — seal() signature unchanged, integrator uses REQUIRED_GATES only, reseal_attested.py never hits to_pin, and test_every_earlier_pin_still_recomputes still passes.

3. NEW FINDINGS FROM THIS REVIEW
<medium> **pipeline/package.py:329 (no_voice call site)**: when v_novoice is set (line 278) the call passes value=v_novoice but the subsequent no_voice_fits guard at 159–162 only triggers on content < nv_lo; a concrete 48 s FITS case with value loss + title that fails context integrity after the break will still reach the fidelity/context re-gates (191–193), fail closed, and record "ruling 91: the takeaway did not earn its place... L-y's no-voice shape did not pass" (line 336). Matches the known (f) edge; no crash but loses the package where old code would have continued. Test at 565–585 only exercises the clean no-voice path.
<low> **pipeline/package_pin.py:429 (takeaway_problems)**: row["text"] != t check is exact (not stripped); the render uses strip() so a trailing space produced by the writer but accepted by render would be refused at pin time. Concrete: takeaway="Nobody bends these rules. " (trailing space) passes render but fails to_pin. Not hit by current tests (all clean strings).

4. REVISED SCORES
| Subsystem              | Cycle 1 | Cycle 2 | Why changed |
|------------------------|---------|---------|-------------|
| takeaway_value contract| <medium>| <low>   | Real-value test (652–668) + parse_value rejection path now verified; prompt injection surface closed by UNTRUSTED + quote_data. |
| build loop / ruling-91 | <high>  | <medium>| Qwen stale-verdict and GLM replay concerns refuted by lone_slot guarantee, explicit val overwrite, and 17 new tests (including mutation-killing set). |
| no_voice_fits + (f)    | <medium>| <medium>| Edge confirmed but accepted; new finding at line 329 does not change severity. |
| pin / backward compat  | <medium>| <low>   | Consensus evidence (seal() untouched, integrator path, reseal_attested.py) eliminates re-pin risk. |

5. FINAL PRIORITY LIST
P0 CRITICAL: none verifiable from diff.
P1 HIGH: none.
P2 MEDIUM:
- package.py:278–279 (no_voice_fits break) + 191–193: the (f) edge (value loss + caption fidelity fail on ruling-91 path ships no package). Document or add lone_slot rescue before no_voice.
- package_pin.py:429: consider row["text"].strip() == t.strip() for robustness (current stricter check can refuse a render-accepted package).
- package.py:159–162: no_voice_fits guard only checks content; if med["measured"] is False on the initial clips-alone verdict the ruling-91 no-voice path is incorrectly blocked (test at 620 only exercises measured=False after value call).

6. THE SINGLE HIGHEST-LEVERAGE CHANGE
The takeaway_problems() + required_gates(takeaway_line(pk)) pair (package_pin.py:418, 421–431) that binds the row text to the exact shipped takeaway — this single check prevents every stale-verdict, replay, and wrong-line attack surface.

7. PRODUCTION READY?
Yes with conditions: (1) the (f)-edge at package.py:278–193 is explicitly documented as accepted (gates must pass on final bytes); (2) no old pins are ever re-processed through to_pin (integrator continues to use seal() + REQUIRED_GATES only); (3) the 11-mutation check remains green after any P2 tweaks.

**Findings**
<medium> pipeline/package.py:329 — FITS clips (48 s), first write value={"adds":"no"}, title fails context integrity after the ruling-91 break: no_voice runs the failing caption again, returns None, line-up ends with no package (old ruling-3 path would have reached lone_slot rewrite).
<low> pipeline/package_pin.py:429 — takeaway text "Nobody bends these rules. " (trailing space) passes render strip() but fails exact == check, raising PinRefused.

SHIP: yes with conditions (document (f) edge; keep integrator on seal() path; address P2 items above)