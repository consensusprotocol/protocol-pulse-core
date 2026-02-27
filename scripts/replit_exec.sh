#!/usr/bin/env bash
# replit_exec.sh — Execute commands on Replit from Ultron via HTTP relay
#
# Usage:
#   ./scripts/replit_exec.sh "python -m services.video_engine.daily_driver --dry-run --force"
#   ./scripts/replit_exec.sh "git pull origin main"
#   REPLIT_URL=https://my-app.replit.app ./scripts/replit_exec.sh "pwd"
#
# Requires: REPLIT_URL and ADMIN_EXEC_TOKEN in .env or environment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load .env if present
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

REPLIT_URL="${REPLIT_URL:-${PUBLIC_HUB_URL:-}}"
TOKEN="${ADMIN_EXEC_TOKEN:-}"

if [[ -z "$REPLIT_URL" ]]; then
    echo "ERROR: REPLIT_URL not set. Set in .env or environment." >&2
    exit 1
fi

if [[ -z "$TOKEN" ]]; then
    echo "ERROR: ADMIN_EXEC_TOKEN not set. Set in .env or environment." >&2
    exit 1
fi

CMD="${1:?Usage: replit_exec.sh \"command\"}"

# Strip trailing slash from URL
REPLIT_URL="${REPLIT_URL%/}"

echo ">>> Executing on Replit: $CMD"
echo ">>> Target: $REPLIT_URL/api/admin/exec"
echo "---"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "$REPLIT_URL/api/admin/exec" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg token "$TOKEN" --arg cmd "$CMD" '{token: $token, cmd: $cmd}')" \
    --connect-timeout 10 \
    --max-time 130)

HTTP_CODE=$(echo "$RESPONSE" | tail -1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [[ "$HTTP_CODE" -ne 200 ]]; then
    echo "ERROR: HTTP $HTTP_CODE" >&2
    echo "$BODY" >&2
    exit 1
fi

# Extract stdout/stderr from JSON
STDOUT=$(echo "$BODY" | jq -r '.stdout // empty')
STDERR=$(echo "$BODY" | jq -r '.stderr // empty')
RC=$(echo "$BODY" | jq -r '.returncode // "1"')

if [[ -n "$STDOUT" ]]; then
    echo "$STDOUT"
fi

if [[ -n "$STDERR" ]]; then
    echo "STDERR:" >&2
    echo "$STDERR" >&2
fi

exit "$RC"
