# Audit 0108, package B (the verdict call sites, the shadow report, the replay), cycle 1: consensus

Reviewers: grok-4.20 SHIP yes (P0/P1/P2 none); qwen3.8-27b SHIP yes with conditions (P0 none); glm-5.3-flash SHIP yes
with conditions (P0 none).

## Implemented

1. glm (P1): with every shadow answer missing and no compared decision on the pin, the report said the pin "WOULD
   have sealed under Grok", which nothing supported. The streak was already safe (missing shadows reset it). FIXED:
   would_seal_under_grok is None in that case (tested).
2. qwen (P1-2): a comment in shadow86 now says that "grok no verdict" on a pin's decision counts as a stop (fail
   closed).
3. qwen (P2): package.hook_ratings' docstring still said "one re-ask" of the same model. It now says the reply out of
   contract moves on to the next model (call_parsed).

## Refuted, with evidence

- qwen P1-1 (replay85's manual 429 handling bypasses the Router's backoff and spend cap): the replay calls
  router.call, so every call is accounted on ruling 48's ledger and stops at its cap (SpendLimit). The manual part
  only lifts the run-long down mark the Router sets on a 429, after a pause, so one rate-limit does not end a
  measurement. The replay is a measurement tool, never a gate.
- glm (P1): the replay's clips-alone / coherence decisions accept two older Grok contracts (disclosed in decide()'s
  docstring) that production's parsers no longer accept. The ruling-88 (b) decision rests on the HOOK rows, which use
  the strict contract (glm confirms). The clips-alone / coherence rows changed no routing.
