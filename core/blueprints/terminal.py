"""
TERMINAL BLUEPRINT — Protocol Pulse
=====================================
Owns: /terminal, /terminal/*, /api/v2/terminal/*
Status: Routes currently live in routes_api_terminal.py (terminal_bp) + routes.py
TODO: Migrate /terminal page route from routes.py into this blueprint (future session).
"""
from flask import Blueprint

terminal_bp = Blueprint("terminal_main", __name__)

# Routes to migrate from routes.py:
#   GET  /terminal                    — pulse_terminal.html (Session 1)
#   GET  /terminal/checkout           — Stripe $29/mo Commander checkout
#   GET  /terminal/account            — terminal_account.html
# API routes already in routes_api_terminal.terminal_bp:
#   GET/POST /api/v2/terminal/*       — price, mempool, fear-greed, signal, etc.
