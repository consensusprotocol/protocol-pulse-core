# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 39 s finish=stop usage in 9735 / out 488 usd~0.061 (upper-bound price)

**P2: pipeline/package_pin.py:89** (trim_problems)  
Concrete scenario: segments=[{"trimmed_leading":"But", "untrimmed_start":0.0, "scorer_pending":True}, {"trimmed_leading":"So", "untrimmed_start":0.0, "scorer_pending":True}]. The n>TRIMMED_PER_PIN_MAX check fires first and the per-segment scorer_pending validation also fires; both messages are collected. Matches the ruling-49(b) intent but the diff contains no path that ever raises the limit after a validate affirmation (the "integrator says when" clause is mentioned only in comments).

**P2: pipeline/package.py:31** (the **{... "scorer_pending": True ...} dict in _package)  
Concrete scenario: a trimmed segment is emitted with scorer_pending=True even if TRIM_SCORER_PENDING were later toggled back to False in the same Python process. The constant only controls stand_alone_check behavior; the emitted pin key is hard-coded. (Test temporarily flips the constant and confirms the check side, but the emission side is unconditional after the constant change at line 14.)

No other violations of the requested properties are present in the diff:  
- trim_problems explicitly refuses a trimmed clip lacking scorer_pending: true (lines 99-101) and refuses scorer_pending on any untrimmed clip (lines 96-97).  
- to_pin copies the key only when present (line 110); SEALED_LATER lists it but older pins without the key therefore hash identically.  
- lineup_ok, lineup_for and the build candidate loop all reject > TRIMMED_PER_LINEUP_MAX trimmed clips (lines 41, 50, 59); test_medley.py:158-160 confirms lineup_for never returns two and that the two MAX constants are kept equal.  
- No code path claims the scorer has affirmed anything; the STAND_ALONE row and scorer_pending list explicitly say "PENDING AT THE RENDER".  
- Nothing in the diff touches the renderer, selector, GPU usage outside the stated Ollama path, or any governing law outside ruling 49.

SHIP: yes with conditions (integrator must document how/when the TRIMMED_PER_*_MAX limit is raised post-affirmation; the pending emission should be guarded by the constant rather than hard-coded True).