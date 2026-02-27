#!/bin/bash
# ============================================================
# REPLIT SETUP SCRIPT — Run this after pulling from GitHub
# ============================================================
# Usage: bash scripts/replit_setup.sh
#
# Prerequisites:
#   - Replit Secrets set: OPENAI_API_KEY, ANTHROPIC_API_KEY
#   - Optional: XAI_API_KEY (Grok), ELEVENLABS_API_KEY (voiceovers)
# ============================================================

set -e

echo "============================================"
echo "  PROTOCOL PULSE — Replit Setup"
echo "============================================"

# 1. Install dependencies
echo ""
echo "--- Step 1: Install Dependencies ---"
pip install pytz apscheduler 2>&1 | tail -2
echo "OK: Dependencies installed"

# 2. Run DB migration
echo ""
echo "--- Step 2: Run DB Migration ---"
python scripts/migrate_published_at.py
echo "OK: Migration complete"

# 3. Run smoke test
echo ""
echo "--- Step 3: Smoke Test ---"
python scripts/smoke_test.py

# 4. Run image health check
echo ""
echo "--- Step 4: Image Health Check ---"
python scripts/image_health_check.py

echo ""
echo "============================================"
echo "  Setup complete! Next steps:"
echo ""
echo "  1. Fix broken images:"
echo "     python scripts/repair_article_images.py --regenerate --published-only"
echo ""
echo "  2. Test single channel (video engine):"
echo "     python scripts/test_single_channel.py"
echo ""
echo "  3. Run full pipeline:"
echo "     python -m services.video_engine.scheduler --now"
echo "============================================"
