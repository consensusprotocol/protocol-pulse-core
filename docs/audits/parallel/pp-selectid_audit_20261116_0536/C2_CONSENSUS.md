# C2 CONSENSUS — pp-selectid audit 20261116_0536 (RULING 118: the day cap, the guard before the free panel)

Seats (Heimdall only, no Grok seat): qwen3.8-27b, deepseek-v4.1-flash, gemma-4-31b-it. SEATS ANSWERED: 2 of 3 (deepseek
cut off at 32,000 tokens again, no answer). qwen P1_OR_WORSE 0; gemma 0. Cycle 2: $0.0094 of Heimdall; the audit $0.0200
vendor-reported, not capped (ruling 118 (b)). No P1 in either cycle; no third cycle. Both seats read cycle 1's
refutation of gemma's P0 (the changed line is in _reserve, where `b` is the parameter) and agree.

P2s noted, not changed:
- qwen "LY_STOP_USD equals LY_LIMIT_USD ($1.00): at the cap no build starts": intended until the free panel takes a
  verdict type: today every verdict is an outside call, so a build at the cap could judge nothing; once the panel
  decides a type, a build at the cap must still run its free path, and the stop moves then (its own audit).
- the unreported estimate counted whole (qwen, gemma: "the correct fail-closed reading"): kept.
- the first day's file keyed to 20261115 (gemma C1): kept, as C1 says.

NEXT AUDITS: deepseek has given no answer on three long audit prompts in a row (32,000 tokens spent reasoning); the next
audits seat qwen, gemma and mimo (xiaomi/mimo-v2.6-flash-rl, which answered all six pilot prompts of the panel).

Suites: all 40 files, 816 tests (813 + 3). Mutations G1-G9: 9 of 9 killed after a control run. FINAL.diff at landing.
