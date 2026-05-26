#!/usr/bin/env python3
import time
import schedule
import logging
import os
import sys

# Setup logging
logging.basicConfig(level=logging.INFO)

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pp_services.scheduler import generate_scheduled_article, run_social_monitoring, maintain_featured_count, archive_old_articles

# Schedule automated content generation
schedule.every(15).minutes.do(generate_scheduled_article)  # Breaking news every 15 minutes
schedule.every(2).hours.do(run_social_monitoring)         # Social monitoring every 2 hours  
schedule.every(6).hours.do(maintain_featured_count)       # Homepage maintenance every 6 hours
schedule.every(1).days.do(archive_old_articles)          # Daily archiving

def run_automation():
    """Run the automation scheduler continuously"""
    logging.info("🚀 Protocol Pulse LIVE AUTOMATION Started!")
    logging.info("📰 Breaking news: Every 15 minutes")
    logging.info("📱 Social monitoring: Every 2 hours")
    logging.info("🔄 Homepage maintenance: Every 6 hours")
    logging.info("📁 Daily archiving: Every 24 hours")
    
    # Generate first article immediately
    try:
        logging.info("🔥 Generating initial breaking news article...")
        generate_scheduled_article()
        logging.info("✅ Initial article generated successfully!")
    except Exception as e:
        logging.error(f"❌ Initial generation failed: {e}")
    
    # Run scheduler loop
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logging.info("⏹️ Automation stopped by user")
            break
        except Exception as e:
            logging.error(f"❌ Automation error: {e}")
            time.sleep(300)  # Wait 5 minutes before retrying

if __name__ == '__main__':
    run_automation()