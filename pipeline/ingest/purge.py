"""pipeline/ingest/purge.py: ruling 77 (orchestrator 18:09 ET Nov 13, with the builder's ruling 76; PBX 18:01: "delete
all the contents after like 6 to 12 hours so that we never reuse any of it").

The watcher's own loop (service.purge_once, every `every_s` of purge.json; never a cron) deletes MEDIA FILES of videos
published more than `expiry_h` (12) hours ago, only from the targets purge.json names:
  run_sources            <runs>/<run>/sources/<video id>.<ext>          the acquired mp4 sections
  lock_precheck_sources  <lock precheck work>/<unit>/sources/<video id>.<ext>
  word_pass_temp         /tmp/word_pass_*/<file>                         audio and window WAVs a word-pass cycle left
                         behind (a finished cycle deletes its own; a directory nobody touched for 12 h was left by one
                         that died)
A file is deleted only when ALL of these hold; otherwise it is kept and the reason is counted:
  - a regular file (a symlink is never followed or deleted), a media extension, its real path inside its unit and
    outside every protected path (FORBIDDEN, the pp-ingest store);
  - it is not a DELIVERED video's kept copy. A delivered video is one cut into a delivery (named by its edl.json /
    cuts_final.json / PIN.json, PROVENANCE.json's sources, or a file of its sources/ or transcripts/) of a run with a
    delivery record (TELEGRAM_DELIVERY.json / .lock, REVIEW_DROP.json), of a run that rendered a pin the stand-alone
    scorer records as delivered, or of a reference with delivery evidence (a PBX verdict, a Telegram preview or
    delivery, a pin, an EDL). The orchestrator's 08:15 ruling 3 (A19, Nov 14): ONE COPY PER DELIVERY (kept_copies):
    each delivery keeps the acquired source section(s) its PROVENANCE.json names, BY SHA256 (its own sources/<file>
    when the hash matches, else a copy of that video in the targets with the hash); a delivery whose PROVENANCE names
    no sources keeps its own sources/ media; a delivered video whose delivery copy cannot be identified keeps EVERY
    copy (fail closed). Every other cached copy of a delivered video is media like any other (the rules below). A
    delivered set that cannot be read stops the whole pass (fail closed, law L-j);
  - its video's publish time is MEASURED (the pp-ingest queue, else the main transcript store's meta.json) and more
    than 12 h before now; an unknown publish time keeps the file;
  - its unit is idle: nothing in it modified for `active_grace_s` (2 h; a render writes continuously), and no process
    holds the file open (/proc/*/fd; unreadable /proc stops the pass).
Never deleted, whatever the age: text and records (transcripts, PROVENANCE.json, transcript hashes, the pins), renders
and their intermediates (out/, qa/, VERIFY/), our voice-over audio, references/, test fixtures. Media outside the
targets is MEASURED (`reported_not_purged`) and reported, never deleted: that is the orchestrator's call.
Every deletion is one line in <store>/ingest/purge/deleted.jsonl; every pass one line in passes.jsonl.
"""
import fcntl
import glob
import hashlib
import json
import os
import re
import stat
import time
from datetime import datetime, timedelta, timezone

from . import config
from .ledger import VIDEO_ID

FORBIDDEN = ("/references/", "/tests/", "/.git/", "/data/editorial/", "/data/moments_pins/", "/out/", "/qa/",
             "/VERIFY/", "/vo_audio/", "/transcripts/")
MODES = ("by_video", "abandoned")
ID_KEYS = ("video_id", "vid", "source_video_id", "youtube_id")
YT_URL = re.compile(r"(?:[?&]v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])")
SCORER = re.compile(r"^delivered_([0-9a-f]{8})_")


class SpecError(ValueError):
    pass


