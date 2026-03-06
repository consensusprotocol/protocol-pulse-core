import os
from dataclasses import dataclass, field

def _get_key(name: str) -> str:
    val = os.environ.get(name, "")
    if val:
        return val
    search_paths = [
        os.path.expanduser("~/protocol_pulse/oracle_briefing/.env"),
        os.path.expanduser("~/protocol_pulse/oracle/.env"),
        os.path.expanduser("~/protocol_pulse/.env"),
        os.path.expanduser("~/.env"),
    ]
    for path in search_paths:
        if os.path.exists(path):
            try:
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(name + "="):
                            v = line.split("=", 1)[1].strip()
                            return v.strip('"').strip("'")
            except Exception:
                pass
    return ""

@dataclass(frozen=True)
class Settings:
    elevenlabs_api_key: str = field(default_factory=lambda: _get_key("ELEVENLABS_API_KEY"))
    anthropic_api_key: str = field(default_factory=lambda: _get_key("ANTHROPIC_API_KEY"))
    elevenlabs_voice_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_VOICE_ID", "cgSgspJ2msm6clMCkdW9"))
    elevenlabs_model_id: str = field(default_factory=lambda: os.getenv("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5"))
    oracle_bind: str = field(default_factory=lambda: os.getenv("ORACLE_BIND", "0.0.0.0"))
    oracle_port: int = field(default_factory=lambda: int(os.getenv("ORACLE_PORT", "8200")))
    cors_origin: str = field(default_factory=lambda: os.getenv("CORS_ORIGIN", "*"))
    request_timeout_sec: float = field(default_factory=lambda: float(os.getenv("REQUEST_TIMEOUT_SEC", "45")))
    max_text_len: int = field(default_factory=lambda: int(os.getenv("MAX_TEXT_LEN", "1600")))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "info"))

settings = Settings()
