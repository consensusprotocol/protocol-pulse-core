# Cycle 1 consensus: pp-selectid audit 20261114_2131 (the 21:10 fixes, the sealed formats, the re-seal)

Reviewers under ruling 107 (2): qwen3.8-27b (P1_OR_WORSE 1) and glm-5.3-flash. glm hit its 24,000-token cap with no
closing count, so the driver treated it as no answer and asked Grok as the third (P1_OR_WORSE 1). Cost: $0.0501
vendor-reported (qwen $0.0044, glm $0.0036, Grok $0.0421).

REFUTED, with evidence:
- qwen P1, "stripping formats leaves the seal valid". A pin sealed with "formats" has that key in its hashed body.
  pin_seal on a stripped pin hashes a body WITHOUT it, so the digest differs. test_formats asserts exactly this
  ("stripping it breaks the seal"), and mutation F3 (the recompute ignoring formats) is killed.
- Grok P1, "the version guard breaks the protected preview and the v2f references (L-d, LAW 22)". None of the
  reference or render checks calls the builder's visual gate. A grep of pipeline/check_preview_reference.py,
  pipeline/regression.sh, regression_test.sh, release_auth.py, pinned.py and run_fresh.py finds no visual_pin,
  layout_block or clean_visual. The guard runs only at this builder's pin stage, for new pins.
- glm P1-5, "format may seal a stringified dict". spotlight.layout_for's record is {"layout": <one of LAYOUTS, a
  string>, ...}: check_layout returns v["layout"], validated against LAYOUTS. So .upper() is "FIRST_HAND" /
  "CONVERSATION".
- glm P1-33, "formats may never reach the pin". package._package seals each segment's visual as
  visual_pin.sealed(m["visual"]) (package.py:383), and sealed() now carries "formats". The chain is visual_for ->
  m["visual"] -> sealed() -> the segment -> package_pin.formats_of -> moments_package["formats"].
- glm P1-39, "the re-seal's day place is not wired". Both call sites exist in unchanged code:
  spotlight.pool -> day_taken(spotlit, channel, day, m["derived_from"]["alternative_to"]) (spotlight.py:219), and
  at the pin proof_ledger.spot_place reads pk["spotlight"]["derived_from"], which spotlight copies from the moment
  (spotlight.py:1137).

IMPLEMENTED:
- glm P1-17: check() now sorts the blocking items first, then a CUT caption, so the 16:9-only decision survives
  TEXTS_MAX. Test: a cut caption listed after 14 whole ones keeps formats ["16x9"].
- glm P1-34/50 and Grok P3 (L-k): the ROLE comparison now uses canon. Each role noun is its canonical token
  (canon_tokens(...)[-1]), compared with the cited clip's canonical tokens. The hyphen and plural stripping is gone.
  Test: a capitalised, sentence-initial "Analyst here." supports "an ANALYST"; "analysts" is another word.
- glm P1-6/53 (the prompt and the gate disagreed): a role word inside a show or channel name the line credits is
  no claim (manifest_terms). Test: "From Analyst Answers: ..." passes, and "Our guests ..." still fails.
- Grok P2: the re-seal no longer mutates the caller's moment. for_pool returns a marked COPY in its place
  (replaced + variants, as a directive variant does). Test: the caller's record has no derived_from.

NOTED: qwen P2 (a verb such as "hosts" or "anchors" trips the rule): it fails closed and costs at most one rewrite,
and the writers are told never to use these words. Kept strict by ruling 106 (b), the stricter reading for
integrity. glm P3 (the coupling of RENDER_16X9_ONLY with the integrator's release): it flips only on the
integrator's word, in its own audited change.

Tests: 85 pass in the touched suites. Every required suite passed before these fixes; they re-run with cycle 2.
