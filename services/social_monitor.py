"""
Social Media & Website Monitoring Service
Monitors Twitter handles, Reddit threads, and websites like CoinDesk
"""
import os
import time
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import tweepy
import praw
import trafilatura
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import base64
from io import BytesIO
from PIL import Image

class SocialMonitor:
    def __init__(self):
        """Initialize social media monitoring service"""
        self.setup_twitter()
        self.setup_reddit()
        self.setup_selenium()
        self.monitored_handles = []
        self.monitored_threads = []
        self.monitored_websites = []
        
    def setup_twitter(self):
        """Initialize Twitter API connection"""
        try:
            # Using existing Twitter/X API credentials from environment
            auth = tweepy.OAuthHandler(
                os.getenv('TWITTER_API_KEY'),
                os.getenv('TWITTER_API_SECRET')
            )
            auth.set_access_token(
                os.getenv('TWITTER_ACCESS_TOKEN'),
                os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
            )
            self.twitter_api = tweepy.API(auth, wait_on_rate_limit=True)
            logging.info("Twitter API initialized successfully")
        except Exception as e:
            logging.warning(f"Twitter API setup failed: {e}")
            self.twitter_api = None
    
    def setup_reddit(self):
        """Initialize Reddit API connection"""
        try:
            self.reddit = praw.Reddit(
                client_id=os.getenv('REDDIT_CLIENT_ID'),
                client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
                user_agent=os.getenv('REDDIT_USER_AGENT')
            )
            logging.info("Reddit API initialized successfully")
        except Exception as e:
            logging.warning(f"Reddit API setup failed: {e}")
            self.reddit = None
    
    def setup_selenium(self):
        """Initialize Selenium for screenshot capabilities"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1200,800')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            logging.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logging.warning(f"Selenium setup failed: {e}")
            self.driver = None
    
    def add_twitter_handle(self, handle: str, keywords: Optional[List[str]] = None):
        """Add Twitter handle to monitoring list"""
        if not handle.startswith('@'):
            handle = f'@{handle}'
        
        monitor_config = {
            'handle': handle,
            'keywords': keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True
        }
        self.monitored_handles.append(monitor_config)
        logging.info(f"Added Twitter handle {handle} to monitoring")
        return monitor_config
    
    def add_reddit_thread(self, subreddit: str, thread_keywords: Optional[List[str]] = None):
        """Add Reddit subreddit/thread to monitoring list"""
        monitor_config = {
            'subreddit': subreddit,
            'keywords': thread_keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True
        }
        self.monitored_threads.append(monitor_config)
        logging.info(f"Added Reddit subreddit r/{subreddit} to monitoring")
        return monitor_config
    
    def add_website(self, url: str, keywords: Optional[List[str]] = None):
        """Add website to monitoring list"""
        monitor_config = {
            'url': url,
            'keywords': keywords or [],
            'last_checked': datetime.utcnow(),
            'active': True,
            'last_content_hash': None
        }
        self.monitored_websites.append(monitor_config)
        logging.info(f"Added website {url} to monitoring")
        return monitor_config
    
    def take_tweet_screenshot(self, tweet_url: str) -> Optional[str]:
        """Take screenshot of a tweet and return base64 encoded image"""
        if not self.driver:
            logging.error("Selenium driver not available for screenshots")
            return None
        
        try:
            # Navigate to tweet
            self.driver.get(tweet_url)
            time.sleep(3)  # Wait for content to load
            
            # Find the tweet container
            tweet_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="tweet"]'))
            )
            
            # Take screenshot of the tweet element
            screenshot = tweet_element.screenshot_as_png
            
            # Convert to base64 for storage
            screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
            
            # Save screenshot to file
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot_filename = f"tweet_screenshot_{timestamp}.png"
            screenshot_path = f"/tmp/{screenshot_filename}"
            
            with open(screenshot_path, 'wb') as f:
                f.write(screenshot)
            
            logging.info(f"Tweet screenshot saved: {screenshot_path}")
            return screenshot_path
            
        except Exception as e:
            logging.error(f"Failed to take tweet screenshot: {e}")
            return None
    
    def monitor_twitter_handles(self) -> List[Dict]:
        """Monitor configured Twitter handles for new tweets"""
        if not self.twitter_api:
            return []
        
        new_content = []
        
        for handle_config in self.monitored_handles:
            if not handle_config['active']:
                continue
                
            try:
                handle = handle_config['handle'].replace('@', '')
                tweets = self.twitter_api.user_timeline(
                    screen_name=handle,
                    count=10,
                    tweet_mode='extended',
                    since_id=None
                )
                
                for tweet in tweets:
                    # Check if tweet is recent (within last hour)
                    tweet_time = tweet.created_at
                    if tweet_time > handle_config['last_checked']:
                        
                        # Take screenshot
                        tweet_url = f"https://twitter.com/{handle}/status/{tweet.id}"
                        screenshot_path = self.take_tweet_screenshot(tweet_url)
                        
                        new_content.append({
                            'type': 'twitter',
                            'handle': handle_config['handle'],
                            'content': tweet.full_text,
                            'url': tweet_url,
                            'timestamp': tweet_time,
                            'screenshot': screenshot_path,
                            'engagement': {
                                'likes': tweet.favorite_count,
                                'retweets': tweet.retweet_count,
                                'replies': tweet.reply_count
                            }
                        })
                
                # Update last checked time
                handle_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring Twitter handle {handle_config['handle']}: {e}")
        
        return new_content
    
    def monitor_reddit_threads(self) -> List[Dict]:
        """Monitor configured Reddit subreddits for new content"""
        if not self.reddit:
            return []
        
        new_content = []
        
        for thread_config in self.monitored_threads:
            if not thread_config['active']:
                continue
                
            try:
                subreddit = self.reddit.subreddit(thread_config['subreddit'])
                
                # Get hot posts from last 24 hours
                for submission in subreddit.hot(limit=20):
                    post_time = datetime.fromtimestamp(submission.created_utc)
                    
                    if post_time > thread_config['last_checked']:
                        # Check if post contains relevant keywords
                        content_text = f"{submission.title} {submission.selftext}".lower()
                        keywords = thread_config['keywords']
                        
                        if not keywords or any(keyword.lower() in content_text for keyword in keywords):
                            new_content.append({
                                'type': 'reddit',
                                'subreddit': thread_config['subreddit'],
                                'title': submission.title,
                                'content': submission.selftext,
                                'url': f"https://reddit.com{submission.permalink}",
                                'timestamp': post_time,
                                'engagement': {
                                    'score': submission.score,
                                    'comments': submission.num_comments,
                                    'upvote_ratio': submission.upvote_ratio
                                }
                            })
                
                # Update last checked time
                thread_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring Reddit subreddit {thread_config['subreddit']}: {e}")
        
        return new_content
    
    def monitor_websites(self) -> List[Dict]:
        """Monitor configured websites for new content"""
        new_content = []
        
        for website_config in self.monitored_websites:
            if not website_config['active']:
                continue
                
            try:
                # Extract content using trafilatura
                downloaded = trafilatura.fetch_url(website_config['url'])
                if not downloaded:
                    continue
                    
                text_content = trafilatura.extract(downloaded)
                if not text_content:
                    continue
                
                # Create content hash to detect changes
                import hashlib
                content_hash = hashlib.md5(text_content.encode()).hexdigest()
                
                # Check if content has changed
                if website_config['last_content_hash'] != content_hash:
                    new_content.append({
                        'type': 'website',
                        'url': website_config['url'],
                        'content': text_content,
                        'timestamp': datetime.utcnow(),
                        'content_hash': content_hash
                    })
                    
                    # Update last content hash
                    website_config['last_content_hash'] = content_hash
                
                # Update last checked time
                website_config['last_checked'] = datetime.utcnow()
                
            except Exception as e:
                logging.error(f"Error monitoring website {website_config['url']}: {e}")
        
        return new_content
    
    def run_monitoring_cycle(self) -> Dict:
        """Run complete monitoring cycle and return all new content"""
        logging.info("Starting social media monitoring cycle")
        
        results = {
            'twitter': self.monitor_twitter_handles(),
            'reddit': self.monitor_reddit_threads(),
            'websites': self.monitor_websites(),
            'timestamp': datetime.utcnow()
        }
        
        total_items = len(results['twitter']) + len(results['reddit']) + len(results['websites'])
        logging.info(f"Monitoring cycle complete. Found {total_items} new items")
        
        return results
    
    def get_monitoring_status(self) -> Dict:
        """Get current monitoring configuration and status"""
        return {
            'twitter_handles': len(self.monitored_handles),
            'reddit_threads': len(self.monitored_threads),
            'websites': len(self.monitored_websites),
            'handles': [h['handle'] for h in self.monitored_handles if h['active']],
            'subreddits': [t['subreddit'] for t in self.monitored_threads if t['active']],
            'website_urls': [w['url'] for w in self.monitored_websites if w['active']]
        }
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

# Global instance
social_monitor = SocialMonitor()