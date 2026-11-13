# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 22 s finish=stop usage in 7716 / out 151 usd~0.042 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none verifiable from diff** (cost() exclusively selects one basis; bool/missing/None rep routes to "estimate" via explicit `isinstance(..., (int,float)) and not isinstance(..., bool)` at visual_pin.py:44; package.py:20-24 only mutates the split counters on exact string match; no gate, seal, or cache-key mutation present—usd/usd_basis explicitly stripped before cache write at visual_pin.py:76 and omitted from sealed test at test_visual_pin.py:139; all paths in modified visual_for and build see() carry a basis; test coverage added for the three cases).  

**SHIP: yes**