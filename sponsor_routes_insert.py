"""
SPONSOR AGENT ROUTES — insert before error handlers in routes.py
Routes:
  GET  /admin/sponsors           → Kanban pipeline board
  GET  /admin/sponsors/list      → table view
  POST /api/sponsors/scan        → trigger radar scan
  GET  /api/sponsors/scan-stream → SSE live scan progress
  POST /api/sponsors/draft/<id>  → generate outreach draft
  POST /api/sponsors/send/<id>   → send via Resend
  POST /api/sponsors/status/<id> → update status
  GET  /api/sponsors/export      → CSV export
  GET  /api/sponsors/metrics     → pipeline funnel stats
  GET  /api/sponsors/<id>        → sponsor detail JSON
  POST /api/sponsors             → create sponsor manually
  PATCH /api/sponsors/<id>       → update sponsor fields
  GET  /sponsorship              → public sponsorship deck
  POST /api/sponsorship/contact  → inbound lead form
  POST /api/sponsors/config      → update agent config
  POST /api/sponsors/resend-webhook → Resend delivery events
"""

# ──────────────────────────────────────────────
# SPONSOR ADMIN — KANBAN BOARD
# ──────────────────────────────────────────────

@app.route('/admin/sponsors')
@login_required
@admin_required
def admin_sponsors_kanban():
    """Sponsor pipeline Kanban board."""
    try:
        from services.sponsor_radar_v2 import ensure_tables
        ensure_tables()
    except Exception as e:
        logging.warning("Could not ensure sponsor tables: %s", e)

    return render_template('admin/sponsors_kanban.html')


@app.route('/admin/sponsors/list')
@login_required
@admin_required
def admin_sponsors_list():
    """Sponsor table view with filters."""
    return render_template('admin/sponsors_list.html')


# ──────────────────────────────────────────────
# SPONSOR API — SCAN
# ──────────────────────────────────────────────

