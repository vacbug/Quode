"""
Rate limiting and anti-bot measures for data collection.
Implements sophisticated rate limiting with exponential backoff and user agent rotation.
"""

import time
import random
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from loguru import logger

from ..utils.config import get_config
from ..utils.helpers import get_random_delay, exponential_backoff_delay


@dataclass
class RequestInfo:
    """Information about a request for rate limiting."""
    timestamp: datetime
    user_agent: str
    success: bool
    response_time: float


class RateLimiter:
    """Advanced rate limiter with anti-bot measures."""
    
    def __init__(self):
        """Initialize the rate limiter."""
        self.config = get_config().rate_limiting
        self.request_history = deque(maxlen=1000)
        self.user_agents = self.config.user_agents or self._get_default_user_agents()
        self.current_user_agent_index = 0
        self.last_request_time = None
        self.consecutive_failures = 0
        self.backoff_multiplier = 1.0
        
        logger.info(f"Rate limiter initialized with {len(self.user_agents)} user agents")
    
    def _get_default_user_agents(self) -> List[str]:
        """Get default user agents if none provided in config."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15"
        ]
    
    def get_user_agent(self) -> str:
        """Get a random user agent."""
        if self.user_agents:
            return random.choice(self.user_agents)
        return self._get_default_user_agents()[0]
    
    def rotate_user_agent(self) -> str:
        """Rotate to the next user agent."""
        if not self.user_agents:
            return self.get_user_agent()
        
        self.current_user_agent_index = (self.current_user_agent_index + 1) % len(self.user_agents)
        return self.user_agents[self.current_user_agent_index]
    
    def calculate_delay(self) -> float:
        """Calculate the delay before the next request."""
        base_delay = self.config.delay_between_requests
        
        # Apply exponential backoff if enabled and there are consecutive failures
        if self.config.exponential_backoff and self.consecutive_failures > 0:
            backoff_delay = exponential_backoff_delay(
                self.consecutive_failures,
                base_delay,
                self.config.max_delay
            )
            delay = max(base_delay, backoff_delay)
        else:
            delay = base_delay
        
        # Add some randomness to avoid detection
        jitter = random.uniform(0.5, 1.5)
        final_delay = delay * jitter
        
        # Ensure delay doesn't exceed maximum
        final_delay = min(final_delay, self.config.max_delay)
        
        return final_delay
    
    def should_wait(self) -> bool:
        """Check if we should wait before making the next request."""
        if not self.last_request_time:
            return False
        
        time_since_last = (datetime.now() - self.last_request_time).total_seconds()
        required_delay = self.calculate_delay()
        
        return time_since_last < required_delay
    
    def wait_if_needed(self) -> None:
        """Wait if necessary to respect rate limits."""
        if self.should_wait():
            wait_time = self.calculate_delay()
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
    
    def record_request(self, success: bool, response_time: float, user_agent: str) -> None:
        """Record a request for rate limiting purposes."""
        request_info = RequestInfo(
            timestamp=datetime.now(),
            user_agent=user_agent,
            success=success,
            response_time=response_time
        )
        
        self.request_history.append(request_info)
        self.last_request_time = request_info.timestamp
        
        if success:
            self.consecutive_failures = 0
            self.backoff_multiplier = max(1.0, self.backoff_multiplier * 0.9)
        else:
            self.consecutive_failures += 1
            self.backoff_multiplier = min(10.0, self.backoff_multiplier * 1.5)
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get statistics about recent requests."""
        if not self.request_history:
            return {
                "total_requests": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "requests_per_minute": 0.0
            }
        
        now = datetime.now()
        recent_requests = [
            req for req in self.request_history
            if (now - req.timestamp).total_seconds() <= 60
        ]
        
        total_requests = len(self.request_history)
        successful_requests = sum(1 for req in self.request_history if req.success)
        success_rate = successful_requests / total_requests if total_requests > 0 else 0.0
        
        avg_response_time = sum(req.response_time for req in self.request_history) / total_requests if total_requests > 0 else 0.0
        requests_per_minute = len(recent_requests)
        
        return {
            "total_requests": total_requests,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "requests_per_minute": requests_per_minute,
            "consecutive_failures": self.consecutive_failures,
            "backoff_multiplier": self.backoff_multiplier
        }
    
    def is_rate_limited(self) -> bool:
        """Check if we're currently rate limited."""
        stats = self.get_request_stats()
        return stats["requests_per_minute"] >= self.config.requests_per_minute
    
    def reset(self) -> None:
        """Reset the rate limiter state."""
        self.request_history.clear()
        self.last_request_time = None
        self.consecutive_failures = 0
        self.backoff_multiplier = 1.0
        logger.info("Rate limiter state reset")


