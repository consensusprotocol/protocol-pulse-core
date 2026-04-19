# Cycle 1: Parallel LLM Dispatch

Authority: CROSS_LLM_AUDIT_LAW.md Phase 2
Implementation: utils/cross_llm_audit.py fire_all_llms()

## Overview

Three external LLMs review the same code package simultaneously
via threaded parallel dispatch. Each model gets the IDENTICAL
package. No model sees what the others said until Cycle 2.

## Models

| Model | Strength | API |
|-------|----------|-----|
| Gemini 2.5 Pro | Architecture, structural analysis | google-generativeai |
| GPT-4o | Frontend, UX critique, completeness | openai |
| Grok-3 | API verification, current info, contrarian | xai (OpenAI-compatible) |

## Prompt Template

The audit package follows the template in CROSS_LLM_AUDIT_LAW.md:

```
# PROTOCOL PULSE -- CODE AUDIT PACKAGE
# Feature: [name]
# Branch: feature/[branch]
# Auditors: You are [Model] -- other models will also review
# Purpose: Pre-merge quality gate

## WHAT THIS FEATURE DOES
[2-paragraph description]

## THE LAWS THIS CODE MUST OBEY
[Pasted from governing gospel/law doc]

## THE CODE
[Qwen's pre-filtered payload -- max 120 lines per file excerpt]

## WHAT WE NEED FROM YOU
[9-section review: Correctness, Law Compliance, Security,
 Frontend Quality, Backend Quality, World-Class Gap,
 Scoring 0-100, Priority Action Plan, One Thing]
```

## Payload Size Limits

- Max 120 lines of pre-filtered code per external LLM call
- Full file sends are BANNED (Qwen pre-filters first)
- Each model's output truncated to 8000 chars for consensus synthesis
- Total package should stay under 4000 tokens to control costs

## Parallel Dispatch (fire_all_llms)

```python
# All 3 fire simultaneously in threads
threads = [
    threading.Thread(target=call_gemini, args=(prompt, results, errors)),
    threading.Thread(target=call_gpt4o,  args=(prompt, results, errors)),
    threading.Thread(target=call_grok,   args=(prompt, results, errors)),
]
for t in threads: t.start()
for t in threads: t.join()
```

If one model fails, the other two results still proceed.
Failures are logged in errors dict and noted in consensus.

## Anti-Hallucination

Every prompt MUST include:
"Only report issues you can verify from the code/data provided. Do not speculate."

This prevents models from inventing issues in code they cannot see.

## Output Storage

Results saved to ~/protocol_pulse/docs/audits/{feature}/:
- C1_GEMINI.md
- C1_GPT4O.md
- C1_GROK.md
- C1_CONSENSUS.md (Claude synthesis)

## Required API Keys

All must be set in ~/protocol_pulse/.env:
- GEMINI_API_KEY
- OPENAI_API_KEY
- XAI_API_KEY
- ANTHROPIC_API_KEY (for Claude synthesis)

NEVER paste Gemini keys in Claude.ai chat -- Google scans and
invalidates instantly. Add via SSH to Ultron only.
