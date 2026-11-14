# Audit 2322, cycle 1: consensus (the spotlight, rulings 90-92; the decoder c705b20ed800)

Reviewers: grok-4.20-0309-reasoning (SHIP yes, no finding), qwen3.8-27b (one critical, mediums; its reply then
repeats one paragraph about twenty times), glm-5.3-flash (first try failed on the network: IncompleteRead; retried on
the current diff, see C1_glm-5.3-flash.md when present). grok and qwen reviewed C1_STEP_grok_qwen.diff.

## Implemented

1. qwen <critical> 1: `never_delivered` was a literal True in build()'s facts, so the row could only PASS. It rested
   on pool()'s usable() call made at the build's start, but the row itself measured nothing (law L-m). FIXED:
   build() now measures it again right before the package: `P.usable([m], ctx, delivered, optout,
   seg_max=SPOT_S[1])` must keep the moment (no delivered span overlapped, not the same speech, inside 12 h). A
   moment usable() drops is a FAIL row and the pin is refused.

## Changed since cycle 1 by the builder (in the fixed diff)

2. The ALONE scorer's wait counts its polls (wait_s // SCORER_POLL_S) instead of reading the clock. Production waits
   the same; a test with a stubbed sleep no longer spins for 60 s.
3. The writer is told the speaker is VERIFIED only when BOTH step-A verdicts verify it. The gates read the verdict off
   the writer, which is unknown until the writer answers.
4. The driver reads SPOTLIGHTS.json again right before it writes a spotlight pin, and refuses the pin when the channel
   already has a spotlight that ET day or the record cannot be read. This closes a race between two builds.
5. snap(): a moment whose own span holds a speaker marker is reported as such, not as "not measured".

## Refuted, with evidence

- qwen <medium> 3 (LP.apply runs after the gates, so an adopted spoken text was not the text the verdicts judged):
  - This is the medley's own order (package.build's no_voice path and the voiced path both apply the lock after
    gate_problems), so it is not new.
  - LP.apply refuses a package whose lines quote an adopted segment's changed words (ruling 67).
  - The adopt class is fillers and one function word (ruling 84).
  - For a spotlight, the segment seals the ALONE scorer's verdict on the rated text. If an adoption changes the text,
    package_pin.scorer_problems refuses the pin ("carries a clip-scorer verdict that does not affirm exactly its
    text"), so it fails closed.
- qwen <medium> 4 (thread safety of VF.check / CI.check_contexts in parallel): package.paid_gates runs the same two
  calls in parallel on one pool for every medley package.
- qwen <medium> 5 (the build can wait up to 10 minutes for the ALONE scorer): this is by design, bounded
  (SCORER_WAIT_S), and only when a moment that passed every other stage has no rating yet.
- qwen <high> 2 (several versions): qwen retracted each one in its own text ("Retracted", "No bug").

## glm-5.3-flash (retried on the current diff: SHIP yes with conditions)

Implemented:
6. glm <medium> package_pin.py: the closing line entered the seal when edl_vo carried the key. A medley's edl_vo that
   ever gained "closing": null (an echo, a hand edit) would have changed its digest. FIXED: the closing enters the
   body for shape "spotlight" only, together with the shape and the comment. A test seals a medley-shaped edl_vo with
   and without the key: the same digest.
7. glm <medium> the test's verified-table fixture and the record fixture were written into the source tree. FIXED:
   they now go in a temporary directory.

glm's two conditions, verified from the code:
- (a) "LP.apply never rewrites vo['closing']": lock_precheck.apply changes only an adopted segment's text and its
  "attested" record, pk["hook_first_words"] and pk["precheck"]. It reads the lines only to refuse a line that quotes
  the changed words (ruling 67). The closing line is never written.
- (b) "snap_risk is ruling 90's risk re-judgement": ruling 90 says "ruling 32's snap; the added words judged as usual".
  ledger_build's ruling-32 docstring defines "as usual": step A (L-s), the exclusion verdict (every L-u risk), L-v 2
  and usable() (time words), and snap_risk() for its price predictions. The spotlight's snapped moment goes through
  each: step A, L-v 2 and usable() in build(), exclusion for a finalist, snap_risk() in snap(). The miner's
  eligibility is judged again too (moments.judge on the snapped span).

Refuted or recorded, with evidence:
- glm <medium> "the turns-a-minute denominator is the marked span": speakers.captions returns EVERY caption line of the
  record (opens_turn true or false), so minutes run from the first caption line to the last. That is the captioned
  episode. It returns None only when no line carries a marker.
- glm <medium> "the inventory's one_per_channel_day can say PASS while the pin-time re-read refuses": then no pin is
  written, and the record (package.json) holds spotlight_pin_refused with the reason. Recorded; nothing is sealed.
- glm <medium> "the wait is skipped when one moment already qualifies": by design. Ruling 90/92 says to seal the first
  moment that qualifies. An unrated moment is reconsidered at the next build, after the scorer's pass.
- glm <high> (scorer dedup): glm retracted it in its own text (the key is the id AND the text).
