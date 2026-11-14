# Audit 2322, cycle 2 (the fixed diff, C2_STEP.diff): outcome

- grok-4.20: SHIP yes with conditions, no critical or high. Its two P2s are IMPLEMENTED:
  - one_per_channel_day reuses the one ET day computed for the package (a build crossing midnight cannot measure two
    days);
  - a test asserts that a rating arriving at poll 2 ends the ALONE scorer's wait there, and that the wait is bounded
    (20 polls).
  - Its third condition (the integrator runs decoder c705b20ed800 with the spotlight branches) is the integrator's
    merge fd5c9cc4 message, 23:16 ET.
- qwen3.8-27b: SHIP yes. It agrees the cycle-1 critical (never_delivered) is fixed and withdraws its other points
  ("No action needed").
- glm-5.3-flash: answered at 824 s and was cut at its 24k-token reply budget (finish=length), with no SHIP line. It
  tags no critical or high. Its points:
  - precheck (<medium>, "arguably high"): a pre-check {"ok": true, "segments": []} would stamp the row PASS. It never
    shipped: lock_precheck.apply refuses a pre-check that does not cover exactly the package's segments, and the
    driver's LP.pin_problems checks again. IMPLEMENTED anyway: the row PASSes only with ONE verdict, pass or adopt, on
    this clip's video. An ok with no verdict is NOT RUN, and a hold is FAIL (tested).
  - N24 "price_now is a hard-coded (True, 'n/a')": REFUTED. The 4th positional of package.inventory is r4_res
    (package.py:3063 `def inventory(fid, dup, rt_ok, r4_res, ...)`), and the spotlight removes the "r4" row. price_now
    is computed from vo_fidelity's deterministic layer (the PRICE_NOW rule and price_now_measured).
  - "the no-closing path's context check may be vacuous": REFUTED. context_integrity.package_view shows the TITLE and
    the CAPTION with the clip, and step B is told that what a viewer concludes a speaker asserts "INCLUDES whatever the
    title, the caption or the voice-over ATTRIBUTES to that speaker". With no closing line, steps B and C judge the
    title's and the caption's framing of the clip. context_a is step A's verdict off the writers.
  - RECORDED (a residual, not a defect of this diff): the first comment is not in context_integrity's view. VO
    fidelity's verdict judges it (an attribution to a named speaker needs that speaker verified), as for the title and
    the caption, but step B does not read it.
