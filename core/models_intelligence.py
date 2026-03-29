"""
Intelligence Data Models — Three-Layer Signal Architecture
==========================================================
signals_raw       → immutable source facts (append-only)
signals_normalized → computed domain-specific scores (0-100)
convergence_state  → live cross-domain regime state
entity_registry    → canonical entity resolution

Add to core/models.py or import separately.
"""

import uuid
from datetime import datetime
from core import db


def _uuid():
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════
# Layer 1: signals_raw — Immutable Source Facts
# ═══════════════════════════════════════════════════════════════════════════

class SignalRaw(db.Model):
    __tablename__ = "signals_raw"

    id = db.Column(db.String(64), primary_key=True, default=_uuid)

    # Source identification
    source_family = db.Column(db.String(32), nullable=False, index=True)
    source_name = db.Column(db.String(64), nullable=False, index=True)
    source_event_id = db.Column(db.String(128), nullable=True)

    # Timestamps
    observed_at = db.Column(db.DateTime, nullable=False, index=True)
    ingested_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Classification
    topic = db.Column(db.String(32), nullable=False, index=True)
    entity_type = db.Column(db.String(32), nullable=True, index=True)
    entity_id = db.Column(db.String(128), nullable=True, index=True)
    entity_name = db.Column(db.String(255), nullable=True)

    asset = db.Column(db.String(32), nullable=True, default="BTC", index=True)
    market = db.Column(db.String(32), nullable=True)
    region = db.Column(db.String(32), nullable=True)

    # Signal properties
    polarity = db.Column(db.Float, nullable=True)          # -1.0 to +1.0
    magnitude = db.Column(db.Float, nullable=True)
    confidence = db.Column(db.Float, nullable=False, default=0.5)
    horizon = db.Column(db.String(16), nullable=False, default="swing")

    # Content
    title = db.Column(db.String(500), nullable=True)
    summary = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(1000), nullable=True)

    # Raw data
    raw_payload_json = db.Column(db.Text, nullable=False)
    extracted_facts_json = db.Column(db.Text, nullable=True)
    tags_json = db.Column(db.Text, nullable=True)

    # Integrity
    dedupe_key = db.Column(db.String(255), nullable=False, unique=True, index=True)
    is_valid = db.Column(db.Boolean, nullable=False, default=True, index=True)
    invalid_reason = db.Column(db.String(255), nullable=True)

    # Quality
    freshness_seconds = db.Column(db.Integer, nullable=True)
    quality_flag = db.Column(db.String(20), nullable=False, default="unreviewed")

    def __repr__(self):
        return f"<SignalRaw {self.source_family}/{self.topic} @ {self.observed_at}>"


# ═══════════════════════════════════════════════════════════════════════════
# Layer 2: signals_normalized — Computed Domain Scores
# ═══════════════════════════════════════════════════════════════════════════

class SignalNormalized(db.Model):
    __tablename__ = "signals_normalized"

    id = db.Column(db.String(64), primary_key=True, default=_uuid)

    signal_key = db.Column(db.String(64), nullable=False, index=True)
    signal_family = db.Column(db.String(32), nullable=False, index=True)

    computed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)

    subject_type = db.Column(db.String(32), nullable=False, default="global", index=True)
    subject_id = db.Column(db.String(128), nullable=False, default="global:bitcoin", index=True)
    asset = db.Column(db.String(32), nullable=True, default="BTC", index=True)

    # Scores
    raw_value = db.Column(db.Float, nullable=False)
    score_0_100 = db.Column(db.Float, nullable=False)
    z_score = db.Column(db.Float, nullable=True)
    percentile = db.Column(db.Float, nullable=True)
    direction = db.Column(db.Integer, nullable=False, default=0)  # -1, 0, +1
    confidence = db.Column(db.Float, nullable=False)
    freshness_seconds = db.Column(db.Integer, nullable=False)
    sample_size = db.Column(db.Integer, nullable=False, default=0)

    # Explainability
    methodology_version = db.Column(db.String(32), nullable=False, default="v1.0.0")
    features_json = db.Column(db.Text, nullable=False)
    contributing_raw_ids_json = db.Column(db.Text, nullable=False, default="[]")
    explanation_json = db.Column(db.Text, nullable=True)
    is_anomalous = db.Column(db.Boolean, nullable=False, default=False, index=True)

    # State label
    state_label = db.Column(db.String(32), nullable=True)
    regime_direction = db.Column(db.String(16), nullable=True)

    def __repr__(self):
        return f"<SignalNormalized {self.signal_key}={self.score_0_100:.1f} @ {self.computed_at}>"


