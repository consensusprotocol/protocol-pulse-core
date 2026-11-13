# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 44 s finish=stop usage in 5913 / out 113 usd~0.032 (upper-bound price)

**P0/P1/P2 findings:** none verifiable from diff  
(returns {} on every failure path (except + if-why); except block cannot raise (stage/sc init, isinstance guard on sc.get, all values from params or caught types); record keys match added tests (stage in why, path/render_scorer_sha always on error, scorer fields only when dict read); non-ASCII test confirms identical sha256(utf8) and affirmed_verdict acceptance; split assignments + stage var exactly as described for partial diagnostics).  

**SHIP: yes**