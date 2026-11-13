# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 32 s finish=stop usage in 15833 / out 330 usd~0.087 (upper-bound price)

**P0: none**  
**P1: none**  
**P2: pipeline/package.py:199** (the final "class" ternary can only be verified to produce "line" when medley_ok+attempts+not-relined are all true on the candidate's tried entry and no package/budget_stop occurred; the exact definition of "attempts" and interaction with rewrite_alone/relined= is outside this diff and must be confirmed against the full medley path).  
**P2: tests/package/proof_ledger.py:290** (when --from-candidate is used the registry outcome is written but "candidate_tries" and "registry":True are never added to the record; the non-candidate path always adds them).  
**P2: pipeline/candidates.py:101** (_at() + timedelta assumes every "until" string is a valid ISO timestamp with Z or offset; malformed legacy registry entries would raise at due() time).  

All other aspects (state machine exactly matching the 14:02 "resting 6 h then one fresh-write try → closed", due() newest-first snapshot preventing double-tries, shared 8-judged-lineup budget via run_due → remaining build, read-before-write + atomic registry save, write_seed=1000 isolating fresh writes while preserving verdict seed, seed() deduplication, candidate vs non-candidate paths, test coverage of the four outcome classes) verify cleanly from the diff. Real-data seeding behavior (old candidates closed as "clip" by current load_candidate) also matches K2.  

**SHIP: yes**