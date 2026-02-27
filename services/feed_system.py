"""
feed_system.py - Comprehensive Feed System for Protocol Pulse

Generates RSS 2.0, Atom 1.0, iTunes Podcast RSS, JSON Feed 1.1,
and OPML exports for the Protocol Pulse Bitcoin intelligence platform.

Usage:
    from services.feed_system import (
        generate_rss_feed,
        generate_atom_feed,
        generate_podcast_feed,
        generate_json_feed,
        generate_opml,
    )
"""

import os
import logging
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from app import db, app
from models import Article, Podcast

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _site_url():
    """Return the canonical site URL (no trailing slash)."""
    return app.config.get("SITE_URL",
                          os.environ.get("SITE_URL", "https://protocolpulse.io")).rstrip("/")


def _rfc822(dt):
    """Format a datetime as RFC-822 (used by RSS 2.0 pubDate)."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


def _iso8601(dt):
    """Format a datetime as ISO-8601 / RFC-3339 (used by Atom & JSON Feed)."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _prettify_xml(element):
    """Return a pretty-printed XML string for an Element."""
    rough = tostring(element, encoding="unicode")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding=None)


def _article_url(article, base_url=None):
    """Build the canonical URL for an article."""
    base = base_url or _site_url()
    return f"{base}/articles/{article.id}"


def _podcast_url(podcast, base_url=None):
    """Build the canonical URL for a podcast episode page."""
    base = base_url or _site_url()
    return f"{base}/podcasts/{podcast.id}"


def _get_published_articles(limit=50):
    """Fetch the latest published articles ordered by published_at DESC."""
    try:
        return (
            Article.query
            .filter_by(published=True)
            .order_by(Article.published_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as exc:
        logger.error("Failed to fetch published articles: %s", exc)
        return []


def _get_podcasts(limit=50):
    """Fetch the latest podcast episodes ordered by published_date DESC."""
    try:
        return (
            Podcast.query
            .order_by(Podcast.published_date.desc())
            .limit(limit)
            .all()
        )
    except Exception as exc:
        logger.error("Failed to fetch podcasts: %s", exc)
        return []


def _safe(value, default=""):
    """Return *value* if truthy, otherwise *default*."""
    return value if value else default


def _cdata(text):
    """Wrap text in a CDATA section string.

    ElementTree does not natively support CDATA, so we inject a sentinel
    during tree construction and replace it after serialisation.
    """
    if not text:
        return ""
    # Replace any existing CDATA end markers to prevent injection
    safe_text = text.replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe_text}]]>"


_CDATA_SENTINEL = "___CDATA_START___"
_CDATA_SENTINEL_END = "___CDATA_END___"


def _set_cdata_text(element, text):
    """Set the text of *element* using CDATA.

    We store sentinels that get replaced in the final XML string
    after pretty-printing, because ElementTree escapes angle brackets.
    """
    if not text:
        element.text = ""
        return
    safe_text = text.replace("]]>", "]]]]><![CDATA[>")
    element.text = f"{_CDATA_SENTINEL}{safe_text}{_CDATA_SENTINEL_END}"


def _inject_cdata(xml_string):
    """Replace CDATA sentinels with real CDATA sections in the final XML."""
    return (
        xml_string
        .replace(_CDATA_SENTINEL, "<![CDATA[")
        .replace(_CDATA_SENTINEL_END, "]]>")
    )


def _audio_mime_type(url):
    """Guess MIME type from an audio URL."""
    if not url:
        return "audio/mpeg"
    url_lower = url.lower()
    if url_lower.endswith(".m4a"):
        return "audio/x-m4a"
    if url_lower.endswith(".ogg"):
        return "audio/ogg"
    if url_lower.endswith(".wav"):
        return "audio/wav"
    if url_lower.endswith(".aac"):
        return "audio/aac"
    return "audio/mpeg"


# ---------------------------------------------------------------------------
# 1. RSS 2.0 Feed (Articles)
# ---------------------------------------------------------------------------

