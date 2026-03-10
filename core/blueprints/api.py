"""
API BLUEPRINT — Protocol Pulse
================================
Owns: /api/* (non-terminal, non-charts, non-mining)
Status: Core API routes in routes_api_v2.py (api_v2). Additional in routes.py.
TODO: Extract remaining /api/* routes from routes.py here (future session).
"""
from flask import Blueprint

api_bp = Blueprint("api_main", __name__)

# Routes already in routes_api_v2.api_v2 (keep there):
#   /api/v2/* — V2 API endpoints

# Routes to migrate from routes.py:
#   GET  /api/sentiment        — sentiment summary
#   GET  /api/articles         — articles list
#   GET  /api/price            — BTC price proxy
#   GET  /api/mempool          — mempool stats proxy
#   GET  /api/fear-greed       — fear & greed index
#   GET  /api/search           — article search
#   POST /api/affiliates/impression — affiliate impression beacon
#   POST /api/affiliates/click      — affiliate click beacon
