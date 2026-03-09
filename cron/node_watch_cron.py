#!/usr/bin/env python3
"""
Protocol Pulse — Bitcoin Node Watch Cron  (post-audit second pass)
Polls Bitnodes API every 15 minutes, stores snapshot, fires threshold alerts.

Crontab:
    */15 * * * * /usr/bin/python3 /home/ultron/protocol_pulse/cron/node_watch_cron.py >> /var/log/node_watch.log 2>&1

Alert edge-trigger design:
  Alerts fire ONLY when a condition transitions from False → True.
  Condition state is persisted in `daily_alert_active` / `weekly_alert_active`
  columns so an oscillating metric does not re-fire on every poll.
"""

import sys
import os
import json
import logging
import fcntl
import time
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
REQUEST_TIMEOUT       = 15    # seconds per attempt
MAX_RETRIES           = 3
RETRY_BACKOFF_BASE    = 10    # seconds; doubles each retry

LOCK_FILE             = '/tmp/node_watch_cron.lock'

# Alert thresholds
ALERT_DAILY_DELTA     = 500   # ±500 nodes vs 24hr ago
ALERT_WEEKLY_DROP     = 1000  # -1000 over 7 days

# Milestone thresholds — only celebrate ≥ this value
MILESTONE_STEP        = 5000
MILESTONE_MIN         = 20000   # ignore 5k/10k/15k (historical)


# ── Exclusive process lock ────────────────────────────────────────────────────
def acquire_lock():
    """
    Use flock to prevent two concurrent cron instances from running.
    Returns the lock file handle (caller must keep reference alive).
    """
    fh = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        log.warning('Another instance is running — exiting.')
        sys.exit(0)
    return fh


# ── Bitnodes fetch with retry ────────────────────────────────────────────────
def fetch_bitnodes_snapshot():
    """
    Fetch latest Bitnodes snapshot with exponential-backoff retry.
    Returns:
        {'node_count': int, 'bitnodes_timestamp': int, 'versions': dict,
         'countries': dict, 'ipv4': int, 'ipv6': int}
    Raises:
        RuntimeError if all retries exhausted.
    """
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(
                BITNODES_SNAPSHOT_URL,
                timeout=REQUEST_TIMEOUT,
                headers={'Accept': 'application/json'},
            )
            r.raise_for_status()
            raw = r.json()

            results = raw.get('results', [])
            if not results:
                raise ValueError('Bitnodes returned empty results list')

            snap  = results[0]
            nodes = snap.get('nodes', {})
            total = snap.get('total_nodes') or len(nodes)
            if total == 0:
                raise ValueError('Node count is zero — likely API outage')

            # Warn on significant mismatch between reported total and parsed count
            if total > 0 and abs(len(nodes) - total) / total > 0.05:
                log.warning(
                    'Node count mismatch: total_nodes=%d, parsed=%d', total, len(nodes)
                )

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
                'node_count':        total,
                'bitnodes_timestamp': snap.get('timestamp', 0),
                'versions':          dict(sorted(versions.items(),  key=lambda x: x[1], reverse=True)[:20]),
                'countries':         dict(sorted(countries.items(), key=lambda x: x[1], reverse=True)[:30]),
                'ipv4': ipv4,
                'ipv6': ipv6,
            }

        except Exception as exc:
            last_exc = exc
            wait = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
            log.warning('Bitnodes attempt %d/%d failed: %s — retrying in %ds',
                        attempt, MAX_RETRIES, exc, wait)
            if attempt < MAX_RETRIES:
                time.sleep(wait)

    raise RuntimeError('All %d Bitnodes retries exhausted. Last error: %s' % (MAX_RETRIES, last_exc))


# ── Alert logic (stateful edge-triggered) ────────────────────────────────────
# Alert type constants — consistent strings, easy to key on downstream
ALERT_ATH        = 'ATH ALERT: Bitcoin nodes hit {count:,}'
ALERT_MILESTONE  = 'MILESTONE: Bitcoin nodes crossed {milestone:,}'
ALERT_DAILY      = 'NETWORK CHANGE: {delta:,} node {direction} vs 24hr ago'
ALERT_WEEKLY     = 'CONTRACTION WARNING: -{delta:,} nodes over 7 days'


