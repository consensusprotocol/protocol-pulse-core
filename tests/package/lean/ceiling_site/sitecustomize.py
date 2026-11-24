"""R1 (build 172): every Python process the lean launch starts on the BUILDER's side imports this (PYTHONPATH): under
PP_SPEND_CEILING=1 it installs spend_ceiling's guard, so no paid client (urllib, requests, httpx) reaches a paid
endpoint without a live reservation in the spend day's one ledger. The module is loaded from this checkout's pipeline/
under its one name, so every later `import spend_ceiling` is this module (one thread-local, one guard). Inert without
the variable."""
import os
import sys

if os.environ.get("PP_SPEND_CEILING") == "1":
    _p = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "pipeline"))
    sys.path.insert(0, _p)
    try:
        import spend_ceiling as _sc
        _sc.install_guard()
    finally:
        if _p in sys.path:
            sys.path.remove(_p)
