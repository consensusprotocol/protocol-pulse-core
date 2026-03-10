"""
MEDIA BLUEPRINT — Protocol Pulse
==================================
Owns: /media, /media/*, /podcasts, /clips
Status: Routes currently live in routes.py.
TODO: Extract media routes from routes.py into this blueprint (future session).
"""
from flask import Blueprint

media_bp = Blueprint("media_main", __name__)

# Routes to migrate from routes.py:
#   GET  /media                — media_terminal.html / media_hub.html
#   GET  /podcasts             — podcast listing
#   GET  /podcast/<id>         — podcast detail
#   GET  /clips                — clips listing
#   GET  /clips/<filename>     — serve clip file
#   GET  /rss                  — RSS feed
#   GET  /atom                 — Atom feed
#   GET  /feed.json            — JSON feed
#   GET  /opml                 — OPML feed
