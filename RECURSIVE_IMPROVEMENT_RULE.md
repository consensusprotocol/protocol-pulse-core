# THE RECURSIVE IMPROVEMENT RULE
## Protocol Pulse Operating System

> Every automated system in Protocol Pulse has a skills file that gets updated weekly.
> This creates recursive, compounding improvement.
> The system gets smarter every Saturday.

---

## The Principle

Traditional media: same editorial instincts, decade after decade.
Protocol Pulse: every agent learns. Every Saturday, the system improves.

**The Rule:** Every automated system has two files:
1. A **soul file** (core instructions — who it is, what it does, its voice)
2. A **skills file** (learned best practices — what's working RIGHT NOW)

Skills files are **append-only logs**. New learnings stack on top.
The most recent entry is the most important.
The soul file never changes. The skills file always grows.

---

## Agent Inventory

| Agent | Soul File | Skills File | Update Frequency |
|-------|-----------|-------------|-----------------|
| Editorial | editorial_framework.py | (embedded) | On-demand |
| Thumbnail | thumbnail_agent.py | THUMBNAIL_SKILLS.md | Weekly (Saturday) |
| Sponsor Radar | sponsor_radar.py | SPONSOR_RADAR_REPORT.md | Weekly (Saturday) |
| Social | (TODO) social_agent.py | (TODO) SOCIAL_SKILLS.md | Weekly |
| SEO | (TODO) seo_agent.py | (TODO) SEO_SKILLS.md | Weekly |
| Article | (in routes.py) | (TODO) ARTICLE_SKILLS.md | Weekly |

---

## The Rule in Detail

### 1. Every agent has a soul file
The soul file is the agent's core identity:
- What it does
- Its voice and style
- Its decision framework
- Its output format

Soul files don't change. They define the agent's character.

### 2. Every agent has a skills file
The skills file is what the agent has LEARNED:
- Latest research in its domain
- What's working right now
- Specific numbers and data points
- Techniques from top practitioners

Skills files are **append-only**. Never delete. Never overwrite.
The history of learning is preserved. The most recent additions dominate.

### 3. Every Saturday, agents update their skills
The cron job runs. Each agent searches for the latest research.
Findings get appended to the skills file with a timestamp.
The next time the system runs, it uses the updated skills.

### 4. This creates recursive improvement
Week 1: Agent learns best practices circa Week 1
Week 4: Agent has 4 weeks of accumulated intelligence
Week 52: Agent has a year of compounding knowledge
Year 3: The agent knows more about its domain than any individual human

This is the Protocol Pulse competitive moat.

---

## Cron Schedule

```bash
# Thumbnail skills update — every Saturday 08:00 UTC
0 8 * * 6 cd /home/runner/protocol-pulse-core && python3 thumbnail_agent.py

# Sponsor radar scan — every Saturday 09:00 UTC
0 9 * * 6 cd /home/runner/protocol-pulse-core && python3 sponsor_radar.py
```

---

## The Philosophy

Media companies think about reach. Great media companies think about intelligence.

Protocol Pulse is building an **intelligence stack** that compounds:
- Every article improves the article generation system
- Every thumbnail improves the thumbnail brief system
- Every sponsor outreach improves the sponsor radar system
- Every Saturday, every agent gets smarter

In 12 months, Protocol Pulse's systems will be optimized by 52 rounds of recursive improvement.
No individual reporter, designer, or sales rep can match that.

**This is how we win.**

---

## Implementation Status

- [x] Thumbnail recursive agent (thumbnail_agent.py + THUMBNAIL_SKILLS.md)
- [x] Sponsor radar agent (sponsor_radar.py + SPONSOR_RADAR_REPORT.md)
- [x] Editorial framework (editorial_framework.py)
- [ ] Social agent (TODO — next session)
- [ ] SEO agent (TODO — next session)
- [ ] Article skills file (TODO — integrate with article generation)

---

*Document Version: 1.0 — Session 3 Build*
*Protocol Pulse — Intelligence for Transactors*
