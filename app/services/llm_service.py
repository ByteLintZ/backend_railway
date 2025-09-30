import requests
import re
import logging
import time
import random
import asyncio
from typing import Optional, List, Dict
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class LLMService:
    def __init__(self):
        # Multiple API keys for 36 students emergency solution
        self.api_keys = [
            os.getenv("OPENROUTER_API_KEY_1", "").strip(),
            os.getenv("OPENROUTER_API_KEY_2", "").strip(),
            os.getenv("OPENROUTER_API_KEY_3", "").strip(),
            os.getenv("OPENROUTER_API_KEY_4", "").strip(),
            os.getenv("OPENROUTER_API_KEY_5", "").strip(),
            os.getenv("OPENROUTER_API_KEY_6", "").strip()
        ]
        # Remove empty keys and fallback to main key if needed
        self.api_keys = [k for k in self.api_keys if k]
        if not self.api_keys:
            fallback_key = os.getenv("OPENROUTER_API_KEY", "").strip()
            if fallback_key:
                self.api_keys = [fallback_key]
        
        # Debug: Print loaded API keys (last 6 chars only)
        print("[LLMService] Loaded API keys:", [k[-6:] for k in self.api_keys])
        import logging
        logging.info(f"[LLMService] Loaded API keys: {[k[-6:] for k in self.api_keys]}")

        self.current_key_index = 0
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        

        
        # Multiple free models - tested and reliable for 36 students
        self.models = [
            "mistralai/mistral-7b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-r1-0528-qwen3-8b:free",
            "z-ai/glm-4.5-air:free",
            "deepseek/deepseek-chat-v3.1:free"
        ]
        
        # Tracking for logging
        self.last_used_model = None
        self.last_used_key = None
        
        logging.info(f"LLMService initialized with {len(self.api_keys)} API keys and {len(self.models)} models")
    

    

    

    
    def get_next_api_key(self):
        """Get next API key in round-robin fashion, always rotating regardless of errors"""
        if not self.api_keys:
            raise Exception("No API keys available")
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def get_educational_system_prompt(self, emotion: str, subject: Optional[str] = None) -> str:
        """Get educational system prompt based on emotion and subject"""
        base_prompt = (
            "Kamu adalah EduBot 🎓, seorang guru AI yang sangat empatik, sabar, dan menyenangkan! "
            "PENTING: Kamu memiliki maksimal 1000 token untuk merespons. Pastikan jawaban kamu lengkap dan tidak terpotong di tengah kalimat. "
            "Jika topiknya panjang, buat ringkasan yang terstruktur atau tawarkan untuk melanjutkan di pesan berikutnya. "
            "Kamu membantu siswa belajar dengan cara yang interaktif dan penuh semangat. "
            "\nKarakteristik kamu:\n"
            "✨ Selalu positif dan mendukung siswa\n"
            "🎯 Memberikan penjelasan yang mudah dipahami\n"
            "💡 Menggunakan contoh praktis dan analogi menarik\n"
            "🎊 Merayakan setiap kemajuan siswa, sekecil apapun\n"
            "🌟 Memberikan tips belajar yang efektif\n"
            "📚 Menyediakan informasi yang akurat dan factual\n"
            "🤗 Memahami dan merespons emosi siswa dengan tepat\n"
            "\nSelalu gunakan:\n"
            "- Emoji yang sesuai untuk membuat percakapan lebih hidup\n"
            "- Bahasa Indonesia yang ramah dan hangat\n"
            "- Pujian dan dorongan positif\n"
            "- Contoh konkret untuk memperjelas konsep\n"
        )
        
        if subject:
            subject_prompts = {
                'matematika': '🔢 Kamu adalah spesialis matematika yang bisa menjelaskan konsep rumit dengan cara sederhana dan menyenangkan!',
                'fisika': '⚛️ Kamu adalah ahli fisika yang membuat eksperimen dan konsep fisika menjadi menarik dan mudah dipahami!',  
                'kimia': '🧪 Kamu adalah guru kimia yang passionate, selalu siap menjelaskan reaksi dan unsur dengan cara yang aman dan menarik!',
                'biologi': '🌿 Kamu adalah biologis yang cinta alam, siap menjelaskan kehidupan dan makhluk hidup dengan penuh antusiasme!',
                'sejarah': '📚 Kamu adalah pencerita sejarah yang hebat, membuat masa lalu hidup dan relevan untuk siswa!',
                'bahasa': '📝 Kamu adalah guru bahasa yang kreatif, membantu siswa mengekspresikan diri dengan lebih baik!',
                'geografi': '🌍 Kamu adalah penjelajah dunia yang membantu siswa memahami planet kita dengan cara yang menarik!',
            }
            base_prompt += f"\n{subject_prompts.get(subject.lower(), '📖 Kamu adalah guru yang passionate di bidang ' + subject + '!')}\n"
        
        emotion_templates = {
            "Senang": (
                "🎉 Siswa sedang merasa senang dan bersemangat! "
                "Manfaatkan energi positif ini untuk:\n"
                "- Berikan pujian yang tulus atas usaha mereka\n"
                "- Bagikan fakta menarik atau tips belajar yang fun\n"
                "- Dorong mereka untuk terus belajar dengan semangat\n"
                "- Gunakan emoji dan bahasa yang ceria 😊✨"
            ),
            
            "Netral": (
                "🤖 Siswa dalam keadaan netral dan siap belajar. "
                "Berikan respons yang:\n"
                "- Jelas dan informatif\n"
                "- Langsung ke inti materi\n"
                "- Menggunakan contoh praktis\n"
                "- Tetap hangat dan mendukung 📚"
            ),
            
            "Bingung": (
                "🤔 Siswa sedang merasa bingung dan butuh bantuan. "
                "Jadilah guru yang sabar dengan:\n"
                "- Akui kebingungan mereka dengan empati\n"
                "- Jelaskan step-by-step dari dasar\n"
                "- Gunakan analogi sederhana dan contoh konkret\n"
                "- Tanyakan apakah penjelasan sudah jelas 💡"
            ),
            
            "Frustrasi": (
                "😤 Siswa sedang frustrasi dan butuh dukungan. "
                "Berikan respons yang menenangkan:\n"
                "- Akui perasaan frustrasi mereka\n"
                "- Pecahkan masalah menjadi langkah kecil\n"
                "- Berikan dorongan positif\n"
                "- Ingatkan bahwa belajar adalah proses 💪"
            ),
            
            "Marah": (
                "😠 Siswa sedang marah dan perlu pendekatan hati-hati. "
                "Tetap tenang dan:\n"
                "- Akui perasaan mereka tanpa judgment\n"
                "- Berikan solusi praktis dan jelas\n"
                "- Hindari bahasa yang bisa memicu emosi\n"
                "- Fokus pada membantu menyelesaikan masalah 🤝"
            ),
        }
        
        return base_prompt + "\n" + emotion_templates.get(emotion, emotion_templates["Netral"])
    
    async def create_empathetic_response(self, user_message: str, emotion: str, confidence: float, 
                                 context_messages: Optional[List[Dict]] = None, 
                                 conversation_subject: Optional[str] = None) -> str:
        """Create educational empathetic response with API key rotation and retry logic for 36 students"""
        
        # Build conversation messages for chat API
        messages = [
            {
                "role": "system",
                "content": self.get_educational_system_prompt(emotion, conversation_subject)
            }
        ]
        
        # Add conversation context
        if context_messages:
            messages.extend(context_messages[:-1])  # Exclude the current message
        
        # Add current user message
        messages.append({
            "role": "user", 
            "content": user_message
        })
        
        # Add small random delay to reduce simultaneous API hits from 36 users
        initial_delay = random.uniform(0.05, 0.3)
        await asyncio.sleep(initial_delay)
        
        # Enhanced logging for emotion classification
        logging.info(f"🎭 EMOTION: {emotion} (confidence: {confidence:.3f}) - User: {user_message[:50]}{'...' if len(user_message) > 50 else ''}")
        
        # Retry configuration with API key rotation
        max_retries = len(self.api_keys) * 2  # Try each key twice
        base_delay = 0.5
        
        current_api_key = self.get_next_api_key()  # Start with next key
        selected_model = random.choice(self.models)  # Select model once for this request
        
        # Start timing for performance logging
        request_start_time = time.time()
        
        for attempt in range(max_retries):
            try:
                # Rotate API key every attempt to distribute load
                if attempt > 0:
                    current_api_key = self.get_next_api_key()
                
                headers = {
                    "Authorization": f"Bearer {current_api_key}",
                    "Content-Type": "application/json"
                }
                
                payload = {
                    "model": selected_model,  # Use consistently selected model
                    "messages": messages,
                    "max_tokens": 1000,
                    "temperature": 0.8,
                    "top_p": 0.9
                }
                
                # Enhanced logging for API attempt
                attempt_start_time = time.time()
                logging.info(f"🚀 ATTEMPT {attempt + 1}/{max_retries}: key=...{current_api_key[-6:]}, model={selected_model}")
                
                response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
                attempt_duration = time.time() - attempt_start_time
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        ai_response = data["choices"][0]["message"]["content"].strip()
                        total_duration = time.time() - request_start_time
                        
                        # Track successful model and key for logging
                        self.last_used_model = selected_model
                        self.last_used_key = current_api_key
                        
                        # Enhanced success logging
                        logging.info(f"✅ SUCCESS: {selected_model} via key ...{current_api_key[-6:]} "
                                   f"({attempt_duration:.2f}s attempt, {total_duration:.2f}s total) "
                                   f"- Response: {len(ai_response)} chars")
                        
                        return self._enhance_educational_response(ai_response, emotion, confidence)
                    else:
                        logging.warning(f"❌ EMPTY: {selected_model} returned empty response (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            continue
                        logging.warning("⚠️  FALLBACK: Using educational fallback after empty responses")
                        return self._get_fallback_response(emotion, user_message)
                        
                elif response.status_code == 429:  # Rate limited - just try next key, no blacklisting
                    logging.warning(f"🚫 RATE LIMITED: key ...{current_api_key[-6:]} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        # Small delay before trying next key
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                        continue
                    else:
                        logging.error("⚠️  All attempts exhausted - using fallback")
                        return self._get_rate_limit_fallback(emotion)
                        
                elif response.status_code >= 500:  # Server errors
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logging.warning(f"Server error {response.status_code}, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logging.error(f"Server error on final attempt: {response.status_code}")
                        return self._get_fallback_response(emotion, user_message)
                        
                else:
                    error_text = response.text[:200] + "..." if len(response.text) > 200 else response.text
                    logging.error(f"❌ HTTP {response.status_code}: {selected_model} via key ...{current_api_key[-6:]} "
                                f"({attempt_duration:.2f}s) - {error_text}")
                    
                    if attempt < max_retries - 1:
                        continue  # Try next key
                    logging.warning("⚠️  FALLBACK: Using educational fallback after all HTTP errors")
                    return self._get_fallback_response(emotion, user_message)
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Request timeout, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logging.error("Request timeout on final attempt")
                    return self._get_timeout_fallback(emotion)
                    
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Connection error, retrying in {delay:.2f}s... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    logging.error("Connection error on final attempt")
                    return self._get_connection_fallback(emotion)
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logging.warning(f"Unexpected error: {e}, retrying in {delay}s... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(delay)
                    continue
                else:
                    logging.error(f"Unexpected error on final attempt: {e}")
                    return self._get_fallback_response(emotion, user_message)
        
        # This should never be reached, but just in case
        return self._get_fallback_response(emotion, user_message)
    
    def _enhance_educational_response(self, response: str, emotion: str, confidence: float) -> str:
        """Enhance response with educational elements"""
        # Add emotion confidence indicator for very high confidence
        if confidence > 0.85:
            emotion_emoji = {
                "Senang": "😊", "Netral": "🤖", "Bingung": "🤔", 
                "Frustrasi": "😤", "Marah": "😠"
            }.get(emotion, "🤖")
            
            response += f"\n\n{emotion_emoji} *Aku bisa merasakan kamu sedang {emotion.lower()} nih!*"
        
        # Add learning tip based on emotion
        learning_tips = {
            "Senang": "\n\n💡 **Tips**: Manfaatkan semangat positif ini untuk mempelajari topik baru!",
            "Bingung": "\n\n💡 **Tips**: Tidak apa-apa bingung, itu artinya otak kamu sedang bekerja keras!",
            "Frustrasi": "\n\n💡 **Tips**: Istirahat sebentar, lalu coba dengan pendekatan yang berbeda ya!",
            "Marah": "\n\n💡 **Tips**: Tarik nafas dalam-dalam, mari kita selesaikan ini bersama-sama."
        }
        
        if emotion in learning_tips and confidence > 0.7:
            response += learning_tips[emotion]
            
        return response
    
    def _get_fallback_response(self, emotion: str, user_message: str) -> str:
        """Enhanced educational fallback responses"""
        fallbacks = {
            "Senang": "🎉 Wah, senang banget denger semangat kamu! Aku siap membantu kamu belajar lebih banyak lagi. Ada yang ingin kamu tanyakan? 😊",
            "Netral": "📚 Halo! Aku EduBot, siap membantu kamu belajar dengan cara yang menyenangkan. Apa yang ingin kita pelajari hari ini? 🤖",
            "Bingung": "🤔 Aku paham kamu merasa bingung. Gak masalah kok! Mari kita pecahkan masalah ini step by step. Bisa ceritakan lebih detail tentang apa yang membingungkan? 💡",
            "Frustrasi": "😤 Aku tahu perasaan frustrasi itu tidak enak. Tapi ingat, setiap ahli pernah jadi pemula! Mari kita coba pendekatan yang lebih mudah ya. Kamu pasti bisa! 💪",
            "Marah": "😠 Aku paham kamu sedang kesal. Mari kita ambil nafas sejenak dan fokus menyelesaikan masalah ini bersama-sama. Aku di sini untuk membantu kamu. 🤝"
        }
        
        base_response = fallbacks.get(emotion, fallbacks["Netral"])
        
        # Add subject detection if possible
        if any(keyword in user_message.lower() for keyword in ['matematika', 'math', 'hitung']):
            base_response += "\n\n🔢 Oh, ini tentang matematika ya? Aku suka banget sama matematika!"
        elif any(keyword in user_message.lower() for keyword in ['fisika', 'physics']):
            base_response += "\n\n⚛️ Fisika nih! Seru banget, kita bisa bahas eksperimen dan rumus-rumus keren!"
        elif any(keyword in user_message.lower() for keyword in ['sejarah', 'history']):
            base_response += "\n\n📚 Sejarah! Aku punya banyak cerita menarik dari masa lalu!"
            
        return base_response
    
    def _get_rate_limit_fallback(self, emotion: str) -> str:
        """Specific fallback for rate limiting scenarios"""
        rate_limit_responses = {
            "Senang": "🎉 Maaf, servernya agak sibuk nih karena banyak teman yang antusias belajar seperti kamu! Tapi aku tetap senang banget bisa chat sama kamu. Coba lagi sebentar ya! 😊",
            "Netral": "🤖 Server sedang sibuk melayani banyak siswa yang sedang belajar. Silakan coba lagi dalam beberapa saat. Terima kasih atas kesabarannya! 📚",
            "Bingung": "🤔 Waduh, servernya lagi rame nih karena banyak yang bertanya seperti kamu! Jangan khawatir, coba tanya lagi sebentar ya. Aku pasti bantu jawab kebingungan kamu! 💡",
            "Frustrasi": "😤 Aku tahu ini bikin frustasi, server lagi sibuk banget. Tapi tenang, coba lagi sebentar dan aku pasti jawab dengan semangat! Kamu pasti bisa mengatasi ini! 💪",
            "Marah": "😠 Maaf ya kalau ini bikin kesal. Server sedang sibuk tapi aku tetap di sini untuk membantu. Mohon bersabar sebentar, aku akan segera membantu kamu! 🤝"
        }
        return rate_limit_responses.get(emotion, rate_limit_responses["Netral"])
    
    def _get_timeout_fallback(self, emotion: str) -> str:
        """Specific fallback for timeout scenarios"""
        timeout_responses = {
            "Senang": "🎉 Wah, semangatmu luar biasa! Tapi koneksinya agak lambat nih. Coba tanya lagi ya, aku pasti jawab dengan antusias! 😊",
            "Netral": "🤖 Koneksi agak lambat saat ini. Silakan ulangi pertanyaan kamu, aku siap membantu! 📚",
            "Bingung": "🤔 Hmm, sepertinya ada gangguan koneksi yang bikin proses jadi lambat. Jangan khawatir, coba lagi ya! Aku tetap siap bantu! 💡",
            "Frustrasi": "😤 Aku paham frustrasimu karena koneksi lambat. Tapi jangan menyerah! Coba lagi dan kita selesaikan masalah ini bersama! 💪",
            "Marah": "😠 Maaf koneksinya bermasalah dan bikin kesal. Aku tetap di sini untuk membantu, coba lagi sebentar ya! 🤝"
        }
        return timeout_responses.get(emotion, timeout_responses["Netral"])
    
    def _get_connection_fallback(self, emotion: str) -> str:
        """Specific fallback for connection error scenarios"""
        connection_responses = {
            "Senang": "🎉 Semangat belajarmu luar biasa! Sayangnya ada masalah koneksi sebentar. Tapi tetap semangat ya, coba lagi! 😊",
            "Netral": "🤖 Terjadi gangguan koneksi. Silakan coba lagi dalam beberapa saat. Aku akan siap membantu! 📚",
            "Bingung": "🤔 Ada gangguan teknis yang bikin koneksi terputus. Gak usah tambah bingung, coba lagi aja ya! Aku pasti bantu! 💡",
            "Frustrasi": "😤 Aku tahu gangguan koneksi ini bikin tambah frustasi. Tapi kita jangan menyerah! Coba lagi dan mari selesaikan bersama! 💪",
            "Marah": "😠 Maaf banget ada masalah teknis yang bikin gangguan. Aku tetap di sini untuk membantu, coba lagi ya! 🤝"
        }
        return connection_responses.get(emotion, connection_responses["Netral"])
    
    def _get_intelligent_fallback(self, user_message: str, emotion: str) -> str:
        """Smart fallbacks based on message content when API is unavailable"""
        message_lower = user_message.lower()
        
        # Math related
        if any(word in message_lower for word in ['matematika', 'hitung', 'rumus', 'angka', 'math']):
            return f"🔢 Aku lihat kamu bertanya tentang matematika! Meski server lagi sibuk, aku tetap semangat bantu kamu belajar matematika. Coba tanya lagi sebentar ya! 📐"
        
        # Science related  
        if any(word in message_lower for word in ['fisika', 'kimia', 'biologi', 'sains', 'science']):
            return f"🔬 Wah, pertanyaan sains nih! Server lagi rame, tapi aku excited bantu kamu explore dunia sains. Tunggu sebentar ya! ⚗️"
        
        # Language related
        if any(word in message_lower for word in ['bahasa', 'grammar', 'kata', 'kalimat']):
            return f"📝 Pertanyaan tentang bahasa ya! Aku suka banget bahas bahasa. Server lagi sibuk, tapi coba lagi sebentar! 🗣️"
        
        # History related
        if any(word in message_lower for word in ['sejarah', 'history', 'masa lalu']):
            return f"📚 Sejarah adalah pelajaran favorit ku! Server lagi sibuk, tapi aku punya banyak cerita menarik untuk kamu. Coba lagi ya! 🏛️"
        
        # General educational
        return self._get_rate_limit_fallback(emotion)

# Global instance
llm_service = LLMService()