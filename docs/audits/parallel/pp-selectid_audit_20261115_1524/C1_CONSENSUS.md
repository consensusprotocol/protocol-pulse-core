# C1 CONSENSUS — pp-selectid audit 20261115_1524 (STATE Q2: the hook job reads an answer whose only extra is trailing closing braces; the hook115 spend read)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of its 16,000 output tokens with no answer
(finish=length), so the driver asked Grok (0). Cycle 1: $0.0379 vendor-reported. No P1.

Grok [P2] "a model-specific tolerance is a maintenance burden; the long-term fix belongs at the provider / output
layer". Noted: it is scoped to the hook job only (every other verdict keeps json.loads), it reads nothing but a
complete object followed by closing braces, the contract's own checks still decide, and every rating read this way
says so in its record ("answer_note"), so its frequency is counted from the records. Ruling 106's default (Q2, 15:24
ET) asked for exactly this; a change at the provider layer would touch every verdict and is not ordered.

No change in this pass. Tests as in the QUESTION (281 pass; 4 of 4 mutations killed).
