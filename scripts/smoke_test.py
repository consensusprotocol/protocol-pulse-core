#!/usr/bin/env python3
"""
smoke_test.py — End-to-end smoke test for Protocol Pulse.

Checks: config loading, DB connection, Ultron connectivity, image health,
template rendering, and key routes.

Usage:
    python scripts/smoke_test.py
"""

import os
import sys
import json
import importlib
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results = []


def check(name, fn):
    try:
        ok, detail = fn()
        status = PASS if ok else FAIL
    except Exception as e:
        status = FAIL
        detail = str(e)
    results.append((name, status, detail))
    print(f"  [{status}] {name}: {detail}")


def check_config():
    from services.config_loader import get_enabled_channels, get_settings
    channels = get_enabled_channels()
    settings = get_settings()
    return len(channels) > 0, f"{len(channels)} channels, top_clips={settings.get('top_clips_for_video', '?')}"


def check_db():
    from app import app, db
    from models import Article
    with app.app_context():
        count = Article.query.count()
        published = Article.query.filter_by(published=True).count()
        return True, f"{count} total articles, {published} published"


def check_published_at():
    from app import app, db
    from models import Article
    with app.app_context():
        has_col = hasattr(Article, 'published_at')
        if not has_col:
            return False, "published_at column missing from model"
        with_ts = db.session.query(Article).filter(Article.published_at.isnot(None)).count()
        total_pub = Article.query.filter_by(published=True).count()
        return True, f"{with_ts}/{total_pub} published articles have published_at set"


def check_default_image():
    path = "static/images/default-header.png"
    exists = os.path.exists(path)
    if exists:
        size = os.path.getsize(path)
        return True, f"exists ({size:,} bytes)"
    return False, "MISSING — articles will show broken images"


def check_headers_dir():
    path = "static/images/headers"
    if os.path.isdir(path):
        count = len([f for f in os.listdir(path) if f.endswith(('.png', '.jpg', '.jpeg', '.webp'))])
        return True, f"{count} header images on disk"
    return False, "directory missing"


def check_ultron():
    try:
        from services.video_engine.ultron_client import ultron
        result = ultron.health_check()
        if result and result.get("status") == "ok":
            gpus = result.get("gpu_count", "?")
            version = result.get("version", "?")
            return True, f"v{version}, {gpus} GPUs"
        return False, f"unexpected response: {result}"
    except Exception as e:
        return False, f"unreachable: {e}"


def check_templates():
    from app import app
    with app.app_context():
        # Verify key templates exist
        templates = ['index.html', 'articles.html', 'category.html', 'article_detail.html']
        missing = []
        for t in templates:
            tpl = app.jinja_env.get_or_select_template(t)
            if tpl is None:
                missing.append(t)
        if missing:
            return False, f"missing: {', '.join(missing)}"
        return True, f"all {len(templates)} key templates found"


def check_to_est_filter():
    from app import app
    with app.app_context():
        has_filter = 'to_est' in app.jinja_env.filters
        return has_filter, "registered" if has_filter else "MISSING — timestamps will show UTC"


def check_dashboard_bp():
    from app import app
    with app.app_context():
        rules = [r.rule for r in app.url_map.iter_rules()]
        has_dashboard = any("/dashboard" in r for r in rules)
        return has_dashboard, "registered" if has_dashboard else "NOT registered in app.py"


def check_env_vars():
    required = {
        "OPENAI_API_KEY": "Image generation",
        "ANTHROPIC_API_KEY": "Article generation",
    }
    optional = {
        "XAI_API_KEY": "Grok-3 analysis",
        "ELEVENLABS_API_KEY": "Voiceovers",
        "TWITTER_API_KEY": "Twitter distribution",
    }
    missing_req = [k for k in required if not os.environ.get(k)]
    missing_opt = [k for k in optional if not os.environ.get(k)]

    if missing_req:
        return False, f"missing required: {', '.join(missing_req)}"
    detail = "all required set"
    if missing_opt:
        detail += f"; optional missing: {', '.join(missing_opt)}"
    return True, detail


def main():
    print("\n" + "=" * 60)
    print("PROTOCOL PULSE — SMOKE TEST")
    print("=" * 60)

    print("\n--- Config ---")
    check("Partner channels config", check_config)

    print("\n--- Database ---")
    check("Database connection", check_db)
    check("published_at column", check_published_at)

    print("\n--- Images ---")
    check("Default header image", check_default_image)
    check("Headers directory", check_headers_dir)

    print("\n--- Templates ---")
    check("Key templates", check_templates)
    check("to_est Jinja filter", check_to_est_filter)

    print("\n--- Blueprints ---")
    check("Dashboard blueprint", check_dashboard_bp)

    print("\n--- External Services ---")
    check("Ultron GPU server", check_ultron)

    print("\n--- Environment ---")
    check("Environment variables", check_env_vars)

    # Summary
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("ALL CHECKS PASSED")
    else:
        print("\nFAILED CHECKS:")
        for name, status, detail in results:
            if status == FAIL:
                print(f"  - {name}: {detail}")
    print("=" * 60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