def check_alerts(NodeSnapshot, new_count, prev):
    """
    Compute (alert_fired, daily_active, weekly_active) for the new snapshot.

    Edge-trigger rule:
      - daily_active  = whether daily-delta condition is currently breached
      - weekly_active = whether weekly-contraction condition is currently breached
      - alert_fired   = non-None only when transitioning False → True

    ATH and milestone alerts are one-shot events, not stateful conditions.
    """
    prev_daily_active  = prev.daily_alert_active  if prev else False
    prev_weekly_active = prev.weekly_alert_active if prev else False
    prev_count         = prev.node_count          if prev else 0

    alert_fired    = None
    daily_active   = False
    weekly_active  = False

    # ── ATH (one-shot) ────────────────────────────────────────────────────────
    ath_row = (
        NodeSnapshot.query
        .order_by(NodeSnapshot.node_count.desc())
        .with_entities(NodeSnapshot.node_count)
        .first()
    )
    if ath_row and new_count > ath_row[0]:
        return ALERT_ATH.format(count=new_count), daily_active, weekly_active

    # ── Milestone (one-shot) ─────────────────────────────────────────────────
    prev_ms = (prev_count // MILESTONE_STEP) * MILESTONE_STEP
    cur_ms  = (new_count  // MILESTONE_STEP) * MILESTONE_STEP
    if cur_ms > prev_ms and cur_ms >= MILESTONE_MIN and new_count >= cur_ms:
        return ALERT_MILESTONE.format(milestone=cur_ms), daily_active, weekly_active

    # ── Daily ±500 (stateful) ─────────────────────────────────────────────────
    yesterday = datetime.utcnow() - timedelta(hours=24)
    day_snap = (
        NodeSnapshot.query
        .filter(NodeSnapshot.timestamp <= yesterday)
        .order_by(NodeSnapshot.timestamp.desc())
        .first()
    )
    if day_snap:
        delta = new_count - day_snap.node_count
        daily_active = abs(delta) >= ALERT_DAILY_DELTA
        # Fire only on rising edge (condition newly became true)
        if daily_active and not prev_daily_active:
            direction   = 'surge' if delta > 0 else 'drop'
            alert_fired = ALERT_DAILY.format(delta=abs(delta), direction=direction)

    # ── Weekly -1000 (stateful) ───────────────────────────────────────────────
    # Only check if daily alert didn't already fire this snapshot
    if alert_fired is None:
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_snap = (
            NodeSnapshot.query
            .filter(NodeSnapshot.timestamp <= week_ago)
            .order_by(NodeSnapshot.timestamp.desc())
            .first()
        )
        if week_snap:
            weekly_delta = new_count - week_snap.node_count
            weekly_active = weekly_delta <= -ALERT_WEEKLY_DROP
            if weekly_active and not prev_weekly_active:
                alert_fired = ALERT_WEEKLY.format(delta=abs(weekly_delta))

    return alert_fired, daily_active, weekly_active


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    log.info('node_watch_cron starting')

    # Prevent concurrent runs via exclusive file lock
    lock_fh = acquire_lock()

    # 1. Fetch from Bitnodes (with retry)
    try:
        data = fetch_bitnodes_snapshot()
    except RuntimeError as e:
        log.error('%s', e)
        sys.exit(1)

    log.info('Bitnodes OK — %d nodes (bitnodes_ts=%d)', data['node_count'], data['bitnodes_timestamp'])

    # 2. Boot Flask app context
    try:
        os.environ.setdefault('FLASK_ENV', 'production')
        from app import app, db
        import models
        NodeSnapshot = models.NodeSnapshot
    except Exception as e:
        log.error('App boot failed: %s', e)
        sys.exit(1)

    with app.app_context():
        # Ensure table exists (idempotent — safe for new columns added via ALTER)
        try:
            db.create_all()
        except Exception as e:
            log.warning('db.create_all: %s', e)

        # Previous snapshot (for edge-trigger state)
        try:
            prev = NodeSnapshot.query.order_by(NodeSnapshot.timestamp.desc()).first()
        except Exception as e:
            log.warning('Could not fetch prev snapshot: %s', e)
            prev = None

        # Alert check
        try:
            alert_fired, daily_active, weekly_active = check_alerts(
                NodeSnapshot, data['node_count'], prev
            )
        except Exception as e:
            log.warning('Alert check error: %s', e)
            alert_fired   = None
            daily_active  = False
            weekly_active = False

        if alert_fired:
            log.warning('ALERT: %s', alert_fired)

        # Use Bitnodes upstream timestamp for the snapshot (not server wall-clock)
        # This ensures delta calculations use data timestamps, not processing timestamps.
        if data['bitnodes_timestamp']:
            snap_ts = datetime.utcfromtimestamp(data['bitnodes_timestamp'])
        else:
            snap_ts = datetime.utcnow()

        # Persist snapshot
        try:
            snap = NodeSnapshot(
                node_count=data['node_count'],
                timestamp=snap_ts,
                snapshot_data=json.dumps({
                    'versions':  data['versions'],
                    'countries': data['countries'],
                    'ipv4':      data['ipv4'],
                    'ipv6':      data['ipv6'],
                }),
                alert_fired=alert_fired,
                daily_alert_active=daily_active,
                weekly_alert_active=weekly_active,
            )
            db.session.add(snap)
            db.session.commit()
            log.info(
                'Snapshot saved — id=%d count=%d daily_active=%s weekly_active=%s alert=%s',
                snap.id, snap.node_count, daily_active, weekly_active, alert_fired or 'none'
            )
        except Exception as e:
            db.session.rollback()
            log.error('DB write failed: %s', e)
            sys.exit(1)

    # Release lock (fd closes on process exit, but be explicit)
    fcntl.flock(lock_fh, fcntl.LOCK_UN)
    lock_fh.close()


if __name__ == '__main__':
    main()
