import os
import logging
import praw
from datetime import datetime
from typing import List, Dict

class RedditService:
    def __init__(self):
        self.reddit = None
        try:
            self.reddit = praw.Reddit(
                client_id=os.environ.get('REDDIT_CLIENT_ID'),
                client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
                user_agent=os.environ.get('REDDIT_USER_AGENT')
            )
            logging.info("Reddit PRAW service initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize PRAW: {e}")
        self.use_api = bool(self.reddit)
        self.base_url = "https://www.reddit.com"

        # Bitcoin and DeFi focused subreddits
        self.crypto_subreddits = [
            'bitcoin',
            'defi', 
            'cryptocurrency',
            'bitcoinbeginners',
            'bitcoindiscussion',
            'lightningnetwork',
            'decentralizedfinance',
            'ethfinance',
            'cryptomarkets',
            'bitcointech'
        ]
    
    def post_to_reddit(self, subreddit_name: str, title: str, url: str) -> Dict:
        """Post a link to Reddit using PRAW"""
        result = {"success": False, "post_url": None, "errors": []}
        
        if not self.reddit:
            result["errors"].append("Reddit API not available")
            return result
            
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            
            # Submit the link post
            submission = subreddit.submit(title=title, url=url)
            
            result["success"] = True
            result["post_url"] = f"https://reddit.com{submission.permalink}"
            result["post_id"] = submission.id
            
            logging.info(f"Successfully posted to r/{subreddit_name}: {result['post_url']}")
            return result
            
        except Exception as e:
            result["errors"].append(f"Reddit posting failed: {e}")
            logging.error(f"Error posting to r/{subreddit_name}: {e}")
            return result

    def get_trending_posts(self, subreddit_name: str, limit: int = 10) -> List[Dict]:
        if not self.reddit:
            return []
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            for submission in subreddit.hot(limit=limit):
                if submission.stickied:
                    continue
                posts.append({
                    'title': submission.title,
                    'url': submission.url,
                    'score': submission.score,
                    'num_comments': submission.num_comments,
                    'created_utc': datetime.fromtimestamp(submission.created_utc),
                    'selftext': submission.selftext,
                    'author': str(submission.author) if submission.author else '[deleted]',
                    'permalink': f"https://reddit.com{submission.permalink}"
                })
            return posts
        except Exception as e:
            logging.error(f"Error fetching posts from r/{subreddit_name}: {e}")
            return []

    def get_trending_topics(self, subreddits, limit=10, time_period='day'):
        """
        Get trending topics from specified subreddits
        subreddits: list of subreddit names
        limit: number of posts to fetch per subreddit
        time_period: 'hour', 'day', 'week', 'month', 'year', 'all'
        """
        trending_posts = []
        
        for subreddit in subreddits:
            try:
                url = f"{self.base_url}/r/{subreddit}/hot.json"
                params = {
                    'limit': limit,
                    't': time_period
                }
                
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get('data', {}).get('children', [])
                    
                    for post_data in posts:
                        post = post_data.get('data', {})
                        
                        # Filter for relevant content
                        if self._is_relevant_post(post):
                            trending_posts.append({
                                'title': post.get('title', ''),
                                'selftext': post.get('selftext', ''),
                                'url': post.get('url', ''),
                                'subreddit': post.get('subreddit', ''),
                                'score': post.get('score', 0),
                                'num_comments': post.get('num_comments', 0),
                                'created_utc': post.get('created_utc', 0),
                                'permalink': f"{self.base_url}{post.get('permalink', '')}",
                                'author': post.get('author', 'Unknown')
                            })
                
                else:
                    logging.warning(f"Failed to fetch from r/{subreddit}: {response.status_code}")
                    
            except Exception as e:
                logging.error(f"Error fetching from r/{subreddit}: {str(e)}")
                continue
        
        # Sort by score (popularity) and return top posts
        trending_posts.sort(key=lambda x: x['score'], reverse=True)
        return trending_posts[:limit * len(subreddits)]
    
    def _is_relevant_post(self, post):
        """Filter posts for relevance to Web3/crypto topics"""
        title = post.get('title', '').lower()
        selftext = post.get('selftext', '').lower()
        
        # Keywords that indicate relevance
        relevant_keywords = [
            'bitcoin', 'btc', 'ethereum', 'eth', 'crypto', 'cryptocurrency', 
            'blockchain', 'web3', 'defi', 'nft', 'dao', 'smart contract',
            'mining', 'staking', 'yield farming', 'dapp', 'metaverse',
            'privacy', 'decentralized', 'protocol', 'token', 'coin',
            'regulation', 'sec', 'cbdc', 'lightning network', 'layer 2'
        ]
        
        # Check if any relevant keywords are in title or text
        content = f"{title} {selftext}"
        return any(keyword in content for keyword in relevant_keywords)
    
    def get_post_details(self, post_url):
        """Get detailed information about a specific Reddit post"""
        try:
            # Convert Reddit URL to JSON API URL
            if 'reddit.com' in post_url:
                json_url = post_url.rstrip('/') + '.json'
            else:
                return None
            
            response = requests.get(json_url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    post_data = data[0].get('data', {}).get('children', [])
                    if post_data:
                        post = post_data[0].get('data', {})
                        
                        # Get top comments
                        comments = []
                        if len(data) > 1:
                            comment_data = data[1].get('data', {}).get('children', [])
                            for comment in comment_data[:5]:  # Top 5 comments
                                comment_info = comment.get('data', {})
                                if comment_info.get('body') and comment_info.get('body') != '[deleted]':
                                    comments.append({
                                        'body': comment_info.get('body', ''),
                                        'score': comment_info.get('score', 0),
                                        'author': comment_info.get('author', 'Unknown')
                                    })
                        
                        return {
                            'title': post.get('title', ''),
                            'selftext': post.get('selftext', ''),
                            'url': post.get('url', ''),
                            'score': post.get('score', 0),
                            'num_comments': post.get('num_comments', 0),
                            'comments': comments,
                            'created_utc': post.get('created_utc', 0)
                        }
            
            return None
            
        except Exception as e:
            logging.error(f"Error fetching post details: {str(e)}")
            return None
    
    def search_subreddit(self, subreddit, query, limit=25):
        """Search for specific topics within a subreddit"""
        try:
            url = f"{self.base_url}/r/{subreddit}/search.json"
            params = {
                'q': query,
                'restrict_sr': 'true',
                'sort': 'relevance',
                'limit': limit,
                't': 'week'  # Posts from the last week
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                
                search_results = []
                for post_data in posts:
                    post = post_data.get('data', {})
                    search_results.append({
                        'title': post.get('title', ''),
                        'selftext': post.get('selftext', ''),
                        'url': post.get('url', ''),
                        'score': post.get('score', 0),
                        'permalink': f"{self.base_url}{post.get('permalink', '')}",
                        'created_utc': post.get('created_utc', 0)
                    })
                
                return search_results
            
            return []
            
        except Exception as e:
            logging.error(f"Error searching subreddit: {str(e)}")
            return []

    def get_bitcoin_trending_topics(self, limit: int = 20) -> List[Dict]:
        """Get trending Bitcoin-related topics using PRAW"""
        if self.use_api:
            bitcoin_subreddits = ['bitcoin', 'bitcoinbeginners', 'bitcoindiscussion', 'lightningnetwork']
            all_posts = []
            
            for subreddit_name in bitcoin_subreddits:
                posts = self.get_trending_posts_praw(subreddit_name, limit=8)
                all_posts.extend(posts)
            
            # Sort by engagement score
            all_posts.sort(key=lambda x: x['score'] + (x['num_comments'] * 2), reverse=True)
            return all_posts[:limit]
        else:
            # Fallback to public API
            return self.get_trending_topics(['bitcoin', 'bitcoinbeginners'], limit=limit)

    def get_defi_trending_topics(self, limit: int = 20) -> List[Dict]:
        """Get trending DeFi-related topics using PRAW"""
        if self.use_api:
            defi_subreddits = ['defi', 'decentralizedfinance', 'ethfinance']
            all_posts = []
            
            for subreddit_name in defi_subreddits:
                posts = self.get_trending_posts_praw(subreddit_name, limit=8)
                all_posts.extend(posts)
            
            # Sort by engagement score
            all_posts.sort(key=lambda x: x['score'] + (x['num_comments'] * 2), reverse=True)
            return all_posts[:limit]
        else:
            # Fallback to public API
            return self.get_trending_topics(['defi', 'cryptocurrency'], limit=limit)

    def get_content_ideas(self, topic_type: str = "bitcoin", limit: int = 5) -> List[Dict]:
        """Get content ideas based on trending topics"""
        if topic_type.lower() == "bitcoin":
            posts = self.get_bitcoin_trending_topics(limit=15)
        elif topic_type.lower() == "defi":
            posts = self.get_defi_trending_topics(limit=15)
        else:
            posts = self.get_trending_topics(['cryptocurrency', 'cryptomarkets'], limit=15)
        
        # Convert to content ideas
        content_ideas = []
        for post in posts[:limit]:
            if isinstance(post, dict):
                score = post.get('score', 0)
                comments = post.get('num_comments', 0)
                
                if score > 50 and comments > 10:  # Minimum engagement threshold
                    idea = {
                        'title': post.get('title', ''),
                        'article_angle': self._generate_article_angle(post),
                        'source_url': post.get('permalink', ''),
                        'engagement_score': score + comments,
                        'subreddit': post.get('subreddit', ''),
                        'created': post.get('created_utc', datetime.now()).strftime('%Y-%m-%d %H:%M') if isinstance(post.get('created_utc'), datetime) else 'Unknown'
                    }
                    content_ideas.append(idea)
        
        return content_ideas

    def _generate_article_angle(self, post: Dict) -> str:
        """Generate a potential article angle from a Reddit post"""
        title = post.get('title', '').lower()
        
        # Common article angles based on post content
        if any(word in title for word in ['price', 'surge', 'rally', 'pump']):
            return "Market Analysis: Price Movement Deep Dive"
        elif any(word in title for word in ['adoption', 'institutional', 'company']):
            return "Adoption News: Industry Impact Analysis"
        elif any(word in title for word in ['technical', 'upgrade', 'update', 'protocol']):
            return "Technical Analysis: Technology Advancement"
        elif any(word in title for word in ['regulation', 'legal', 'sec', 'government']):
            return "Regulatory Update: Policy Impact Assessment"
        elif any(word in title for word in ['hack', 'security', 'exploit']):
            return "Security Alert: Risk Analysis and Prevention"
        elif any(word in title for word in ['defi', 'yield', 'liquidity', 'protocol']):
            return "DeFi Deep Dive: Protocol Analysis"
        else:
            return "Community Spotlight: Trending Discussion Analysis"

    def test_connection(self) -> bool:
        """Test Reddit API connection"""
        if self.use_api and self.reddit:
            try:
                subreddit = self.reddit.subreddit('bitcoin')
                next(subreddit.hot(limit=1))
                return True
            except Exception as e:
                logging.error(f"Reddit PRAW connection test failed: {e}")
                return False
        else:
            # Test public API fallback
            try:
                import requests
                response = requests.get("https://www.reddit.com/r/bitcoin/hot.json?limit=1", timeout=5)
                return response.status_code == 200
            except:
                return False