# ═══════════════════════════════════════════════════════════════════════════
# Layer 3: convergence_state — Cross-Domain Regime State
# ═══════════════════════════════════════════════════════════════════════════

class ConvergenceState(db.Model):
    __tablename__ = "convergence_state"

    id = db.Column(db.String(64), primary_key=True, default=_uuid)
    computed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    regime_key = db.Column(db.String(64), nullable=False, default="btc_global", index=True)
    asset = db.Column(db.String(32), nullable=False, default="BTC", index=True)

    # Core scores
    convergence_score = db.Column(db.Float, nullable=False)
    fragmentation_score = db.Column(db.Float, nullable=False)
    momentum_score = db.Column(db.Float, nullable=False)
    conviction_score = db.Column(db.Float, nullable=False)

    # Dominant thesis
    dominant_thesis_key = db.Column(db.String(128), nullable=True)
    dominant_thesis_label = db.Column(db.String(255), nullable=True)
    dominant_direction = db.Column(db.Integer, nullable=False, default=0)
    confidence = db.Column(db.Float, nullable=False)

    # Signal alignment
    aligned_signal_keys_json = db.Column(db.Text, nullable=False, default="[]")
    conflicting_signal_keys_json = db.Column(db.Text, nullable=False, default="[]")
    cluster_state_json = db.Column(db.Text, nullable=False, default="{}")
    thesis_candidates_json = db.Column(db.Text, nullable=False, default="[]")
    explainability_json = db.Column(db.Text, nullable=False, default="{}")
    alert_flags_json = db.Column(db.Text, nullable=False, default="[]")
    ui_payload_json = db.Column(db.Text, nullable=False, default="{}")

    # Regime tracking
    state_changed = db.Column(db.Boolean, nullable=False, default=False)
    previous_state_id = db.Column(db.String(64), nullable=True)
    regime_label = db.Column(db.String(64), nullable=True)
    persistence_bars = db.Column(db.Integer, nullable=False, default=0)

    # Metadata
    methodology_version = db.Column(db.String(32), nullable=False, default="v1.0.0")
    window_start = db.Column(db.DateTime, nullable=False)
    window_end = db.Column(db.DateTime, nullable=False)
    participating_signals = db.Column(db.Integer, nullable=False, default=0)
    total_expected_signals = db.Column(db.Integer, nullable=False, default=6)

    def __repr__(self):
        return f"<ConvergenceState {self.regime_key} conv={self.convergence_score:.1f} @ {self.computed_at}>"


# ═══════════════════════════════════════════════════════════════════════════
# Helper: entity_registry — Canonical Entity Resolution
# ═══════════════════════════════════════════════════════════════════════════

class EntityRegistry(db.Model):
    __tablename__ = "entity_registry"

    id = db.Column(db.String(128), primary_key=True)
    entity_type = db.Column(db.String(32), nullable=False, index=True)
    canonical_name = db.Column(db.String(255), nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), nullable=False, unique=True, index=True)

    primary_asset = db.Column(db.String(32), nullable=True, default="BTC")
    region = db.Column(db.String(32), nullable=True)
    tags_json = db.Column(db.Text, nullable=True)
    aliases_json = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)

    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Entity {self.entity_type}:{self.canonical_name}>"
