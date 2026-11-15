# C2 CONSENSUS — pp-selectid audit 20261115_1524 (STATE Q2: trailing closing braces; the hook115 spend read)

Reviewers: qwen3.8-27b (P1_OR_WORSE: 0); deepseek-v4.1-flash ran out of tokens again (finish=length, no answer), so
Grok was asked (0). Cycle 2: $0.0234; the audit $0.0613 vendor-reported. No P1 in either cycle; no third cycle.

P2s noted, not changed:
- Grok "hook_answer is called twice on a read answer (in parse, and again for the record's count)": both calls read
  the same text the same way (a pure function of it), so the count is the parse's; the second parse is a few
  microseconds on a ~200-character answer.
- Grok "the strip happens before raw_decode": the offset is taken on the stripped text and the count of braces on
  its rest, both from the same string: consistent.
- qwen / Grok "a provider-layer fix would be better long term": the record's answer_note counts every answer read
  this way, so the rate is visible; a change at the provider layer would touch every verdict and is not ordered.

FINAL DIFF: FINAL.diff (written at landing).
