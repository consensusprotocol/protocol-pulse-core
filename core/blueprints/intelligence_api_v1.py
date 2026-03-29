"""
Intelligence API v1 — Convergence Engine Endpoints
===================================================
Clean, typed API for the Commander terminal and public intelligence surfaces.

Endpoints:
  GET /api/v1/intelligence/signals/latest
  GET /api/v1/intelligence/signals/history
  GET /api/v1/intelligence/convergence/latest
  GET /api/v1/intelligence/convergence/graph
  GET /api/v1/intelligence/entities/<entity_id>

All responses include confidence, freshness, drivers, counterweights.
No score renders without explainability.
"""

import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

log = logging.getLogger("intelligence_api_v1")

intel_api_v1 = Blueprint('intel_api_v1', __name__)


def _parse_explanation(explanation_json):
    """Safely parse explanation JSON string."""
    if isinstance(explanation_json, dict):
        return explanation_json
    try:
        return json.loads(explanation_json) if explanation_json else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _parse_json_field(field):
    """Safely parse any JSON text field."""
    if isinstance(field, (dict, list)):
        return field
    try:
        return json.loads(field) if field else {}
    except (json.JSONDecodeError, TypeError):
        return {}


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/intelligence/signals/latest
# ═══════════════════════════════════════════════════════════════════════════

@intel_api_v1.route('/api/v1/intelligence/signals/latest')
def get_latest_signals():
    """Returns latest normalized signals for all or specific keys."""
    from models_intelligence import SignalNormalized
    from app import db

    asset = request.args.get('asset', 'BTC')
    keys_param = request.args.get('keys', '')
    subject_id = request.args.get('subject_id', 'global:bitcoin')

    # Get latest signal per key
    signal_keys = ['miner_conviction', 'exchange_pressure', 'insider_heat']
    if keys_param:
        signal_keys = [k.strip() for k in keys_param.split(',')]

    signals = []
    for key in signal_keys:
        row = (SignalNormalized.query
               .filter_by(signal_key=key, subject_id=subject_id, asset=asset)
               .order_by(SignalNormalized.computed_at.desc())
               .first())
        if not row:
            continue

        explanation = _parse_explanation(row.explanation_json)
        signals.append({
            "signal_key": row.signal_key,
            "signal_family": row.signal_family,
            "score": row.score_0_100,
            "direction": row.direction,
            "confidence": row.confidence,
            "freshness_seconds": row.freshness_seconds,
            "state_label": row.state_label,
            "regime_direction": row.regime_direction,
            "headline": explanation.get("headline", ""),
            "drivers": explanation.get("drivers", []),
            "counterweights": explanation.get("counterweights", []),
            "sample_size": row.sample_size,
            "methodology_version": row.methodology_version,
            "computed_at": row.computed_at.isoformat() + "Z" if row.computed_at else None,
            "is_anomalous": row.is_anomalous,
        })

    return jsonify({
        "asset": asset,
        "subject_id": subject_id,
        "as_of": datetime.utcnow().isoformat() + "Z",
        "signal_count": len(signals),
        "signals": signals,
    })


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/intelligence/signals/history
# ═══════════════════════════════════════════════════════════════════════════

@intel_api_v1.route('/api/v1/intelligence/signals/history')
def get_signal_history():
    """Returns historical scores for a specific signal."""
    from models_intelligence import SignalNormalized

    signal_key = request.args.get('signal_key')
    if not signal_key:
        return jsonify({"error": "signal_key required"}), 400

    subject_id = request.args.get('subject_id', 'global:bitcoin')
    range_param = request.args.get('range', '24h')
    limit = min(int(request.args.get('limit', 500)), 2000)

    # Parse range
    range_map = {'1h': 1, '6h': 6, '24h': 24, '7d': 168, '30d': 720}
    hours = range_map.get(range_param, 24)
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    rows = (SignalNormalized.query
            .filter(SignalNormalized.signal_key == signal_key,
                    SignalNormalized.subject_id == subject_id,
                    SignalNormalized.computed_at >= cutoff)
            .order_by(SignalNormalized.computed_at.asc())
            .limit(limit)
            .all())

    points = [
        {
            "ts": row.computed_at.isoformat() + "Z",
            "score": row.score_0_100,
            "direction": row.direction,
            "confidence": row.confidence,
        }
        for row in rows
    ]

    return jsonify({
        "signal_key": signal_key,
        "subject_id": subject_id,
        "range": range_param,
        "point_count": len(points),
        "points": points,
    })


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/intelligence/convergence/latest
# ═══════════════════════════════════════════════════════════════════════════

