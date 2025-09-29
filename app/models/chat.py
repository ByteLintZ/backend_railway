from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid

class ChatMessage(BaseModel):
    id: str = None
    content: str
    timestamp: datetime = None
    sender: str  # 'user' or 'assistant'
    emotion: Optional[str] = None
    emotion_confidence: Optional[float] = None
    
    def __init__(self, **data):
        if data.get('id') is None:
            data['id'] = str(uuid.uuid4())
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now()
        super().__init__(**data)

class ChatResponse(BaseModel):
    id: str
    content: str
    emotion: str
    emotion_confidence: float
    timestamp: datetime

class Conversation(BaseModel):
    id: str
    user_id: str  # New field for per-user isolation
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessage] = []
    subject: Optional[str] = None  # Educational subject
    study_level: Optional[str] = None  # Elementary, Middle, High School, etc.
    
class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    last_message: Optional[str] = None
    message_count: int = 0
    subject: Optional[str] = None
    dominant_emotion: Optional[str] = None

class CreateConversationRequest(BaseModel):
    title: Optional[str] = "Percakapan Baru"
    subject: Optional[str] = None
    study_level: Optional[str] = None

class UpdateConversationRequest(BaseModel):
    title: str

class EmotionResult(BaseModel):
    emotion: str
    confidence: float
    all_probabilities: dict = {}

class LegacyMessage(BaseModel):
    message: str
    timestamp: Optional[datetime] = None

class MessageRequest(BaseModel):
    content: str