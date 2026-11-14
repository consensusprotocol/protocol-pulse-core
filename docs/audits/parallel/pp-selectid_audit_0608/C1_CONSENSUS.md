# Audit 0608 (ruling 91's MEDLEY half: the takeaway's value verdict), cycle 1: consensus

Reviewers:
- grok-4.20: SHIP yes with conditions.
- qwen3.8-27b: SHIP yes with conditions.
- glm-5.3-flash: hit its 24k-token cap after 882 s (finish=length, no SHIP line). Its text holds 43 <medium> and 1
  <question>, with no <critical> and no <high> anywhere. Every point it reached is answered below. It reviews again in
  cycle 2.

Upper-bound cost: about $0.66 ($0.124 + $0.106 + $0.430), outside SPEND_LY.json.

## Implemented

- A test of the REAL path. It answers qwen's condition 1 and glm's "verify" items on the call site, the row's text and
  the pin.
  - test_the_real_verdict_runs_inside_the_build_and_its_row_seals runs build() with package.takeaway_value itself,
    only the router faked (the Rig's new real_value switch).
  - A clear yes seals the row from the real record (status PASS, text = the spoken takeaway, by the fake back-end,
    words 16), and to_pin accepts it.
  - An answer out of contract is rejected (router.reject) and is no verdict. On clips that meet the seconds that is the
    no-voice shape.
  - test_medley: 185 tests (18 new).

## By design (the orchestrator decides; asked on STATE line 1, 06:14, question A)

- grok <high>: a value loss never increments take_failed, so after two losses on short clips the line-up ends
  without ruling 3's no-voice.
  - That is the reading under question. Ruling 91: "a medley that loses its takeaway falls back to L-y's no-voice
    shape ONLY IF its clips meet the seconds". Ruling 3's path may add a clip, which 91 does not allow for a value
    loss.
  - test_a_value_loss_never_counts_toward_ruling_3s_two_failures pins it. The 11-mutation check killed the mutation
    that counts a loss (M9).
  - If the orchestrator rules otherwise, it is a one-line change. No change now.

## Refuted, with evidence from the code

- grok <medium> / qwen <low> / qwen condition 2: "an OLD pin re-pinned through to_pin is now refused". No path does
  that.
  - tests/package/reseal_attested.py (ruling 67) re-seals with package_pin.seal() directly (lines 40-43 and 100),
    never to_pin.
  - The integrator's scripts/integrator/check_pin_only.py calls gate_problems(gates) with the default REQUIRED_GATES
    and seal(). It never calls required_gates; its own takeaway_value check reads the row, with no row needed when there
    is no takeaway.
  - seal() is unchanged. Every proof pin still recomputes (test_spotlight test_every_pin_sealed_before_recomputes;
    test_speakers test_every_earlier_pin_still_recomputes_and_a_dropped_later_field_is_caught).
- qwen <high>: "a stale verdict after a ruling-65 rewrite".
  - lone_slot returns only "caption" or "title". rewrite_alone rebuilds the package with dict(fields, **{slot: line})
    for that slot alone, so the takeaway and its verdict never change on that path.
  - The coherence-failure path continues to a NEW write, which gets its own verdict: the call is unconditional for
    every write past the cheap branch, so `val` is always the verdict of the write being gated.
  - to_pin's takeaway_problems refuses any row whose text is not the shipped takeaway (fail closed).
- glm (a), "the lock could replace the takeaway after the verdict".
  - lock_precheck.apply changes only the segments (the adopted clip text), hook_first_words and pk["precheck"].
  - It reads the lines only to refuse one that quotes an adopted segment's changed words (ruling 67).
- glm (1), "a replayed reply could pass".
  - package_pin.gate_problems refuses any REQUIRED row whose replayed is not exactly False, and takeaway_value is
    required for a medley with a takeaway.
  - The test feeds {"text": t, "replayed": True} and gets PinRefused.
  - build() runs the same gate_problems before it returns a package.
  - In this code "replayed" means served OFFLINE (never deliverable). A live run's recorded reply is "cached" and
    replayed False: the fixed seed's "one verdict per text" is that cached reply.
- glm <question>, "is segs the play order?". Yes. build() passes the same segs to takeaway_value and to
  assemble_medley([m["moment_id"] for m in segs], ...), whose segments the render plays in that order.
- glm, "out['why_none'] is not shown". build() builds it from every tried line-up's rec["why"] ("no angle gave a
  package: angle 1: ..."). test_a_second_loss_ends_the_line_up_and_never_adds_a_clip asserts "ruling 91" in it.

## Accepted as is (fail closed, bounded): the (f) edge

grok and glm both judge it acceptable; glm calls it "acceptable-with-note rather than a blocker".
- The case: on clips that meet the seconds, a write whose takeaway loses its value verdict AND whose caption (or
  title) alone fails a gate goes to the no-voice shape with that caption. Its gates then fail closed (no package; the
  why is recorded), with no ruling-65 rewrite of the caption on that path.
- Nothing wrong can ship. Ruling 3's no-voice path already has the same property ("the title and caption are the
  latest write's and go through every gate again").
- Possible improvement, NOT built here (a proposal for the orchestrator, outside ruling 91's text): give both no-voice
  paths ruling 65 (b)'s fixed caption when the caption alone fails.

## Verified, no change

- qwen <medium> no_voice_fits vs ruling 3; qwen <medium> injection; glm's prompt and ok-rule checks. Clip text and
  the line are quote_data'd, with '"' -> "'", under the UNTRUSTED note. The parse is strict: exactly the five keys,
  each answer "yes" or "no". The cap is counted in code.
- glm on the guard in no_voice (content < nv_lo with value): redundant after no_voice_fits, kept as a fail-closed guard.
- glm on _takeaway_record's value sub-dict omitting words / cap / text: the record keeps "text" and "words" at its top
  level, and the sealed row carries all of them. Diagnostics only.
- glm on alone_n / last_fid / last_rw65: its own trace finds the forced rewrite consistent with ruling 66's
  takeaway-alone writes. The one rewrite is spent when it starts, so no loop can repeat it.
