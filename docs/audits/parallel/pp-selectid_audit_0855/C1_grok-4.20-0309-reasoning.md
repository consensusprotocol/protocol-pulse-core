# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 16 s finish=stop usage in 6323 / out 134 usd~0.035 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none** (The three limit strings now emitted by placement() exactly match the three cases described in the new docstring and in the updated PLACEMENT LIMITS sentence. The added test at test_medley.py:57-62 exercises the precise 08:46 shape that previously failed (short hook + short last clip) and confirms both placement() and lineup_for produce the expected order. No other logic, prompt text, or call sites are altered in the diff. The updated code is consistent with the Ruling 54 description supplied in the audit package.)

**SHIP: yes**