@intel_api_v1.route('/api/v1/intelligence/convergence/latest')
def get_convergence_latest():
    """Returns latest convergence state — flagship Commander endpoint."""
    from models_intelligence import ConvergenceState

    regime_key = request.args.get('regime_key', 'btc_global')
    asset = request.args.get('asset', 'BTC')

    state = (ConvergenceState.query
             .filter_by(regime_key=regime_key, asset=asset)
             .order_by(ConvergenceState.computed_at.desc())
             .first())

    if not state:
        # Fall back to computing live
        return _compute_live_convergence()

    explainability = _parse_json_field(state.explainability_json)
    aligned = _parse_json_field(state.aligned_signal_keys_json)
    conflicting = _parse_json_field(state.conflicting_signal_keys_json)
    alerts = _parse_json_field(state.alert_flags_json)
    thesis_candidates = _parse_json_field(state.thesis_candidates_json)

    return jsonify({
        "asset": state.asset,
        "regime_key": state.regime_key,
        "as_of": state.computed_at.isoformat() + "Z" if state.computed_at else None,
        "convergence_score": state.convergence_score,
        "fragmentation_score": state.fragmentation_score,
        "momentum_score": state.momentum_score,
        "conviction_score": state.conviction_score,
        "dominant_thesis": {
            "key": state.dominant_thesis_key,
            "label": state.dominant_thesis_label,
            "direction": state.dominant_direction,
            "confidence": state.confidence,
        },
        "aligned_signals": aligned,
        "conflicting_signals": conflicting,
        "alerts": alerts,
        "explainability": explainability,
        "regime_label": state.regime_label,
        "participating_signals": state.participating_signals,
        "total_expected_signals": state.total_expected_signals,
        "state_changed": state.state_changed,
        "methodology_version": state.methodology_version,
    })


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/intelligence/convergence/graph
# ═══════════════════════════════════════════════════════════════════════════

@intel_api_v1.route('/api/v1/intelligence/convergence/graph')
def get_convergence_graph():
    """Returns graph payload for the frontend Orb/Web visualization."""
    from models_intelligence import ConvergenceState

    regime_key = request.args.get('regime_key', 'btc_global')
    asset_param = request.args.get('asset', 'BTC')

    state = (ConvergenceState.query
             .filter_by(regime_key=regime_key, asset=asset_param)
             .order_by(ConvergenceState.computed_at.desc())
             .first())

    if not state:
        return _compute_live_convergence_graph()

    ui_payload = _parse_json_field(state.ui_payload_json)

    return jsonify({
        "asset": state.asset,
        "regime_key": state.regime_key,
        "as_of": state.computed_at.isoformat() + "Z" if state.computed_at else None,
        "convergence_score": state.convergence_score,
        **ui_payload,
    })


# ═══════════════════════════════════════════════════════════════════════════
# GET /api/v1/intelligence/matrix
# ═══════════════════════════════════════════════════════════════════════════

