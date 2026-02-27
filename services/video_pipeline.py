
"""
Video Generation Pipeline
==========================
Orchestrates video creation:
1. Clip extraction from YouTube partners
2. Highlight detection
3. Voiceover generation (ElevenLabs)
4. Medley assembly on Ultron GPUs
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class VideoPipeline:
    """
    End-to-end video generation pipeline.
    """
    
    def __init__(self):
        self.elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY")
        self.output_dir = Path("static/video")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_voiceover(self, script: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Optional[str]:
        """
        Generate voiceover audio using ElevenLabs.
        Returns path to audio file.
        """
        if not self.elevenlabs_key:
            logger.warning("ElevenLabs not configured")
            return None
        
        try:
            import requests
            
            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.elevenlabs_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": script,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=60
            )
            
            if response.ok:
                filename = f"voiceover_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
                filepath = self.output_dir / filename
                
                with open(filepath, "wb") as f:
                    f.write(response.content)
                
                logger.info(f"Voiceover generated: {filepath}")
                return str(filepath)
            else:
                logger.error(f"ElevenLabs error: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Voiceover generation error: {e}")
            return None
    
    def create_medley(self, config: Dict) -> Dict:
        """
        Create a video medley using Ultron GPUs.
        
        config:
            clips: list of clip info
            duration: target duration in seconds
            voiceover_script: optional narration script
            title: medley title
        """
        from services.ultron_gpu_service import ultron_gpu_service
        
        if not ultron_gpu_service.connected:
            return {"success": False, "error": "Ultron not connected"}
        
        # Generate voiceover if script provided
        voiceover_path = None
        if config.get("voiceover_script"):
            voiceover_path = self.generate_voiceover(config["voiceover_script"])
        
        # Start render on Ultron
        render_config = {
            "duration": config.get("duration", 60),
            "output_name": f"medley_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4",
            "voiceover": voiceover_path
        }
        
        result = ultron_gpu_service.render_medley(render_config)
        
        if result.get("success"):
            return {
                "success": True,
                "job_id": render_config["output_name"],
                "voiceover": voiceover_path,
                "status": "rendering"
            }
        else:
            return result
    
    def get_job_status(self, job_id: str) -> Dict:
        """Check status of a render job."""
        from services.ultron_gpu_service import ultron_gpu_service
        return ultron_gpu_service.get_render_progress(job_id)


# Singleton
video_pipeline = VideoPipeline()
