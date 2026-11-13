# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 65 s finish=stop usage in 15596 / out 577 usd~0.092 (upper-bound price)

**P0: none verifiable from diff**  
**P1: none verifiable from diff**  
**P2: pipeline/attest.py:122 (attested_text word_at + words)**  
Concrete scenario: an insert opcode with lo == hi on the pin token side that falls inside a multi-token approved word (e.g. "that'swhy" tokenized as one canon token but split by run decode) would hit the "if lo < n and not wmap[lo][1]" guard and raise ValueError("a difference splits a word..."). The test suite never exercises a split inside a single approved surface word; the real held-pin case uses whole-word boundaries only. Behavior matches the documented "Raises ValueError when a difference does not fall on whole words (fail closed)", but the guard's exact token-length assumption is not exercised on a replace-inside-punctuated-word case also present in the fixture texts.  

**P2: tests/package/reseal_attested.py:253**  
Concrete scenario: build_rec["tried"][0]["attempts"][0]["second_pass"] contains a replayed=True reading that exactly matches start/end/VID. The code explicitly rejects it ("a replayed reading is never evidence"), matching the ruling's "live, not replayed" requirement and the test "test_it_refuses_without_both_recognisers_or_on_another_pin". The refusal path writes nothing (exit 2), satisfying fail-closed. However, the lookup uses round(..., 3) on floats; the diff supplies no proof that every prior build record uses identical 3-decimal rounding, so a future float drift would silently skip the live reading and refuse a valid reseal.  

**P2: tests/package/test_speakers.py:472**  
Concrete scenario: any pin carrying "btc_screen" (the 13:38 pin committed 13:45) previously failed the "every earlier pin still recomputes" loop because seal() was called without the final argument. The added mp.get("btc_screen") makes the test match the integrator's check_pin_only call site and restores the "earlier pins unchanged" guarantee after SEALED_LATER grew. Pure test-only change; no runtime effect on pins.  

All other paths (carry_class never returns carry for critical tokens, attested_text produces canon-equivalent output, reads() requires both recognisers to agree on run decode at every diff + neighbors, quotes() blocks any line containing a changed span, seal compatibility for pre-attested pins, nothing written on any refusal, attested record sealed inside package_sha256) match the ruling text, the held-clip fixture, L-j byte-exact authorisation, L-k canonical-form requirement, selection-lock preservation, and the 12 passing suites. K1–K5 readings above are identical to the ruling.  

**SHIP: yes**