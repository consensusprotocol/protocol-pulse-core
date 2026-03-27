#!/usr/bin/env python3
"""Ultron Relay Server — Full autopilot endpoint for remote command execution.
Runs on port 8201, exposed via Cloudflare tunnel at relay.protocolpulse.io
"""

import os
import sys
import json
import base64
import subprocess
import time
import hashlib
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Token auth — uses env var or falls back to hardcoded
# Set via: export ULTRON_RELAY_TOKEN="your_token"
TOKEN = "57eadb9f3e6503ecf381b9046f90f7c21dd98e1d9c17bc8d83061649b081edcf"

def check_auth():
    """Validate token from JSON body."""
    data = request.get_json(silent=True) or {}
    return data.get("token") == TOKEN

# ─── /health ────────────────────────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "service": "ultron-relay",
        "host": "ultron",
        "port": 8201,
        "token_set": bool(TOKEN),
        "endpoints": ["/health", "/exec", "/push", "/pull"]
    })

# ─── /exec — Run shell commands ─────────────────────────────────────────────
@app.route("/exec", methods=["POST"])
def exec_cmd():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    cmd = data.get("cmd", "")
    timeout = min(data.get("timeout", 120), 600)  # Max 10 min
    cwd = data.get("cwd", "/home/ultron/protocol_pulse")

    if not cmd:
        return jsonify({"error": "no cmd provided"}), 400

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd
        )
        return jsonify({
            "returncode": result.returncode,
            "stdout": result.stdout[-50000:],  # Cap output at 50KB
            "stderr": result.stderr[-10000:]
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": f"timeout after {timeout}s"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── /push — Write files to Ultron ──────────────────────────────────────────
@app.route("/push", methods=["POST"])
def push_file():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    path = data.get("path", "")
    content_b64 = data.get("content_b64", "")

    if not path or not content_b64:
        return jsonify({"error": "path and content_b64 required"}), 400

    # Security: only allow writes under /home/ultron
    if not os.path.abspath(path).startswith("/home/ultron"):
        return jsonify({"error": "path must be under /home/ultron"}), 403

    try:
        content = base64.b64decode(content_b64)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        return jsonify({
            "ok": True,
            "path": path,
            "bytes": len(content)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── /pull — Read files from Ultron ─────────────────────────────────────────
@app.route("/pull", methods=["POST"])
def pull_file():
    if not check_auth():
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    path = data.get("path", "")

    if not path:
        return jsonify({"error": "path required"}), 400

    if not os.path.abspath(path).startswith("/home/ultron"):
        return jsonify({"error": "path must be under /home/ultron"}), 403

    if not os.path.exists(path):
        return jsonify({"error": f"not found: {path}"}), 404

    try:
        with open(path, "rb") as f:
            content = f.read()
        return jsonify({
            "ok": True,
            "path": path,
            "bytes": len(content),
            "content_b64": base64.b64encode(content).decode()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ─── Main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"[RELAY] Starting Ultron relay on port 8201...")
    print(f"[RELAY] Token: {TOKEN[:8]}...{TOKEN[-8:]}")
    print(f"[RELAY] Endpoints: /health, /exec, /push, /pull")
    app.run(host="0.0.0.0", port=8201, debug=False)
