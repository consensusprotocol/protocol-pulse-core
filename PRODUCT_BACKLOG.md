# PROTOCOL PULSE — PRODUCT BACKLOG
# Tasks queued from PBX session 2026-03-05
# Prioritized for phased execution
# Status: ACTIVE BACKLOG. Reference before each session.

---

## PHASE NEXT (after video pipeline stable)

### 1. Newsletter Full Activation
- Welcome email for new signups (confirm subscription + "mark not spam" instruction)
- Import old subscriber emails from consensusprotocol.org era
- Send reactivation email to legacy subs: "We're live! Here's what to expect"
- Ensure all buttons/links in email templates work
- Daily digest already built (routes_newsletter_trigger.py on Replit)

### 2. Intelligent Clip Selection Logic
- Current: Claude LLM selects clips from transcripts with basic prompt
- Needed: Codified analysis scoring each clip moment by:
  - Real-time topic demand (velocity from daily_signals.json)
  - Engagement potential (does this topic trend on X right now?)
  - Novelty (has this been covered in last 3 episodes?)
  - Speaker authority (is this person a recognized expert?)
  - Emotional impact (controversial, surprising, data-heavy?)
- Score each potential clip 0-100, select top 5 from 5 unique channels
- This transforms clip selection from "ask Claude" to "data-driven ranking"

### 3. PBX ElevenLabs Professional Voice Clone
- PBX is at studio NOW to record 30-minute sample
- Upload to ElevenLabs Professional Voice Cloning
- Integrate as Host 2 (male) replacing Mark
- Eventually: phone call briefings + PBX Report narration

---

## PHASE LATER (after core products live)

### 4. Avatar Instant-Response Mode
- Problem: 10.8s avatar render = most users leave
- Solution: Remotion voice wave animation as DEFAULT (instant response)
- Avatar loads on button press with holographic/glitch beam-up effect
- Glassmorphism loading state → stable avatar image feed
- "Her"-level conversational intelligence with real-time assistance

### 5. Gemini Vision Camera Feature
- User points phone camera at Bitcoin hardware (Coldcard, Trezor, etc.)
- Avatar sees via camera, gives real-time setup instructions
- Browser-based (no app needed), mobile-compatible
- Uses Gemini 2.5 Flash multimodal (already integrated on Ultron)
- Potential killer feature for onboarding newbies

### 6. Sat Stacker Game
- Interactive browser game on protocolpulse.io
- Players earn sats (real Lightning payments)
- Self-funding model: ad revenue from game page covers sat payouts + profit
- Lightning layer for instant settlement (cash out or accumulate in account)
- GetIB wallet integration for auto-distribution at threshold
- Dedicated foundational buildout required (game design, economics, Lightning infra)

### 7. Phone Call Briefings
- Sign up for morning/daily briefings delivered as PHONE CALL
- ElevenLabs voice (PBX clone when ready) reads the daily digest
- Also: Telegram text updates with key signals
- Twilio or similar for call delivery
- Premium feature (Sovereign tier?)

### 8. Mobile UI Forensic Audit
- Triple-check every page on 375px viewport
- Navigation, article cards, media player, terminal dashboard
- Touch targets, scroll behavior, font sizes
- Ensure glassmorphism effects don't break on mobile Safari/Chrome

### 9. Article Page Final 10%
- articles.protocolpulse.io is 90% done on Vercel
- Remaining: Cloudflare Workers proxy (seamless URL), SEO meta tags,
  social share images, related articles section, reading progress bar
- Then: redirect protocolpulse.io/articles → Vercel seamlessly

---

## FUTURE FEATURES (post-revenue)

### 10. X Articles + Substack Distribution
- 1 X Article per week (Wednesday), 1 Substack per week (Sunday)
- Same analysis, platform-specific formatting
- Auto-generated from best intelligence of the week

### 11. HeyGen Avatar Episodes
- Weekly "PBX Report" using HeyGen PBX avatar ($2/min)
- Separate from daily Pulse Check (which uses TTS voices)
- Coin Bureau style, cypherpunk editorial angle

### 12. V19-V21 Pipeline Completion
- V19: Orchestrator integration (night runner)
- V20: Self-analysis + prompt evolution
- V21: Sponsor agent (after 10 consecutive clean uploads)

---

*Updated: 2026-03-05 by PBX voice notes session*
