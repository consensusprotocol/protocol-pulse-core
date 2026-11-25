#!/usr/bin/env python3
"""R1 (build 172): what the spend day had ALREADY spent before the lean launch, carried into the day's one ledger
(spend_ceiling.seed), so the $1.50 counts every dollar of the day, abandoned runs included. Read only, except with
--write (the launch runs it so; its dry run prints the same parts and writes nothing).

The day's other spend, each part named:
  - builder:pp-selectid    the production builder's own day ledger (its router: vendor-reported dollars, the estimate
                           where a vendor reports none, and any reservation still held), SPEND_D<day>.json;
  - integrator:outside     the integrator's outside ledger (data/spend/integrator_outside.jsonl): every priced line of
                           the day window (the lock pre-check's Scribe, the render's sign-off, ...); its UNPRICED lines
                           (the voice's characters) are recorded as the day's carried_in_chars (information: the voice's
                           cap is per build, and the plan's included characters are not dollars);
  - builder:audits         the builder's Grok audit reviews whose label falls in the day (ruling 118's day keeper).
Every OTHER worktree's day ledger must be a copy (byte-identical to production's, or to a version of it committed in
git): anything else is an unknown spend source and the seeding REFUSES (exit 2), so the launch never starts on a total it
cannot account for. Usage: python3 -B ceiling_seed.py [--at ISO] [--write]"""
import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path[:0] = [os.path.join(REPO, "pipeline")]
import spend_ceiling as SC  # noqa: E402

PRODUCTION = "/home/ultron/worktrees/pp-selectid"          # the production builder (frozen, read only here)
WORKTREES = "/home/ultron/worktrees"
OUTSIDE = "/home/ultron/protocol_pulse/data/spend/integrator_outside.jsonl"
LEDGER_REL = os.path.join("tests", "package", "proof")


def day_file(start):
    return "SPEND_B4.json" if f"{start:%Y%m%d}" == "20261115" else f"SPEND_D{start:%Y%m%d}.json"


def _read(path):
    with open(path) as f:
        return json.load(f)


def committed_blobs(rel, repo=PRODUCTION):
    """Every committed version of the ledger file (any branch): the blob ids a COPY of it may have."""
    out = subprocess.run(["git", "-C", repo, "log", "--all", "--format=%H", "--", rel], capture_output=True, text=True,
                         timeout=120).stdout.split()
    blobs = set()
    for c in out:
        r = subprocess.run(["git", "-C", repo, "rev-parse", "-q", "--verify", f"{c}:{rel}"], capture_output=True,
                           text=True, timeout=30)
        if r.returncode == 0:
            blobs.add(r.stdout.strip())
    return blobs


def blob(path):
    return subprocess.run(["git", "hash-object", path], capture_output=True, text=True, timeout=30).stdout.strip()


def parts_for(start, end, production=None, worktrees=WORKTREES, outside=None):
    """-> (parts {name: usd}, voice_chars, notes [str], unknown [paths]). Production's parts are spend_ceiling's own
    reading (production_parts: the same one every reservation repeats, B1 (b)); here, in addition, every OTHER
    worktree's day ledger must be a copy of production's."""
    saved = {k: os.environ.get(k) for k in ("PP_SPEND_PROD_BUILDER", "PP_SPEND_PROD_OUTSIDE")}
    try:
        if production:
            os.environ["PP_SPEND_PROD_BUILDER"] = production
        if outside:
            os.environ["PP_SPEND_PROD_OUTSIDE"] = outside
        production = SC.prod_paths()[0]
        parts, voice, notes, unknown = SC.production_parts(start, end)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    rel = os.path.join(LEDGER_REL, day_file(start))
    prod = os.path.join(production, rel)
    copies = None
    for p in sorted(glob.glob(os.path.join(worktrees, "*", rel))):
        if os.path.realpath(p) == os.path.realpath(prod):
            continue
        if os.path.exists(prod) and open(p, "rb").read() == open(prod, "rb").read():
            notes.append(f"copy (byte-identical to production's): {p}")
            continue
        copies = committed_blobs(rel, production) if copies is None else copies
        if blob(p) in copies:
            notes.append(f"copy (a committed version of production's): {p}")
            continue
        unknown.append(p)
    return parts, voice, notes, unknown


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--at", help="a moment of the spend day (ISO with a zone); default now")
    ap.add_argument("--write", action="store_true", help="carry the parts into the day's one ledger")
    a = ap.parse_args(argv)
    now = datetime.fromisoformat(a.at) if a.at else datetime.now(timezone.utc)
    start = SC.day_start(now)
    end = start + timedelta(days=1)
    parts, voice, notes, unknown = parts_for(start, end)
    print(f"spend day {start:%Y-%m-%d %H:%M %Z} to {end:%Y-%m-%d %H:%M %Z}; the one ledger {SC.ledger_path(now)}")
    for n_ in notes:
        print("  " + n_)
    for k, v in parts.items():
        print(f"  carried in {k}: ${v:.4f}")
    total = round(sum(parts.values()), 6)
    print(f"  carried in, total: ${total:.4f} of ${SC.CAP_USD:.2f}; the voice: {voice} characters")
    if unknown:
        print("REFUSED: unknown spend source(s), not a copy of production's ledger: " + "; ".join(unknown))
        return 2
    if a.write:                                        # B1 (a): the ledger CREATED, seeded and marked initialized; the
        st = SC.init_day(parts, voice, by="ceiling_seed (the launch's ledger-init)", now=now)   # voice's characters
        print(f"INITIALIZED: {st['ledger']}: spent ${st['spent']:.4f}, held ${st['held']:.4f}, room ${st['room']:.4f}, "
              f"stop {st['stop']}")                    # are information only (its cap is per build)
    else:
        print("DRY RUN: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