@app.route('/api/sponsors/scan', methods=['POST'])
@login_required
@admin_required
def api_sponsors_scan():
    """Trigger a full Grok radar scan (background)."""
    import threading
    try:
        def _run():
            try:
                from services.sponsor_radar_v2 import run_scan
                run_scan()
            except Exception as exc:
                logging.error("Background sponsor scan error: %s", exc, exc_info=True)

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return jsonify({"ok": True, "message": "Scan started in background. Refresh in 60s."})
    except Exception as e:
        logging.error("api_sponsors_scan error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route('/api/sponsors/scan-stream')
@login_required
@admin_required
def api_sponsors_scan_stream():
    """SSE endpoint streaming live scan progress (Phase 0 addition #1)."""
    import queue
    import threading

    q = queue.Queue()

    def _run():
        try:
            from services.sponsor_radar_v2 import run_scan
            def callback(evt, msg):
                q.put((evt, msg))
            run_scan(progress_callback=callback)
        except Exception as exc:
            q.put(("error", str(exc)[:200]))
        finally:
            q.put(("done", "Scan complete"))

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    def generate():
        import json as _json
        while True:
            try:
                evt, msg = q.get(timeout=120)
                yield f"data: {_json.dumps({'event': evt, 'message': msg})}\n\n"
                if evt in ("done", "complete"):
                    break
            except queue.Empty:
                yield "data: {\"event\": \"timeout\", \"message\": \"Scan timed out\"}\n\n"
                break

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


# ──────────────────────────────────────────────
# SPONSOR API — CRUD
# ──────────────────────────────────────────────

@app.route('/api/sponsors', methods=['GET'])
@login_required
@admin_required
def api_sponsors_all():
    """Get all sponsors grouped by pipeline_stage."""
    import sqlite3
    try:
        from services.sponsor_radar_v2 import _get_db_path, ensure_tables
        ensure_tables()
        db_path = _get_db_path()

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            status_filter = request.args.get('status', '')
            if status_filter:
                cur.execute(
                    "SELECT * FROM sponsors WHERE is_deleted=0 AND status=? ORDER BY relevance_score DESC",
                    (status_filter,)
                )
            else:
                cur.execute(
                    "SELECT * FROM sponsors WHERE is_deleted=0 ORDER BY pipeline_stage ASC, relevance_score DESC"
                )
            rows = [dict(r) for r in cur.fetchall()]

            # Parse JSON fields
            for row in rows:
                try:
                    row['podcasts_they_sponsor'] = json.loads(row.get('podcasts_they_sponsor') or '[]')
                except (json.JSONDecodeError, TypeError):
                    row['podcasts_they_sponsor'] = []
                try:
                    row['signal_sources'] = json.loads(row.get('signal_sources') or '{}')
                except (json.JSONDecodeError, TypeError):
                    row['signal_sources'] = {}

            return jsonify({"sponsors": rows, "count": len(rows)})
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsors_all error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/sponsors/<int:sponsor_id>', methods=['GET'])
@login_required
@admin_required
def api_sponsor_detail(sponsor_id):
    """Get full sponsor detail with outreach history and activity log."""
    import sqlite3
    try:
        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM sponsors WHERE id=? AND is_deleted=0", (sponsor_id,))
            sponsor = cur.fetchone()
            if not sponsor:
                return jsonify({"error": "Not found"}), 404

            sponsor = dict(sponsor)
            for field in ('podcasts_they_sponsor', 'signal_sources'):
                try:
                    sponsor[field] = json.loads(sponsor.get(field) or '{}')
                except (json.JSONDecodeError, TypeError):
                    sponsor[field] = {}

            cur.execute(
                "SELECT * FROM sponsor_outreach WHERE sponsor_id=? ORDER BY version DESC",
                (sponsor_id,)
            )
            outreach = [dict(r) for r in cur.fetchall()]

            cur.execute(
                "SELECT * FROM sponsor_activity_log WHERE sponsor_id=? ORDER BY created_at DESC LIMIT 50",
                (sponsor_id,)
            )
            activity = [dict(r) for r in cur.fetchall()]

            return jsonify({"sponsor": sponsor, "outreach": outreach, "activity": activity})
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsor_detail error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/sponsors', methods=['POST'])
@login_required
@admin_required
def api_sponsors_create():
    """Manually create a sponsor prospect."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        company_name = (data.get('company_name') or '').strip()
        if not company_name:
            return jsonify({"error": "company_name required"}), 400

        from services.sponsor_radar_v2 import _get_db_path, ensure_tables, validate_email_deliverability
        ensure_tables()
        db_path = _get_db_path()

        email = (data.get('contact_email') or '').strip()
        email_ok = 1 if validate_email_deliverability(email) else 0
        now = datetime.utcnow().isoformat()

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sponsors (
                    company_name, category, website, contact_email, contact_name,
                    contact_linkedin, estimated_monthly_spend, notes,
                    status, pipeline_stage, email_verified, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,1,?,?,?)
            """, (
                company_name,
                data.get('category', 'other'),
                data.get('website', ''),
                email,
                data.get('contact_name', ''),
                data.get('contact_linkedin', ''),
                data.get('estimated_monthly_spend', ''),
                data.get('notes', ''),
                data.get('status', 'prospect'),
                email_ok, now, now,
            ))
            sponsor_id = cur.lastrowid
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (sponsor_id, 'manual_add', f'Manually added by admin', 'admin'))
            conn.commit()
            return jsonify({"ok": True, "id": sponsor_id}), 201
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsors_create error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/sponsors/<int:sponsor_id>', methods=['PATCH'])
@login_required
@admin_required
def api_sponsor_update(sponsor_id):
    """Update sponsor fields."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        allowed = {
            'company_name', 'category', 'website', 'contact_email', 'contact_name',
            'contact_linkedin', 'estimated_monthly_spend', 'notes', 'deal_value_monthly',
            'auto_followup_enabled',
        }
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            return jsonify({"error": "No valid fields to update"}), 400

        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        now = datetime.utcnow().isoformat()
        updates['updated_at'] = now

        set_clause = ', '.join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [sponsor_id]

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE sponsors SET {set_clause} WHERE id=? AND is_deleted=0",
                values
            )
            if cur.rowcount == 0:
                return jsonify({"error": "Sponsor not found"}), 404
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (sponsor_id, 'fields_updated', f'Updated: {list(updates.keys())}', 'admin'))
            conn.commit()
            return jsonify({"ok": True})
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsor_update error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR API — STATUS / PIPELINE
# ──────────────────────────────────────────────

VALID_STATUSES = {'prospect', 'outreach_drafted', 'contacted', 'replied', 'negotiating', 'deal', 'rejected', 'inbound'}
STATUS_STAGE_MAP = {
    'prospect': 1, 'inbound': 1, 'outreach_drafted': 3, 'contacted': 4,
    'replied': 5, 'negotiating': 5, 'deal': 6, 'rejected': 6,
}

@app.route('/api/sponsors/status/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def api_sponsor_status(sponsor_id):
    """Update sponsor status and pipeline stage."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        new_status = data.get('status', '').lower()
        if new_status not in VALID_STATUSES:
            return jsonify({"error": f"Invalid status. Valid: {list(VALID_STATUSES)}"}), 400

        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        now = datetime.utcnow().isoformat()
        stage = STATUS_STAGE_MAP.get(new_status, 1)

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT status FROM sponsors WHERE id=? AND is_deleted=0",
                (sponsor_id,)
            )
            row = cur.fetchone()
            if not row:
                return jsonify({"error": "Sponsor not found"}), 404

            old_status = row[0]
            cur.execute("""
                UPDATE sponsors SET status=?, pipeline_stage=?, updated_at=?
                WHERE id=?
            """, (new_status, stage, now, sponsor_id))
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (
                sponsor_id, 'status_changed',
                f'Status: {old_status} → {new_status}',
                data.get('actor', 'admin')
            ))
            conn.commit()
            return jsonify({"ok": True, "status": new_status, "stage": stage})
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsor_status error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR API — OUTREACH DRAFT
# ──────────────────────────────────────────────

