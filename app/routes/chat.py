from fastapi import APIRouter, HTTPException, Request
from typing import List
from datetime import datetime
import logging
import uuid
import asyncio

from ..models.chat import (
    ChatMessage, ChatResponse, Conversation, ConversationSummary, 
    CreateConversationRequest, UpdateConversationRequest, LegacyMessage, MessageRequest
)
from ..services.emotion_classifier import emotion_classifier
from ..services.llm_service import llm_service
from ..services.conversation_service import conversation_service
from ..services.request_queue import request_queue
from ..services.user_limiter import user_limiter
from ..utils.logger import save_chat_log

router = APIRouter()

# Conversation Management Endpoints
@router.post("/conversations", response_model=Conversation)
async def create_conversation(request: Request, body: CreateConversationRequest):
    """Create a new educational conversation (per-user)"""
    try:
        user_id = user_limiter.get_user_id_from_request(request)
        conversation = conversation_service.create_conversation(
            user_id=user_id,
            title=body.title,
            subject=body.subject,
            study_level=body.study_level
        )
        return conversation
    except Exception as e:
        logging.error(f"Error creating conversation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create conversation")

@router.get("/conversations", response_model=List[ConversationSummary])
async def get_all_conversations(request: Request):
    """Get all conversation summaries for the current user"""
    try:
        user_id = user_limiter.get_user_id_from_request(request)
        return conversation_service.get_all_conversations(user_id)
    except Exception as e:
        logging.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail="Failed to get conversations")