def generate_rss_feed():
    """Generate an RSS 2.0 XML feed of the latest published articles.

    Includes ``dc:creator`` and ``content:encoded`` namespaces with full
    HTML article content wrapped in CDATA sections.

    Returns:
        str: Complete RSS 2.0 XML document as a string.
    """
    base_url = _site_url()
    articles = _get_published_articles(limit=50)
    now = datetime.utcnow()

    rss = Element("rss", version="2.0")
    rss.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")

    channel = SubElement(rss, "channel")

    # -- Channel metadata --
    SubElement(channel, "title").text = "Protocol Pulse"
    SubElement(channel, "link").text = base_url
    SubElement(channel, "description").text = (
        "Bitcoin intelligence, on-chain analysis, and cypherpunk insights "
        "delivered by Protocol Pulse."
    )
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "copyright").text = f"\u00a9 {now.year} Protocol Pulse"
    SubElement(channel, "pubDate").text = _rfc822(now)
    SubElement(channel, "lastBuildDate").text = _rfc822(now)
    SubElement(channel, "generator").text = "Protocol Pulse Feed System"

    # Self-referencing Atom link (best practice for RSS readers)
    atom_self = SubElement(channel, "atom:link")
    atom_self.set("href", f"{base_url}/feeds/rss")
    atom_self.set("rel", "self")
    atom_self.set("type", "application/rss+xml")

    # -- Items --
    for article in articles:
        item = SubElement(channel, "item")

        SubElement(item, "title").text = _safe(article.title, "Untitled")

        article_link = _article_url(article, base_url)
        SubElement(item, "link").text = article_link

        # description -- full HTML content in CDATA
        desc = SubElement(item, "description")
        _set_cdata_text(desc, _safe(article.content, article.summary or ""))

        # content:encoded -- full HTML content in CDATA
        content_encoded = SubElement(item, "content:encoded")
        _set_cdata_text(content_encoded, _safe(article.content, ""))

        SubElement(item, "pubDate").text = _rfc822(
            article.published_at or article.created_at
        )

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "true")
        guid.text = article_link

        # Category
        if article.category:
            SubElement(item, "category").text = article.category

        # Tags as additional categories
        if article.tags:
            for tag in article.tags.split(","):
                tag = tag.strip()
                if tag:
                    SubElement(item, "category").text = tag

        # dc:creator (author)
        SubElement(item, "dc:creator").text = _safe(
            article.author, "Protocol Pulse AI"
        )

        SubElement(item, "author").text = _safe(
            article.author, "Protocol Pulse AI"
        )

    xml_str = _prettify_xml(rss)
    # Inject real CDATA sections
    xml_str = _inject_cdata(xml_str)
    return xml_str


# ---------------------------------------------------------------------------
# 2. Atom 1.0 Feed (Articles)
# ---------------------------------------------------------------------------

