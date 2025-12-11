from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from typing import Dict
from loguru import logger

class RateLimiter:
    """Rate limiter to prevent abuse"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = defaultdict(list)
    
    async def __call__(self, scope, receive, send):
        # Only apply to HTTP requests
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Create a request object to get client info
        request = Request(scope, receive)
        client_ip = request.client.host if request.client else "127.0.0.1"
        user_agent = request.headers.get("user-agent", "unknown")
        client_id = f"{client_ip}:{user_agent}"
        
        current_time = time.time()
        
        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if current_time - req_time < 60
        ]
        
        # Check rate limit
        if len(self.requests[client_id]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_id}")
            
            async def send_response(message):
                if message["type"] == "http.response.start":
                    # Send rate limit response
                    await send({
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"retry-after", b"60")
                        ]
                    })
                    await send({
                        "type": "http.response.body",
                        "body": b'{"error": "Rate limit exceeded", "message": "Too many requests. Please try again in a minute."}'
                    })
            
            await send_response(None)
            return
        
        # Add current request
        self.requests[client_id].append(current_time)
        
        await self.app(scope, receive, send)