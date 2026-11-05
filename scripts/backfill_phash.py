#!/usr/bin/env python3
"""
backfill_phash.py — Compute image_phash from LOCAL files, then fix remotes + collisions.

Phase 1: Compute phash from the LOCAL file at cover_image_url for every published article.
         Skips/flags rows whose cover is remote (http) or file missing.
Phase 2: Regenerates:
         (a) Every published article whose cover or header is remote/missing.
         (b) Every collision group (d<=6) among newest 300, keeping the oldest.
         Uses generate_article_header_image_with_phash for local-only output.
         4s throttle; on Pexels 429 back off 20s*attempt.

Usage:
    python3 scripts/backfill_phash.py                      # full run
    python3 scripts/backfill_phash.py --limit 300          # newest N only
    python3 scripts/backfill_phash.py --phase1-only        # just compute, no regen
"""
import os, sys, sqlite3, logging, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.expanduser('~/protocol_pulse/.env'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DB_DEFAULT = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")
STATIC_ROOT = os.path.expanduser("~/protocol_pulse")

from articles.image_guard import compute_phash, _hamming


def _local_file_path(url):
    """Convert a /static/... URL to an absolute path, or return None for remote/invalid."""
    if not url:
        return None
    if url.startswith('http'):
        return None  # remote — not local
    if url.startswith('/static/'):
        path = os.path.join(STATIC_ROOT, url.lstrip('/'))
        if os.path.exists(path):
            return path
    return None


def phase1_compute(conn, limit):
    """Compute phash from the LOCAL file at cover_image_url. Skip remote/missing."""
    c = conn.cursor()
    q = "SELECT id, cover_image_url, image_phash FROM articles WHERE published = 1 ORDER BY id DESC"
    if limit:
        q += f" LIMIT {int(limit)}"
    c.execute(q)
    rows = c.fetchall()

    computed = 0
    skipped_has_phash = 0
    skipped_remote = 0
    skipped_missing = 0
    recomputed = 0

    for aid, cover_url, existing_phash in rows:
        local_path = _local_file_path(cover_url)

        if local_path is None:
            if cover_url and cover_url.startswith('http'):
                skipped_remote += 1
                logger.debug("Phase 1 skip id=%d: remote URL", aid)
            else:
                skipped_missing += 1
                logger.debug("Phase 1 skip id=%d: missing/invalid path", aid)
            continue

        # Always recompute from the file to ensure DB matches actual file
        try:
            with open(local_path, 'rb') as f:
                img_bytes = f.read()
            phash = compute_phash(img_bytes)
            if phash:
                if phash != existing_phash:
                    c.execute("UPDATE articles SET image_phash = ? WHERE id = ?", (phash, aid))
                    if existing_phash:
                        recomputed += 1
                    else:
                        computed += 1
                else:
                    skipped_has_phash += 1
            else:
                skipped_missing += 1
        except Exception as e:
            logger.warning("Phase 1 error id=%d: %s", aid, e)
            skipped_missing += 1

    conn.commit()
    logger.info("Phase 1: computed=%d, recomputed=%d, already_correct=%d, remote=%d, missing=%d",
                computed, recomputed, skipped_has_phash, skipped_remote, skipped_missing)
    return computed + recomputed


def phase2_fix(conn, limit):
    """Regenerate: (a) remote/missing covers, (b) collision groups."""
    c = conn.cursor()
    limit_val = limit or 300

    # Load articles
    c.execute("""
        SELECT id, cover_image_url, header_image_url, image_phash, title, category
        FROM articles WHERE published = 1 ORDER BY id DESC LIMIT ?
    """, (limit_val,))
    rows = c.fetchall()

    # Identify articles needing regeneration
    needs_regen = set()
    id_to_row = {}
    for aid, cover, header, phash, title, cat in rows:
        id_to_row[aid] = (title, cat, cover)
        # (a) remote or missing cover/header
        if cover and cover.startswith('http'):
            needs_regen.add(aid)
        elif not cover or cover == '/static/images/default-header.png':
            needs_regen.add(aid)
        elif not os.path.exists(os.path.join(STATIC_ROOT, cover.lstrip('/'))):
            needs_regen.add(aid)
        if header and header.startswith('http'):
            needs_regen.add(aid)

    # (b) Find collision groups (d<=6) among rows that have phashes
    phash_rows = [(aid, phash) for aid, _, _, phash, _, _ in rows if phash]
    collision_groups = {}
    checked = set()
    for i, (aid, aph) in enumerate(phash_rows):
        if aid in checked:
            continue
        group = [aid]
        checked.add(aid)
        for j, (bid, bph) in enumerate(phash_rows):
            if j <= i or bid in checked:
                continue
            try:
                if _hamming(aph, bph) <= 6:
                    group.append(bid)
                    checked.add(bid)
            except Exception:
                pass
        if len(group) > 1:
            group.sort()  # oldest first = keeper
            collision_groups[group[0]] = group

    # Add collision victims (all except keeper) to regen set
    for keeper_id, group in collision_groups.items():
        for aid in group[1:]:
            needs_regen.add(aid)

    if not needs_regen:
        logger.info("Phase 2: 0 articles need regeneration")
        return 0

    logger.info("Phase 2: %d articles to regenerate (%d remote/missing, %d collision groups)",
                len(needs_regen),
                sum(1 for aid in needs_regen if aid not in [g for gs in collision_groups.values() for g in gs[1:]]),
                len(collision_groups))

    # Import image service for regeneration
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
        from image_service import ImageGenerationService
        img_svc = ImageGenerationService()
    except Exception as e:
        logger.error("Cannot import ImageGenerationService: %s", e)
        return 0

    regenerated = 0
    total = len(needs_regen)
    for idx, aid in enumerate(sorted(needs_regen, reverse=True)):
        title, cat, old_url = id_to_row.get(aid, ("bitcoin", "bitcoin", ""))
        try:
            new_url, new_phash = img_svc.generate_article_header_image_with_phash(
                title=title or "bitcoin", category=cat or "bitcoin")

            if new_url and new_url != "/static/images/default-header.png" and new_phash:
                c.execute("""
                    UPDATE articles SET cover_image_url = ?, header_image_url = ?, image_phash = ?
                    WHERE id = ?
                """, (new_url, new_url, new_phash, aid))
                regenerated += 1
                logger.info("Regen %d/%d ID %d: phash=%s path=%s", idx + 1, total, aid, new_phash, new_url[:60])
                if regenerated % 5 == 0:
                    conn.commit()
            else:
                logger.warning("Regen FAIL %d/%d ID %d: service returned default", idx + 1, total, aid)
        except Exception as e:
            logger.error("Regen ERROR %d/%d ID %d: %s", idx + 1, total, aid, e)

        time.sleep(4)  # 4s throttle

    conn.commit()
    logger.info("Phase 2: regenerated %d / %d articles", regenerated, total)
    return regenerated


def main():
    limit = None
    phase1_only = '--phase1-only' in sys.argv
    for i, arg in enumerate(sys.argv):
        if arg == '--limit' and i + 1 < len(sys.argv):
            limit = int(sys.argv[i + 1])

    db_path = DB_DEFAULT
    conn = sqlite3.connect(db_path)

    logger.info("=== Phase 1: compute phash from local files ===")
    phase1_compute(conn, limit)

    if not phase1_only:
        logger.info("=== Phase 2: regenerate remote/missing/collisions ===")
        phase2_fix(conn, limit or 300)

        # Re-run phase 1 over everything to update phashes for regenerated files
        logger.info("=== Phase 1 (re-run): recompute all phashes ===")
        phase1_compute(conn, None)

    conn.close()
    logger.info("=== Done ===")


if __name__ == '__main__':
    main()
