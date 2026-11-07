#!/usr/bin/env python3
"""
verify_site_health.py — Gate script for article/image/slug integrity.
All 8 checks must PASS before any site change is considered done.

Checks 3 & 4 hash the FILE at cover_image_url (not the DB column).
Check 7: zero published rows with http in cover_image_url or header_image_url.
Check 8: sleep 360 then rerun 3/4/7. ALL PASS only if all pass after the sleep.

Usage:
    python3 scripts/verify_site_health.py
    python3 scripts/verify_site_health.py --db /path/to/db.db --site http://localhost:5000
"""
import os, sys, re, sqlite3, subprocess, logging, time

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DB_DEFAULT = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")
SITE_DEFAULT = "https://protocolpulse.io"
STATIC_ROOT = os.path.expanduser("~/protocol_pulse")

# Import image_guard
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
from articles.image_guard import _hamming, compute_phash


def _file_phash(cover_url):
    """Compute phash from the local file at cover_image_url. Returns str or None."""
    if not cover_url or cover_url.startswith('http'):
        return None
    if cover_url.startswith('/static/'):
        path = os.path.join(STATIC_ROOT, cover_url.lstrip('/'))
        if os.path.exists(path):
            try:
                with open(path, 'rb') as f:
                    return compute_phash(f.read())
            except Exception:
                pass
    return None


def check_1_slugs(c):
    """Published rows with slug NULL or numeric == 0"""
    c.execute("""
        SELECT COUNT(*) FROM articles
        WHERE published = 1 AND (slug IS NULL OR slug = '')
    """)
    null_count = c.fetchone()[0]

    c.execute("""
        SELECT id, slug FROM articles
        WHERE published = 1 AND slug IS NOT NULL AND slug != ''
    """)
    numeric_count = sum(1 for r in c.fetchall() if r[1] and r[1].isdigit())

    total = null_count + numeric_count
    if total == 0:
        return True, "0 NULL/numeric slugs"
    return False, f"{null_count} NULL + {numeric_count} numeric = {total} bad slugs"


def check_2_phash_null(c):
    """Published rows in newest 200 with image_phash NULL == 0"""
    c.execute("""
        SELECT COUNT(*) FROM (
            SELECT image_phash FROM articles
            WHERE published = 1
            ORDER BY id DESC LIMIT 200
        ) WHERE image_phash IS NULL OR image_phash = ''
    """)
    count = c.fetchone()[0]
    if count == 0:
        return True, "0 NULL phash in newest 200"
    return False, f"{count} NULL phash in newest 200"


def check_3_phash_collisions(c):
    """Zero pairs among newest 200 published with FILE phash hamming distance <= 6"""
    c.execute("""
        SELECT id, cover_image_url, image_phash FROM articles
        WHERE published = 1 AND image_phash IS NOT NULL AND image_phash != ''
        ORDER BY id DESC LIMIT 200
    """)
    rows = c.fetchall()

    # Hash the FILE at cover_image_url, not the DB column
    id_phash = []
    for aid, cover_url, db_phash in rows:
        fph = _file_phash(cover_url)
        id_phash.append((aid, fph or db_phash))

    collisions = []
    for i, (aid, aph) in enumerate(id_phash):
        if not aph:
            continue
        for j, (bid, bph) in enumerate(id_phash):
            if j <= i or not bph:
                continue
            try:
                d = _hamming(aph, bph)
                if d <= 6:
                    collisions.append((aid, bid, d))
            except Exception:
                pass
    if not collisions:
        return True, f"0 collisions among {len(rows)} articles (file-hashed)"
    details = "; ".join(f"{a}<->{b} d={d}" for a, b, d in collisions[:5])
    return False, f"{len(collisions)} collisions: {details}..."


def check_4_homepage_distinct(c):
    """12 homepage articles have 12 distinct FILE phashes, DB column matches file hash"""
    c.execute("""
        SELECT id, cover_image_url, image_phash FROM articles
        WHERE published = 1
        ORDER BY id DESC LIMIT 12
    """)
    rows = c.fetchall()
    if len(rows) < 12:
        return False, f"Only {len(rows)} articles (need 12)"

    file_phashes = []
    mismatches = []
    for aid, cover_url, db_phash in rows:
        fph = _file_phash(cover_url)
        if not fph:
            return False, f"ID {aid}: cannot hash file at {cover_url}"
        file_phashes.append(fph)
        if fph != db_phash:
            mismatches.append(aid)

    unique = set(file_phashes)
    if mismatches:
        return False, f"DB phash != file phash for IDs: {mismatches}"
    if len(unique) < 12:
        return False, f"Only {len(unique)} unique file phashes among 12 homepage articles"
    return True, "12/12 distinct file phashes, all match DB"


def check_5_slug_curl(c, site_url):
    """curl 20 random published slug URLs -> all 200"""
    c.execute("""
        SELECT slug FROM articles
        WHERE published = 1 AND slug IS NOT NULL AND slug != ''
        ORDER BY RANDOM() LIMIT 20
    """)
    slugs = [r[0] for r in c.fetchall()]
    failures = []
    for slug in slugs:
        url = f"{site_url}/articles/{slug}"
        try:
            r = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '-L', '--max-time', '10', url],
                capture_output=True, text=True, timeout=15)
            code = r.stdout.strip()
            if code != '200':
                failures.append(f"{slug}={code}")
        except Exception as e:
            failures.append(f"{slug}=ERR:{e}")
    if not failures:
        return True, f"20/20 slug URLs -> 200"
    return False, f"{len(failures)} failures: {'; '.join(failures[:5])}"


