"""
routes.py — Orchestrator: registers all route blueprints.
The actual route handlers live in:
  - routes_admin.py  (admin_bp)
  - routes_api.py    (api_bp)
  - routes_auth.py   (auth_bp)
  - routes_pages.py  (pages_bp)
  - routes_helpers.py (shared state, decorators, services)
"""
from app import app, db, cache
from flask import request, jsonify, redirect, render_template, Response, session
from flask_login import current_user
import models
import logging
import os
import re
from datetime import datetime

# ── Import shared state (initializes services, runs startup tasks) ──────────
import routes_helpers  # noqa: F401

# ── Register blueprints ─────────────────────────────────────────────────────
from routes_admin import admin_bp
from routes_api import api_bp
from routes_auth import auth_bp
from routes_pages import pages_bp

app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(pages_bp)

logging.info("All route blueprints registered: admin, api, auth, pages")

# ── Legacy blueprints (social, premium_api) ──────────────────────────────────
try:
    from routes_social import social
    app.register_blueprint(social)
except (ModuleNotFoundError, ImportError) as e:
    logging.warning("routes_social not loaded: %s", e)

@app.template_filter('clean_preview')
def clean_preview_filter(content, max_length=150):
    """Extract clean preview text from HTML content, prioritizing TL;DR sections"""
    if not content:
        return ""
    
    # First try to extract TL;DR content specifically
    tldr_match = re.search(r'<div class="tldr-section">.*?<strong>TL;DR:\s*(.*?)</strong>', content, re.DOTALL | re.IGNORECASE)
    if tldr_match:
        tldr_text = tldr_match.group(1)
        # Strip any remaining HTML tags from TL;DR
        clean_tldr = re.sub(r'<[^>]+>', '', tldr_text).strip()
        if clean_tldr:
            # Return clean TL;DR text, truncated if needed
            return clean_tldr[:max_length] + ("..." if len(clean_tldr) > max_length else "")
    
    # Fallback: strip all HTML tags and get clean text
    clean_text = re.sub(r'<[^>]+>', '', content)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()  # Normalize whitespace
    
    # Return truncated clean text
    return clean_text[:max_length] + ("..." if len(clean_text) > max_length else "")


@app.before_request
def _first_visit_onboarding():
    """Redirect first-time visitors to onboarding. Cookie-based, skips bots/API/assets."""
    if request.path != '/':
        return None
    # Skip if cookie exists (returning visitor)
    if request.cookies.get('pp_visited'):
        return None
    # Skip bots
    ua = (request.headers.get('User-Agent') or '').lower()
    if any(b in ua for b in ('bot', 'crawl', 'spider', 'google', 'bing', 'slurp', 'facebookexternal', 'twitterbot')):
        return None
    # Skip if coming back from onboarding (referer check)
    ref = (request.headers.get('Referer') or '').lower()
    if 'onboarding' in ref or 'signal-terminal' in ref:
        return None
    # Redirect to onboarding
    resp = redirect('/onboarding/commander')
    return resp

@app.after_request
def _set_visited_cookie(response):
    """Set pp_visited cookie on onboarding and homepage responses."""
    if request.path in ('/', '/onboarding/commander', '/signal-terminal'):
        if not request.cookies.get('pp_visited'):
            response.set_cookie('pp_visited', '1', max_age=365*24*60*60, httponly=True, samesite='Lax')
    return response

@app.before_request
def track_operative_activity():
    """Track active operatives on each page for heatmap display"""
    if request.method != 'GET':
        return
    if request.path.startswith('/static/') or request.path.startswith('/api/'):
        return
    if request.path.startswith('/admin/') and not request.path == '/admin':
        return
    
    user_agent = request.headers.get('User-Agent', '').lower()
    if any(bot in user_agent for bot in ['bot', 'crawler', 'spider', 'curl', 'wget', 'replit']):
        return
    
    try:
        import hashlib
        session_hash = hashlib.sha256(
            f"{request.remote_addr}:{request.headers.get('User-Agent', '')}".encode()
        ).hexdigest()[:32]
        
        page_names = {
            '/': 'Home',
            '/live': 'Live Terminal',
            '/media-hub': 'Media Hub',
            '/drill': 'Recovery Drill',
            '/operator-costs': 'Operator Costs',
            '/scorecard': 'Sovereign Scorecard',
            '/whale-watcher': 'Whale Watcher',
            '/value-stream': 'Value Stream',
            '/sovereign-custody': 'Custody Manual',
            '/clips': 'Signal Clips',
            '/solo-slayers': 'Solo Slayers',
            '/freedom-tech': 'Freedom Tech',
            '/merch': 'Sovereign Merch',
            '/meetups': 'Meetups',
            '/podcast': 'Podcasts',
            '/articles': 'Articles',
        }
        
        page_path = request.path.rstrip('/')
        if not page_path:
            page_path = '/'
        page_name = page_names.get(page_path, page_path.split('/')[-1].title() if page_path else 'Home')
        
        models.RollingActivity.record_activity(page_path, page_name, session_hash)
        
        # Cleanup stale records every 100th request (probabilistic)
        import random
        if random.random() < 0.01:  # ~1% of requests trigger cleanup
            models.RollingActivity.cleanup_stale()
    except Exception as e:
        logging.debug(f"Activity tracking error: {e}")

_view_cache = {}  # Simple in-memory cache for view deduplication

@app.before_request
def track_article_view():
    """Auto-track article views for analytics with deduplication."""
    if request.path.startswith('/article/') and request.method == 'GET':
        try:
            # Skip bots and admin paths
            user_agent = request.headers.get('User-Agent', '').lower()
            if any(bot in user_agent for bot in ['bot', 'crawler', 'spider', 'curl', 'wget']):
                return
            
            parts = request.path.split('/')
            if len(parts) >= 3 and parts[2].isdigit():
                article_id = int(parts[2])
                
                # Deduplicate views: 1 view per IP per article per 5 minutes
                import hashlib
                ip_hash = hashlib.sha256(request.remote_addr.encode()).hexdigest()[:16]
                cache_key = f"{ip_hash}:{article_id}"
                now = datetime.utcnow().timestamp()
                
                if cache_key in _view_cache:
                    if now - _view_cache[cache_key] < 300:  # 5 minutes
                        return  # Skip duplicate view
                
                _view_cache[cache_key] = now
                
                # Clean old cache entries (keep last 1000)
                if len(_view_cache) > 1000:
                    sorted_keys = sorted(_view_cache, key=_view_cache.get)
                    for k in sorted_keys[:500]:
                        del _view_cache[k]
                
                from services.analytics_service import analytics_service
                
                request_info = {
                    'user_agent': request.headers.get('User-Agent'),
                    'referrer': request.headers.get('Referer'),
                    'ip': request.remote_addr
                }
                
                analytics_service.track_event(
                    event_type='view',
                    content_type='article',
                    content_id=article_id,
                    source_platform='website',
                    request_info=request_info
                )
        except Exception as e:
            logging.debug(f"Article view tracking skipped: {e}")

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

