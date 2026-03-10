"""
MAIN BLUEPRINT — Protocol Pulse
=================================
Owns: /, /live, /about, /contact, /search, misc pages
Status: Routes currently live in routes.py.
TODO: Extract homepage and misc routes from routes.py into this blueprint (future session).
"""
from flask import Blueprint

main_bp = Blueprint("main", __name__)

# Routes to migrate from routes.py:
#   GET  /                — index.html (homepage)
#   GET  /live            — live page
#   GET  /about           — about.html
#   GET  /contact         — contact.html
#   GET  /search          — search.html
#   GET  /sponsors        — sponsors.html
#   GET  /events          — events.html
#   GET  /disruption-tracker — disruption_tracker.html
#   GET  /charts          — see charts.py
