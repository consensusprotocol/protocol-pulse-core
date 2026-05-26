from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from typing import Iterable, List, Optional, Sequence


@dataclass(frozen=True)
class SitemapEntry:
    path: str
    changefreq: str = "weekly"
    priority: str = "0.6"
    lastmod: Optional[datetime] = None


class SEOEngine:
    """Central SEO helpers for sitemap XML and social/meta tag payloads."""

    def __init__(self, site_name: str = "Protocol Pulse", default_locale: str = "en_US") -> None:
        self.site_name = site_name
        self.default_locale = default_locale

    def build_sitemap_xml(self, base_url: str, entries: Sequence[SitemapEntry]) -> str:
        base = (base_url or "").rstrip("/")
        lines: List[str] = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

        for entry in entries:
            path = entry.path if entry.path.startswith("/") else f"/{entry.path}"
            loc = f"{base}{path}"
            lastmod = ""
            if entry.lastmod:
                lastmod = f"<lastmod>{entry.lastmod.strftime('%Y-%m-%d')}</lastmod>"
            lines.append(
                "  <url>"
                f"<loc>{escape(loc)}</loc>"
                f"<changefreq>{escape(entry.changefreq)}</changefreq>"
                f"<priority>{escape(entry.priority)}</priority>"
                f"{lastmod}"
                "</url>"
            )

        lines.append("</urlset>")
        return "\n".join(lines)

    def default_sitemap_entries(self) -> List[SitemapEntry]:
        return [
            SitemapEntry("/", "daily", "1.0"),
            SitemapEntry("/articles", "daily", "0.9"),
            SitemapEntry("/dossier", "weekly", "0.9"),
            SitemapEntry("/live", "daily", "0.8"),
            SitemapEntry("/signal-terminal", "daily", "0.8"),
            SitemapEntry("/whale-watcher", "daily", "0.8"),
            SitemapEntry("/map", "weekly", "0.7"),
            SitemapEntry("/about", "monthly", "0.5"),
            SitemapEntry("/contact", "monthly", "0.5"),
            SitemapEntry("/donate", "monthly", "0.5"),
            SitemapEntry("/premium", "monthly", "0.6"),
            SitemapEntry("/privacy-policy", "monthly", "0.3"),
        ]

    def article_sitemap_entries(self, articles: Iterable[object]) -> List[SitemapEntry]:
        article_entries: List[SitemapEntry] = []
        for article in articles:
            article_id = getattr(article, "id", None)
            if article_id is None:
                continue
            lastmod = getattr(article, "updated_at", None) or getattr(article, "created_at", None)
            article_entries.append(
                SitemapEntry(
                    path=f"/articles/{article_id}",
                    changefreq="weekly",
                    priority="0.7",
                    lastmod=lastmod,
                )
            )
        return article_entries

    def build_meta_tags(
        self,
        *,
        title: str,
        description: str,
        url: str,
        image_url: Optional[str] = None,
        site_name: Optional[str] = None,
        content_type: str = "website",
        twitter_card: str = "summary_large_image",
        canonical_url: Optional[str] = None,
    ) -> List[dict]:
        site = site_name or self.site_name
        clean_title = (title or site).strip()
        clean_description = (description or "").strip()
        clean_url = (url or "").strip()
        clean_image = (image_url or "").strip()
        canonical = (canonical_url or clean_url).strip()

        tags = [
            {"tag": "title", "content": clean_title},
            {"tag": "meta", "name": "description", "content": clean_description},
            {"tag": "meta", "property": "og:title", "content": clean_title},
            {"tag": "meta", "property": "og:description", "content": clean_description},
            {"tag": "meta", "property": "og:url", "content": clean_url},
            {"tag": "meta", "property": "og:type", "content": content_type},
            {"tag": "meta", "property": "og:site_name", "content": site},
            {"tag": "meta", "property": "og:locale", "content": self.default_locale},
            {"tag": "meta", "name": "twitter:card", "content": twitter_card},
            {"tag": "meta", "name": "twitter:title", "content": clean_title},
            {"tag": "meta", "name": "twitter:description", "content": clean_description},
            {"tag": "link", "rel": "canonical", "href": canonical},
        ]
        if clean_image:
            tags.append({"tag": "meta", "property": "og:image", "content": clean_image})
            tags.append({"tag": "meta", "name": "twitter:image", "content": clean_image})
        return tags
