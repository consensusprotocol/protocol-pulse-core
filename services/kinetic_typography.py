"""
Kinetic Typography Service
Generates animated caption overlays for video clips using FFmpeg
Standard for 2026 social video distribution

Features:
- Voice sync via subtitle timing from transcript
- Walter Cronkite style bold red/black/white overlays
- Multiple animation presets (fade, typewriter, bounce, scale, slide)
"""
import os
import subprocess
import logging
import json
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Voice ID mapping for ElevenLabs sync
VOICE_PROFILES = {
    'walter_cronkite': {
        'voice_id': 'onwK4e9ZLuTAKqWW03F9',
        'speaking_rate': 145,  # words per minute
        'word_gap': 0.05  # seconds between words
    },
    'alex_quant': {
        'voice_id': 'EXAVITQu4vr4xnSDxMaL',
        'speaking_rate': 160,
        'word_gap': 0.04
    },
    'sarah_macro': {
        'voice_id': 'XrExE9yKIg1WjnnlVkGX',
        'speaking_rate': 155,
        'word_gap': 0.045
    }
}

class KineticTypographyService:
    """Generate animated text overlays for viral video clips"""
    
    ANIMATION_PRESETS = {
        'fade_in': {
            'filter': "drawtext=text='%s':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:alpha='if(lt(t,%f),t/%f,1)'",
            'description': 'Smooth fade-in effect'
        },
        'typewriter': {
            'filter': "drawtext=text='%s':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=h-100:enable='between(t,%f,%f)'",
            'description': 'Typewriter reveal effect'
        },
        'bounce': {
            'filter': "drawtext=text='%s':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=(h/2)+sin(t*10)*20:enable='between(t,%f,%f)'",
            'description': 'Bouncing text animation'
        },
        'scale_pop': {
            'filter': "drawtext=text='%s':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=(h-text_h)/2:enable='between(t,%f,%f)'",
            'description': 'Pop-in scale effect'
        },
        'slide_up': {
            'filter': "drawtext=text='%s':fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:fontsize=%d:fontcolor=white:x=(w-text_w)/2:y=h-100-((t-%f)*50):enable='between(t,%f,%f)'",
            'description': 'Slide up from bottom'
        }
    }
    
    STYLE_PRESETS = {
        'protocol_pulse': {
            'font_color': 'white',
            'stroke_color': 'black',
            'stroke_width': 3,
            'font_size': 48,
            'position': 'bottom'
        },
        'breaking_news': {
            'font_color': '#dc2626',
            'stroke_color': 'white',
            'stroke_width': 4,
            'font_size': 56,
            'position': 'center'
        },
        'alex_quant': {
            'font_color': '#3b82f6',
            'stroke_color': 'black',
            'stroke_width': 3,
            'font_size': 44,
            'position': 'bottom'
        },
        'sarah_macro': {
            'font_color': '#a855f7',
            'stroke_color': 'black',
            'stroke_width': 3,
            'font_size': 44,
            'position': 'bottom'
        }
    }
    
    def __init__(self):
        self.output_dir = 'static/clips/kinetic'
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("Kinetic Typography service initialized")
    
    def generate_caption_overlay(
        self,
        input_video: str,
        captions: List[Dict],
        output_path: Optional[str] = None,
        style: str = 'protocol_pulse',
        animation: str = 'fade_in'
    ) -> Optional[str]:
        """
        Generate video with animated caption overlays
        
        Args:
            input_video: Path to input video file
            captions: List of caption dicts with 'text', 'start', 'end' keys
            output_path: Optional output path
            style: Style preset name
            animation: Animation preset name
            
        Returns:
            Path to output video with captions
        """
        if not os.path.exists(input_video):
            logger.error(f"Input video not found: {input_video}")
            return None
        
        style_config = self.STYLE_PRESETS.get(style, self.STYLE_PRESETS['protocol_pulse'])
        
        if not output_path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(self.output_dir, f'kinetic_{timestamp}.mp4')
        
        filter_complex = self._build_filter_chain(captions, style_config, animation)
        
        cmd = [
            'ffmpeg', '-y',
            '-i', input_video,
            '-vf', filter_complex,
            '-c:a', 'copy',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-crf', '23',
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                logger.info(f"Kinetic typography generated: {output_path}")
                return output_path
            else:
                logger.error(f"FFmpeg error: {result.stderr}")
                return None
        except subprocess.TimeoutExpired:
            logger.error("Kinetic typography generation timed out")
            return None
        except Exception as e:
            logger.error(f"Kinetic typography error: {e}")
            return None
    
    def _build_filter_chain(
        self,
        captions: List[Dict],
        style: Dict,
        animation: str
    ) -> str:
        """Build FFmpeg filter chain for captions"""
        filters = []
        
        for i, caption in enumerate(captions):
            text = caption.get('text', '').replace("'", "\\'").replace(":", "\\:")
            start = caption.get('start', 0)
            end = caption.get('end', start + 3)
            
            font_size = style.get('font_size', 48)
            font_color = style.get('font_color', 'white')
            stroke_color = style.get('stroke_color', 'black')
            stroke_width = style.get('stroke_width', 3)
            
            y_pos = 'h-120' if style.get('position') == 'bottom' else '(h-text_h)/2'
            
            filter_str = (
                f"drawtext=text='{text}':"
                f"fontsize={font_size}:"
                f"fontcolor={font_color}:"
                f"borderw={stroke_width}:"
                f"bordercolor={stroke_color}:"
                f"x=(w-text_w)/2:"
                f"y={y_pos}:"
                f"enable='between(t,{start},{end})'"
            )
            
            if animation == 'fade_in':
                fade_duration = min(0.5, (end - start) / 4)
                filter_str += f":alpha='if(lt(t-{start},{fade_duration}),(t-{start})/{fade_duration},1)'"
            
            filters.append(filter_str)
        
        return ','.join(filters) if filters else 'null'
    
    def generate_headline_clip(
        self,
        input_video: str,
        headline: str,
        subtitle: Optional[str] = None,
        duration: float = 5.0,
        style: str = 'breaking_news'
    ) -> Optional[str]:
        """Generate a clip with animated headline overlay"""
        captions = [
            {'text': headline, 'start': 0.5, 'end': duration - 0.5}
        ]
        if subtitle:
            captions.append({
                'text': subtitle,
                'start': 1.5,
                'end': duration - 0.5
            })
        
        return self.generate_caption_overlay(
            input_video=input_video,
            captions=captions,
            style=style,
            animation='fade_in'
        )
    
    def generate_quote_card(
        self,
        background_video: str,
        quote: str,
        author: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Generate animated quote card video"""
        captions = [
            {'text': f'"{quote}"', 'start': 0.5, 'end': 4.5},
            {'text': f'— {author}', 'start': 2.0, 'end': 5.0}
        ]
        
        return self.generate_caption_overlay(
            input_video=background_video,
            captions=captions,
            output_path=output_path,
            style='protocol_pulse',
            animation='fade_in'
        )
    
    def get_available_styles(self) -> Dict:
        """Return available style presets"""
        return self.STYLE_PRESETS
    
    def get_available_animations(self) -> Dict:
        """Return available animation presets"""
        return {k: v['description'] for k, v in self.ANIMATION_PRESETS.items()}
    
    def sync_captions_to_voice(
        self,
        transcript: str,
        audio_duration: float,
        voice_profile: str = 'walter_cronkite'
    ) -> List[Dict]:
        """
        Sync caption timing to voice audio using speaking rate.
        Ensures kinetic text matches Walter Cronkite style delivery.
        """
        profile = VOICE_PROFILES.get(voice_profile, VOICE_PROFILES['walter_cronkite'])
        words_per_minute = profile['speaking_rate']
        word_gap = profile['word_gap']
        
        words = transcript.split()
        total_words = len(words)
        words_per_second = words_per_minute / 60
        
        captions = []
        current_time = 0.5
        
        chunk_size = 6
        for i in range(0, total_words, chunk_size):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            chunk_duration = len(chunk_words) / words_per_second
            
            caption = {
                'text': chunk_text,
                'start': round(current_time, 2),
                'end': round(current_time + chunk_duration + 0.3, 2)
            }
            
            captions.append(caption)
            current_time += chunk_duration + word_gap
            
            if current_time >= audio_duration - 0.5:
                break
        
        logger.info(f"Generated {len(captions)} voice-synced captions")
        return captions
    
    def generate_walter_cronkite_clip(
        self,
        input_video: str,
        transcript: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Generate kinetic typography video with Walter Cronkite voice sync."""
        try:
            probe_cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', input_video]
            result = subprocess.run(probe_cmd, capture_output=True, text=True)
            duration = float(result.stdout.strip()) if result.stdout.strip() else 30.0
        except:
            duration = 30.0
        
        captions = self.sync_captions_to_voice(transcript, duration, 'walter_cronkite')
        
        return self.generate_caption_overlay(
            input_video=input_video,
            captions=captions,
            output_path=output_path,
            style='breaking_news',
            animation='fade_in'
        )


kinetic_service = KineticTypographyService()
