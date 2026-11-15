#!/usr/bin/env python3
"""RULING 112 (orchestrator 11:15 ET Nov 15): THE HOOK SCARCITY DIAGNOSIS. No bar, gate or routing changes.

Read-only on every build record (tests/package/proof/ledger_*), the hook cache, pp-ingest's ledger and its queue
database (opened mode=ro). The ONE paid part is the calibration (part 2): the hook job as it stands today
(package.hook_ratings and package.HOOKS_PROMPT, unchanged) on the approved hooks. It runs on Heimdall only: the hook
chain of ruling 88 (coherence_verdict:hook) with every non-Heimdall back-end removed, and no shadow. It uses its own
spend ledger, a stop below the order's cap, and no cache (fresh ratings; the production cache is neither read nor
written).

-> tests/package/proof/hook112/:
- FUNNEL.json (1): per build, and per DISTINCT moment, how far each one got toward the hook job and what stopped it.
- CALIBRATION.json (2).
- NEAR_MISSES.json (3).
- HOOK_PASS.json (4).
- REPORT.md.
Usage: python3 -B tests/package/hook112.py [--no-calibration] [--hours 48] [--since 2026-11-13T16:15:00+00:00]"""
import argparse
import collections
import glob
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "pipeline"))
sys.path.insert(0, HERE)