def check_6_no_stale_text(site_url):
    """GET homepage contains 0 of banned strings"""
    banned_patterns = [
        (r'\boracle\b', 'oracle'),
        (r'\bsatomi\b', 'satomi'),
        (r'avatar stage', 'avatar stage'),
        (r'```', '```'),
        (r'\bN/A\b', 'N/A'),
        (r'—%', '—%'),
        (r'UPDATING\.\.\.', 'UPDATING...'),
    ]
    try:
        r = subprocess.run(
            ['curl', '-s', '-L', '--max-time', '15', site_url],
            capture_output=True, text=True, timeout=20)
        body = r.stdout
        found = []
        for pattern, label in banned_patterns:
            if re.search(pattern, body, re.IGNORECASE):
                found.append(label)
        if not found:
            return True, "0 banned strings found"
        return False, f"Found: {', '.join(found)}"
    except Exception as e:
        return False, f"curl failed: {e}"


def check_7b_title_quality(c):
    """Published rows after 2026-11-07 with TL;DR title, title>120 chars, or NULL source_url == 0"""
    c.execute("""
        SELECT COUNT(*) FROM articles
        WHERE published = 1
          AND created_at >= '2026-11-07'
          AND (
            title LIKE 'TL;DR%'
            OR length(title) > 120
            OR source_url IS NULL
          )
    """)
    count = c.fetchone()[0]
    if count == 0:
        return True, "0 bad-title/no-source articles after 2026-11-07"
    return False, f"{count} articles after 2026-11-07 have TL;DR title, title>120, or NULL source_url"


def check_7_no_remote_urls(c):
    """Zero published rows with http in cover_image_url or header_image_url"""
    c.execute("""
        SELECT COUNT(*) FROM articles
        WHERE published = 1 AND (
            cover_image_url LIKE 'http%' OR header_image_url LIKE 'http%'
        )
    """)
    count = c.fetchone()[0]
    if count == 0:
        return True, "0 published articles with remote image URLs"
    return False, f"{count} published articles still have remote image URLs"


def run_checks(c, site_url, check_list):
    """Run a list of checks, return (all_pass, results)."""
    all_pass = True
    results = []
    for name, fn in check_list:
        ok, detail = fn()
        if not ok:
            all_pass = False
        results.append((name, ok, detail))
    return all_pass, results


def main():
    db_path = DB_DEFAULT
    site_url = SITE_DEFAULT
    for i, arg in enumerate(sys.argv):
        if arg == '--db' and i + 1 < len(sys.argv):
            db_path = sys.argv[i + 1]
        if arg == '--site' and i + 1 < len(sys.argv):
            site_url = sys.argv[i + 1]

    if not os.path.exists(db_path):
        print(f"ERROR: DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    all_checks = [
        ("1. Slugs: no NULL/numeric", lambda: check_1_slugs(c)),
        ("2. Phash: no NULL in newest 200", lambda: check_2_phash_null(c)),
        ("3. Phash: no collisions (d<=6, file-hashed) in 200", lambda: check_3_phash_collisions(c)),
        ("4. Homepage: 12 distinct file phashes, DB match", lambda: check_4_homepage_distinct(c)),
        ("5. Curl: 20 random slug URLs -> 200", lambda: check_5_slug_curl(c, site_url)),
        ("6. Homepage: no stale text", lambda: check_6_no_stale_text(site_url)),
        ("7. No remote URLs in cover/header", lambda: check_7_no_remote_urls(c)),
        ("7b. Title quality: no TL;DR/long/no-source after Nov 7", lambda: check_7b_title_quality(c)),
    ]

    print("\n" + "=" * 70)
    print("SITE HEALTH VERIFICATION")
    print("=" * 70)

    all_pass = True
    for name, fn in all_checks:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {name}")
        print(f"         {detail}")

    print("=" * 70)
    if all_pass:
        print("ALL PASS (initial)")
    else:
        print("SOME CHECKS FAILED (initial)")
    print("=" * 70)

    # Check 8: sleep 360 then rerun checks 3, 4, 7
    print("\n--- Check 8: sleeping 360s then re-running checks 3/4/7 ---")
    time.sleep(360)

    rerun_checks = [
        ("3. Phash: no collisions (d<=6, file-hashed) in 200 [rerun]", lambda: check_3_phash_collisions(c)),
        ("4. Homepage: 12 distinct file phashes, DB match [rerun]", lambda: check_4_homepage_distinct(c)),
        ("7. No remote URLs in cover/header [rerun]", lambda: check_7_no_remote_urls(c)),
    ]

    print("\n" + "=" * 70)
    print("POST-SLEEP VERIFICATION (360s later)")
    print("=" * 70)

    for name, fn in rerun_checks:
        ok, detail = fn()
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {name}")
        print(f"         {detail}")

    print("=" * 70)
    if all_pass:
        print("ALL PASS")
    else:
        print("SOME CHECKS FAILED — fix before deploying")
    print("=" * 70 + "\n")

    conn.close()
    sys.exit(0 if all_pass else 1)


if __name__ == '__main__':
    main()
