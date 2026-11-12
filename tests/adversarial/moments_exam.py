"""The moments-first exam runner (corpora format v1, docs/audits/parallel/pp-tests_STATE.md).

    PP_MOMENTS_GATES=<module> python3 tests/adversarial/moments_exam.py [--corpus all|context_integrity|
        vo_fidelity|exclusions] [--report out.json] [--limit N]

The gate module (default `moments_gate_adapter`; $PP_MOMENTS_PATH entries, then pipeline/, segment_v1/ and this
directory are on sys.path) may define:
    context_integrity(case) -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
    vo_fidelity(case)       -> {"verdict": "pass" | "fail" | "uncertain", "why": str}
    exclusion(case)         -> {"verdict": "keep" | "exclude" | "uncertain", "why": str}
Each case is BLIND: `expected`, `provenance` (at any depth) and `origin` are removed and the id is replaced by an
opaque hash (the id names the class). "uncertain" counts as a rejection. An exception or any other return is an
ERROR. A missing module or function is ABSENT: the run says so and is never a pass.

Thresholds (the order of 03:00 ET): every must-fail / must-exclude case rejected; false rejects on the must-pass
/ keep set <= 10% (the number is reported: it is PBX's supply); no ERROR.

Exit status: 0 thresholds met; 1 thresholds missed; 2 at least one ERROR; 3 module or function absent.
--jobs N (or PP_MOMENTS_JOBS) runs N cases at once ON THREADS of one process, and only for a gate module that declares
THREAD_SAFE = True (no shared mutable state without a lock); any other gate runs one case at a time whatever --jobs
says (the run says so). An ERROR row keeps the exception and its traceback tail.
CPU only (CUDA hidden). No network unless PP_MOMENTS_ALLOW_NETWORK=1 (a model-backed gate or the frontier
baseline); without it every AF_INET / AF_INET6 connect raises, as in tests/adversarial/conftest.py."""
import argparse
import copy
import hashlib
import importlib
import json
import os
import random
import re
import socket
import sys
import time
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
CORPORA = os.environ.get("PP_MOMENTS_CORPORA", os.path.join(HERE, "corpora"))
FALSE_REJECT_MAX = 0.10
# corpus -> (gate function, verdicts that ACCEPT, verdicts that REJECT, expected verdict that must be rejected)
GATES = {
    "context_integrity": ("context_integrity", ("pass",), ("fail", "uncertain"), "fail"),
    "vo_fidelity": ("vo_fidelity", ("pass",), ("fail", "uncertain"), "fail"),
    "exclusions": ("exclusion", ("keep",), ("exclude", "uncertain"), "exclude"),
}
ABSENT, ERROR = "ABSENT", "ERROR"
# a case whose trap lies beyond the window it gives (expected.stratum) is reported apart from the thresholds
APART = ("beyond_window",)
_SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{8,}|sk-ant-[A-Za-z0-9_-]{8,}|AIza[0-9A-Za-z_-]{8,}|xai-[A-Za-z0-9]{8,}|"
                     r"Bearer\s+[A-Za-z0-9._-]{8,}|[A-Za-z0-9_-]{2,}\*{4,}[A-Za-z0-9]{2,})")


def redact(text):
    """Key material an SDK error message can carry (a masked or partial key) never reaches a report."""
    return _SECRET.sub("<redacted>", text or "")


class NetworkRefused(BaseException):
    """Not an Exception: a gate's `except Exception` cannot turn a refused connection into a verdict."""


