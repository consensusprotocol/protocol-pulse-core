Read PIPELINE_LAWS.md. Read docs/VISUAL_DESIGN_SYSTEM.md if it exists.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRIDAY DEMO AUDIT — PROTOCOL PULSE FULL SITE + ORACLE POLISH
DEADLINE: Friday (2 days). Goal: polished live demo for real audience.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run the cross-LLM audit via utils/cross_llm_audit.py on these files:
  - templates/oracle_live.html
  - oracle/avatar_server.py (lines 1-100, 1573-1620, 1919-2000)
  - templates/merch.html

AUDIT QUESTIONS FOR EACH MODEL (8 brutal questions):
1. What is the most likely failure mode during a live demo with 10 people watching?
2. What would cause a visitor to think the experience is broken when it isn't?
3. What mobile-specific failure modes exist that desktop testing wouldn't catch?
4. What happens if the GPU is processing a pipeline render while someone uses the oracle?
5. What is the worst UX moment in the current oracle flow?
6. What visual element would immediately signal "amateur" to a sophisticated audience?
7. What is one change that would have the highest impact on demo quality?
8. What network conditions would cause a silent failure?

AFTER AUDIT:
1. Synthesize Cycle 1 findings — rank issues P0/P1/P2
2. Cycle 2 cross-validation
3. Implement all P0 and P1 fixes
4. Specifically check and fix:
   - Oracle: during thinking state, avatar face must ALWAYS be visible (never black)
   - Oracle: if /oracle/thinking video fails to load, show static avatar image fallback
   - Oracle: response latency display — show "Satomi is thinking..." with elapsed time counter
   - Oracle: if chat takes >15s, show reassuring message "Rendering your brief..."
   - Merch: verify /merch loads products from Printful live (PRINTFUL_API_KEY is set)
   - Site: verify all nav links work (no 404s on primary nav)
   - Articles: verify category filter tabs work end-to-end
   - Admin: verify dashboard loads all widgets correctly

5. git add -A && git commit -m "feat(friday-audit): P0+P1 fixes from multi-LLM demo readiness audit" && git push
