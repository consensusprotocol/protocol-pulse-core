"""
ARTICLES BLUEPRINT — Protocol Pulse
=====================================
Owns: /articles, /article/<id>, /category/*
Status: Routes currently live in routes.py.
TODO: Extract article routes from routes.py into this blueprint (future session).
"""
from flask import Blueprint

articles_bp = Blueprint("articles_main", __name__)

# Routes to migrate from routes.py:
#   GET  /articles             — articles listing
#   GET  /article/<id>         — article detail
#   GET  /articles/<category>  — category listing
#   GET  /bitcoin              — Bitcoin category
#   GET  /defi                 — DeFi category
#   GET  /regulation           — Regulation category
#   GET  /privacy              — Privacy category
#   GET  /innovation           — Innovation category
#   POST /admin/generate       — Article generation (admin)
#   POST /admin/publish/<id>   — Publish article (admin)
