"""
MINING BLUEPRINT — Protocol Pulse
===================================
Owns: /mining, /mining-risk, /api/mining/*
Status: Routes currently live in routes.py (p3-mining-intel session).
TODO: Extract mining routes from routes.py into this blueprint (future session).
"""
from flask import Blueprint

mining_bp = Blueprint("mining_main", __name__)

# Routes to migrate from routes.py:
#   GET  /mining                    — mining_hub.html
#   GET  /mining-risk               — mining_risk.html
#   GET  /api/mining/live-stats     — live mining stats (30s cache)
#   GET  /api/mining/pools          — pool distribution (5min cache)
#   GET  /api/mining/articles       — mining-category articles
#   GET  /api/charts/hashrate-history — hashrate chart data (10min cache)
