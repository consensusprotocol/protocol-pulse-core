# Audit 20261114_1835 (ruling 104's directive path), cycle 3: consensus

- grok-4.20: SHIP yes. No P0, P1 or P2.
- qwen3.8-27b: SHIP yes. No P0 or P1.
- glm-5.3-flash: yes with two conditions, both documentation, recorded here.

## glm's documentation conditions

1. **A pool admission is not a pin.** The pin re-reads the spotlights record and the ET day at pin time
   (proof_ledger.spot_place). A build that crosses midnight, or a record written between the pool and the pin, can
   still refuse the pin. This is unchanged, and lawful.
2. **Two directive rows for one parent: the last wins** (directives() builds a dict). The builder writes the file,
   one row per parent. The build's RULING 104 line names the variant's ending, so a wrong "ends" is visible before
   anything seals.

All three confirm (f) and (g): nothing raises out of the pin's try or the pool, and nothing changes for a well-formed
directive or for any moment without one. FINAL.diff = the diff cycle 3 reviewed. 16 of 16 mutations killed.
