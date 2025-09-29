import os
import csv
import time
import logging
from datetime import datetime

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "chat_logs.csv")

def setup_logging():
    """Setup logging configuration"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(LOG_DIR, 'app.log')),
            logging.StreamHandler()
        ]
    )

def save_chat_log(student_message: str, emotion: str, confidence: float, 
                  all_probs: dict, prompt: str, ai_response: str, 
                  **kwargs):
    """Save comprehensive chat interaction to CSV log for research analysis"""
    try:
        # Ensure logs directory exists
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        # Check if file exists to write headers
        file_exists = os.path.exists(LOG_FILE)
        
        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    # Basic interaction data
                    "timestamp", "datetime", "student_message", "ai_response",
                    # Emotion classification data
                    "predicted_emotion", "emotion_confidence", "top_3_emotions", "classifier_model",
                    "emotion_classification_time_ms",
                    # LLM response data
                    "llm_model_used", "api_key_used", "llm_response_time_ms", 
                    "total_processing_time_ms",
                    # Context data
                    "conversation_id", "user_id", "prompt_sent",
                    # System status
                    "available_keys", "blacklisted_keys", "system_load"
                ])
            
            writer.writerow([
                # Basic interaction data
                int(time.time()), 
                datetime.now().isoformat(),
                student_message, 
                ai_response,
                # Emotion classification data
                emotion, 
                confidence,
                kwargs.get('top_emotions', str(all_probs)),
                kwargs.get('classifier_model', 'ZenyxS/indobert-emotion-emotionclf'),
                kwargs.get('emotion_time_ms', 0),
                # LLM response data
                kwargs.get('llm_model', 'unknown'),
                kwargs.get('api_key_ending', 'unknown'),
                kwargs.get('llm_time_ms', 0),
                kwargs.get('total_time_ms', 0),
                # Context data
                kwargs.get('conversation_id', 'unknown'),
                kwargs.get('user_id', 'unknown'),
                prompt,
                # System status
                kwargs.get('available_keys', 0),
                kwargs.get('blacklisted_keys', 0),
                kwargs.get('system_load', 'normal')
            ])
        
        # Enhanced console logging for debugging
        logging.info(f"📝 CHAT LOG | User: {kwargs.get('user_id', 'unknown')[:8]}... | "
                    f"Emotion: {emotion}({confidence:.2f}) | "
                    f"Model: {kwargs.get('llm_model', 'unknown')} | "
                    f"Key: ...{kwargs.get('api_key_ending', 'unknown')} | "
                    f"Time: {kwargs.get('total_time_ms', 0)}ms | "
                    f"Keys: {kwargs.get('available_keys', 0)}/{kwargs.get('available_keys', 0) + kwargs.get('blacklisted_keys', 0)}")
        
    except Exception as e:
        logging.error(f"Error saving enhanced chat log: {e}")