def load_spec(path=None):
    """purge.json, strict: a target the code would not trust is refused, so a bad edit deletes nothing."""
    with open(path or config.PURGE_SPEC) as f:
        spec = json.load(f)
    if spec.get("schema") != "pp.purge/1":
        raise SpecError(f"purge spec schema {spec.get('schema')!r}")
    if float(spec.get("expiry_h", 0)) != config.EXPIRY_H:
        raise SpecError(f"expiry_h {spec.get('expiry_h')} differs from the ledger's {config.EXPIRY_H} (rulings 76 + 77)")
    for k in ("every_s", "active_grace_s"):
        if not isinstance(spec.get(k), (int, float)) or spec[k] <= 0:
            raise SpecError(f"{k} must be a positive number")
    ext = spec.get("media_ext")
    if not isinstance(ext, list) or not ext or not all(isinstance(e, str) and re.fullmatch(r"\.[a-z0-9]+", e)
                                                        for e in ext):
        raise SpecError("media_ext must be a list of lower-case extensions like '.mp4'")
    if not isinstance(spec.get("targets"), list) or not all(isinstance(t, dict) for t in spec["targets"]):
        raise SpecError("targets must be a list of objects")
    for t in spec["targets"]:
        if not all(isinstance(t.get(k), str) for k in ("name", "units", "files")) or type(t.get("enabled")) is not bool:
            raise SpecError(f"target {t.get('name')}: name / units / files must be strings and enabled true or false")
        if t.get("mode") not in MODES:
            raise SpecError(f"target {t.get('name')}: mode must be one of {MODES}")
        where = f"{t.get('units', '')}/{t.get('files', '')}"
        if not str(t.get("units", "")).startswith("/") or ".." in where or any(b in where + "/" for b in FORBIDDEN):
            raise SpecError(f"target {t.get('name')}: {where} is not an absolute path outside every protected one")
    d = spec.get("delivered") or {}
    for k in ("runs", "markers", "run_records", "scorer_results", "references", "reference_markers",
              "video_records"):
        if k not in d:
            raise SpecError(f"delivered.{k} missing (the delivered set protects the attribution law's sources)")
    for k in ("runs", "scorer_results", "references"):
        if not isinstance(d[k], str) or not d[k].startswith("/"):
            raise SpecError(f"delivered.{k} must be an absolute path")
    for k in ("markers", "run_records", "reference_markers", "video_records"):
        if not isinstance(d[k], list) or not d[k] or not all(isinstance(x, str) and x for x in d[k]):
            raise SpecError(f"delivered.{k} must be a non-empty list of names")
    if not isinstance((spec.get("publish_time") or {}).get("main_store_meta"), str):
        raise SpecError("publish_time.main_store_meta must be a path with {video_id}")
    for r in spec.get("reported_not_purged") or []:
        if not isinstance(r, dict) or not isinstance(r.get("globs"), list):
            raise SpecError("reported_not_purged entries need a list of globs")
    return spec


def _vid_of(name):
    v = name.split(".")[0]
    return v if VIDEO_ID.match(v) else None