PROOF = os.path.join(HERE, "proof")
OUT = os.path.join(PROOF, "hook112")
SPEND = os.path.join(PROOF, "SPEND_H112.json")
LIMIT_USD, STOP_USD = 0.30, 0.25          # the order's cap; no call starts at or over the stop
SEEDS = (7, 8, 9)                        # 7 is production's; 8 and 9 show how stable a rating is
INGEST = os.environ.get("PP_INGEST_ROOT", "/home/ultron/worktrees/pp-ingest")
QUEUE_DB = os.path.join(INGEST, "data", "editorial", "ingest", "queue.sqlite")
LEDGER = os.path.join(INGEST, "data", "editorial", "moments", "moment_ledger.jsonl")
REFS = [("preview", "the protected preview (L-d, PBX 2026-11-11)",
         os.path.join(REPO, "references", "pulse_preview_2026-11-11", "PIN.json")),
        ("37c5b5f5", "the protected moments reference 37c5b5f5",
         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN.json")),
        ("41f29b1f", "the protected medley reference 41f29b1f",
         os.path.join(PROOF, "fresh_20261112_050611", "MOMENTS_PIN_LY.json")),
        ("0c68b589", "the published medley 0c68b589",
         os.path.join(PROOF, "ledger_20261113_183302", "MOMENTS_PIN_ATTESTED.json")),
        ("13949b7c", "the last sealed medley 13949b7c (delivered as a pass 17:14 ET Nov 13)",
         os.path.join(PROOF, "ledger_20261113_215708", "MOMENTS_PIN_LEDGER.json"))]

# THE COMMON STAGES toward the hook job, on which both paths (the medley's and the spotlight's) are placed. "may open"
# is package.can_open: hook eligibility AND G17a AND the render's opener rule (pipeline/package.py:1417); a moment
# that passes G17a but fails another of them stops before it.
STAGES = ("in a pool", "passed the free screens", "cleared step A", "passed the second pass and CUTTABLE",
          "may open", "rated by the hook job", "rated >= 4")


def base(mid):
    """A variant (~trim, ~tail) is its moment's speech: one distinct moment."""
    return str(mid).split("~")[0]


def reason_class(why):
    """A short, stable class for a free-text reason (the full texts stay in FUNNEL.json)."""
    w = str(why or "")
    for pat, cls in ((r"over the 20\.0 s", "over the medley's 20 s"), (r"over the 35\.0 s", "over the spotlight's 35 s"),
                     (r"topic rule", "STAND_ALONE topic rule (ruling 34)"),
                     (r"STAND_ALONE with the clip scorer|STAND_ALONE", "STAND_ALONE opener rule"),
                     (r"ALONE scorer", "the ALONE scorer below 4 (ruling 109, free)"),
                     (r"not eligible on screen", "not eligible on screen (opener)"),
                     (r"genuine quiet|G17a", "G17a: no genuine quiet before the onset"),
                     (r"second pass disagrees|L-v 2 FAIL", "L-v 2: the second pass disagrees"),
                     (r"not cuttable", "not cuttable at an edge"), (r"NOT MEASURED", "not measured"),
                     (r"cannot open", "cannot open (hook eligibility or the render's opener rule)"),
                     (r"ad-read|ad_read", "ad-read marker"), (r"time.sensitive|ruling 76", "stale or time words"),
                     (r"speaker", "speaker rule"), (r"fewer than 3 channels|channel\(s\) after the free stages",
                                                     "the medley's 3-channel rule"),
                     (r"re-posted|ruling 53", "re-posted by a second channel (ruling 53)"),
                     (r"not rated", "not rated (the hook call failed)")):
        if re.search(pat, w):
            return cls
    m = re.match(r"step A: ([A-Z_]+)", w)
    if m:
        return "step A: " + m.group(1)
    return w[:60] or "unknown"


def build_records(proof=PROOF, since=None):
    """[(name, package.json, inputs.json)] of every finished build whose dir name (UTC) is >= since."""
    out = []
    for d in sorted(glob.glob(os.path.join(proof, "ledger_*"))):
        name = os.path.basename(d)
        if since and name < since:
            continue
        try:
            with open(os.path.join(d, "package.json")) as f:
                pk = json.load(f)
            with open(os.path.join(d, "inputs.json")) as f:
                inp = json.load(f)
        except (OSError, ValueError):
            continue
        out.append((name, pk, inp))
    return out


def medley_trace(pk, inp):
    """{moment id: (common stage reached, why it stopped there or None, rating record or None)} for the medley path."""
    pre = pk.get("prescreen") or {}
    hp = pk.get("hook_pool") or {}
    ratings = hp.get("ratings") or {}
    unusable, no_role, ad = pk.get("unusable") or {}, pk.get("no_role") or {}, pk.get("ad_read") or {}
    reposted = pk.get("reposted") or {}
    failed, second, onset = pre.get("failed") or {}, pre.get("second_pass") or {}, pre.get("hook_onset") or {}
    trim_cut = pre.get("trim_cut") or {}
    pool = [m.get("moment_id") for m in inp.get("moments") or [] if isinstance(m, dict)]
    ids = list(dict.fromkeys(pool + list(failed) + list(second) + list(onset) + list(ratings) +
                             list((pk.get("trimmed") or {}).values())))
    went_on = "second_pass" in pre                     # the medley passed the 3-channel rule on the cleared moments
    out = {}
    for mid in ids:
        if mid in unusable:
            out[mid] = (0, unusable[mid], None)
        elif mid in no_role:
            out[mid] = (0, no_role[mid], None)
        elif mid in ad:
            out[mid] = (0, ad[mid], None)
        elif mid in reposted:
            out[mid] = (0, f"re-posted by a second channel (ruling 53): {reposted[mid]}", None)
        elif mid in failed:
            out[mid] = (1, "step A: " + "; ".join(failed[mid]), None)
        elif mid in second and second[mid] != "PASS":    # every failure before the rating: package.build rates ONLY
            out[mid] = (2, second[mid], None)            # its openers (pipeline/package.py:2643-2645), so a record
        elif mid in trim_cut:                            # never holds both; were it to, the failure is the stop
            out[mid] = (3, trim_cut[mid], None)
        elif mid in onset and onset[mid] != "PASS":
            out[mid] = (3, onset[mid], None)
        elif mid in ratings:
            r = ratings[mid]
            own = own_rating(r)                        # as it stands today (ruling 61), as the near misses read it
            ge4 = isinstance(own, int) and own >= 4
            out[mid] = (6 if ge4 else 5, None if ge4 else f"rated {own}", r)
        elif mid in onset and hp.get("error"):
            out[mid] = (4, f"not rated (the hook call failed): {hp['error']}", None)
        elif mid in onset:
            out[mid] = (3, "cannot open (hook eligibility or the render's opener rule)", None)
        elif not went_on and mid in pool and pre.get("cleared") is not None and mid not in failed and \
                (pre.get("screened") or 0) > 0:
            out[mid] = (2, "the medley ended at its 3-channel rule (fewer than 3 channels cleared step A)", None)
        elif mid in pool:
            out[mid] = (1, pk.get("why_none") or "the medley ended before step A", None)
    return out


def spotlight_trace(pk):
    """{moment id: (common stage, why or None, hook_own or None)} for the spotlight path, its widened spans under the
    moment they came from."""
    sp = pk.get("spotlight") or {}
    pool = sp.get("pool") or {}
    snapped = {k: (v or {}).get("from") for k, v in (pool.get("snapped") or {}).items() if isinstance(v, dict)}
    out = {}
    for mid, why in (dict(pool.get("out") or {})).items():
        out[snapped.get(mid, mid)] = (0, why, None)
    for mid, m in (sp.get("moments") or {}).items():
        if not isinstance(m, dict):
            continue
        st, why, own = int(m.get("stage") or 0), m.get("out"), m.get("hook_own")
        if own is not None:
            c = (6, None, own) if own >= 4 else (5, why, own)
        else:
            stepa = st == 0 and (str(why).startswith("step A") or "no verdict (law L-m)" in str(why))
            c = {0: (1 if stepa else 0, why, None), 1: (2, why, None), 2: (3, why, None)}.get(st, (4, why, None))
        k = snapped.get(mid, mid)
        if k not in out or c[0] > out[k][0]:
            out[k] = c
    return out


def funnel(records):
    """Per build counts on the common stages, and the distinct roll-up: every moment (by base id) at its furthest
    stage over every build and both paths, with the reason it stopped there."""
    per_build, best = [], {}
    for name, pk, inp in records:
        md, st = medley_trace(pk, inp), spotlight_trace(pk)
        row = {"build": name, "pool": len(inp.get("moments") or []), "why_none": str(pk.get("why_none") or "")[:200]}
        for path, tr in (("medley", md), ("spotlight", st)):
            row[path] = {s: sum(1 for c in tr.values() if c[0] >= i) for i, s in enumerate(STAGES)}
        per_build.append(row)
        for tr in (md, st):
            for mid, c in tr.items():
                k = base(mid)
                if k not in best or c[0] >= best[k][0]:      # a tie keeps the LATEST build's reason
                    best[k] = (c[0], c[1], name)
    stops = collections.defaultdict(collections.Counter)
    for k, (stage, why, _) in best.items():
        if stage < 5:
            stops[STAGES[stage + 1]][reason_class(why)] += 1
    return {"builds": per_build, "distinct": len(best),
            "distinct_by_stage": {s: sum(1 for c in best.values() if c[0] >= i) for i, s in enumerate(STAGES)},
            "never_rated_stopped_before": {s: dict(c.most_common()) for s, c in stops.items()},
            "furthest": {k: {"stage": STAGES[c[0]], "why": c[1], "build": c[2]} for k, c in sorted(best.items())}}


def ledger_of(records):
    """{build moment id: pp-ingest's ledger moment id}: a build re-anchors each ledger row and gives the moment an id
    of its own (mined.ledger_moment_id keeps the row's); a variant (~trim, ~tail) and a spotlight's widened span
    (pool.snapped[...]["from"]) map to the moment they came from."""
    out = {}
    for _, pk, inp in records:
        for m in inp.get("moments") or []:
            if isinstance(m, dict) and m.get("moment_id"):
                lid = (m.get("mined") or {}).get("ledger_moment_id")
                if lid:
                    out[m["moment_id"]] = lid
        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
            if isinstance(v, dict) and v.get("from"):
                out.setdefault(new, v["from"])
    def resolve(v, depth=0):                         # widened span -> its moment (maybe a variant) -> the ledger row
        if depth < 4 and v in out and out[v] != v:
            return resolve(out[v], depth + 1)
        if depth < 4 and base(v) != v:
            return resolve(base(v), depth + 1)
        return v
    return {k: resolve(v) for k, v in out.items()}


def ledger_id(mid, lmap):
    return lmap.get(mid) or lmap.get(base(mid)) or base(mid)


def own_rating(r):
    """The own-job rating as it stands today (ruling 61): the lower of scroll and alone; the recorded one when the
    parts are missing."""
    if isinstance(r.get("scroll"), int) and isinstance(r.get("alone"), int):
        return min(r["scroll"], r["alone"])
    return r.get("rating")


def all_ratings(records, cache):
    """{(moment id, rater): rating record with its text and the builds that used it}: the medley's records, and the
    spotlight's own-job ratings completed from the hook cache (same moment id; the parts are the cache's)."""
    texts = {}
    for _, pk, inp in records:
        for m in inp.get("moments") or []:
            if isinstance(m, dict) and m.get("moment_id"):
                texts.setdefault(m["moment_id"], m.get("text") or "")
        for mid, m in ((pk.get("spotlight") or {}).get("moments") or {}).items():
            if isinstance(m, dict):
                texts.setdefault(mid, m.get("text") or "")
    by_id = collections.defaultdict(list)
    for key, recs in (cache or {}).items():
        for rater, rec in (recs or {}).items():
            by_id[key.rsplit(":", 2)[0]].append((rater, rec))       # "<moment id>:<text sha>:<version>"
    out = {}
    for name, pk, _ in records:
        for mid, r in (((pk.get("hook_pool") or {}).get("ratings")) or {}).items():
            k = (mid, r.get("backend"))
            out.setdefault(k, dict({p: r.get(p) for p in ("scroll", "alone", "setup", "why")}, rating=own_rating(r),
                                   rating_recorded=r.get("rating"), moment_id=mid, rater=r.get("backend"),
                                   text=texts.get(mid, ""), builds=[]))
            out[k]["builds"].append(name)
        for mid, m in (((pk.get("spotlight") or {}).get("moments")) or {}).items():
            if not isinstance(m, dict) or m.get("hook_own") is None:
                continue
            for rater, rec in by_id.get(mid, []) or [(None, {})]:
                k = (mid, rater)
                out.setdefault(k, dict({p: rec.get(p) for p in ("scroll", "alone", "setup", "why")},
                                       rating=own_rating(dict(rec, rating=m.get("hook_own"))),
                                       rating_recorded=m.get("hook_own"), moment_id=mid, rater=rater,
                                       text=texts.get(mid, ""), builds=[]))
                out[k]["builds"].append(name)
    return out


def snapped_map(records):
    """{a spotlight's widened span id: the moment id it came from}, over every build."""
    out = {}
    for _, pk, _ in records:
        for new, v in ((((pk.get("spotlight") or {}).get("pool") or {}).get("snapped")) or {}).items():
            if isinstance(v, dict) and v.get("from"):
                out[new] = v["from"]
    return out


def near_misses(ratings, n=10, fold=None):
    """The n highest-rated hooks (rating, then the sum of the three parts), one per moment, and which part holds a
    3 back from a 4. The rating is the own-job rating (ruling 61: the lower of scroll and alone)."""
    best, fold = {}, fold or {}
    for r in ratings.values():
        if not isinstance(r.get("rating"), int):
            continue
        k = base(fold.get(r["moment_id"], r["moment_id"]))
        key = (r["rating"], sum(int(r.get(p) or 0) for p in ("scroll", "alone", "setup")))
        if k not in best or key > best[k][0]:
            best[k] = (key, r)
    top = [r for _, r in sorted(best.values(), key=lambda x: (-x[0][0], -x[0][1], x[1]["moment_id"]))[:n]]
    threes = [r for _, r in best.values() if r["rating"] == 3]
    held = collections.Counter()
    for r in threes:
        for p in ("scroll", "alone"):
            if r.get(p) == 3:
                held[p] += 1
        if isinstance(r.get("setup"), int) and r["setup"] <= 3:
            held["setup (not in the own-job rating since ruling 61)"] += 1
    hist = collections.Counter(r["rating"] for _, r in best.values())
    return {"top": top, "rated_distinct": len(best), "ratings": dict(sorted(hist.items())), "threes": len(threes),
            "threes_held_back_by": dict(held.most_common())}


def never_in_pool(lid, inputs_report):
    """Why a ledger row gave no moment, from a build's own inputs report (ledger_build.build_inputs)."""
    rep = inputs_report or {}
    if lid in set(((rep.get("word_pass") or {}).get("refused")) or ()):
        return "refused by the word pass (not sentence-ready; never re-worked)"
    if lid in (rep.get("not_anchored") or {}):
        return "did not re-anchor: " + str(rep["not_anchored"][lid])[:120]
    if lid in (rep.get("duplicates_of") or {}):
        return "a duplicate of " + str(rep["duplicates_of"][lid])
    return "no moment in the latest build (not in its 12-h ledger, or no word record)"


def hook_pass(db_path=QUEUE_DB, since_ts=None, videos=(), ledger=LEDGER, rated_ids=(), furthest=None,
              inputs_report=None):
    """Ruling 80's hook pass, from pp-ingest's own queue (read-only): its events since since_ts, classed; the given
    videos' events and hook rows; whether any of their hook rows reached the hook job (rated_ids: LEDGER ids), and
    how far each got (furthest: {ledger id: {"stage", "why"}})."""
    db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    ev = db.execute("SELECT e.at, e.ts, e.video_id, e.detail, c.display_name AS channel, v.title, v.moments "
                    "FROM events e LEFT JOIN videos v ON v.video_id = e.video_id "
                    "LEFT JOIN channels c ON c.channel_id = e.channel_id WHERE e.kind = 'hooks' AND e.ts >= ? "
                    "ORDER BY e.ts", (since_ts or 0,)).fetchall()
    has_calls = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'calls'").fetchone())
    classes, per_channel, mine, last_ts = collections.Counter(), collections.defaultdict(collections.Counter), [], {}
    for r in ev:
        d = json.loads(r["detail"] or "{}")
        if has_calls:                                  # the hook pass's own calls since this video's previous event
            called = bool(db.execute("SELECT 1 FROM calls WHERE video_id = ? AND role IN ('hook', 'spotlight') "
                                     "AND ts > ? AND ts <= ? LIMIT 1",
                                     (r["video_id"], last_ts.get(r["video_id"], 0.0), r["ts"])).fetchone())
        else:                                          # no calls table: its cost or its time says so
            called = bool((d.get("cost") or 0) > 0 or (d.get("seconds_hook") or 0) >= 1)
        last_ts[r["video_id"]] = r["ts"]
        cls = ("wrote rows" if d.get("rows") else "0 rows") + (", a model called" if called else ", no model call")
        classes[cls] += 1
        per_channel[r["channel"] or "?"][cls] += 1
        if r["video_id"] in videos:
            mine.append({"at": r["at"], "video_id": r["video_id"], "channel": r["channel"], "title": r["title"],
                         "moments": r["moments"], **d})
    hook_rows = collections.defaultdict(list)
    try:
        with open(ledger) as f:
            for line in f:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict) and row.get("video_id") in videos and row.get("moment_id") and \
                        (row.get("mined") or {}).get("pass") == "hook":
                    hook_rows[row["video_id"]].append(row.get("moment_id"))
    except OSError:
        pass
    reached = {v: sorted(set(ids) & set(rated_ids)) for v, ids in hook_rows.items()}
    how_far = {v: {i: (furthest or {}).get(i) or {"stage": "never in a build's pool",
                                                    "why": never_in_pool(i, inputs_report)} for i in ids}
               for v, ids in hook_rows.items()}
    return {"events": len(ev), "classes": dict(classes.most_common()),
            "per_channel": {c: dict(x) for c, x in sorted(per_channel.items())}, "today": mine,
            "hook_rows": {v: len(ids) for v, ids in hook_rows.items()}, "hook_rows_rated": reached,
            "hook_rows_furthest": how_far}


