# Batch 100 (ruling 131 (A)+(B)), cycle 2 (break-it): consensus

Panel: Heimdall only, one seat per invocation at `HEIMDALL_AUDIT_EFFORT=medium`. Each seat was asked for a CONCRETE
input that breaks B1-B7.

| Seat | Model | Verdict | Findings | Completion tokens | Trace |
|---|---|---|---|---|---|
| gptoss | openai/gpt-oss-20b | PASS | 0 | 14,301 | Each of B1-B7 is traced against the code: took needs run_ok and dist >= 3; held pairs raise; sealed only after the re-lock; norm unchanged. |
| qwen27b | qwen27b | no JSON verdict | 0 | 32,768 (cap; finish "length") | 104k characters of reasoning. B1-B7 are each traced and judged "protected" / "not a defect". It wrote "I'm going to report PASS. I cannot find a concrete defect that I can prove with a specific input traced through the code", then hit the cap during extra edge checks (replace-op distances 0/2/3; currency_format kept through (A)), all judged correct. |

**Consensus:** no finding in either cycle. Nothing to implement.

**Recorded, not hidden:**
- qwen27b's cycle-2 answer was cut at the token cap, so its only verdict is the one stated in its reasoning.
- gpt-oss's cycle-1 tail repeats one line.
