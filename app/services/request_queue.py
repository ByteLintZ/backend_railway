import asyncio
import logging
from typing import Callable, Any
from datetime import datetime

class SimpleStatsTracker:
    """
    Simple statistics tracker with MINIMAL rate limiting to avoid OpenRouter 429s.
    Just enough throttling to prevent rate limits, but much faster than before.
    """
    
    def __init__(self):
        self.total_requests = 0
        self.failed_requests = 0
        self._lock = asyncio.Lock()
        # Very gentle rate limiting - just enough to avoid 429s
        self._semaphore = asyncio.Semaphore(50)  # Max 50 concurrent - more than enough for 36 users
        
        logging.info("SimpleStatsTracker initialized - MINIMAL throttling to avoid rate limits")
    
    async def add_request(self, request_func: Callable, *args, **kwargs) -> Any:
        """
        Execute with minimal rate limiting - just enough to avoid OpenRouter 429s.
        Much faster than the old queue, but prevents API abuse.
        """
        async with self._semaphore:  # Limit to 50 concurrent
            async with self._lock:
                self.total_requests += 1
            
            try:
                # Execute with minimal throttling
                result = await request_func(*args, **kwargs)
                return result
                
            except Exception as e:
                async with self._lock:
                    self.failed_requests += 1
                logging.error(f"Request failed: {e}")
                raise
    
    def get_stats(self) -> dict:
        """Get basic statistics - no queue info since there's no queue!"""
        return {
            "mode": "minimal_throttling",
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.total_requests - self.failed_requests) / max(self.total_requests, 1) * 100,
            "message": "Minimal throttling - 50 concurrent max to avoid OpenRouter 429s",
            "timestamp": datetime.now().isoformat()
        }

# Global "queue" instance - but it's really just a stats tracker now!
request_queue = SimpleStatsTracker()