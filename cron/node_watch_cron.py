#!/usr/bin/env python3
"""
Protocol Pulse — Bitcoin Node Watch Cron
Polls Bitnodes API every 15 minutes, stores snapshot, fires threshold alerts.

Crontab:
    */15 * * * * /usr/bin/python3 /home/ultron/protocol_pulse/cron/node_watch_cron.py >> /var/log/node_watch.log 2>&1
"""

import sys
import os
import json
import logging
import requests
from datetime import datetime, timedelta

# ── Project root ──────────────────────────────────────────────────────────────
_CRON_DIR    = os.path.dirname(os.path.abspath(__file__))
_PROJECT_DIR = os.path.dirname(_CRON_DIR)
sys.path.insert(0, _PROJECT_DIR)
sys.path.insert(0, os.path.join(_PROJECT_DIR, 'core'))

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [node_watch] %(levelname)s %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ',
)
log = logging.getLogger('node_watch')

# ── Constants ─────────────────────────────────────────────────────────────────
BITNODES_SNAPSHOT_URL = 'https://bitnodes.io/api/v1/snapshots/?limit=1'
REQUEST_TIMEOUT       = 15  # seconds

# Alert thresholds
ALERT_DAILY_DELTA  = 500   # ±500 nodes vs yesterday
ALERT_WEEKLY_DROP  = 1000  # -1000 over 7 days
MILESTONE_STEP     = 5000  # 20k, 25k, 30k …


# ── Bitnodes fetch ────────────────────────────────────────────────────────────
def fetch_bitnodes_snapshot():
    """
    Returns:
        {'node_count': int, 'timestamp': int, 'versions': dict,
         'countries': dict, 'ipv4': int, 'ipv6': int}
    Raises on failure.
    """
    r = requests.get(
        BITNODES_SNAPSHOT_URL,
        timeout=REQUEST_TIMEOUT,
        headers={'Accept': 'application/json'},
    )
    r.raise_for_status()
    raw = r.json()

    results = raw.get('results', [])
    if not results:
        raise ValueError('Bitnodes returned empty results')

    snap  = results[0]
    nodes = snap.get('nodes', {})
    total = snap.get('total_nodes') or len(nodes)
    if total == 0:
        raise ValueError('Node count is zero — likely API outage')

    versions: dict  = {}
    countries: dict = {}
    ipv4 = 0
    ipv6 = 0

    for addr, info in nodes.items():
        if not isinstance(info, list):
            continue
        ver     = info[1] if len(info) > 1 else 'unknown'
        country = info[7] if len(info) > 7 else None
        versions[ver] = versions.get(ver, 0) + 1
        if country:
            countries[country] = countries.get(country, 0) + 1
        if addr.startswith('['):
            ipv6 += 1
        else:
            ipv4 += 1

    return {
        'node_count': total,
        'timestamp':  snap.get('timestamp', 0),
        'versions':   dict(sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:20]),
        'countries':  dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:30]),
        'ipv4': ipv4,
        'ipv6': ipv6,
    }


# ── Alert logic (edge-triggered) ──────────────────────────────────────────────
def check_alerts(NodeSnapshot, new_count):
    """
    Returns alert_type string or None.
    Edge-triggered: does NOT re-fire if the same alert already appears on the
    most recent snapshot.
    """
    prev = NodeSnapshot.query.order_by(NodeSnapshot.timestamp.desc()).first()
    prev_count = prev.node_count if prev else 0

    # ATH
    ath = (
        NodeSnapshot.query
        .order_by(NodeSnapshot.node_count.desc())
        .with_entities(NodeSnapshot.node_count)
        .first()
    )
    if ath and new_count > ath[0]:
        return 'ATH ALERT: Bitcoin nodes hit {:,}'.format(new_count)

    # Milestone (crossed a MILESTONE_STEP boundary since last snapshot)
    prev_ms = (prev_count // MILESTONE_STEP) * MILESTONE_STEP
    cur_ms  = (new_count  // MILESTONE_STEP) * MILESTONE_STEP
    if cur_ms > prev_ms and new_count >= cur_ms and cur_ms > 0:
        return 'MILESTONE: Bitcoin nodes crossed {:,}'.format(cur_ms)

    # Daily ±500
    yesterday = datetime.utcnow() - timedelta(hours=24)
    day_snap = (
        NodeSnapshot.query
        .filter(NodeSnapshot.timestamp <= yesterday)
        .order_by(NodeSnapshot.timestamp.desc())
        .first()
    )
    if day_snap:
        delta = new_count - day_snap.node_count
        if abs(delta) >= ALERT_DAILY_DELTA:
            direction = 'surge' if delta > 0 else 'drop'
            alert = 'NETWORK CHANGE: {:,} node {} vs 24hr ago'.format(abs(delta), direction)
            # Edge: skip if previous snapshot already has same type
            if prev and prev.alert_fired and prev.alert_fired.startswith('NETWORK CHANGE:'):
                return None
            return alert

    # Weekly -1000
    week_ago = datetime.utcnow() - timedelta(days=7)
    week_snap = (
        NodeSnapshot.query
        .filter(NodeSnapshot.timestamp <= week_ago)
        .order_by(NodeSnapshot.timestamp.desc())
        .first()
    )
    if week_snap:
        weekly_delta = new_count - week_snap.node_count
        if weekly_delta <= -ALERT_WEEKLY_DROP:
            alert = 'CONTRACTION WARNING: -{:,} nodes over 7 days'.format(abs(weekly_delta))
            if prev and prev.alert_fired and prev.alert_fired.startswith('CONTRACTION WARNING:'):
                return None
            return alert

    return None


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info('node_watch_cron starting')

    try:
        data = fetch_bitnodes_snapshot()
    except Exception as e:
        log.error('Bitnodes fetch failed: %s', e)
        sys.exit(1)

    log.info('Bitnodes OK — %d nodes', data['node_count'])

    try:
        os.environ.setdefault('FLASK_ENV', 'production')
        from app import app, db
        import models
        NodeSnapshot = models.NodeSnapshot
    except Exception as e:
        log.error('App boot failed: %s', e)
        sys.exit(1)

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            log.warning('db.create_all: %s', e)

        try:
            alert = check_alerts(NodeSnapshot, data['node_count'])
        except Exception as e:
            log.warning('Alert check error: %s', e)
            alert = None

        if alert:
            log.warning('ALERT: %s', alert)

        try:
            snap = NodeSnapshot(
                node_count=data['node_count'],
                timestamp=datetime.utcnow(),
                snapshot_data=json.dumps({
                    'versions':  data['versions'],
                    'countries': data['countries'],
                    'ipv4':      data['ipv4'],
                    'ipv6':      data['ipv6'],
                }),
                alert_fired=alert,
            )
            db.session.add(snap)
            db.session.commit()
            log.info('Snapshot saved — id=%d count=%d alert=%s',
                     snap.id, snap.node_count, alert or 'none')
        except Exception as e:
            db.session.rollback()
            log.error('DB write failed: %s', e)
            sys.exit(1)


if __name__ == '__main__':
    main()
