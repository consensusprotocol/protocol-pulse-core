#!/usr/bin/env python3
"""
Convergence Engine — Database Migration + Cycle Runner
======================================================
1. Creates the three intelligence tables if they don't exist
2. Runs a full convergence cycle (ingest → normalize → converge → persist)

Usage:
    python3 scripts/migrate_and_run_convergence.py
    python3 scripts/migrate_and_run_convergence.py --migrate-only
    python3 scripts/migrate_and_run_convergence.py --cycle-only
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "core"))
sys.path.insert(0, str(BASE_DIR / "services"))
os.chdir(str(BASE_DIR / "core"))  # ensure working dir matches existing Flask context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("convergence_cycle")


def migrate_tables():
    """Create intelligence tables if they don't exist."""
    from app import app, db

    # Import models so SQLAlchemy knows about them
    from models_intelligence import SignalRaw, SignalNormalized, ConvergenceState, EntityRegistry

    with app.app_context():
        # Create only the new tables (won't touch existing ones)
        db.create_all()

        # Verify tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()

        required = ['signals_raw', 'signals_normalized', 'convergence_state', 'entity_registry']
        for t in required:
            if t in tables:
                log.info("✅ Table '%s' exists", t)
            else:
                log.error("❌ Table '%s' MISSING", t)

        log.info("Migration complete. %d tables in database.", len(tables))


def run_convergence_cycle():
    """Execute full convergence cycle: compute signals → compute convergence → persist."""
    from app import app, db
    from models_intelligence import SignalNormalized, ConvergenceState
    from signal_normalizer_service import SignalNormalizer, compute_convergence

    normalizer = SignalNormalizer()
    results = normalizer.compute_all()

    if not results:
        log.error("No signal results computed. Aborting cycle.")
        return

    # Compute convergence
    conv = compute_convergence(results)
    now = datetime.utcnow()

    with app.app_context():
        # 1. Persist normalized signals
        for r in results:
            entry = SignalNormalized(
                id=str(uuid.uuid4()),
                signal_key=r['signal_key'],
                signal_family=r['signal_family'],
                computed_at=now,
                window_start=now - timedelta(hours=1),
                window_end=now,
                raw_value=r['raw_value'],
                score_0_100=r['score'],
                direction=r['direction'],
                confidence=r['confidence'],
                freshness_seconds=0,
                sample_size=r['sample_size'],
                features_json=json.dumps(r['features']),
                contributing_raw_ids_json=json.dumps(r.get('raw_ids', [])),
                explanation_json=json.dumps(r['explanation']),
                state_label=r['state_label'],
                regime_direction="bullish" if r['direction'] == 1 else "bearish" if r['direction'] == -1 else "neutral",
            )
            db.session.add(entry)
        log.info("Persisted %d normalized signals", len(results))

        # 2. Persist convergence state
        # Check for state change
        prev = (ConvergenceState.query
                .order_by(ConvergenceState.computed_at.desc())
                .first())
        state_changed = (prev is None or
                         prev.dominant_thesis_key != conv.get('dominant_thesis_key') or
                         abs(prev.convergence_score - conv['convergence_score']) > 10)

        conv_entry = ConvergenceState(
            id=str(uuid.uuid4()),
            computed_at=now,
            regime_key="btc_global",
            asset="BTC",
            convergence_score=conv['convergence_score'],
            fragmentation_score=conv['fragmentation_score'],
            momentum_score=conv['momentum_score'],
            conviction_score=conv['conviction_score'],
            dominant_thesis_key=conv.get('dominant_thesis_key'),
            dominant_thesis_label=conv.get('dominant_thesis_label'),
            dominant_direction=conv.get('dominant_direction', 0),
            confidence=conv['confidence'],
            aligned_signal_keys_json=json.dumps(conv.get('aligned_signals', [])),
            conflicting_signal_keys_json=json.dumps(conv.get('conflicting_signals', [])),
            cluster_state_json="{}",
            thesis_candidates_json="[]",
            explainability_json=json.dumps(conv.get('explainability', {})),
            alert_flags_json=json.dumps(conv.get('alerts', [])),
            ui_payload_json=json.dumps(conv.get('ui_payload', {})),
            state_changed=state_changed,
            previous_state_id=prev.id if prev else None,
            regime_label=conv.get('regime_label'),
            persistence_bars=(prev.persistence_bars + 1 if prev and not state_changed else 0),
            window_start=now - timedelta(minutes=5),
            window_end=now,
            participating_signals=conv.get('participating_signals', 0),
            total_expected_signals=conv.get('total_expected_signals', 6),
        )
        db.session.add(conv_entry)
        db.session.commit()

        log.info(
            "Convergence cycle complete: score=%.1f thesis=%s direction=%d changed=%s",
            conv['convergence_score'],
            conv.get('dominant_thesis_key', 'unknown'),
            conv.get('dominant_direction', 0),
            state_changed,
        )

        # Print summary
        print(f"\n{'='*60}")
        print(f"CONVERGENCE CYCLE COMPLETE — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"{'='*60}")
        for r in results:
            arrow = "▲" if r['direction'] == 1 else "▼" if r['direction'] == -1 else "●"
            print(f"  {arrow} {r['signal_key']}: {r['score']:.1f} ({r['state_label']}) conf={r['confidence']:.2f}")
            print(f"    → {r['explanation']['headline']}")
        print(f"\n  CONVERGENCE: {conv['convergence_score']:.1f}")
        print(f"  THESIS: {conv.get('dominant_thesis_label', 'unknown')}")
        print(f"  REGIME CHANGED: {state_changed}")
        if conv.get('alerts'):
            for a in conv['alerts']:
                print(f"  ⚡ ALERT: {a.get('label', '')} ({a.get('severity', '')})")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate-only", action="store_true")
    parser.add_argument("--cycle-only", action="store_true")
    args = parser.parse_args()

    if args.migrate_only:
        migrate_tables()
    elif args.cycle_only:
        run_convergence_cycle()
    else:
        migrate_tables()
        run_convergence_cycle()