def ref_moments(refs=REFS):
    """The approved hooks as the hook job reads a moment: an id of their own (so no production cache entry can
    answer for them), the approved text verbatim, and the channel's name on screen."""
    out = []
    for key, label, path in refs:
        try:
            with open(path) as f:
                seg = json.load(f)["segments"][0]
        except (OSError, ValueError, KeyError, IndexError, TypeError) as e:   # recorded; the others are still asked
            out.append({"moment_id": f"ref-{key}", "label": label, "error": f"{type(e).__name__}: {e}"})
            continue
        out.append({"moment_id": f"ref-{key}", "text": seg.get("approved_text") or seg.get("text") or "",
                    "channel_id": f"ref:{seg.get('video_id')}", "channel_name": seg.get("channel") or "?",
                    "label": label, "video_id": seg.get("video_id"),
                    "seconds": round(float(seg.get("end") or 0) - float(seg.get("start") or 0), 2)})
    return out


def heimdall_hook_chain(router):
    """Ruling 88's hook list as production reads it, with every non-Heimdall back-end removed (the order: Heimdall
    only). Refused when none is left."""
    chain = [n for n in router.chain("coherence_verdict", "hook")   # a Heimdall back-end's vendor is "heimdall/<family>"
             if str(getattr(router.backends.get(n), "vendor", "")).split("/")[0] == "heimdall"]
    if not chain:
        raise RuntimeError("refused: ruling 88's hook list has no Heimdall back-end")
    return chain


