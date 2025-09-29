import json
import os
import uuid
from typing import List, Optional, Dict
from datetime import datetime
from ..models.chat import Conversation, ConversationSummary, ChatMessage

class ConversationService:
    def _get_user_dir(self, user_id: str) -> str:
        user_dir = os.path.join(self.conversations_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    def __init__(self):
        self.conversations_dir = "data/conversations"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories if they don't exist"""
        os.makedirs(self.conversations_dir, exist_ok=True)
        
    def _get_conversation_file(self, conversation_id: str, user_id: str = None) -> str:
        if user_id is not None:
            user_dir = self._get_user_dir(user_id)
            return os.path.join(user_dir, f"{conversation_id}.json")
        else:
            return os.path.join(self.conversations_dir, f"{conversation_id}.json")
    
    def _generate_title(self, first_message: str) -> str:
        """Generate an educational title from the first message"""
        # Educational keywords to detect subject
        subjects = {
            'matematika': '🔢 Matematika',
            'fisika': '⚛️ Fisika', 
            'kimia': '🧪 Kimia',
            'biologi': '🌿 Biologi',
            'sejarah': '📚 Sejarah',
            'bahasa': '📝 Bahasa',
            'geografi': '🌍 Geografi',
            'ekonomi': '💰 Ekonomi',
            'sains': '🔬 Sains'
        }
        
        # Check for educational subjects
        message_lower = first_message.lower()
        for keyword, subject in subjects.items():
            if keyword in message_lower:
                return f"{subject}: {first_message[:30]}..."
        
        # Default educational title
        words = first_message.split()[:6]
        title = " ".join(words)
        if len(first_message.split()) > 6:
            title += "..."
        return f"📖 {title[:45]}"
    
    def create_conversation(self, user_id: str, title: Optional[str] = None, subject: Optional[str] = None, 
        study_level: Optional[str] = None) -> Conversation:
        """Create a new educational conversation for a user"""
        conversation_id = str(uuid.uuid4())
        now = datetime.now()
        conversation = Conversation(
            id=conversation_id,
            user_id=user_id,
            title=title or "💭 Percakapan Baru",
            created_at=now,
            updated_at=now,
            messages=[],
            subject=subject,
            study_level=study_level
        )
        self._save_conversation(conversation, user_id)
        return conversation
    
    def get_conversation(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Get a specific conversation by ID for a user"""
        file_path = self._get_conversation_file(conversation_id, user_id)
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                data['created_at'] = datetime.fromisoformat(data['created_at'])
                data['updated_at'] = datetime.fromisoformat(data['updated_at'])
                for message in data.get('messages', []):
                    message['timestamp'] = datetime.fromisoformat(message['timestamp'])
                return Conversation(**data)
        except Exception as e:
            print(f"Error loading conversation {conversation_id} for user {user_id}: {e}")
            return None

    def get_all_conversations(self, user_id: str) -> List[ConversationSummary]:
        """Get all conversation summaries for a user"""
        summaries = []
        user_dir = self._get_user_dir(user_id)
        for filename in os.listdir(user_dir):
            if filename.endswith('.json'):
                conversation_id = filename[:-5]
                conversation = self.get_conversation(conversation_id, user_id)
                if conversation:
                    last_message = None
                    dominant_emotion = None
                    if conversation.messages:
                        user_messages = [msg for msg in conversation.messages if msg.sender == "user"]
                        if user_messages:
                            last_message = user_messages[-1].content[:80] + "..." if len(user_messages[-1].content) > 80 else user_messages[-1].content
                        recent_emotions = [msg.emotion for msg in conversation.messages[-5:] if msg.emotion]
                        if recent_emotions:
                            dominant_emotion = max(set(recent_emotions), key=recent_emotions.count)
                    summary = ConversationSummary(
                        id=conversation.id,
                        title=conversation.title,
                        created_at=conversation.created_at,
                        updated_at=conversation.updated_at,
                        last_message=last_message,
                        message_count=len(conversation.messages),
                        subject=conversation.subject,
                        dominant_emotion=dominant_emotion
                    )
                    summaries.append(summary)
        summaries.sort(key=lambda x: x.updated_at, reverse=True)
        return summaries
    
    def add_message_to_conversation(self, conversation_id: str, user_id: str, message: ChatMessage) -> bool:
        """Add a message to an existing conversation for a user"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        conversation.messages.append(message)
        conversation.updated_at = datetime.now()
        # Auto-generate educational title from first user message
        if (len([msg for msg in conversation.messages if msg.sender == "user"]) == 1 
            and conversation.title == "💭 Percakapan Baru"):
            conversation.title = self._generate_title(message.content)
        self._save_conversation(conversation, user_id)
        return True
    
    def update_conversation_title(self, conversation_id: str, user_id: str, title: str) -> bool:
        """Update conversation title for a user"""
        conversation = self.get_conversation(conversation_id, user_id)
        if not conversation:
            return False
        conversation.title = title
        conversation.updated_at = datetime.now()
        self._save_conversation(conversation, user_id)
        return True
    
    def delete_conversation(self, conversation_id: str, user_id: str) -> bool:
        """Delete a conversation for a user"""
        file_path = self._get_conversation_file(conversation_id, user_id)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                return True
            except Exception as e:
                print(f"Error deleting conversation {conversation_id} for user {user_id}: {e}")
                return False
        return False
    
    def _save_conversation(self, conversation: Conversation, user_id: str = None):
        """Save conversation to file in user directory"""
        if user_id is None:
            user_id = getattr(conversation, 'user_id', None)
        file_path = self._get_conversation_file(conversation.id, user_id)
        data = conversation.dict()
        data['created_at'] = conversation.created_at.isoformat()
        data['updated_at'] = conversation.updated_at.isoformat()
        for message in data['messages']:
            if isinstance(message['timestamp'], datetime):
                message['timestamp'] = message['timestamp'].isoformat()
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving conversation {conversation.id} for user {user_id}: {e}")

# Global instance
conversation_service = ConversationService()