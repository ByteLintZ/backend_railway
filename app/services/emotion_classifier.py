from transformers import pipeline
import logging

class EmotionClassifier:
    def __init__(self):
        self.model_id = "ZenyxS/indobert-emotion-emotionclf"
        self.clf = None
        self._load_model()
    
    def _load_model(self):
        """Load the emotion classification model"""
        try:
            self.clf = pipeline("text-classification", model=self.model_id, tokenizer=self.model_id)
            logging.info("Emotion classifier loaded successfully")
        except Exception as e:
            logging.error(f"Error loading emotion classifier: {e}")
            raise
    
    def classify_emotion(self, text: str):
        """Classify emotion from text with enhanced logging"""
        import time
        
        try:
            # Time the classification
            start_time = time.time()
            result = self.clf(text, top_k=None)
            classification_time = time.time() - start_time
            
            if not result or len(result) == 0:
                logging.error("Empty result from emotion classifier")
                return "Unknown", 0.0, {}
                
            # Get all emotion scores for detailed logging
            all_emotions = {}
            for emotion_result in result:
                if isinstance(emotion_result, dict):
                    all_emotions[emotion_result['label']] = emotion_result['score']
            
            # Get top emotion
            top_result = result[0]
            if isinstance(top_result, dict):
                top_label = top_result['label']
                top_score = top_result['score']
            else:
                logging.error("Unexpected emotion classifier result format")
                return "Unknown", 0.0, {}
            
            # Enhanced logging with all emotion scores
            emotions_summary = ", ".join([f"{emotion}={score:.3f}" for emotion, score in sorted(all_emotions.items(), key=lambda x: x[1], reverse=True)[:3]])
            logging.info(f"🧠 CLASSIFIER: {top_label} ({top_score:.4f}) in {classification_time:.3f}s - Top 3: {emotions_summary}")
            
            return top_label, top_score, all_emotions
            
        except Exception as e:
            logging.error(f"❌ CLASSIFIER ERROR: {e}")
            return "Unknown", 0.0, {}

# Global instance
emotion_classifier = EmotionClassifier()