# FEATURE SPEC — media-unified-p2
## IDENTITY
- **FEATURE:**       MEDIA UNIFIED Phase 2
- **BRANCH:**        agent/media-unified-p2
- **WORKTREE_DIR:**  ~/worktrees/media-unified-p2
- **SESSION:**       agent_media-unified-p2
- **PRIORITY:**      🟡 Medium

## SCOPE
Implement Phase 2 features from MEDIA_UNIFIED_PHASE_ROADMAP.md in media_unified.html:
Kill fake X feed, kill hardcoded quotes, wire telemetry/sentiment to live API endpoints,
add Nostr relay manager panel, add Signal Strength composite indicator,
add health strip. All per MEDIA_UNIFIED_PHASE_ROADMAP.md spec.
Banned: Three.js, VR, DAO, quantum auth, Sora, genetic algorithms.

## SUCCESS CRITERIA
1. No hardcoded fake tweets or quotes in media_unified.html
2. Telemetry bar pulls live from /api/spaces/live and /api/media/sentiment
3. Signal Strength composite indicator: 70% existing + 30% x_spaces sentiment
4. Nostr relay manager shows relay status (connected/disconnected)
5. Health strip shows service status for 5 core services
6. All API calls handle errors gracefully (show last known value, not crash)
7. Page loads in <3s on first visit
8. Regression zero FAILs

## FILES_TO_TOUCH
- `templates/media_unified.html` — Phase 2 features
- `core/routes.py` — any new API endpoints needed for P2 features

## FILES_NEVER_TOUCH
- `video_pipeline_v3/` — no pipeline touches
- `templates/intelligence_dashboard.html` — separate page
- `regression_test.sh`

## GPU USAGE
- Requires GPU render: NO

## PR FORMAT
- **Title:** `feat(media-unified): Phase 2 — live telemetry, Nostr, signal strength, health strip`

## STATUS
- [x] Spec written
- [ ] Agent launched
