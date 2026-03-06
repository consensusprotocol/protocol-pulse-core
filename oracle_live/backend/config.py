import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str = os.getenv("ELEVENLABS_API_KEY", "")
    elevenlabs_voice_id: str = os.getenv("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9")
    elevenlabs_model_id: str = os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    oracle_bind: str = os.getenv("ORACLE_BIND", "0.0.0.0")
    oracle_port: int = int(os.getenv("ORACLE_PORT", "8202"))
    cors_origin: str = os.getenv("CORS_ORIGIN", "*")
    request_timeout_sec: float = float(os.getenv("REQUEST_TIMEOUT_SEC", "45"))
    max_text_len: int = int(os.getenv("MAX_TEXT_LEN", "1600"))
    log_level: str = os.getenv("LOG_LEVEL", "info")

settings = Settings()