class AsyncRateLimiter(RateLimiter):
    """Asynchronous version of the rate limiter."""
    
    async def async_wait_if_needed(self) -> None:
        """Asynchronously wait if necessary to respect rate limits."""
        if self.should_wait():
            wait_time = self.calculate_delay()
            logger.debug(f"Async rate limiting: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
    
    async def async_record_request(self, success: bool, response_time: float, user_agent: str) -> None:
        """Asynchronously record a request."""
        self.record_request(success, response_time, user_agent)


class RequestSession:
    """Manages a session of requests with rate limiting."""
    
    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize the request session.
        
        Args:
            rate_limiter: Rate limiter instance. If None, creates a new one.
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self.session_start_time = datetime.now()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
    
    def __enter__(self):
        """Enter the session context."""
        logger.info("Starting request session")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the session context."""
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
        
        logger.info(f"Request session ended - Duration: {session_duration:.2f}s, "
                   f"Requests: {self.total_requests}, Success rate: {success_rate:.2%}")
    
    def make_request(self, request_func, *args, **kwargs):
        """
        Make a request with rate limiting.
        
        Args:
            request_func: Function to execute the request
            *args: Arguments for the request function
            **kwargs: Keyword arguments for the request function
        
        Returns:
            Result of the request function
        """
        import time
        
        self.total_requests += 1
        user_agent = self.rate_limiter.get_user_agent()
        
        # Wait if rate limiting is needed
        self.rate_limiter.wait_if_needed()
        
        # Make the request
        start_time = time.time()
        try:
            result = request_func(*args, **kwargs)
            response_time = time.time() - start_time
            
            # Record successful request
            self.rate_limiter.record_request(True, response_time, user_agent)
            self.successful_requests += 1
            
            logger.debug(f"Request successful - Response time: {response_time:.3f}s")
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Record failed request
            self.rate_limiter.record_request(False, response_time, user_agent)
            self.failed_requests += 1
            
            logger.warning(f"Request failed after {response_time:.3f}s: {e}")
            raise
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        session_duration = (datetime.now() - self.session_start_time).total_seconds()
        success_rate = self.successful_requests / self.total_requests if self.total_requests > 0 else 0.0
        
        return {
            "session_duration": session_duration,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "requests_per_second": self.total_requests / session_duration if session_duration > 0 else 0.0,
            **self.rate_limiter.get_request_stats()
        }


class AntiBotMeasures:
    """Implements various anti-bot detection measures."""
    
    def __init__(self):
        """Initialize anti-bot measures."""
        self.config = get_config().rate_limiting
        self.session_cookies = {}
        self.proxy_rotation = False
        self.headers_rotation = True
    
    def get_headers(self, user_agent: str) -> Dict[str, str]:
        """Get headers that mimic a real browser."""
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add some randomness to headers
        if random.random() > 0.5:
            headers['Cache-Control'] = 'max-age=0'
        
        if random.random() > 0.7:
            headers['DNT'] = '1'
        
        return headers
    
    def add_session_cookies(self, domain: str, cookies: Dict[str, str]) -> None:
        """Add cookies for a domain."""
        self.session_cookies[domain] = cookies
    
    def get_session_cookies(self, domain: str) -> Dict[str, str]:
        """Get cookies for a domain."""
        return self.session_cookies.get(domain, {})
    
    def should_rotate_proxy(self) -> bool:
        """Determine if proxy should be rotated."""
        return self.proxy_rotation and random.random() > 0.8
    
    def get_random_delay_pattern(self) -> float:
        """Get a random delay that mimics human behavior."""
        # Humans don't make requests at exactly regular intervals
        base_delay = self.config.delay_between_requests
        
        # Add some human-like randomness
        if random.random() > 0.7:
            # Occasionally take longer breaks
            return base_delay * random.uniform(2.0, 5.0)
        elif random.random() > 0.9:
            # Very occasionally take very long breaks
            return base_delay * random.uniform(5.0, 15.0)
        else:
            # Normal variation
            return base_delay * random.uniform(0.8, 1.2)
