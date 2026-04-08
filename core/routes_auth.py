"""
routes_auth.py — Auth routes blueprint for Protocol Pulse.
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
    _jwt_required, _apply_rate_limit, _JWT_SECRET, _JWT_ALGORITHM, _JWT_EXPIRY_HOURS, _jwt,
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

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/webhook/printful', methods=['POST'])
def printful_webhook():
    """Handle Printful webhook for order status updates"""
    try:
        data = request.get_json()
        event_type = data.get('type')
        order_data = data.get('data', {}).get('order', {})
        
        logging.info(f"Printful webhook: {event_type} - Order {order_data.get('id')}")
        
        # Could integrate with notifications here
        return jsonify({'received': True}), 200
    except Exception as e:
        logging.error(f"Printful webhook error: {e}")
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    # Always generate a fresh CSRF token for the login page
    import secrets as _secrets
    if 'csrf_token' not in session or request.method == 'GET':
        session['csrf_token'] = _secrets.token_hex(32)
        session.modified = True

    if request.method == 'POST':
        # Cloudflare Turnstile bot check
        cf_token = request.form.get('cf-turnstile-response', '')
        if not verify_turnstile(cf_token):
            flash('CAPTCHA verification failed. Please try again.', 'error')
            return render_template('login.html')

        # CSRF check for login — lenient: if token missing from session, allow but warn
        form_token = request.form.get('csrf_token') or request.headers.get('X-CSRF-Token', '')
        session_token = session.get('csrf_token', '')
        if form_token and session_token and form_token != session_token:
            # Tokens present but don't match — genuine CSRF attempt, block it
            abort(400, 'Invalid CSRF token')
        # If either token is missing entirely (Cloudflare session issue), allow through
        # since login itself doesn't carry sensitive session state to steal

        login_input = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = models.User.query.filter_by(username=login_input).first()
        if not user:
            user = models.User.query.filter_by(email=login_input).first()
        if user and user.password_hash and user.check_password(password):
            login_user(user)
            session.pop('csrf_token', None)  # Clear token after successful login
            if getattr(user, 'is_admin', False):
                return redirect('/admin')
            return redirect('/')
        else:
            flash('Invalid username or password')
            return render_template('login.html')
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    # Public registration disabled — redirect to Commander join page
    return redirect('/join', code=302)

@auth_bp.route('/join')
def join_page():
    """Premium onboarding / join page."""
    from services.price_service import PriceService
    try:
        ps = PriceService()
        prices = ps.get_prices()
        btc_price = prices.get('bitcoin', {}).get('price', 0) if prices else 0
    except:
        btc_price = 0
    stripe_key = os.environ.get('STRIPE_PUBLISHABLE_KEY', os.environ.get('STRIPE_PUBLIC_KEY', ''))
    return render_template('join.html', btc_price=btc_price, stripe_key=stripe_key)

@auth_bp.route('/oauth/youtube/callback')
def youtube_oauth_callback():
    """Handle YouTube OAuth callback — exchange code INSTANTLY, no delay."""
    import requests as _req, re as _re, time as _time
    
    code = request.args.get('code')
    error = request.args.get('error')
    
    if error:
        flash(f'YouTube authorization failed: {error}', 'error')
        return redirect('/admin/youtube-auth')
    
    if not code:
        flash('No authorization code received', 'error')
        return redirect('/admin/youtube-auth')
    
    # INSTANT exchange — do this before any other processing
    client_id = os.environ.get('YOUTUBE_CLIENT_ID', '')
    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET', '')
    redirect_uri = 'https://protocolpulse.io/oauth/youtube/callback'
    
    try:
        resp = _req.post(
            'https://oauth2.googleapis.com/token',
            data={
                'code': code,
                'client_id': client_id,
                'client_secret': client_secret,
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code',
            },
            timeout=10
        )
        logging.info(f'[YouTube] Exchange status: {resp.status_code}, body: {resp.text[:200]}')
        
        if resp.ok:
            data = resp.json()
            refresh_token = data.get('refresh_token')
            access_token = data.get('access_token')
            
            if refresh_token:
                # Save to .env immediately
                env_path = '/home/ultron/protocol_pulse/.env'
                try:
                    with open(env_path) as ef:
                        env_content = ef.read()
                    if 'YOUTUBE_REFRESH_TOKEN=' in env_content:
                        env_content = _re.sub(r'YOUTUBE_REFRESH_TOKEN=.*', f'YOUTUBE_REFRESH_TOKEN={refresh_token}', env_content)
                    else:
                        env_content += f'\nYOUTUBE_REFRESH_TOKEN={refresh_token}\n'
                    with open(env_path, 'w') as ef:
                        ef.write(env_content)
                    os.environ['YOUTUBE_REFRESH_TOKEN'] = refresh_token
                    logging.info(f'[YouTube] SUCCESS - refresh token saved: {refresh_token[:20]}...')
                except Exception as save_err:
                    logging.error(f'[YouTube] Save failed: {save_err}')
                flash('YouTube authorized successfully! Auto-publishing enabled.', 'success')
                return render_template('admin/youtube_token.html', refresh_token=refresh_token)
            elif access_token:
                # Already authorized — no new refresh token issued
                existing_rt = os.environ.get('YOUTUBE_REFRESH_TOKEN', '')
                if existing_rt:
                    flash('YouTube already authorized. Existing token active.', 'success')
                    return render_template('admin/youtube_token.html', refresh_token=existing_rt)
                flash(f'Access token received but no refresh token (status {resp.status_code}). Revoke access at myaccount.google.com/permissions then retry.', 'warning')
                return redirect('/admin/youtube-auth')
        else:
            flash(f'Google returned error {resp.status_code}: {resp.text[:150]}', 'error')
            return redirect('/admin/youtube-auth')
    except Exception as e:
        logging.error(f'[YouTube] callback exception: {e}')
        flash(f'Exchange error: {e}', 'error')
        return redirect('/admin/youtube-auth')

@auth_bp.route('/subscribe/premium/<tier>')
@login_required
def subscribe_premium(tier):
    """Initiate premium subscription checkout"""
    from services.monetization_service import monetization_service
    
    if tier not in ['operator', 'commander', 'sovereign']:
        flash('Invalid subscription tier')
        return redirect(url_for('pages.premium_page'))
    
    result = monetization_service.create_checkout_session(
        tier=tier,
        user_email=current_user.email,
        success_url=request.host_url + 'subscription/success',
        cancel_url=request.host_url + 'premium'
    )
    
    if result.get('checkout_url'):
        return redirect(result['checkout_url'])
    elif result.get('simulated'):
        flash('Stripe not configured - subscription simulated for demo')
        return redirect(url_for('pages.premium_page'))
    else:
        flash(f"Error: {result.get('error', 'Unknown error')}")
        return redirect(url_for('pages.premium_page'))

@auth_bp.route('/api/v1/checkout/create-session', methods=['POST'])
def api_checkout_create_session():
    """Create Stripe checkout session for Commander subscription (called from /commander page)."""
    import stripe
    stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
    if not stripe.api_key:
        return jsonify({'error': 'Stripe not configured'}), 500
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Protocol Pulse Commander',
                        'description': 'Full tactical Bitcoin intelligence. Priority Oracle, Signal Engine, Pulse Terminal.',
                    },
                    'unit_amount': 2900,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url.rstrip('/') + '/onboarding/commander?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url.rstrip('/') + '/commander',
        )
        return jsonify({'url': session.url})
    except Exception as e:
        logging.error(f'Stripe checkout session error: {e}')
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/onboarding')
def onboarding_redirect():
    from flask import redirect
    return redirect('/onboarding/commander', 302)

@auth_bp.route('/onboarding/commander')
def commander_onboarding():
    """Premium commander onboarding — 7-screen experience."""
    # Allow all users — guests get placeholder values
    from flask_login import current_user as _cu
    if not _cu.is_authenticated:
        return render_template('commander_onboarding.html',
                               member_number='PP-XXXX',
                               join_date='2026',
                               user=None)
    if getattr(_cu, 'onboarding_completed', False) and not _cu.is_admin:
        return redirect('/intelligence')
    member_number = f"PP-{_cu.id:04d}"
    join_date = _cu.created_at.strftime('%B %d, %Y') if _cu.created_at else '2026'
    return render_template('commander_onboarding.html',
                           member_number=member_number,
                           join_date=join_date,
                           user=_cu)

@auth_bp.route('/api/user/onboarding-complete', methods=['POST'])
@login_required
def mark_onboarding_complete():
    """Mark commander onboarding as complete."""
    current_user.onboarding_completed = True
    current_user.onboarding_completed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})

def _schedule_welcome_emails(email: str, tier: str):
    """Schedule 3-email post-payment welcome sequence via background threads."""
    import threading

    resend_key = os.environ.get("RESEND_API_KEY", "")
    if not resend_key:
        logging.warning("RESEND_API_KEY not set — skipping welcome email sequence for %s", email)
        return

    def _send_email(subject: str, html_body: str):
        try:
            import requests as _req
            _req.post("https://api.resend.com/emails", json={
                "from": "Protocol Pulse <terminal@protocolpulse.io>",
                "to": [email],
                "subject": subject,
                "html": html_body,
            }, headers={"Authorization": f"Bearer {resend_key}"}, timeout=15)
            logging.info("Welcome email sent to %s: %s", email, subject)
        except Exception as e:
            logging.error("Failed to send welcome email to %s: %s", email, e)

    # Email 1 — Immediate
    def send_email_1():
        _send_email(
            "Terminal access granted — here's what you're seeing",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#FF0033;font-size:16px;letter-spacing:2px;'>TERMINAL ACCESS GRANTED</h1>"
            "<p>Commander,</p>"
            "<p>Your Intelligence Terminal is live. Right now, PCAF is scanning every block for anomalies. "
            "The Convergence Matrix is correlating 8 independent data feeds. The Monte Carlo engine is "
            "running probability distributions across 5 scenarios.</p>"
            "<p>This isn't a dashboard. It's a war room.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence' "
            "style='color:#00D4FF;'>Enter the Terminal →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    # Email 2 — 72h later
    def send_email_2():
        import time as _time
        _time.sleep(259200)  # 72 hours
        _send_email(
            "PCAF is watching — your first anomaly patterns",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#FFAA00;font-size:16px;letter-spacing:2px;'>PCAF ACTIVE</h1>"
            "<p>Commander,</p>"
            "<p>PCAF v1 uses a Graph Neural Network autoencoder to detect anomalies in Bitcoin's chain state. "
            "When the anomaly score crosses 0.7, it means the GNN reconstruction error is elevated — "
            "something in the mempool, hashrate, or fee structure doesn't fit the pattern.</p>"
            "<p>Most alerts are noise. The ones that aren't tend to precede significant moves by 12-48 hours.</p>"
            "<p>Check your alert history and start voting on accuracy — it calibrates the model.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence/alerts' "
            "style='color:#00D4FF;'>View Alert History →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    # Email 3 — 7 days later
    def send_email_3():
        import time as _time
        _time.sleep(604800)  # 7 days
        _send_email(
            "The scenario that's forming right now",
            "<div style='font-family:monospace;color:#E2E2EF;background:#0A0A0F;padding:32px;'>"
            "<h1 style='color:#00FF88;font-size:16px;letter-spacing:2px;'>SCENARIO UPDATE</h1>"
            "<p>Commander,</p>"
            "<p>The Monte Carlo engine has been running for a week now. Five scenarios are being tracked, "
            "each with probability distributions updated every 6 hours based on 28 precursor signals.</p>"
            "<p>The engine doesn't predict. It maps probability space — and when probabilities shift, "
            "the contradiction detector flags conflicting signals before you act on incomplete data.</p>"
            "<p>Check which scenario has the highest probability right now.</p>"
            "<p style='margin-top:24px;'><a href='https://protocolpulse.io/intelligence/scenarios' "
            "style='color:#00D4FF;'>View Scenarios →</a></p>"
            "<p style='color:#555;font-size:12px;margin-top:32px;'>Protocol Pulse · Sovereign Infrastructure</p>"
            "</div>"
        )

    threading.Thread(target=send_email_1, daemon=True).start()
    threading.Thread(target=send_email_2, daemon=True).start()
    threading.Thread(target=send_email_3, daemon=True).start()
    logging.info("Welcome email sequence scheduled for %s (%s tier)", email, tier)

@auth_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events including merch orders"""
    import stripe
    from services.monetization_service import monetization_service
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature', '')
    
    # Check if this is a merch order (custom handling)
    stripe_key = os.environ.get('STRIPE_SECRET_KEY')
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')
    
    if stripe_key and webhook_secret:
        stripe.api_key = stripe_key
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            
            if event['type'] == 'checkout.session.completed':
                session_obj = event['data']['object']
                metadata = session_obj.get('metadata', {})

                # Terminal API subscription: provision ApiSubscriber
                if metadata.get('subscription_type') == 'terminal_api':
                    try:
                        from services.stripe_service import provision_terminal_subscriber
                        result = provision_terminal_subscriber(session_obj, db, models)
                        if result.get('success') and result.get('api_key') and result.get('email'):
                            import threading
                            from routes_premium_api import _send_welcome_email
                            t = threading.Thread(
                                target=_send_welcome_email,
                                args=(result['email'], result['api_key']),
                                daemon=True,
                            )
                            t.start()
                    except Exception as e:
                        logging.error(f"Terminal subscriber provisioning error: {e}")

                # Subscription: set user tier by email
                tier = metadata.get('tier')
                if tier in ('operator', 'commander', 'sovereign') and metadata.get('subscription_type') != 'terminal_api':
                    email = session_obj.get('customer_email') or (session_obj.get('customer_details') or {}).get('email')
                    if email:
                        user = models.User.query.filter_by(email=email).first()
                        if user:
                            user.subscription_tier = tier
                            user.stripe_customer_id = session_obj.get('customer')
                            user.stripe_subscription_id = session_obj.get('subscription')
                            try:
                                db.session.commit()
                                logging.info(f"Subscription tier set: {email} -> {tier}")
                                # Post-payment welcome email sequence
                                _schedule_welcome_emails(email, tier)
                            except Exception as e:
                                db.session.rollback()
                                logging.error(f"Error setting subscription tier: {e}")

                # Handle merch orders - submit to Printful
                if metadata.get('type') == 'merch_order':
                    try:
                        printful_items_json = metadata.get('printful_items', '[]')
                        printful_items = json.loads(printful_items_json)
                        shipping = session_obj.get('shipping_details', {})
                        address = shipping.get('address', {})
                        
                        # Create Printful order
                        order_data = {
                            'recipient': {
                                'name': shipping.get('name', ''),
                                'address1': address.get('line1', ''),
                                'address2': address.get('line2', ''),
                                'city': address.get('city', ''),
                                'state_code': address.get('state', ''),
                                'country_code': address.get('country', 'US'),
                                'zip': address.get('postal_code', ''),
                                'email': session_obj.get('customer_details', {}).get('email', '')
                            },
                            'items': printful_items
                        }
                        
                        # Submit to Printful as draft (for review)
                        result = printful_service.create_order(order_data, confirm=False)
                        if result:
                            logging.info(f"Printful order created: {result.get('id')}")
                        else:
                            logging.error("Failed to create Printful order")
                            
                    except Exception as e:
                        logging.error(f"Error processing merch order: {e}")
                    
                    return jsonify({'success': True}), 200
                    
        except Exception as e:
            logging.error(f"Webhook signature verification failed: {e}")
    
    # Fall back to monetization service for other events
    result = monetization_service.handle_webhook(payload, sig_header)
    
    if result.get('error'):
        return jsonify({'error': result['error']}), 400
    
    return jsonify({'success': True}), 200

