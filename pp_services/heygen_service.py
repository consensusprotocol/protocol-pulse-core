import os
import logging
import requests
import json
import time
from typing import Dict, Optional, List, Tuple
import tempfile


class HeyGenService:
    def __init__(self):
        """Initialize HeyGen service for AI video generation"""
        self.api_key = os.environ.get('HEYGEN_API_KEY')
        
        if not self.api_key:
            raise ValueError("HEYGEN_API_KEY environment variable is required")
        
        # HeyGen API configuration
        self.base_url = "https://api.heygen.com"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Protocol Pulse optimized avatar configurations
        self.avatar_configs = {
            "professional_male": {
                "avatar_id": "Daisy-inskirt-20220818",  # Professional male presenter
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",  # Clear male voice
                "style": "professional"
            },
            "professional_female": {
                "avatar_id": "Susan_public_2_20240328",  # Professional female presenter
                "voice_id": "2d5b0e6c0c8b4f0f8f8f8f8f8f8f8f8f",  # Clear female voice
                "style": "professional"
            },
            "news_anchor_male": {
                "avatar_id": "josh_lite3_20230714",  # News anchor style
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",
                "style": "authoritative"
            },
            "crypto_expert": {
                "avatar_id": "Tyler-insuit-20220721",  # Tech expert look
                "voice_id": "1bd001e7e50f421d891986aad5158bc8",
                "style": "knowledgeable"
            }
        }
        
        # Video quality settings for different content types
        self.quality_settings = {
            "podcast_teaser": {
                "resolution": "1280x720",
                "quality": "high",
                "background": "crypto_themed"
            },
            "news_update": {
                "resolution": "1920x1080", 
                "quality": "premium",
                "background": "news_studio"
            },
            "analysis_video": {
                "resolution": "1920x1080",
                "quality": "premium", 
                "background": "tech_analysis"
            },
            "social_media": {
                "resolution": "1080x1080",
                "quality": "high",
                "background": "minimal"
            }
        }
        
        logging.info("HeyGen service initialized successfully")

    def get_available_avatars(self) -> List[Dict]:
        """Get list of available avatars from HeyGen"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/avatars",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("avatars", [])
            else:
                logging.error(f"Failed to fetch avatars: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error fetching avatars: {e}")
            return []

    def get_available_voices(self) -> List[Dict]:
        """Get list of available voices from HeyGen"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/voices",
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("data", {}).get("voices", [])
            else:
                logging.error(f"Failed to fetch voices: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            logging.error(f"Error fetching voices: {e}")
            return []

    def create_bitcoin_news_video(self, title: str, content: str, 
                                avatar_type: str = "news_anchor_male") -> Optional[str]:
        """Create a Bitcoin news video with professional presentation"""
        try:
            # Get avatar configuration
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["news_anchor_male"])
            quality_config = self.quality_settings["news_update"]
            
            # Create engaging script for Bitcoin news
            script = self._format_news_script(title, content)
            
            # Prepare video generation request
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#000000"  # Black background for Protocol Pulse theme
                    }
                }],
                "dimension": {
                    "width": 1920,
                    "height": 1080
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "bitcoin_news")
            
        except Exception as e:
            logging.error(f"Error creating Bitcoin news video: {e}")
            return None

    def create_defi_analysis_video(self, analysis_content: str,
                                 avatar_type: str = "crypto_expert") -> Optional[str]:
        """Create a DeFi analysis video with technical expertise presentation"""
        try:
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["crypto_expert"])
            quality_config = self.quality_settings["analysis_video"]
            
            # Format analysis content for video presentation
            script = self._format_analysis_script(analysis_content)
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text", 
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#DC2626"  # Red background for Protocol Pulse branding
                    }
                }],
                "dimension": {
                    "width": 1920,
                    "height": 1080
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "defi_analysis")
            
        except Exception as e:
            logging.error(f"Error creating DeFi analysis video: {e}")
            return None

    def create_podcast_teaser_video(self, episode_title: str, summary: str,
                                  avatar_type: str = "professional_female") -> Optional[str]:
        """Create a podcast teaser video to promote audio episodes"""
        try:
            avatar_config = self.avatar_configs.get(avatar_type, self.avatar_configs["professional_female"])
            quality_config = self.quality_settings["podcast_teaser"]
            
            # Create engaging teaser script
            script = self._format_teaser_script(episode_title, summary)
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#1F2937"  # Dark background with Protocol Pulse styling
                    }
                }],
                "dimension": {
                    "width": 1280,
                    "height": 720
                },
                "aspect_ratio": "16:9"
            }
            
            return self._generate_video(video_data, "podcast_teaser")
            
        except Exception as e:
            logging.error(f"Error creating podcast teaser video: {e}")
            return None

    def create_social_media_video(self, content: str, format_type: str = "square") -> Optional[str]:
        """Create short-form videos optimized for social media platforms"""
        try:
            avatar_config = self.avatar_configs["professional_male"]
            
            # Format content for social media (shorter, punchier)
            script = self._format_social_script(content)
            
            # Configure dimensions based on format type
            if format_type == "square":
                dimensions = {"width": 1080, "height": 1080}
                aspect_ratio = "1:1"
            elif format_type == "vertical":
                dimensions = {"width": 1080, "height": 1920}
                aspect_ratio = "9:16"
            else:  # horizontal
                dimensions = {"width": 1920, "height": 1080}
                aspect_ratio = "16:9"
            
            video_data = {
                "video_inputs": [{
                    "character": {
                        "type": "avatar",
                        "avatar_id": avatar_config["avatar_id"],
                        "avatar_style": avatar_config["style"]
                    },
                    "voice": {
                        "type": "text",
                        "input_text": script,
                        "voice_id": avatar_config["voice_id"]
                    },
                    "background": {
                        "type": "color",
                        "value": "#000000"
                    }
                }],
                "dimension": dimensions,
                "aspect_ratio": aspect_ratio
            }
            
            return self._generate_video(video_data, f"social_{format_type}")
            
        except Exception as e:
            logging.error(f"Error creating social media video: {e}")
            return None

    def _generate_video(self, video_data: Dict, video_type: str) -> Optional[str]:
        """Generate video using HeyGen API and return video URL"""
        try:
            # Submit video generation request
            response = requests.post(
                f"{self.base_url}/v2/video/generate",
                headers=self.headers,
                json=video_data
            )
            
            if response.status_code != 200:
                logging.error(f"Video generation failed: {response.status_code} - {response.text}")
                return None
            
            result = response.json()
            video_id = result.get("data", {}).get("video_id")
            
            if not video_id:
                logging.error("No video ID returned from HeyGen")
                return None
            
            logging.info(f"Video generation started with ID: {video_id}")
            
            # Poll for video completion
            return self._wait_for_video_completion(video_id, video_type)
            
        except Exception as e:
            logging.error(f"Error in video generation: {e}")
            return None

    def _wait_for_video_completion(self, video_id: str, video_type: str, 
                                 max_wait_time: int = 300) -> Optional[str]:
        """Wait for video generation to complete and return download URL"""
        try:
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                # Check video status
                response = requests.get(
                    f"{self.base_url}/v1/video_status.get",
                    headers=self.headers,
                    params={"video_id": video_id}
                )
                
                if response.status_code != 200:
                    logging.error(f"Failed to check video status: {response.text}")
                    time.sleep(10)
                    continue
                
                status_data = response.json()
                status = status_data.get("data", {}).get("status")
                
                if status == "completed":
                    video_url = status_data.get("data", {}).get("video_url")
                    logging.info(f"Video {video_id} completed: {video_url}")
                    return video_url
                elif status == "failed":
                    logging.error(f"Video generation failed for {video_id}")
                    return None
                else:
                    logging.info(f"Video {video_id} status: {status}")
                    time.sleep(15)  # Wait 15 seconds before checking again
            
            logging.error(f"Video generation timed out for {video_id}")
            return None
            
        except Exception as e:
            logging.error(f"Error waiting for video completion: {e}")
            return None

    def _format_news_script(self, title: str, content: str) -> str:
        """Format news content into engaging video script"""
        intro = "Breaking news in the Bitcoin world:"
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        # Keep it concise for video (aim for 60-90 seconds)
        if len(formatted_content) > 500:
            formatted_content = formatted_content[:500] + "..."
        
        script = f"{intro} {title}. {formatted_content}"
        return script

    def _format_analysis_script(self, content: str) -> str:
        """Format analysis content for technical video presentation"""
        intro = "Here's your DeFi protocol analysis:"
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        if len(formatted_content) > 600:
            formatted_content = formatted_content[:600] + "..."
        
        script = f"{intro} {formatted_content}"
        return script

    def _format_teaser_script(self, title: str, summary: str) -> str:
        """Format podcast episode into engaging teaser"""
        intro = "Coming up on Protocol Pulse:"
        formatted_summary = summary.replace('#', '').replace('*', '').strip()
        
        if len(formatted_summary) > 300:
            formatted_summary = formatted_summary[:300] + "..."
        
        script = f"{intro} {title}. {formatted_summary} Don't miss this episode!"
        return script

    def _format_social_script(self, content: str) -> str:
        """Format content for short social media videos (15-30 seconds)"""
        formatted_content = content.replace('#', '').replace('*', '').strip()
        
        # Keep very short for social media
        if len(formatted_content) > 200:
            formatted_content = formatted_content[:200] + "..."
        
        return formatted_content

    def test_connection(self) -> bool:
        """Test HeyGen API connection"""
        try:
            response = requests.get(
                f"{self.base_url}/v2/avatars",
                headers=self.headers
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logging.error(f"HeyGen connection test failed: {e}")
            return False

    def get_account_info(self) -> Dict:
        """Get account information and limits"""
        try:
            response = requests.get(
                f"{self.base_url}/v1/user/remaining_quota",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return response.json().get("data", {})
            else:
                logging.error(f"Failed to get account info: {response.text}")
                return {}
                
        except Exception as e:
            logging.error(f"Error getting account info: {e}")
            return {}

# Initialize the service
heygen_service = HeyGenService()