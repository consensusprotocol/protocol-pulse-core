Below is a ruthless 2026-grade review of the spec. The current spec is solid for a useful internal sponsor CRM + outreach tool, but it is **not yet a true unfair-advantage revenue engine**. It’s missing closed-loop learning, multi-source signal fusion, deliverability intelligence, contact discovery/verification rigor, agentic workflow controls, and a much more advanced UI/ops model.

---

# Executive verdict

**What’s strong already**
- Clear revenue objective
- Good initial schema
- Good insistence on raw research storage and no hallucination
- Human confirmation before send
- Activity logging and soft-delete
- Basic AI loop: research → score → draft → review

**What’s weak / incomplete**
- Too email-centric
- Too single-source-centric on intelligence
- No contact discovery/verification pipeline
- No deliverability/reputation layer
- No closed-loop learning from outcomes
- No account-based buying committee model
- No event-driven architecture
- No serious compliance/governance model
- No experimentation framework
- No “why now” trigger engine
- No sponsor package recommendation / pricing optimization
- UI is Kanban-first, but not operator-superpower-first

If built exactly as written, this becomes a decent internal tool.  
If upgraded with the additions below, it becomes a **sponsor intelligence operating system**.

---

# 1. MISSING FEATURES

## 1) Multi-source signal fusion, not just Grok research
Right now the spec over-relies on Grok web research. In 2026, best-in-class prospecting systems fuse:
- web/news signals
- podcast transcript mentions
- YouTube sponsor reads
- newsletter ad placements
- LinkedIn hiring trends
- website pixel / ad-tech changes
- product launches / funding / geo expansion
- conference sponsorships
- affiliate program changes
- competitor sponsorship activity

### Add:
**Sponsor Signal Graph**
A normalized signal layer that stores every evidence item with:
- source type
- source URL
- timestamp
- confidence score
- extracted entities
- spend intent classification
- “Bitcoin adjacency” score

This should power:
- relevance scoring
- urgency scoring
- outreach angle generation
- explainability in UI

Without this, “deep research” remains too opaque and brittle.

---

## 2) Contact discovery + verification pipeline
The spec has `contact_email`, `contact_name`, `contact_linkedin`, but no system for how these are found and verified.

### Add:
**Buying Committee Discovery**
For each sponsor account, identify:
- Head of Growth
- Partnerships lead
- Podcast/media buyer
- Brand marketing manager
- Founder/CEO for smaller firms

Store multiple contacts per sponsor, not one.