def generate_atom_feed():
    """Generate an Atom 1.0 XML feed of the latest published articles.

    Returns:
        str: Complete Atom 1.0 XML document as a string.
    """
    base_url = _site_url()
    articles = _get_published_articles(limit=50)
    now = datetime.utcnow()

    feed = Element("feed")
    feed.set("xmlns", "http://www.w3.org/2005/Atom")

    SubElement(feed, "title").text = "Protocol Pulse"
    SubElement(feed, "subtitle").text = (
        "Bitcoin intelligence, on-chain analysis, and cypherpunk insights."
    )

    link_self = SubElement(feed, "link")
    link_self.set("href", f"{base_url}/feeds/atom")
    link_self.set("rel", "self")
    link_self.set("type", "application/atom+xml")

    link_alt = SubElement(feed, "link")
    link_alt.set("href", base_url)
    link_alt.set("rel", "alternate")
    link_alt.set("type", "text/html")

    SubElement(feed, "id").text = f"{base_url}/"
    SubElement(feed, "updated").text = _iso8601(now)
    SubElement(feed, "generator").text = "Protocol Pulse Feed System"
    SubElement(feed, "rights").text = f"\u00a9 {now.year} Protocol Pulse"

    # Feed-level author
    author = SubElement(feed, "author")
    SubElement(author, "name").text = "Protocol Pulse"
    SubElement(author, "uri").text = base_url

    # -- Entries --
    for article in articles:
        entry = SubElement(feed, "entry")

        SubElement(entry, "title").text = _safe(article.title, "Untitled")

        article_link = _article_url(article, base_url)

        link_el = SubElement(entry, "link")
        link_el.set("href", article_link)
        link_el.set("rel", "alternate")
        link_el.set("type", "text/html")

        SubElement(entry, "id").text = article_link

        pub_dt = article.published_at or article.created_at or now
        updated_dt = getattr(article, "updated_at", None) or pub_dt
        SubElement(entry, "published").text = _iso8601(pub_dt)
        SubElement(entry, "updated").text = _iso8601(updated_dt)

        # Author
        entry_author = SubElement(entry, "author")
        SubElement(entry_author, "name").text = _safe(
            article.author, "Protocol Pulse AI"
        )

        # Summary (plain text excerpt)
        if article.summary:
            summary_el = SubElement(entry, "summary")
            summary_el.set("type", "text")
            summary_el.text = article.summary

        # Content (full HTML)
        if article.content:
            content_el = SubElement(entry, "content")
            content_el.set("type", "html")
            _set_cdata_text(content_el, article.content)

        # Categories
        if article.category:
            cat_el = SubElement(entry, "category")
            cat_el.set("term", article.category)
            cat_el.set("label", article.category)

        if article.tags:
            for tag in article.tags.split(","):
                tag = tag.strip()
                if tag:
                    tag_el = SubElement(entry, "category")
                    tag_el.set("term", tag)
                    tag_el.set("label", tag)

    xml_str = _prettify_xml(feed)
    xml_str = _inject_cdata(xml_str)
    return xml_str


# ---------------------------------------------------------------------------
# 3. iTunes-Compatible Podcast RSS Feed
# ---------------------------------------------------------------------------

