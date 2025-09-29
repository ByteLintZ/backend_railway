import time
import logging
import os
from collections import defaultdict, deque
from typing import Dict, Optional
from datetime import datetime, timedelta

PROMPT_LIMIT_ENABLED = os.getenv("PROMPT_LIMIT_ENABLED", "true").lower() == "true"

class UserPromptLimiter:
    """
    Service to limit the number of prompts per user to prevent excessive API usage.
    Tracks prompts per user and enforces daily limits.
    """
    
    def __init__(self, max_prompts_per_user: int = 3, reset_hours: int = 24):
        self.max_prompts_per_user = max_prompts_per_user
        self.reset_hours = reset_hours
        
        # Track user prompts with timestamps
        self.user_prompts: Dict[str, deque] = defaultdict(deque)
        
        logging.info(f"UserPromptLimiter initialized: {max_prompts_per_user} prompts per user, resets every {reset_hours} hours")
    
    def get_user_id_from_request(self, request) -> str:
        """
        Extract user identifier from Authorization header (token).
        In production, this should be a secure, unique token per user.
        """
        auth_header = getattr(request, 'headers', {}).get('authorization')
        if auth_header:
            # Expecting 'Bearer <token>' or just the token
            if auth_header.lower().startswith('bearer '):
                token = auth_header[7:].strip()
            else:
                token = auth_header.strip()
            if token:
                return token
        # Ultimate fallback - use a default identifier
        return "unknown_user"
    
    def _cleanup_old_prompts(self, user_id: str):
        """Remove prompts older than reset_hours"""
        cutoff_time = time.time() - (self.reset_hours * 3600)
        
        while self.user_prompts[user_id] and self.user_prompts[user_id][0] < cutoff_time:
            self.user_prompts[user_id].popleft()
    
    def can_user_make_prompt(self, user_id: str) -> tuple[bool, int, int]:
        """
        Check if user can make another prompt.
        Returns: (can_make_prompt, prompts_used, prompts_remaining)
        """
        if not PROMPT_LIMIT_ENABLED:
            # Unlimited prompts if toggle is off
            return True, 0, self.max_prompts_per_user

        self._cleanup_old_prompts(user_id)
        prompts_used = len(self.user_prompts[user_id])
        prompts_remaining = max(0, self.max_prompts_per_user - prompts_used)
        can_make_prompt = prompts_used < self.max_prompts_per_user
        return can_make_prompt, prompts_used, prompts_remaining
    
    def record_prompt(self, user_id: str) -> bool:
        """
        Record a prompt for the user.
        
        Returns:
            bool: True if prompt was recorded successfully, False if limit exceeded
        """
        can_prompt, used, remaining = self.can_user_make_prompt(user_id)
        
        if not can_prompt:
            logging.warning(f"User {user_id} exceeded prompt limit ({used}/{self.max_prompts_per_user})")
            return False
        
        # Record the prompt with current timestamp
        self.user_prompts[user_id].append(time.time())
        logging.info(f"User {user_id} made prompt {used + 1}/{self.max_prompts_per_user}")
        
        return True
    
    def get_user_stats(self, user_id: str) -> dict:
        """Get current stats for a user"""
        self._cleanup_old_prompts(user_id)
        
        can_prompt, used, remaining = self.can_user_make_prompt(user_id)
        
        # Calculate time until next reset if at limit
        next_reset = None
        if not can_prompt and self.user_prompts[user_id]:
            oldest_prompt = self.user_prompts[user_id][0]
            next_reset_time = oldest_prompt + (self.reset_hours * 3600)
            next_reset = datetime.fromtimestamp(next_reset_time).isoformat()
        
        return {
            "user_id": user_id,
            "prompts_used": used,
            "prompts_remaining": remaining,
            "max_prompts": self.max_prompts_per_user,
            "can_make_prompt": can_prompt,
            "next_reset": next_reset,
            "reset_hours": self.reset_hours
        }
    
    def get_all_stats(self) -> dict:
        """Get stats for all users"""
        # Clean up all users
        for user_id in list(self.user_prompts.keys()):
            self._cleanup_old_prompts(user_id)
        
        total_users = len(self.user_prompts)
        total_prompts = sum(len(prompts) for prompts in self.user_prompts.values())
        
        users_at_limit = sum(1 for user_id in self.user_prompts.keys() 
                           if not self.can_user_make_prompt(user_id)[0])
        
        return {
            "total_active_users": total_users,
            "total_prompts_today": total_prompts,
            "users_at_limit": users_at_limit,
            "max_prompts_per_user": self.max_prompts_per_user,
            "reset_hours": self.reset_hours,
            "timestamp": datetime.now().isoformat()
        }

# Global limiter instance
user_limiter = UserPromptLimiter(max_prompts_per_user=3, reset_hours=24)