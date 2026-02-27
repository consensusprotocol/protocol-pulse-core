
"""
Ultron 4090 GPU Service
=======================
Connects to your Ultron server (4x 4090 GPUs) via SSH for:
- Video rendering (medley generation)
- AI inference (Ollama for heavy tasks)
- FFmpeg processing

Configuration:
- ULTRON_HOST: SSH host (e.g., "192.168.1.100" or "ultron")
- ULTRON_USER: SSH user (default: "ultron")
- ULTRON_KEY_PATH: Path to SSH private key (optional if using ssh-agent)
"""

import os
import logging
import json
import subprocess
from datetime import datetime
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class UltronGPUService:
    """
    Interface to Ultron server's 4090 GPUs.
    """
    
    def __init__(self):
        self.host = os.environ.get("ULTRON_HOST", "ultron")
        self.user = os.environ.get("ULTRON_USER", "ultron")
        self.key_path = os.environ.get("ULTRON_KEY_PATH")
        self.project_path = os.environ.get("ULTRON_PROJECT_PATH", "/home/ultron/protocol_pulse")
        
        self.connected = False
        self._test_connection()
    
    def _test_connection(self):
        """Test SSH connection to Ultron."""
        try:
            result = self._ssh_command("echo 'connected'", timeout=10)
            if result and "connected" in result:
                self.connected = True
                logger.info(f"Ultron connection established: {self.user}@{self.host}")
            else:
                logger.warning("Ultron connection test failed")
        except Exception as e:
            logger.warning(f"Ultron not available: {e}")
    
    def _ssh_command(self, cmd: str, timeout: int = 60) -> Optional[str]:
        """Execute command on Ultron via SSH."""
        ssh_args = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=10"]
        
        if self.key_path:
            ssh_args.extend(["-i", self.key_path])
        
        ssh_args.append(f"{self.user}@{self.host}")
        ssh_args.append(cmd)
        
        try:
            result = subprocess.run(
                ssh_args,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"SSH command failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"SSH command timed out: {cmd[:50]}...")
            return None
        except Exception as e:
            logger.error(f"SSH error: {e}")
            return None
    
    def get_gpu_status(self) -> List[Dict]:
        """Get status of all GPUs on Ultron."""
        if not self.connected:
            return []
        
        cmd = "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader"
        result = self._ssh_command(cmd)
        
        if not result:
            return []
        
        gpus = []
        for line in result.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "memory_used": parts[2],
                    "memory_total": parts[3],
                    "utilization": parts[4]
                })
        
        return gpus
    
    def render_medley(self, config: Dict) -> Dict:
        """
        Trigger medley video render on Ultron GPU 1.
        
        config:
            duration: int (seconds)
            output_name: str
            clips: list of clip paths (optional)
        """
        if not self.connected:
            return {"success": False, "error": "Ultron not connected"}
        
        duration = config.get("duration", 60)
        output_name = config.get("output_name", f"medley_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp4")
        
        cmd = f"""
cd {self.project_path} && \
CUDA_VISIBLE_DEVICES=1 ./venv/bin/python medley_director.py \
    --output logs/{output_name} \
    --progress-file logs/{output_name}.progress \
    --report-file logs/{output_name}.report.json \
    --duration {duration}
"""
        
        logger.info(f"Starting medley render: {output_name}")
        
        # Run async (don't wait for completion)
        subprocess.Popen(
            ["ssh", "-o", "StrictHostKeyChecking=no", f"{self.user}@{self.host}", f"nohup {cmd} &"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return {
            "success": True,
            "output_name": output_name,
            "message": "Render started on GPU 1"
        }
    
    def get_render_progress(self, output_name: str) -> Dict:
        """Check progress of a render job."""
        if not self.connected:
            return {"progress": 0, "status": "disconnected"}
        
        progress_file = f"{self.project_path}/logs/{output_name}.progress"
        result = self._ssh_command(f"cat {progress_file} 2>/dev/null | tail -1")
        
        if not result:
            return {"progress": 0, "status": "unknown"}
        
        # Parse ffmpeg progress output
        try:
            # Look for "out_time=" or percentage
            if "out_time=" in result:
                # Parse time
                return {"progress": 50, "status": "rendering", "raw": result.strip()}
            elif "progress=end" in result:
                return {"progress": 100, "status": "complete"}
            else:
                return {"progress": 0, "status": "pending", "raw": result.strip()}
        except:
            return {"progress": 0, "status": "unknown"}
    
    def run_ollama_inference(self, prompt: str, model: str = "llama3.1:70b") -> Optional[str]:
        """
        Run inference on Ultron's Ollama instance.
        Uses GPU 0 (intelligence lane).
        """
        if not self.connected:
            return None
        
        # Escape the prompt for shell
        import shlex
        safe_prompt = shlex.quote(prompt)
        
        cmd = f"""
cd {self.project_path} && \
curl -s http://localhost:11434/api/generate -d '{{
    "model": "{model}",
    "prompt": {json.dumps(prompt)},
    "stream": false
}}' | jq -r '.response'
"""
        
        result = self._ssh_command(cmd, timeout=300)  # 5 min timeout for inference
        return result.strip() if result else None
    
    def check_ollama_status(self) -> Dict:
        """Check if Ollama is running on Ultron."""
        if not self.connected:
            return {"running": False, "error": "Not connected"}
        
        result = self._ssh_command("curl -s http://localhost:11434/api/tags")
        
        if result:
            try:
                data = json.loads(result)
                models = [m.get("name") for m in data.get("models", [])]
                return {"running": True, "models": models}
            except:
                pass
        
        return {"running": False, "error": "Ollama not responding"}


# Singleton
ultron_gpu_service = UltronGPUService()
