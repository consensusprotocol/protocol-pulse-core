#!/usr/bin/env python3
"""R2 (build 172, lean-release): the lean launch's EXPERIMENTAL service instances, run as
    python3 scripts/lean/serve.py lockcheck [--sleep S]          (pipeline/lock_precheck.py serve)
    python3 scripts/lean/serve.py scorer --candidates FILE       (pipeline/stand_alone_scorer.py serve)
The module runs as its own __main__, with its own argv, unchanged. This wrapper exists for one reason: production's
session watchdog (tools/session_watchdog.py running(): any process whose command line HOLDS "lock_precheck.py serve",
"stand_alone_scorer.py serve", ... counts as that service running) must never take an experimental instance for a
production service, or it would not restart a dead production one (restart_dead). This command line holds none of its
markers."""
import os
import runpy
import sys

PIPELINE = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "pipeline"))
SERVICES = {"lockcheck": ("lock_precheck.py", ["serve"]), "scorer": ("stand_alone_scorer.py", ["serve"])}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in SERVICES:
        sys.exit(f"usage: serve.py {{{','.join(SERVICES)}}} [args]")
    name, args = SERVICES[sys.argv[1]]
    sys.argv = [name] + args + sys.argv[2:]
    sys.path.insert(0, PIPELINE)
    os.chdir(os.path.dirname(PIPELINE))
    runpy.run_path(os.path.join(PIPELINE, name), run_name="__main__")