def generate_podcast_feed():
    """Generate an iTunes / Apple Podcasts compatible RSS feed.

    Includes all required iTunes namespace tags so the feed is
    submission-ready for Apple Podcasts, Spotify, and Google Podcasts.

    Returns:
        str: Complete podcast RSS XML document as a string.
    """
    base_url = _site_url()
    podcasts = _get_podcasts(limit=50)
    now = datetime.utcnow()

    rss = Element("rss", version="2.0")
    rss.set("xmlns:itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    rss.set("xmlns:atom", "http://www.w3.org/2005/Atom")
    rss.set("xmlns:podcast", "https://podcastindex.org/namespace/1.0")
    rss.set("xmlns:dc", "http://purl.org/dc/elements/1.1/")

    channel = SubElement(rss, "channel")

    # -- Channel metadata --
    SubElement(channel, "title").text = "Protocol Pulse Podcast"
    SubElement(channel, "link").text = f"{base_url}/podcasts"
    SubElement(channel, "description").text = (
        "Bitcoin intelligence, on-chain analysis, and cypherpunk insights "
        "delivered by Protocol Pulse. Your ears on the blockchain."
    )
    SubElement(channel, "language").text = "en-us"
    SubElement(channel, "copyright").text = f"\u00a9 {now.year} Protocol Pulse"
    SubElement(channel, "pubDate").text = _rfc822(now)
    SubElement(channel, "lastBuildDate").text = _rfc822(now)
    SubElement(channel, "generator").text = "Protocol Pulse Feed System"

    # Atom self-link
    atom_self = SubElement(channel, "atom:link")
    atom_self.set("href", f"{base_url}/feeds/podcast")
    atom_self.set("rel", "self")
    atom_self.set("type", "application/rss+xml")

    # -- iTunes channel tags --
    SubElement(channel, "itunes:author").text = "Protocol Pulse"
    SubElement(channel, "itunes:summary").text = (
        "Bitcoin intelligence, on-chain analysis, and cypherpunk insights "
        "delivered by Protocol Pulse."
    )
    SubElement(channel, "itunes:type").text = "episodic"
    SubElement(channel, "itunes:explicit").text = "false"

    itunes_owner = SubElement(channel, "itunes:owner")
    SubElement(itunes_owner, "itunes:name").text = "Protocol Pulse"
    SubElement(itunes_owner, "itunes:email").text = "podcast@protocolpulse.io"

    itunes_image = SubElement(channel, "itunes:image")
    itunes_image.set("href", f"{base_url}/static/images/podcast-cover.png")

    itunes_category = SubElement(channel, "itunes:category")
    itunes_category.set("text", "Technology")
    itunes_sub = SubElement(itunes_category, "itunes:category")
    itunes_sub.set("text", "Cryptocurrency")

    # Additional category for broader discovery
    itunes_category2 = SubElement(channel, "itunes:category")
    itunes_category2.set("text", "News")
    itunes_sub2 = SubElement(itunes_category2, "itunes:category")
    itunes_sub2.set("text", "Tech News")

    # -- Episodes --
    for podcast in podcasts:
        item = SubElement(channel, "item")

        SubElement(item, "title").text = _safe(podcast.title, "Untitled Episode")

        episode_link = _podcast_url(podcast, base_url)
        SubElement(item, "link").text = episode_link

        # Description in CDATA
        desc = SubElement(item, "description")
        _set_cdata_text(desc, _safe(podcast.description, ""))

        # content:encoded
        content_encoded = SubElement(item, "content:encoded")
        _set_cdata_text(content_encoded, _safe(podcast.description, ""))

        pub_dt = podcast.published_date or now
        SubElement(item, "pubDate").text = _rfc822(pub_dt)

        guid = SubElement(item, "guid")
        guid.set("isPermaLink", "false")
        guid.text = f"protocolpulse-podcast-{podcast.id}"

        # dc:creator
        SubElement(item, "dc:creator").text = _safe(podcast.host, "Protocol Pulse")

        # -- Enclosure (audio file) --
        if podcast.audio_url:
            enclosure = SubElement(item, "enclosure")
            enclosure.set("url", podcast.audio_url)
            enclosure.set("type", _audio_mime_type(podcast.audio_url))
            enclosure.set("length", "0")  # Length unknown without HEAD request

        # -- iTunes episode tags --
        SubElement(item, "itunes:author").text = _safe(podcast.host, "Protocol Pulse")
        SubElement(item, "itunes:summary").text = _safe(podcast.description, "")[:4000]
        SubElement(item, "itunes:explicit").text = "false"

        if podcast.duration:
            SubElement(item, "itunes:duration").text = str(podcast.duration)

        if podcast.episode_number:
            SubElement(item, "itunes:episode").text = str(podcast.episode_number)
            SubElement(item, "itunes:episodeType").text = "full"

        # Season -- model does not have season_number, default to 1 if episodes exist
        season = getattr(podcast, "season_number", None)
        if season:
            SubElement(item, "itunes:season").text = str(season)

        # Episode cover image
        if podcast.cover_image_url:
            ep_image = SubElement(item, "itunes:image")
            ep_image.set("href", podcast.cover_image_url)

        # podcast:transcript (if model ever gains a transcript_url field)
        transcript_url = getattr(podcast, "transcript_url", None)
        if transcript_url:
            transcript_el = SubElement(item, "podcast:transcript")
            transcript_el.set("url", transcript_url)
            transcript_el.set("type", "text/plain")

        # Category
        if podcast.category:
            SubElement(item, "category").text = podcast.category

    xml_str = _prettify_xml(rss)
    xml_str = _inject_cdata(xml_str)
    return xml_str


# ---------------------------------------------------------------------------
# 4. JSON Feed 1.1
# ---------------------------------------------------------------------------

def generate_json_feed():
    """Generate a JSON Feed 1.1 representation of published articles.

    Returns:
        dict: A Python dictionary matching the JSON Feed 1.1 specification.
              The caller should serialise it with ``json.dumps()`` when
              serving an HTTP response.
    """
    base_url = _site_url()
    articles = _get_published_articles(limit=50)

    items = []
    for article in articles:
        article_link = _article_url(article, base_url)
        pub_dt = article.published_at or article.created_at

        entry = {
            "id": article_link,
            "url": article_link,
            "title": _safe(article.title, "Untitled"),
            "content_html": _safe(article.content, ""),
            "date_published": _iso8601(pub_dt),
        }

        # Optional fields
        if article.summary:
            entry["summary"] = article.summary

        updated_dt = getattr(article, "updated_at", None)
        if updated_dt:
            entry["date_modified"] = _iso8601(updated_dt)

        if article.author:
            entry["authors"] = [{"name": article.author}]
        else:
            entry["authors"] = [{"name": "Protocol Pulse AI"}]

        tags = []
        if article.category:
            tags.append(article.category)
        if article.tags:
            tags.extend(t.strip() for t in article.tags.split(",") if t.strip())
        if tags:
            entry["tags"] = tags

        image_url = getattr(article, "header_image_url", None)
        if image_url:
            entry["image"] = image_url
            entry["banner_image"] = image_url

        items.append(entry)

    feed = {
        "version": "https://jsonfeed.org/version/1.1",
        "title": "Protocol Pulse",
        "home_page_url": base_url,
        "feed_url": f"{base_url}/feeds/json",
        "description": (
            "Bitcoin intelligence, on-chain analysis, and cypherpunk insights "
            "delivered by Protocol Pulse."
        ),
        "language": "en-US",
        "authors": [
            {
                "name": "Protocol Pulse",
                "url": base_url,
            }
        ],
        "items": items,
    }

    icon_url = f"{base_url}/static/images/favicon.png"
    feed["icon"] = icon_url
    feed["favicon"] = icon_url

    return feed


# ---------------------------------------------------------------------------
# 5. OPML Export
# ---------------------------------------------------------------------------

def generate_opml():
    """Generate an OPML document listing all available Protocol Pulse feeds.

    Returns:
        str: Complete OPML XML document as a string.
    """
    base_url = _site_url()
    now = datetime.utcnow()

    opml = Element("opml", version="2.0")

    head = SubElement(opml, "head")
    SubElement(head, "title").text = "Protocol Pulse Feeds"
    SubElement(head, "dateCreated").text = _rfc822(now)
    SubElement(head, "dateModified").text = _rfc822(now)
    SubElement(head, "ownerName").text = "Protocol Pulse"
    SubElement(head, "ownerEmail").text = "feeds@protocolpulse.io"

    body = SubElement(opml, "body")

    # Group: Articles
    articles_group = SubElement(body, "outline")
    articles_group.set("text", "Protocol Pulse Articles")
    articles_group.set("title", "Protocol Pulse Articles")

    rss_outline = SubElement(articles_group, "outline")
    rss_outline.set("type", "rss")
    rss_outline.set("text", "Protocol Pulse (RSS 2.0)")
    rss_outline.set("title", "Protocol Pulse (RSS 2.0)")
    rss_outline.set("xmlUrl", f"{base_url}/feeds/rss")
    rss_outline.set("htmlUrl", base_url)

    atom_outline = SubElement(articles_group, "outline")
    atom_outline.set("type", "rss")
    atom_outline.set("text", "Protocol Pulse (Atom)")
    atom_outline.set("title", "Protocol Pulse (Atom)")
    atom_outline.set("xmlUrl", f"{base_url}/feeds/atom")
    atom_outline.set("htmlUrl", base_url)

    json_outline = SubElement(articles_group, "outline")
    json_outline.set("type", "rss")
    json_outline.set("text", "Protocol Pulse (JSON Feed)")
    json_outline.set("title", "Protocol Pulse (JSON Feed)")
    json_outline.set("xmlUrl", f"{base_url}/feeds/json")
    json_outline.set("htmlUrl", base_url)

    # Group: Podcast
    podcast_group = SubElement(body, "outline")
    podcast_group.set("text", "Protocol Pulse Podcast")
    podcast_group.set("title", "Protocol Pulse Podcast")

    podcast_outline = SubElement(podcast_group, "outline")
    podcast_outline.set("type", "rss")
    podcast_outline.set("text", "Protocol Pulse Podcast (iTunes RSS)")
    podcast_outline.set("title", "Protocol Pulse Podcast (iTunes RSS)")
    podcast_outline.set("xmlUrl", f"{base_url}/feeds/podcast")
    podcast_outline.set("htmlUrl", f"{base_url}/podcasts")

    return _prettify_xml(opml)
