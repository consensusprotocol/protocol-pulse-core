# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 10 s finish=stop usage in 6333 / out 232 usd~0.037 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: none** (from diff only)

Verified from diff:  
- RULES and DECODER constants updated exactly to the integrator's ruling-73 values ("ruling 17 + ruling 72 + ruling 73" and "8a101f222598"); docstring updated with the stated rationale and full new decoder SHA.  
- All three updated test assertions match the new decoder in filenames.  
- Explicit test added that an entry carrying the *old* rules string (even with a later timestamp) is ignored and does not change the returned outcome.  
- Explicit test added that a ruling-73 "the render cannot cut this span" hold produces verdict="hold", overall ok=False, and the reason text is propagated; a sibling entry carrying a "cut" object produces verdict="pass".  
- No other logic, constants, paths, or behavior altered in the visible diff. All 15 suites reported OK.

The diff implements exactly the checked requirements (old decoder/rules never read; ruling-73 hold cannot pass; nothing else changes).

**SHIP: yes**