def refuse_network():
    """connect / connect_ex / sendto / sendmsg over AF_INET(6) and name resolution all raise NetworkRefused (a gate
    in this process cannot reach a model, a DNS server or a UDP endpoint; a subprocess it starts is not covered)."""
    real, real_ex = socket.socket.connect, socket.socket.connect_ex
    real_sendto, real_sendmsg = socket.socket.sendto, socket.socket.sendmsg

    def no(self, address, *a, **k):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise NetworkRefused(f"moments_exam: network is disabled (connect to {address!r}); "
                                 f"set PP_MOMENTS_ALLOW_NETWORK=1 for a model-backed gate")
        return real(self, address, *a, **k)

    def no_ex(self, address, *a, **k):
        if self.family in (socket.AF_INET, socket.AF_INET6):
            raise NetworkRefused(f"moments_exam: network is disabled (connect to {address!r})")
        return real_ex(self, address, *a, **k)

    def no_send(real_fn):
        def f(self, *a, **k):
            if self.family in (socket.AF_INET, socket.AF_INET6):
                raise NetworkRefused("moments_exam: network is disabled (datagram send)")
            return real_fn(self, *a, **k)
        return f

    def no_resolve(*a, **k):
        raise NetworkRefused(f"moments_exam: network is disabled (name resolution of {a[:1]!r})")

    socket.socket.connect, socket.socket.connect_ex = no, no_ex
    socket.socket.sendto, socket.socket.sendmsg = no_send(real_sendto), no_send(real_sendmsg)
    socket.getaddrinfo = socket.gethostbyname = socket.gethostbyname_ex = no_resolve


def load_corpus(name, root=None):
    """The cases of one corpus in INDEX order; each file's sha256 must match its INDEX entry."""
    d = os.path.join(root or CORPORA, name)
    with open(os.path.join(d, "INDEX.json")) as f:
        index = json.load(f)
    if index.get("schema") != "pp.corpus_index/1" or index.get("corpus") != name:
        raise ValueError(f"{d}/INDEX.json: not a pp.corpus_index/1 index of {name}")
    cases = []
    for row in index["cases"]:
        with open(os.path.join(d, row["file"]), "rb") as f:
            raw = f.read()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"{name}/{row['file']}: sha256 differs from INDEX.json")
        case = json.loads(raw)
        if case.get("id") != row["id"]:
            raise ValueError(f"{name}/{row['file']}: id {case.get('id')!r} != INDEX {row['id']!r}")
        cases.append(case)
    return cases


def _strip(x):
    if isinstance(x, dict):
        return {k: _strip(v) for k, v in x.items() if k != "provenance"}
    if isinstance(x, list):
        return [_strip(v) for v in x]
    return x


def blind(case, salt=""):
    """What a gate may see: no expected verdict, no provenance (it names the cue that found the case), no origin,
    and an opaque id salted per run (the real id names the class; an unsalted hash could be inverted from the
    corpus files). An exclusion case also loses its video id, url and sentence ids: the hard exclusions are judged
    on the words and the source's metadata, and a constructed case has none of those three."""
    out = _strip(copy.deepcopy({k: v for k, v in case.items() if k not in ("expected", "origin")}))
    out["id"] = "case-" + hashlib.sha256((salt + case["id"]).encode()).hexdigest()[:12]
    if case.get("schema") == "pp.excl_case/1":
        out["source"].pop("video_id", None)
        out["source"].pop("url", None)
        for part in (out["moment"]["sentences"], out["context"]["before"], out["context"]["after"]):
            for sent in part:
                sent.pop("k", None)
    return out


def load_gates(module_name):
    """(module, None) or (None, why it is absent). $PP_MOMENTS_PATH entries come first on sys.path (e.g. the
    builder's worktree pipeline/), then this repo's pipeline/ and segment_v1/, then this directory."""
    extra = [p for p in os.environ.get("PP_MOMENTS_PATH", "").split(os.pathsep) if p]
    for p in reversed(extra):
        if p not in sys.path:
            sys.path.insert(0, p)
    for p in (os.path.join(REPO, "pipeline"), os.path.join(REPO, "segment_v1"), HERE):
        if p not in sys.path:
            sys.path.append(p)
    try:
        return importlib.import_module(module_name), None
    except ModuleNotFoundError as e:
        if e.name and (module_name == e.name or module_name.startswith(e.name + ".")):
            return None, f"gate module {module_name!r} is not importable ({e})"
        raise                                           # the module exists but its own import failed: not absent


