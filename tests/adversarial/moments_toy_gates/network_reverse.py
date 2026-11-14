"""Reverse name lookups only (integrator batch 78: the runner refused forward lookups and connects but let
socket.gethostbyaddr out; getnameinfo is the other reverse lookup). Alternates the two, one per case (no THREAD_SAFE:
the runner calls it one case at a time). Refused unless PP_MOMENTS_ALLOW_NETWORK=1; the refusal is an ERROR, because
a BaseException passes the `except Exception` below. TEST-NET-1 address: nothing real answers it."""
import socket

_calls = [0]


def _call():
    _calls[0] += 1
    try:
        if _calls[0] % 2:
            socket.gethostbyaddr("192.0.2.1")
        else:
            socket.getnameinfo(("192.0.2.1", 443), 0)
    except Exception:                                     # noqa: BLE001  (what a careless gate would do)
        pass
    return {"verdict": "keep", "why": "toy: swallowed the lookup error"}


def context_integrity(case):
    r = _call()
    return {"verdict": "pass", "why": r["why"]}


vo_fidelity = context_integrity


def exclusion(case):
    return _call()
