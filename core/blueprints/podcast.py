"""
SESSION 16 — CYPHERPUNK'D PODCAST PAGE
=======================================
Routes:
  GET  /podcast               → episode listing page
  GET  /podcast/<slug>        → individual episode page
  GET  /podcast/feed.xml      → valid RSS 2.0 + iTunes feed
  GET  /admin/podcast/add     → admin form to add episodes
  POST /admin/podcast/add     → create new episode

DB: podcast_episodes table (PodcastEpisode model)
Seed: 10 episodes auto-seeded on first startup if table is empty.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from email.utils import format_datetime

from flask import (
    Blueprint, abort, render_template, request, redirect,
    url_for, Response, flash
)
from flask_login import current_user

logger = logging.getLogger(__name__)

podcast_bp = Blueprint("podcast", __name__)

# ─── Seed data ────────────────────────────────────────────────────────────────

SEED_EPISODES = [
    {
        "slug": "knut-svanholm-bitcoin-philosophy",
        "title": "The Philosophy of Bitcoin Sovereignty",
        "episode_number": 1,
        "guest_name": "Knut Svanholm",
        "guest_bio": "Bitcoin author and philosopher. Author of 'Bitcoin: Everything Divided by 21 Million'.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder1",
        "duration": "1:12:34",
        "published_at": "2025-01-15",
        "show_notes": "Deep dive into Bitcoin as a philosophical breakthrough — why 21 million is not a number but a statement. Knut unpacks sovereignty, scarcity, and what it means to opt out of the fiat system.",
        "tags": '["philosophy", "sovereignty", "Bitcoin"]',
        "featured": True,
    },
    {
        "slug": "luke-dashjr-bitcoin-development",
        "title": "Bitcoin Core Development and the Road to 21M",
        "episode_number": 2,
        "guest_name": "Luke Dashjr",
        "guest_bio": "Bitcoin Core developer and vocal advocate for Bitcoin's fixed supply.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder2",
        "duration": "1:28:11",
        "published_at": "2025-02-01",
        "show_notes": "Luke discusses Bitcoin Core development priorities, the politics of consensus, and why the 21M cap is the most important line of code ever written.",
        "tags": '["development", "Bitcoin Core", "technical"]',
        "featured": False,
    },
    {
        "slug": "natalie-brunell-bitcoin-journalism",
        "title": "Bitcoin Journalism in the Age of Noise",
        "episode_number": 3,
        "guest_name": "Natalie Brunell",
        "guest_bio": "Bitcoin journalist and host of Coin Stories podcast.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder3",
        "duration": "58:22",
        "published_at": "2025-02-15",
        "show_notes": "How to cut through misinformation in crypto media. Natalie shares her approach to signal vs. noise and why Bitcoin-only journalism matters.",
        "tags": '["journalism", "media", "Bitcoin"]',
        "featured": True,
    },
    {
        "slug": "bruce-barone-bitcoin-mining-ops",
        "title": "Running a Bitcoin Mine in 2025",
        "episode_number": 4,
        "guest_name": "Bruce Barone Jr.",
        "guest_bio": "Bitcoin mining operator and entrepreneur.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder4",
        "duration": "1:05:44",
        "published_at": "2025-03-01",
        "show_notes": "The economics of running a Bitcoin mining operation post-halving. Bruce breaks down energy costs, hardware cycles, and what separates profitable miners from casualties.",
        "tags": '["mining", "operations", "energy"]',
        "featured": False,
    },
    {
        "slug": "joseph-welbourn-carbon-marine",
        "title": "Carbon Marine: Bitcoin on the High Seas",
        "episode_number": 5,
        "guest_name": "Joseph Welbourn",
        "guest_bio": "Founder of Carbon Marine, pioneering offshore Bitcoin mining.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder5",
        "duration": "1:18:03",
        "published_at": "2025-03-15",
        "show_notes": "Innovative approaches to Bitcoin mining using marine environments — stranded gas, offshore rigs, and the logistical frontier of energy arbitrage at sea.",
        "tags": '["mining", "innovation", "energy", "offshore"]',
        "featured": False,
    },
    {
        "slug": "michelle-weekley-bytefederal",
        "title": "ByteFederal: Bringing Bitcoin to the Streets",
        "episode_number": 6,
        "guest_name": "Michelle Weekley",
        "guest_bio": "Executive at ByteFederal, expanding Bitcoin ATM network across the US.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder6",
        "duration": "52:17",
        "published_at": "2025-04-01",
        "show_notes": "How ByteFederal is making Bitcoin accessible to every American through a growing ATM network. Michelle on regulatory hurdles, community adoption, and cash-to-Bitcoin flows.",
        "tags": '["adoption", "ATM", "retail", "accessibility"]',
        "featured": True,
    },
    {
        "slug": "bitcoin-sovereignty-panel-2025",
        "title": "The Sovereignty Panel: Living Off Bitcoin",
        "episode_number": 7,
        "guest_name": "Panel Discussion",
        "guest_bio": "Multiple guests discussing Bitcoin-native lifestyles.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder7",
        "duration": "1:45:22",
        "published_at": "2025-04-15",
        "show_notes": "Panel of Bitcoiners who have adopted Bitcoin as their primary financial tool. Real stories of circular economies, self-custody, and life beyond the banking system.",
        "tags": '["sovereignty", "panel", "lifestyle"]',
        "featured": False,
    },
    {
        "slug": "bitcoin-lightning-network-deep-dive",
        "title": "Lightning Network: State of Play 2025",
        "episode_number": 8,
        "guest_name": "Lightning Developer",
        "guest_bio": "Lightning Network developer and infrastructure builder.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder8",
        "duration": "1:22:55",
        "published_at": "2025-05-01",
        "show_notes": "Current state of Lightning Network adoption and development. Channel liquidity, routing economics, and the path to Bitcoin becoming internet money.",
        "tags": '["Lightning", "technical", "layer2"]',
        "featured": False,
    },
    {
        "slug": "bitcoin-etf-institutional-adoption",
        "title": "ETF Approval and What It Means for Bitcoin",
        "episode_number": 9,
        "guest_name": "Market Analyst",
        "guest_bio": "Institutional Bitcoin market analyst.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder9",
        "duration": "1:08:33",
        "published_at": "2025-05-15",
        "show_notes": "Deep analysis of Bitcoin ETF impact on market structure, custody flows, and whether institutional adoption strengthens or compromises Bitcoin's original promise.",
        "tags": '["ETF", "institutional", "markets"]',
        "featured": True,
    },
    {
        "slug": "bitcoin-halving-2024-aftermath",
        "title": "Post-Halving Bitcoin: What Comes Next",
        "episode_number": 10,
        "guest_name": "Bitcoin Economist",
        "guest_bio": "Bitcoin-focused economist and market researcher.",
        "youtube_url": "https://www.youtube.com/watch?v=placeholder10",
        "duration": "1:31:44",
        "published_at": "2025-06-01",
        "show_notes": "Analysis of post-halving market dynamics, miner capitulation cycles, and what Bitcoin economics tells us about the next four years.",
        "tags": '["halving", "economics", "markets"]',
        "featured": False,
    },
]


def _seed_episodes() -> None:
    """Seed podcast_episodes table with initial data if empty."""
    try:
        from app import db
        import models as m
        if m.PodcastEpisode.query.count() > 0:
            return
        for ep in SEED_EPISODES:
            pub = datetime.strptime(ep["published_at"], "%Y-%m-%d")
            obj = m.PodcastEpisode(
                slug=ep["slug"],
                title=ep["title"],
                episode_number=ep.get("episode_number"),
                guest_name=ep.get("guest_name"),
                guest_bio=ep.get("guest_bio"),
                youtube_url=ep.get("youtube_url"),
                duration=ep.get("duration"),
                published_at=pub,
                show_notes=ep.get("show_notes"),
                tags=ep.get("tags", "[]"),
                featured=ep.get("featured", False),
            )
            db.session.add(obj)
        db.session.commit()
        logger.info("Seeded %d podcast episodes", len(SEED_EPISODES))
    except Exception as exc:
        logger.warning("Podcast seed failed: %s", exc)


# ─── Routes ───────────────────────────────────────────────────────────────────

@podcast_bp.route("/podcast")
def podcast_index():
    """Episode listing — /podcast"""
    _seed_episodes()
    import models as m
    episodes = (
        m.PodcastEpisode.query
        .order_by(m.PodcastEpisode.episode_number.desc())
        .all()
    )
    featured = next((e for e in episodes if e.featured), None)
    return render_template(
        "podcast.html",
        episodes=episodes,
        featured=featured,
        page_title="CypherPunk'd Podcast",
    )


@podcast_bp.route("/podcast/feed.xml")
def podcast_feed():
    """Valid RSS 2.0 + iTunes podcast feed."""
    _seed_episodes()
    import models as m
    episodes = (
        m.PodcastEpisode.query
        .filter(m.PodcastEpisode.published_at.isnot(None))
        .order_by(m.PodcastEpisode.published_at.desc())
        .all()
    )
    xml = _build_rss(episodes)
    return Response(xml, mimetype="application/rss+xml; charset=utf-8")


@podcast_bp.route("/podcast/add", methods=["GET", "POST"])
def podcast_add():
    """Admin form to add a new episode — /podcast/add (login required)."""
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        abort(403)
    if request.method == "POST":
        _handle_add_form()
        return redirect(url_for("podcast.podcast_index"))
    return render_template("podcast_admin_add.html", page_title="Add Episode")


@podcast_bp.route("/podcast/<slug>")
def podcast_episode(slug: str):
    """Individual episode page — /podcast/<slug>"""
    _seed_episodes()
    import models as m
    ep = m.PodcastEpisode.query.filter_by(slug=slug).first_or_404()
    # Related: share at least one tag, exclude self, limit 3
    related = _get_related(ep, limit=3)
    return render_template(
        "podcast_episode.html",
        ep=ep,
        related=related,
        page_title=f"{ep.title} — CypherPunk'd",
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_related(ep, limit: int = 3):
    import models as m
    try:
        ep_tags = set(ep.tags_list)
        candidates = (
            m.PodcastEpisode.query
            .filter(m.PodcastEpisode.id != ep.id)
            .order_by(m.PodcastEpisode.episode_number.desc())
            .limit(50)
            .all()
        )
        scored = sorted(
            candidates,
            key=lambda c: len(ep_tags & set(c.tags_list)),
            reverse=True,
        )
        return scored[:limit]
    except Exception:
        return []


def _handle_add_form() -> None:
    from app import db
    import models as m
    f = request.form
    pub_str = f.get("published_at", "")
    try:
        pub = datetime.strptime(pub_str, "%Y-%m-%d") if pub_str else datetime.utcnow()
    except ValueError:
        pub = datetime.utcnow()
    tags_raw = f.get("tags", "")
    tags_json = json.dumps([t.strip() for t in tags_raw.split(",") if t.strip()])
    import re
    base_slug = re.sub(r"[^a-z0-9]+", "-", (f.get("title") or "episode").lower()).strip("-")
    slug = base_slug
    i = 2
    while m.PodcastEpisode.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{i}"
        i += 1
    obj = m.PodcastEpisode(
        slug=slug,
        title=f.get("title", ""),
        episode_number=int(f.get("episode_number") or 0) or None,
        guest_name=f.get("guest_name"),
        guest_bio=f.get("guest_bio"),
        youtube_url=f.get("youtube_url"),
        audio_url=f.get("audio_url"),
        duration=f.get("duration"),
        published_at=pub,
        show_notes=f.get("show_notes"),
        tags=tags_json,
        featured=bool(f.get("featured")),
        thumbnail_url=f.get("thumbnail_url"),
    )
    db.session.add(obj)
    db.session.commit()
    flash("Episode added successfully.", "success")


def _build_rss(episodes) -> str:
    items = ""
    for ep in episodes:
        pub_rfc = ""
        if ep.published_at:
            pub_rfc = ep.published_at.strftime("%a, %d %b %Y 12:00:00 +0000")
        audio = ep.audio_url or ep.youtube_url or ""
        enc = f'<enclosure url="{_xml_escape(audio)}" type="audio/mpeg" length="0"/>' if audio else ""
        items += f"""
    <item>
      <title>{_xml_escape(ep.title)}</title>
      <link>https://protocolpulse.io/podcast/{_xml_escape(ep.slug)}</link>
      <guid isPermaLink="true">https://protocolpulse.io/podcast/{_xml_escape(ep.slug)}</guid>
      <pubDate>{pub_rfc}</pubDate>
      <itunes:duration>{_xml_escape(ep.duration or '')}</itunes:duration>
      <description>{_xml_escape(ep.show_notes or '')}</description>
      <itunes:summary>{_xml_escape((ep.show_notes or '')[:200])}</itunes:summary>
      <itunes:episode>{ep.episode_number or ''}</itunes:episode>
      <itunes:author>Protocol Pulse</itunes:author>
      {enc}
    </item>"""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>CypherPunk'd</title>
    <description>The uncensored voice of Bitcoin sovereignty. Deep conversations with builders, thinkers, and freedom advocates on the frontier of sound money.</description>
    <link>https://protocolpulse.io/podcast</link>
    <language>en-us</language>
    <itunes:author>Protocol Pulse</itunes:author>
    <itunes:owner>
      <itunes:name>Protocol Pulse</itunes:name>
      <itunes:email>hello@protocolpulse.io</itunes:email>
    </itunes:owner>
    <itunes:category text="Technology"/>
    <itunes:category text="Business">
      <itunes:category text="Investing"/>
    </itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
    <image>
      <url>https://protocolpulse.io/static/images/podcast-cover.jpg</url>
      <title>CypherPunk'd</title>
      <link>https://protocolpulse.io/podcast</link>
    </image>
    <itunes:image href="https://protocolpulse.io/static/images/podcast-cover.jpg"/>
    {items}
  </channel>
</rss>"""


def _xml_escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
