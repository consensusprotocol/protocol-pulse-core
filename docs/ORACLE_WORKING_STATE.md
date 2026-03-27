# Oracle (Satomi) Working State — v1

**Tagged:** `oracle-satomi-working-v1` on 2026-03-26
**Branch:** `main`

---

## What Works

- **go() fixed** (commit `6a10cde0`): removed orphaned `.catch()` block, `go()` now globally defined and callable from console/UI
- **Gemini vision confirmed**: vision analysis routes through `process()` pipeline, Satomi lip-syncs hardware guidance
- **Plasma corona orbital**: canvas-based circular avatar with animated plasma corona effect
- **ElevenLabs voice**: Rachel voice (`21m00Tcm4TlvDq8ikWAM`) via `eleven_multilingual_v2`
- **Session log**: conversation history maintained per session
- **Avatar server**: port 8200, health check at `/health`, generation at `/generate`

## Known Issues

- Avatar crops when session log expands (layout fix in progress)
- Vision + voice confirmed working but Wav2Lip lip-sync quality varies with input audio

## Key Files

| File | Purpose |
|------|---------|
| `templates/oracle_live.html` | Main Oracle UI (HTML + inline JS/CSS) |
| `oracle/avatar_server.py` | Avatar generation server (port 8200, cuda:1) |
| `oracle/data/visitor_memory.db` | Visitor session memory |

## Key Commits

| Commit | Description |
|--------|-------------|
| `6a10cde0` | fix(oracle): remove orphaned .catch() — go() globally defined |
| `fc6e0667` | fix(oracle): remove orphaned voice audio block |
| `60b5447e` | fix(oracle): vision routes through process()->Wav2Lip |
| `01f79aca` | fix(oracle+flask-restart+6-surgical) |
| `a4bf4c6d` | snapshot(oracle): Satomi working — vision+voice confirmed |

## Revert Command

To restore this exact working state:

```bash
git checkout oracle-satomi-working-v1 -- templates/oracle_live.html
```

Or to restore full repo state:

```bash
git checkout oracle-satomi-working-v1
```

## Backup Files

- `templates/oracle_live.html.bak_working_20260326`
