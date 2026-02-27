
import schedule
import time
import random
import logging
from datetime import datetime
from app import app, db
from models import Article
from services.content_generator import ContentGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_scheduler():
    logging.info('🚀 Protocol Pulse Content Scheduler Test Started')
    logging.info('📰 Generating every 15 minutes')
    
    generator = ContentGenerator()
    BREAKING_TOPICS = [
        'Bitcoin mining difficulty reaches new all-time high as hash rate surges',
        'Major institutional investors allocate billions to Bitcoin treasury reserves', 
        'Lightning Network payment volume breaks monthly records'
    ]
    
    with app.app_context():
        try:
            topic = random.choice(BREAKING_TOPICS)
            logging.info(f'🔄 Generating test article: {topic[:50]}...')
            
            article_data = generator.generate_article(
                topic=topic,
                content_type='breaking_news',
                source_type='scheduler_test'
            )
            
            if article_data:
                article = Article()
                article.title = article_data['title']
                article.content = article_data['content']
                article.category = 'Test'
                article.tags = 'scheduler,test,automated'
                article.author = 'Al Ingle'
                article.published = False  # Test mode
                article.featured = False
                db.session.add(article)
                db.session.commit()
                
                logging.info(f'✅ Scheduler test successful: Generated article ID {article.id}')
                logging.info(f'📰 Title: {article.title}')
                return True
            else:
                logging.error('❌ Failed to generate test article')
                return False
                
        except Exception as e:
            logging.error(f'❌ Scheduler test error: {str(e)}')
            return False

if __name__ == '__main__':
    success = test_scheduler()
    print(f'Scheduler test result: {"SUCCESS" if success else "FAILED"}')
