"""
routes_admin.py — Admin routes blueprint for Protocol Pulse.
Auto-generated from routes.py split.
"""
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, make_response, session, Response, abort, send_file, send_from_directory, stream_with_context
from flask_login import login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app import app, db, limiter, cache
from routes_helpers import (
    models, verify_turnstile, admin_required, premium_required,
    premium_hub_required, _require_csrf, _trigger_sentiment_classification,
    ai_service, reddit_service, content_generator, content_engine,
    substack_service, rss_service, media_feed_service, printful_service,
    price_service, newsletter_service, ghl_service, ADMIN_SECRET,
    get_space_transcript, summarize_for_tweet,
)
import hashlib
import json
import logging
import requests
import os
import re
import stripe
import uuid
from functools import wraps
from datetime import datetime, timedelta
import threading
import time
from services.youtube_service import YouTubeService

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/sync-podcasts')
@login_required
@admin_required
def sync_podcasts():
    """Sync all podcast RSS feeds"""
    if not rss_service:
        flash('RSS service not available (install feedparser)')
        return redirect('/admin/podcasts')
    try:
        results = rss_service.sync_all_feeds()
        flash(f'Podcast sync completed: {results}')
        return redirect('/admin/podcasts')
    except Exception as e:
        logging.error(f"Error syncing podcasts: {e}")
        flash(f'Error syncing podcasts: {e}')
        return redirect('/admin/podcasts')

