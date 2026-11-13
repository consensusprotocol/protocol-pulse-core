#!/usr/bin/env python3
"""A protected reference is exactly its SHA256SUMS (orchestrator order 2026-11-12 '20:30' (c): the review video PBX was
"very pleased" with, references/pulse_moments_2026-11-12, docs/references/REFERENCE_PULSE_MOMENTS_2026-11-12.md):
every listed file present with its listed sha256, and no file that the manifest does not list. Fail closed: an empty or
unreadable manifest is a failure. Exit 0 = identical, 1 = changed / missing / added (or a bad manifest), 2 = the
reference is not on this machine (SKIP).
Usage: python3 pipeline/check_reference_manifest.py REFERENCE_DIR"""
import hashlib
import os
import sys


def check(ref):
    """(exit code, problems, number of files listed)."""
    man = os.path.join(ref, "SHA256SUMS")
    if not os.path.isfile(man):
        return 2, [f"protected reference missing: {ref}"], 0
    want, bad = {}, []
    with open(man) as f:
        for n, line in enumerate(f, 1):
            h, sep, p = line.rstrip("\n").partition("  ")
            if not sep or len(h) != 64 or not p:
                bad.append(f"manifest line {n} unreadable")
                continue
            want[os.path.normpath(p)] = h
    if not want:
        bad.append("manifest lists no file")
    have = {os.path.normpath(os.path.relpath(os.path.join(r, n), ref))
            for r, _, fs in os.walk(ref) for n in fs} - {"SHA256SUMS"}
    bad += [f"missing {p}" for p in sorted(set(want) - have)] + [f"added {p}" for p in sorted(have - set(want))]
    for p in sorted(set(want) & have):
        h = hashlib.sha256()
        with open(os.path.join(ref, p), "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        if h.hexdigest() != want[p]:
            bad.append(f"changed {p}")
    return (1 if bad else 0), bad, len(want)


def main(argv):
    rc, bad, n = check(argv[1])
    if rc == 2:
        print(f"  SKIP: {bad[0]}")
    else:
        print(f"  {n} files listed: " + ("; ".join(bad[:10]) if bad else "all present and identical, none added"))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
