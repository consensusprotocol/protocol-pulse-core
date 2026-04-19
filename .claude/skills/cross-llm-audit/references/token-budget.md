# Token Budget and Cost Control

Authority: PIPELINE_LAWS.md "LAW: QWEN FIRST (COST LAW)"

## Budget Limits

| Limit | Amount | Action |
|-------|--------|--------|
| Soft limit | $2 per improvement cycle | Log warning, continue execution |
| Hard limit | $5 per improvement cycle | Pause execution, Telegram alert to PBX |

An "improvement cycle" = one full audit run (Qwen + Cycle 1 + optional Cycle 2).

## Cost Breakdown (Typical)

| Component | Cost | Notes |
|-----------|------|-------|
| Qwen pre-filter | $0.00 | Local Ollama, always free |
| Gemini 2.5 Pro (Cycle 1) | ~$0.10-0.20 | 120-line payload |
| GPT-4o (Cycle 1) | ~$0.10-0.20 | 120-line payload |
| Grok-3 (Cycle 1) | ~$0.05-0.15 | 120-line payload |
| Claude synthesis (Cycle 1) | ~$0.05-0.10 | sonnet for synthesis |
| Cycle 2 (if needed) | ~$0.30-0.65 | Same models, cross-exam |
| Total (1-cycle) | ~$0.30-0.65 | Under soft limit |
| Total (2-cycle) | ~$0.60-1.30 | Under soft limit |

## Why Full File Sends Are Banned

Sending a 2000-line file to 3 external LLMs:
- Input tokens: ~8000 per model x 3 = 24000 tokens
- Cost: ~$3-8 per cycle
- Two cycles: ~$8-20 total

With Qwen pre-filter (120-line payload):
- Input tokens: ~500 per model x 3 = 1500 tokens
- Cost: ~$0.30-0.60 per cycle
- Two cycles: ~$0.60-1.30 total

Savings: 80-90% reduction in external API costs.

## Telegram Alert Integration

When hard limit ($5) is reached:
1. Execution pauses (does not abort)
2. Telegram message sent to PBX with:
   - Feature name
   - Current spend total
   - Number of cycles completed
   - Remaining action items
3. PBX decides: continue (raise limit) or stop

Telegram bot: uses existing Protocol Pulse Telegram integration
via services/telegram_alerts.py (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID in .env).

## FEATURE_MAP Audit Registry

Every feature that undergoes audit must be registered in
utils/cross_llm_audit.py FEATURE_MAP dict:

```python
FEATURE_MAP = {
    "feature-name": ("GOVERNING_GOSPEL.md", "branch-name"),
    ...
}
```

The FEATURE_MAP provides:
- Which gospel/law doc governs the feature
- Which branch contains the code to audit
- Enables audit history tracking per feature

For features already merged to main, use EXPLICIT_FILES dict
to specify which files to include in the audit package.

## Cost Tracking

Each audit run logs:
- Start time, end time
- Models called, tokens consumed (estimated)
- Total cost (estimated)
- Feature name and cycle number

Logs saved to: logs/audits/{feature}_{timestamp}.json
This enables cost trending over time.

## Budget Override

PBX can override the hard limit for critical audits by setting:
```bash
export AUDIT_BUDGET_OVERRIDE=10  # raises hard limit to $10
```

This is for exceptional cases only (major pipeline rewrites,
security-critical fixes). Default limits apply to all other audits.
