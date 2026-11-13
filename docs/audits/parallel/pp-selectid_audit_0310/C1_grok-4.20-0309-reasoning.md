# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 97 s finish=stop usage in 11249 / out 574 usd~0.071 (upper-bound price)

**P0: none**

**P1: none**

**P2:**
- pipeline/package.py:17 (stand_alone_check): edl construction and call to SA.check_edl(edl, rate=None, subject=SA.subject_terms("", "bitcoin")) exactly matches the render's validate-stage call (hook first, then ordered clips with index/labeling implied by check_edl, rate=None, bitcoin subject). Reproduces the exact PASS/FAIL/FAIL verdicts on the held pin d2657bbe texts (test:195).
- pipeline/package.py:28 (no_role_on_screen): calls both SA.opener("clip", ...) and SA.opener("hook", ...) with rate=None semantics; returns non-None (drops) *only* for conjunction/reply-fragment openers that fail both roles. Pronoun openers that fail hook but pass clip return None (test:205). Matches "drops ONLY moments that can be neither".
- pipeline/package.py:52,93,107 and inventory:134: stand_alone_check result is threaded into every medley package's gates row (PASS only if ["ok"] is True; rows evidence captured; unmeasured/missing/FAIL never produces PASS). package_pin.py:153 and test:166 confirm required_gates now includes "stand_alone"; missing row or FAIL refuses pin (test:244).
- pipeline/package.py:61,92,96 and build(): no_role filter runs immediately after usable(), before prescreen/angle/vendor calls (test:233 verifies bad moment never reaches angle_write). lineup_for(need_stand_alone=True) skips any candidate that fails the check (including pronoun-hook fallback and no-Bitcoin-subject cases); never seals a lineup the render's check_edl(rate=None) would reject.
- All existing checks (usable, prescreen, coherence, hook_onset, etc.) and acceptance criteria are untouched; this is strictly additive stricter pre-filter + gate (complies with "never change what an EXISTING check accepts", L-m, L-j, "pin must never seal a lineup render would hold").
- tests/package/test_medley.py:194-257: new TestStandAloneAtThePinStage exercises every stated behavior, the held-pin reproduction, no_role rule, lineup selection change, build() filtering, gate row, and pin refusal on FAIL. Existing tests updated only for the new required gate.

No violations of any listed governing law visible in the diff (L-a through L-l, M2, M12, LAW 20/22, pin-stage rules). Hard-coded bitcoin subject matches the provided "for a pinned moments package labelled 'bitcoin'" context; no other subjects appear in diff. Imports inside functions and "smallest diff" constraints followed. No renderer/compositor/selector changes.

**SHIP: yes**