@admin_bp.route('/admin/x-replies')
@login_required
@admin_required
def admin_x_replies():
    """Admin dashboard for Sovereign Sentry reply queue."""
    from models import XInboxTweet

    pending = (
        XInboxTweet.query.filter_by(status='drafted')
        .order_by(XInboxTweet.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('admin/x_replies.html', pending=pending)

@admin_bp.route('/admin/x-replies/<int:inbox_id>/approve', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_approve(inbox_id):
    """Approve a draft and post reply to X."""
    from models import XInboxTweet, XReplyDraft, XReplyPost
    from services.x_client import XClient

    inbox = XInboxTweet.query.get_or_404(inbox_id)
    draft = inbox.drafts.order_by(XReplyDraft.created_at.desc()).first()
    if not draft:
        flash('No draft available for this tweet.')
        return redirect('/admin/x-replies')

    # Allow inline edit of draft text
    new_text = request.form.get('draft_text', '').strip()
    if new_text:
        draft.draft_text = new_text

    client = XClient()
    result = client.post_reply(in_reply_to_tweet_id=inbox.tweet_id, text=draft.draft_text)

    post = XReplyPost(
        inbox_id=inbox.id,
        draft_id=draft.id,
        reply_tweet_id=result.get('tweet_id'),
        response_payload=json.dumps(result.get('raw', {})),
    )
    inbox.status = 'posted' if result.get('success') else 'error'

    db.session.add(post)
    db.session.add(inbox)
    db.session.commit()

    if result.get('success'):
        flash('Reply posted to X.')
    else:
        flash('Reply failed to post; see logs.')
    return redirect('/admin/x-replies')

@admin_bp.route('/admin/x-replies/<int:inbox_id>/reject', methods=['POST'])
@login_required
@admin_required
def admin_x_reply_reject(inbox_id):
    """Reject a draft; tweet will not be replied to."""
    from models import XInboxTweet

    inbox = XInboxTweet.query.get_or_404(inbox_id)
    inbox.status = 'rejected'
    db.session.add(inbox)
    db.session.commit()
    flash('Draft rejected.')
    return redirect('/admin/x-replies')

@admin_bp.route('/admin/newsletter')
@login_required
def admin_newsletter():
    """Newsletter admin dashboard."""
    if not current_user.is_admin:
        return redirect(url_for('pages.index'))
    sub_count = models.NewsletterSubscriber.query.filter_by(subscribed=True).count()
    total_subs = models.NewsletterSubscriber.query.count()
    recent_sends = models.NewsletterSend.query.order_by(models.NewsletterSend.sent_at.desc()).limit(10).all()
    last_send = recent_sends[0] if recent_sends else None
    return render_template('admin_newsletter.html',
                           sub_count=sub_count, total_subs=total_subs,
                           recent_sends=recent_sends, last_send=last_send)

@admin_bp.route('/api/admin/newsletter/history')
@login_required
@admin_required
def api_admin_newsletter_history():
    """Newsletter dispatch history — DB sends + queue files."""
    import glob as _glob
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    queue_dir = os.path.join(project_root, 'data', 'newsletter_queue')
    sent_dir = os.path.join(queue_dir, 'sent')

    # DB sends
    sends = models.NewsletterSend.query.order_by(models.NewsletterSend.sent_at.desc()).limit(30).all()
    db_sends = [{
        'id': s.id,
        'subject': s.subject,
        'recipient_count': s.recipient_count,
        'open_count': getattr(s, 'open_count', 0),
        'click_count': getattr(s, 'click_count', 0),
        'sent_at': s.sent_at.isoformat() + 'Z' if s.sent_at else None,
        'source': 'db',
    } for s in sends]

    # Campaigns (model may not exist in all deployments)
    try:
        campaigns = models.NewsletterCampaign.query.order_by(models.NewsletterCampaign.sent_at.desc()).limit(30).all()
        for c in campaigns:
            db_sends.append({
                'id': f'campaign-{c.id}',
                'subject': c.top_headline or 'Daily Digest',
                'recipient_count': c.recipient_count,
                'open_count': 0,
                'click_count': 0,
                'sent_at': c.sent_at.isoformat() + 'Z' if c.sent_at else None,
                'status': c.status,
                'source': 'campaign',
            })
    except AttributeError:
        pass  # NewsletterCampaign model not available in this deployment

    # Queue (pending)
    pending = []
    hook_files = sorted(_glob.glob(os.path.join(queue_dir, '*_hook.json')))
    for hf in hook_files:
        try:
            with open(hf) as f:
                data = json.load(f)
            pending.append({
                'filename': os.path.basename(hf),
                'hook': (data.get('hook', '') or '')[:200],
                'brief_type': data.get('brief_type', ''),
                'generated_at': data.get('generated_at', ''),
            })
        except Exception:
            pending.append({'filename': os.path.basename(hf), 'hook': '(parse error)', 'brief_type': '', 'generated_at': ''})

    # Sent files
    sent_files = []
    if os.path.isdir(sent_dir):
        for sf in sorted(os.listdir(sent_dir), reverse=True)[:20]:
            try:
                with open(os.path.join(sent_dir, sf)) as f:
                    data = json.load(f)
                sent_files.append({
                    'filename': sf,
                    'hook': (data.get('hook', '') or '')[:200],
                    'brief_type': data.get('brief_type', ''),
                    'generated_at': data.get('generated_at', ''),
                })
            except Exception:
                sent_files.append({'filename': sf, 'hook': '', 'brief_type': '', 'generated_at': ''})

    # Sort DB sends by date
    db_sends.sort(key=lambda x: x.get('sent_at') or '', reverse=True)

    return jsonify({
        'dispatches': db_sends,
        'pending_queue': pending,
        'sent_queue_files': sent_files,
    })

@admin_bp.route('/api/admin/newsletter/preview')
@login_required
@admin_required
def api_admin_newsletter_preview():
    """Generate and return a preview of the current newsletter HTML."""
    try:
        import importlib.util as _ilu
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        _ne_path = os.path.join(project_root, 'services', 'newsletter_engine.py')
        _ne_spec = _ilu.spec_from_file_location('_newsletter_engine_preview', _ne_path)
        _ne_mod = _ilu.module_from_spec(_ne_spec)
        _ne_spec.loader.exec_module(_ne_mod)
        engine = _ne_mod.NewsletterEngine()
        articles = engine.get_todays_articles(5)
        btc_data = engine.get_btc_price()
        summary = engine.generate_ai_summary(articles)
        html = engine.generate_html(articles, summary, btc_data)
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
    except Exception as e:
        return f'<html><body style="background:#000;color:#f55;padding:40px;font-family:monospace;">Preview error: {e}</body></html>', 500, {'Content-Type': 'text/html'}

@admin_bp.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard"""
    total_articles = models.Article.query.count()
    published_articles = models.Article.query.filter_by(published=True).count()
    total_podcasts = models.Podcast.query.count()
    recent_articles = models.Article.query.order_by(models.Article.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_articles=total_articles,
                         published_articles=published_articles,
                         total_podcasts=total_podcasts,
                         recent_articles=recent_articles)

@admin_bp.route('/api/admin/pipeline-stats')
@login_required
@admin_required
def api_admin_pipeline_stats():
    """Pipeline health: article counts, video render status."""
    now = datetime.utcnow()
    h24 = now - timedelta(hours=24)
    d7 = now - timedelta(days=7)
    h1 = now - timedelta(hours=1)

    articles_24h = models.Article.query.filter(models.Article.created_at >= h24).count()
    articles_7d = models.Article.query.filter(models.Article.created_at >= d7).count()
    articles_total = models.Article.query.count()
    articles_published = models.Article.query.filter_by(published=True).count()
    articles_draft = models.Article.query.filter_by(published=False).count()
    articles_1h = models.Article.query.filter(models.Article.created_at >= h1).count()

    # Daily sparkline: count per day for last 7 days
    sparkline = []
    for i in range(6, -1, -1):
        day_start = now - timedelta(days=i + 1)
        day_end = now - timedelta(days=i)
        cnt = models.Article.query.filter(
            models.Article.created_at >= day_start,
            models.Article.created_at < day_end
        ).count()
        sparkline.append(cnt)

    # Last video render — check logs
    last_video = None
    try:
        report_paths = [
            os.path.expanduser('~/protocol_pulse/logs/daily_pulse.report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_pipeline_report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_daily_beat.report.json'),
        ]
        for rpath in report_paths:
            if os.path.exists(rpath):
                mtime = os.path.getmtime(rpath)
                ts = datetime.utcfromtimestamp(mtime).isoformat() + 'Z'
                last_video = {'path': os.path.basename(rpath), 'timestamp': ts}
                break
    except Exception:
        pass

    # Next briefing (13:00 UTC daily)
    next_briefing = now.replace(hour=13, minute=0, second=0, microsecond=0)
    if next_briefing <= now:
        next_briefing += timedelta(days=1)

    return jsonify({
        'articles_24h': articles_24h,
        'articles_7d': articles_7d,
        'articles_total': articles_total,
        'articles_published': articles_published,
        'articles_draft': articles_draft,
        'articles_1h': articles_1h,
        'sparkline': sparkline,
        'last_video': last_video,
        'next_briefing': next_briefing.isoformat() + 'Z',
        'timestamp': now.isoformat() + 'Z',
    })

@admin_bp.route('/api/admin/audience-stats')
@login_required
@admin_required
def api_admin_audience_stats():
    """Newsletter subscribers, email stats."""
    try:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now - timedelta(days=7)

        total_subs = models.NewsletterSubscriber.query.filter_by(subscribed=True).count()
        total_unsub = models.NewsletterSubscriber.query.filter_by(subscribed=False).count()
        new_today = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.subscribed_at >= today_start,
            models.NewsletterSubscriber.subscribed == True
        ).count()
        new_week = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.subscribed_at >= week_start,
            models.NewsletterSubscriber.subscribed == True
        ).count()
        unsub_week = models.NewsletterSubscriber.query.filter(
            models.NewsletterSubscriber.unsubscribed_at >= week_start
        ).count()

        last_send = models.NewsletterSend.query.order_by(models.NewsletterSend.sent_at.desc()).first()
        last_send_data = None
        if last_send:
            last_send_data = {
                'subject': last_send.subject,
                'sent_at': last_send.sent_at.isoformat() + 'Z' if last_send.sent_at else None,
                'recipient_count': last_send.recipient_count,
                'open_count': getattr(last_send, 'open_count', 0),
                'click_count': getattr(last_send, 'click_count', 0),
            }

        next_email = now.replace(hour=8, minute=0, second=0, microsecond=0)
        if next_email <= now:
            next_email += timedelta(days=1)

        return jsonify({
            'total_subscribers': total_subs,
            'total_unsubscribed': total_unsub,
            'new_today': new_today,
            'new_week': new_week,
            'unsub_week': unsub_week,
            'last_send': last_send_data,
            'next_email': next_email.isoformat() + 'Z',
            'timestamp': now.isoformat() + 'Z',
        })
    except Exception as e:
        return jsonify({'error': str(e), 'total_subscribers': 0})

@admin_bp.route('/api/admin/content-stats')
@login_required
@admin_required
def api_admin_content_stats():
    """Top articles, sentiment distribution, affiliate clicks."""
    now = datetime.utcnow()
    d7 = now - timedelta(days=7)

    top_articles_q = models.Article.query.filter_by(published=True)\
        .order_by(models.Article.created_at.desc()).limit(10).all()
    top_articles = [{
        'id': a.id,
        'title': a.title[:70],
        'category': a.category,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
    } for a in top_articles_q]

    # Sentiment distribution from SentimentReport
    sentiment_dist = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    try:
        reports = models.SentimentReport.query.order_by(models.SentimentReport.report_date.desc()).limit(30).all()
        for r in reports:
            s = (r.overall_sentiment or '').lower()
            if 'bull' in s:
                sentiment_dist['bullish'] += 1
            elif 'bear' in s:
                sentiment_dist['bearish'] += 1
            else:
                sentiment_dist['neutral'] += 1
    except Exception:
        pass

    # Affiliate click counts per partner
    affiliate_data = []
    try:
        partners = models.AffiliatePartner.query.filter_by(is_active=True).all()
        for p in partners:
            clicks_7d = models.AffiliateClick.query.filter(
                models.AffiliateClick.partner_id == p.id,
                models.AffiliateClick.clicked_at >= d7
            ).count()
            clicks_total = models.AffiliateClick.query.filter_by(partner_id=p.id).count()
            affiliate_data.append({
                'name': p.name,
                'slug': p.slug,
                'clicks_7d': clicks_7d,
                'clicks_total': clicks_total,
            })
    except Exception:
        pass

    # Draft queue
    draft_queue = models.Article.query.filter_by(published=False)\
        .order_by(models.Article.created_at.desc()).limit(5).all()
    draft_list = [{
        'id': a.id,
        'title': a.title[:60],
        'category': a.category,
        'created_at': a.created_at.isoformat() + 'Z' if a.created_at else None,
    } for a in draft_queue]

    return jsonify({
        'top_articles': top_articles,
        'sentiment_dist': sentiment_dist,
        'affiliate_data': affiliate_data,
        'draft_queue': draft_list,
        'timestamp': now.isoformat() + 'Z',
    })

@admin_bp.route('/api/admin/system-health')
@login_required
@admin_required
def api_admin_system_health():
    """CPU, RAM, disk, GPU, recent errors."""
    import psutil
    import subprocess

    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    # GPU via nvidia-smi
    gpu = None
    try:
        gpu_out = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            timeout=3
        ).decode().strip().split(',')
        gpu = {
            'utilization': float(gpu_out[0].strip()),
            'temp': float(gpu_out[1].strip()),
            'memory_used': float(gpu_out[2].strip()),
            'memory_total': float(gpu_out[3].strip()),
        }
    except Exception:
        pass

    # Recent errors from gunicorn error log
    errors = []
    log_paths = [
        os.path.expanduser('~/protocol_pulse/logs/waitress.log'),
        os.path.expanduser('~/protocol_pulse/logs/app.log'),
    ]
    for lp in log_paths:
        try:
            with open(lp, 'r') as f:
                lines = f.readlines()[-200:]
            for line in lines:
                if 'ERROR' in line or 'CRITICAL' in line or 'Traceback' in line:
                    errors.append(line.strip()[:200])
            errors = errors[-10:]
            break
        except Exception:
            pass

    # Uptime
    uptime_seconds = None
    try:
        boot_time = psutil.boot_time()
        uptime_seconds = int(datetime.utcnow().timestamp() - boot_time)
    except Exception:
        pass

    return jsonify({
        'cpu_pct': cpu,
        'ram_used_gb': round(ram.used / (1024**3), 1),
        'ram_total_gb': round(ram.total / (1024**3), 1),
        'ram_pct': round(ram.percent, 1),
        'disk_used_gb': round(disk.used / (1024**3), 1),
        'disk_total_gb': round(disk.total / (1024**3), 1),
        'disk_pct': round(disk.percent, 1),
        'gpu': gpu,
        'recent_errors': errors,
        'uptime_seconds': uptime_seconds,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
    })

@admin_bp.route('/api/admin/data-health')
def api_admin_data_health():
    """Data staleness check for all intelligence sources. No auth required for monitoring."""
    try:
        import sys as _sys_wd, importlib.util
        _wd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "services", "data_staleness_watchdog.py")
        _spec = importlib.util.spec_from_file_location("data_staleness_watchdog", _wd_path)
        _mod = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_mod)
        check_all = _mod.check_all
        sources = check_all()
        critical = sum(1 for s in sources if s["status"] in ("CRITICAL", "MISSING"))
        warning = sum(1 for s in sources if s["status"] == "WARNING")
        ok = sum(1 for s in sources if s["status"] == "OK")
        overall = "CRITICAL" if critical > 0 else ("WARNING" if warning > 0 else "OK")
        return jsonify({
            "overall": overall,
            "counts": {"ok": ok, "warning": warning, "critical": critical},
            "sources": sources,
            "checked_at": datetime.utcnow().isoformat() + "Z",
        })
    except Exception as e:
        return jsonify({"error": str(e), "overall": "ERROR"}), 500


@admin_bp.route('/api/admin/revenue-stats')
@login_required
@admin_required
def api_admin_revenue_stats():
    """Stripe MRR, active Commander subscribers."""
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    if not stripe_key:
        return jsonify({'available': False})

    try:
        import stripe as _stripe
        _stripe.api_key = stripe_key

        commander_count = models.User.query.filter(
            models.User.subscription_tier.in_(['commander', 'sovereign'])
        ).count()

        mrr_cents = 0
        recent_charges = []
        try:
            subs = _stripe.Subscription.list(status='active', limit=100)
            for sub in subs.data:
                for item in sub['items']['data']:
                    plan = item.get('plan') or item.get('price', {})
                    amount = plan.get('amount', 0) or 0
                    interval = plan.get('interval', 'month')
                    if interval == 'year':
                        mrr_cents += amount // 12
                    else:
                        mrr_cents += amount
        except Exception:
            pass

        try:
            charges = _stripe.Charge.list(limit=5, created={'gte': int((datetime.utcnow() - timedelta(days=30)).timestamp())})
            for ch in charges.data:
                if ch.paid:
                    recent_charges.append({
                        'amount': ch.amount / 100,
                        'currency': ch.currency.upper(),
                        'created': datetime.utcfromtimestamp(ch.created).isoformat() + 'Z',
                        'description': ch.description or '',
                    })
        except Exception:
            pass

        return jsonify({
            'available': True,
            'mrr_usd': round(mrr_cents / 100, 2),
            'commander_count': commander_count,
            'recent_charges': recent_charges,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
        })
    except Exception as e:
        return jsonify({'available': False, 'error': str(e)})

@admin_bp.route('/admin/youtube-debug')
@login_required
def youtube_debug():
    """Debug YouTube OAuth - shows exact token exchange response."""
    from services.youtube_service import YouTubeService
    import requests as _req
    yt = YouTubeService()
    results = {
        'configured': yt.is_oauth_configured(),
        'redirect_uri': yt._get_oauth_redirect_uri(),
        'client_id_present': bool(os.environ.get('YOUTUBE_CLIENT_ID')),
        'client_secret_present': bool(os.environ.get('YOUTUBE_CLIENT_SECRET')),
        'existing_refresh_token': bool(os.environ.get('YOUTUBE_REFRESH_TOKEN')),
    }
    # Test a direct connection to Google
    try:
        test = _req.get('https://accounts.google.com/.well-known/openid-configuration', timeout=5)
        results['google_reachable'] = test.status_code == 200
    except Exception as e:
        results['google_reachable'] = str(e)
    return jsonify(results)

@admin_bp.route('/admin/youtube-auth')
@login_required
@admin_required
def admin_youtube_auth():
    """YouTube OAuth authorization page"""
    from services.youtube_service import YouTubeService
    yt = YouTubeService()
    
    # Reload env to pick up any recently saved tokens
    from dotenv import load_dotenv as _ldenv
    _ldenv('/home/ultron/protocol_pulse/.env', override=True)
    import importlib, sys
    # Force reload of env vars into current process
    for key in ['YOUTUBE_REFRESH_TOKEN', 'YOUTUBE_CLIENT_ID', 'YOUTUBE_CLIENT_SECRET']:
        val = open('/home/ultron/protocol_pulse/.env').read()
        import re as _re
        m = _re.search(rf'^{key}=(.+)$', val, _re.MULTILINE)
        if m: os.environ[key] = m.group(1).strip()
    
    is_configured = yt.is_oauth_configured()
    is_authorized = yt.is_upload_authorized()
    channel_info = None
    if is_authorized:
        try:
            channel_info = yt.get_authorized_channel_info()
        except Exception:
            channel_info = {'title': 'Channel connected', 'id': 'authorized', 'thumbnail': None}
    auth_url = None
    
    if is_configured and not is_authorized:
        auth_url, state = yt.get_oauth_url()
        session['youtube_oauth_state'] = state
    
    return render_template('admin/youtube_auth.html',
                          is_configured=is_configured,
                          is_authorized=is_authorized,
                          channel_info=channel_info,
                          auth_url=auth_url)

@admin_bp.route('/admin/api/upload-short', methods=['POST'])
@login_required
@admin_required
def admin_upload_short():
    """Upload a video clip as a YouTube Short"""
    from services.youtube_service import YouTubeService
    yt = YouTubeService()
    
    data = request.get_json()
    clip_path = data.get('clip_path')
    title = data.get('title', 'Protocol Pulse Signal')
    description = data.get('description')
    tags = data.get('tags')
    privacy = data.get('privacy', 'private')
    
    if not clip_path:
        return jsonify({'success': False, 'error': 'No clip path provided'}), 400
    
    result = yt.upload_short(clip_path, title, description, tags, privacy)
    return jsonify(result)

@admin_bp.route('/admin/api/post-to-x', methods=['POST'])
@login_required
@admin_required
def admin_post_to_x():
    """Post a video clip or text to X/Twitter"""
    from services.x_service import XService
    x_service = XService()
    
    data = request.get_json()
    clip_path = data.get('clip_path')
    caption = data.get('caption', 'Protocol Pulse Signal')
    article_url = data.get('article_url')
    
    # Check if X is configured
    status = x_service.get_upload_status()
    if not status['configured']:
        return jsonify({'success': False, 'error': 'X/Twitter API not configured'}), 400
    
    if clip_path:
        # Post video clip
        if not os.path.exists(clip_path):
            return jsonify({'success': False, 'error': f'Clip not found: {clip_path}'}), 404
        
        tweet_id = x_service.post_clip_with_link(
            video_path=clip_path,
            title=caption,
            article_url=article_url
        )
        
        if tweet_id:
            return jsonify({
                'success': True, 
                'tweet_id': tweet_id,
                'tweet_url': f'https://x.com/i/status/{tweet_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to post video to X'}), 500
    else:
        # Post text only (for article promotion)
        tweet_id = x_service.post_article_tweet(
            type('Article', (), {'title': caption, 'id': data.get('article_id', '')})(),
            base_url=request.host_url.rstrip('/')
        )
        
        if tweet_id:
            return jsonify({
                'success': True,
                'tweet_id': str(tweet_id),
                'tweet_url': f'https://x.com/i/status/{tweet_id}'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to post to X'}), 500

@admin_bp.route('/admin/api/x-status')
@login_required
@admin_required
def admin_x_status():
    """Check X/Twitter API status"""
    from services.x_service import XService
    x_service = XService()
    return jsonify(x_service.get_upload_status())

@admin_bp.route('/admin/api/dry-run-dual-image-news', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_dry_run_dual_image_news():
    """
    Dry-run breaking news dual-image post: draft text + cover + branded asset, no actual post.
    Query/body: article_id (int). Uses article title and header_image_url; returns what would be posted.
    """
    article_id = request.args.get('article_id') or (request.get_json(silent=True) or {}).get('article_id')
    if article_id is None or article_id == '':
        return jsonify({'success': False, 'error': 'article_id required'}), 400
    try:
        article_id = int(article_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': 'article_id must be an integer'}), 400
    article = models.Article.query.get(article_id)
    if not article:
        return jsonify({'success': False, 'error': 'Article not found'}), 404
    base_url = request.host_url.rstrip('/')
    article_url = f"{base_url}/articles/{article.id}"
    draft_text = (article.title[:200] + "..." if len(article.title) > 200 else article.title) + "\n\n" + article_url
    if len(draft_text) > 280:
        draft_text = draft_text[:277] + "..."
    cover_url = article.header_image_url or None
    if not cover_url:
        cover_url = f"{base_url}/static/images/default-header.png"
    from services.x_service import XService
    x_service = XService()
    result = x_service.post_dual_image_news(draft_text, cover_url, dry_run=True)
    result['article_id'] = article_id
    result['article_title'] = article.title
    result['cover_url_resolved'] = cover_url
    return jsonify({'success': True, 'dry_run': result})

@admin_bp.route('/admin/generate')
@login_required
@admin_required
def admin_generate():
    """Content Command Center - All content generation tools"""
    prompts = models.ContentPrompt.query.filter_by(active=True).all()
    total_articles = models.Article.query.count()
    published_articles = models.Article.query.filter_by(published=True).count()
    total_podcasts = models.Podcast.query.count()
    
    # Count clips
    try:
        from services.ai_clips_service import ai_clips_service
        total_clips = len(ai_clips_service.get_all_clips())
    except:
        total_clips = 0
    
    return render_template('admin/content_command.html', 
                          prompts=prompts,
                          total_articles=total_articles,
                          published_articles=published_articles,
                          total_podcasts=total_podcasts,
                          total_clips=total_clips)

@admin_bp.route('/admin/publish-to-substack/<int:article_id>', methods=['POST'])
@login_required
@admin_required  
def publish_to_substack(article_id):
    """Publish existing article to Substack using python-substack"""
    try:
        if not substack_service:
            return jsonify({'success': False, 'error': 'Substack service not available'})
            
        article = models.Article.query.get_or_404(article_id)
        
        # Determine content type from category
        category = article.category.lower()
        if 'bitcoin' in category:
            content_type = 'bitcoin'
        elif 'defi' in category:
            content_type = 'defi'
        else:
            content_type = 'article'
        
        # Format content for newsletter
        newsletter_content = substack_service.format_content_for_newsletter(
            article.content, content_type
        )
        
        # Publish to Substack
        substack_url = substack_service.publish_to_substack(
            article.title,
            newsletter_content,
            article.header_image_url
        )
        
        if substack_url:
            # Update article with Substack URL
            article.substack_url = substack_url
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'substack_url': substack_url,
                'message': 'Article published to Substack successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to publish to Substack'})
            
    except Exception as e:
        logging.error(f"Substack publishing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/share-reddit/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def share_to_reddit(article_id):
    """Cross-post article to Reddit using PRAW"""
    try:
        from services.reddit_service import RedditService
        
        article = models.Article.query.get_or_404(article_id)
        
        # Get target subreddit from request (default to 'bitcoin')
        request_data = request.get_json() or {}
        target_subreddit = request_data.get('subreddit', 'bitcoin')
        
        # Prepare Reddit post
        post_title = article.title
        post_url = article.substack_url or request.url_root + f"articles/{article.id}"
        
        # Post to Reddit
        reddit_service = RedditService()
        result = reddit_service.post_to_reddit(target_subreddit, post_title, post_url)
        
        if result["success"]:
            return jsonify({
                'success': True,
                'reddit_url': result["post_url"],
                'message': f'Successfully posted to r/{target_subreddit}'
            })
        else:
            return jsonify({
                'success': False,
                'errors': result.get("errors", ["Unknown error"]),
                'message': 'Failed to post to Reddit'
            })
            
    except Exception as e:
        logging.error(f"Reddit crosspost failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/generate-content', methods=['POST'])
@login_required
@admin_required
def generate_content():
    """Generate content using the content engine"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Invalid JSON data'})
        
        topic = data.get('topic', '')
        content_type = data.get('content_type', 'bitcoin_news')
        auto_publish = data.get('auto_publish', False)
        
        if not topic:
            return jsonify({'success': False, 'error': 'Topic is required'})
        
        # Generate content using the content engine
        result = content_engine.generate_and_publish_article(topic, content_type, auto_publish)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Content generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/sentiment-report', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_sentiment_report():
    """View and trigger daily sentiment reports"""
    
    if request.method == 'POST':
        try:
            from services.sentiment_tracker_service import sentiment_tracker
            article_id = sentiment_tracker.run_daily_report()
            if article_id:
                flash(f'Sentiment report generated! Article ID: {article_id}', 'success')
            else:
                flash('No report generated - may already exist for today', 'warning')
        except Exception as e:
            flash(f'Error generating report: {str(e)}', 'error')
        return redirect(url_for('admin.admin_sentiment_report'))
    
    reports = models.SentimentReport.query.order_by(models.SentimentReport.report_date.desc()).limit(30).all()
    return render_template('admin/sentiment_reports.html', reports=reports)

@admin_bp.route('/admin/generate-podcast', methods=['POST'])
@login_required
@admin_required
def generate_podcast():
    """Generate audio intelligence podcast from YouTube video"""
    from services.podcast_generator import podcast_generator
    
    try:
        data = request.get_json() or {}
        video_id = data.get('video_id')
        channel_name = data.get('channel_name', 'YouTube Channel')
        
        if not video_id:
            return jsonify({'success': False, 'error': 'video_id required'})
        
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        
        result = podcast_generator.generate_podcast_from_video(
            video_id=video_id,
            thumbnail_url=thumbnail_url,
            channel_name=channel_name
        )
        
        if result and result.get('audio_file'):
            article = models.Article(
                title=f"Audio Deep Dive: {channel_name} Analysis",
                summary=f"Deep-dive audio analysis featuring expert commentary",
                content=f'<p class="article-paragraph">Listen to our AI-hosted podcast breakdown.</p><audio controls src="/{result["audio_file"]}" style="width:100%; margin-top: 1rem;"></audio>',
                category='Podcast',
                image_url=thumbnail_url,
                published=True
            )
            db.session.add(article)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'article_id': article.id,
                'audio_file': result.get('audio_file'),
                'video_file': result.get('video_file')
            })
        
        return jsonify({'success': False, 'error': 'Failed to generate podcast'})
        
    except Exception as e:
        logging.error(f"Podcast generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/generate-podcasts-batch', methods=['POST'])
@login_required
@admin_required
def generate_podcasts_batch():
    """Generate podcasts from all monitored Bitcoin channels"""
    from services.automation import generate_podcasts_from_partners
    
    try:
        result = generate_podcasts_from_partners()
        return jsonify({
            'success': True,
            'message': 'Partner podcast generation completed',
            'videos_found': result.get('videos_found'),
            'articles_generated': len(result.get('articles_generated', [])),
            'podcasts_generated': len(result.get('podcasts_generated', [])),
        })
    except Exception as e:
        logging.error(f"Batch podcast generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/spaces/recap', methods=['POST'])
@login_required
@admin_required
def admin_space_recap():
    """
    Generate a post-Space recap tweet from a transcript and optionally post to X.
    Body: JSON with keys:
      - space_id (optional, used if transcript_text is empty)
      - transcript_text (optional; if omitted we call get_space_transcript)
      - provider (optional, default 'xspacestream')
      - auto_post (bool, default True)
    """
    data = request.get_json(force=True, silent=True) or {}
    space_id = data.get('space_id') or ''
    transcript_text = (data.get('transcript_text') or '').strip()
    provider = data.get('provider') or 'xspacestream'
    auto_post = bool(data.get('auto_post', True))

    if not transcript_text and not space_id:
        return jsonify({'success': False, 'error': 'space_id or transcript_text required'}), 400

    try:
        if not transcript_text and space_id:
            space_data = get_space_transcript(space_id=space_id, provider=provider)
            transcript_text = (space_data or {}).get('transcript_text', '') or ''

        recap = summarize_for_tweet(transcript_text)
        tweet_text = (recap.get('tweet_text') or '').strip()
        if not tweet_text:
            return jsonify({'success': False, 'error': 'No recap text could be generated'}), 500

        tweet_id = None
        x_status = "not_posted"
        if auto_post:
            try:
                from services.x_service import XService
                x = XService()
                if x.client:
                    tweet_id = x.client.update_status(tweet_text).id
                    x_status = "posted"
                else:
                    x_status = "skipped_no_client"
            except Exception as e:
                logging.error("Space recap X post failed: %s", e)
                x_status = "error"

        return jsonify({
            'success': True,
            'recap': recap,
            'tweet_text': tweet_text,
            'tweet_id': tweet_id,
            'x_status': x_status,
        })
    except Exception as e:
        logging.error("admin_space_recap failed: %s", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/extract-clips', methods=['POST'])
@login_required
@admin_required
def api_extract_clips():
    """Extract viral clips from a YouTube video using AI transcript analysis"""
    try:
        from services.ai_clips_service import ai_clips_service
        
        data = request.get_json() or {}
        video_id = data.get('video_id')
        num_clips = data.get('num_clips', 5)
        
        if not video_id:
            return jsonify({'success': False, 'error': 'Video ID required'})
        
        result = ai_clips_service.process_video(video_id, max_clips=num_clips)
        
        return jsonify({
            'success': True,
            'message': f"Extracted {len(result.get('clips', []))} clips from video",
            'clips': result.get('clips', [])
        })
    except Exception as e:
        logging.error(f"Clip extraction failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/process-partner-clips', methods=['POST'])
@login_required
@admin_required
def api_process_partner_clips():
    """Process all partner channels for viral clips"""
    try:
        from services.ai_clips_service import ai_clips_service
        
        result = ai_clips_service.process_partner_channels()
        
        return jsonify({
            'success': True,
            'clips_created': result.get('clips_created', 0),
            'channels_processed': result.get('channels_processed', 0)
        })
    except Exception as e:
        logging.error(f"Partner clip processing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/process-partner-channels', methods=['POST'])
@login_required
@admin_required
def process_partner_channels():
    """Process all partner YouTube channels for new content"""
    try:
        from services.automation import process_all_partner_channels
        
        result = process_all_partner_channels()
        
        return jsonify({
            'success': True,
            'message': 'Partner channels processed',
            'videos_found': result.get('videos_found', 0),
            'articles_generated': result.get('articles_generated', 0),
            'podcasts_generated': result.get('podcasts_generated', 0)
        })
    except Exception as e:
        logging.error(f"Partner channel processing failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/run-daily-pipeline', methods=['POST'])
@login_required
@admin_required
def run_daily_pipeline():
    """Run the full daily content automation pipeline"""
    try:
        data = request.get_json() or {}
        include_reddit = data.get('include_reddit', True)
        include_youtube = data.get('include_youtube', True)
        auto_publish = data.get('auto_publish', False)
        
        results = {
            'reddit_articles': 0,
            'youtube_content': 0,
            'total_generated': 0
        }
        
        if include_reddit:
            try:
                from services.automation import generate_from_trending_reddit
                reddit_result = generate_from_trending_reddit()
                results['reddit_articles'] = reddit_result.get('articles_generated', 0)
            except Exception as e:
                logging.warning(f"Reddit generation skipped: {e}")
        
        if include_youtube:
            try:
                from services.automation import process_all_partner_channels
                yt_result = process_all_partner_channels()
                results['youtube_content'] = yt_result.get('articles_generated', 0) + yt_result.get('podcasts_generated', 0)
            except Exception as e:
                logging.warning(f"YouTube processing skipped: {e}")
        
        results['total_generated'] = results['reddit_articles'] + results['youtube_content']
        
        return jsonify({
            'success': True,
            'message': f"Daily pipeline complete. Generated {results['total_generated']} pieces of content.",
            'results': results
        })
    except Exception as e:
        logging.error(f"Daily pipeline failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/generate-social-package', methods=['POST'])
@login_required
@admin_required
def admin_generate_social_package():
    """Alias route for social package generation from content command center"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Video ID required'})
    
    try:
        package = podcast_generator.create_full_social_package(
            video_id=video_id,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'message': f"Full social package created for {channel_name}",
            'package': package
        })
    except Exception as e:
        logging.error(f"Social package generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/generate-bitcoin-lens', methods=['POST'])
@login_required
@admin_required
def admin_generate_bitcoin_lens():
    """Generate Bitcoin Lens reactionary article from content command center"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Content Creator')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'Video ID required'})
    
    try:
        result = podcast_generator.generate_bitcoin_lens_article(
            video_id=video_id,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'message': f"Bitcoin Lens article generated for {channel_name}",
            'article_id': result.get('article_id'),
            'title': result.get('title')
        })
    except Exception as e:
        logging.error(f"Bitcoin Lens generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/multimodal/social-package', methods=['POST'])
@login_required
@admin_required
def generate_social_package():
    """Generate full social media package from a YouTube video (podcast + clips + article)"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    thumbnail_url = data.get('thumbnail_url')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'video_id required'})
    
    if not thumbnail_url:
        thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    try:
        package = podcast_generator.create_full_social_package(
            video_id=video_id,
            thumbnail_url=thumbnail_url,
            channel_name=channel_name
        )
        
        return jsonify({
            'success': True,
            'package': {
                'podcast_created': package.get('podcast') is not None,
                'article_title': package.get('article', {}).get('title') if package.get('article') else None,
                'clips_count': len(package.get('clips', [])),
                'social_videos_count': len(package.get('social_videos', [])),
                'generated_at': package.get('generated_at')
            }
        })
    except Exception as e:
        logging.error(f"Social package generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/multimodal/bitcoin-lens', methods=['POST'])
@login_required
@admin_required
def generate_bitcoin_lens_article():
    """Generate a Bitcoin Lens reactionary review article from a YouTube video"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    video_id = data.get('video_id')
    channel_name = data.get('channel_name', 'Partner Channel')
    
    if not video_id:
        return jsonify({'success': False, 'error': 'video_id required'})
    
    try:
        result = podcast_generator.generate_bitcoin_lens_review(video_id, channel_name)
        
        if result:
            return jsonify({
                'success': True,
                'article': {
                    'title': result.get('title'),
                    'content_preview': result.get('content', '')[:500] + '...',
                    'channel': result.get('source_channel'),
                    'generated_at': result.get('generated_at')
                }
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate Bitcoin Lens review'})
            
    except Exception as e:
        logging.error(f"Bitcoin Lens generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/multimodal/extract-clip', methods=['POST'])
@login_required
@admin_required
def extract_podcast_clip():
    """Extract a 60-second clip from an existing podcast audio file"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    audio_file = data.get('audio_file')
    start_time = data.get('start_time', 30)
    
    if not audio_file:
        return jsonify({'success': False, 'error': 'audio_file path required'})
    
    try:
        clip_path = podcast_generator.extract_60s_clip(audio_file, start_time=start_time)
        
        if clip_path:
            return jsonify({
                'success': True,
                'clip_path': clip_path
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to extract clip'})
            
    except Exception as e:
        logging.error(f"Clip extraction failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/multimodal/social-wrapper', methods=['POST'])
@login_required
@admin_required
def create_social_wrapper():
    """Wrap an audio clip with YouTube thumbnail and cyberpunk headline overlay"""
    from services.podcast_generator import podcast_generator
    
    data = request.json or {}
    audio_clip = data.get('audio_clip')
    thumbnail_url = data.get('thumbnail_url')
    headline = data.get('headline', 'Bitcoin Intelligence Briefing')
    output_format = data.get('format', 'shorts')
    
    if not audio_clip or not thumbnail_url:
        return jsonify({'success': False, 'error': 'audio_clip and thumbnail_url required'})
    
    try:
        video_path = podcast_generator.create_social_video_wrapper(
            audio_clip=audio_clip,
            thumbnail_url=thumbnail_url,
            headline=headline,
            output_format=output_format
        )
        
        if video_path:
            return jsonify({
                'success': True,
                'video_path': video_path,
                'format': output_format
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to create social wrapper'})
            
    except Exception as e:
        logging.error(f"Social wrapper creation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/multimodal/auto-process', methods=['POST'])
@login_required
@admin_required
def auto_process_partner_videos():
    """Automatically process new videos from partner channels"""
    youtube_service = YouTubeService()
    
    try:
        results = youtube_service.auto_process_new_partner_videos()
        
        return jsonify({
            'success': True,
            'results': {
                'videos_found': results.get('videos_found', 0),
                'articles_generated': len(results.get('articles_generated', [])),
                'podcasts_generated': len(results.get('podcasts_generated', [])),
                'clips_created': len(results.get('clips_created', [])),
                'errors': results.get('errors', [])
            }
        })
    except Exception as e:
        logging.error(f"Auto-process partner videos failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/ghl-sync', methods=['POST'])
@login_required
@admin_required
def admin_ghl_sync():
    """Manually trigger GHL Custom Value sync for network metrics"""
    try:
        result = ghl_service.sync_network_metrics()
        if result.get('success'):
            logging.info(f"GHL SYNC SUCCESS: Difficulty={result.get('difficulty')}, Hashrate={result.get('hashrate')}")
            return jsonify({
                'success': True,
                'message': 'GHL Custom Values synced successfully',
                'difficulty': result.get('difficulty'),
                'hashrate': result.get('hashrate'),
                'synced_at': result.get('synced_at')
            })
        else:
            return jsonify({'success': False, 'error': result.get('error')})
    except Exception as e:
        logging.error(f"GHL sync error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/social-listener', methods=['GET'])
@login_required
@admin_required
def admin_social_listener():
    """Get Social Intelligence Listener status and recent findings"""
    try:
        from services.social_listener import social_listener
        status = social_listener.get_status()
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        logging.error(f"Social Listener status error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/social-listener/scan', methods=['POST'])
@login_required
@admin_required
def admin_social_listener_scan():
    """Manually trigger a social listener scan"""
    try:
        from services.social_listener import social_listener
        if not social_listener.initialized:
            return jsonify({'success': False, 'error': 'Social Listener not initialized - check Twitter API credentials'})
        
        results = social_listener.scan_all_targets()
        logging.info(f"Social Listener manual scan: {results.get('scanned')} handles, {len(results.get('new_tweets', []))} new tweets")
        return jsonify({
            'success': True,
            'scanned': results.get('scanned'),
            'new_tweets': len(results.get('new_tweets', [])),
            'errors': len(results.get('errors', [])),
            'timestamp': results.get('timestamp')
        })
    except Exception as e:
        logging.error(f"Social Listener scan error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/generate-from-reddit', methods=['POST'])
@login_required
@admin_required
def generate_from_reddit():
    """Generate content from Reddit trending topics"""
    try:
        # Get Reddit trending topics
        trending_topics = reddit_service.get_trending_topics(['cryptocurrency', 'bitcoin', 'ethereum', 'web3'])
        
        if not trending_topics:
            return jsonify({'success': False, 'error': 'No trending topics found'})
        
        results = []
        for topic in trending_topics[:3]:  # Generate from top 3 topics
            try:
                result = content_engine.generate_content_from_reddit_trend(topic)
                results.append({
                    'topic': topic.get('title', 'Unknown'),
                    'result': result
                })
            except Exception as e:
                results.append({
                    'topic': topic.get('title', 'Unknown'),
                    'result': {'success': False, 'error': str(e)}
                })
        
        return jsonify({'success': True, 'results': results})
        
    except Exception as e:
        logging.error(f"Reddit content generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/ai-review/<int:article_id>', methods=['POST'])
@login_required
@admin_required
def ai_review_article(article_id):
    """Trigger AI review and auto-publishing for article"""
    try:
        # Use AI review workflow (Gemini as Editor-in-Chief)
        result = content_engine.approve_and_publish_article(article_id)
        
        if result["success"]:
            return jsonify({
                'success': True,
                'substack_url': result.get("substack_url"),
                'message': result.get("message"),
                'review': result.get("review")
            })
        else:
            return jsonify({
                'success': False,
                'errors': result.get("errors", ["Unknown error"]),
                'message': result.get("message"),
                'review': result.get("review")
            })
            
    except Exception as e:
        logging.error(f"AI review failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/write', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_write_article():
    """Admin page for writing manual articles"""
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        category = request.form.get('category', 'Bitcoin')
        author = request.form.get('author', current_user.username)
        seo_description = request.form.get('seo_description', '')
        tags = request.form.get('tags', '')
        is_pressing = request.form.get('is_pressing') == 'on'
        action = request.form.get('action', 'draft')
        
        if not title or not content:
            flash('Title and content are required.')
            return redirect('/admin/write')
        
        article = models.Article(
            title=title,
            content=content,
            category=category,
            author=author,
            seo_description=seo_description or title[:155],
            seo_title=title[:60],
            tags=tags,
            is_pressing=is_pressing,
            source_type='manual',
            published=(action == 'publish')
        )
        db.session.add(article)
        db.session.commit()
        
        if action == 'publish':
            flash(f'Article "{title}" published successfully!')
        else:
            flash(f'Article "{title}" saved as draft.')
        
        return redirect('/admin')
    
    return render_template('admin/write_article.html')

@admin_bp.route('/admin/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_edit_article(article_id):
    """Admin page for editing existing articles"""
    article = models.Article.query.get_or_404(article_id)
    
    if request.method == 'POST':
        article.title = request.form.get('title', '').strip()
        article.content = request.form.get('content', '').strip()
        article.category = request.form.get('category', 'Bitcoin')
        article.author = request.form.get('author', current_user.username)
        article.seo_description = request.form.get('seo_description', '') or article.title[:155]
        article.seo_title = article.title[:60]
        article.tags = request.form.get('tags', '')
        article.is_pressing = request.form.get('is_pressing') == 'on'
        action = request.form.get('action', 'publish')
        
        if not article.title or not article.content:
            flash('Title and content are required.')
            return redirect(f'/admin/edit/{article_id}')
        
        article.published = (action == 'publish')
        db.session.commit()
        
        if action == 'publish':
            flash(f'Article "{article.title}" updated and published!')
        else:
            flash(f'Article "{article.title}" saved as draft.')
        
        return redirect('/admin')
    
    return render_template('admin/edit_article.html', article=article)

@admin_bp.route('/admin/delete/<int:article_id>', methods=['DELETE'])
@login_required
@admin_required
def admin_delete_article(article_id):
    """Admin endpoint to delete an article"""
    try:
        article = models.Article.query.get_or_404(article_id)
        title = article.title
        db.session.delete(article)
        db.session.commit()
        logging.info(f"Article '{title}' (ID: {article_id}) deleted by {current_user.username}")
        return jsonify({'success': True, 'message': f'Article "{title}" deleted successfully'})
    except Exception as e:
        logging.error(f"Error deleting article {article_id}: {e}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/ads')
@login_required
@admin_required
def admin_ads():
    """Admin page for managing advertisements"""
    ads = models.Advertisement.query.all()
    return render_template('admin/ads.html', ads=ads)

@admin_bp.route('/admin/launch-sequences')
@login_required
@admin_required
def admin_launch_sequences():
    """View all launch sequences"""
    sequences = models.LaunchSequence.query.order_by(models.LaunchSequence.created_at.desc()).all()
    return render_template('admin_launch_sequences.html', sequences=sequences)

@admin_bp.route('/admin/launch-sequence/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_launch_sequence():
    """Create a new launch sequence"""
    if request.method == 'POST':
        from services.launch_sequence import launch_sequence_service
        
        content = request.form.get('content', '')
        content_type = request.form.get('content_type', 'article')
        content_id = request.form.get('content_id')
        
        result = launch_sequence_service.generate_launch_sequence(
            content=content,
            content_type=content_type,
            content_id=int(content_id) if content_id else None
        )
        
        seq = models.LaunchSequence(
            content_id=result.get('content_id'),
            content_type=result.get('content_type'),
            primary_post_copy=result.get('primary_post_copy'),
            thread_replies=result.get('thread_replies'),
            quote_variants=result.get('quote_variants'),
            reply_drafts=result.get('reply_drafts'),
            hashtags=result.get('hashtags'),
            posting_time=result.get('posting_time'),
            velocity_prediction=result.get('velocity_prediction'),
            first_reply_link=result.get('first_reply_link'),
            call_to_action=result.get('call_to_action'),
            status='draft'
        )
        db.session.add(seq)
        db.session.commit()
        
        flash('Launch sequence created successfully!')
        return redirect(url_for('admin.admin_launch_sequences'))
    
    articles = models.Article.query.filter_by(published=True).order_by(models.Article.created_at.desc()).limit(20).all()
    podcasts = models.Podcast.query.order_by(models.Podcast.published_date.desc()).limit(20).all()
    return render_template('create_launch_sequence.html', articles=articles, podcasts=podcasts)

@admin_bp.route('/admin/launch-sequence/<int:seq_id>')
@login_required
@admin_required
def view_launch_sequence(seq_id):
    """View a specific launch sequence"""
    import json
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    drafts = []
    if seq.reply_drafts:
        try:
            drafts = json.loads(seq.reply_drafts)
        except:
            pass
    return render_template('view_launch_sequence.html', sequence=seq, drafts=drafts)

@admin_bp.route('/admin/launch-sequence/<int:seq_id>/approve', methods=['GET', 'POST'])
@login_required
@admin_required
def approve_launch_sequence(seq_id):
    """Approve a launch sequence for use"""
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    seq.status = 'approved'
    seq.approved_at = datetime.utcnow()
    db.session.commit()
    flash('Launch sequence approved!')
    return redirect(url_for('admin.admin_launch_sequences'))

@admin_bp.route('/admin/launch-sequence/<int:seq_id>/regenerate', methods=['GET', 'POST'])
@login_required
@admin_required
def regenerate_launch_sequence(seq_id):
    """Regenerate a launch sequence with new content"""
    from services.launch_sequence import launch_sequence_service
    
    seq = models.LaunchSequence.query.get_or_404(seq_id)
    
    content = seq.primary_post_copy or ""
    if seq.content_id and seq.content_type == 'article':
        article = models.Article.query.get(seq.content_id)
        if article:
            content = f"{article.title}\n\n{article.summary or article.content[:500]}"
    
    result = launch_sequence_service.generate_launch_sequence(
        content=content,
        content_type=seq.content_type or 'article',
        content_id=seq.content_id
    )
    
    seq.primary_post_copy = result.get('primary_post_copy')
    seq.thread_replies = result.get('thread_replies')
    seq.quote_variants = result.get('quote_variants')
    seq.reply_drafts = result.get('reply_drafts')
    seq.hashtags = result.get('hashtags')
    seq.velocity_prediction = result.get('velocity_prediction')
    seq.status = 'draft'
    db.session.commit()
    
    flash('Launch sequence regenerated!')
    return redirect(url_for('admin.view_launch_sequence', seq_id=seq_id))

@admin_bp.route('/admin/target-alerts')
@login_required
@admin_required
def admin_target_alerts():
    """View all target alerts"""
    alerts = models.TargetAlert.query.order_by(models.TargetAlert.created_at.desc()).limit(50).all()
    return render_template('admin_target_alerts.html', alerts=alerts)

@admin_bp.route('/admin/target-alerts/scan', methods=['POST'])
@login_required
@admin_required
def scan_targets():
    """Scan RSS feeds for new opportunities"""
    from services.target_monitor import target_monitor_service
    
    alerts_data = target_monitor_service.scan_rss_feeds()
    
    for alert_data in alerts_data[:10]:
        drafts = target_monitor_service.generate_reply_drafts(
            alert_data['source_account'],
            alert_data['content_snippet']
        )
        
        alert = models.TargetAlert(
            trigger_type=alert_data['trigger_type'],
            source_url=alert_data['source_url'],
            source_account=alert_data['source_account'],
            content_snippet=alert_data['content_snippet'],
            priority=alert_data['priority'],
            strategy_suggested=alert_data.get('strategy_suggested', 'default'),
            draft_replies=json.dumps(drafts) if drafts else None,
            status='pending'
        )
        db.session.add(alert)
    
    db.session.commit()
    
    return jsonify({'success': True, 'count': len(alerts_data)})

@admin_bp.route('/admin/target-alert/<int:alert_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_alert(alert_id):
    """Approve an alert for posting"""
    alert = models.TargetAlert.query.get_or_404(alert_id)
    alert.status = 'approved'
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/admin/target-alert/<int:alert_id>/skip', methods=['POST'])
@login_required
@admin_required
def skip_alert(alert_id):
    """Skip an alert"""
    alert = models.TargetAlert.query.get_or_404(alert_id)
    alert.status = 'skipped'
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/admin/nostr')
@login_required
@admin_required
def admin_nostr():
    """Nostr broadcaster dashboard"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    status = nostr_broadcaster.get_relay_status()
    events = models.NostrEvent.query.order_by(models.NostrEvent.created_at.desc()).limit(50).all()
    
    return render_template('admin_nostr.html', status=status, events=events)

@admin_bp.route('/admin/nostr/test', methods=['POST'])
@login_required
@admin_required
def test_nostr():
    """Test Nostr broadcast"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    result = nostr_broadcaster.test_connection()
    
    if result.get('success'):
        event = models.NostrEvent(
            event_id=result.get('event_id'),
            content_type='test',
            relays_success=json.dumps(result.get('relays_success', [])),
            relays_failed=json.dumps(result.get('relays_failed', []))
        )
        db.session.add(event)
        db.session.commit()
    
    return jsonify(result)

@admin_bp.route('/admin/nostr/broadcast', methods=['POST'])
@login_required
@admin_required
def broadcast_to_nostr():
    """Broadcast content to Nostr"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    data = request.get_json() or {}
    content = data.get('content', '')
    content_type = data.get('type', 'note')
    content_id = data.get('content_id')
    
    if not content:
        return jsonify({'error': 'Content required'}), 400
    
    result = nostr_broadcaster.broadcast_note(content)
    
    if result.get('success') or result.get('simulated'):
        event = models.NostrEvent(
            event_id=result.get('event_id'),
            content_type=content_type,
            content_id=content_id,
            relays_success=json.dumps(result.get('relays_success', [])),
            relays_failed=json.dumps(result.get('relays_failed', []))
        )
        db.session.add(event)
        db.session.commit()
    
    return jsonify(result)

@admin_bp.route('/admin/intelligence')
@login_required
@admin_required
def intelligence_dashboard():
    """Main intelligence dashboard with all metrics"""
    from services.nostr_broadcaster import nostr_broadcaster
    
    articles_count = models.Article.query.filter_by(published=True).count()
    podcasts_count = models.Podcast.query.count()
    
    launch_sequences = models.LaunchSequence.query.order_by(models.LaunchSequence.created_at.desc()).limit(5).all()
    pending_sequences = models.LaunchSequence.query.filter_by(status='draft').count()
    
    target_alerts = models.TargetAlert.query.filter_by(status='pending').order_by(models.TargetAlert.created_at.desc()).limit(5).all()
    pending_alerts = models.TargetAlert.query.filter_by(status='pending').count()
    
    nostr_status = nostr_broadcaster.get_relay_status()
    nostr_events = models.NostrEvent.query.count()
    total_zaps = db.session.query(db.func.sum(models.NostrEvent.zaps_amount_sats)).scalar() or 0
    
    avg_velocity = db.session.query(db.func.avg(models.LaunchSequence.actual_velocity_score)).filter(
        models.LaunchSequence.actual_velocity_score.isnot(None)
    ).scalar() or 0
    
    reply_squad = models.ReplySquadMember.query.filter_by(active=True).order_by(
        models.ReplySquadMember.reciprocal_engagements.desc()
    ).limit(10).all()
    
    return render_template('intelligence_dashboard.html',
        articles_count=articles_count,
        podcasts_count=podcasts_count,
        launch_sequences=launch_sequences,
        pending_sequences=pending_sequences,
        target_alerts=target_alerts,
        pending_alerts=pending_alerts,
        nostr_status=nostr_status,
        nostr_events=nostr_events,
        total_zaps=total_zaps,
        avg_velocity=avg_velocity,
        reply_squad=reply_squad
    )

@admin_bp.route('/admin/reply-squad')
@login_required
@admin_required
def admin_reply_squad():
    """Manage reply squad members"""
    members = models.ReplySquadMember.query.order_by(models.ReplySquadMember.priority, models.ReplySquadMember.handle).all()
    return render_template('admin_reply_squad.html', members=members)

@admin_bp.route('/admin/reply-squad/add', methods=['POST'])
@login_required
@admin_required
def add_reply_squad_member():
    """Add a new reply squad member"""
    data = request.get_json() or request.form
    
    member = models.ReplySquadMember(
        handle=data.get('handle', ''),
        display_name=data.get('display_name', ''),
        category=data.get('category', 'general'),
        priority=int(data.get('priority', 2)),
        notes=data.get('notes', '')
    )
    db.session.add(member)
    db.session.commit()
    
    if request.is_json:
        return jsonify({'success': True, 'id': member.id})
    flash('Reply squad member added!')
    return redirect(url_for('admin.admin_reply_squad'))

@admin_bp.route('/admin/reply-squad/init', methods=['POST'])
@login_required
@admin_required
def init_reply_squad():
    """Initialize reply squad with default members"""
    from services.target_monitor import REPLY_SQUAD
    
    for member_data in REPLY_SQUAD:
        existing = models.ReplySquadMember.query.filter_by(handle=member_data['handle']).first()
        if not existing:
            member = models.ReplySquadMember(
                handle=member_data['handle'],
                display_name=member_data.get('name', ''),
                category=member_data.get('category', 'general'),
                priority=member_data.get('priority', 2)
            )
            db.session.add(member)
    
    db.session.commit()
    flash('Reply squad initialized!')
    return redirect(url_for('admin.admin_reply_squad'))

@admin_bp.route('/admin/auth-cleanup', methods=['POST'])
@login_required
@admin_required
def admin_auth_cleanup():
    """Purge all Orange Is The New Jill related data from database"""
    try:
        purged_count = 0
        
        # Clean up articles with Orange Is The New Jill content
        articles = models.Article.query.filter(
            db.or_(
                models.Article.title.ilike('%orange is the new jill%'),
                models.Article.title.ilike('%orange is the nw jill%'),
                models.Article.content.ilike('%orange is the new jill%')
            )
        ).all()
        
        for article in articles:
            db.session.delete(article)
            purged_count += 1
        
        # Clean up podcasts with Orange Is The New Jill content
        podcasts = models.Podcast.query.filter(
            db.or_(
                models.Podcast.title.ilike('%orange is the new jill%'),
                models.Podcast.title.ilike('%orange is the nw jill%'),
                models.Podcast.description.ilike('%orange is the new jill%')
            )
        ).all()
        
        for podcast in podcasts:
            db.session.delete(podcast)
            purged_count += 1
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'purged_count': purged_count,
            'message': f'Successfully purged {purged_count} Orange Is The New Jill items'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/revenue')
@login_required
@admin_required
def admin_revenue():
    """Revenue dashboard"""
    from services.monetization_service import monetization_service
    
    stats = monetization_service.get_revenue_stats()
    return render_template('admin_revenue.html', stats=stats)

@admin_bp.route('/admin/contact-submissions')
@login_required
@admin_required
def admin_contact_submissions():
    """List contact form submissions; filter by read/unread."""
    read_filter = request.args.get('read', '')
    q = models.ContactSubmission.query
    if read_filter == 'read':
        q = q.filter_by(read=True)
    elif read_filter == 'unread':
        q = q.filter_by(read=False)
    submissions = q.order_by(models.ContactSubmission.created_at.desc()).limit(200).all()
    unread_count = models.ContactSubmission.query.filter_by(read=False).count()
    return render_template('admin/contact_submissions.html', submissions=submissions, read_filter=read_filter, unread_count=unread_count)

@admin_bp.route('/admin/contact-submissions/<int:sub_id>/read', methods=['POST'])
@login_required
@admin_required
def admin_contact_submission_mark_read(sub_id):
    """Mark a contact submission as read."""
    _require_csrf()
    sub = models.ContactSubmission.query.get_or_404(sub_id)
    sub.read = True
    db.session.commit()
    flash('Marked as read.', 'success')
    return redirect(url_for('admin.admin_contact_submissions'))

@admin_bp.route('/admin/premium-asks')
@login_required
@admin_required
def admin_premium_asks():
    """List Sovereign Elite monthly asks; filter by status."""
    status_filter = request.args.get('status', '')
    q = models.PremiumAsk.query
    if status_filter in ('pending', 'answered'):
        q = q.filter_by(status=status_filter)
    asks = q.order_by(models.PremiumAsk.created_at.desc()).limit(100).all()
    pending_count = models.PremiumAsk.query.filter_by(status='pending').count()
    return render_template('admin/premium_asks.html', asks=asks, status_filter=status_filter, pending_count=pending_count)

@admin_bp.route('/admin/premium-asks/<int:ask_id>/answer', methods=['POST'])
@login_required
@admin_required
def admin_premium_ask_answer(ask_id):
    """Mark a PremiumAsk as answered with optional text and URL."""
    from datetime import datetime
    ask = models.PremiumAsk.query.get_or_404(ask_id)
    answer_text = (request.form.get('answer_text') or '').strip()
    answer_url = (request.form.get('answer_url') or '').strip()[:500]
    ask.answer_text = answer_text or None
    ask.answer_url = answer_url or None
    ask.status = 'answered'
    ask.answered_at = datetime.utcnow()
    db.session.commit()
    flash('Ask marked as answered.')
    return redirect(url_for('admin.admin_premium_asks'))

@admin_bp.route('/admin/captions')
@login_required
@admin_required
def admin_captions():
    """Captions.ai video generation dashboard"""
    from services.captions_service import captions_service
    return render_template('admin_captions.html', 
                         initialized=captions_service.initialized,
                         avatars=captions_service.AVATARS)

@admin_bp.route('/admin/api/captions/generate', methods=['POST'])
@login_required
@admin_required
def generate_captions_video():
    """Generate AI avatar video via Captions.ai"""
    from services.captions_service import captions_service
    
    data = request.get_json()
    script = data.get('script', '')
    avatar_type = data.get('avatar', 'alex')
    
    if not script:
        return jsonify({'error': 'Script is required'}), 400
    
    if len(script) > 800:
        return jsonify({'error': 'Script must be 800 characters or less'}), 400
    
    result = captions_service.create_video(script, avatar_type)
    
    if result:
        return jsonify({
            'success': True,
            'video_id': result.get('video_id'),
            'status': result.get('status'),
            'message': 'Video generation started'
        })
    else:
        return jsonify({'error': 'Failed to start video generation'}), 500

@admin_bp.route('/admin/api/captions/status/<video_id>')
@login_required
@admin_required
def check_captions_status(video_id):
    """Check status of Captions.ai video generation"""
    from services.captions_service import captions_service
    
    result = captions_service.check_video_status(video_id)
    
    if result:
        return jsonify(result)
    else:
        return jsonify({'error': 'Failed to check video status'}), 500

@admin_bp.route('/admin/api/captions/daily-brief', methods=['POST'])
@login_required
@admin_required
def generate_daily_brief_video():
    """Generate daily brief video with network data"""
    from services.captions_service import captions_service
    from services.node_service import node_service
    
    data = request.get_json()
    avatar_type = data.get('avatar', 'sarah')
    
    # Get current network data
    network_data = node_service.get_network_stats()
    network_data['price'] = node_service.get_bitcoin_price() or 0
    
    result = captions_service.generate_daily_brief(network_data, avatar_type)
    
    if result:
        return jsonify({
            'success': True,
            'video_id': result.get('video_id'),
            'status': result.get('status'),
            'message': 'Daily brief video generation started'
        })
    else:
        return jsonify({'error': 'Failed to generate daily brief'}), 500

@admin_bp.route('/admin/analytics')
@admin_required
def analytics_dashboard():
    """Sovereign Analytics Dashboard - Self-learning intelligence metrics."""
    from services.analytics_service import analytics_service

    # Get key metrics
    velocity_leaders = analytics_service.get_velocity_leaders(hours=24, limit=10)
    persona_comparison = analytics_service.get_persona_comparison(days=7)
    strategy_effectiveness = analytics_service.get_strategy_effectiveness(days=7)
    hourly_performance = analytics_service.get_hourly_performance(days=7)
    window_stats = analytics_service.get_30min_window_stats(days=7)
    sponsor_metrics = analytics_service.get_sponsor_metrics(days=30)
    
    # Recent events
    recent_events = models.EngagementEvent.query.order_by(
        models.EngagementEvent.created_at.desc()
    ).limit(20).all()
    
    # Top performers all-time
    top_performers = models.ContentPerformance.query.order_by(
        models.ContentPerformance.grok_score_total.desc()
    ).limit(5).all()
    
    return render_template('admin/analytics_dashboard.html',
        velocity_leaders=velocity_leaders,
        persona_comparison=persona_comparison,
        strategy_effectiveness=strategy_effectiveness,
        hourly_performance=hourly_performance,
        window_stats=window_stats,
        sponsor_metrics=sponsor_metrics,
        recent_events=recent_events,
        top_performers=top_performers
    )

@admin_bp.route('/admin/supervisor')
@admin_required
def supervisor_dashboard():
    """Multi-Agent Supervisor Dashboard - Alex & Sarah orchestration."""
    return render_template('admin/supervisor_dashboard.html')

@admin_bp.route('/admin/segments')
@admin_required
def segments_dashboard():
    """Audience Segmentation Dashboard - K-Means clustering visualization."""
    try:
        from services.audience_segmentation import segmentation_engine
        
        summary = segmentation_engine.get_segment_summary()
        
        return render_template(
            'admin/segments_dashboard.html',
            segments=summary.get('segments', []),
            total_users=summary.get('total_users', 0),
            is_trained=segmentation_engine.is_trained
        )
    except Exception as e:
        logging.error(f"Segments dashboard error: {e}")
        return render_template(
            'admin/segments_dashboard.html',
            segments=[],
            total_users=0,
            is_trained=False,
            error=str(e)
        )

@admin_bp.route('/admin/deck')
@login_required
@admin_required
def admin_deck():
    """Real-Time Sponsorship Deck: live views and impressions for sponsor conversations."""
    from services.sponsorship_metrics_service import get_sponsorship_metrics
    from pathlib import Path
    data_dir = Path(app.root_path) / "data"
    metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db.session, days_back=30)
    return render_template('admin/sponsorship_deck.html', metrics=metrics)

@admin_bp.route('/admin/deck/export-pdf')
@login_required
@admin_required
def admin_deck_export_pdf():
    """Generate Red/Black/White PDF summary of sponsorship metrics."""
    from services.sponsorship_metrics_service import get_sponsorship_metrics
    from pathlib import Path
    from io import BytesIO
    data_dir = Path(app.root_path) / "data"
    metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db.session, days_back=30)
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except ImportError:
        return "reportlab not installed. pip install reportlab", 503
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name="DeckTitle", parent=styles["Heading1"], textColor=colors.HexColor("#dc2626"), fontName="Helvetica-Bold", fontSize=18)
    body_style = ParagraphStyle(name="DeckBody", parent=styles["Normal"], textColor=colors.white, fontName="Helvetica", fontSize=10)
    white = colors.HexColor("#ffffff")
    red = colors.HexColor("#dc2626")
    black = colors.HexColor("#0a0a0a")
    story = []
    story.append(Paragraph("PROTOCOL PULSE — SPONSORSHIP METRICS", title_style))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"Period: last {metrics['period_days']} days. Generated: {metrics['generated_at'][:19]} UTC.", body_style))
    story.append(Spacer(1, 0.4 * inch))
    data = [
        ["Metric", "Value", "Source"],
        ["YouTube views", str(metrics.get("youtube_views", 0)), metrics.get("youtube_source", "—")],
        ["Website unique visits", str(metrics.get("website_unique_visits", 0)), metrics.get("website_source", "—")],
        ["Social impressions (X)", str(metrics.get("social_impressions", 0)), metrics.get("social_source", "—")],
    ]
    t = Table(data, colWidths=[2.2 * inch, 1.5 * inch, 1.5 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), red),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BACKGROUND", (0, 1), (-1, -1), black),
        ("TEXTCOLOR", (0, 1), (-1, -1), white),
        ("GRID", (0, 0), (-1, -1), 0.5, red),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [black, colors.HexColor("#1a1a1a")]),
    ]))
    story.append(t)
    doc.build(story)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="protocol_pulse_sponsorship_deck.pdf")

@admin_bp.route('/admin/command-deck')
@admin_required
def command_deck():
    """Sovereign Command Deck - System control center"""
    scheduler_status = {'running': False, 'jobs': []}
    telegram_status = {'initialized': False}
    try:
        from services.scheduler import get_scheduler_status
        scheduler_status = get_scheduler_status()
    except Exception as e:
        logging.debug("Scheduler not available: %s", e)
    try:
        from services.telegram_bot import pulse_operative
        telegram_status = pulse_operative.get_status()
    except Exception:
        pass  # telegram_bot optional
    return render_template('admin/command_deck.html',
        scheduler_status=scheduler_status,
        telegram_status=telegram_status,
        deck_time=datetime.utcnow()
    )

@admin_bp.route('/admin/api/activate-scheduler', methods=['POST'])
@admin_required
def activate_scheduler():
    """Activate the sovereign scheduler"""
    try:
        from services.scheduler import initialize_scheduler, get_scheduler_status
        
        initialize_scheduler()
        status = get_scheduler_status()
        
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        logging.error(f"Scheduler activation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/send-heartbeat', methods=['POST'])
@admin_required
def send_heartbeat():
    """Send Empire Ready heartbeat to Telegram"""
    try:
        from services.sovereign_heartbeat import send_heartbeat_sync, get_system_status
        
        result = send_heartbeat_sync()
        status = get_system_status()
        
        return jsonify({
            'success': result.get('success', False),
            'error': result.get('error'),
            'system_status': status
        })
    except Exception as e:
        logging.error(f"Heartbeat error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/system-status')
@admin_required
def get_system_status_api():
    """Get current system status"""
    try:
        from services.sovereign_heartbeat import get_system_status
        return jsonify(get_system_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/clips/status')
@admin_required
def clips_status_api():
    """Get AI Clips service status"""
    try:
        from services.ai_clips_service import ai_clips_service
        return jsonify(ai_clips_service.get_status())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/clips/generate', methods=['POST'])
@admin_required
def generate_clips_api():
    """Trigger daily clips generation job"""
    try:
        from services.ai_clips_service import ai_clips_service
        results = ai_clips_service.run_daily_clips_job()
        return jsonify(results)
    except Exception as e:
        logging.error(f"Clips generation error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/clips/process-video', methods=['POST'])
@admin_required
def process_video_clips_api():
    """Process a specific YouTube video for clips"""
    try:
        from services.ai_clips_service import ai_clips_service
        data = request.get_json()
        video_id = data.get('video_id')
        video_title = data.get('title', 'Untitled')
        channel_name = data.get('channel', 'Manual')
        max_clips = data.get('max_clips', 2)
        
        if not video_id:
            return jsonify({'error': 'video_id required'}), 400
        
        results = ai_clips_service.process_video(video_id, video_title, channel_name, max_clips)
        return jsonify({'success': True, 'clips': results})
    except Exception as e:
        logging.error(f"Video processing error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/clips/channels')
@admin_required
def get_clips_channels_api():
    """Get configured clips channels"""
    try:
        from services.ai_clips_service import ai_clips_service
        channels = []
        for ch in ai_clips_service.CLIPS_CHANNELS:
            daily_count = ai_clips_service._get_daily_count(ch['id'])
            channels.append({
                **ch,
                'today_count': daily_count,
                'remaining': ch.get('daily_limit', 1) - daily_count
            })
        return jsonify(channels)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/collect-signals', methods=['POST'])
@admin_required
def collect_signals_api():
    """Trigger signal collection from X, Nostr, and Stacker News APIs"""
    try:
        from services.sentiment_tracker_service import SentimentTrackerService
        tracker = SentimentTrackerService()
        
        x_posts = tracker.fetch_x_posts(hours_back=24)
        nostr_notes = tracker.fetch_nostr_notes(hours_back=24)
        stacker_posts = tracker.fetch_stacker_news(limit=15)
        all_posts = x_posts + nostr_notes + stacker_posts
        saved = tracker.save_signals_to_db(all_posts)
        return jsonify({
            'success': True,
            'collected': {
                'x_posts': len(x_posts),
                'nostr_notes': len(nostr_notes),
                'stacker_news': len(stacker_posts)
            },
            'saved_to_db': saved,
            'message': f'Collected {len(x_posts)} X, {len(nostr_notes)} Nostr, {len(stacker_posts)} Stacker News; saved {saved} new signals'
        })
    except Exception as e:
        logging.error(f"Signal collection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/signals')
@admin_required
def get_collected_signals_api():
    """Get collected signals from database"""
    try:
        
        limit = request.args.get('limit', 50, type=int)
        platform = request.args.get('platform', None)
        legendary_only = request.args.get('legendary', 'false').lower() == 'true'
        
        query = models.CollectedSignal.query.filter(models.CollectedSignal.is_verified == True)
        
        if platform:
            query = query.filter(models.CollectedSignal.platform == platform)
        if legendary_only:
            query = query.filter(models.CollectedSignal.is_legendary == True)
        
        signals = query.order_by(
            models.CollectedSignal.is_legendary.desc(),
            models.CollectedSignal.engagement_score.desc()
        ).limit(limit).all()
        
        return jsonify({
            'success': True,
            'count': len(signals),
            'signals': [{
                'id': s.id,
                'platform': s.platform,
                'author_name': s.author_name,
                'author_handle': s.author_handle,
                'author_tier': s.author_tier,
                'content': s.content,
                'url': s.url,
                'engagement_score': s.engagement_score,
                'is_legendary': s.is_legendary,
                'posted_at': s.posted_at.isoformat() if s.posted_at else None,
                'collected_at': s.collected_at.isoformat() if s.collected_at else None
            } for s in signals]
        })
    except Exception as e:
        logging.error(f"Error fetching signals: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/zero-hour-audit', methods=['GET'])
@admin_required
def zero_hour_audit():
    """Zero Hour Readiness Audit - Test all system connections"""
    from sqlalchemy import text
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'telegram': {'status': 'UNKNOWN', 'message': ''},
        'ghl': {'status': 'UNKNOWN', 'message': ''},
        'database': {'status': 'UNKNOWN', 'message': ''},
        'overall': 'CHECKING'
    }
    
    try:
        result = db.session.execute(text('SELECT 1'))
        result.fetchone()
        results['database'] = {'status': 'ONLINE', 'message': 'PostgreSQL connection verified'}
    except Exception as e:
        results['database'] = {'status': 'OFFLINE', 'message': str(e)}
    
    try:
        ghl_result = ghl_service.verify_api_connection()
        if ghl_result.get('success'):
            results['ghl'] = {'status': 'ONLINE', 'message': f"API verified - Status {ghl_result.get('status_code', 200)}"}
        else:
            results['ghl'] = {'status': 'DEGRADED', 'message': ghl_result.get('error', 'Unknown error')}
    except Exception as e:
        results['ghl'] = {'status': 'OFFLINE', 'message': str(e)}
    
    try:
        from services.telegram_bot import pulse_operative
        if pulse_operative and pulse_operative.initialized:
            import requests as tg_requests
            tg_token = os.environ.get('TELEGRAM_BOT_TOKEN')
            tg_chat = os.environ.get('TELEGRAM_CHAT_ID')
            
            if tg_token and tg_chat:
                tg_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                tg_payload = {
                    'chat_id': tg_chat,
                    'text': '🟢 *ZERO HOUR AUDIT*\n\n_Heartbeat confirmed. System operational._\n\n⚡ Protocol Pulse Intelligence',
                    'parse_mode': 'Markdown'
                }
                tg_response = tg_requests.post(tg_url, json=tg_payload, timeout=10)
                
                if tg_response.status_code == 200:
                    results['telegram'] = {'status': 'ONLINE', 'message': 'Heartbeat dispatched successfully'}
                else:
                    results['telegram'] = {'status': 'DEGRADED', 'message': f'API returned {tg_response.status_code}'}
            else:
                results['telegram'] = {'status': 'OFFLINE', 'message': 'Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID'}
        else:
            results['telegram'] = {'status': 'OFFLINE', 'message': 'Bot not initialized - check TELEGRAM_BOT_TOKEN'}
    except Exception as e:
        results['telegram'] = {'status': 'OFFLINE', 'message': str(e)}
    
    all_online = all(r['status'] == 'ONLINE' for r in [results['telegram'], results['ghl'], results['database']])
    results['overall'] = 'EMPIRE READY' if all_online else 'DEGRADED'
    
    return jsonify(results)

@admin_bp.route('/admin/api/ghl-webhook-test', methods=['POST'])
@admin_required
def ghl_webhook_test():
    """Send test webhook payload to GHL with operative data"""
    try:
        result = ghl_service.send_webhook_test(
            first_name="Test Operative",
            signal_points=750,
            sovereign_segment="Sovereign Node"
        )
        return jsonify(result)
    except Exception as e:
        logging.error(f"GHL webhook test error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/ghl-verify', methods=['GET'])
@admin_required
def ghl_verify():
    """Verify GHL API connection returns 200 OK"""
    try:
        result = ghl_service.verify_api_connection()
        return jsonify(result)
    except Exception as e:
        logging.error(f"GHL verification error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/sarah-welcome', methods=['POST'])
@admin_required
def trigger_sarah_welcome():
    """Trigger Sarah Welcome emails to recent Scorecard completers"""
    try:
        result = ghl_service.send_sarah_welcome_to_recent_scorecard_users()
        return jsonify(result)
    except Exception as e:
        logging.error(f"Sarah Welcome error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/sms-test-pulse', methods=['POST'])
@admin_required
def sms_test_pulse():
    """Send a test SMS pulse from the Command Deck"""
    try:
        from services.sms_service import sms_service
        
        data = request.get_json() or {}
        phone_number = data.get('phone_number')
        contact_id = data.get('contact_id')
        
        if not phone_number and not contact_id:
            return jsonify({'success': False, 'error': 'Phone number or contact ID required'}), 400
        
        result = sms_service.send_test_pulse(phone_number=phone_number, contact_id=contact_id)
        return jsonify(result)
    except Exception as e:
        logging.error(f"SMS test pulse error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/whale-sms-dispatch', methods=['POST'])
@admin_required
def whale_sms_dispatch():
    """Dispatch SMS alert for mega-whale transaction"""
    try:
        from services.sms_service import sms_service
        
        data = request.get_json() or {}
        btc_amount = data.get('btc_amount', 1000)
        source = data.get('source', 'cold storage')
        destination = data.get('destination', 'Exchange')
        alex_analysis = data.get('alex_analysis', 'High sell pressure detected')
        
        result = sms_service.mega_whale_alert(btc_amount, source, destination, alex_analysis)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Whale SMS dispatch error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/autopost')
@login_required
@admin_required
def admin_autopost():
    """Admin UI for autopost drafts and daily briefs"""
    drafts = models.AutoPostDraft.query.order_by(models.AutoPostDraft.created_at.desc()).limit(50).all()
    daily_briefs = models.DailyBrief.query.order_by(models.DailyBrief.created_at.desc()).limit(10).all()
    return render_template('admin/autopost.html', drafts=drafts, daily_briefs=daily_briefs)

@admin_bp.route('/admin/api/autopost/<int:draft_id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_autopost(draft_id):
    """Approve an autopost draft"""
    draft = models.AutoPostDraft.query.get_or_404(draft_id)
    
    autopost_enabled = os.environ.get('AUTOPOST_X', 'false').lower() == 'true'
    
    if autopost_enabled:
        draft.status = 'posted'
        draft.posted_at = datetime.utcnow()
    else:
        draft.status = 'approved'
        draft.approved_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'success': True, 'status': draft.status})

@admin_bp.route('/admin/api/autopost/<int:draft_id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_autopost(draft_id):
    """Reject an autopost draft"""
    draft = models.AutoPostDraft.query.get_or_404(draft_id)
    draft.status = 'rejected'
    db.session.commit()
    
    return jsonify({'success': True})

@admin_bp.route('/admin/api/generate-daily-brief', methods=['POST'])
@login_required
@admin_required
def generate_daily_brief_api():
    """Generate a new daily brief from Sarah"""
    try:
        from services.sarah_analyst import sarah_analyst
        
        feed_items = models.FeedItem.query.order_by(models.FeedItem.created_at.desc()).limit(50).all()
        
        top_signals = sarah_analyst.analyze_signals(feed_items, limit=3)
        
        sentiment = models.SentimentSnapshot.query.order_by(models.SentimentSnapshot.created_at.desc()).first()
        sentiment_data = None
        if sentiment:
            sentiment_data = {'state': sentiment.state, 'score': sentiment.score}
        
        brief_data = sarah_analyst.generate_daily_brief(top_signals, sentiment_data)
        
        signals_json = json.dumps([{
            'title': s['item'].title,
            'source': s['item'].source,
            'score': s['score'],
            'sovereignty_impact': s['sovereignty_impact'],
            'reasons': s['reasons']
        } for s in top_signals])
        
        brief = models.DailyBrief(
            headline=brief_data['headline'],
            body=brief_data['body'],
            signals_json=signals_json,
            status='draft'
        )
        db.session.add(brief)
        db.session.commit()
        
        return jsonify({'success': True, 'brief_id': brief.id})
    except Exception as e:
        logging.error(f"Daily brief generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/daily-brief/<int:brief_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_daily_brief(brief_id):
    """Publish a daily brief"""
    brief = models.DailyBrief.query.get_or_404(brief_id)
    
    if brief.status == 'published':
        return jsonify({'success': False, 'error': 'Brief already published'}), 400
    
    if brief.status != 'draft':
        return jsonify({'success': False, 'error': 'Only draft briefs can be published'}), 400
    
    brief.status = 'published'
    brief.published_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/admin/api/daily-brief/<int:brief_id>/create-tweet', methods=['POST'])
@login_required
@admin_required
def create_tweet_from_brief(brief_id):
    """Create a tweet draft from a daily brief"""
    try:
        from services.sarah_analyst import sarah_analyst
        
        brief = models.DailyBrief.query.get_or_404(brief_id)
        
        signals = json.loads(brief.signals_json) if brief.signals_json else []
        mock_signals = [{'item': type('obj', (object,), {'title': s.get('title', 'Signal'), 'source': s.get('source', 'Unknown')})(), 'sovereignty_impact': s.get('sovereignty_impact', 5)} for s in signals]
        
        tweet_body = sarah_analyst.generate_tweet_draft({'signals': mock_signals})
        tweet_body = tweet_body.replace('{link}', f'/briefs/{brief.id}')
        
        draft = models.AutoPostDraft(
            platform='x',
            body=tweet_body,
            reason=f'Daily Brief #{brief.id}',
            status='draft'
        )
        db.session.add(draft)
        db.session.commit()
        
        return jsonify({'success': True, 'draft_id': draft.id})
    except Exception as e:
        logging.error(f"Tweet creation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/crm-setup')
@login_required
@admin_required
def crm_setup_wizard():
    """CRM Setup Wizard with step-by-step configuration"""
    current_api_key = os.environ.get('GHL_API_KEY', '')
    current_location_id = os.environ.get('GHL_LOCATION_ID', '')
    masked_key = f"{current_api_key[:8]}...{current_api_key[-4:]}" if current_api_key and len(current_api_key) > 12 else ''
    
    return render_template('admin/crm_setup.html',
                         current_api_key=masked_key,
                         current_location_id=current_location_id)

@admin_bp.route('/admin/api/crm-setup/save-keys', methods=['POST'])
@login_required
@admin_required
def save_crm_keys():
    """Save CRM API keys - Note: User must manually add to Secrets tab"""
    try:
        data = request.get_json()
        api_key = data.get('api_key', '')
        location_id = data.get('location_id', '')
        
        if not api_key or not location_id:
            return jsonify({'success': False, 'error': 'Both API Key and Location ID are required'})
        
        return jsonify({
            'success': True,
            'message': 'Configuration validated. Add GHL_API_KEY and GHL_LOCATION_ID to your Secrets tab.',
            'instructions': 'Go to Tools → Secrets and add: GHL_API_KEY and GHL_LOCATION_ID'
        })
    except Exception as e:
        logging.error(f"CRM key save error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/crm-setup/test')
@login_required
@admin_required
def test_crm_connection():
    """Test CRM connection to HighLevel"""
    try:
        api_key = os.environ.get('GHL_API_KEY')
        location_id = os.environ.get('GHL_LOCATION_ID')
        
        if not api_key or not location_id:
            return jsonify({
                'success': False,
                'error': 'API Key or Location ID not configured in Secrets'
            })
        
        import requests
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        response = requests.get(
            f'https://services.leadconnectorhq.com/locations/{location_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return jsonify({'success': True, 'message': 'Connection verified'})
        else:
            return jsonify({
                'success': False,
                'error': f'HighLevel returned status {response.status_code}: {response.text[:100]}'
            })
            
    except Exception as e:
        logging.error(f"CRM test error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/crm-setup/send-test-payload', methods=['POST'])
@login_required
@admin_required
def send_test_crm_payload():
    """Send a test Recruit payload to HighLevel"""
    try:
        api_key = os.environ.get('GHL_API_KEY')
        location_id = os.environ.get('GHL_LOCATION_ID')
        
        if not api_key or not location_id:
            return jsonify({
                'success': False,
                'error': 'API Key or Location ID not configured'
            })
        
        import requests
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'Version': '2021-07-28'
        }
        
        test_payload = {
            'firstName': 'Protocol',
            'lastName': 'Test',
            'email': f'test-{datetime.utcnow().strftime("%Y%m%d%H%M%S")}@protocolpulse.test',
            'tags': ['PP_Recruit', 'PP_Test'],
            'source': 'Protocol Pulse CRM Test',
            'locationId': location_id
        }
        
        response = requests.post(
            'https://services.leadconnectorhq.com/contacts/',
            headers=headers,
            json=test_payload,
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            return jsonify({'success': True, 'message': 'Test contact created in HighLevel'})
        else:
            return jsonify({
                'success': False,
                'error': f'HighLevel returned {response.status_code}: {response.text[:200]}'
            })
            
    except Exception as e:
        logging.error(f"CRM test payload error: {e}")
        return jsonify({'success': False, 'error': str(e)})

@admin_bp.route('/admin/api/realtime-stats')
@login_required
@admin_required
def api_realtime_stats():
    """API endpoint for real-time stats refresh"""
    try:
        from services.realtime_intel import realtime_intel
        return jsonify(realtime_intel.get_realtime_stats())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/approve-tweet/<int:tweet_id>', methods=['POST'])
@login_required
@admin_required
def api_approve_tweet(tweet_id):
    """Approve a peak tweet for posting"""
    try:
        from services.realtime_intel import realtime_intel
        success = realtime_intel.approve_tweet(tweet_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/dismiss-tweet/<int:tweet_id>', methods=['POST'])
@login_required
@admin_required
def api_dismiss_tweet(tweet_id):
    """Dismiss a peak tweet draft"""
    try:
        tweet = models.AutoTweet.query.get(tweet_id)
        if tweet:
            tweet.status = 'dismissed'
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Tweet not found'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/generate-suggestions', methods=['POST'])
@login_required
@admin_required
def api_generate_suggestions():
    """Manually trigger content suggestion generation"""
    try:
        from services.realtime_intel import realtime_intel
        suggestions = realtime_intel.generate_content_suggestions()
        return jsonify({
            'success': True,
            'count': len(suggestions),
            'suggestions': [s.title for s in suggestions if s]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def _seed_affiliate_products_if_empty():
    """Seed default affiliate products for cold wallets, seed plates, miners (only if none exist)."""
    if models.AffiliateProduct.query.first():
        return
    from services.monetization_service import monetization_service
    defaults = [
        {'name': 'Trezor Model T', 'product_type': 'trezor', 'product_id': 'trezor-model-t', 'category': 'cold_wallet', 'short_description': 'Hardware wallet with touchscreen and passphrase support.'},
        {'name': 'Trezor Safe 3', 'product_type': 'trezor', 'product_id': 'trezor-safe-3', 'category': 'cold_wallet', 'short_description': 'Secure hardware wallet for Bitcoin self-custody.'},
        {'name': 'Ledger Nano X', 'product_type': 'amazon', 'product_id': 'B07S5JQ7M2', 'category': 'cold_wallet', 'short_description': 'Bluetooth hardware wallet (Amazon).'},
        {'name': 'Cryptosteel Capsule', 'product_type': 'amazon', 'product_id': 'B09V2R9Q7K', 'category': 'seed_plate', 'short_description': 'Fire- and shock-resistant seed phrase backup.'},
        {'name': 'Bitaxe Miner', 'product_type': 'amazon', 'product_id': 'B0B1XYZ', 'category': 'miner', 'short_description': 'DIY Bitcoin mining (use real ASIN when you have one).'},
    ]
    for d in defaults:
        url = monetization_service.generate_affiliate_link(d['product_type'], d['product_id'])
        p = models.AffiliateProduct(
            name=d['name'],
            product_type=d['product_type'],
            product_id=d['product_id'],
            category=d['category'],
            short_description=d['short_description'],
            affiliate_url=url or '',
            active=True,
        )
        db.session.add(p)
    db.session.commit()
    logging.info("Seeded affiliate products.")

@admin_bp.route('/admin/smart-analytics')
@login_required
@admin_required
def admin_smart_analytics():
    """Smart analytics dashboard: all metrics, user preferences, affiliate performance, revenue."""
    try:
        _seed_affiliate_products_if_empty()
        from services.smart_analytics_service import smart_analytics_service
        from services.monetization_service import monetization_service
        days = request.args.get('days', 7, type=int)
        if days not in (1, 7, 14, 30):
            days = 7
        data = smart_analytics_service.get_smart_dashboard_data(days=days)
        revenue = monetization_service.get_revenue_stats()
        return render_template('admin/smart_analytics.html',
                             data=data,
                             revenue=revenue,
                             days=days)
    except Exception as e:
        logging.error(f"Smart analytics error: {e}")
        return render_template('admin/smart_analytics.html',
                             data={},
                             revenue={},
                             days=7)

@admin_bp.route('/admin/generate-affiliate-article', methods=['POST'])
@login_required
@admin_required
def admin_generate_affiliate_article():
    """Generate one product-highlight article (draft) with affiliate link."""
    from services.monetization_service import monetization_service
    from services.content_engine import ContentEngine
    import random
    products = models.AffiliateProduct.query.filter_by(active=True).all()
    product = random.choice(products) if products else None
    if not product:
        return jsonify({'success': False, 'error': 'No affiliate products. Add products in admin.'}), 400
    affiliate_url = product.affiliate_url or monetization_service.generate_affiliate_link(product.product_type, product.product_id or '')
    topic = (
        f"Product highlight: {product.name}. "
        f"For transactors who want the best in our niche. "
        f"Write a practical, helpful article (not salesy). "
        f"Include this referral link as the primary CTA for readers: {affiliate_url}. "
        f"Product category: {product.category}. "
        f"Short description: {product.short_description or ''}. "
        f"Keep tone Protocol Pulse: intelligence for transactors."
    )
    try:
        engine = ContentEngine()
        result = engine.generate_and_publish_article(
            topic, content_type="bitcoin_news", auto_publish=False
        )
        if result.get('success') and result.get('article_id'):
            article = models.Article.query.get(result['article_id'])
            if article and affiliate_url:
                article.content = (article.content or '') + f"\n\n---\n[Get {product.name}]({affiliate_url})"
                db.session.commit()
            return jsonify({
                'success': True,
                'article_id': result['article_id'],
                'title': result.get('title'),
                'product': product.name,
            })
    except Exception as e:
        logging.error(f"Affiliate article generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': False, 'error': 'Generation failed'}), 500

@admin_bp.route('/admin/rtsa')
@login_required
@admin_required
def admin_rtsa():
    """Admin dashboard for RTSA product management"""
    from services.rtsa_service import rtsa_service
    
    draft_products = rtsa_service.get_draft_products()
    approved_products = rtsa_service.get_approved_products(limit=20)
    hot_products = rtsa_service.get_hot_products()
    
    return render_template('admin/rtsa.html',
                         draft_products=draft_products,
                         approved_products=approved_products,
                         hot_products=hot_products)

@admin_bp.route('/admin/api/rtsa/forge', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_forge():
    """Manually trigger RTSA forge from current sentiment"""
    from services.rtsa_service import rtsa_service
    from services.sentiment_engine import get_latest_sentiment
    
    try:
        sentiment = get_latest_sentiment()
        sentiment['state_changed'] = True
        
        product = rtsa_service.forge_from_sentiment(sentiment)
        
        if product:
            return jsonify({
                'success': True,
                'product': product.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': 'Forge failed'}), 500
            
    except Exception as e:
        logging.error(f"RTSA manual forge error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/admin/api/rtsa/approve/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_approve(product_id):
    """Approve an RTSA draft product"""
    from services.rtsa_service import rtsa_service
    
    result = rtsa_service.approve_product(product_id, current_user.id)
    
    if result and result.get('success'):
        return jsonify(result)
    else:
        return jsonify({'success': False, 'error': result.get('error', 'Approval failed')}), 400

@admin_bp.route('/admin/api/rtsa/reject/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_reject(product_id):
    """Reject an RTSA draft product"""
    from services.rtsa_service import rtsa_service
    
    success = rtsa_service.reject_product(product_id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Rejection failed'}), 400

@admin_bp.route('/admin/api/rtsa/broadcast/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def admin_rtsa_broadcast(product_id):
    """Broadcast an approved RTSA product to social"""
    from services.rtsa_service import rtsa_service
    
    product = models.RealTimeProduct.query.get(product_id)
    if not product or product.status != 'approved':
        return jsonify({'success': False, 'error': 'Product not found or not approved'}), 404
    
    success = rtsa_service.broadcast_new_product(product)
    
    return jsonify({'success': success})

@admin_bp.route('/admin/affiliates')
@login_required
@admin_required
def admin_affiliates():
    """Admin affiliate analytics dashboard."""
    _p3_init_tables()
    try:
        from services.affiliate_injector import compute_ab_stats, get_partner_config
        K_ANON = 10  # k-anonymity threshold

        # Clicks last 30 days per partner
        rows = db.session.execute(db.text(
            "SELECT partner, date(clicked_at) as day, COUNT(*) as cnt "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner, day ORDER BY day"
        )).fetchall()
        clicks_by_day = {}
        for r in rows:
            clicks_by_day.setdefault(r[0], {})[r[1]] = r[2]

        # Total clicks (30d) per partner
        totals = db.session.execute(db.text(
            "SELECT partner, COUNT(*) as total, "
            "COUNT(DISTINCT user_hash) as unique_users "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "GROUP BY partner"
        )).fetchall()
        totals_map = {r[0]: {"total": r[1], "unique_users": r[2]} for r in totals}

        # Top referrer pages (k-anon enforced)
        top_refs = db.session.execute(db.text(
            "SELECT partner, referrer_page, COUNT(*) as cnt, "
            "COUNT(DISTINCT user_hash) as uniq "
            "FROM p3_affiliate_clicks "
            "WHERE clicked_at >= date('now', '-30 days') "
            "AND referrer_page != '' "
            "GROUP BY partner, referrer_page "
            "HAVING uniq >= :k "
            "ORDER BY cnt DESC LIMIT 20"
        ), {"k": K_ANON}).fetchall()

        # A/B stats
        ab_stats = {
            "meanwhile": compute_ab_stats("meanwhile"),
            "rns_id": compute_ab_stats("rns_id"),
        }

        partner_cfg = get_partner_config()

        return render_template(
            'admin_affiliates.html',
            clicks_by_day=clicks_by_day,
            totals_map=totals_map,
            top_refs=top_refs,
            ab_stats=ab_stats,
            partner_cfg=partner_cfg,
            k_anon=K_ANON,
        )
    except Exception as e:
        logging.error("admin_affiliates error: %s", e)
        return render_template('admin_affiliates.html',
                               clicks_by_day={}, totals_map={}, top_refs=[],
                               ab_stats={}, partner_cfg={}, k_anon=10,
                               error=str(e))

@admin_bp.route('/admin/guest-pipeline')
@login_required
@admin_required
def admin_guest_pipeline():
    """Guest booking kanban board."""
    from models import GuestOutreach

    guests_raw = GuestOutreach.query.order_by(GuestOutreach.created_at).all()
    guests = []
    for g in guests_raw:
        topics = []
        if g.topics:
            try:
                topics = json.loads(g.topics)
            except (ValueError, TypeError):
                topics = [t.strip() for t in g.topics.split(",") if t.strip()]
        guests.append({
            "id": g.id,
            "name": g.name,
            "handle": g.handle,
            "email": g.email,
            "topics": topics,
            "status": g.status,
            "notes": g.notes,
            "last_outreach_at": g.last_outreach_at,
            "scheduled_date": g.scheduled_date,
        })

    guests_json = json.dumps([{
        "id": g["id"], "name": g["name"], "handle": g["handle"],
        "email": g["email"], "topics": g["topics"], "status": g["status"],
        "notes": g["notes"],
    } for g in guests])

    return render_template('admin/guest_pipeline.html', guests=guests, guests_json=guests_json)

@admin_bp.route('/api/admin/guest', methods=['POST'])
@admin_required
def api_add_guest():
    """Add a new guest to the pipeline."""
    from models import GuestOutreach

    data = request.get_json(force=True)
    topics_str = data.get("topics", "")
    topics_json = json.dumps([t.strip() for t in topics_str.split(",") if t.strip()]) if topics_str else "[]"

    guest = GuestOutreach(
        name=data["name"],
        handle=data.get("handle"),
        email=data.get("email"),
        topics=topics_json,
        status=data.get("status", "identified"),
        notes=data.get("notes"),
    )
    db.session.add(guest)
    db.session.commit()
    return jsonify({"ok": True, "id": guest.id})

@admin_bp.route('/api/admin/guest/<int:guest_id>', methods=['PUT'])
@admin_required
def api_update_guest(guest_id):
    """Update a guest in the pipeline."""
    from models import GuestOutreach

    guest = GuestOutreach.query.get_or_404(guest_id)
    data = request.get_json(force=True)

    if "name" in data:
        guest.name = data["name"]
    if "handle" in data:
        guest.handle = data["handle"]
    if "email" in data:
        guest.email = data["email"]
    if "topics" in data:
        topics_str = data["topics"]
        guest.topics = json.dumps([t.strip() for t in topics_str.split(",") if t.strip()]) if topics_str else "[]"
    if "status" in data:
        guest.status = data["status"]
    if "notes" in data:
        guest.notes = data["notes"]

    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.route('/api/admin/guest/<int:guest_id>', methods=['DELETE'])
@admin_required
def api_delete_guest(guest_id):
    """Delete a guest from the pipeline."""
    from models import GuestOutreach

    guest = GuestOutreach.query.get_or_404(guest_id)
    db.session.delete(guest)
    db.session.commit()
    return jsonify({"ok": True})

@admin_bp.route('/api/admin/guest/seed', methods=['POST'])
@admin_required
def api_seed_guests():
    """Seed default guest list."""
    from services.sponsor_outreach_service import seed_default_guests
    count = seed_default_guests()
    return jsonify({"ok": True, "count": count})

@admin_bp.route('/api/admin/guest-outreach/run', methods=['POST'])
@admin_required
def api_run_guest_outreach():
    """Trigger guest booking outreach cycle."""
    from services.sponsor_outreach_service import run_daily_guest_outreach
    results = run_daily_guest_outreach()
    return jsonify(results)

@admin_bp.route('/api/admin/test-sms', methods=['POST'])
@admin_required
def twilio_test_sms():
    """Send a test SMS via Twilio."""
    try:
        from services.twilio_service import send_sms
        data = request.get_json() or {}
        to = data.get('to') or os.environ.get('PBX_PHONE_NUMBER')
        message = data.get('message', 'Protocol Pulse: Satomi online. Systems nominal. Test SMS successful.')
        if not to:
            return jsonify({'success': False, 'error': 'No phone number provided and PBX_PHONE_NUMBER not set'}), 400
        ok = send_sms(to, message)
        return jsonify({'success': ok, 'to': to})
    except Exception as e:
        logging.error('Test SMS error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/test-call', methods=['POST'])
@admin_required
def twilio_test_call():
    """Place a test voice call via Twilio."""
    try:
        from services.twilio_service import send_voice_call
        data = request.get_json() or {}
        to = data.get('to') or os.environ.get('PBX_PHONE_NUMBER')
        message = data.get('message', 'This is Satomi from Protocol Pulse. Your intelligence system is online and operational. All systems nominal.')
        if not to:
            return jsonify({'success': False, 'error': 'No phone number provided and PBX_PHONE_NUMBER not set'}), 400
        ok = send_voice_call(to, message)
        return jsonify({'success': ok, 'to': to})
    except Exception as e:
        logging.error('Test call error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/morning-brief', methods=['POST'])
@admin_required
def twilio_morning_brief():
    """Generate and deliver morning intelligence brief via voice call + SMS."""
    try:
        from services.satomi_brief_generator import generate_and_deliver_brief
        result = generate_and_deliver_brief()
        return jsonify(result)
    except Exception as e:
        logging.error('Morning brief error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/api/admin/gpu-status')
def api_gpu_status():
    try:
        from services.gpu_scheduler import get_scheduler
        sched = get_scheduler()
        return jsonify(sched.status())
    except Exception as e:
        logging.error(f'GPU status error: {e}')
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/gpu-render', methods=['POST'])
@login_required
def api_gpu_render():
    """Request a manual render via GPU scheduler."""
    try:
        from services.gpu_scheduler import get_scheduler
        data = request.get_json() or {}
        episode = data.get('episode', f"manual_{datetime.utcnow().strftime('%Y%m%d_%H%M')}")
        sched = get_scheduler()
        result = sched.request_render(episode)
        return jsonify(result)
    except Exception as e:
        logging.error(f'GPU render request error: {e}')
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/admin/spaces-alert', methods=['POST'])
@admin_required
def twilio_spaces_alert():
    """Send X Spaces hot-detection SMS alert."""
    try:
        from services.twilio_service import send_spaces_alert
        data = request.get_json() or {}
        to = data.get('to') or os.environ.get('PBX_PHONE_NUMBER')
        title = data.get('title', 'Bitcoin X Space')
        speaker = data.get('speaker', 'Unknown')
        score = data.get('score', 80)
        if not to:
            return jsonify({'success': False, 'error': 'No phone number provided and PBX_PHONE_NUMBER not set'}), 400
        ok = send_spaces_alert(to, title, speaker, score)
        return jsonify({'success': ok, 'to': to})
    except Exception as e:
        logging.error('Spaces alert error: %s', e)
        return jsonify({'success': False, 'error': str(e)}), 500


# ── KOL Sentiment Brief Admin ───────────────────────────────────────────────

@admin_bp.route('/api/admin/sentiment-brief-refresh', methods=['POST'])
@admin_required
def admin_sentiment_brief_refresh():
    """Force regenerate the KOL sentiment brief."""
    try:
        from services.sentiment_brief_service import SentimentBriefService
        svc = SentimentBriefService()
        brief = svc.build_sentiment_brief()
        return jsonify({"success": True, "brief": brief})
    except Exception as e:
        logging.error(f"Sentiment brief refresh error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ── Reply Engine Admin ───────────────────────────────────────────────────────

@admin_bp.route('/api/admin/reply-auto-post/toggle', methods=['POST'])
@admin_required
def admin_reply_auto_post_toggle():
    """Toggle the ENABLE_AUTO_REPLY feature flag."""
    from services.feature_flags import is_enabled
    current = is_enabled("ENABLE_AUTO_REPLY")
    new_val = "false" if current else "true"
    os.environ["ENABLE_AUTO_REPLY"] = new_val
    return jsonify({
        "success": True,
        "ENABLE_AUTO_REPLY": not current,
        "message": f"Auto-reply {'enabled' if not current else 'disabled'}",
    })


@admin_bp.route('/api/admin/reply-drafts')
@admin_required
def admin_reply_drafts():
    """Return latest 20 pending reply drafts for review."""
    try:
        from services.reply_engine import get_pending_drafts
        drafts = get_pending_drafts(limit=20)
        return jsonify({"success": True, "drafts": drafts, "count": len(drafts)})
    except Exception as e:
        logging.error(f"Reply drafts error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@admin_bp.route('/api/admin/reply-drafts/<int:draft_id>/approve', methods=['POST'])
@admin_required
def admin_reply_draft_approve(draft_id):
    """Approve and immediately post a specific reply draft."""
    try:
        from services.reply_engine import approve_and_post_draft
        result = approve_and_post_draft(draft_id)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Reply draft approve error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════
# OPS BOARD — Full Kanban API
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/admin/board')
@login_required
def admin_board():
    """Ops Board — Team Kanban."""
    if not current_user.is_admin:
        return redirect(url_for('pages.index'))
    # Load team members for assignee dropdown
    team = models.User.query.filter_by(is_admin=True).order_by(models.User.email).all()
    return render_template('admin/board.html', team=team)


@admin_bp.route('/api/admin/board/cards', methods=['GET'])
@login_required
def api_board_cards():
    """Get all cards grouped by column."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    cards = models.BoardCard.query.filter(
        models.BoardCard.column != 'archived'
    ).order_by(models.BoardCard.column, models.BoardCard.position).all()
    result = {}
    for col in ['backlog', 'in_progress', 'review', 'done']:
        result[col] = [c.to_dict() for c in cards if c.column == col]
    return jsonify(result)


@admin_bp.route('/api/admin/board/cards', methods=['POST'])
@login_required
def api_board_create_card():
    """Create a new card."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    # Max position in column
    max_pos = db.session.query(db.func.max(models.BoardCard.position)).filter_by(
        column=data.get('column', 'backlog')
    ).scalar() or 0
    card = models.BoardCard(
        title       = data.get('title', 'Untitled').strip()[:200],
        description = data.get('description', ''),
        column      = data.get('column', 'backlog'),
        priority    = data.get('priority', 'medium'),
        tag         = data.get('tag', 'feature'),
        assignee_id = data.get('assignee_id') or None,
        creator_id  = current_user.id,
        position    = max_pos + 1,
        due_date    = datetime.strptime(data['due_date'], '%Y-%m-%d') if data.get('due_date') else None,
    )
    db.session.add(card)
    db.session.commit()
    return jsonify(card.to_dict()), 201


@admin_bp.route('/api/admin/board/cards/<int:card_id>', methods=['PATCH'])
@login_required
def api_board_update_card(card_id):
    """Update card fields (title, description, column, priority, tag, assignee, due_date)."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    card = models.BoardCard.query.get_or_404(card_id)
    data = request.get_json() or {}
    for field in ['title', 'description', 'column', 'priority', 'tag', 'position']:
        if field in data:
            setattr(card, field, data[field])
    if 'assignee_id' in data:
        card.assignee_id = data['assignee_id'] or None
    if 'due_date' in data:
        card.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d') if data['due_date'] else None
    card.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify(card.to_dict())


@admin_bp.route('/api/admin/board/cards/<int:card_id>', methods=['DELETE'])
@login_required
def api_board_delete_card(card_id):
    """Archive (soft-delete) a card."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    card = models.BoardCard.query.get_or_404(card_id)
    card.column = 'archived'
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/board/cards/<int:card_id>/move', methods=['POST'])
@login_required
def api_board_move_card(card_id):
    """Move card to a column at a specific position. Reorders siblings."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    card = models.BoardCard.query.get_or_404(card_id)
    data = request.get_json() or {}
    new_col = data.get('column', card.column)
    new_pos = int(data.get('position', 0))

    # Pull card out of old position
    siblings = models.BoardCard.query.filter(
        models.BoardCard.column == new_col,
        models.BoardCard.id != card_id,
        models.BoardCard.column != 'archived'
    ).order_by(models.BoardCard.position).all()

    # Re-index: insert at new_pos
    card.column = new_col
    card.updated_at = datetime.utcnow()
    for i, sib in enumerate(siblings):
        sib.position = i if i < new_pos else i + 1
    card.position = new_pos
    db.session.commit()
    return jsonify(card.to_dict())


@admin_bp.route('/api/admin/board/cards/<int:card_id>/comments', methods=['GET'])
@login_required
def api_board_get_comments(card_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    comments = models.BoardComment.query.filter_by(card_id=card_id).order_by(
        models.BoardComment.created_at).all()
    return jsonify([c.to_dict() for c in comments])


@admin_bp.route('/api/admin/board/cards/<int:card_id>/comments', methods=['POST'])
@login_required
def api_board_add_comment(card_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    models.BoardCard.query.get_or_404(card_id)
    data = request.get_json() or {}
    body = (data.get('body') or '').strip()
    if not body:
        return jsonify({'error': 'Empty comment'}), 400
    comment = models.BoardComment(card_id=card_id, author_id=current_user.id, body=body)
    # Update card timestamp
    card = models.BoardCard.query.get(card_id)
    card.updated_at = datetime.utcnow()
    db.session.add(comment)
    db.session.commit()
    return jsonify(comment.to_dict()), 201


@admin_bp.route('/api/admin/board/comments/<int:comment_id>', methods=['DELETE'])
@login_required
def api_board_delete_comment(comment_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    c = models.BoardComment.query.get_or_404(comment_id)
    if c.author_id != current_user.id:
        return jsonify({'error': 'Can only delete your own comments'}), 403
    db.session.delete(c)
    db.session.commit()
    return jsonify({'ok': True})


@admin_bp.route('/api/admin/board/stats', methods=['GET'])
@login_required
def api_board_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from sqlalchemy import func
    counts = dict(db.session.query(
        models.BoardCard.column, func.count(models.BoardCard.id)
    ).filter(models.BoardCard.column != 'archived').group_by(models.BoardCard.column).all())
    urgent = models.BoardCard.query.filter(
        models.BoardCard.priority == 'urgent',
        models.BoardCard.column != 'done',
        models.BoardCard.column != 'archived'
    ).count()
    return jsonify({'counts': counts, 'urgent': urgent,
                    'total': sum(counts.values())})


@admin_bp.route('/api/admin/mission-status', methods=['GET'])
@login_required
def api_admin_mission_status():
    """Mission control summary for the unified admin dashboard widget."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403

    # Active newsletter subscribers
    try:
        subscribers = models.NewsletterSubscriber.query.filter_by(subscribed=True).count()
    except Exception:
        subscribers = 0

    # Outreach totals
    try:
        prospects_total = models.SponsorOutreach.query.count()
        prospects_sent = models.SponsorOutreach.query.filter(
            models.SponsorOutreach.status.in_(['contacted', 'replied', 'deal'])
        ).count()
        prospects_replied = models.SponsorOutreach.query.filter(
            models.SponsorOutreach.replied_at.isnot(None)
        ).count()
    except Exception:
        prospects_total = prospects_sent = prospects_replied = 0

    # Board counts
    try:
        board_in_progress = models.BoardCard.query.filter(
            models.BoardCard.column == 'in_progress'
        ).count()
        board_urgent = models.BoardCard.query.filter(
            models.BoardCard.priority == 'urgent',
            models.BoardCard.column != 'done',
            models.BoardCard.column != 'archived'
        ).count()
    except Exception:
        board_in_progress = board_urgent = 0

    # Last render
    last_render_date = None
    try:
        report_paths = [
            os.path.expanduser('~/protocol_pulse/logs/daily_pulse.report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_pipeline_report.json'),
            os.path.expanduser('~/protocol_pulse/logs/medley_daily_beat.report.json'),
        ]
        for rpath in report_paths:
            if os.path.exists(rpath):
                mtime = os.path.getmtime(rpath)
                last_render_date = datetime.utcfromtimestamp(mtime).isoformat() + 'Z'
                break
    except Exception:
        pass

    return jsonify({
        'subscribers': subscribers,
        'prospects_total': prospects_total,
        'prospects_sent': prospects_sent,
        'prospects_replied': prospects_replied,
        'board_in_progress': board_in_progress,
        'board_urgent': board_urgent,
        'last_render_date': last_render_date,
    })


# ═══════════════════════════════════════════════════════════════════════════
# SPONSOR OUTREACH COMMAND CENTER
# ═══════════════════════════════════════════════════════════════════════════

@admin_bp.route('/admin/outreach')
@login_required
def admin_outreach():
    """Sponsor outreach command center."""
    if not current_user.is_admin:
        return redirect(url_for('pages.index'))
    return render_template('admin/outreach.html')


@admin_bp.route('/api/admin/outreach/prospects', methods=['GET'])
@login_required
def api_outreach_prospects():
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    prospects = models.SponsorOutreach.query.order_by(
        models.SponsorOutreach.status,
        models.SponsorOutreach.created_at.desc()
    ).all()
    return jsonify([{
        'id': p.id, 'company': p.company, 'email': p.email,
        'category': p.category, 'status': p.status,
        'sent_at': p.sent_at.isoformat() + 'Z' if p.sent_at else None,
        'replied_at': p.replied_at.isoformat() + 'Z' if p.replied_at else None,
        'deal_value': p.deal_value, 'notes': p.notes or '',
        'domain': p.domain or '',
    } for p in prospects])


@admin_bp.route('/api/admin/outreach/prospects/<int:pid>', methods=['PATCH'])
@login_required
def api_outreach_update(pid):
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    p = models.SponsorOutreach.query.get_or_404(pid)
    data = request.get_json() or {}
    for field in ['status', 'email', 'notes', 'deal_value']:
        if field in data:
            setattr(p, field, data[field])
    if data.get('replied'):
        p.replied_at = datetime.utcnow()
        p.status = 'replied'
    db.session.commit()
    return jsonify({'ok': True, 'id': p.id, 'status': p.status})


@admin_bp.route('/api/admin/outreach/prospects', methods=['POST'])
@login_required
def api_outreach_add():
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    p = models.SponsorOutreach(
        company=data.get('company',''),
        domain=data.get('domain',''),
        email=data.get('email',''),
        category=data.get('category','other'),
        status='prospect',
        notes=data.get('notes',''),
    )
    db.session.add(p)
    db.session.commit()
    return jsonify({'ok': True, 'id': p.id}), 201


@admin_bp.route('/api/admin/outreach/send', methods=['POST'])
@login_required
def api_outreach_send():
    """Send intro email to a single prospect using the outreach service."""
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    data = request.get_json() or {}
    pid = data.get('prospect_id')
    if not pid:
        return jsonify({'error': 'prospect_id required'}), 400
    p = models.SponsorOutreach.query.get_or_404(pid)
    if not p.email:
        return jsonify({'error': 'No email address for this prospect'}), 400
    try:
        import importlib.util as _ilu
        spec = _ilu.spec_from_file_location('sos',
            '/home/ultron/protocol_pulse/core/services/sponsor_outreach_service.py')
        svc = _ilu.module_from_spec(spec); spec.loader.exec_module(svc)
        result = svc.send_sponsor_intro(p.company, p.email, p.category)
        if result.get('ok'):
            p.sent_at = datetime.utcnow()
            p.status = 'contacted'
            p.subject = result.get('subject', '')
            db.session.commit()
            # Alert team via board card
            try:
                pbx = models.User.query.filter_by(email='soldtwodragons@gmail.com').first()
                if pbx:
                    card = models.BoardCard(
                        title=f'Sponsor outreach sent: {p.company}',
                        description=f'Email sent to {p.email}. Subject: {p.subject}',
                        column='in_progress', priority='medium', tag='marketing',
                        creator_id=pbx.id, position=0
                    )
                    db.session.add(card)
                    db.session.commit()
            except Exception:
                pass
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/admin/outreach/stats', methods=['GET'])
@login_required
def api_outreach_stats():
    if not current_user.is_admin:
        return jsonify({'error': 'Forbidden'}), 403
    from sqlalchemy import func
    counts = dict(db.session.query(
        models.SponsorOutreach.status, func.count(models.SponsorOutreach.id)
    ).group_by(models.SponsorOutreach.status).all())
    total = sum(counts.values())
    sent = counts.get('contacted', 0) + counts.get('replied', 0) + counts.get('deal', 0)
    return jsonify({
        'total': total, 'sent': sent,
        'prospect': counts.get('prospect', 0),
        'contacted': counts.get('contacted', 0),
        'replied': counts.get('replied', 0),
        'deal': counts.get('deal', 0),
        'lost': counts.get('lost', 0),
        'pp_count': models.SponsorOutreach.query.filter(
            (models.SponsorOutreach.notes == None) |
            (~models.SponsorOutreach.notes.like('%Boomers%'))
        ).count(),
        'boomers_count': models.SponsorOutreach.query.filter(
            models.SponsorOutreach.notes.like('%Boomers%')
        ).count(),
    })
