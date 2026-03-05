"""Daily newsletter trigger endpoint for Protocol Pulse."""
import os, json, requests
from datetime import datetime
from flask import Blueprint, jsonify, request

newsletter_trigger_bp = Blueprint("newsletter_trigger", __name__)
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

@newsletter_trigger_bp.route("/api/newsletter/send", methods=["POST"])
def send_daily_digest():
    auth = request.headers.get("Authorization", "")
    if "581b1076" not in auth and request.remote_addr != "127.0.0.1":
        return jsonify({"error": "unauthorized"}), 401
    try:
        date_str = datetime.now().strftime("%B %d, %Y")
        signals_path = os.path.join(os.path.dirname(__file__), "data", "intelligence", "daily_signals.json")
        topics = []
        if os.path.exists(signals_path):
            with open(signals_path) as f:
                topics = json.load(f).get("topics", [])[:3]
        topic_html = ""
        for t in topics:
            s = t.get("velocity_score", 0)
            c = "#00CC66" if t.get("sentiment") == "bullish" else "#CC0000" if t.get("sentiment") == "bearish" else "#888"
            topic_html += f'<tr><td style="padding:8px 0;color:#EDE">{t.get("topic","")}</td><td style="width:200px"><div style="background:#1F1F1F;border-radius:4px;height:20px"><div style="background:{c};width:{min(s,100)}%;height:100%;border-radius:4px"></div></div></td><td style="color:{c};text-align:right;padding-left:12px">{s}</td></tr>'
        html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0A0A0A;font-family:Arial,sans-serif"><div style="max-width:600px;margin:0 auto;background:#0A0A0A"><div style="padding:30px 20px;text-align:center"><h1 style="color:#CC0000;font-size:28px;margin:0">PROTOCOL PULSE</h1><p style="color:#888;font-size:14px;margin:8px 0 0">Daily Intelligence Brief &mdash; {date_str}</p></div><div style="height:1px;background:linear-gradient(90deg,transparent,#CC0000,transparent)"></div><div style="padding:20px"><h2 style="color:#CC0000;font-size:16px;letter-spacing:2px">TOPIC VELOCITY</h2><table style="width:100%">{topic_html}</table></div><div style="padding:20px;text-align:center"><a href="https://protocolpulse.io" style="display:inline-block;padding:12px 30px;background:#CC0000;color:white;text-decoration:none;border-radius:6px;font-weight:600">Read Full Briefing</a></div><div style="padding:20px;text-align:center;border-top:1px solid #1F1F1F"><p style="color:#555;font-size:12px">Protocol Pulse &mdash; Intelligence for Transactors</p></div></div></body></html>"""
        if not RESEND_API_KEY:
            return jsonify({"status": "preview", "html_length": len(html)}), 200
        r = requests.post("https://api.resend.com/emails", json={"from": "Protocol Pulse <intel@protocolpulse.io>", "to": ["pbx@consensusprotocol.com"], "subject": f"Protocol Pulse Daily Brief — {date_str}", "html": html}, headers={"Authorization": f"Bearer {RESEND_API_KEY}"}, timeout=10)
        return jsonify({"status": "sent", "resend_status": r.status_code}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
