# Ruling 86: the shadow's side-by-side (Heimdall decided; Grok asked the same prompts)

Build ledger_20261114_230148, written 2026-11-14 18:23 EST. 9 verdicts shadowed, 11 decisions compared, 3 differ (2 on the pin's clips); 0 not compared; 0 still running; shadow cost $0.0685 reported; the pin WOULD NOT have sealed under Grok.

Heimdall stricter: Heimdall failed what Grok passed. Heimdall looser: Heimdall passed what Grok failed (on the pin's clips, Grok would have stopped it).

| type | unit | Heimdall | Grok | compare | on the pin | Heimdall model |
|---|---|---|---|---|---|---|
| exclusion | moment | False | True | stricter |  | heimdall:deepseek/deepseek-v4.1-flash |
| fidelity | closing | True | False | looser | yes | heimdall:qwen/qwen3.8-27b |
| fidelity | comment | True | False | looser | yes | heimdall:qwen/qwen3.8-27b |