@intel_api_v1.route('/api/v1/intelligence/matrix')
def get_sovereign_matrix():
    """
    Returns the Sovereign Signal Matrix payload — the public-facing composite.
    Combines latest signals + convergence into one response.
    """
    from models_intelligence import SignalNormalized, ConvergenceState

    signal_keys = ['miner_conviction', 'exchange_pressure', 'insider_heat']
    domains = []

    for key in signal_keys:
        row = (SignalNormalized.query
               .filter_by(signal_key=key, subject_id='global:bitcoin')
               .order_by(SignalNormalized.computed_at.desc())
               .first())
        if row:
            explanation = _parse_explanation(row.explanation_json)
            domains.append({
                "key": row.signal_family,
                "label": row.signal_family.capitalize(),
                "signal_key": row.signal_key,
                "score": row.score_0_100,
                "direction": row.direction,
                "confidence": row.confidence,
                "state_label": row.state_label,
                "status": "aligned" if row.direction != 0 else "mixed",
                "headline": explanation.get("headline", ""),
            })

    # Get convergence state
    conv = (ConvergenceState.query
            .order_by(ConvergenceState.computed_at.desc())
            .first())

    composite = {}
    if conv:
        composite = {
            "score": conv.convergence_score,
            "label": "Constructive" if conv.dominant_direction == 1 else "Cautious" if conv.dominant_direction == -1 else "Mixed",
            "direction": conv.dominant_direction,
            "confidence": conv.confidence,
            "headline": conv.dominant_thesis_label or "Awaiting sufficient data",
        }
    else:
        # Compute from available domains
        if domains:
            avg_score = sum(d['score'] for d in domains) / len(domains)
            composite = {
                "score": round(avg_score, 1),
                "label": "Constructive" if avg_score > 60 else "Cautious" if avg_score < 40 else "Mixed",
                "direction": 1 if avg_score > 60 else -1 if avg_score < 40 else 0,
                "confidence": round(sum(d['confidence'] for d in domains) / len(domains), 2),
                "headline": "Computed from available signals",
            }

    aligned_count = sum(1 for d in domains if d.get('direction') == composite.get('direction', 0) and d.get('direction') != 0)

    return jsonify({
        "type": "matrix",
        "as_of": datetime.utcnow().isoformat() + "Z",
        "composite": composite,
        "domains": domains,
        "alignment_count": aligned_count,
        "conflict_count": len(domains) - aligned_count,
        "fragmentation_score": conv.fragmentation_score if conv else 50,
        "dominant_thesis": {
            "key": conv.dominant_thesis_key if conv else "awaiting_data",
            "label": conv.dominant_thesis_label if conv else "Awaiting sufficient data",
        },
    })


# ═══════════════════════════════════════════════════════════════════════════
# Fallback: live computation when no DB rows exist
# ═══════════════════════════════════════════════════════════════════════════

def _compute_live_convergence():
    """Compute convergence live from data files when DB is empty."""
    try:
        import sys as _sys; _sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent)); from services.signal_normalizer_service import SignalNormalizer, compute_convergence
        normalizer = SignalNormalizer()
        results = normalizer.compute_all()
        conv = compute_convergence(results)

        return jsonify({
            "asset": "BTC",
            "regime_key": "btc_global",
            "as_of": datetime.utcnow().isoformat() + "Z",
            "status": "degraded_live_compute", "source": "fallback",
            **{k: v for k, v in conv.items() if k != 'ui_payload'},
        })
    except Exception as e:
        log.error("Live convergence computation failed: %s", e)
        return jsonify({"status": "unavailable", "error": "Convergence engine initializing", "detail": str(e)}), 503


def _compute_live_convergence_graph():
    """Compute graph payload live."""
    try:
        import sys as _sys; _sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent.parent)); from services.signal_normalizer_service import SignalNormalizer, compute_convergence
        normalizer = SignalNormalizer()
        results = normalizer.compute_all()
        conv = compute_convergence(results)

        return jsonify({
            "asset": "BTC",
            "regime_key": "btc_global",
            "as_of": datetime.utcnow().isoformat() + "Z",
            "convergence_score": conv['convergence_score'],
            **conv.get('ui_payload', {}),
        })
    except Exception as e:
        return jsonify({"status": "unavailable", "error": "Graph engine initializing"}), 503