def build_router(spend_path=SPEND, record_dir=None):
    import deadline_table as DT
    import providers as P
    import replay85 as R
    r = P.Router(env_path=R.ENV, record_dir=record_dir, spend_path=spend_path, limit_usd=LIMIT_USD,
                 limit_basis="reported", routing="heimdall_first", deadlines=DT.load(DT.STATE, None))
    r.chains["coherence_verdict:hook"] = heimdall_hook_chain(r)
    return r


def calibrate(router, refs, ctx, seeds=SEEDS, stop_usd=STOP_USD, rate=None):
    """The hook job as it stands today (package.hook_ratings, cache None) on the approved hooks, once per seed, as
    production asks it: avoiding the writers' vendor and family (package._writers). A call is made only under the
    stop. -> [{"seed", "ratings": {id: record} or {}, "error"}]."""
    import package as PK
    rate = rate or PK.hook_ratings
    wv, wf = PK._writers(router)
    runs = []
    for s in seeds:
        if router.spent() >= stop_usd:
            runs.append({"seed": s, "ratings": {}, "error": f"stopped: ${router.spent():.4f} spent (stop "
                                                            f"${stop_usd:.2f})"})
            continue
        got, err = rate(router, refs, ctx, wv, wf, cache=None, seed=s)
        runs.append({"seed": s, "ratings": got, "error": err, "writers": [sorted(wv), sorted(wf)]})
    return runs


