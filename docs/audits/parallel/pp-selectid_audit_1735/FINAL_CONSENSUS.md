# pp-selectid audit 1735 (ruling 66 amended + 17:20): FINAL consensus (cycle 2)

(Started 17:22 ET; the label 1735 was typed, not read from the clock.)

**Cycle 2:** no P0 and no P1 from any reviewer.
- grok: "SHIP: yes with conditions".
- qwen: "SHIP: yes".
- glm: "Production ready: yes, with conditions".

All three verify the cycle-1 fix (an out-of-contract reply's model is still avoided by the second write). They also
verify:
- the loop's bound (WRITES full writes + 2 takeaway-alone writes; every iteration spends one or breaks);
- that no gate accepts more than before;
- the merge precondition;
- that ruling 65's caption path and prompts are byte-identical;
- that no judge is touched.

No code change after cycle 1.

## The conditions, checked in code (no change needed)

| # | condition | evidence |
|---|---|---|
| 1 | glm N6: takeaway_alone_gates' context check must match paid_gates' | Both call `CI.check_contexts(router, pk, CI.contexts_from_sources(pk, sources, now), writers_v, 7, a_use, writers_f, True)`, argument for argument (package.py paid_gates; takeaway_alone_gates). |
| 2 | glm N8: the 240-character cap vs the word budget | takeaway_budget caps `hi` at `min(LY_TAKEAWAY_MAX_WORDS, ...)`, and house style's TAKEAWAY_MAX_WORDS is 20. At most 20 words is well under 240 characters, so the cap never refuses a budget-sized takeaway. |
| 3 | grok P2: avoid_model passed as a set | providers._as_set takes `set, frozenset, list, tuple`; _skip tests `name in am`. |
| 4 | grok: real-backend tests in CI; monitor cost | No CI runs real back-ends here (spend cap; recorded replies serve re-runs). The takeaway-alone writes are logged per build ("the takeaway alone" in package.log) and priced in the build's spend line. |
| 5 | qwen N14 / glm: a provider failure with no reply leaves the model unknown | Agreed vacuous: no reply means no model wrote a line. The router's own fail-over picks the chain's next. |

## Recorded P2s (no change)

- glm/grok: RUNTIME on "-" may reach the writer's prompt when the bridge is the cause. When no takeaway length lands
  it, the budget is None and nothing is written; otherwise the takeaway's length CAN land it.
- qwen: the dedup compares truncated details. Prompt length only.

## Cost of this audit

Upper-bound price estimates from each reply's usage, not on the ruling-48 ledger:

| cycle | grok | qwen | glm |
|---|---|---|---|
| 1 | $0.099 | $0.101 | $0.168 |
| 2 | $0.134 | $0.114 | $0.156 |

About $0.77 in all.
