
╔══════════════════════════════════════════════════════════════════════════════╗
║         PROTOCOL PULSE — PHASE 4: 10-FEATURE SEQUENTIAL BUILD SPRINT       ║
║         One at a time. Gospel → Phase 0 → Build → Audit → Merge. Repeat.  ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are executing 10 feature builds SEQUENTIALLY — never in parallel.
Each build follows the identical strict process. No shortcuts. No skipped steps.

INVIOLABLE LAWS FOR ALL BUILDS:
1. Read CROSS_LLM_AUDIT_LAW.md before starting each feature
2. Run Phase 0 pre-build LLM council (cross_llm_audit.py --phase0) before writing code
3. Build full implementation in its worktree/branch
4. Run regression_test.sh — zero FAILs before ANY commit
5. Run full 2-cycle cross-LLM audit on ACTUAL built code (never specs)
6. Second Claude Code pass on all P0+P1 audit findings
7. git add -A && git commit && git push after every feature
8. Write BUILD_COMPLETE.md in the worktree root
9. Only start the NEXT feature after current one has BUILD_COMPLETE.md committed

════════════════════════════════════════════════════════════════════════════════
THE PROCESS (same for every feature, no exceptions)
════════════════════════════════════════════════════════════════════════════════

For each feature:

STEP 1 — SETUP
  git worktree add ~/worktrees/{FEATURE_ID} feature/{FEATURE_BRANCH} 2>/dev/null || \
    git worktree add ~/worktrees/{FEATURE_ID} -b feature/{FEATURE_BRANCH}
  cd ~/worktrees/{FEATURE_ID}
  cat ~/protocol_pulse/CROSS_LLM_AUDIT_LAW.md
  cat ~/protocol_pulse/docs/gospels/{GOSPEL_FILE}

STEP 2 — PHASE 0 PRE-BUILD COUNCIL
  cd ~/protocol_pulse
  python3 utils/cross_llm_audit.py --feature {FEATURE_ID} --phase0
  # This fires Gemini+GPT-4o+Grok SIMULTANEOUSLY against the gospel spec
  # Read the synthesis in docs/audits/{FEATURE_ID}/C0_SYNTHESIS.md
  # Write PHASE0_ADDENDUM.md in the worktree — binding spec additions
  # Build CANNOT start until Phase 0 completes

STEP 3 — BUILD
  cd ~/worktrees/{FEATURE_ID}
  # Implement the full feature per gospel + Phase 0 addendum
  # All new files go in the worktree
  # Routes added to core/routes.py (edit in worktree, it's symlinked or copied)
  # Services in services/ or cron/ as specced
  # Templates in core/templates/
  # No banned tech (Creatomate, OpusClip, MuseTalk, SadTalker per feature laws)

STEP 4 — REGRESSION TEST
  cd ~/protocol_pulse
  bash regression_test.sh
  # MUST be zero FAILs — fix anything failing before proceeding

STEP 5 — CROSS-LLM AUDIT (2 full cycles on ACTUAL CODE)
  python3 utils/cross_llm_audit.py --feature {FEATURE_ID}
  # Cycle 1: Gemini+GPT-4o+Grok audit actual built code in parallel
  # Cycle 2: Models cross-validate each other's findings
  # Read docs/audits/{FEATURE_ID}/CYCLE2_SYNTHESIS.md
  # Implement all P0 + P1 findings immediately

STEP 6 — SECOND CLAUDE CODE PASS
  # Apply every P0 and P1 finding from the audit
  # Re-run regression_test.sh — still zero FAILs

STEP 7 — COMMIT + PUSH
  cd ~/worktrees/{FEATURE_ID}
  git add -A
  git commit -m "feat({FEATURE_ID}): complete build — gospel + Phase0 + 2-cycle audit"
  git push origin feature/{FEATURE_BRANCH}

STEP 8 — BUILD_COMPLETE.md
  Write BUILD_COMPLETE.md to ~/worktrees/{FEATURE_ID}/BUILD_COMPLETE.md with:
  - What was built (routes, services, templates, DB tables)
  - Audit grade and key findings fixed
  - Commit hash
  - Any PBX actions required (e.g. Stripe keys, API credentials)
  git add BUILD_COMPLETE.md && git commit -m "docs: BUILD_COMPLETE for {FEATURE_ID}" && git push

════════════════════════════════════════════════════════════════════════════════
THE 10 FEATURES — EXECUTE IN THIS EXACT ORDER
════════════════════════════════════════════════════════════════════════════════