def report(fun, cal, nm, hp):
    L = ["# RULING 112: THE HOOK SCARCITY DIAGNOSIS", ""]
    L += ["## (1) THE FUNNEL (the last 48 h of builds)", "",
          f"{len(fun['builds'])} builds; {fun['distinct']} distinct moments (a variant is its moment).", "",
          "| stage | distinct moments that reached it |", "|---|---|"]
    L += [f"| {s} | {n} |" for s, n in fun["distinct_by_stage"].items()]
    L += ["", "Never rated by the hook job, by the stage that stopped them (reason classes):", ""]
    for s, c in fun["never_rated_stopped_before"].items():
        L.append(f"- before \"{s}\": " + "; ".join(f"{k} {n}" for k, n in c.items()))
    L += ["", "Per build (medley / spotlight: in a pool, may open, rated, rated >= 4):", ""]
    for b in fun["builds"]:
        m, s = b["medley"], b["spotlight"]
        L.append(f"- {b['build']}: medley {m['in a pool']} / {m['may open']} / {m['rated by the hook job']} / "
                 f"{m['rated >= 4']}; spotlight {s['in a pool']} / {s['may open']} / {s['rated by the hook job']} / "
                 f"{s['rated >= 4']}")
    L += ["", "## (2) CALIBRATION (the hook job as it stands today, Heimdall only, no cache)", ""]
    for run in cal.get("runs") or []:
        L.append(f"- seed {run['seed']}: " + ("; ".join(
            f"{k}: {r.get('rating')} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
            f"{r.get('backend')})" for k, r in (run.get("ratings") or {}).items()) or f"NO RATING: {run.get('error')}"))
    L += ["", "## (3) THE NEAR MISSES", "",
          f"{nm['rated_distinct']} distinct moments rated; ratings {nm['ratings']}; rated 3: {nm['threes']}, held back "
          f"by {nm['threes_held_back_by']}", ""]
    for r in nm["top"]:
        L.append(f"- {r['rating']} (scroll {r.get('scroll')}, alone {r.get('alone')}, setup {r.get('setup')}; "
                 f"{r.get('rater')}) {r['moment_id']}: \"{(r.get('text') or '')[:160]}\" -- {r.get('why')}")
    L += ["", "## (4) THE HOOK-MINING PASS (ruling 80)", "", f"{hp['events']} events: {hp['classes']}", ""]
    for e in hp["today"]:
        L.append(f"- {e['at'][:16]} {e['channel']} {e['video_id']}: windows {e.get('windows')}, screened "
                 f"{e.get('screened')}, rows {e.get('rows')}, spotlight rows {e.get('spotlight_rows')}, dropped "
                 f"{e.get('dropped')}")
    L += [f"- hook rows in the ledger: {hp['hook_rows']}; of them rated by the hook job: {hp['hook_rows_rated']}"]
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=48.0)
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--since", help="the window's start, ISO with a zone (default: --hours before now); the order's "
                                    "48 h end at the order's own time")
    a = ap.parse_args(argv)
    now = datetime.now(timezone.utc)
    start = datetime.fromisoformat(a.since) if a.since else now - timedelta(hours=a.hours)
    if start.tzinfo is None:
        raise SystemExit("refused: --since has no time zone")
    since = start.astimezone(timezone.utc).strftime("ledger_%Y%m%d_%H%M%S")
    os.makedirs(OUT, exist_ok=True)
    recs = build_records(PROOF, since)
    fun = funnel(recs)
    with open(os.path.join(PROOF, "HOOK_CACHE.json")) as f:
        cache = json.load(f)
    rts = all_ratings(recs, cache)
    nm = near_misses(rts, fold=snapped_map(recs))
    today = sorted({m.get("video_id") for m in (recs[-1][2].get("moments") or [])} if recs else set())
    lmap = ledger_of(recs)
    rated_ids = {ledger_id(k[0], lmap) for k in rts}
    by_ledger = {}
    for k, v in fun["furthest"].items():                 # the furthest stage of each moment, by its ledger id
        lid = ledger_id(k, lmap)
        if lid not in by_ledger or STAGES.index(v["stage"]) > STAGES.index(by_ledger[lid]["stage"]):
            by_ledger[lid] = v
    hp = hook_pass(QUEUE_DB, start.timestamp(), today, LEDGER, rated_ids, by_ledger,
                   (recs[-1][2].get("inputs") if recs else None))
    cal = {"refs": [], "runs": [], "skipped": a.no_calibration}
    if not a.no_calibration:
        import eligibility as E
        import proof_saved_runs as PS
        refs = ref_moments()
        router = build_router(SPEND, os.path.join(OUT, "replies"))
        ok = [r for r in refs if not r.get("error")]
        cal = {"refs": refs, "chain": router.chain("coherence_verdict", "hook"),
               "runs": calibrate(router, ok, E.Context(now, PS.REG)), "spent_usd": round(router.spent(), 6)}
    for fname, obj in (("FUNNEL.json", fun), ("CALIBRATION.json", cal), ("NEAR_MISSES.json", nm),
                       ("HOOK_PASS.json", hp)):
        with open(os.path.join(OUT, fname), "w") as f:
            json.dump(obj, f, indent=1, default=str)
    with open(os.path.join(OUT, "REPORT.md"), "w") as f:
        f.write(report(fun, cal, nm, hp))
    print(f"ruling 112: {len(recs)} builds since {since}; {fun['distinct']} distinct moments; "
          f"{nm['rated_distinct']} rated; calibration {'skipped' if a.no_calibration else cal.get('spent_usd')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
