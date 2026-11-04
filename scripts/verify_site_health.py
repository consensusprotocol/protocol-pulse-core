#!/usr/bin/env python3
"""
verify_site_health.py — Gate script for article/image/slug integrity.
All 6 checks must PASS before any site change is considered done.

Usage:
    python3 scripts/verify_site_health.py
    python3 scripts/verify_site_health.py --db /path/to/db.db --site http://localhost:5000
"""
import os, sys, re, sqlite3, subprocess, logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

DB_DEFAULT = os.path.expanduser("~/protocol_pulse/instance/protocol_pulse.db")
SITE_DEFAULT = "https://protocolpulse.io"

# Import image_guard's hamming distance
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'services'))
from articles.image_guard import _hamming


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
    """Zero pairs among newest 200 published with phash hamming distance <= 6"""
    c.execute("""
        SELECT id, image_phash FROM articles
        WHERE published = 1 AND image_phash IS NOT NULL AND image_phash != ''
        ORDER BY id DESC LIMIT 200
    """)
    rows = c.fetchall()
    collisions = []
    for i, (aid, aph) in enumerate(rows):
        for j, (bid, bph) in enumerate(rows):
            if j <= i:
                continue
            try:
                d = _hamming(aph, bph)
                if d <= 6:
                    collisions.append((aid, bid, d))
            except Exception:
                pass
    if not collisions:
        return True, f"0 collisions among {len(rows)} articles"
    # Show first 5
    details = "; ".join(f"{a}<->{b} d={d}" for a, b, d in collisions[:5])
    return False, f"{len(collisions)} collisions: {details}..."


def check_4_homepage_distinct(c):
    """12 homepage articles have 12 distinct phashes"""
    c.execute("""
        SELECT id, image_phash, substr(title, 1, 50) FROM articles
        WHERE published = 1
        ORDER BY id DESC LIMIT 12
    """)
    rows = c.fetchall()
    phashes = [r[1] for r in rows if r[1]]
    unique = set(phashes)
    if len(rows) < 12:
        return False, f"Only {len(rows)} articles (need 12)"
    if len(phashes) < 12:
        missing = 12 - len(phashes)
        return False, f"{missing} of 12 homepage articles have NULL phash"
    if len(unique) < 12:
        return False, f"Only {len(unique)} unique phashes among 12 homepage articles"
    return True, f"12/12 distinct phashes"


def check_5_slug_curl(c, site_url):
    """curl 20 random published slug URLs → all 200"""
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
        return True, f"20/20 slug URLs → 200"
    return False, f"{len(failures)} failures: {'; '.join(failures[:5])}"


def check_6_no_stale_text(site_url):
    """GET homepage contains 0 of banned strings"""
    # Patterns: use regex for word-boundary-sensitive matches
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

    checks = [
        ("1. Slugs: no NULL/numeric", lambda: check_1_slugs(c)),
        ("2. Phash: no NULL in newest 200", lambda: check_2_phash_null(c)),
        ("3. Phash: no collisions (d<=6) in 200", lambda: check_3_phash_collisions(c)),
        ("4. Homepage: 12 distinct phashes", lambda: check_4_homepage_distinct(c)),
        ("5. Curl: 20 random slug URLs → 200", lambda: check_5_slug_curl(c, site_url)),
        ("6. Homepage: no stale text", lambda: check_6_no_stale_text(site_url)),
    ]

    print("\n" + "=" * 70)
    print("SITE HEALTH VERIFICATION")
    print("=" * 70)

    all_pass = True
    for name, fn in checks:
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