──────────────────────────────────────────────────────────────────────────────
BUILD 1 of 10 — F5: NODE WATCH
FEATURE_ID: f5-node-watch
FEATURE_BRANCH: feature/f5-node-watch
GOSPEL: docs/gospels/F5_NODE_WATCH_GOSPEL.md
WHY FIRST: Fast win, fully self-contained, no external API keys needed (Bitnodes
           is free/public), delivers live Bitcoin network data to homepage.
WORKTREE: ~/worktrees/f5-node-watch (may already exist — check first)
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 2 of 10 — B1: NEWSLETTER ENGINE
FEATURE_ID: b1-newsletter
FEATURE_BRANCH: feature/b1-newsletter
GOSPEL: docs/gospels/B1_NEWSLETTER_GOSPEL.md
WHY SECOND: Direct revenue/retention impact. Resend API is already in .env.
            Subscriber capture is live. This activates the full email channel.
WORKTREE: ~/worktrees/b1-newsletter
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 3 of 10 — V30: PULSE TERMINAL API (Commander $49/mo)
FEATURE_ID: v30-terminal-api
FEATURE_BRANCH: feature/v30-terminal-api
GOSPEL: docs/gospels/V30_TERMINAL_API_GOSPEL.md
WHY THIRD: Direct revenue — the $49/mo Commander tier is the highest-priority
           monetization feature. P3 premium-stripe laid the Stripe foundation.
           This plugs intelligence data into a paid API with rate limiting.
NOTE: PBX must add STRIPE_COMMANDER_PRICE_ID to .env for Stripe checkout.
      Build the full feature anyway. Document the missing key in BUILD_COMPLETE.md.
WORKTREE: ~/worktrees/v30-terminal-api
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 4 of 10 — F4: NOSTR INTELLIGENCE SYSTEM
FEATURE_ID: f4-nostr
FEATURE_BRANCH: feature/f4-nostr
GOSPEL: docs/gospels/F4_NOSTR_GOSPEL.md
WHY FOURTH: Distribution and community. Nostr is the cypherpunk-native social
            layer. This makes PP a first-class Nostr citizen — monitoring,
            scoring, and publishing to the protocol.
WORKTREE: ~/worktrees/f4-nostr
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 5 of 10 — F1: AVATAR ORACLE OVERHAUL
FEATURE_ID: f1-avatar-oracle
FEATURE_BRANCH: feature/f1-avatar-oracle
GOSPEL: docs/gospels/F1_AVATAR_ORACLE_GOSPEL.md
WHY FIFTH: The Oracle is PP's #1 differentiator. The Wav2Lip engine is on Ultron
           and working. This makes the oracle page production-grade — the anime
           cyberpunk persona, the full UI overhaul, the Oracle Sanctuary layout.
CRITICAL LAWS (enforced by gospel):
  - Wav2Lip ONLY for lip-sync (batch_size=48, FP16, GPU-cached)
  - apply_blink() body = `return frame` (disabled permanently)
  - DO NOT call HeyGen for Oracle avatar
WORKTREE: ~/worktrees/f1-avatar-oracle
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 6 of 10 — F2: MARKET BRIEFING ROOM
FEATURE_ID: f2-briefing-room
FEATURE_BRANCH: feature/f2-briefing-room
GOSPEL: docs/gospels/F2_BRIEFING_ROOM_GOSPEL.md
WHY SIXTH: Premium content. HeyGen Sarah avatar ($1/min) delivers daily market
           briefings. Archive of last 3 briefings. This is the "Coin Bureau meets
           Bloomberg" content layer.
NOTE: Uses HeyGen API (HEYGEN_API_KEY in .env). Sarah avatar ID: d259c335741f4fc0b061e04c59388b4e
WORKTREE: ~/worktrees/f2-briefing-room
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 7 of 10 — F3: SCHIFF-BOT HYPOCRISY METRIC
FEATURE_ID: f3-schiff-bot
FEATURE_BRANCH: feature/f3-schiff-bot
GOSPEL: docs/gospels/F3_SCHIFF_BOT_GOSPEL.md
WHY SEVENTH: Viral differentiator. Real EDGAR 13F SEC filings, Peter Schiff's
             gold holdings parsed, Schiff's anti-Bitcoin tweets scored against
             actual portfolio performance. The "Brian" persona delivers verdict.
