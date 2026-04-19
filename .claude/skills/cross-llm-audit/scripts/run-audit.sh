#!/usr/bin/env bash
set -euo pipefail

# PROTOCOL PULSE — Cross-LLM Audit Runner
# Wraps utils/cross_llm_audit.py with env validation and logging.
# Usage: bash run-audit.sh FEATURE_NAME
# Exit codes: 0 = consensus reached, 1 = disagreement, 2 = env failure

FEATURE="${1:-}"

if [[ -z "$FEATURE" ]]; then
    echo "ERROR: Feature name required."
    echo "Usage: bash $0 FEATURE_NAME"
    echo "Example: bash $0 fix-freeze-frames"
    exit 2
fi

# --- Validate Ollama ---
echo "Checking Ollama at localhost:11434..."
if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "FAIL: Ollama not reachable at localhost:11434"
    echo "Start Ollama: systemctl start ollama"
    exit 2
fi

QWEN_AVAILABLE=$(curl -sf http://localhost:11434/api/tags | python3 -c "
import sys, json
tags = json.load(sys.stdin)
models = [m['name'] for m in tags.get('models', [])]
print('yes' if any('qwen' in m.lower() for m in models) else 'no')
" 2>/dev/null || echo "no")

if [[ "$QWEN_AVAILABLE" != "yes" ]]; then
    echo "FAIL: Qwen3 model not found in Ollama"
    echo "Pull it: ollama pull qwen3"
    exit 2
fi
echo "OK: Ollama + Qwen3 available"

# --- Validate API keys ---
MISSING_KEYS=""
for KEY in OPENAI_API_KEY GEMINI_API_KEY XAI_API_KEY; do
    if [[ -z "${!KEY:-}" ]]; then
        MISSING_KEYS="$MISSING_KEYS $KEY"
    fi
done

if [[ -n "$MISSING_KEYS" ]]; then
    echo "FAIL: Missing API keys:$MISSING_KEYS"
    echo "Add them to ~/protocol_pulse/.env"
    exit 2
fi
echo "OK: All API keys present"

# --- Prepare log directory ---
LOG_DIR="$HOME/protocol_pulse/logs/audits"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="${LOG_DIR}/${FEATURE}_${TIMESTAMP}.json"

# --- Run the audit ---
echo ""
echo "=========================================="
echo "CROSS-LLM AUDIT: $FEATURE"
echo "Log: $LOG_FILE"
echo "=========================================="
echo ""

cd "$HOME/protocol_pulse"

if python3 utils/cross_llm_audit.py --feature "$FEATURE" 2>&1 | tee "$LOG_FILE"; then
    echo ""
    echo "CONSENSUS REACHED for $FEATURE"
    echo "Results: $LOG_FILE"
    exit 0
else
    PYTHON_EXIT=$?
    echo ""
    echo "AUDIT COMPLETED WITH DISAGREEMENT (exit $PYTHON_EXIT)"
    echo "Results: $LOG_FILE"
    exit 1
fi
