"""
CHARTS BLUEPRINT — Protocol Pulse
===================================
Owns: /charts, /charts/*, /api/charts/*
Status: Routes currently live in routes.py (p3-charts session).
TODO: Extract chart routes from routes.py into this blueprint (future session).
"""
from flask import Blueprint

charts_bp = Blueprint("charts_main", __name__)

# Routes to migrate from routes.py:
#   GET  /charts                         — charts.html (9 sections)
#   GET  /charts/embed/<chart_id>        — embeddable chart widget
#   GET  /api/charts/price-history       — proxy CoinGecko
#   GET  /api/charts/mempool-data        — proxy mempool.space
#   GET  /api/charts/hashrate-history    — proxy blockchair
#   GET  /api/charts/pool-distribution   — mining pool donut
#   GET  /api/charts/fee-history         — mempool fees
#   GET  /api/charts/lightning           — lightning stats
#   GET  /api/charts/fear-greed          — F&G index
#   POST /api/charts/price-alert         — set price alert
#   POST /api/charts/ai-explain          — Claude Haiku chart analysis
