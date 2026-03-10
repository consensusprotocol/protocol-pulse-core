"""
PREMIUM BLUEPRINT — Protocol Pulse
====================================
Owns: /premium, /commander, /upgrade, /subscription/*
Status: Routes in routes.py + routes_commander.py (commander_bp) + routes_premium_api.py.
TODO: Consolidate all monetization routes here (future session).
"""
from flask import Blueprint

premium_bp_main = Blueprint("premium_main", __name__)

# Routes to migrate:
#   GET  /premium              — premium_hub.html
#   GET  /commander            — commander tier landing
#   GET  /upgrade              — upgrade flow
#   POST /subscription/checkout — Stripe checkout
#   GET  /subscription/success  — success page
#   POST /webhook/stripe        — Stripe webhook (keep in routes.py or here)
# Already in routes_commander.commander_bp:
#   GET/POST /api/v1/commander/* — Commander API endpoints