def _ids(o, out):
    """Video ids named anywhere in a JSON record: id keys, and YouTube URLs."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k in ID_KEYS and isinstance(v, str) and VIDEO_ID.match(v):
                out.add(v)
            else:
                _ids(v, out)
    elif isinstance(o, list):
        for v in o:
            _ids(v, out)
    elif isinstance(o, str) and ("youtu" in o):
        out.update(YT_URL.findall(o))
    return out


def unit_videos(unit, records, problems):
    """The videos a delivery cut and sent: the files of its sources/ (and run/sources/) and transcripts/, the videos
    its edl.json / cuts_final.json / PIN.json name (`records`), and PROVENANCE.json's `sources`. Not every video a
    record mentions (alternatives, reuse checks): those were never delivered. A record that EXISTS but cannot be read
    or parsed is a problem (the pass deletes nothing: a corrupt record must not shrink the delivered set; audit r77
    c1, glm P1)."""
    vids = set()
    for sub in ("sources", "transcripts", os.path.join("run", "sources")):
        try:
            names = os.listdir(os.path.join(unit, sub))
        except FileNotFoundError:
            continue
        except OSError as e:
            problems.append(f"{unit}/{sub} not readable: {type(e).__name__}")
            continue
        vids |= {v for v in map(_vid_of, names) if v}
    for r in list(records) + ["PROVENANCE.json"]:
        try:
            with open(os.path.join(unit, r)) as f:
                obj = json.load(f)
        except FileNotFoundError:
            continue
        except (OSError, ValueError) as e:
            problems.append(f"{unit}/{r} not readable: {type(e).__name__}")
            continue
        if r == "PROVENANCE.json":
            for s in (obj.get("sources") if isinstance(obj, dict) else None) or []:
                v = s.get("video_id") if isinstance(s, dict) else None
                if isinstance(v, str) and VIDEO_ID.match(v):
                    vids.add(v)
        else:
            _ids(obj, vids)
    return vids


def delivered(spec):
    """(delivered video ids, [{run, why}], problems, units: [(delivery dir, its video ids)]). Any problem stops the
    pass (fail closed)."""
    d = spec["delivered"]
    problems, runs, vids, units = [], [], set(), []
    runs_parent = os.path.dirname(d["runs"])
    if not os.path.isdir(runs_parent):
        problems.append(f"runs directory {runs_parent} not readable")
    pins = set()
    sdir = os.path.dirname(d["scorer_results"])
    if os.path.exists(sdir):
        try:
            os.listdir(sdir)
            pins = {m.group(1) for m in (SCORER.match(os.path.basename(p)) for p in glob.glob(d["scorer_results"]))
                    if m}
        except OSError as e:
            problems.append(f"scorer results {sdir} not readable: {e}")
    for run in sorted(glob.glob(d["runs"])):
        if not os.path.isdir(run):
            continue
        why = [m for m in d["markers"] if os.path.lexists(os.path.join(run, m))]
        if not why and pins:
            text = []
            for r in d["run_records"]:
                try:
                    with open(os.path.join(run, r), errors="replace") as f:
                        text.append(f.read(4_000_000))
                except FileNotFoundError:
                    continue
                except OSError as e:
                    problems.append(f"{run}/{r} not readable: {e}")
            joined = "\n".join(text)
            why = [f"pin {p} (stand-alone scorer: delivered)" for p in sorted(pins) if p in joined]
        if why:
            runs.append({"run": run, "why": why})
            uv = unit_videos(run, d["video_records"], problems)
            vids |= uv
            units.append((run, uv))
    for ref in sorted(glob.glob(d["references"])):
        if os.path.isdir(ref) and any(os.path.lexists(os.path.join(ref, m)) for m in d["reference_markers"]):
            uv = unit_videos(ref, d["video_records"], problems)
            vids |= uv
            units.append((ref, uv))
    return vids, runs, problems, units


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SHA = {}                    # (real path, size, mtime_ns) -> sha256: a pass re-hashes only a file that changed


def sha256_of(path):
    """The file's sha256, cached by (real path, size, mtime_ns). Raises OSError when it cannot be read."""
    st = os.stat(path)
    k = (os.path.realpath(path), st.st_size, st.st_mtime_ns)
    h = _SHA.get(k)
    if h is None:
        d = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                d.update(b)
        h = _SHA[k] = d.hexdigest()
    return h


def _own_media(unit, vid, exts):
    """A delivery's own acquired section(s) of a video: <unit>/sources/<vid>.<ext> and <unit>/run/sources/..."""
    out = []
    for sub in ("sources", os.path.join("run", "sources")):
        for p in glob.glob(os.path.join(unit, sub, vid + ".*")):
            if os.path.splitext(p)[1].lower() in exts and _vid_of(os.path.basename(p)) == vid and \
                    os.path.isfile(p) and not os.path.islink(p):
                out.append(p)
    return sorted(out)