NOTE: SEC EDGAR API is public/free. No auth needed.
WORKTREE: ~/worktrees/f3-schiff-bot
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 8 of 10 — F6: MARKETING OS + MILESTONE CAMPAIGN ENGINE
FEATURE_ID: f6-marketing-os
FEATURE_BRANCH: feature/f6-marketing-os
GOSPEL: docs/gospels/F6_MARKETING_OS_GOSPEL.md
WHY EIGHTH: When BTC hits $100K/$120K/$150K/$175K/$200K — PP fires coordinated
            campaigns automatically. Performance metrics schema. This is the
            "always-on marketing team" layer.
WORKTREE: ~/worktrees/f6-marketing-os
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 9 of 10 — V22: MULTI-FORMAT VIDEO DISTRIBUTION
FEATURE_ID: v22-multi-format
FEATURE_BRANCH: feature/v22-multi-format
GOSPEL: docs/gospels/V22_MULTI_FORMAT_GOSPEL.md
WHY NINTH: Distribution amplification. Every Pulse Check episode gets reformatted
           and distributed across platforms (YouTube, X/Twitter, Nostr, newsletter)
           automatically. Maximizes reach per render.
WORKTREE: ~/worktrees/v22-multi-format
──────────────────────────────────────────────────────────────────────────────

──────────────────────────────────────────────────────────────────────────────
BUILD 10 of 10 — ARTICLE PAGE FINAL 10%
FEATURE_ID: p4-article-page
FEATURE_BRANCH: feature/p4-article-page
GOSPEL: ~/protocol_pulse/ARTICLE_PAGE_LAWS.md (use this as gospel)
WHY TENTH: Articles are the foundation of everything — SEO, affiliate, newsletter.
           This completes the final 10%: Cloudflare proxy seamless URL, SEO meta,
           related articles, reading progress bar, TL;DR strip, social share,
           tip jar CTA, pro badge for Commander content.
WORKTREE: ~/worktrees/p4-article-page
NOTE: Load ARTICLE_PAGE_LAWS.md into THIS session — it is gospel.
──────────────────────────────────────────────────────────────────────────────

════════════════════════════════════════════════════════════════════════════════
QUALITY BAR FOR EVERY FEATURE
════════════════════════════════════════════════════════════════════════════════

Every feature must achieve ALL of the following before BUILD_COMPLETE:

FUNCTIONALITY:
✅ All routes respond with HTTP 200 (not 404/500)
✅ All DB tables created via db.create_all() or migration
✅ All cron jobs registered in cron scheduler
✅ All API endpoints return valid JSON with correct structure
✅ All forms submit without errors
✅ Admin views render correctly (if applicable)

VISUAL:
✅ Matches VISUAL_DESIGN_SYSTEM.md exactly:
   - Background: #0A0A0F
   - Accent: #FF3333 (red)
   - Gold: #F8C15C
   - Font: JetBrains Mono for data, system sans for body
   - Dark glassmorphism panels
   - Red/cyan/gold radial glow effects where appropriate
✅ Mobile responsive (375px viewport — no horizontal scroll)
✅ Extends base.html (nav, footer, bottom gold bar)
✅ No broken images or missing assets

CODE QUALITY:
✅ No hardcoded API keys or secrets in code (use os.environ.get())
✅ All external API calls have try/except with graceful fallback
✅ All DB queries have error handling
✅ No circular imports
✅ No unused imports

AUDIT:
✅ Both LLM audit cycles complete
✅ All P0 findings fixed
✅ All P1 findings fixed
✅ Regression test: zero FAILs

════════════════════════════════════════════════════════════════════════════════
TRACKING
════════════════════════════════════════════════════════════════════════════════

Maintain ~/protocol_pulse/logs/phase4_builds.md:

| # | Feature | Branch | Status | Commit | Grade | PBX Actions |
|---|---------|--------|--------|--------|-------|-------------|

Update after each BUILD_COMPLETE.

════════════════════════════════════════════════════════════════════════════════
BEGIN NOW — START WITH BUILD 1: F5 NODE WATCH
════════════════════════════════════════════════════════════════════════════════

Execute autonomously. After each build completes:
  - Confirm BUILD_COMPLETE.md is committed and pushed
  - Update phase4_builds.md
  - Start the next build immediately

If you hit a blocker that requires PBX action (e.g. missing API key):
  - Document it in BUILD_COMPLETE.md under "PBX ACTIONS REQUIRED"
  - Move to the next feature — don't block on missing credentials
  - Come back to blocked items after all 10 are done

Go.
