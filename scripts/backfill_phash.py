#!/usr/bin/env python3
"""
backfill_phash.py — Compute image_phash for published articles, then fix collisions.

Phase 1: Compute phash for every published article (local files + URLs).
Phase 2: Find collision groups (hamming dist <= 6), keep oldest, regenerate rest.

Uses direct sqlite3 for persistence. image_guard for phash computation and distance.

Usage:
    python3 scripts/backfill_phash.py                      # full run
    python3 scripts/backfill_phash.py --limit 200          # newest N only
    python3 scripts/backfill_phash.py --phase1-only        # just compute, no regen
"""
import os, sys, sqlite3, logging, io, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/protocol_pulse/.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_DEFAULT = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")

from articles.image_guard import compute_phash, _hamming, check_image_bytes, remember_accepted


def get_image_bytes(url, static_root=None):
    """Get image bytes from URL or local path. Returns bytes or None."""
    if not url:
        return None
    if url.startswith('http'):
        try:
            import requests
            r = requests.get(url, timeout=12)
            r.raise_for_status()
            return r.content
        except Exception:
            return None
    elif url.startswith('/static/'):
        # Try production static dir, then worktree
        for base in [os.path.expanduser('~/protocol_pulse'),
                     os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')]:
            path = os.path.join(base, url.lstrip('/'))
            if os.path.exists(path):
                try:
                    with open(path, 'rb') as f:
                        return f.read()
                except Exception:
                    pass
    return None


def phase1_compute(conn, limit):
    """Compute phash for all published articles missing it."""
    c = conn.cursor()
    if limit:
        c.execute("""
            SELECT id, cover_image_url, header_image_url, image_phash FROM articles
            WHERE published = 1 ORDER BY id DESC LIMIT ?
        """, (limit,))
    else:
        c.execute("""
            SELECT id, cover_image_url, header_image_url, image_phash FROM articles
            WHERE published = 1 ORDER BY id DESC
        """)
    rows = c.fetchall()

    computed = 0
    skipped = 0
    failed = 0

    for aid, cover_url, header_url, existing_phash in rows:
        if existing_phash:
            skipped += 1
            continue

        url = cover_url or header_url or ''
        img_bytes = get_image_bytes(url)
        if not img_bytes:
            failed += 1
            continue

        phash = compute_phash(img_bytes)
        if phash:
            c.execute("UPDATE articles SET image_phash = ? WHERE id = ?", (phash, aid))
            computed += 1
        else:
            failed += 1

    conn.commit()
    logger.info("Phase 1: computed=%d, skipped=%d (had phash), failed=%d", computed, skipped, failed)
    return computed


def phase2_fix_collisions(conn, limit):
    """Find collision groups, regenerate images for duplicates."""
    import requests

    c = conn.cursor()
    if limit:
        c.execute("""
            SELECT id, image_phash, title, category, cover_image_url FROM articles
            WHERE published = 1 AND image_phash IS NOT NULL AND image_phash != ''
            ORDER BY id DESC LIMIT ?
        """, (limit,))
    else:
        c.execute("""
            SELECT id, image_phash, title, category, cover_image_url FROM articles
            WHERE published = 1 AND image_phash IS NOT NULL AND image_phash != ''
            ORDER BY id DESC
        """)
    rows = c.fetchall()

    # Build collision groups: phash → [article_ids sorted ascending]
    # Use exact match (dist 0) first since that's the main issue
    phash_to_ids = {}
    id_to_row = {}
    for aid, ph, title, cat, url in rows:
        id_to_row[aid] = (title, cat, url)
        phash_to_ids.setdefault(ph, []).append(aid)

    # Also find near-duplicates (dist <= 6) not caught by exact match
    collision_groups = {}
    checked = set()
    for i, (aid, aph, _, _, _) in enumerate(rows):
        if aid in checked:
            continue
        group = [aid]
        checked.add(aid)
        for j, (bid, bph, _, _, _) in enumerate(rows):
            if bid in checked:
                continue
            try:
                if _hamming(aph, bph) <= 6:
                    group.append(bid)
                    checked.add(bid)
            except Exception:
                pass
        if len(group) > 1:
            group.sort()  # oldest first
            collision_groups[group[0]] = group

    if not collision_groups:
        logger.info("Phase 2: 0 collision groups found")
        return 0

    total_collisions = sum(len(g) - 1 for g in collision_groups.values())
    logger.info("Phase 2: %d collision groups, %d articles to regenerate",
                len(collision_groups), total_collisions)

    # Load ALL existing phashes for the guard
    c.execute("SELECT image_phash FROM articles WHERE image_phash IS NOT NULL AND image_phash != ''")
    db_phashes = {r[0] for r in c.fetchall()}
    session_phashes = set()

    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        logger.error("PEXELS_API_KEY not set — cannot regenerate")
        return 0

    from services.pexels_image import get_pexels_image

    regenerated = 0
    total_to_regen = sum(len(g) - 1 for g in collision_groups.values())
    regen_idx = 0
    for keeper_id, group in collision_groups.items():
        # Keep the oldest (keeper_id), regenerate the rest
        keeper_phash = None
        c.execute("SELECT image_phash FROM articles WHERE id = ?", (keeper_id,))
        row = c.fetchone()
        if row and row[0]:
            keeper_phash = row[0]
            session_phashes.add(keeper_phash)

        for aid in group[1:]:  # skip keeper
            regen_idx += 1
            title, cat, old_url = id_to_row.get(aid, ("bitcoin", "bitcoin", ""))

            # Remove old phash from db_phashes so the new one can be different
            old_ph_row = None
            c.execute("SELECT image_phash FROM articles WHERE id = ?", (aid,))
            r = c.fetchone()
            if r and r[0]:
                old_ph_row = r[0]
                db_phashes.discard(old_ph_row)

            new_url, new_phash = get_pexels_image(
                title or "bitcoin", cat or "bitcoin", article_id=aid,
                db_phashes=db_phashes, session_phashes=session_phashes)

            if new_url and new_url != "/static/images/default-header.png" and new_phash:
                c.execute("""
                    UPDATE articles SET cover_image_url = ?, header_image_url = ?, image_phash = ?
                    WHERE id = ?
                """, (new_url, new_url, new_phash, aid))
                db_phashes.add(new_phash)
                session_phashes.add(new_phash)
                regenerated += 1
                logger.info("Regen %d/%d ID %d: phash=%s url=%s", regen_idx, total_to_regen, aid, new_phash, new_url[:60])
                # Commit progress and throttle to stay under Pexels rate limit
                if regenerated % 5 == 0:
                    conn.commit()
                time.sleep(3)
            else:
                logger.warning("Regen FAIL %d/%d ID %d: Pexels returned default", regen_idx, total_to_regen, aid)
                # Re-add old phash
                if old_ph_row:
                    db_phashes.add(old_ph_row)
                time.sleep(2)  # back off after failure too

    conn.commit()
    logger.info("Phase 2: regenerated %d articles", regenerated)
    return regenerated


def main():
    limit = None
    phase1_only = '--phase1-only' in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])
        if arg == '--db' and i + 1 < len(sys.argv):
            DB_DEFAULT_override = sys.argv[i + 1]

    db_path = DB_DEFAULT
    conn = sqlite3.connect(db_path)

    phase1_compute(conn, limit)

    if not phase1_only:
        phase2_fix_collisions(conn, limit or 200)

    conn.close()


if __name__ == '__main__':
    main()
