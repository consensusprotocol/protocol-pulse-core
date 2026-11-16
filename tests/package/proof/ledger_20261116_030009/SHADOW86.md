# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)

Build ledger_20261116_030009, written 2026-11-15 22:08 EST. 1 verdicts shadowed, 2 decisions compared, 2 differ (0 on the pin's clips); 0 not compared; 0 still running; shadow cost $0.0070 reported.

Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed (on the pin's clips, Grok would have stopped it).

| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |
|---|---|---|---|---|---|---|
| step_a | 7b106fda94a4c0dd7562 | ('NOT_OWN_SINCERE',) | () | stricter |  | heimdall:deepseek/deepseek-v4.1-flash |
| step_a | 7b106fda94a4c0dd7562~trim | ('NOT_OWN_SINCERE',) | () | stricter |  | heimdall:deepseek/deepseek-v4.1-flash |
