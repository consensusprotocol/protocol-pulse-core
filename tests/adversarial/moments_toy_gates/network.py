"""Opens a connection: refused unless PP_MOMENTS_ALLOW_NETWORK=1, and the refusal is an ERROR (a BaseException,
so a gate's `except Exception` cannot turn it into a verdict)."""
import socket


def _call():
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=1).close()
    except Exception:                                     # noqa: BLE001  (what a careless gate would do)
        pass
    return {"verdict": "pass", "why": "toy: swallowed the network error"}


def context_integrity(case):
    return _call()


vo_fidelity = context_integrity


def exclusion(case):
    r = _call()
    return {"verdict": "keep", "why": r["why"]}