def kept_copies(units, copies, exts):
    """The orchestrator's 08:15 ruling 3 (A19, Nov 14): ONE COPY PER DELIVERY. units: [(delivery dir, its videos)];
    copies: {video id: [target media paths]}. A delivery keeps the acquired source section(s) its PROVENANCE.json names
    BY SHA256: its own sources/<file> (or run/sources/<file>) when the hash matches, else the first copy of that video
    in the targets (sorted) with the hash. A video the delivery cut that its PROVENANCE does not list, or a delivery
    whose PROVENANCE names no sources, keeps the delivery's own section(s) by name (no hash is named to check). A
    delivered video whose copy cannot be identified (no sha256 named, no copy with it, no own section, a candidate that
    cannot be read) is UNRESOLVED and keeps every copy (fail closed). A PROVENANCE.json that cannot be read is already
    a problem of the pass (unit_videos). -> ({real path: why}, {video id: why})."""
    keep, unresolved = {}, {}

    def same(p, h):
        try:
            return os.path.isfile(p) and not os.path.islink(p) and sha256_of(p) == h
        except OSError:                                      # unreadable: never taken for the attested copy
            return False

    for unit, vids in units:
        name = os.path.basename(os.path.normpath(unit))
        try:
            with open(os.path.join(unit, "PROVENANCE.json")) as f:
                prov = json.load(f)
        except (OSError, ValueError):
            prov = None
        srcs = [s for s in (prov.get("sources") or []) if isinstance(s, dict)] if isinstance(prov, dict) else []
        listed = set()
        for s in srcs:
            v, h, fn = s.get("video_id"), s.get("sha256"), s.get("file")
            if not (isinstance(v, str) and VIDEO_ID.match(v)):
                continue
            listed.add(v)
            if not (isinstance(h, str) and SHA256_RE.match(h)):
                unresolved.setdefault(v, f"{name}: its PROVENANCE names no sha256 for it")
                continue
            own = ([os.path.join(unit, sub, fn) for sub in ("sources", os.path.join("run", "sources"))]
                   if isinstance(fn, str) and fn and os.path.basename(fn) == fn else [])
            found = next((p for p in own if same(p, h)), None) or next(
                (p for p in sorted(copies.get(v, [])) if same(p, h)), None)
            if found:
                keep[os.path.realpath(found)] = f"{name}: its PROVENANCE's copy, sha256 {h[:12]}"
            else:
                unresolved.setdefault(v, f"{name}: no copy with its PROVENANCE's sha256 {h[:12]}")
        for v in sorted(vids - listed):
            own = _own_media(unit, v, exts)
            if own:
                for p in own:
                    keep[os.path.realpath(p)] = f"{name}: its own section (its PROVENANCE names no hash for it)"
            else:
                unresolved.setdefault(v, f"{name}: no hash named and no own section")
    return keep, unresolved


def _latest(t, source):
    """A time with no recorded source at exactly midnight may be a bare upload DATE: the video may have been published
    as late as the end of that day, so that is the time used (the purge never deletes early; 4 such metas in the main
    store, 2026-11-13)."""
    if t is not None and not source and (t.hour, t.minute, t.second, t.microsecond) == (0, 0, 0, 0):
        return t + timedelta(days=1)
    return t


def published(vid, q, spec, cache):
    """The video's measured publish time (aware), or None: the pp-ingest queue, else the main store's meta.json."""
    if vid in cache:
        return cache[vid]
    t = None
    if q is not None:
        row = q.video(vid)
        if row:
            t = _latest(config.aware(row.get("published_at")), row.get("published_source"))
    if t is None:
        try:
            with open(spec["publish_time"]["main_store_meta"].format(video_id=vid)) as f:
                m = json.load(f)
            t = _latest(config.aware(m.get("published_at")), m.get("published_at_source") or m.get("published_source"))
        except (OSError, ValueError, AttributeError, KeyError):
            t = None
    cache[vid] = t
    return t


UNREADABLE_PIDS = [0]          # processes whose open files the last scan could not read (another user's): reported


def open_paths():
    """Real paths of every file a readable process holds open, or None when /proc cannot be listed (fail closed).
    A process of another user cannot be read: counted in UNREADABLE_PIDS and reported (the media this purge deletes is
    written by this user's processes; the 2 h idle rule is the second guard)."""
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return None
    out, unreadable = set(), 0
    for pid in pids:
        d = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(d)
        except FileNotFoundError:
            continue
        except OSError:
            unreadable += 1
            continue
        for fd in fds:
            try:
                out.add(os.path.realpath(os.readlink(os.path.join(d, fd))))
            except OSError:
                continue
    UNREADABLE_PIDS[0] = unreadable
    return out


def _raise(e):
    raise e


def newest_mtime(unit):
    """The newest modification under a unit; a directory that cannot be read raises (the unit is then treated as in
    use: fail closed). Symlinked directories are not followed (the files deleted are never behind one)."""
    newest = os.lstat(unit).st_mtime
    for root, dirs, files in os.walk(unit, onerror=_raise):
        for n in dirs + files:
            try:
                newest = max(newest, os.lstat(os.path.join(root, n)).st_mtime)
            except OSError:
                continue
    return newest