### New table:
```sql
CREATE TABLE IF NOT EXISTS sponsor_contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sponsor_id INTEGER NOT NULL REFERENCES sponsors(id),
  full_name TEXT,
  role_title TEXT,
  seniority TEXT,              -- manager|director|vp|founder|cxo
  email TEXT,
  email_status TEXT,           -- unverified|verified|risky|bounced
  linkedin_url TEXT,
  twitter_url TEXT,
  source TEXT,                 -- enrichment provider / manual / grok
  confidence_score INTEGER DEFAULT 0,
  is_primary INTEGER DEFAULT 0,
  last_verified_at DATETIME,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Why this matters
A sponsor deal is rarely won by one generic inbox.  
You need **account-based outreach**, not just lead-based outreach.

---

## 3) Trigger-based “why now” engine
The current spec finds sponsors, but doesn’t strongly model **timing**.

### Add:
**Why-Now Trigger Engine**
Examples:
- company launched a new product
- raised funding
- entered US market
- hired growth/podcast/performance roles
- competitor started sponsoring Bitcoin podcasts
- conference season approaching
- quarter-end budget flush
- major Bitcoin market cycle event
- regulatory event increasing category demand
- website changed pricing / campaign pages
- new affiliate campaign launched

Each trigger should create:
- urgency score
- recommended angle
- recommended send window
- follow-up cadence recommendation

This is one of the biggest missing pieces.

---

## 4) Closed-loop learning from outcomes
The spec drafts and sends, but doesn’t learn.

### Add:
**Outcome Learning Layer**
Track:
- open rate by subject pattern
- reply rate by angle
- positive reply rate by category
- conversion rate by company size
- time-to-reply by send time/day
- deal close rate by trigger type
- average ACV by sponsor segment
- best-performing stats snippets from Protocol Pulse metrics

Then use this to:
- rank outreach variants
- recommend next-best-action
- improve scoring model
- optimize package recommendations

This turns the system from automation into **compounding intelligence**.

---

## 5) Offer/package recommendation engine
The spec estimates deal value but doesn’t recommend what to sell.

### Add:
**Dynamic Sponsorship Package Composer**
For each sponsor, generate recommended package:
- newsletter placement
- site display
- podcast pre-roll / mid-roll
- sponsored article
- event sponsorship
- bundle package
- test budget package
- quarterly package
- category exclusivity upsell

Include:
- recommended monthly price range
- confidence
- rationale
- expected close probability
- expected LTV
- objection handling notes

This is critical because outreach should not just say “want to sponsor?”  
It should say **“here’s the exact package that fits your current spend behavior and audience overlap.”**

---

## 6) Deliverability intelligence and sender reputation controls
Resend is good, but sending is not enough.

### Add:
**Deliverability Guardrail System**
- domain warm-up state
- inbox placement monitoring
- bounce tracking
- complaint tracking
- unsubscribe handling
- suppression list
- role-based inbox avoidance (`info@`, `hello@`, etc.)
- send throttling by domain
- per-domain cadence rules
- spam phrase linting
- DMARC/SPF/DKIM/BIMI health checks
- content fingerprinting to avoid repetitive AI patterns

This is mandatory if volume grows.

---

## 7) Multi-channel orchestration
Spec mentions `email|linkedin|twitter` in outreach table, but only email is operationalized.

### Add:
**Channel Orchestrator**
- email first
- LinkedIn connect + note
- X/Twitter engagement before outreach
- warm-up touch via comment/reply on public content
- calendar invite / one-click meeting link
- retargeting audience export for high-value accounts
- CRM task generation for manual founder outreach

Best systems in 2026 are **channel-aware**, not email-only.

---

## 8) Autonomous but bounded agent workflows
The current “agent” is really a set of scripts. In 2026, this should be a supervised multi-agent system.

### Add:
**Agent roles**
- Scout Agent: finds sponsors and signals
- Research Agent: compiles evidence dossier
- Contact Agent: finds/validates contacts
- Strategist Agent: chooses angle/package
- Copy Agent: drafts outreach
- Critic Agent: scores realism and reply likelihood
- Compliance Agent: checks claims/privacy/spam risk
- Scheduler Agent: chooses send time/follow-up
- Deal Desk Agent: recommends pricing and concessions

Each agent should produce structured outputs with confidence and provenance.  
All autonomous actions should require policy checks and, for sending, human approval.

---

## 9) Explainable scoring
`relevance_score` is too simplistic.

### Add:
Break scoring into components:
- audience fit score
- spend likelihood score
- Bitcoin affinity score
- urgency score
- contactability score
- deliverability score
- expected ACV score
- close probability
- strategic value score

Then compute:
- `priority_score`
- `next_best_action`

This makes the system operable and trustworthy.

---

## 10) Competitive intelligence and whitespace mapping
The spec finds active sponsors, but not market gaps.

### Add:
**Sponsor Whitespace Explorer**
Questions it should answer:
- Which sponsor categories are underpenetrated in Bitcoin media?
- Which brands sponsor competitors but not Protocol Pulse?
- Which brands are increasing spend elsewhere?
- Which categories have high fit but low current outreach coverage?
- Which accounts are likely to churn from competitor channels?

This creates pipeline beyond obvious podcast sponsors.

---

## 11) Relationship memory + objection intelligence
Need a memory system for every account.

### Add:
- prior objections
- legal/compliance concerns
- budget timing
- preferred channel
- tone preference
- founder affinity
- prior intros
- mutual connections
- meeting notes
- proposal history

And use it in every future draft.

---

## 12) Proposal and contracting workflow
The spec stops at outreach/pipeline.

### Add:
- proposal generation
- insertion order / sponsorship agreement templates
- e-sign integration
- invoice creation handoff
- campaign launch checklist
- renewal reminders
- post-campaign reporting

Revenue engine should cover **lead → close → renew**.

---

## 13) Renewal / expansion engine
Big omission.

### Add:
For won sponsors:
- campaign performance dashboard
- renewal probability score
- upsell suggestions
- 30/60/90-day check-ins
- automated QBR draft
- expansion recommendations based on performance

This is where compounding revenue happens.

---

## 14) Human-in-the-loop controls beyond send confirmation
Need stronger governance.

### Add:
Approval gates for:
- low-confidence research
- unverifiable claims
- high-value accounts
- regulated categories
- aggressive follow-up sequences
- package discounts beyond threshold

---

## 15) Experimentation framework
No A/B testing layer exists.

### Add:
- subject line experiments
- CTA experiments
- angle experiments
- send-time experiments
- package framing experiments
- follow-up sequence experiments

With Bayesian or bandit optimization, not just static A/B.

---

# 2. CUTTING-EDGE 2026 TOOLS / APIS / TECHNIQUES

Below are concrete additions worth considering.

## LLM / agent orchestration
- **LangGraph** or equivalent graph-based agent workflow orchestration for deterministic multi-step pipelines
- **PydanticAI** for typed agent outputs and validation
- **Instructor** for schema-constrained LLM extraction
- **OpenTelemetry GenAI semantic conventions** for tracing prompts, latency, token usage, and failures
- **Model Context Protocol (MCP)** for tool interoperability across research, CRM, email, analytics, and browser tools
- **Vercel AI SDK / AI SDK RSC** if frontend uses React and wants streaming structured UI updates
- **Guardrails AI** or **NVIDIA NeMo Guardrails** for policy enforcement on outbound claims

## Search / retrieval / evidence
- **Tavily**, **Exa**, **Firecrawl**, **Jina AI Reader**, **Browserbase**, **Playwright**
- **Perplexity Sonar API** or equivalent web-grounded research API as secondary verifier
- **Diffbot Knowledge Graph** for company/entity enrichment
- **Common Crawl / GDELT / Event Registry** for event/news monitoring
- **Podscan**, **Listen Notes**, **Podchaser**, **YouTube Data API**, transcript APIs for sponsor mention extraction
- **LinkedIn job post scraping via compliant providers** or enrichment APIs for hiring signals

## Contact enrichment / verification
- **Clay**-style enrichment workflows if available internally
- **People Data Labs**
- **Apollo**
- **Clearbit / Breeze Intelligence equivalents**
- **Dropcontact**
- **Hunter**
- **NeverBounce / ZeroBounce / Bouncer** for email verification

## Deliverability / email ops
- **Resend webhooks**
- **Postmark-style inbound parsing** if inbound reply capture is needed
- **Mail-Tester / GlockApps / Inbox placement APIs** where available
- **DMARC aggregate report parsers**
- **List-Unsubscribe headers**
- **ARC / BIMI support**
- **Domain reputation monitoring**

## Data / storage / analytics
- **SQLite + Litestream** or **Turso/libSQL** if staying SQLite-first but wanting replication
- **DuckDB** for local analytics and CSV/export/report generation
- **ClickHouse** for event analytics if volume grows
- **pgvector** or **SQLite-Vec** for semantic memory / retrieval
- **Apache Iceberg / Delta** only if data lake ambitions exist
- **Temporal** or **Inngest** for durable workflows and retries
- **Redis Streams / NATS / Kafka** for event-driven processing depending scale
- **OpenSearch / Meilisearch / Typesense** for fast sponsor search/filtering

## Frontend / realtime UX
- **React 19 / Next.js 16**
- **TanStack Table / Virtual**
- **shadcn/ui**
- **Framer Motion**
- **tldraw**-style collaborative board interactions if ambitious
- **WebSockets / SSE**
- **CRDTs / Yjs / Liveblocks** for collaborative editing and presence
- **Command palette** with AI actions
- **AG Grid** if enterprise table complexity is high

## Security / compliance
- **Vault / Doppler / 1Password Secrets Automation**
- **SOPS + age**
- **OIDC / SSO / SCIM**
- **Cedar / OPA** for policy-as-code
- **Audit log signing / tamper-evident logs**
- **Field-level encryption**
- **PII detection / redaction tooling**

## ML / optimization techniques
- contextual bandits for send-time and angle optimization
- survival analysis for reply timing
- uplift modeling for follow-up decisions
- graph ranking for account prioritization
- calibration models for confidence scoring
- anomaly detection for deliverability and pipeline health

---

# 3. UX ELEVATION

The current “dark cyberpunk Kanban” is aesthetic, but not enough. 2027-feeling UX is about **agency, explainability, speed, and collaboration**.

## A) Live sponsor command center
Instead of a static board, create a **real-time sponsor ops cockpit**:
- live feed of newly detected sponsors
- signal cards streaming in
- “why this account now” badges
- AI-generated recommended next action
- confidence/provenance chips
- one-click approve / revise / snooze

Think Bloomberg terminal meets Linear meets Clay.

---

## B) Account dossier view
Every sponsor should have a rich account page with:
- company summary
- signal timeline
- active campaigns detected
- podcast sponsorship evidence
- contact map
- outreach history
- objections / notes
- recommended package
- AI strategy memo
- confidence and evidence links

This is far more useful than just Kanban columns.

---

## C) AI copilot with reversible actions
Add a side-panel copilot:
- “Draft a more founder-led version”
- “Show me only high-urgency exchanges”
- “Why is this score 82?”
- “Generate a 2-touch sequence instead”
- “Compare this account to River / Swan / Unchained”
- “What package should we pitch?”

Every AI action should show:
- proposed diff
- evidence used
- confidence
- undo

---

## D) Progressive disclosure of automation
Use automation levels:
- Manual
- Assisted
- Suggested
- Auto-draft
- Auto-schedule
- Auto-follow-up (with policy)

This gives operators confidence and control.

---

## E) Timeline-first interaction model
For each sponsor, show a unified timeline:
- scan found
- research updated
- contact verified
- draft generated
- sent
- opened
- replied
- meeting booked
- proposal sent
- deal won/lost

This should be the primary truth surface.

---

## F) Inline evidence hovercards
Any AI claim in UI should be hoverable:
- “Detected sponsor on 3 Bitcoin podcasts”
- hover → source links, transcript snippets, dates

This is a huge trust unlock.

---

## G) Smart triage views
Not just Kanban/list. Add:
- Hot accounts
- Needs approval
- Follow-up due today
- High ACV / low contactability
- At-risk deliverability
- New trigger events
- Renewal opportunities

---

## H) Collaborative review
- comments on drafts
- mention teammates
- approval requests
- shared annotations on evidence
- live presence in account view

---

## I) One-click “strategy packs”
Generate downloadable/internal strategy briefs:
- account summary
- recommended angle
- package
- contacts
- recent signals
- draft outreach
- objections
- next steps

Useful for founder-led selling.

---

## J) Mobile executive mode
A lightweight mobile view:
- approve drafts
- approve sends
- voice-note feedback
- see hot accounts
- reply to AI questions

This matters if leadership is involved in closing.

---

# 4. PERFORMANCE WINS

## 1) Event-driven architecture
Do not make this a chain of synchronous scripts.

### Use events like:
- `sponsor.detected`
- `research.completed`
- `contact.enriched`
- `draft.generated`
- `draft.reviewed`
- `send.approved`
- `email.sent`
- `email.opened`
- `reply.detected`
- `status.changed`
- `trigger.detected`

This improves retries, observability, and modularity.

---

## 2) Durable workflows
Use **Temporal** or **Inngest** for:
- scans
- enrichment retries
- draft generation
- follow-up scheduling
- webhook handling
- nightly backups

This avoids cron-script fragility.

---

## 3) Split OLTP from analytics
If staying with SQLite:
- operational writes in SQLite/libSQL
- analytical queries in DuckDB snapshots or replicated warehouse
- event logs append-only

This keeps UI fast and analytics cheap.

---

## 4) Incremental scanning and deduplication
Don’t rescan everything every Sunday blindly.

### Add:
- source checkpointing
- content hashing
- transcript diffing
- entity dedupe
- canonical company resolution
- sponsor alias mapping

This cuts cost and latency dramatically.

---

## 5) Caching and memoization
Cache:
- company research summaries
- transcript extraction results
- metrics snapshots
- contact verification results
- prompt templates and scoring outputs

Use TTLs and invalidation on trigger events.

---

## 6) Concurrency controls and rate limiting
Need:
- provider-specific rate limiters
- backoff/retry policies
- circuit breakers
- dead-letter queue for failed enrichments
- idempotency keys for sends and webhook processing

---

## 7) Full-text + semantic search
Use:
- FTS5 for SQLite text search
- vector embeddings for semantic retrieval over notes, transcripts, and prior successful outreach

This powers better operator search and AI grounding.

---

## 8) Observability from day one
Track:
- scan duration
- provider latency
- token cost per sponsor
- draft acceptance rate
- send approval rate
- webhook failure rate
- duplicate sponsor rate
- false positive sponsor detection rate
- reply attribution accuracy

Without this, the system will silently degrade.

---

## 9) Webhook-first updates
For Resend events and future integrations:
- verify signatures
- process asynchronously
- maintain idempotent event store
- reconcile delayed events

---

## 10) Schema upgrades
Current schema is too denormalized for long-term scale.

### Add tables:
- `sponsor_contacts`
- `sponsor_signals`
- `sponsor_research_runs`
- `sponsor_score_breakdown`
- `sponsor_packages`
- `sponsor_experiments`
- `sponsor_webhook_events`
- `sponsor_approvals`
- `sponsor_tasks`
- `sponsor_segments`

---

# 5. MONETIZATION / GROWTH

## 1) Dynamic pricing and package optimization
Use historical outcomes + category benchmarks to recommend:
- starter package
- anchor package
- premium package
- exclusivity upsell
- annual prepay discount
- test campaign offer

This directly increases close rate and ACV.

---

## 2) Referral / intro engine
For each target account, identify:
- mutual connections
- portfolio overlaps
- founder network paths
- existing sponsor referrals
- conference overlap

Then suggest warm intro routes. Warm intros can outperform cold outbound massively.

---

## 3) Competitor conquesting
Track brands sponsoring:
- competing Bitcoin media
- adjacent fintech/crypto podcasts
- macro/finance newsletters
- creator channels

Then pitch Protocol Pulse as:
- incremental reach
- more niche audience
- better CAC efficiency
- category exclusivity

---

## 4) Auto-generated sponsor proof packs
Generate one-click proof packs:
- audience demographics
- campaign examples
- performance stats
- testimonials
- inventory availability
- package options

This shortens sales cycles.

---

## 5) Renewal and expansion automation
As noted earlier:
- renewal reminders
- upsell recommendations
- post-campaign reports
- “you should add newsletter + site retargeting” suggestions

Retention is the fastest revenue growth lever.

---

## 6) Inventory and scarcity engine
If Protocol Pulse has limited ad inventory, expose:
- available slots
- category exclusivity windows
- upcoming sold-out periods
- urgency messaging

Scarcity closes deals.

---

## 7) Revenue forecasting
Need a forecast model:
- weighted pipeline
- expected monthly sponsor revenue
- confidence intervals
- scenario planning
- category concentration risk

This helps product and editorial planning too.

---

## 8) Sponsor-fit marketplace mode
Longer-term, this could become a productized sponsor marketplace:
- inbound sponsor application form
- self-serve media kit
- AI package recommender
- meeting booking
- proposal request flow

Potentially a growth loop.

---

# 6. SECURITY / PRIVACY

This area is under-specified.

## 1) PII governance
You are storing names, emails, LinkedIn URLs, notes.

Need:
- data classification
- retention policy
- lawful basis / legitimate interest review
- DSAR/deletion workflow where applicable
- field-level encryption for contact data
- access controls by role
- auditability of who viewed/exported contacts

---

## 2) Anti-spam / compliance
Need explicit controls for:
- CAN-SPAM
- GDPR/UK GDPR legitimate interest
- unsubscribe handling
- suppression lists
- do-not-contact flags
- frequency caps
- jurisdiction-aware outreach rules

---

## 3) Prompt injection / data poisoning defense
Web research can contain malicious text.

Need:
- sanitization of scraped content
- source trust scoring
- prompt isolation
- no direct execution of model-suggested actions
- provenance display
- allowlist/denylist for sources

---

## 4) Secrets management
`.env` is not enough for a serious system.

Need:
- secret manager
- rotation policy
- environment separation
- least-privilege API keys
- webhook secret verification

---

## 5) Role-based access control
Admin UI should not be all-or-nothing.

Roles:
- viewer
- researcher
- operator
- approver
- admin
- finance

Especially important for send approvals, exports, and pricing edits.

---

## 6) Tamper-evident audit logs
Activity logs should be immutable or at least tamper-evident for sensitive actions:
- send approvals
- status changes
- exports
- deletions
- pricing changes
- contact edits

---

## 7) Export controls
CSV export is useful but dangerous.

Need:
- export watermarking
- actor logging
- row count limits
- reason capture for large exports
- optional encrypted export

---

## 8) Model safety for outbound claims
The system must never fabricate:
- audience metrics
- sponsor overlap
- ad spend
- contact role
- campaign performance

Add a **claim verifier** that checks every outbound sentence against structured evidence.

---

## 9) Backup security
Nightly CSV backups to local path are risky.

Need:
- encryption at rest
- backup integrity checks
- retention policy
- restore drills
- offsite encrypted replication

---

# 7. TOP 5 P0 ADDITIONS

## 1) [SPONSOR SIGNAL GRAPH]
A normalized evidence system that stores all sponsor signals from podcasts, transcripts, news, hiring, website changes, and competitor sponsorships with source URLs, timestamps, confidence, and extracted entities. This becomes the factual backbone for scoring, explainability, and outreach personalization.  
**Why it’s P0:** Without a signal graph, the whole system is too opaque, too brittle, and too dependent on one model’s narrative summary.

---

## 2) [BUYING COMMITTEE DISCOVERY + CONTACT VERIFICATION]
Replace single-contact storage with a multi-contact account model and a verification pipeline for role, email validity, and seniority. Support primary/secondary contacts, role-based routing, and confidence scoring.  
**Why it’s P0:** Great outreach to the wrong or invalid contact is wasted effort; contactability is a first-order determinant of revenue.

---

## 3) [WHY-NOW TRIGGER ENGINE]
Detect and score timing events like funding, launches, hiring, competitor sponsorships, conference cycles, and Bitcoin market catalysts, then use them to drive urgency, angle selection, and send timing.  
**Why it’s P0:** Timing is often the difference between ignored outreach and a live deal; this is a major unfair-advantage layer.

---

## 4) [CLOSED-LOOP LEARNING + EXPERIMENTATION]
Track outcomes across subjects, angles, categories, send times, and package types, then continuously optimize drafts, scoring, and next-best actions using bandits or Bayesian learning.  
**Why it’s P0:** Otherwise the system automates activity, not learning; a revenue engine must improve with every send and every reply.

---

## 5) [DELIVERABILITY + COMPLIANCE GUARDRAILS]
Add sender reputation monitoring, bounce/complaint handling, suppression lists, unsubscribe support, spam-risk linting, domain health checks, and policy enforcement for outbound claims and outreach legality.  
**Why it’s P0:** If deliverability degrades or compliance is mishandled, the entire channel collapses and creates legal/reputational risk.

---

# Recommended spec upgrades, concretely

## Expand schema
Add at minimum:
- `sponsor_contacts`
- `sponsor_signals`
- `sponsor_score_breakdown`
- `sponsor_packages`
- `sponsor_approvals`
- `sponsor_webhook_events`
- `sponsor_experiments`
- `sponsor_tasks`
- `sponsor_replies`
- `sponsor_research_runs`

## Expand statuses
Current statuses are too coarse. Consider:
- prospect
- researching
- researched
- contact_enriched
- draft_pending_review
- draft_approved
- scheduled
- sent
- opened
- replied_positive
- replied_neutral
- replied_negative
- meeting_booked
- proposal_sent
- negotiating
- won
- lost
- nurture
- suppressed

## Add confidence fields everywhere
For research, contacts, scores, and package recommendations.

## Add policy engine
Before send:
- evidence sufficiency check
- contact verification check
- compliance check
- deliverability check
- approval check

## Add “next best action”
Every sponsor row should have:
- `next_best_action`
- `next_best_action_reason`
- `next_action_due_at`

---

# Final blunt assessment

This spec is a **good v1.5 internal automation tool**, but not yet a **world-class 2026 sponsor intelligence platform**.

To make it exceptional, the biggest leap is this:

**Stop thinking of it as “AI writes sponsor emails.”  
Start thinking of it as “an evidence-backed, multi-agent, account-based revenue operating system with closed-loop learning.”**

That means:
1. richer signals,
2. better contacts,
3. better timing,
4. better deliverability,
5. better learning,
6. better packaging,
7. better operator UX.

If you want, I can next turn this into a **revised 2026 gospel spec** with:
- upgraded architecture
- expanded DB schema
- event model
- agent definitions
- UI spec
- security/compliance section
- implementation phases
- acceptance criteria.