@auth_bp.route("/v1/auth/token", methods=["POST"])
def v1_auth_token():
    """
    Issue a JWT for Commander API access.
    POST body: {"email": "...", "password": "..."}
    Returns: {"token": "...", "tier": "...", "expires_in": 86400}
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password required"}), 400

    user = models.User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    tier = getattr(user, "subscription_tier", "free")
    if tier not in ("operator", "commander", "sovereign"):
        return jsonify({"error": "Commander or higher tier required for API access"}), 403

    expiry = datetime.utcnow() + timedelta(hours=_JWT_EXPIRY_HOURS)
    payload = {
        "user_id": user.id,
        "email": user.email,
        "tier": tier,
        "exp": expiry,
        "iat": datetime.utcnow(),
    }
    token = _jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)

    return jsonify({
        "token": token,
        "tier": tier,
        "expires_in": _JWT_EXPIRY_HOURS * 3600,
        "expires_at": expiry.strftime("%Y-%m-%dT%H:%M:%SZ"),
    })

@auth_bp.route("/v1/stripe/webhook", methods=["POST"])
def v1_stripe_webhook():
    """
    Stripe webhook for Pulse Terminal subscriptions.
    Handles checkout.session.completed and customer.subscription.deleted.
    """
    from services.stripe_service import (
        validate_webhook_signature,
        handle_checkout_completed,
        handle_subscription_deleted,
    )

    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")
    webhook_secret = os.environ.get("STRIPE_TERMINAL_WEBHOOK_SECRET", "")

    if webhook_secret:
        event = validate_webhook_signature(payload, sig_header, webhook_secret)
        if event is None:
            return jsonify({"error": "Invalid signature"}), 400
    else:
        # Dev mode: parse without verification
        try:
            event = json.loads(payload)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

    event_type = event.get("type", "")
    event_data = (event.get("data") or {}).get("object") or {}

    if event_type == "checkout.session.completed":
        result = handle_checkout_completed(event_data, db, models)
        logging.info("Terminal checkout completed: %s", result)
        return jsonify({"received": True, "result": result})

    elif event_type == "customer.subscription.deleted":
        result = handle_subscription_deleted(event_data, db, models)
        logging.info("Terminal subscription deleted: %s", result)
        return jsonify({"received": True, "result": result})

    # All other events acknowledged
    return jsonify({"received": True, "event_type": event_type})

@auth_bp.route("/terminal/commander")
def terminal_commander_page():
    """Commander upgrade page — redirects to Stripe checkout."""
    return redirect(url_for("auth.terminal_checkout"))

@auth_bp.route("/terminal/checkout")
@login_required
def terminal_checkout():
    """Initiate Stripe checkout for $29/mo Commander tier."""
    from services.monetization_service import monetization_service
    success_url = request.host_url.rstrip("/") + "/terminal?activated=1"
    cancel_url  = request.host_url.rstrip("/") + "/terminal"
    result = monetization_service.create_checkout_session(
        tier="commander",
        user_email=current_user.email,
        success_url=success_url,
        cancel_url=cancel_url,
    )
    if result.get("simulated"):
        # Dev mode: simulate success — upgrade tier directly
        current_user.subscription_tier = "commander"
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return redirect(url_for("pages.pulse_terminal", activated=1))
    if result.get("checkout_url"):
        return redirect(result["checkout_url"])
    flash("Unable to start checkout. Please try again.")
    return redirect(url_for("pages.pulse_terminal"))

@auth_bp.route("/terminal/account")
@login_required
def terminal_account():
    """Show Commander API key and account status."""
    is_commander = getattr(current_user, "subscription_tier", "free") in ("commander", "sovereign")
    if not is_commander:
        return redirect(url_for("pages.pulse_terminal"))
    try:
        sub = models.ApiSubscriber.query.filter_by(email=current_user.email).first()
    except Exception:
        sub = None
    return render_template("terminal_account.html", sub=sub)

@auth_bp.route('/checkout/commander')
def checkout_commander():
    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Protocol Pulse Commander',
                        'description': 'Full tactical Bitcoin intelligence. Priority Oracle, Signal Engine, Pulse Terminal.',
                    },
                    'unit_amount': 2900,
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.host_url + 'commander/welcome?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.host_url + 'value-stream',
        )
        return redirect(session.url, code=303)
    except Exception as e:
        logging.error(f'Stripe checkout error: {e}')
        return redirect('/value-stream')

@auth_bp.route('/register')
def register_page():
    return render_template('register.html')

@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def api_auth_register():
    """JSON registration endpoint for the /register form."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Use email local part as username, deduplicate if needed
    base_username = email.split('@')[0][:60]
    username = base_username
    suffix = 1
    while models.User.query.filter_by(username=username).first():
        username = f"{base_username}{suffix}"
        suffix += 1

    if models.User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    try:
        user = models.User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Send welcome email via Resend
        try:
            import resend
            resend.api_key = os.getenv('RESEND_API_KEY')
            if resend.api_key:
                resend.Emails.send({
                    "from": "Protocol Pulse <intel@protocolpulse.io>",
                    "to": email,
                    "subject": "You're in. Daily Bitcoin signal starts now.",
                    "html": "<h2>Welcome to Protocol Pulse.</h2><p>Every morning: the signal, not the noise.</p><p>What you get: daily Bitcoin briefs, live Oracle access, on-chain intelligence.</p><p>Your first brief is live now at <a href='https://protocolpulse.io'>protocolpulse.io</a></p><p><a href='https://protocolpulse.io/oracle'>Consult the Oracle &rarr;</a></p>"
                })
        except Exception as mail_err:
            logging.warning('Welcome email failed for %s: %s', email, mail_err)

        # Auto-login the new user and redirect to onboarding
        login_user(user)
        return jsonify({'success': True, 'redirect': '/onboarding/commander'})
    except Exception as e:
        db.session.rollback()
        logging.error('Registration error: %s', e)
        return jsonify({'error': 'Registration failed. Try again.'}), 500

