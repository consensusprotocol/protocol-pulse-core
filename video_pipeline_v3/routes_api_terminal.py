"""Pulse Terminal API — Commander tier endpoints for pipeline intelligence data.

Endpoints:
  GET /api/v2/terminal/topics     — Topic velocity data
  GET /api/v2/terminal/entities   — Entity mention tracking
  GET /api/v2/terminal/sentiment  — Overall market sentiment
  GET /api/v2/terminal/breaking   — Breaking news alerts

Authentication: X-API-Key header required on all endpoints.
"""

import json
import os
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, jsonify, request

terminal_bp = Blueprint("terminal", __name__)

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "intelligence")

MOCK_TOPICS = {
    "mock": True,
    "note": "Pipeline data not yet accumulated. Real data populates after first production scan.",
    "topics": [
        {"topic": "ETF flows", "channels": 7, "sentiment": "bullish", "velocity_score": 85},
        {"topic": "mining difficulty", "channels": 4, "sentiment": "bearish", "velocity_score": 42},
        {"topic": "self-custody", "channels": 3, "sentiment": "neutral", "velocity_score": 35},
    ],
    "scan_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "next_scan": None,
}

MOCK_ENTITIES = {
    "mock": True,
    "note": "Pipeline data not yet accumulated. Real data populates after first production scan.",
    "entities": [
        {"name": "Saylor", "mentions_24h": 14, "sentiment_shift": "+23%"},
        {"name": "BlackRock", "mentions_24h": 9, "sentiment_shift": "+5%"},
    ],
}

MOCK_SENTIMENT = {
    "mock": True,
    "note": "Pipeline data not yet accumulated. Real data populates after first production scan.",
    "overall": {"score": 72, "label": "bullish", "change_24h": "+7"},
    "institutional": {"score": 85, "label": "very_bullish"},
    "retail": {"score": 55, "label": "neutral"},
}

MOCK_BREAKING = {
    "mock": True,
    "note": "Pipeline data not yet accumulated. Real data populates after first production scan.",
    "breaking": False,
    "last_alert": None,
    "monitoring": True,
}


def _load_api_keys():
    path = os.path.join(CONFIG_DIR, "api_keys.json")
    if not os.path.exists(path):
        return {"keys": []}
    with open(path) as f:
        return json.load(f)


def _authenticate(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get("X-API-Key", "")
        if not api_key:
            return jsonify({"error": "Missing X-API-Key header"}), 401

        keys_data = _load_api_keys()
        matched = None
        for entry in keys_data.get("keys", []):
            if entry["key"] == api_key:
                matched = entry
                break

        if not matched:
            return jsonify({"error": "Invalid API key"}), 403

        request.api_tier = matched.get("tier", "free")
        request.api_subscriber = matched.get("subscriber", "unknown")
        return f(*args, **kwargs)
    return decorated


def _load_data_file(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@terminal_bp.route("/api/v2/terminal/topics", methods=["GET"])
@_authenticate
def get_topics():
    data = _load_data_file("daily_signals.json")
    if data is None:
        result = dict(MOCK_TOPICS)
        result["scan_time"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        result = {
            "topics": data.get("topic_velocity", []),
            "scan_time": data.get("scan_time", ""),
            "next_scan": data.get("next_scan"),
        }

    # Free tier: only top 3 topics
    if getattr(request, "api_tier", "free") != "commander":
        result["topics"] = result.get("topics", [])[:3]
        result["tier"] = "free"
    else:
        result["tier"] = "commander"

    return jsonify(result)


@terminal_bp.route("/api/v2/terminal/entities", methods=["GET"])
@_authenticate
def get_entities():
    data = _load_data_file("entity_mentions.json")
    if data is None:
        return jsonify(MOCK_ENTITIES)
    return jsonify(data)


@terminal_bp.route("/api/v2/terminal/sentiment", methods=["GET"])
@_authenticate
def get_sentiment():
    data = _load_data_file("sentiment.json")
    if data is None:
        return jsonify(MOCK_SENTIMENT)
    return jsonify(data)


@terminal_bp.route("/api/v2/terminal/breaking", methods=["GET"])
@_authenticate
def get_breaking():
    data = _load_data_file("daily_signals.json")
    if data is None:
        return jsonify(MOCK_BREAKING)

    breaking = data.get("breaking_threshold", False)
    return jsonify({
        "breaking": breaking,
        "last_alert": data.get("last_breaking_alert"),
        "monitoring": True,
    })
