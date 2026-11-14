# Audit 0041 (rulings 94 + 95), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes with conditions; qwen3.8-27b SHIP no (one critical); glm-5.3-flash SHIP yes with
conditions.

## Implemented

1. qwen <critical> / glm <high> 1, 8: _can_open(pending_verdict=True) put a synthetic (5, None) in place of a missing
   verdict. It never sealed anything: the spotlight's ALONE >= 4 gate reads the real verdict, and stand_alone_check
   reads it at the pin. The placeholder is gone all the same. An explicit `defer` (spotlight only, a third-person
   opener with NO verdict yet) skips the opener test without assuming a score, and the medley never defers. glm's
   condition is met with a test: a third-person spotlight whose ALONE verdict is 3.0 is refused by the opener rule;
   with no verdict it waits and is refused at the ALONE stage ("no rating"); at 4.0 it reaches the package.
2. glm <high> 24: the pool's trim variant is now checked again by usable() and against the pool's ids before it
   replaces the snapped moment.
3. grok: next_attempt's `now` was unused. It now gives each upload's age in hours (a measured fact for ruling 95).
4. The integrator's merged stand_alone.py (409188ef, sha256 14f30115...) replaces this branch's copy byte for byte:
   the same rule, with its comments and messages. Its test file is not taken: it imports run_fresh.moments_screen,
   which only the render side has. This branch keeps its own ruling-94 cases.

## Refuted, with evidence

- glm <high> 2 (the snap may prepend a sentence, so the trim never happens): when the snap adds the sentence BEFORE,
  the moment no longer opens on the conjunction. The new first word is judged by the opener rule like any other, and
  the moment is trimmed only when it still opens on a trim word. That is the ruling (a conjunction is the opener's
  fault only when it is heard first).
- grok: P.utc_z is in module scope (spotlight.py imports package as P at the top).
- glm <high> 15 (affirmed() for moments=True reads the score alone): this is ruling 60's moments rule, the same as
  the clip rule's (score >= 3.5 alone).
