# grok-4.20-0309-reasoning (grok-4.20-0309-reasoning) 46 s finish=stop usage in 17102 / out 530 usd~0.099 (upper-bound price)

**Findings**

No <critical> findings. All paths in the diff were examined line-by-line against the exact text of RULING 93, L-m, L-j, L-d, M12 and the supplied test fixtures.

No <high> findings. Every layout_block call (eligibility.py:32, package.py:48/59/71, spotlight.py:115/119, visual_pin.py:247) treats unmeasured, missing burned_in list, ticker, crawl, cut, covers_speaker or non-whole_16x9 as a blocking string; clean_visual and layout_ok never treat these as eligible. Old visual-1 records (no "burned_in" key) are rejected by layout_block:247 and force recompute (VERSION bumped to visual-2 at visual_pin.py:144, cache key changes). Sealed records from before the change omit the new key (sealed:260 uses "if k in rec") so pre-ruling-93 pins remain byte-identical until cache miss.

<medium> spotlight.py:89 (clean_visual): local `import visual_pin as VP` is inside the function while the module already binds VP at module level (evidenced by pre-existing `VP.hook_block(v)` at the updated line 114 and continued use at line 119). Harmless on every concrete visual dict in test_spotlight.py:433-447 and test_medley.py:372-391, but style deviates from smallest-diff intent (M1) and is redundant.

All other paths match the ruling verbatim:
- No channel-name hold remains (eligibility.py:21-24, layout_ok:25 returns only on channel_id; test_eligibility.py:289-296, test_select_by_id.py:505-520 now assert Bitcoin Magazine layout_eligible=True and only not_sentence_ready).
- Ticker (test_medley.py:369 TICKER dict) produces "ruling 93: a ticker" block before any pin or write (package.py:59, spotlight.py:118).
- Whole static lower_third/bug produces burned_in FLAG only, stays clean, reaches package (test_medley.py:384, clean_visual:90, flags:224).
- Protected preview outcome unchanged (Bitcoin Magazine clip still excluded, now solely by not_sentence_ready; selection locks/cut points for used clips untouched).
- G3/G10/G17c/L-b/L-c/L-g/L-k paths, canon, sentence_law, release_auth, visual-1 backward seals, and must-fail fixtures untouched by this diff.

**SHIP: yes**