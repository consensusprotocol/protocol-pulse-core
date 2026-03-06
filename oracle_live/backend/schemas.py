from typing import List, Optional
from pydantic import BaseModel, Field

class OracleAskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[str] = None
    voice_id: Optional[str] = None
    interrupt_id: Optional[str] = None

class VisemeEvent(BaseModel):
    time: float
    viseme: int
    duration: float
    word: str = ""

class OracleAskResponse(BaseModel):
    answer_text: str
    audio_base64: str
    content_type: str = "audio/mpeg"
    duration: float
    generation_time: float
    viseme_timeline: List[VisemeEvent]
    mode: str = "viseme"
    conversation_id: Optional[str] = None
    interrupt_id: Optional[str] = None

class InterruptRequest(BaseModel):
    conversation_id: Optional[str] = None
    interrupt_id: Optional[str] = None

class InterruptResponse(BaseModel):
    ok: bool
    conversation_id: Optional[str] = None
    interrupt_id: Optional[str] = None