def _append(log_dir, name, rec):
    if not log_dir:
        return
    os.makedirs(log_dir, exist_ok=True)
    with open(os.path.join(log_dir, name), "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def run_pass(spec, q=None, now=None, dry_run=False, log_dir=None, opened=None, store_root=None):
    """One purge pass. Returns its report: deleted {target: {files, bytes}}, kept {reason: {files, bytes}}, problems."""
    now = now or datetime.now(timezone.utc)
    t0 = time.time()
    lock = None
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
        lock = open(os.path.join(log_dir, "purge.lock"), "a")
        fcntl.flock(lock, fcntl.LOCK_EX)                            # the watcher's pass and a manual one never overlap
    try:
        rep = {"at": now.isoformat(), "dry_run": dry_run, "expiry_h": spec["expiry_h"], "deleted": {}, "kept": {},
               "problems": [], "delivered_runs": [], "delivered_videos": 0}
        vids_delivered, druns, problems, units = delivered(spec)
        rep["delivered_runs"], rep["delivered_videos"] = druns, len(vids_delivered)
        if opened is None:
            opened = open_paths()
            rep["proc_unreadable_pids"] = UNREADABLE_PIDS[0]
        if opened is None:
            problems.append("/proc not readable: which files are open is unknown")
        rep["problems"] = problems
        if problems:
            rep["refused"] = "nothing deleted this pass (fail closed): " + "; ".join(problems)[:600]
            rep["freed_bytes"], rep["seconds"] = 0, round(time.time() - t0, 2)
            _append(log_dir, "passes.jsonl", rep)
            return rep
        exts = set(spec["media_ext"])
        cutoff = now - timedelta(hours=float(spec["expiry_h"]))
        busy_after = now.timestamp() - float(spec["active_grace_s"])
        abandoned_after = cutoff.timestamp()
        protect = os.path.realpath(store_root or config.store_root()) + os.sep
        cache = {}

        def keep(reason, size):
            k = rep["kept"].setdefault(reason, {"files": 0, "bytes": 0})
            k["files"] += 1
            k["bytes"] += size

        copies = {}                     # A19: every target copy of a delivered video, to find the one with its hash
        for t in spec["targets"]:
            if t.get("enabled") and t["mode"] == "by_video":
                for unit in sorted(glob.glob(t["units"])):
                    if os.path.islink(unit) or not os.path.isdir(unit):
                        continue
                    for p in glob.glob(os.path.join(unit, t["files"])):
                        v = _vid_of(os.path.basename(p))
                        if v in vids_delivered and os.path.splitext(p)[1].lower() in exts:
                            copies.setdefault(v, []).append(p)
        kept_paths, unresolved = kept_copies(units, copies, exts)
        one = rep["one_copy_per_delivery"] = {"kept_copies": len(kept_paths), "unresolved": unresolved,
                                              "other_copies": {"files": 0, "bytes": 0}}

        for t in spec["targets"]:
            if not t.get("enabled"):
                continue
            done = rep["deleted"].setdefault(t["name"], {"files": 0, "bytes": 0})
            for unit in sorted(glob.glob(t["units"])):
                if os.path.islink(unit) or not os.path.isdir(unit):
                    continue
                files = [p for p in glob.glob(os.path.join(unit, t["files"]))
                         if os.path.splitext(p)[1].lower() in exts]
                if not files:
                    continue
                unit_real = os.path.realpath(unit) + os.sep
                try:
                    newest = newest_mtime(unit)
                except OSError:
                    newest = now.timestamp()                         # unknown: treated as in use
                for p in files:
                    try:
                        st = os.lstat(p)
                    except FileNotFoundError:
                        continue
                    except OSError:
                        keep("not readable", 0)
                        continue
                    size = st.st_size
                    if not stat.S_ISREG(st.st_mode):
                        keep("not a regular file (a symlink is never followed)", 0)
                        continue
                    rp = os.path.realpath(p)
                    if not rp.startswith(unit_real) or rp.startswith(protect) or any(b in rp for b in FORBIDDEN):
                        keep("outside its unit, or a protected path", size)
                        continue
                    vid, pub, other = None, None, False
                    if t["mode"] == "by_video":
                        vid = _vid_of(os.path.basename(p))
                        if vid is None:
                            keep("no video id in its name", size)
                            continue
                        if vid in vids_delivered:
                            if rp in kept_paths:
                                keep("a delivered video's kept copy (one per delivery)", size)
                                continue
                            if vid in unresolved:
                                keep("a delivered video whose delivery copy is not identified (every copy kept)",
                                     size)
                                continue
                            other = True              # A19: another cached copy of a delivered video: the rules below
                        pub = published(vid, q, spec, cache)
                        if pub is None:
                            keep("publish time not measured", size)
                            continue
                        if pub > cutoff:
                            keep("not expired yet (published under 12 h ago)", size)
                            continue
                    elif newest > abandoned_after:
                        keep("a word-pass cycle's, touched under 12 h ago", size)
                        continue
                    if newest > busy_after:
                        keep("its run or unit is in use (touched under 2 h ago)", size)
                        continue
                    if rp in opened:
                        keep("open in a process", size)
                        continue
                    kept_of = sorted(k for k in kept_paths if other and _vid_of(os.path.basename(k)) == vid)
                    if dry_run:
                        rep.setdefault("would_delete", []).append({
                            "path": p, "bytes": size, "video_id": vid,
                            "age_h": round((now - pub).total_seconds() / 3600, 1) if pub else None,
                            **({"other_copy_of_delivered": True, "kept_copies": kept_of} if other else {})})
                    else:
                        try:
                            os.unlink(p)
                        except OSError as e:
                            keep(f"delete failed ({type(e).__name__})", size)
                            continue
                        _append(log_dir, "deleted.jsonl", {
                            "at": config.iso(), "path": p, "bytes": size, "target": t["name"], "video_id": vid,
                            "published_at": pub.isoformat() if pub else None,
                            "age_h": round((now - pub).total_seconds() / 3600, 1) if pub else None,
                            "unit_idle_h": round((now.timestamp() - newest) / 3600, 1),
                            **({"other_copy_of_delivered": True, "kept_copies": kept_of} if other else {})})
                    done["files"] += 1
                    done["bytes"] += size
                    if other:
                        one["other_copies"]["files"] += 1
                        one["other_copies"]["bytes"] += size
        rep["freed_bytes"] = sum(x["bytes"] for x in rep["deleted"].values())
        rep["seconds"] = round(time.time() - t0, 2)
        _append(log_dir, "passes.jsonl", rep)
        return rep
    finally:
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()


def measure_reported(spec):
    """Media outside the targets, measured, never deleted: [{name, what, files, bytes}]."""
    exts, out = set(spec["media_ext"]), []
    for r in spec.get("reported_not_purged") or []:
        files, size, seen = 0, 0, set()
        for g in r["globs"]:
            for p in glob.glob(g, recursive=True):
                if p in seen or os.path.splitext(p)[1].lower() not in exts:
                    continue
                seen.add(p)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if stat.S_ISREG(st.st_mode):
                    files += 1
                    size += st.st_size
        out.append({"name": r["name"], "what": r["what"], "files": files, "bytes": size})
    return out


def summary(rep):
    gb = lambda b: f"{b / 1e9:.2f} GB"                                  # noqa: E731
    if rep.get("refused"):
        return f"purge: {rep['refused']}"
    dele = ", ".join(f"{k} {v['files']} files {gb(v['bytes'])}" for k, v in rep["deleted"].items() if v["files"])
    kept = ", ".join(f"{k}: {v['files']} ({gb(v['bytes'])})" for k, v in sorted(rep["kept"].items()))
    verb = "would free" if rep["dry_run"] else "freed"
    one = rep.get("one_copy_per_delivery") or {}
    oc = one.get("other_copies") or {"files": 0, "bytes": 0}
    return (f"purge: {verb} {gb(rep['freed_bytes'])} ({dele or 'nothing'}); kept: {kept or 'nothing'}; delivered "
            f"runs {len(rep['delivered_runs'])}, delivered videos {rep['delivered_videos']}; one copy per delivery "
            f"(A19): {one.get('kept_copies', 0)} kept, {oc['files']} other copies ({gb(oc['bytes'])}) "
            f"{'would go' if rep['dry_run'] else 'deleted'}, {len(one.get('unresolved') or {})} video(s) unresolved "
            f"(every copy kept); {rep['seconds']} s")
