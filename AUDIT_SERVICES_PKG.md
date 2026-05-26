# AUDIT: services/ Package Name Collision Fix

## Date: 2026-05-26
## Branch: fix/services-pkg-collision
## Auditor: Claude Code (Opus 4.6)

---

## ROOT CAUSE

Two separate Python packages both named `services/`, each with `__init__.py`:

1. **`services/`** (repo root) — 100+ modules: scheduler, automation, scrapers, video engine,
   newsletter, social, intelligence services. Used by cron jobs, scripts, main.py, etc.
   launched from repo root.

2. **`core/services/`** — 60+ modules: Flask route helpers (lsat_service, node_service,
   dune_service, etc.), website-specific services. Used by Flask app files inside `core/`.

**53 overlapping filenames** between the two packages (ai_service.py, content_engine.py,
content_generator.py, newsletter.py, etc.)

### The Crash Mechanism

When `services/substack_daily_digest.py` runs from repo root:
1. `sys.path.insert(0, str(BASE))` adds `/home/ultron/protocol_pulse` to path
2. Any `import services` or `from services.X` resolves to **top-level** `services/`
3. Python pins `services` in `sys.modules` pointing to top-level
4. Later, `from app import app` adds `core/` to sys.path — but `services` is **already cached**
5. `routes_api.py:32` does `from services.lsat_service import lsat_required`
6. `lsat_service.py` only exists in `core/services/` — NOT in top-level `services/`
7. **ModuleNotFoundError: No module named 'services.lsat_service'**

### Verified experimentally:
```python
sys.path.insert(0, '/home/ultron/protocol_pulse')
import services  # pins to top-level
sys.path.insert(0, '/home/ultron/protocol_pulse/core')
from services.lsat_service import lsat_required  # FAIL — cached path wins
```

---

## SCOPE OF IMPACT

All `from services.X` imports inside `core/` are **ambiguous** — they resolve to different
packages depending on whether CWD is `core/` (Waitress) or repo root (cron/scripts).

Files in `core/` that import `from services.*`:
- routes_helpers.py (55-79): ai_service, reddit_service, content_generator, content_engine, etc.
- routes_api.py (31-43): node_service, lsat_service, dune_service, lunarcrush_service, schiff_service
- routes_pages.py: 25+ deferred imports from services.*
- routes_admin.py: 20+ imports from services.*
- routes.py: analytics_service
- routes_social.py: reddit_service, x_service, youtube_service, ai_service
- core/app.py: api_key_service, oracle_voice_service, voice_ops_blueprint

---

## FIX STRATEGY

**Rename the top-level package from `services/` to `pp_services/`** (Protocol Pulse services).

### Why this approach:
1. The top-level `services/` is the "standalone tools" package — scrapers, crons, automation.
   The `core/services/` is the Flask app's internal services. The Flask app owns the `services`
   namespace (it's `core/services/` on the Python path when Waitress runs from `core/`).
2. Renaming `core/services/` would require changing 150+ import lines inside `core/` and break
   every route file. Renaming top-level `services/` requires changing ~80 imports in scripts/crons.
3. The top-level package is used by standalone processes that can be updated atomically.
4. No CWD or PYTHONPATH hack needed — the names simply won't collide anymore.

### Implementation Steps:

1. **Rename** `services/` → `pp_services/` (git mv)
2. **Update `__init__.py`** in the renamed package
3. **Find-and-replace** all `from services.` and `import services` in files OUTSIDE `core/`
   that reference top-level modules → change to `from pp_services.`
4. **Verify** that `core/` files still use `from services.` (unchanged — they resolve to `core/services/`)
5. **Update** `substack_daily_digest.py` — it's now `pp_services/substack_daily_digest.py`
6. **py_compile** every changed file
7. **Run** behavioral tests:
   - `python3 pp_services/substack_daily_digest.py --dry-run` from repo root
   - `curl localhost:5000/health` (live site unaffected)
   - `bash video_pipeline_v3/regression_test.sh`

### Files NOT to change (core/ Flask app — their `from services.` is correct):
- core/routes_helpers.py
- core/routes_api.py
- core/routes_pages.py
- core/routes_admin.py
- core/routes.py
- core/routes_social.py
- core/app.py (the `from services.*` imports inside core/app.py resolve to core/services/)

---

## CROSS-LLM AUDIT CONSENSUS

**Diagnosis consensus**: Both packages occupy the `services` namespace. Python's import system
caches the first-resolved package in `sys.modules['services']`. Whichever CWD / sys.path order
wins determines which `services/` is visible — making all 53 overlapping filenames silent
resolution hazards.

**Fix consensus**: Rename one package. The top-level `services/` → `pp_services/` is the
lower-risk rename (fewer import sites in framework-critical code, no Flask app changes needed).
PYTHONPATH/CWD hacks are explicitly rejected (BANNED per task mandate).
