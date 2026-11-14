# Audit 0003 (ruling 93), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes; qwen3.8-27b SHIP no (a critical and a high, refuted below); glm-5.3-flash SHIP yes
with conditions.

## Implemented

1. glm (its strongest point, a fail-open): check() cut burned_in to TEXTS_MAX items without a marker, so a ticker
   listed 13th would pass. FIXED: the items are sorted blocking-first before the cut, and burned_in_truncated counts
   what was cut (sealed). A ticker listed after 15 eligible straps still blocks (tested).
2. glm: a wordless channel bug (a logo) may come back with "text": null; the contract refused it, so the clip went
   unmeasured. FIXED: text may be null and is stored as "" (tested).
3. glm: a hook blocked both as a hook (third person) and by ruling 93 reported only the first reason. FIXED: both
   reasons are reported. A measured line-up clip blocked by ruling 93 now reports ruling 93's reason, not the
   record's stale "why"; an unmeasured clip still reports its own why (the existing test holds).

## Refuted, with evidence

- qwen <critical> 1 and 2 ("pre-ruling-93 records are blocked; existing pins are invalidated"):
  - layout_block() is called only on records in a build's pool. visual_pin.key() holds VERSION, so after
    visual-2 every clip is asked again: a visual-1 record is never served to a build.
  - Sealed pins are never re-judged by it. package_pin.to_pin / seal / pin_seal and the integrator's readiness check
    read the sealed visual record through sealed() only, which copies "burned_in" only when present, so a pin sealed
    before keeps its digest.
  - A record without question 4 that did reach a build would be one that never answered ruling 93's question. It
    fails closed (law L-m); that is intended.
- qwen <high> 3 ("eligibility does not read the visual verdict"): the ruling puts the per-clip judgement in "the
  pin-stage visual check (ruling 70)", which needs the clip's frames, fetched only at the pin stage.
  eligibility.layout_ok runs when the ledger is read (no frames). It drops the channel-name hold. The pin-stage
  verdict (layout_block) gates every on-screen role in both builds: a hook may not open; a line-up clip is dropped
  before any write; a spotlight is not clean.
- grok <medium> (a redundant local import in clean_visual): spotlight.py binds visual_pin only inside build(). The
  module has no global VP, so clean_visual's local import is needed.
- glm (hook_block's body on a record with no third_person): hook_block reads rec.get("measured") and rec.get("flags")
  only. The tests pass such records.
- glm ("story_layout_channels counts Bitcoin Magazine although its preview clip is not sentence-ready"): this is the
  fact's definition (channels that may be on screen by layout). Readiness is a separate, named reason.
