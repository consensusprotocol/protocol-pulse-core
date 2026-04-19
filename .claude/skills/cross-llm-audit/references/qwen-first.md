# Qwen-First Pre-Filter

Authority: PIPELINE_LAWS.md "LAW: QWEN FIRST (COST LAW)"

## Why Qwen First

Qwen3 runs locally on Ollama (localhost:11434) using cuda:2/cuda:3.
Cost per call: $0. No API key required. No rate limits.

External LLMs (Gemini, GPT-4o, Grok) cost money per token.
Qwen pre-filters so externals receive only surgical payloads,
not full file dumps.

## Ollama Setup

Qwen3 must be available at localhost:11434.
Verify with:
```bash
curl -s http://localhost:11434/api/tags | python3 -c "
import sys, json
tags = json.load(sys.stdin)
models = [m['name'] for m in tags.get('models', [])]
print('Qwen3 available' if any('qwen' in m.lower() for m in models) else 'Qwen3 NOT FOUND')
"
```

Ollama models auto-unload after 5 minutes idle (KEEP_ALIVE=5m).
First call may take 10-20s for model load.

## GPU Isolation

- cuda:0 = pipeline (daily_producer.py)
- cuda:1 = avatar server
- cuda:2/3 = Qwen3 via Ollama

NEVER run Qwen on cuda:0 or cuda:1. This is enforced by
CUDA_VISIBLE_DEVICES in load_env().

## Pre-Filter Rules

1. Qwen reads ALL modified/new files for the feature
2. Qwen identifies candidate issues with confidence scores
3. Only findings with specific file:line citations pass the filter
4. Vague observations ("could be improved") are rejected
5. Maximum 120 lines of pre-filtered payload sent to external LLMs

## 120-Line Payload Cap

External LLMs receive ONLY Qwen's pre-filtered findings.
Full file sends to external LLMs are BANNED.

The payload contains:
- File path and relevant function/class
- Specific line numbers with code snippets
- Qwen's assessment and confidence score
- The exact question for the external LLM to answer

If Qwen's findings exceed 120 lines, prioritize by severity:
CRITICAL first, then HIGH, then MEDIUM. Drop LOW entirely.

## Confidence Threshold

If Qwen confidence >= 0.85 AND no external LLM disagrees from
a previous cycle: implement the fix without external API calls.

This saves money on clear-cut issues like typos, missing imports,
or obvious logic errors that Qwen can identify with high certainty.

## Cost Rationale

Typical audit costs:
- Qwen pre-filter: $0 (local)
- 3 external LLMs with 120-line payload: ~$0.30-0.60 per cycle
- Claude synthesis: ~$0.10 per cycle
- Full 2-cycle audit: ~$0.80-1.50 total

Without Qwen pre-filter (sending full files):
- 3 external LLMs with 2000+ line payloads: ~$3-8 per cycle
- Full 2-cycle audit: ~$8-20 total

Qwen saves 80-90% on external LLM costs.
