import os
import re
import json
import logging
try:
    import googleapiclient.discovery
except ImportError:
    googleapiclient = None
try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ModuleNotFoundError:
    YouTubeTranscriptApi = None
    logging.warning("youtube_transcript_api not installed - transcript fetching disabled")
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.http import MediaFileUpload
except ImportError:
    Credentials = None
    Flow = None
    MediaFileUpload = None

YOUTUBE_UPLOAD_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

class YouTubeService:
    # Global filter list for content to exclude from media feeds
    EXCLUDED_CONTENT = [
        'Orange Is The Nw Jill',
        'Orange Is The New Jill',
        'orange is the nw jill',
        'orange is the new jill'
    ]
    
    # PROTOCOL PULSE PRIMARY CHANNEL - Permanent autonomy activated
    PROTOCOL_PULSE_CHANNEL = {
        'id': 'UC8xfLJfmCpZ_aTydO0U_zcQ',
        'name': 'Protocol Pulse',
        'primary_playlist': 'PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd',  # Cypherpunk'd
        'auto_approve': True,  # Sequences go directly to dispatch queue
        'sovereign_window': '08:30',  # EST targeting for maximum reach
        'persona_mode': 'alex_sarah_debate'  # +75 conversation density
    }
    
    # Bitcoin channels for audio intelligence podcast generation
    PODCAST_CHANNELS = [
        {'name': 'Protocol Pulse', 'id': 'UC8xfLJfmCpZ_aTydO0U_zcQ', 'priority': True},
        {'name': 'Coin Bureau', 'id': 'UCqK_GSMbpiV8spgD3ZGloSw'},
        {'name': 'Natalie Brunell', 'id': 'UC6c1WLEK4w4qsKaIKqGptUw'},
        {'name': 'Bitcoin Magazine', 'id': 'UCni7PAlyNS0_12H-26DJJ3w'},
        {'name': 'Simply Bitcoin', 'id': 'UCNDkNyQe6ShQR3XjPPMnbvg'},
        {'name': 'Robert Breedlove', 'id': 'UCJLVQQf3LzXd7N_BuRZ3Vdw'},
        {'name': 'BTC Sessions', 'id': 'UChzLnWVsl3puKQwc5PoO6Zg'},
    ]
    
    # Podcast Series YouTube Configuration
    # Map show IDs to their YouTube playlist/video data
    # TO UPDATE: Replace video IDs below with actual YouTube video IDs from your channel
    # Format: Go to any YouTube video URL like youtube.com/watch?v=XXXXXXXXXXX
    # The 11-character code after "v=" is the video ID
    # Live Broadcasts - Featured shows with embedded videos
    LIVE_BROADCASTS = {
        'cypherpunkd': {
            'title': "Cypherpunk'd // Intel Briefing",
            'channel': 'Protocol Pulse',
            'playlist_id': 'PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd',
            'description': 'The original cypherpunk podcast exploring Bitcoin, privacy, and digital freedom.',
            'latest_id': 'QX3M8Ka9vUA'
        },
        'protocol_pulse': {
            'title': 'Protocol Pulse // Analysis',
            'channel': 'Coin Bureau',
            'channel_id': 'UCqK_GSMbpiV8spgD3ZGloSw',
            'description': 'Top crypto analysis and market insights from Coin Bureau.',
            'latest_id': 'rYQgy8QDEBI'
        }
    }
    
    SERIES_CONFIG = {
        'cypherpunkd': {
            'title': "Cypherpunk'd // Intel Briefing",
            'channel': 'Protocol Pulse',
            'description': 'The original cypherpunk podcast exploring Bitcoin, privacy, and digital freedom.',
            'playlist': [
                {'id': 'QX3M8Ka9vUA', 'title': 'Adam Back: From Cypherpunk to Bitcoin Treasury'},
                {'id': 'k0BWlvnBmIE', 'title': 'The Big Print: Decentralization Episode'},
                {'id': 'ERJ3NCqTTqg', 'title': 'Why Hyperinflation Makes Bitcoin Inevitable'}
            ],
            'latest_id': 'QX3M8Ka9vUA'
        },
        'protocol_pulse': {
            'title': 'Protocol Pulse // Analysis',
            'channel': 'Protocol Pulse',
            'description': 'Bitcoin analysis and market insights.',
            'playlist': [
                {'id': 'F9D7yL8C_W8', 'title': 'Bitcoin 2025 Conference Highlights'},
                {'id': 'GtDMBqLVrpE', 'title': 'The Case for Sound Money'}
            ],
            'latest_id': 'F9D7yL8C_W8'
        },
        'genesis_book': {
            'title': 'The Genesis Book Series',
            'channel': 'Protocol Pulse',
            'description': 'A series exploring Austrian economics and the foundational ideas behind Bitcoin.',
            'playlist': [
                {'id': 'QX3M8Ka9vUA', 'title': 'Genesis Book Series'}
            ],
            'latest_id': 'QX3M8Ka9vUA'
        },
        'daylight_robbery': {
            'title': 'Daylight Robbery Series',
            'channel': 'Protocol Pulse',
            'description': 'A series exposing the hidden story of how taxation has shaped human civilization.',
            'playlist': [
                {'id': 'ERJ3NCqTTqg', 'title': 'Daylight Robbery Analysis'}
            ],
            'latest_id': 'ERJ3NCqTTqg'
        },
        'big_print': {
            'title': 'The Big Print Series',
            'channel': 'Protocol Pulse',
            'description': 'An exposé revealing how the Federal Reserve engineered wealth extraction through monetary policy.',
            'playlist': [
                {'id': 'k0BWlvnBmIE', 'title': 'The Big Print Series'}
            ],
            'latest_id': 'k0BWlvnBmIE'
        },
        'everything_21m': {
            'title': 'Everything Divided By 21 Million',
            'channel': 'Protocol Pulse',
            'description': 'A cinematic exploration of Bitcoin\'s relationship to time, money, freedom, and human progress.',
            'playlist': [
                {'id': 'GtDMBqLVrpE', 'title': 'Everything Divided By 21 Million'}
            ],
            'latest_id': 'GtDMBqLVrpE'
        }
    }
    
    @staticmethod
    def get_thumbnail(video_id: str) -> str:
        """Get highest resolution YouTube thumbnail URL"""
        return f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    @staticmethod
    def get_hq_thumbnail(video_id: str) -> str:
        """Get high quality thumbnail (fallback if maxres not available)"""
        return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    
    @staticmethod
    def get_embed_url(video_id: str, autoplay: bool = True) -> str:
        """Get YouTube embed URL with modestbranding"""
        params = "modestbranding=1&rel=0"
        if autoplay:
            params = f"autoplay=1&{params}"
        return f"https://www.youtube.com/embed/{video_id}?{params}"
    
    @staticmethod
    def extract_id(url: str) -> str:
        """Extract video ID from various YouTube URL formats"""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
            r"(?:embed\/)([0-9A-Za-z_-]{11})"
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    # Designated channels to monitor for reactionary articles
    MONITORED_CHANNELS = {
        'BitcoinMagazine': 'UC6s6fMupv37_XN72S_5fDYA',
        'NatalieBrunell': 'UC0_M9-3R_mXv2oF_u7O08uQ',
        'SimplyBitcoin': 'UCqK_GSMbpiV8spgD3ZGloSw',
        'BTCSessions': 'UChzLnWVsl3puKQwc5PoO6Zg',
        'RobertBreedlove': 'UCpvDOLw4CXEmT-kKMCGe8Yg'
    }
    
    # Channel and Playlist IDs for dynamic fetching
    CHANNEL_PLAYLISTS = {
        'cypherpunkd': {
            'channel_id': None,  # Will be fetched dynamically
            'playlist_id': 'PLQ4MjCv9Oedpb79dWlGmJ4PUMYexx9Whd',
            'search_term': 'Cypherpunkd Bitcoin'
        },
        'protocol_pulse': {
            'channel_id': None,
            'playlist_id': None,
            'search_term': 'Protocol Pulse Bitcoin analysis'
        },
        'genesis_book': {
            'channel_id': None,
            'playlist_id': None,
            'search_term': 'Genesis Book Bitcoin Aaron van Wirdum'
        },
        'coin_bureau': {
            'channel_id': 'UCqK_GSMbpiV8spgD3ZGloSw',  # Coin Bureau channel
            'playlist_id': None,
            'search_term': 'Coin Bureau Bitcoin'
        }
    }
    
    @classmethod
    def get_series_data(cls, show_id: str) -> dict:
        """Get YouTube series data for a podcast show"""
        return cls.SERIES_CONFIG.get(show_id, {})
    
    @classmethod
    def get_all_series(cls) -> dict:
        """Get all configured series data"""
        return cls.SERIES_CONFIG

    def __init__(self):
        self.api_key = os.environ.get('YOUTUBE_API_KEY')
        self.youtube = (googleapiclient.discovery.build('youtube', 'v3', developerKey=self.api_key) if googleapiclient and self.api_key else None)
        self.openai_client = (OpenAI(api_key=os.environ.get('OPENAI_API_KEY')) if OpenAI and os.environ.get('OPENAI_API_KEY') else None)
        self.handles = ['BitcoinMagazine', 'nataliebrunell', 'bytefederal', 'BTCSessions', 'SimplyBitcoin', 'CoinBureau', 'thejackmallersshow', 'RobertBreedlove22']
        self._playlist_cache = {}  # Cache for API results
    
    def _is_excluded_content(self, title: str) -> bool:
        """Check if content should be excluded based on title"""
        title_lower = title.lower()
        for excluded in self.EXCLUDED_CONTENT:
            if excluded.lower() in title_lower:
                logging.info(f"Filtering out excluded YouTube content: {title}")
                return True
        return False
    
    def get_playlist_videos(self, playlist_id: str, max_results: int = 10) -> list:
        """
        Fetch videos from a YouTube playlist using the API.
        Falls back to hardcoded data if API is unavailable.
        """
        if not self.youtube:
            logging.warning("YouTube API not available - using fallback data")
            return []
        
        cache_key = f"playlist_{playlist_id}"
        if cache_key in self._playlist_cache:
            return self._playlist_cache[cache_key]
        
        try:
            request = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=playlist_id,
                maxResults=max_results
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item.get('snippet', {})
                video_id = snippet.get('resourceId', {}).get('videoId')
                if video_id:
                    videos.append({
                        'id': video_id,
                        'title': snippet.get('title', 'Untitled'),
                        'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                        'description': snippet.get('description', '')[:200],
                        'published_at': snippet.get('publishedAt', '')
                    })
            
            self._playlist_cache[cache_key] = videos
            logging.info(f"Fetched {len(videos)} videos from playlist {playlist_id}")
            return videos
            
        except Exception as e:
            logging.error(f"Error fetching playlist {playlist_id}: {e}")
            return []
    
    def search_playlist(self, search_term: str) -> str:
        """
        Search for a playlist by term and return playlist ID.
        """
        if not self.youtube:
            return None
        
        try:
            request = self.youtube.search().list(
                part='snippet',
                q=search_term,
                type='playlist',
                maxResults=1
            )
            response = request.execute()
            
            if response.get('items'):
                return response['items'][0]['id']['playlistId']
            return None
            
        except Exception as e:
            logging.error(f"Error searching playlist: {e}")
            return None
    
    def get_channel_uploads(self, channel_id: str, max_results: int = 5) -> list:
        """
        Get recent uploads from a channel.
        Falls back to RSS feed if YouTube API is not available.
        """
        # First try the API
        if self.youtube:
            try:
                request = self.youtube.channels().list(
                    part='contentDetails',
                    id=channel_id
                )
                response = request.execute()
                
                if response.get('items'):
                    uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                    return self.get_playlist_videos(uploads_id, max_results)
            except Exception as e:
                logging.warning(f"YouTube API failed, trying RSS fallback: {e}")
        
        # Fallback to RSS feed (publicly available, no API key needed)
        try:
            import requests
            import xml.etree.ElementTree as ET
            
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
            response = requests.get(rss_url, timeout=10)
            
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
                
                videos = []
                entries = root.findall('atom:entry', ns)[:max_results]
                
                for entry in entries:
                    video_id = entry.find('yt:videoId', ns)
                    title = entry.find('atom:title', ns)
                    
                    if video_id is not None and title is not None:
                        videos.append({
                            'id': video_id.text,
                            'title': title.text,
                            'thumbnail': f"https://img.youtube.com/vi/{video_id.text}/maxresdefault.jpg"
                        })
                
                if videos:
                    logging.info(f"Successfully fetched {len(videos)} videos via RSS for channel {channel_id}")
                    return videos
                    
        except Exception as e:
            logging.error(f"RSS fallback also failed: {e}")
        
        return []
    
    def get_latest_video(self, channel_id: str) -> dict:
        """
        Get the latest video from a channel for podcast generation.
        Returns dict with id, title, published_at, thumbnail.
        """
        videos = self.get_channel_uploads(channel_id, max_results=1)
        
        if videos:
            video = videos[0]
            return {
                'id': video.get('id'),
                'title': video.get('title'),
                'thumbnail': video.get('thumbnail', f"https://img.youtube.com/vi/{video.get('id')}/maxresdefault.jpg"),
                'published_at': video.get('published_at', None)
            }
        return None
    
    def get_dynamic_series(self, show_id: str) -> dict:
        """
        Get series data with dynamic video fetching.
        Uses API if available, falls back to static config.
        """
        static_config = self.SERIES_CONFIG.get(show_id, {})
        
        if not self.youtube:
            return static_config
        
        playlist_config = self.CHANNEL_PLAYLISTS.get(show_id, {})
        playlist_id = playlist_config.get('playlist_id')
        channel_id = playlist_config.get('channel_id')
        search_term = playlist_config.get('search_term')
        
        videos = []
        
        if playlist_id:
            videos = self.get_playlist_videos(playlist_id)
        elif channel_id:
            videos = self.get_channel_uploads(channel_id)
        elif search_term:
            found_playlist = self.search_playlist(search_term)
            if found_playlist:
                videos = self.get_playlist_videos(found_playlist)
        
        if videos:
            return {
                **static_config,
                'playlist': videos,
                'latest_id': videos[0]['id'] if videos else static_config.get('latest_id'),
                'dynamic': True
            }
        
        return static_config
    
    def get_all_dynamic_series(self) -> dict:
        """
        Get all series with dynamic video data where available.
        """
        result = {}
        for show_id in self.SERIES_CONFIG.keys():
            result[show_id] = self.get_dynamic_series(show_id)
        return result

    def get_channel_id(self, handle):
        if not self.youtube:
            return 'mock_channel_id'
        try:
            request = self.youtube.search().list(part='snippet', type='channel', q=f'@{handle}', maxResults=1)
            response = request.execute()
            return response['items'][0]['id']['channelId'] if response['items'] else 'mock_channel_id'
        except Exception as e:
            logging.error(f"YouTube search error: {e}")
            return 'mock_channel_id'

    def get_recent_videos(self):
        if not self.youtube:
            return [{'id': 'mock_id', 'title': 'Mock video', 'transcript': 'Mock Web3 video content.', 'thumbnail': 'mock.jpg', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]
        
        videos = []
        try:
            for handle in self.handles:
                channel_id = self.get_channel_id(handle)
                request = self.youtube.channels().list(part='contentDetails', id=channel_id)
                response = request.execute()
                uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                
                request = self.youtube.playlistItems().list(part='snippet', playlistId=uploads_id, maxResults=2)
                response = request.execute()
                
                for item in response['items']:
                    video_id = item['snippet']['resourceId']['videoId']
                    transcript = self._get_transcript(video_id)
                    relevance = self._is_relevant(item['snippet']['title'] + ' ' + transcript)
                    
                    if relevance['is_relevant']:
                        videos.append({
                            'id': video_id,
                            'title': item['snippet']['title'],
                            'transcript': transcript,
                            'thumbnail': item['snippet']['thumbnails']['high']['url'],
                            'is_relevant': True,
                            'topic': relevance['topic'],
                            'nuance': relevance['nuance']
                        })
            return videos
        except Exception as e:
            logging.error(f"YouTube API error: {e}")
            return [{'id': 'mock_id', 'title': 'Mock video', 'transcript': 'Mock Web3 video content.', 'thumbnail': 'mock.jpg', 'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}]

    def _get_transcript(self, video_id):
        if YouTubeTranscriptApi is None:
            return "Transcript unavailable"
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            return ' '.join([t['text'] for t in transcript])
        except Exception:
            return "Transcript unavailable"

    def draft_reactionary_article(self, video_data: dict) -> str:
        """
        Transcribes designated show and drafts a complementary review.
        Creates a "reactionary article" that reviews the key arguments made
        and offers additional philosophical analysis through the 'Bitcoin Lens'.
        
        Args:
            video_data: Dict containing 'id', 'title', and optionally 'transcript'
            
        Returns:
            HTML-formatted article content ready for publication
        """
        if not self.openai_client:
            logging.warning("OpenAI client not available for reactionary article")
            return None
        
        try:
            transcript = video_data.get('transcript')
            if not transcript or transcript == "Transcript unavailable":
                transcript = self._get_transcript(video_data['id'])
            
            if not transcript or transcript == "Transcript unavailable":
                logging.warning(f"No transcript available for video {video_data['id']}")
                return None
            
            prompt = f"""
            ACT AS: Walter Cronkite reporting for Protocol Pulse - the premier Bitcoin-first media network.
            
            TASK: Transcribe and REVIEW the following show: '{video_data['title']}'.
            
            CONTENT: {transcript[:8000]}
            
            GOAL: Draft a reactionary article that:
            1. Summarizes the key arguments and insights made in the show.
            2. Review the creator's arguments as a peer journalist. Contrast their points with the Protocol Pulse 'Bitcoin Lens' and provide a final verdict on whether the signal matches the noise.
            3. Provides additional philosophical analysis through the 'Bitcoin Lens'.
            4. Offers Protocol Pulse's authoritative perspective on the topics discussed.
            5. Maintains journalistic integrity while being engaging and insightful.
            
            FORMAT: Return ONLY valid HTML with these sections:
            - A compelling TL;DR box (class="tldr-section")
            - An introduction paragraph (class="article-paragraph")
            - Key points with headers (class="article-subheader")
            - Analysis paragraphs (class="article-paragraph")
            - A conclusion with Protocol Pulse perspective and final verdict.
            
            TONE: Authoritative, insightful, Bitcoin-maximalist perspective. Like a trusted evening news anchor who deeply understands sound money.
            """
            
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logging.error(f"Error drafting reactionary article: {e}")
            return None
    
    def get_monitored_channel_videos(self, limit: int = 5) -> list:
        """
        Get latest videos from monitored Bitcoin channels for reactionary articles.
        
        Args:
            limit: Maximum videos per channel
            
        Returns:
            List of video data dictionaries
        """
        if not self.youtube:
            return []
        
        videos = []
        try:
            for handle, channel_id in self.MONITORED_CHANNELS.items():
                try:
                    request = self.youtube.channels().list(part='contentDetails', id=channel_id)
                    response = request.execute()
                    
                    if response['items']:
                        uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                        
                        request = self.youtube.playlistItems().list(
                            part='snippet', 
                            playlistId=uploads_id, 
                            maxResults=limit
                        )
                        response = request.execute()
                        
                        for item in response['items']:
                            snippet = item['snippet']
                            video_id = item['snippet']['resourceId']['videoId']
                            thumbnail = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                                        snippet.get('thumbnails', {}).get('high', {}).get('url')
                            
                            videos.append({
                                'id': video_id,
                                'title': snippet['title'],
                                'channel': handle,
                                'thumbnail': thumbnail,
                                'published_at': snippet['publishedAt']
                            })
                except Exception as e:
                    logging.warning(f"Error fetching videos from {handle}: {e}")
                    continue
                    
            return videos
        except Exception as e:
            logging.error(f"Error getting monitored channel videos: {e}")
            return []
    
    def _is_relevant(self, text):
        if not self.openai_client:
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
        
        if len(text.split()) < 20 or any(m in text.lower() for m in ['lol', '😂', 'meme']):
            return {'is_relevant': False}
        
        try:
            response = self.openai_client.chat.completions.create(
                model='gpt-4o',
                messages=[{'role': 'user', 'content': f"Analyze text: '{text[:500]}'. Is it relevant to Web3/Bitcoin/DeFi? If yes, extract topic (e.g., 'Bitcoin ETF') and nuance (e.g., 'bullish'). Return JSON: {{'is_relevant': bool, 'topic': str, 'nuance': str}}"}],
                max_tokens=100
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"Relevance analysis error: {e}")
            return {'is_relevant': True, 'topic': 'Web3', 'nuance': 'Speculative'}
    
    # ==========================================
    # MULTIMODAL CONTENT ENGINE - Auto-Transcription
    # ==========================================
    
    def check_partner_channels_for_new_videos(self, hours_back: int = 12) -> list:
        """
        Check partner channels for new videos uploaded in the last N hours.
        Returns list of videos ready for auto-transcription and Bitcoin Lens review.
        
        Partner Channels: Coin Bureau, Natalie Brunell, Bitcoin Magazine,
        Simply Bitcoin, BTC Sessions, Robert Breedlove
        """
        from datetime import datetime, timedelta
        
        new_videos = []
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        for channel in self.PODCAST_CHANNELS:
            channel_name = channel['name']
            channel_id = channel['id']
            
            try:
                videos = self.get_channel_latest_videos(channel_id, limit=3)
                
                for video in videos:
                    published_str = video.get('published_at', '')
                    if published_str:
                        try:
                            published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                            if published_dt.replace(tzinfo=None) > cutoff_time:
                                new_videos.append({
                                    'video_id': video['id'],
                                    'title': video['title'],
                                    'channel_name': channel_name,
                                    'thumbnail': video.get('thumbnail', self.get_thumbnail(video['id'])),
                                    'published_at': published_str
                                })
                                logging.info(f"Found new video from {channel_name}: {video['title']}")
                        except ValueError:
                            continue
                            
            except Exception as e:
                logging.warning(f"Error checking {channel_name} for new videos: {e}")
                continue
        
        return new_videos
    
    def auto_process_new_partner_videos(self) -> dict:
        """
        Automatically process new partner videos:
        1. Detect new videos from partner channels
        2. Generate Bitcoin Lens review articles
        3. Create AI podcast episodes
        4. Extract social clips
        
        Returns summary of processed content.
        """
        from services.podcast_generator import podcast_generator
        
        results = {
            'videos_found': 0,
            'articles_generated': [],
            'podcasts_generated': [],
            'clips_created': [],
            'errors': []
        }
        
        new_videos = self.check_partner_channels_for_new_videos(hours_back=12)
        results['videos_found'] = len(new_videos)
        
        for video in new_videos:
            video_id = video['video_id']
            channel_name = video['channel_name']
            thumbnail = video['thumbnail']
            
            try:
                package = podcast_generator.create_full_social_package(
                    video_id=video_id,
                    thumbnail_url=thumbnail,
                    channel_name=channel_name
                )
                
                if package.get('article'):
                    results['articles_generated'].append({
                        'title': package['article'].get('title'),
                        'channel': channel_name,
                        'video_id': video_id
                    })
                
                if package.get('podcast'):
                    results['podcasts_generated'].append({
                        'audio_file': package['podcast'].get('audio_file'),
                        'channel': channel_name
                    })
                
                if package.get('social_videos'):
                    results['clips_created'].extend(package['social_videos'])
                    
            except Exception as e:
                error_msg = f"Error processing {channel_name} video {video_id}: {e}"
                logging.error(error_msg)
                results['errors'].append(error_msg)
        
        logging.info(f"Auto-processed {len(new_videos)} partner videos: "
                     f"{len(results['articles_generated'])} articles, "
                     f"{len(results['podcasts_generated'])} podcasts")
        
        return results
    
    def check_cypherpunkd_playlist(self, hours_back: int = 12) -> list:
        """
        Check the Cypherpunk'd playlist for new episodes.
        Returns list of new videos from the primary Protocol Pulse playlist.
        """
        if not self.youtube:
            logging.warning("YouTube API not available for Cypherpunk'd check")
            return []
        
        playlist_id = self.PROTOCOL_PULSE_CHANNEL['primary_playlist']
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        new_videos = []
        
        try:
            request = self.youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=10
            )
            response = request.execute()
            
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                title = snippet['title']
                published_str = snippet.get('publishedAt', '')
                
                if any(ex.lower() in title.lower() for ex in self.EXCLUDED_CONTENT):
                    continue
                
                try:
                    published_dt = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                    if published_dt.replace(tzinfo=None) > cutoff_time:
                        thumbnail = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                                   snippet.get('thumbnails', {}).get('high', {}).get('url') or \
                                   self.get_thumbnail(video_id)
                        
                        new_videos.append({
                            'video_id': video_id,
                            'title': title,
                            'channel_name': 'Protocol Pulse',
                            'thumbnail': thumbnail,
                            'published_at': published_str,
                            'is_cypherpunkd': True,
                            'auto_approve': True
                        })
                        logging.info(f"[CYPHERPUNK'D] New episode detected: {title}")
                except ValueError:
                    continue
                    
        except Exception as e:
            logging.error(f"Error checking Cypherpunk'd playlist: {e}")
        
        return new_videos
    
    def auto_process_cypherpunkd_with_launch(self) -> dict:
        """
        AUTONOMOUS PIPELINE for Cypherpunk'd:
        1. Detect new episodes from the playlist
        2. Generate full social package (article, podcast, clips)
        3. Create launch sequence with Alex/Sarah persona debate
        4. Auto-approve sequence for dispatch queue
        5. Send Telegram confirmation
        
        This is the "permanent autonomy" workflow.
        """
        from services.podcast_generator import podcast_generator
        from services.launch_sequence import launch_sequence_service
        from services.telegram_bot import pulse_operative
        from app import db
        import models
        import asyncio
        
        results = {
            'videos_found': 0,
            'packages_created': [],
            'sequences_queued': [],
            'telegram_alerts': [],
            'errors': []
        }
        
        new_episodes = self.check_cypherpunkd_playlist(hours_back=12)
        results['videos_found'] = len(new_episodes)
        
        if not new_episodes:
            logging.info("[CYPHERPUNK'D AUTONOMY] No new episodes detected")
            return results
        
        for episode in new_episodes:
            video_id = episode['video_id']
            title = episode['title']
            thumbnail = episode['thumbnail']
            
            try:
                logging.info(f"[CYPHERPUNK'D AUTONOMY] Processing: {title}")
                
                package = podcast_generator.create_full_social_package(
                    video_id=video_id,
                    thumbnail_url=thumbnail,
                    channel_name='Protocol Pulse'
                )
                
                results['packages_created'].append({
                    'title': title,
                    'video_id': video_id,
                    'article': package.get('article', {}).get('title'),
                    'clips': len(package.get('social_videos', []))
                })
                
                article_content = None
                if package.get('article'):
                    article_content = package['article'].get('content', '')
                    if not article_content:
                        article_content = f"Cypherpunk'd Episode: {title}"
                else:
                    article_content = f"Cypherpunk'd Episode: {title}"
                
                sequence = launch_sequence_service.generate_launch_sequence(
                    content=article_content,
                    content_type='article',
                    content_id=package.get('article', {}).get('id')
                )
                
                from services.launch_sequence import generate_persona_debate_thread
                import json
                debate_thread = generate_persona_debate_thread(article_content, title)
                if debate_thread:
                    logging.info(f"[PERSONA DEBATE] Generated {len(debate_thread)} tweets for Alex vs Sarah thread")
                
                if sequence and sequence.get('id'):
                    seq_record = models.LaunchSequence.query.get(sequence['id'])
                    if seq_record:
                        seq_record.status = 'approved'
                        seq_record.dispatch_window = f"{self.PROTOCOL_PULSE_CHANNEL.get('sovereign_window', '08:30')} EST"
                        seq_record.dispatch_timezone = 'America/New_York'
                        seq_record.is_autonomous = True
                        
                        if debate_thread:
                            seq_record.persona_debate = json.dumps(debate_thread)
                            seq_record.thread_replies = json.dumps([t['text'] for t in debate_thread])
                        
                        db.session.commit()
                        
                        results['sequences_queued'].append({
                            'sequence_id': sequence['id'],
                            'title': title,
                            'status': 'approved',
                            'dispatch_window': seq_record.dispatch_window
                        })
                        
                        alert_msg = f"""
🔴 *SIGNAL SECURED*
━━━━━━━━━━━━━━━━━━━━━

*New Cypherpunk'd episode processed and queued for dispatch.*

📺 *Episode:* {title[:50]}...
🎯 *Sequence ID:* #{sequence['id']}
⏰ *Dispatch Window:* {seq_record.dispatch_window} EST
✅ *Status:* AUTO-APPROVED

_The autonomous pipeline has activated._
                        """
                        
                        if pulse_operative.initialized:
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                try:
                                    result = loop.run_until_complete(pulse_operative.send_message(alert_msg))
                                finally:
                                    loop.close()
                                
                                if result.get('success'):
                                    results['telegram_alerts'].append({'sent': True, 'title': title})
                                    logging.info(f"[PULSE OPERATIVE] Telegram alert sent for: {title}")
                                else:
                                    results['telegram_alerts'].append({'sent': False, 'error': result.get('error')})
                            except Exception as tg_err:
                                logging.warning(f"Telegram alert failed: {tg_err}")
                                results['telegram_alerts'].append({'sent': False, 'error': str(tg_err)})
                        else:
                            logging.info("[PULSE OPERATIVE] Not initialized - skipping Telegram alert")
                            results['telegram_alerts'].append({'sent': False, 'error': 'Bot not initialized'})
                
            except Exception as e:
                error_msg = f"Error processing Cypherpunk'd episode {video_id}: {e}"
                logging.error(error_msg)
                results['errors'].append(error_msg)
        
        logging.info(f"[CYPHERPUNK'D AUTONOMY] Complete: {len(results['packages_created'])} packages, "
                     f"{len(results['sequences_queued'])} sequences queued")
        
        return results
    
    def get_channel_latest_videos(self, channel_id: str, limit: int = 5) -> list:
        """
        Get latest videos from a specific channel.
        Uses the uploads playlist for the channel.
        """
        if not self.youtube:
            logging.warning("YouTube API not available")
            return []
        
        try:
            request = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                return []
            
            uploads_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
            request = self.youtube.playlistItems().list(
                part='snippet',
                playlistId=uploads_id,
                maxResults=limit
            )
            response = request.execute()
            
            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                video_id = snippet['resourceId']['videoId']
                thumbnail = snippet.get('thumbnails', {}).get('maxres', {}).get('url') or \
                           snippet.get('thumbnails', {}).get('high', {}).get('url') or \
                           self.get_thumbnail(video_id)
                
                videos.append({
                    'id': video_id,
                    'title': snippet['title'],
                    'thumbnail': thumbnail,
                    'published_at': snippet.get('publishedAt', ''),
                    'description': snippet.get('description', '')[:200]
                })
            
            return videos
            
        except Exception as e:
            logging.error(f"Error getting latest videos for channel {channel_id}: {e}")
            return []
    
    def _get_oauth_redirect_uri(self):
        domains = os.environ.get('REPLIT_DOMAINS', '').split(',')
        if domains and domains[0]:
            return f"https://{domains[0]}/oauth/youtube/callback"
        dev_domain = os.environ.get('REPLIT_DEV_DOMAIN', 'localhost:5000')
        return f"https://{dev_domain}/oauth/youtube/callback"
    
    def is_oauth_configured(self):
        client_id = os.environ.get('YOUTUBE_CLIENT_ID')
        client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET')
        return bool(client_id and client_secret)
    
    def is_upload_authorized(self):
        return bool(os.environ.get('YOUTUBE_REFRESH_TOKEN'))
    
    def get_oauth_url(self):
        if not self.is_oauth_configured():
            return None, None
        
        client_config = {
            "web": {
                "client_id": os.environ.get('YOUTUBE_CLIENT_ID'),
                "client_secret": os.environ.get('YOUTUBE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._get_oauth_redirect_uri()]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=YOUTUBE_UPLOAD_SCOPES)
        flow.redirect_uri = self._get_oauth_redirect_uri()
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        return auth_url, state
    
    def exchange_oauth_code(self, code):
        if not self.is_oauth_configured():
            return None
        
        client_config = {
            "web": {
                "client_id": os.environ.get('YOUTUBE_CLIENT_ID'),
                "client_secret": os.environ.get('YOUTUBE_CLIENT_SECRET'),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self._get_oauth_redirect_uri()]
            }
        }
        
        flow = Flow.from_client_config(client_config, scopes=YOUTUBE_UPLOAD_SCOPES)
        flow.redirect_uri = self._get_oauth_redirect_uri()
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret
            }
        except Exception as e:
            logging.error(f"Failed to exchange OAuth code: {e}")
            return None
    
    def _get_upload_credentials(self):
        refresh_token = os.environ.get('YOUTUBE_REFRESH_TOKEN')
        if not refresh_token:
            return None
        
        return Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=os.environ.get('YOUTUBE_CLIENT_ID'),
            client_secret=os.environ.get('YOUTUBE_CLIENT_SECRET')
        )
    
    def upload_short(self, video_path, title, description=None, tags=None, privacy='private'):
        if not self.is_upload_authorized():
            return {'success': False, 'error': 'YouTube not authorized. Visit /admin/youtube-auth first.'}
        
        credentials = self._get_upload_credentials()
        if not credentials:
            return {'success': False, 'error': 'Failed to get upload credentials'}
        
        try:
            youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
            
            if not title.endswith('#Shorts') and '#shorts' not in title.lower():
                title = f"{title} #Shorts"
            
            if len(title) > 100:
                title = title[:97] + "..."
            
            body = {
                'snippet': {
                    'title': title,
                    'description': description or 'Bitcoin intelligence from Protocol Pulse',
                    'tags': tags or ['bitcoin', 'crypto', 'btc', 'shorts'],
                    'categoryId': '22'
                },
                'status': {
                    'privacyStatus': privacy,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
            
            request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)
            response = request.execute()
            
            video_id = response.get('id')
            return {
                'success': True,
                'video_id': video_id,
                'url': f'https://youtube.com/shorts/{video_id}',
                'title': title
            }
            
        except Exception as e:
            logging.error(f"YouTube upload failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_authorized_channel_info(self):
        if not self.is_upload_authorized():
            return None
        
        credentials = self._get_upload_credentials()
        if not credentials:
            return None
        
        try:
            youtube = googleapiclient.discovery.build('youtube', 'v3', credentials=credentials)
            request = youtube.channels().list(part='snippet', mine=True)
            response = request.execute()
            
            if response.get('items'):
                channel = response['items'][0]
                return {
                    'id': channel['id'],
                    'title': channel['snippet']['title'],
                    'thumbnail': channel['snippet']['thumbnails']['default']['url']
                }
            return None
        except Exception as e:
            logging.error(f"Failed to get authorized channel info: {e}")
            return None