@app.route('/api/sponsors/draft/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def api_sponsor_draft(sponsor_id):
    """Generate hyper-personalized outreach draft."""
    try:
        data = request.get_json(force=True) or {}
        channel = data.get('channel', 'email').lower()
        from services.sponsor_outreach_gen import generate_draft
        result = generate_draft(sponsor_id, channel=channel)
        return jsonify({"ok": True, "draft": result})
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logging.error("api_sponsor_draft error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR API — SEND VIA RESEND
# ──────────────────────────────────────────────

@app.route('/api/sponsors/send/<int:sponsor_id>', methods=['POST'])
@login_required
@admin_required
def api_sponsor_send(sponsor_id):
    """Send outreach email via Resend. Requires explicit confirmation in payload."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        if not data.get('confirmed'):
            return jsonify({"error": "Must include confirmed=true to send"}), 400

        draft_id = data.get('draft_id')
        if not draft_id:
            return jsonify({"error": "draft_id required"}), 400

        from services.sponsor_radar_v2 import _get_db_path, get_daily_send_count
        db_path = _get_db_path()

        # Rate limit check (Phase 0 addition #6)
        sent_today = get_daily_send_count(db_path)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT daily_send_limit FROM sponsor_config WHERE id=1")
            cfg = cur.fetchone()
            daily_limit = cfg["daily_send_limit"] if cfg else 25
        finally:
            conn.close()

        if sent_today >= daily_limit:
            return jsonify({
                "error": f"Daily send limit ({daily_limit}) reached. Reset at midnight UTC.",
                "sent_today": sent_today
            }), 429

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()

            # Get draft
            cur.execute(
                "SELECT * FROM sponsor_outreach WHERE id=? AND sponsor_id=?",
                (draft_id, sponsor_id)
            )
            draft = cur.fetchone()
            if not draft:
                return jsonify({"error": "Draft not found"}), 404

            # Get sponsor
            cur.execute(
                "SELECT * FROM sponsors WHERE id=? AND is_deleted=0",
                (sponsor_id,)
            )
            sponsor = cur.fetchone()
            if not sponsor:
                return jsonify({"error": "Sponsor not found"}), 404

            recipient_email = sponsor["contact_email"]
            if not recipient_email:
                return jsonify({"error": "No contact email on file for this sponsor"}), 400

            # Send via Resend
            resend_key = os.environ.get("RESEND_API_KEY")
            if not resend_key:
                return jsonify({"error": "RESEND_API_KEY not configured"}), 500

            import requests as req_lib
            resp = req_lib.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}",
                         "Content-Type": "application/json"},
                json={
                    "from": "PBX <partnerships@protocolpulse.io>",
                    "to": [recipient_email],
                    "subject": draft["subject"],
                    "text": draft["body"],
                },
                timeout=15,
            )

            if resp.status_code not in (200, 201):
                logging.error("Resend API error %s: %s", resp.status_code, resp.text[:300])
                return jsonify({
                    "error": f"Resend API error: {resp.status_code}",
                    "detail": resp.text[:200]
                }), 502

            resend_data = resp.json()
            message_id = resend_data.get("id", "")
            now = datetime.utcnow().isoformat()

            # Update DB
            cur.execute(
                "UPDATE sponsor_outreach SET sent_at=?, resend_message_id=? WHERE id=?",
                (now, message_id, draft_id)
            )
            cur.execute(
                "UPDATE sponsors SET status='contacted', pipeline_stage=4, last_contacted_at=?, updated_at=? WHERE id=?",
                (now, now, sponsor_id)
            )
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (
                sponsor_id, 'email_sent',
                f'Sent to {recipient_email} — Resend ID: {message_id}',
                'admin'
            ))
            conn.commit()

            return jsonify({
                "ok": True,
                "resend_message_id": message_id,
                "sent_to": recipient_email,
                "sent_at": now,
            })

        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()

    except Exception as e:
        logging.error("api_sponsor_send error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR API — SOFT DELETE
# ──────────────────────────────────────────────

@app.route('/api/sponsors/<int:sponsor_id>', methods=['DELETE'])
@login_required
@admin_required
def api_sponsor_delete(sponsor_id):
    """Soft-delete a sponsor record (LAW 3 compliance)."""
    import sqlite3
    try:
        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE sponsors SET is_deleted=1, updated_at=? WHERE id=?",
                (datetime.utcnow().isoformat(), sponsor_id)
            )
            if cur.rowcount == 0:
                return jsonify({"error": "Sponsor not found"}), 404
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (sponsor_id, 'soft_deleted', 'Marked as deleted', 'admin'))
            conn.commit()
            return jsonify({"ok": True})
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsor_delete error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR API — METRICS / EXPORT
# ──────────────────────────────────────────────

@app.route('/api/sponsors/metrics')
@login_required
@admin_required
def api_sponsors_metrics():
    """Pipeline funnel stats."""
    import sqlite3
    try:
        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT status, COUNT(*) as cnt,
                       AVG(relevance_score) as avg_score,
                       SUM(deal_value_monthly) as total_value
                FROM sponsors
                WHERE is_deleted=0
                GROUP BY status
            """)
            rows = cur.fetchall()
            by_status = {r[0]: {"count": r[1], "avg_score": round(r[2] or 0, 1),
                                 "total_value": r[3] or 0}
                         for r in rows}

            cur.execute("SELECT COUNT(*) FROM sponsors WHERE is_deleted=0")
            total = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM sponsor_outreach WHERE sent_at IS NOT NULL")
            total_sent = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM sponsor_outreach WHERE replied_at IS NOT NULL")
            total_replied = cur.fetchone()[0]

            cur.execute("""
                SELECT SUM(deal_value_monthly) FROM sponsors
                WHERE status='deal' AND is_deleted=0
            """)
            actual_mrr = cur.fetchone()[0] or 0

            cur.execute("""
                SELECT SUM(deal_value_monthly * deal_probability_pct / 100.0)
                FROM sponsors
                WHERE is_deleted=0 AND status NOT IN ('deal','rejected')
            """)
            projected_mrr = int(cur.fetchone()[0] or 0)

            reply_rate = round((total_replied / total_sent * 100), 1) if total_sent else 0.0

            return jsonify({
                "total_prospects": total,
                "by_status": by_status,
                "total_sent": total_sent,
                "total_replied": total_replied,
                "reply_rate_pct": reply_rate,
                "actual_mrr": actual_mrr,
                "projected_mrr": projected_mrr,
            })
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsors_metrics error: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route('/api/sponsors/export')
@login_required
@admin_required
def api_sponsors_export():
    """Export sponsors to CSV."""
    import sqlite3
    import io
    import csv as csv_lib
    try:
        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT company_name, category, website, contact_email, contact_name,
                       estimated_monthly_spend, relevance_score, deal_probability_pct,
                       opportunity_signal, status, deal_value_monthly, last_contacted_at,
                       created_at, notes
                FROM sponsors WHERE is_deleted=0
                ORDER BY relevance_score DESC
            """)
            rows = cur.fetchall()
        finally:
            conn.close()

        output = io.StringIO()
        writer = csv_lib.writer(output)
        writer.writerow([
            "Company", "Category", "Website", "Email", "Contact",
            "Est Monthly Spend", "Score", "Deal Prob %", "Signal",
            "Status", "Deal Value/Mo", "Last Contacted", "Added", "Notes"
        ])
        for row in rows:
            writer.writerow(list(row))

        resp = make_response(output.getvalue())
        resp.headers["Content-Type"] = "text/csv"
        resp.headers["Content-Disposition"] = (
            f"attachment; filename=sponsors_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        )
        return resp
    except Exception as e:
        logging.error("api_sponsors_export error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# SPONSOR AGENT CONFIG
# ──────────────────────────────────────────────

@app.route('/api/sponsors/config', methods=['GET', 'POST'])
@login_required
@admin_required
def api_sponsors_config():
    """Get or update autonomous agent config (Phase 0 addition #2)."""
    import sqlite3
    try:
        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            if request.method == 'GET':
                cur = conn.cursor()
                cur.execute("SELECT * FROM sponsor_config WHERE id=1")
                row = cur.fetchone()
                return jsonify(dict(row) if row else {})

            data = request.get_json(force=True) or {}
            allowed = {'auto_draft_enabled', 'auto_draft_threshold',
                       'daily_send_limit', 'followup_days_1', 'followup_days_2', 'followup_days_3'}
            updates = {k: v for k, v in data.items() if k in allowed}
            if not updates:
                return jsonify({"error": "No valid config fields"}), 400

            updates['updated_at'] = datetime.utcnow().isoformat()
            cur = conn.cursor()
            set_clause = ', '.join(f"{k}=?" for k in updates)
            cur.execute(f"UPDATE sponsor_config SET {set_clause} WHERE id=1", list(updates.values()))
            conn.commit()
            return jsonify({"ok": True})
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsors_config error: %s", e)
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# RESEND WEBHOOK — bounce/open tracking
# ──────────────────────────────────────────────

@app.route('/api/sponsors/resend-webhook', methods=['POST'])
def api_sponsors_resend_webhook():
    """Handle Resend delivery webhooks for bounce/open tracking (Phase 0 addition #6)."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        event_type = data.get('type', '')
        email_data = data.get('data', {})
        message_id = email_data.get('email_id') or data.get('email_id', '')

        if not message_id:
            return jsonify({"ok": True})  # Ignore events without message ID

        from services.sponsor_radar_v2 import _get_db_path
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            now = datetime.utcnow().isoformat()

            if event_type == 'email.opened':
                cur.execute(
                    "UPDATE sponsor_outreach SET opened_at=? WHERE resend_message_id=? AND opened_at IS NULL",
                    (now, message_id)
                )
                # Log on sponsor
                cur.execute(
                    "SELECT sponsor_id FROM sponsor_outreach WHERE resend_message_id=?",
                    (message_id,)
                )
                row = cur.fetchone()
                if row:
                    cur.execute("""
                        INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                        VALUES (?,?,?,?)
                    """, (row[0], 'email_opened', f'Email opened — Resend ID: {message_id}', 'system'))

            elif event_type == 'email.bounced':
                cur.execute(
                    "UPDATE sponsor_outreach SET bounce_at=? WHERE resend_message_id=?",
                    (now, message_id)
                )
                cur.execute(
                    "SELECT sponsor_id FROM sponsor_outreach WHERE resend_message_id=?",
                    (message_id,)
                )
                row = cur.fetchone()
                if row:
                    cur.execute("""
                        INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                        VALUES (?,?,?,?)
                    """, (row[0], 'email_bounced', f'Email bounced — Resend ID: {message_id}', 'system'))

            conn.commit()
            return jsonify({"ok": True})
        except sqlite3.Error as e:
            conn.rollback()
            logging.error("Resend webhook DB error: %s", e)
            return jsonify({"ok": True})  # Return 200 to prevent Resend retry storms
        finally:
            conn.close()
    except Exception as e:
        logging.error("Resend webhook error: %s", e)
        return jsonify({"ok": True})  # Always 200 to Resend


# ──────────────────────────────────────────────
# PUBLIC SPONSORSHIP PAGE
# ──────────────────────────────────────────────

@app.route('/sponsorship')
def public_sponsorship():
    """Public-facing sponsorship/advertising page with live metrics."""
    try:
        from services.sponsorship_metrics_service import get_sponsorship_metrics
        import os as _os
        data_dir_path = None
        try:
            from app import app as _app
            data_dir_path = _app.root_path
        except Exception:
            pass
        from pathlib import Path
        data_dir = Path(data_dir_path or '.').parent / 'data' if data_dir_path else None
        metrics = get_sponsorship_metrics(data_dir=data_dir, db_session=db.session, days_back=30)
    except Exception as e:
        logging.warning("Could not load sponsorship metrics: %s", e)
        metrics = {
            "youtube_views": "10,000+",
            "website_unique_visits": "8,500+",
            "social_impressions": "50,000+",
            "period_days": 30,
        }
    return render_template('sponsorship.html', metrics=metrics)


@app.route('/api/sponsorship/contact', methods=['POST'])
def api_sponsorship_contact():
    """Inbound sponsor lead form — saves with status=inbound."""
    import sqlite3
    try:
        data = request.get_json(force=True) or {}
        company_name = (data.get('company_name') or '').strip()
        email = (data.get('email') or '').strip()
        name = (data.get('name') or '').strip()
        message = (data.get('message') or '').strip()
        package = (data.get('package') or '').strip()

        if not company_name or not email:
            return jsonify({"error": "company_name and email are required"}), 400

        # Basic email format check
        import re as _re
        if not _re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Invalid email format"}), 400

        from services.sponsor_radar_v2 import _get_db_path, ensure_tables
        ensure_tables()
        db_path = _get_db_path()
        now = datetime.utcnow().isoformat()
        notes = f"Package interest: {package}\nMessage: {message}"

        conn = sqlite3.connect(db_path)
        try:
            cur = conn.cursor()
            # Check if already exists
            cur.execute(
                "SELECT id FROM sponsors WHERE company_name=? AND is_deleted=0",
                (company_name,)
            )
            existing = cur.fetchone()
            if existing:
                # Add note to existing record
                cur.execute("""
                    INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                    VALUES (?,?,?,?)
                """, (existing[0], 'inbound_resubmit', f'Re-submitted via sponsorship form. {notes[:200]}', 'system'))
                conn.commit()
                return jsonify({"ok": True, "message": "Thank you! We'll be in touch soon."})

            cur.execute("""
                INSERT INTO sponsors (
                    company_name, contact_email, contact_name,
                    notes, status, pipeline_stage,
                    outreach_angle, created_at, updated_at
                ) VALUES (?,?,?,?,'inbound',1,?,?,?)
            """, (
                company_name, email, name, notes,
                f"Inbound lead — interested in {package or 'sponsorship'}",
                now, now
            ))
            sponsor_id = cur.lastrowid
            cur.execute("""
                INSERT INTO sponsor_activity_log (sponsor_id, action, detail, actor)
                VALUES (?,?,?,?)
            """, (sponsor_id, 'inbound_lead', f'Inbound via /sponsorship form. Package: {package}', 'system'))
            conn.commit()

            # Notify via Resend (best-effort)
            try:
                resend_key = os.environ.get("RESEND_API_KEY")
                if resend_key:
                    import requests as rlib
                    rlib.post(
                        "https://api.resend.com/emails",
                        headers={"Authorization": f"Bearer {resend_key}",
                                 "Content-Type": "application/json"},
                        json={
                            "from": "Protocol Pulse <noreply@protocolpulse.io>",
                            "to": ["pbx@protocolpulse.io"],
                            "subject": f"New Sponsor Lead: {company_name}",
                            "text": f"Company: {company_name}\nEmail: {email}\nName: {name}\nPackage: {package}\nMessage: {message}",
                        },
                        timeout=10,
                    )
            except Exception as notify_err:
                logging.warning("Lead notification email failed: %s", notify_err)

            return jsonify({"ok": True, "message": "Thank you! We'll be in touch within 24 hours."})
        except sqlite3.Error as e:
            conn.rollback()
            return jsonify({"error": "Database error"}), 500
        finally:
            conn.close()
    except Exception as e:
        logging.error("api_sponsorship_contact error: %s", e)
        return jsonify({"error": str(e)}), 500
