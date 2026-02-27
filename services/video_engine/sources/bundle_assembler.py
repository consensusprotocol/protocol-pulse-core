"""
Source Bundle Assembler
========================
Combines all source data into a unified source_bundle.json.
This is the single input document for the editorial pipeline.

Sources:
  - YouTube transcripts (with word-level timestamps)
  - Notable tweets
  - Market snapshot
  - X Spaces (empty for now)
  - PP article headlines (from existing system)
"""
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger("BundleAssembler")


class SourceBundleAssembler:
    """Assemble all source data into source_bundle.json."""

    def __init__(self, bundle_path: Path, date_str: str = None):
        self.bundle_path = bundle_path
        self.date_str = date_str or datetime.utcnow().strftime("%Y-%m-%d")

    def assemble(self,
                 youtube_data: Dict[str, dict],
                 tweets: List[dict],
                 market_data: Dict,
                 spaces: List[dict] = None,
                 article_headlines: List[dict] = None) -> Dict:
        """
        Assemble all sources into a unified bundle.

        Args:
            youtube_data: {video_id: {channel_name, title, text, segments, words, ...}}
            tweets: list of notable tweet dicts
            market_data: market snapshot dict
            spaces: list of spaces dicts (empty for now)
            article_headlines: recent PP article headlines

        Returns: source_bundle dict
        """
        logger.info(f"\nAssembling source bundle for {self.date_str}...")

        # Build transcript summaries for the bundle
        transcripts = []
        for vid_id, tx_data in youtube_data.items():
            transcripts.append({
                "source_type": "youtube",
                "source_id": vid_id,
                "source_name": tx_data.get("channel_name", "Unknown"),
                "channel_handle": tx_data.get("channel_handle", ""),
                "title": tx_data.get("title", ""),
                "text": tx_data.get("text", ""),
                "timestamped_text": tx_data.get("timestamped_text", ""),
                "char_count": tx_data.get("char_count", 0),
                "segment_count": tx_data.get("segment_count", 0),
                "word_count": tx_data.get("word_count", 0),
                "has_word_timestamps": tx_data.get("has_word_timestamps", False),
            })

        # Build tweet digest
        tweet_digest = []
        for t in (tweets or []):
            tweet_digest.append({
                "source_type": "tweet",
                "source_id": t.get("tweet_id", ""),
                "author_handle": t.get("author_handle", ""),
                "author_name": t.get("author_name", ""),
                "text": t.get("text", ""),
                "likes": t.get("likes", 0),
                "retweets": t.get("retweets", 0),
                "url": t.get("url", ""),
            })

        bundle = {
            "date": self.date_str,
            "assembled_at": datetime.utcnow().isoformat(),
            "sources": {
                "youtube": {
                    "count": len(transcripts),
                    "transcripts": transcripts,
                },
                "tweets": {
                    "count": len(tweet_digest),
                    "tweets": tweet_digest,
                },
                "market": market_data or {},
                "spaces": {
                    "count": len(spaces or []),
                    "spaces": spaces or [],
                },
                "articles": {
                    "count": len(article_headlines or []),
                    "headlines": article_headlines or [],
                }
            },
            "stats": {
                "total_transcript_chars": sum(t["char_count"] for t in transcripts),
                "total_transcripts": len(transcripts),
                "total_tweets": len(tweet_digest),
                "total_spaces": len(spaces or []),
                "has_market_data": bool(market_data and market_data.get("price_usd")),
            }
        }

        # Save to bundle
        output_path = self.bundle_path / "inputs" / "source_bundle.json"
        output_path.write_text(json.dumps(bundle, indent=2, default=str))
        logger.info(f"  Source bundle saved: {output_path}")
        logger.info(f"    Transcripts: {len(transcripts)}")
        logger.info(f"    Tweets: {len(tweet_digest)}")
        logger.info(f"    Market data: {'yes' if bundle['stats']['has_market_data'] else 'no'}")

        return bundle

    def load_existing_articles(self, limit: int = 20) -> List[dict]:
        """Load recent article headlines from the PP database for context."""
        try:
            from app import app, db
            from models import Article

            with app.app_context():
                articles = Article.query.filter_by(published=True).order_by(
                    Article.published_at.desc()
                ).limit(limit).all()

                return [
                    {
                        "title": a.title,
                        "category": a.category,
                        "published_at": str(a.published_at) if a.published_at else "",
                        "source_type": a.source_type or "rss",
                    }
                    for a in articles
                ]
        except Exception as e:
            logger.debug(f"  Could not load PP articles: {e}")
            return []
