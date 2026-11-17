# RULING 136: THE BUILDER'S DESIGN (selection side), one page. Nothing built yet: your ruling first.

## (1) TWO CLASSES: every selection-side row of the R132 table (pp-selectid_R132_TABLE_20261117.md)

HARD (still refuses). Each is on your list, or names its reason:
- Row 3, usable:
  - the hard exclusion flags and opt-out (exclusion);
  - the 12 h rule;
  - L-p, a delivered span never again (never-reused);
  - L-v 3, time words past 24 h (stale time);
  - L-u's 20 s per source (runtime).
- Row 4, ruling 53: a speech re-posted by a second channel used once (never-reused).
- Row 6, the ad-read marker (exclusion).
- The adapter's "altcoin or not about Bitcoin" screen (exclusion: the show's scope). I propose HARD; I cannot name a stopped video, so it is yours to rule.
- Rows 7, 9 and 16: 3 channels after the free stages, after step A, after the second screen (channel count).
- Rows 8 and 15: step A and the second screen, ONLY for a factual or stale-time refusal, and only when BOTH families refuse. Any other step-A reason is SOFT.
- Row 10: L-v 2 second recognition and CUTTABLE (the words are what the cut carries; a cut that breaks mid-word).
- Rows 14 and 24, the visual check: ONLY a crop that cuts a face or burned text. Every other visual flag is SOFT.
- Row 19 line-up rules: ONLY one clip per channel (L-u, L-y 4) and the seconds 36.7-51.5 (runtime).
- Row 23: the lock pre-check after rulings 131 and 135 (the integrator's).
- Row 25: the exclusion verdict (exclusion and accusation).
- Row 27 line gates:
  - ONLY the ROLE rule (wrong or unknown speaker credit: 3f481f5a's "guest");
  - runtime R4;
  - recency (stale time).
- The seal: the spend stop; the 12 h window at the seal (window_problems).

SOFT (scores and FLAGS; never refuses):
- Row 5: the clip scorer, STAND_ALONE opener, and "completes the previous claim".
- Row 11: G17a hook onset, and ruling 33's trimmed cut. A cut that breaks mid-word stays HARD by row 10.
- Row 12: hook eligibility and the STAND_ALONE hook rule.
- Row 13: the calibrated hook bar.
- Rows 14 and 24: the other visual flags (third person, lower third, layout).
- Row 18: the join table.
- Row 19: the other line-up rules: the price cap (ruling 133), a short clip last, trimmed clips, STAND_ALONE.
- Row 21: the clips-alone verdict.
- Row 22: the question hook (ruling 37).
- Row 27: house style, L-y shape, DUPLICATE.
- Row 28: the value verdict.
- Row 29: VO fidelity.
- Row 30: context integrity.
- Row 31: coherence (the free panel).

A write that fails its own gate is written again, as now; only a line still failing after its rewrites becomes a flag.

## (2) NEVER EMPTY (package.build and package_pin; the integrator prints the note)
- The search runs as now and prefers a CLEAN line-up: on a soft failure it still tries the next line-up first.
- It no longer forgets the refused ones. Every line-up that passed every HARD gate and failed only SOFT ones is kept as a candidate, with its flags in plain words (e.g. "hook below the bar: scroll 2", "one join flagged").
- When no clean line-up seals, the build takes the best kept candidate: the fewest flags, then the highest soft scores.
  - It runs that candidate's remaining gates. The hard ones can still refuse; the soft ones only add flags.
  - It seals only if it has at most 3 flags.
  - The pin gets "review_flags": [plain words], a new SEALED_LATER field. This is a lockstep with the integrator's check_pin_only.
  - The integrator's Telegram note opens with "REVIEW FLAGS: ...".
- Limits (a day counter on my side, FLAGGED_DAY.json, checked again by the integrator):
  - at most 1 flagged package per build window (proposed: per build, as each build is one window);
  - at most 2 per 21:10-21:10 day.
  - A clean package always outranks a flagged one: if both are ready, the clean one is handed first, and the flagged one only if the day's limit allows.
- Money: a flagged candidate pays the same paid gates as a clean one, inside the same stop. No extra outside call is made just to flag.

## (3) YIELD, the number on line 1 from now (a free script over the records; no model call)
- Per gate (by R132 row), over the last 7 days' build records:
  - ENTERED: moments, or line-ups, that reached the gate;
  - REFUSED;
  - SHOWN WRONG, counted as a later reversal of the same span or line-up:
    - (a) it passed the same gate after a ruling changed it (e.g. the lock holds cleared by 131 and 135);
    - (b) a PBX-approved package that the gate refuses in the R132 replay;
    - (c) a refusal made only because a service was down (the 34 moments of the scorer outage).
- Any HARD gate refusing more than 25 % of what enters it goes on line 1 for your review.
- Built first, because it is free and tells us which classes matter.

## ORDER
135 lands → today's attempt → yield (free) → the class switch and never-empty (audit-first) → the 133 batch.