@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, request: Request):
    """Get a specific conversation for the current user"""
    user_id = user_limiter.get_user_id_from_request(request)
    conversation = conversation_service.get_conversation(conversation_id, user_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation

@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(conversation_id: str, request: Request, body: UpdateConversationRequest):
    """Update conversation title for the current user"""
    user_id = user_limiter.get_user_id_from_request(request)
    success = conversation_service.update_conversation_title(conversation_id, user_id, body.title)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Title updated successfully"}

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request):
    """Delete a conversation for the current user"""
    user_id = user_limiter.get_user_id_from_request(request)
    success = conversation_service.delete_conversation(conversation_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted successfully"}

@router.post("/conversations/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(conversation_id: str, request: Request, message: MessageRequest):
    """Send a message in a specific conversation with educational context (per-user)"""
    try:
        user_id = user_limiter.get_user_id_from_request(request)
        can_prompt, used, remaining = user_limiter.can_user_make_prompt(user_id)
        if not can_prompt:
            raise HTTPException(
                status_code=429, 
                detail=f"Daily prompt limit reached ({used}/3). Try again tomorrow to avoid additional charges."
            )
        conversation = conversation_service.get_conversation(conversation_id, user_id)
        warning = None
        if not conversation:
            # Auto-create a new conversation and warn the user
            conversation = conversation_service.create_conversation(user_id=user_id)
            warning = f"Conversation not found. A new conversation was created (id: {conversation.id})."
            conversation_id = conversation.id
        user_message = ChatMessage(
            content=message.content,
            sender="user"
        )
        conversation_service.add_message_to_conversation(conversation_id, user_id, user_message)
        import time
        total_start_time = time.time()
        try:
            user_id = user_limiter.get_user_id_from_request(request)
            can_prompt, used, remaining = user_limiter.can_user_make_prompt(user_id)
            if not can_prompt:
                raise HTTPException(
                    status_code=429, 
                    detail=f"Daily prompt limit reached ({used}/3). Try again tomorrow to avoid additional charges."
                )
            conversation = conversation_service.get_conversation(conversation_id, user_id)
            if not conversation:
                raise HTTPException(status_code=404, detail="Conversation not found")
            user_message = ChatMessage(
                content=message.content,
                sender="user"
            )
            conversation_service.add_message_to_conversation(conversation_id, user_id, user_message)
            import time
            total_start_time = time.time()
            # Get emotion classification with timing
            emotion_start_time = time.time()
            emotion, confidence, all_probs = emotion_classifier.classify_emotion(message.content)
            emotion_time_ms = (time.time() - emotion_start_time) * 1000
            # Get updated conversation for context (per-user)
            conversation = conversation_service.get_conversation(conversation_id, user_id)
            context_messages = []
            for msg in conversation.messages[-6:]:
                role = "user" if msg.sender == "user" else "assistant"
                context_messages.append({"role": role, "content": msg.content})
            # Generate educational AI response with timing and model tracking
            llm_start_time = time.time()
            llm_model_used = "unknown"
            api_key_ending = "unknown"
            async def generate_response():
                nonlocal llm_model_used, api_key_ending
                result = await llm_service.create_empathetic_response(
                    user_message=message.content,
                    emotion=emotion,
                    confidence=confidence,
                    context_messages=context_messages,
                    conversation_subject=conversation.subject
                )
                # Get the actual model and key that were used
                llm_model_used = getattr(llm_service, 'last_used_model', 'unknown')
                last_key = getattr(llm_service, 'last_used_key', '')
                api_key_ending = last_key[-6:] if last_key else "unknown"
                return result
            try:
                ai_content = await asyncio.wait_for(
                    request_queue.add_request(generate_response),
                    timeout=30.0  # Reasonable timeout
                )
            except asyncio.TimeoutError:
                logging.warning(f"AI response generation timed out for conversation {conversation_id}")
                ai_content = "I apologize, but the response took too long. Please try again."
            llm_time_ms = (time.time() - llm_start_time) * 1000
            # Create AI response message
            ai_message = ChatMessage(
                content=ai_content,
                sender="assistant",
                emotion=emotion,
                emotion_confidence=confidence
            )
            # Add AI message to conversation (per-user)
            conversation_service.add_message_to_conversation(conversation_id, user_id, ai_message)
            # Record the successful prompt for the user
            user_limiter.record_prompt(user_id)
            # Calculate total processing time
            total_time_ms = (time.time() - total_start_time) * 1000
            # Get system status for logging
            available_keys = len(llm_service.api_keys)
            blacklisted_keys = 0
            # Enhanced comprehensive logging
            save_chat_log(
                student_message=message.content,
                emotion=emotion,
                confidence=confidence,
                all_probs=all_probs,
                prompt=f"Conv:{conversation_id[:8]} | Emotion:{emotion} | Context:{len(context_messages)} msgs",
                ai_response=ai_content,
                # Enhanced data for research
                conversation_id=conversation_id,
                user_id=user_id,
                emotion_time_ms=round(emotion_time_ms, 2),
                llm_model=llm_model_used,
                api_key_ending=api_key_ending,
                llm_time_ms=round(llm_time_ms, 2),
                total_time_ms=round(total_time_ms, 2),
                available_keys=available_keys,
                blacklisted_keys=blacklisted_keys,
                system_load="normal" if total_time_ms < 5000 else "high",
                top_emotions=f"{emotion}({confidence:.3f})" + (f", {list(all_probs.keys())[:2]}" if isinstance(all_probs, dict) and len(all_probs) > 1 else "")
            )
            # If a warning was set, append it to the AI response
            response_content = ai_content
            if warning:
                response_content = f"⚠️ {warning}\n\n" + ai_content
            return ChatResponse(
                id=ai_message.id,
                content=response_content,
                emotion=emotion,
                emotion_confidence=confidence,
                timestamp=ai_message.timestamp
            )
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logging.error(f"Error in conversation message: {e}")
            logging.error(f"Full traceback: {error_details}")
            raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")
        user_message = message.message.strip()
        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        # Step 1: Classify emotion
        emotion, confidence, all_probs = emotion_classifier.classify_emotion(user_message)
        # Step 2: Generate empathetic response with minimal throttling
        ai_content = await llm_service.create_empathetic_response(user_message, emotion, confidence)
        # Record the successful prompt for the user
        user_limiter.record_prompt(user_id)
        # Return response
        return ChatResponse(
            id="legacy",
            content=ai_content,
            emotion=emotion,
            emotion_confidence=confidence,
            timestamp=None
        )
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logging.error(f"Error in legacy chat endpoint: {e}")
        logging.error(f"Full traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Failed to process legacy chat: {str(e)}")

@router.get("/api/keys-status")
async def get_keys_status():
    """Monitor API key blacklist status for emergency debugging"""
    import time
    from datetime import datetime
    
    # Clean up expired keys first
    llm_service._cleanup_blacklisted_keys()
    
    # Get blacklist status
    blacklisted_info = []
    for key, blacklist_until in llm_service.blacklisted_keys.items():
        remaining_seconds = max(0, blacklist_until - time.time())
        remaining_minutes = int(remaining_seconds / 60)
        
    # Blacklisting removed: all keys are always available
    available_keys = [f"...{key[-6:]}" for key in llm_service.api_keys]
    return {
        "total_keys": len(llm_service.api_keys),
        "available_keys": len(available_keys),
        "blacklisted_keys": 0,
        "blacklist_duration_minutes": 0,
        "available_key_endings": available_keys,
        "blacklisted_key_info": [],
        "current_models": llm_service.models
    }