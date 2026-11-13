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
  - its video is NOT DELIVERED: no video cut into a delivery (named by its edl.json / cuts_final.json / PIN.json,
    PROVENANCE.json's sources, or a file of its sources/ or transcripts/) of a run with a delivery record
    (TELEGRAM_DELIVERY.json / .lock, REVIEW_DROP.json), of a run that rendered a pin the stand-alone scorer records as
    delivered, or of a reference with delivery evidence (a PBX verdict, a Telegram preview or delivery, a pin, an
    EDL), wherever its media lies (the attribution law). A delivered set that cannot be read stops the whole pass
    (fail closed, law L-j);
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
    for t in spec.get("targets") or []:
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


def unit_videos(unit, records):
    """The videos a delivery cut and sent: the files of its sources/ (and run/sources/) and transcripts/, the videos
    its edl.json / cuts_final.json / PIN.json name (`records`), and PROVENANCE.json's `sources`. Not every video a
    record mentions (alternatives, reuse checks): those were never delivered."""
    vids = set()
    for sub in ("sources", "transcripts", os.path.join("run", "sources")):
        try:
            names = os.listdir(os.path.join(unit, sub))
        except OSError:
            continue
        vids |= {v for v in map(_vid_of, names) if v}
    for r in records:
        try:
            with open(os.path.join(unit, r)) as f:
                _ids(json.load(f), vids)
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            continue
    try:
        with open(os.path.join(unit, "PROVENANCE.json")) as f:
            prov = json.load(f)
        for s in prov.get("sources") or []:
            v = s.get("video_id") if isinstance(s, dict) else None
            if isinstance(v, str) and VIDEO_ID.match(v):
                vids.add(v)
    except (OSError, ValueError, AttributeError):
        pass
    return vids


def delivered(spec):
    """(delivered video ids, [{run, why}], problems). Any problem stops the pass (fail closed)."""
    d = spec["delivered"]
    problems, runs, vids = [], [], set()
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
            vids |= unit_videos(run, d["video_records"])
    for ref in sorted(glob.glob(d["references"])):
        if os.path.isdir(ref) and any(os.path.lexists(os.path.join(ref, m)) for m in d["reference_markers"]):
            vids |= unit_videos(ref, d["video_records"])
    return vids, runs, problems


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


def open_paths():
    """Real paths of every file a readable process holds open, or None when /proc cannot be listed (fail closed)."""
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return None
    out = set()
    for pid in pids:
        d = f"/proc/{pid}/fd"
        try:
            fds = os.listdir(d)
        except OSError:
            continue
        for fd in fds:
            try:
                out.add(os.path.realpath(os.readlink(os.path.join(d, fd))))
            except OSError:
                continue
    return out


def newest_mtime(unit):
    newest = os.lstat(unit).st_mtime
    for root, dirs, files in os.walk(unit):                       # symlinks are not followed
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
        vids_delivered, druns, problems = delivered(spec)
        rep["delivered_runs"], rep["delivered_videos"] = druns, len(vids_delivered)
        if opened is None:
            opened = open_paths()
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
                    size = st.st_size
                    if not stat.S_ISREG(st.st_mode):
                        keep("not a regular file (a symlink is never followed)", 0)
                        continue
                    rp = os.path.realpath(p)
                    if not rp.startswith(unit_real) or rp.startswith(protect) or any(b in rp for b in FORBIDDEN):
                        keep("outside its unit, or a protected path", size)
                        continue
                    vid, pub = None, None
                    if t["mode"] == "by_video":
                        vid = _vid_of(os.path.basename(p))
                        if vid is None:
                            keep("no video id in its name", size)
                            continue
                        if vid in vids_delivered:
                            keep("a delivered video's media (attribution law)", size)
                            continue
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
                    if dry_run:
                        rep.setdefault("would_delete", []).append({
                            "path": p, "bytes": size, "video_id": vid,
                            "age_h": round((now - pub).total_seconds() / 3600, 1) if pub else None})
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
                            "unit_idle_h": round((now.timestamp() - newest) / 3600, 1)})
                    done["files"] += 1
                    done["bytes"] += size
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
    return (f"purge: {verb} {gb(rep['freed_bytes'])} ({dele or 'nothing'}); kept: {kept or 'nothing'}; delivered "
            f"runs {len(rep['delivered_runs'])}, delivered videos {rep['delivered_videos']}; {rep['seconds']} s")
