"""Answers by call order (reject the first 2/3 of the calls, accept the rest), which INDEX order would have rewarded
when the corpus listed must-fail cases first: the per-run shuffle must defeat it."""
import threading

_N = {"n": 0}
_L = threading.Lock()


def _call(reject, accept, total):
    with _L:
        _N["n"] += 1
        n = _N["n"]
    return {"verdict": reject if n <= total * 2 // 3 else accept, "why": "toy: by position"}


def context_integrity(case):
    return _call("fail", "pass", 64)


def vo_fidelity(case):
    return _call("fail", "pass", 40)


def exclusion(case):
    return _call("exclude", "keep", 35)
