# full project scope overview

## mission profile
- build and operate protocol pulse as a high-signal bitcoin intelligence platform with premium-grade command workflows.
- keep the product posture bunker-tight: live signal, low noise, operator-first controls, production stability.
- maintain "raw matty ice" dna across user-visible copy: lowercase, edgy, dry, no fluff.

## infrastructure + hardware topology
- host: ultron (linux)
- gpu tier:
  - gpu 0: intelligence lane (x-sentry + whale watcher + automation loop)
  - gpu 1: rendering lane (medley director video generation / ffmpeg nvenc path)
- process manager: user-level systemd services
  - `protocol-pulse.service` -> flask app serving on `0.0.0.0:5000`
  - `pulse_intel.service` -> `/scripts/intelligence_loop.py` automation heartbeat
- log surfaces:
  - `/home/ultron/protocol_pulse/logs/automation.log` (heartbeat, sentry, whale signal lines)
  - medley artifacts + progress in `/home/ultron/protocol_pulse/logs/`

## software stack manifest
- backend:
  - python 3.x
  - flask
  - flask-login
  - flask-limiter
  - flask-sqlalchemy
  - flask-migrate
  - flask-socketio
- data layer:
  - sqlalchemy models in `models.py`
  - runtime table bootstrap currently via `db.create_all()` in `app.py`
- frontend:
  - jinja templates
  - shared css tokens + style sheets
  - javascript for realtime + interaction
  - socket.io client for hub streams
  - three.js for risk-oracle globe
- ai / model integrations:
  - ollama lane integrated in service ecosystem
  - x-sentry/social automation and content tooling pipelines
- media/rendering:
  - ffmpeg nvenc workflow
  - medley director render orchestration

## architecture map (entrypoints + runtime flow)
- `run_server.py`
  - production launch entry for flask/socket service.
- `app.py`
  - app + extension initialization, session/csrf context setup, route import boundary.
- `routes.py`
  - primary route surface (public pages, premium hub, admin endpoints, webhooks, api layer).
- `models.py`
  - user/subscription, content, automation, analytics, partner tracking, whale/sentry entities.
- `scripts/intelligence_loop.py`
  - 5-minute sovereign heartbeat loop:
    - x-sentry cycle
    - whale watcher ingest
    - signal logger output
- `medley_director.py`
  - gpu 1 render worker for 60-second intelligence brief output + progress tracking.

## core feature inventory (world-class target lanes)

### 1) x-sentry intelligence lane
- monitors target signals and drafts reply intelligence.
- writes classified signal lines into automation stream (`[sentry] ...`).
- feeds sentry queue controls in commander hub/admin.

### 2) whale watcher lane
- ingests mempool/chain whale activity.
- persists whale transactions, flags mega whales.
- powers:
  - whale feed tiles
  - red glitch event signaling on hub
  - automation signal stream (`[whale] ...`)

### 3) 3d risk oracle
- three.js globe with risk-oriented points of interest.
- data source: mining risk location json payload.
- visual language:
  - risk tier colors (safe/monitor/danger)
  - pulsing nodes by risk intensity
- interaction:
  - clickable nodes populate tactical brief panel (location, sentiment, grid pressure, action cue).

### 4) medley director (video lane)
- hub action: engage medley director.
- backend dispatch:
  - runs render worker pinned to gpu 1.
  - tracks progress via ffmpeg progress output.
- ui status:
  - live render progress bar
  - status messaging
  - output artifact endpoint.

### 5) sovereign bridge onboarding ramp
- hub "bitcoin services" partner ramp by category:
  - earn / borrow / insure / spend / save / self-custody / business
- each partner card includes:
  - what it is
  - eligibility tags
  - why use it
  - cta
  - disclosure posture
- tracking:
  - partner click events with user/session/ref code context
- admin visibility:
  - partner ramp analytics
  - conversion notes
  - ctr-oriented review.

## current blockers (must remain visible)

### blocker 1: circular import/routing integrity
- circular import behavior between app/routes historically caused missing route registration and endpoint build errors.
- recent fix pattern:
  - keep `import routes` at absolute bottom of `app.py`
  - initialize app/extensions before route registration
  - run with reloader off to avoid duplicate loader edge cases.
- requirement going forward:
  - preserve boot order discipline or split blueprints cleanly.

### blocker 2: ssh tunnel/port requirements
- required ports for operational workflow:
  - `11434` (ollama/model lane tunnel)
  - `5000` (flask app/hub tunnel)
- if tunnels are not active/correct, remote access and model calls degrade/fail.
- no random port guessing. lock docs + launch scripts to explicit tunnel map.

## deployment status snapshot
- `pulse_intel.service`: **active (running)**
- verified status:
  - loaded from user systemd unit
  - running `scripts/intelligence_loop.py`
  - restart persistence enabled.

## quality bar to continue building confidently
- foundation is moving in the right direction, but production hardening remains mandatory:
  - enforce strong secret/session policy
  - migrate from dev server to hardened wsgi runtime
  - lock cors/origin policies
  - enforce migration-first schema ops (not runtime table creation)
  - complete csrf/webhook verification pass.

## immediate next phase handoff
- next operation: mining risk data injection.
- objective:
  - enrich risk dataset coverage
  - increase oracle tactical fidelity
  - keep hub interactions fast, deterministic, and operator-grade.
