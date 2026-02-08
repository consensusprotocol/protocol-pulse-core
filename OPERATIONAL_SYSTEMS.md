# Protocol Pulse — Operational Systems for Content Strategies

Status of systems that are **ready to run** vs **need cron/env** to start the content strategies laid out in the editorial rulebook.

---

## Ready to run (no extra setup)

| System | What it does | How to trigger |
|--------|----------------|----------------|
| **Article drafting** | Generates one article (ContentEngine or Reddit → ContentGenerator), saves draft, optional Substack | `POST /api/trigger-automation` or cron every 6h |
| **Sarah daily brief** | Builds briefing from CollectedSignal + NodeService, creates Article + SarahBrief | `POST /api/sarah-briefing/generate` (e.g. cron 06:00 UTC) |
| **Signal collection** | Fetches X, Nostr, Stacker News → saves to CollectedSignal | `POST /admin/api/collect-signals` (admin) |
| **Emergency flash check** | Checks SentimentBuffer for 40%+ drift, creates EmergencyFlash | `POST /api/sarah-briefing/check-flash` |
| **Fact-check** | Runs on every generated article via `verify_article_before_publish()` | Automatic in content_generator pipeline |
| **Duplicate gatekeeper** | Gemini compares topic to last 10 headlines; blocks DUPLICATE | Automatic in content_generator |
| **Editor-in-Chief review** | Gemini scores article 1–10; APPROVE ≥7 | content_engine.review_article_with_gemini() |
| **Daily brief (admin flow)** | FeedItem → sarah_analyst.analyze_signals + generate_daily_brief → DailyBrief | `POST /admin/api/generate-daily-brief` |
| **Tweet draft from brief** | Sarah persona tweet from daily brief | `POST /admin/api/daily-brief/<id>/create-tweet` |
| **Multi-agent supervisor** | Alex (NodeService ground truth) + Sarah (macro layer) → content package | `multi_agent_supervisor.build_content_package()` |
| **Content analyzer** | Newsworthiness 1–10 (Gemini/OpenAI); gates 6+/7+/8+ | `content_analyzer.score_newsworthiness()` |
| **Target monitor** | New YouTube videos from supported_sources; new X posts; flag_for_article | `target_monitor.get_new_youtube_videos()` etc. |
| **Scheduler tasks** | Single entry point for cron: cypherpunk_loop, sarah_brief_prep, sarah_intelligence_briefing, etc. | `scheduler.run_task("task_name")` |

---

## Need cron or env to be “on”

| System | Dependency | How to turn on |
|--------|------------|----------------|
| **Cypherpunk’d loop (articles every 6h)** | Cron hitting `/api/trigger-automation` | Render cron `0 */6 * * *` (already in render.yaml) |
| **Sarah brief at 06:00** | Cron or scheduler | Add cron `0 6 * * *` → `POST /api/sarah-briefing/generate` |
| **Intelligence stream (intel tweets every 3h)** | X (and optionally Nostr) credentials; partner YouTube | Cron every 3h calling `intelligence_stream_service.run_intel_stream_cycle()` or an API that does it |
| **Sentiment buffer update** | SentimentBuffer rows (from CollectedSignal/FeedItem) | Cron every 5min → `sentiment_service.update_buffer()` or scheduler.run_task("sentiment_buffer_update") |
| **Social listener (priority X reply + image)** | X API, optional Gemini Imagen | Wire social_listener to a stream or cron when priority accounts post |
| **Spaces recap** | yt-dlp, AssemblyAI API key, Space URL | Implement spaces_service.get_space_audio_url + transcribe when you have keys |
| **Podcast from partners** | ElevenLabs (and supported_sources YouTube) | automation.process_all_partner_channels() or generate_podcasts_from_partners() |

---

## Summary

- **Article pipeline**: Trigger automation is live; ensure the 6h cron is active on Render so drafting runs automatically.
- **Sarah brief**: Routes and DB are in place; run signal collection (admin or cron), then call generate (manual or 06:00 cron).
- **Intel stream / sentiment / social listener / Spaces**: Code is in place; enable via cron or background workers once the right env (X, Nostr, AssemblyAI, etc.) is configured.

All editorial rules (6-section structure, accuracy mandate, fact-check, headlines) are enforced in `content_generator` and `content_engine` for any article generated through this stack.
