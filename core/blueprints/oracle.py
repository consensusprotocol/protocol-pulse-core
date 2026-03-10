"""
ORACLE BLUEPRINT — Protocol Pulse
===================================
Owns: /oracle, /oracle-live, /oracle/*
Status: Core oracle routes in oracle_routes.py (oracle_bp).
        /oracle-live in routes.py.
TODO: Consolidate all oracle routes here (future session).
"""
from flask import Blueprint

oracle_bp_main = Blueprint("oracle_main", __name__)

# Routes to migrate from routes.py:
#   GET  /oracle-live          — oracle.html (avatar streaming interface)
#   GET  /oracle               — oracle onboarding/hub
# API routes in oracle_routes.oracle_bp:
#   POST /api/oracle/ask       — Oracle Q&A endpoint
#   POST /api/oracle/generate  — Avatar generation
