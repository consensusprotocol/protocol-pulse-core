# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 54 s finish=stop usage in 19400 / out 414 usd~0.107 (upper-bound price)

**Findings**

No P0 or P1 findings verifiable from the diff.

P2: pipeline/speakers.py:217 (in check())
Concrete failure scenario: model returns `{"people": [{"name":"Jeff Booth","role":"guest","line":"title: Jeff Booth Warning"}], "speaker":{"name":"Jeff Booth","basis":"When I wrote The Price of Tomorrow","why":"x"}}` with a basis that is only in source_lines() and not in clip/around -> check() correctly sets name=unknown (per test at test_speakers.py:690) but the "people" list still carries the title-derived person; a downstream tagger using only "people" could credit a title-only name that the speaker logic itself rejected.

P2: pipeline/package_pin.py:72 (speaker_problems call) + speakers.py:232 (base dict)
Concrete failure scenario: attribute() hits ProviderError before any router.call (e.g. missing env var for a chain member) -> returns dict with measured=False, name=unknown, why=...; speaker_problems accepts it (no "named without line/basis" path taken) and to_pin succeeds, so a completely unmeasured segment reaches the sealed pin (violates "nothing measured is never a pass" but is allowed by the explicit speaker_problems logic shown).

P2: tests/package/proof_batch.py:378 (and equivalent calls at proof_ly.py:484, proof_ledger.py:464)
Concrete failure scenario: package_batch_{tag}.json is written (line 380) *before* SP.attribute_package, then overwritten; a concurrent process or failed run reading the intermediate JSON sees segments without speaker records, yet the test fixtures in test_medley.py:514 and test_angles.py:496 assume the final form is always present.

**Verdict**
SHIP: yes with conditions (must add speaker record before any intermediate JSON write; tighten measured=False handling in speaker_problems to match L-m/L-j; confirm production package flow calls attribute_package before any seal)