@auth_bp.route('/commander')
def commander_page():
    """Commander conversion page — live signal proof, one dramatic screen."""
    signals = {}
    btc_price = None
    kol_quote = None

    try:
        _project = str(Path(__file__).resolve().parent.parent)
        sys.path.insert(0, _project) if _project not in sys.path else None
        from services.intelligence_engine_v2 import IntelligenceEngineV2
        engine = IntelligenceEngineV2()
        all_signals = engine.compute_signal_scores()
        for key in ("on_chain_accumulation", "narrative_velocity", "miner_conviction"):
            if key in all_signals:
                signals[key] = all_signals[key]
    except Exception as e:
        logging.warning(f"Commander signals failed: {e}")

    try:
        from services.panopticon_service import get_btc_price
        btc_price = get_btc_price()
    except Exception:
        btc_price = None

    try:
        from services.intelligence_engine_v2 import _read_json, LATEST_PATH
        ctx = _read_json(LATEST_PATH) or {}
        whale_alerts = ctx.get("whale_alerts", [])
        if whale_alerts:
            kol_quote = whale_alerts[0].get("message", "")[:120]
    except Exception:
        kol_quote = None

    return render_template('commander.html', signals=signals, btc_price=btc_price, kol_quote=kol_quote)

@auth_bp.route('/commander/dashboard')
@login_required
def commander_dashboard():
    """Commander Dashboard — sovereign Bitcoin intelligence command center."""
    from flask_login import current_user as _cu
    tier = getattr(_cu, 'subscription_tier', '')
    if tier not in ('commander', 'sovereign', 'admin'):
        flash('Commander tier required.', 'warning')
        return redirect('/commander')

    import json as _json; from pathlib import Path
    _project = str(Path(__file__).resolve().parent.parent)

    # Load morning intelligence brief
    morning_brief = {}
    try:
        _mb_path = os.path.join(_project, 'data', 'intelligence', 'morning_intelligence_brief.json')
        if os.path.exists(_mb_path):
            with open(_mb_path) as _f:
                morning_brief = _json.load(_f)
    except Exception:
        pass

    # Load sovereign context (live market data)
    sovereign = {}
    try:
        _sc_path = os.path.join(_project, 'data', 'sovereign_context', 'latest.json')
        if os.path.exists(_sc_path):
            with open(_sc_path) as _f:
                sovereign = _json.load(_f)
    except Exception:
        pass

    # Load KOL sentiment brief
    kol_brief = {}
    try:
        _kol_path = os.path.join(_project, 'data', 'intelligence', 'kol_sentiment_brief.json')
        if os.path.exists(_kol_path):
            with open(_kol_path) as _f:
                kol_brief = _json.load(_f)
    except Exception:
        pass

    return render_template('commander_dashboard.html',
                           authed=True,
                           user=_cu,
                           morning_brief=morning_brief,
                           sovereign=sovereign,
                           kol_brief=kol_brief)

@auth_bp.route('/commander/welcome')
def commander_welcome():
    return render_template('commander_welcome.html')