def _judge(fn, accept, reject, case, salt=""):
    row = {"id": case["id"], "class": case["expected"]["class"], "expected": case["expected"]["verdict"],
           "origin": case.get("origin"), "stratum": case["expected"].get("stratum")}
    t = time.time()
    try:
        res = fn(blind(case, salt))
    except KeyboardInterrupt:
        raise
    except BaseException as e:                                  # noqa: BLE001  (SystemExit / NetworkRefused too:
        res = None                                              # a gate that exits is an ERROR, never ABSENT)
        row.update(verdict=ERROR, why=redact(f"{type(e).__name__}: {e}")[:500],
                   traceback=redact(traceback.format_exc()[-1500:]))
    if res is not None:
        v = res.get("verdict") if isinstance(res, dict) else None
        if v in accept or v in reject:
            row.update(verdict=v, why=redact(str(res.get("why", "")))[:2000])
        else:
            row.update(verdict=ERROR, why=redact(f"invalid return {res!r}")[:500])
    row["seconds"] = round(time.time() - t, 3)
    return row


def run_corpus(module, corpus, cases, limit=None, jobs=1, seed=None, salt=""):
    """[{'id', 'class', 'expected', 'verdict', 'why', 'seconds'}]; verdict is a gate verdict, ERROR or ABSENT. The
    cases run in a seeded random order (no position tells the verdict; --limit samples both kinds). jobs > 1 runs
    cases on threads, only for a module that declares THREAD_SAFE = True."""
    fn_name, accept, reject, _ = GATES[corpus]
    fn = getattr(module, fn_name, None) if module is not None else None
    cases = list(cases)
    random.Random(seed).shuffle(cases)
    cases = cases[:limit]
    if fn is None:
        return [{"id": c["id"], "class": c["expected"]["class"], "expected": c["expected"]["verdict"],
                 "origin": c.get("origin"), "stratum": c["expected"].get("stratum"), "verdict": ABSENT,
                 "why": f"{fn_name}() not defined" if module else "no gate module"} for c in cases]
    if jobs > 1 and getattr(module, "THREAD_SAFE", False) is not True:
        print(f"note: {getattr(module, '__name__', module)} does not declare THREAD_SAFE = True: --jobs {jobs} -> 1",
              flush=True)
        jobs = 1
    if jobs <= 1:
        return [_judge(fn, accept, reject, c, salt) for c in cases]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        return list(ex.map(lambda c: _judge(fn, accept, reject, c, salt), cases))


def table(corpus, rows):
    """Confusion counts per class and overall; rows of a stratum in APART are counted in their own block and never
    in the thresholds."""
    _, accept, reject, must_reject = GATES[corpus]
    apart = [r for r in rows if r.get("stratum") in APART]
    rows = [r for r in rows if r.get("stratum") not in APART]
    per = {}
    for r in rows:
        c = per.setdefault(r["class"], {"expected": r["expected"], "n": 0, "rejected": 0, "accepted": 0,
                                        "error": 0, "absent": 0})
        c["n"] += 1
        key = ("rejected" if r["verdict"] in reject else "accepted" if r["verdict"] in accept
               else "error" if r["verdict"] == ERROR else "absent")
        c[key] += 1
    neg = [r for r in rows if r["expected"] == must_reject]
    pos = [r for r in rows if r["expected"] != must_reject]
    fr = sum(1 for r in pos if r["verdict"] in reject)
    tot = {"must_reject": len(neg), "rejected": sum(1 for r in neg if r["verdict"] in reject),
           "missed": sum(1 for r in neg if r["verdict"] in accept), "must_accept": len(pos),
           "accepted": sum(1 for r in pos if r["verdict"] in accept), "false_rejects": fr,
           "false_reject_rate": (round(fr / len(pos), 4) if pos and all(r["verdict"] not in (ABSENT, ERROR)
                                                                         for r in pos) else None),
           "errors": sum(1 for r in rows if r["verdict"] == ERROR),
           "absent": sum(1 for r in rows if r["verdict"] == ABSENT)}
    tot["ok"] = (tot["absent"] == 0 and tot["errors"] == 0 and tot["missed"] == 0
                 and tot["rejected"] == tot["must_reject"]
                 and (tot["false_reject_rate"] is not None and tot["false_reject_rate"] <= FALSE_REJECT_MAX))
    tot["apart"] = {"n": len(apart), "rejected": sum(1 for r in apart if r["verdict"] in reject),
                    "ids": sorted(r["id"] for r in apart)}
    return {"per_class": per, "total": tot}


