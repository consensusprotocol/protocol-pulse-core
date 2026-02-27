#!/usr/bin/env python3
"""
Continuous article generation loop - runs every 15 minutes
"""
import time
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def run_generation():
    """Run the article generation script"""
    try:
        result = subprocess.run(
            ['python3', 'generate_article_now.py'],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            logging.info("✅ Article generated successfully")
        else:
            logging.error(f"❌ Generation failed: {result.stderr[:200]}")
    except Exception as e:
        logging.error(f"❌ Error running generation: {e}")

if __name__ == '__main__':
    logging.info("🚀 Starting automated article generation (every 15 minutes)")
    
    # Generate first article immediately
    logging.info("📰 Generating initial article...")
    run_generation()
    
    # Loop forever, generating every 15 minutes
    while True:
        try:
            logging.info(f"⏰ Waiting 15 minutes until {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(900)  # 15 minutes = 900 seconds
            
            logging.info("📰 Generating new article...")
            run_generation()
            
        except KeyboardInterrupt:
            logging.info("⏹️  Automation stopped")
            break
        except Exception as e:
            logging.error(f"❌ Loop error: {e}")
            time.sleep(60)  # Wait 1 minute before retry
