# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 26 s finish=stop usage in 13962 / out 306 usd~0.077 (upper-bound price)

**P0 findings:** None verifiable from diff.  
**P1 findings:** None verifiable from diff.  
**P2 findings:**  
- pipeline/package.py:29 (lineup_ok): extracts exactly the rules stated in lineup_for docstring (hook eligibility+G17a, clip eligibility, LY_CLIPS count, one-per-channel or repeat_ok, SHORT_CLIP_S last, crange, stand_alone_check); test at :334 confirms lineup_for outputs pass it.  
- pipeline/package.py:200 (build): weak now includes hook (COHERENCE_MIN=4 unchanged); swap_lineup:200-212 respects dropped/doomed via avoid, grows dropped on no-swap path, free excludes used+avoid → no re-judge/loop possible.  
- pipeline/package.py:158,191,220 (build): total counts every judged line-up across angles (while total < LINEUPS_PER_BUILD); search budget (over_budget) from t0 ends build, package_over from per-line clips-alone start ends only that line-up's writes; test at :281-287 verifies no dodge.  
- pipeline/package.py:172-182,208 (build+swap): swapped line-ups still route through full medley()→gates, supply_exception, no_voice, question_hook, write loop; nothing else altered.  
- tests/package/test_medley.py:308-354: all swap/lineup_ok/build behaviors in ruling 41 description are exercised with exact constants and outcomes.  

SHIP: yes