# C2 CONSENSUS — pp-selectid audit 20261116_0826 (RULING 119 (3): glm out of every chain)

Seats (Heimdall only): qwen3.8-27b, gemma-4-31b-it, mimo-v2.6-flash-rl. SEATS ANSWERED: 2 of 3 (mimo cut off again, now at
32,000 tokens, no answer). qwen P1_OR_WORSE 0; gemma 0. The audit $0.0139 of Heimdall, not capped. No P1 in either cycle;
no third cycle.

qwen's two headings tagged [P1] are checks it states and answers itself, with its count at 0: (a) the writer-family skip
is intact (exclusion deepseek -> Grok: with deepseek writing and Grok down, no leg, fail closed; fidelity qwen -> Grok:
qwen is another family, picked); (b) "is local_judge:gemma3:27b defined": yes, it is a back-end of
pipeline/model_providers.json (unchanged; ruling 102's last resort), distinct from local:gemma3:27b.
P2 noted: "the 'today' routing's coverage": the test asserts today's step C and coherence lists and glm in none of
today's lists. The JSON comma (C1's P3): syntax only.

Suites: all 40 files, 816 tests. Mutations C1-C3: 3 of 3 killed after a control run. FINAL.diff at landing.
