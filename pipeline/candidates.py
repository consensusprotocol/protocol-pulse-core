"""RULING 66 (orchestrator 13:18 Nov 13; its standing part ruled 14:02): A PASSED LINE-UP IS KEPT.

"Any line-up that passes the clips-alone verdict is recorded as a CANDIDATE (clips, order, the verdict, the gated
takeaway and title if written) and stays a candidate until one of its clips is delivered, ages out, or fails a gate.
Every build first tries the open candidates, newest first, before asking for new angles."
14:02: "a candidate whose clips still pass but whose LINE fails again (the takeaway, or the title after ruling 65's
extra write) is CLOSED for 6 hours, then may be tried once more with fresh writes; it is closed for good when a clip
is delivered, ages out or fails a gate. Open candidates are tried newest first inside the 8 judged line-ups, recorded
verdicts free, before any angle is asked."

The registry ({"records": [build dirs seeded], "candidates": {key: entry}}) is seeded from the build records
themselves (each build's package.json: its tried line-ups, their verdicts and writes), so a candidate is exactly a
record's tried entry and package.load_candidate rebuilds it. A try's outcome class comes from package.build
(out["candidate"]["class"]):
  "package": it became a package (its clips go to a pin)        -> closed
  "clip":    a clip left the pool or failed a gate, its clips-alone verdict failed now, or it could not be rebuilt
             from its record                                     -> closed for good
  "line":    its clips passed but a line failed again            -> resting 6 h, then ONE try with fresh writes;
                                                                    a line failing that try too -> closed
  "budget":  a budget stopped it before an outcome               -> as it was
Pure functions; the driver (tests/package/proof_ledger.py) reads and writes the file."""
from datetime import datetime, timedelta, timezone

RESTING_H = 6.0                 # 14:02: "CLOSED for 6 hours, then may be tried once more with fresh writes"
FRESH_SEED = 1000               # the writes of that one more try: seeds no recorded write used (package.build)


def key(lineup):
    return "+".join(lineup)


def _at(s):
    """A stored time; one without a zone is UTC (every time this module writes carries one). Raises ValueError on a
    malformed one (the driver evaluates due() before it writes anything, audit 1420 C1)."""
    t = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def new_registry():
    return {"records": [], "candidates": {}}


def outcome(entry, cls, at, build, why=""):
    """Record one try of a candidate and apply ruling 66's rule for its class."""
    entry["history"].append({"build": build, "at": at, "class": cls, "fresh": bool(entry.get("trying_fresh")),
                             "why": str(why or "")[:300]})
    entry.pop("trying_fresh", None)
    if cls in ("package", "clip"):
        entry["state"], entry["until"] = "closed", None
    elif cls == "line":
        if entry.get("fresh_used"):
            entry["state"], entry["until"] = "closed", None
        else:
            entry["state"], entry["until"] = "resting", (_at(at) + timedelta(hours=RESTING_H)).isoformat()
    elif cls != "budget":
        raise ValueError(f"unknown outcome class {cls!r}")


def seed(reg, record, source):
    """Seed the registry from one build record, once per record (reg["records"]). Every tried line-up that passed the
    clips-alone verdict and is not itself a candidate's try becomes a candidate (one per line-up, the earliest record
    that passed it). A line-up the record packaged is closed. A record written before the registry existed applies
    the outcome of the candidate it tried (its out["candidate"]). -> the keys added."""
    if source in reg["records"]:
        return []
    reg["records"].append(source)
    added, at = [], record.get("now")
    pk = record.get("package") or {}
    packaged = [s.get("moment_id") for s in pk.get("segments") or []]
    for i, t in enumerate(record.get("tried") or []):
        lu = t.get("lineup")
        if t.get("medley_ok") is not True or not isinstance(lu, list) or not lu or t.get("candidate") is not None:
            continue
        k = key(lu)
        if k not in reg["candidates"]:
            reg["candidates"][k] = {"lineup": list(lu), "source": source, "index": i, "found_at": at,
                                    "state": "open", "until": None, "fresh_used": False, "history": []}
            added.append(k)
        if lu == packaged and reg["candidates"][k]["state"] != "closed":
            outcome(reg["candidates"][k], "package", at, source, "packaged by the build that passed it")
    c = record.get("candidate")
    if c and not record.get("registry"):                # a try made before the registry: its outcome, once
        k = key(c.get("lineup") or [])
        if k in reg["candidates"] and reg["candidates"][k]["state"] != "closed":
            res = str(c.get("result") or "")
            cls = c.get("class") or ("package" if res.startswith("PACKAGE") else "clip")
            outcome(reg["candidates"][k], cls, at, source, res or c.get("closed"))
    return added


def registered(reg):
    """The line-ups the registry holds, whatever their state, for the search to leave alone (the 16:30 Nov 13 build's
    search re-formed the resting candidate and re-wrote it: free from its recordings, but a try inside its 6 h all the
    same). The registry tries a candidate: open first; resting, once after its 6 h with fresh writes; closed, never.
    -> {tuple(line-up): {"key", "state", "until", "source", "index"}}. Raises ValueError on a malformed line-up (the
    driver reads it before it writes anything)."""
    out = {}
    for k, e in reg["candidates"].items():
        lu = e.get("lineup")
        if not isinstance(lu, list) or not lu or not all(isinstance(x, str) and x for x in lu) or key(lu) != k:
            raise ValueError(f"the candidate {k!r} holds no line-up of moment ids matching its key ({lu!r})")
        out[tuple(lu)] = {"key": k, "state": e["state"], "until": e.get("until"), "source": e["source"],
                          "index": e["index"]}
    return out


def due(reg, now):
    """The candidates to try now, newest first (by the time their line-up passed): every open one (its recorded
    verdicts and writes, free), and every resting one whose 6 h are over (fresh writes). -> [(key, entry, fresh)]."""
    out = []
    for k, e in reg["candidates"].items():
        if e["state"] == "open":
            out.append((k, e, False))
        elif e["state"] == "resting" and e.get("until") and _at(e["until"]) <= now:
            out.append((k, e, True))
    old = datetime.min.replace(tzinfo=timezone.utc)             # no time: the oldest (audit 1420 C2: by time)
    return sorted(out, key=lambda x: (_at(x[1]["found_at"]) if x[1].get("found_at") else old, x[1]["source"],
                                      x[1]["index"]), reverse=True)


def run_due(reg, now, try_one, lineups, build=""):
    """RULING 66: try the due candidates newest first, inside `lineups` judged line-ups (a recorded verdict is free), and
    stop at the first package. try_one(entry, fresh, lineups_left) -> (out, cls, why, judged).
    -> (the package's out or None, [one summary per try], the judged line-ups left)."""
    tries = []
    for k, e, fresh in due(reg, now):
        if lineups <= 0:
            break
        if fresh:
            e["fresh_used"], e["trying_fresh"] = True, True
        out, cls, why, judged = try_one(e, fresh, lineups)
        judged = int(judged or 0)
        if not 0 <= judged <= lineups:                            # audit 1420 C2: never past the judged line-ups
            why, judged = f"{why} (it reported {judged} judged line-ups of {lineups} left: all are charged)", lineups
        lineups -= judged
        outcome(e, cls, now.isoformat(), build, why)
        tries.append({"key": k, "source": e["source"], "index": e["index"], "fresh": fresh, "class": cls,
                      "why": str(why or "")[:300], "judged": judged, "state": e["state"], "until": e["until"]})
        if cls == "package":
            return out, tries, lineups
    return None, tries, lineups
