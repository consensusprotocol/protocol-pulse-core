#!/bin/bash
# SYSTEM 2: Stable Branch Promotion Gate
# Only promotes main → render-stable if the new grade beats the current best.
# Usage: bash promote_to_stable.sh <grade_score_integer>

set -euo pipefail

BASE="/home/ultron/protocol_pulse"
BEST_GRADE_FILE="$BASE/logs/best_grade.json"
LESSONS_FILE="$BASE/PIPELINE_LESSONS.md"

if [ $# -lt 1 ]; then
    echo "Usage: bash promote_to_stable.sh <grade_score>"
    echo "  grade_score: integer 0-100"
    exit 1
fi

NEW_SCORE="$1"

# Validate input is an integer
if ! [[ "$NEW_SCORE" =~ ^[0-9]+$ ]]; then
    echo "ERROR: grade score must be an integer, got: $NEW_SCORE"
    exit 1
fi

# Read current best
if [ -f "$BEST_GRADE_FILE" ]; then
    BEST=$(python3 -c "import json; print(json.load(open('$BEST_GRADE_FILE')).get('score', 0))" 2>/dev/null || echo "0")
else
    BEST=0
    mkdir -p "$BASE/logs"
    echo '{"score": 0, "promoted_at": "never"}' > "$BEST_GRADE_FILE"
fi

echo "Current best: $BEST | New score: $NEW_SCORE"

# Check if new score beats current best
if [ "$NEW_SCORE" -le "$BEST" ]; then
    echo "REJECTED: score $NEW_SCORE does not beat current best $BEST. Not promoting."
    exit 1
fi

echo "NEW HIGH SCORE: $NEW_SCORE beats $BEST — promoting to render-stable..."

cd "$BASE"

# Stash any uncommitted work
git add -A
git stash push -m "pre-promotion stash" 2>/dev/null || true

# Checkout or create render-stable
if git rev-parse --verify render-stable >/dev/null 2>&1; then
    git checkout render-stable
else
    git checkout -b render-stable
fi

# Merge main into render-stable
git merge main --no-ff -m "promote: grade $NEW_SCORE beats $BEST" || {
    echo "ERROR: merge conflict during promotion. Aborting."
    git merge --abort 2>/dev/null || true
    git checkout main
    git stash pop 2>/dev/null || true
    exit 1
}

# Back to main
git checkout main
git stash pop 2>/dev/null || true

# Update best grade file
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
python3 -c "
import json
data = {'score': $NEW_SCORE, 'promoted_at': '$TIMESTAMP', 'previous_best': $BEST}
json.dump(data, open('$BEST_GRADE_FILE', 'w'), indent=2)
"

# Log to PIPELINE_LESSONS.md
cat >> "$LESSONS_FILE" <<EOF

### PROMOTION [$(date '+%Y-%m-%d %H:%M')] render-stable updated
Score $NEW_SCORE beats previous best $BEST. Main merged to render-stable.

---
EOF

echo "PROMOTED: new best grade $NEW_SCORE on render-stable (was $BEST)"
