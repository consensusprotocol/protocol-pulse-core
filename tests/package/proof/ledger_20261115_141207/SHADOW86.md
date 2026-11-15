# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)

Build ledger_20261115_141207, written 2026-11-15 09:24 EST. 7 verdicts shadowed, 15 decisions compared, 2 differ (0 on the pin's clips); 0 not compared; 0 still running; shadow cost $0.1084 reported.

Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed (on the pin's clips, Grok would have stopped it).

| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |
|---|---|---|---|---|---|---|
| step_a | 9828eed5df8effcc4bdd | () | ('REFERENT_OUTSIDE', 'STALE_TIME') | looser |  | heimdall:z-ai/glm-5.3-flash |
| step_a | d6fa1390934d5c1aa62a~trim | () | ('REFERENT_OUTSIDE',) | looser |  | heimdall:z-ai/glm-5.3-flash |
