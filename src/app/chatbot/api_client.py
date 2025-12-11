import httpx
import json
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime  
from loguru import logger
from app.config.settings import settings
from app.utils.circuit_breaker import CircuitBreaker

class APIClient:
    """Enhanced API client with retry logic and circuit breaker"""
    
    def __init__(self):
        self.base_url = settings.MOCK_API_URL
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
            transport=httpx.AsyncHTTPTransport(retries=3)
        )
        
        # Circuit breaker for external API calls
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exceptions=(httpx.RequestError,)
        )
    
    @CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    async def schedule_appointment(self, appointment_data: Dict) -> Dict[str, Any]:
        """Schedule appointment with retry logic"""
        try:
            url = f"{self.base_url}{settings.APPOINTMENT_API_ENDPOINT}"
            
            # Prepare payload with validation
            payload = self._validate_appointment_data(appointment_data)
            
            # Make request with retry
            response = await self._make_request_with_retry(
                "POST", url, json=payload, max_retries=3
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Appointment scheduled: {result.get('appointment_id')}")
                return {
                    "success": True,
                    "appointment_id": result.get('appointment_id'),
                    "message": "Appointment scheduled successfully",
                    "details": payload,
                    "timestamp": response.headers.get('date', '')
                }
            else:
                logger.error(f"API Error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}",
                    "details": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"Appointment scheduling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback": True
            }
    
    async def _make_request_with_retry(
        self, method: str, url: str, 
        max_retries: int = 3, **kwargs
    ) -> httpx.Response:
        """Make HTTP request with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, url, **kwargs)
                
                # Retry on server errors
                if 500 <= response.status_code < 600 and attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Retry {attempt + 1}/{max_retries} for {url}")
                    await asyncio.sleep(wait_time)
                    continue
                
                return response
                
            except (httpx.TimeoutException, httpx.NetworkError) as e:
                if attempt == max_retries - 1:
                    raise e
                
                wait_time = 2 ** attempt
                logger.warning(f"Network error, retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)
    
    def _validate_appointment_data(self, data: Dict) -> Dict:
        """Validate and sanitize appointment data"""
        required_fields = ['service_type', 'date', 'time', 'customer_name', 'email']
        
        validated = {}
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
            
            value = str(data[field]).strip()
            if not value:
                raise ValueError(f"Empty value for field: {field}")
            
            validated[field] = value
        
        # Optional fields
        optional_fields = ['phone', 'notes']
        for field in optional_fields:
            if field in data and data[field]:
                validated[field] = str(data[field]).strip()
        
        # Email validation
        import re
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, validated['email']):
            raise ValueError("Invalid email format")
        
        return validated
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def health_check(self) -> Dict:
        """Check API health"""
        try:
            response = await self.client.get(f"{self.base_url}/api/health", timeout=5.0)
            return {
                "healthy": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds()
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }