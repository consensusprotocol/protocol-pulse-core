# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)

Build ledger_20261115_032027, written 2026-11-14 22:27 EST. 1 verdicts shadowed, 5 decisions compared, 2 differ (0 on the pin's clips); 0 not compared; 0 still running; shadow cost $0.0184 reported.

Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed (on the pin's clips, Grok would have stopped it).

| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |
|---|---|---|---|---|---|---|
| step_a | 933f9d33a8e345356177 | () | ('REFERENT_OUTSIDE',) | looser |  | heimdall:deepseek/deepseek-v4.1-flash |
| step_a | a49592a93a4a81a8d050 | ('NOT_OWN_SINCERE',) | () | stricter |  | heimdall:deepseek/deepseek-v4.1-flash |
