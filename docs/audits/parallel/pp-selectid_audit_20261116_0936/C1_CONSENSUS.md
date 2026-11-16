# C1 CONSENSUS — pp-selectid audit 20261116_0936 (RULING 120's note: the delta of the stand-alone floor)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 3 of 3. P1_OR_WORSE: gemma 0,
mimo 0, qwen 1. Cycle 1 $0.0034 of Heimdall, not capped.

A CORRECTION TO THE QUESTION: it gave a typed time for the integrator's agreement ("09:47 ET"), which was wrong (this audit
began at 09:36 ET by the clock); QUESTION.txt now says "after ruling 120". No bearing on the code.

qwen's one P1, "telegram.py's STAND_ALONE_BAR_NOTE is not in this diff; if the two texts differ the integrator's check
refuses the mark": TRUE THAT THE TWO MUST MATCH, and not a defect of this diff: that constant lives in the integrator's tree
(its half, its own audited delta, landed after this one in the agreed order). qwen itself notes "If the Telegram change is
its own audited delta, this code is correct in isolation". AT LANDING the match is CHECKED, not assumed: before this half
lands, the integrator's branch's telegram.STAND_ALONE_BAR_NOTE is read (read only) and must equal package_pin.STAND_ALONE_NOTE
byte for byte, or nothing lands. No change to the code.
