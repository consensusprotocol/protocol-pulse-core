# Protocol Pulse Image Service
# Real photos from Unsplash/Pexels with red/black brand overlay
# NO DUPLICATE IMAGES

import os
import logging
import requests
import random
from datetime import datetime
from PIL import Image, ImageDraw
from io import BytesIO

# Track used image URLs to prevent duplicates
_used_images = set()

class ImageGenerationService:
    def __init__(self):
        self.unsplash_key = os.environ.get("UNSPLASH_ACCESS_KEY")
        self.pexels_key = os.environ.get("PEXELS_API_KEY")
        self.target_width = 1200
        self.target_height = 630
        
        if self.unsplash_key:
            logging.info("Image service initialized with Unsplash")
        elif self.pexels_key:
            logging.info("Image service initialized with Pexels")
        else:
            logging.warning("No image API keys found - using defaults")
    
    def _extract_keywords(self, title):
        """Smart keyword extraction - finds the MAIN SUBJECT for relevant images."""
        title_lower = title.lower()
        
        # SPECIFIC TOPIC MAPPINGS - exact phrase matches for best results
        specific_topics = {
            # Companies
            'cash app': 'smartphone mobile payment fintech app',
            'coinbase': 'cryptocurrency exchange trading',
            'microstrategy': 'corporate business office',
            'blackrock': 'wall street investment banking',
            'fidelity': 'institutional investment finance',
            'strike': 'mobile payment lightning',
            'futurebit': 'computer hardware mining rig',
            'apollo': 'hardware device technology',
            
            # Bitcoin topics
            'lightning network': 'lightning bolt electricity power',
            'bitcoin mining': 'data center servers racks',
            'bitcoin etf': 'wall street stock exchange trading',
            'bitcoin price': 'stock chart trading screen',
            'bitcoin rally': 'bull wall street success',
            'bitcoin adoption': 'global world technology',
            'halving': 'gold scarcity precious metal',
            'hashrate': 'data center supercomputer',
            'difficulty': 'computer servers power',
            
            # Financial
            'federal reserve': 'federal reserve building marble',
            'interest rate': 'bank finance economy',
            'inflation': 'money prices economy',
            'treasury': 'government finance building',
            'regulation': 'courthouse government law',
            
            # Countries
            'el salvador': 'central america tropical landscape',
            'china': 'china asia beijing',
        }
        
        # Check specific matches first
        for topic, search in specific_topics.items():
            if topic in title_lower:
                return search
        
        # Keyword-to-visual mappings
        visual_map = {
            'bitcoin': 'gold coin cryptocurrency',
            'btc': 'gold cryptocurrency',
            'mining': 'data center servers',
            'etf': 'wall street trading floor',
            'price': 'trading chart stocks',
            'wallet': 'vault security',
            'lightning': 'lightning bolt energy',
            'network': 'technology network connected',
            'adoption': 'global technology',
            'institutional': 'corporate office building',
            'regulation': 'government courthouse',
            'whale': 'ocean large scale',
            'exchange': 'trading screens market',
            'payment': 'mobile payment transaction',
            'transaction': 'digital payment',
            'security': 'cybersecurity lock',
            'privacy': 'anonymous privacy',
            'staking': 'growth investment',
            'yield': 'money growth returns',
        }
        
        # Filter stopwords
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'new', 'amid', 'despite', 'how', 'why', 'what', 'when', 'where',
            'this', 'that', 'these', 'those', 'its', 'it', 'they', 'their',
            'more', 'most', 'some', 'any', 'than', 'just', 'also', 'now',
            'says', 'said', 'reportedly', 'enhances', 'offers', 'brings',
            'reaches', 'hits', 'adds', 'surges', 'past', 'record', 'high'
        }
        
        words = title_lower.replace(':', '').replace('-', ' ').replace("'s", '').split()
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Build search from mapped keywords
        search_parts = []
        for kw in keywords[:3]:
            if kw in visual_map:
                search_parts.append(visual_map[kw])
            elif kw not in ['bitcoin', 'btc', 'crypto']:  # Skip generic crypto terms
                search_parts.append(kw)
        
        if search_parts:
            return ' '.join(search_parts[:2])
        
        return 'cryptocurrency finance technology'

    def _search_unsplash(self, query):
        global _used_images
        if not self.unsplash_key:
            return None
        try:
            url = "https://api.unsplash.com/search/photos"
            params = {"query": query, "per_page": 15, "orientation": "landscape", "content_filter": "high"}
            headers = {"Authorization": f"Client-ID {self.unsplash_key}"}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                # Shuffle and find unused image
                random.shuffle(results)
                for photo in results:
                    photo_url = photo["urls"]["regular"]
                    photo_id = photo["id"]
                    if photo_id not in _used_images:
                        _used_images.add(photo_id)
                        return photo_url
                # If all used, pick random anyway
                if results:
                    return results[0]["urls"]["regular"]
            return None
        except Exception as e:
            logging.error(f"Unsplash error: {e}")
            return None
    
    def _search_pexels(self, query):
        global _used_images
        if not self.pexels_key:
            return None
        try:
            url = "https://api.pexels.com/v1/search"
            params = {"query": query, "per_page": 15, "orientation": "landscape"}
            headers = {"Authorization": self.pexels_key}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                photos = data.get("photos", [])
                random.shuffle(photos)
                for photo in photos:
                    photo_id = str(photo["id"])
                    if photo_id not in _used_images:
                        _used_images.add(photo_id)
                        return photo["src"]["large"]
                if photos:
                    return photos[0]["src"]["large"]
            return None
        except Exception as e:
            logging.error(f"Pexels error: {e}")
            return None
    
    def _apply_brand_overlay(self, img):
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        width, height = img.size
        
        for y in range(height):
            if y > height * 0.5:
                progress = (y - height * 0.5) / (height * 0.5)
                alpha = int(180 * progress)
                red_tint = int(40 * progress)
                draw.line([(0, y), (width, y)], fill=(red_tint, 0, 0, alpha))
            if y < height * 0.3:
                progress = 1 - (y / (height * 0.3))
                alpha = int(100 * progress)
                draw.line([(0, y), (width, y)], fill=(20, 0, 0, alpha))
        
        red_tint = Image.new('RGBA', img.size, (60, 0, 0, 30))
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        img = Image.alpha_composite(img, red_tint)
        img = Image.alpha_composite(img, overlay)
        return img.convert('RGB')
    
    def _resize_and_crop(self, img):
        target_ratio = self.target_width / self.target_height
        img_ratio = img.width / img.height
        
        if img_ratio > target_ratio:
            new_height = img.height
            new_width = int(new_height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, new_height))
        else:
            new_width = img.width
            new_height = int(new_width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, new_width, top + new_height))
        
        return img.resize((self.target_width, self.target_height), Image.Resampling.LANCZOS)
    
    def generate_article_header_image(self, article_title, article_summary=""):
        keywords = self._extract_keywords(article_title)
        logging.info(f"Searching for image: {keywords}")
        
        photo_url = self._search_unsplash(keywords)
        if not photo_url:
            photo_url = self._search_pexels(keywords)
        
        if not photo_url:
            logging.warning(f"No photo found for '{keywords}' - using default")
            return self._get_default_image()
        
        try:
            response = requests.get(photo_url, timeout=15)
            img = Image.open(BytesIO(response.content))
            img = self._resize_and_crop(img)
            img = self._apply_brand_overlay(img)
            local_path = self._save_image(img, article_title)
            logging.info(f"Generated branded image: {local_path}")
            return local_path
        except Exception as e:
            logging.error(f"Error processing image: {e}")
            return self._get_default_image()
    
    def _save_image(self, img, title):
        os.makedirs('static/images/headers', exist_ok=True)
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title.replace(' ', '_')[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"header_{safe_title}_{timestamp}.jpg"
        filepath = f"static/images/headers/{filename}"
        img.save(filepath, "JPEG", quality=85, optimize=True)
        return f"/static/images/headers/{filename}"
    
    def _get_default_image(self):
        return "/static/images/default_header.jpg"

# Singleton instance
image_service = ImageGenerationService()
