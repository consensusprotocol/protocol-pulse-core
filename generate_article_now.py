#!/usr/bin/env python3
"""
Simple script to generate a single article immediately
Can be run from cron or manually
"""
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Article
from pp_services.content_generator import ContentGenerator
import random
import logging

logging.basicConfig(level=logging.INFO)

# Breaking news topics
TOPICS = [
    "Bitcoin mining difficulty reaches new all-time high as hash rate surges",
    "Major institutional investors allocate billions to Bitcoin treasury reserves", 
    "Lightning Network payment volume breaks monthly records",
    "DeFi protocols implement revolutionary new yield farming mechanisms",
    "Central banks accelerate CBDC development in response to Bitcoin adoption",
    "Major corporations announce Bitcoin payment integration plans",
    "Renewable energy Bitcoin mining initiatives expand globally",
    "DeFi total value locked reaches new milestone despite market volatility",
    "Bitcoin ETF inflows surge as retail and institutional demand grows",
    "Layer 2 scaling solutions see unprecedented adoption rates"
]

def generate_article():
    """Generate a single breaking news article"""
    with app.app_context():
        try:
            generator = ContentGenerator()
            topic = random.choice(TOPICS)
            
            logging.info(f"🔥 Generating article: {topic}")
            
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='ai_generated'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.summary = ""
                article.category = article_data.get('category', 'Bitcoin')
                article.tags = article_data.get('tags', 'bitcoin,breaking,news')
                article.author = "Al Ingle"
                article.seo_title = article_data.get('seo_title', article_data['title'])
                article.seo_description = article_data.get('seo_description', article_data['title'][:150])
                article.published = True
                article.featured = True
                db.session.add(article)
                db.session.commit()
                
                logging.info(f"✅ Article created: {article.title}")
                
                # Auto-publish to Substack
                try:
                    from pp_services.substack_service import SubstackService
                    substack_service = SubstackService()
                    newsletter_content = substack_service.format_content_for_newsletter(article.content, 'bitcoin')
                    substack_url = substack_service.publish_to_substack(article.title, newsletter_content, article.header_image_url)
                    
                    if substack_url:
                        article.substack_url = substack_url
                        db.session.commit()
                        logging.info(f"🚀 Published to Substack: {substack_url}")
                except Exception as e:
                    logging.error(f"❌ Substack error: {e}")
                
                return True
            else:
                logging.error("❌ No article data generated")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = generate_article()
    sys.exit(0 if success else 1)
