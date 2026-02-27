import os
import logging
import subprocess
import json
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class ClipsService:
    def __init__(self):
        self.clips_dir = 'static/clips'
        self.outro_path = 'static/videos/outro.mp4'
        self.opus_api_key = os.environ.get('OPUSCLIP_API_KEY')
        
        os.makedirs(self.clips_dir, exist_ok=True)
        
        self.ffmpeg_available = self._check_ffmpeg()
        
        logger.info(f"Clips service initialized. FFmpeg: {self.ffmpeg_available}, OpusClip: {bool(self.opus_api_key)}")
    
    def _check_ffmpeg(self) -> bool:
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def extract_clip(self, video_path: str, start_time: float, duration: float, output_name: str) -> Dict[str, Any]:
        if not self.ffmpeg_available:
            return {'success': False, 'error': 'FFmpeg not available'}
        
        try:
            output_path = os.path.join(self.clips_dir, f"{output_name}.mp4")
            
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(start_time),
                '-i', video_path,
                '-t', str(duration),
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                '-crf', '23',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return {
                    'success': True,
                    'output_path': output_path,
                    'duration': duration
                }
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Clip extraction error: {e}")
            return {'success': False, 'error': str(e)}
    
    def append_outro(self, clip_path: str, output_name: str = None) -> Dict[str, Any]:
        if not self.ffmpeg_available:
            return {'success': False, 'error': 'FFmpeg not available'}
        
        if not os.path.exists(self.outro_path):
            return {'success': False, 'error': 'Outro video not found'}
        
        try:
            if output_name:
                output_path = os.path.join(self.clips_dir, f"{output_name}_final.mp4")
            else:
                base = os.path.splitext(os.path.basename(clip_path))[0]
                output_path = os.path.join(self.clips_dir, f"{base}_final.mp4")
            
            concat_file = os.path.join(self.clips_dir, 'concat_list.txt')
            with open(concat_file, 'w') as f:
                f.write(f"file '{os.path.abspath(clip_path)}'\n")
                f.write(f"file '{os.path.abspath(self.outro_path)}'\n")
            
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-preset', 'fast',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            os.remove(concat_file)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return {
                    'success': True,
                    'output_path': output_path
                }
            else:
                return {'success': False, 'error': result.stderr}
                
        except Exception as e:
            logger.error(f"Outro append error: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_with_opus(self, youtube_url: str) -> Dict[str, Any]:
        if not self.opus_api_key:
            return {'success': False, 'error': 'OpusClip API key not configured'}
        
        try:
            import httpx
            
            response = httpx.post(
                'https://api.opus.pro/v1/clips',
                headers={
                    'Authorization': f'Bearer {self.opus_api_key}',
                    'Content-Type': 'application/json'
                },
                json={
                    'video_url': youtube_url,
                    'num_clips': 5,
                    'min_duration': 30,
                    'max_duration': 60
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'job_id': data.get('job_id'),
                    'status': 'processing'
                }
            else:
                return {'success': False, 'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"OpusClip API error: {e}")
            return {'success': False, 'error': str(e)}
    
    def check_opus_status(self, job_id: str) -> Dict[str, Any]:
        if not self.opus_api_key:
            return {'success': False, 'error': 'OpusClip API key not configured'}
        
        try:
            import httpx
            
            response = httpx.get(
                f'https://api.opus.pro/v1/clips/{job_id}',
                headers={'Authorization': f'Bearer {self.opus_api_key}'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'status': data.get('status'),
                    'clips': data.get('clips', [])
                }
            else:
                return {'success': False, 'error': f"API error: {response.status_code}"}
                
        except Exception as e:
            logger.error(f"OpusClip status check error: {e}")
            return {'success': False, 'error': str(e)}
    
    def download_opus_clips(self, clips: List[Dict]) -> List[Dict[str, Any]]:
        results = []
        
        for i, clip in enumerate(clips):
            try:
                import httpx
                
                clip_url = clip.get('url')
                if not clip_url:
                    continue
                
                filename = f"opus_clip_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i}.mp4"
                output_path = os.path.join(self.clips_dir, filename)
                
                response = httpx.get(clip_url, timeout=120)
                if response.status_code == 200:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    final_result = self.append_outro(output_path)
                    
                    results.append({
                        'success': True,
                        'original': output_path,
                        'with_outro': final_result.get('output_path') if final_result.get('success') else None,
                        'title': clip.get('title', f'Clip {i+1}'),
                        'score': clip.get('virality_score', 0)
                    })
                    
            except Exception as e:
                logger.error(f"Clip download error: {e}")
                results.append({'success': False, 'error': str(e)})
        
        return results
    
    def get_all_clips(self) -> List[Dict[str, Any]]:
        clips = []
        
        if not os.path.exists(self.clips_dir):
            return clips
        
        for filename in os.listdir(self.clips_dir):
            if filename.endswith('.mp4'):
                filepath = os.path.join(self.clips_dir, filename)
                stat = os.stat(filepath)
                
                clips.append({
                    'filename': filename,
                    'path': filepath,
                    'url': f'/static/clips/{filename}',
                    'size': stat.st_size,
                    'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    'is_final': '_final' in filename
                })
        
        clips.sort(key=lambda x: x['created'], reverse=True)
        return clips
    
    def get_status(self) -> Dict[str, Any]:
        clips = self.get_all_clips()
        return {
            'ffmpeg_available': self.ffmpeg_available,
            'opus_configured': bool(self.opus_api_key),
            'clips_count': len(clips),
            'final_clips_count': len([c for c in clips if c['is_final']])
        }

clips_service = ClipsService()