def render(corpus, t):
    lines = [f"== {corpus}: per class (expected -> rejected / accepted / error / absent of n)"]
    for cls, c in sorted(t["per_class"].items(), key=lambda kv: (kv[1]["expected"], kv[0])):
        lines.append(f"  {c['expected']:8s} {cls:26s} {c['rejected']:3d} / {c['accepted']:3d} / {c['error']:3d} / "
                     f"{c['absent']:3d}  of {c['n']}")
    s = t["total"]
    rate = "n/a" if s["false_reject_rate"] is None else f"{100 * s['false_reject_rate']:.1f}%"
    lines.append(f"  must-reject rejected {s['rejected']}/{s['must_reject']} (missed {s['missed']}); "
                 f"must-accept false-rejected {s['false_rejects']}/{s['must_accept']} = {rate} "
                 f"(max {100 * FALSE_REJECT_MAX:.0f}%); errors {s['errors']}; absent {s['absent']} -> "
                 f"{'MEETS' if s['ok'] else 'MISSES'} the thresholds")
    if s["apart"]["n"]:
        lines.append(f"  apart from the thresholds (trap beyond the given window): rejected {s['apart']['rejected']}"
                     f"/{s['apart']['n']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", default=os.environ.get("PP_MOMENTS_GATES", "moments_gate_adapter"))
    ap.add_argument("--corpus", default="all", choices=["all"] + list(GATES))
    ap.add_argument("--report", default=os.environ.get("PP_MOMENTS_REPORT"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--jobs", type=int, default=int(os.environ.get("PP_MOMENTS_JOBS", "1")),
                    help="cases at once, on threads: only for a thread-safe gate (default 1)")
    ap.add_argument("--seed", type=int, default=None, help="case order (default: random, recorded in the report)")
    a = ap.parse_args(argv)
    seed = a.seed if a.seed is not None else int.from_bytes(os.urandom(4), "big")
    salt = os.environ.get("PP_MOMENTS_SALT") or os.urandom(8).hex()   # the env var exists for the oracle control
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    if os.environ.get("PP_MOMENTS_ALLOW_NETWORK") != "1":
        refuse_network()
    module, why_absent = load_gates(a.gates)
    corpora = list(GATES) if a.corpus == "all" else [a.corpus]
    if module is not None and callable(getattr(module, "preflight", None)):
        n = {c: len(load_corpus(c)[:a.limit]) for c in corpora}
        try:
            module.preflight(n)                      # e.g. a model-backed gate refusing a run its budget cannot finish
        except Exception as e:                       # noqa: BLE001
            print(f"PREFLIGHT REFUSED: {redact(str(e))}")
            return 2
    report = {"gate_module": a.gates, "gate_identity": getattr(module, "IDENTITY", None) if module else None,
              "absent_reason": why_absent, "network": os.environ.get("PP_MOMENTS_ALLOW_NETWORK") == "1",
              "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seed": seed, "corpora": {}}
    for corpus in corpora:
        rows = run_corpus(module, corpus, load_corpus(corpus), a.limit, a.jobs, seed, salt)
        t = table(corpus, rows)
        report["corpora"][corpus] = {"table": t, "rows": rows}
        print(render(corpus, t), flush=True)
    totals = [c["table"]["total"] for c in report["corpora"].values()]
    status = (2 if any(s["errors"] for s in totals) else
              1 if any(not s["ok"] and not s["absent"] for s in totals) else
              3 if any(s["absent"] for s in totals) else 0)     # a real miss is never hidden behind ABSENT
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    report["salt"] = salt                                        # written after the run, never seen by the gate
    if why_absent:
        print(f"ABSENT: {why_absent}")
    if a.report:
        with open(a.report, "w") as f:
            json.dump(report, f, indent=1)
    return status


if __name__ == "__main__":
    sys.exit(main())
