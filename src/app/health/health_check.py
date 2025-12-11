from typing import Dict, List
from datetime import datetime
import psutil
import httpx
from loguru import logger
from app.config.settings import settings

class HealthChecker:
    """Comprehensive health checking for all dependencies"""
    
    def __init__(self):
        self.dependencies = [
            ("qdrant", self._check_qdrant),
            ("redis", self._check_redis),
            ("api_service", self._check_api_service),
            ("disk_space", self._check_disk_space),
            ("memory", self._check_memory)
        ]
    
    async def check_health(self) -> Dict:
        """Check health of all dependencies"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": settings.APP_NAME,
            "version": "1.0.0",
            "dependencies": {}
        }
        
        # Check each dependency
        all_healthy = True
        for dep_name, check_func in self.dependencies:
            try:
                result = await check_func() if check_func.__code__.co_flags & 0x80 else check_func()
                health_status["dependencies"][dep_name] = result
                
                if not result.get("healthy", False):
                    all_healthy = False
                    health_status["status"] = "degraded"
                    
            except Exception as e:
                logger.error(f"Health check failed for {dep_name}: {e}")
                health_status["dependencies"][dep_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                all_healthy = False
                health_status["status"] = "unhealthy"
        
        # Add system metrics
        health_status["system"] = self._get_system_metrics()
        
        return health_status
    
    def _check_qdrant(self) -> Dict:
        """Check Qdrant connection"""
        from qdrant_client import QdrantClient
        
        try:
            client = QdrantClient(
                host=settings.QDRANT_URL,
                port=settings.QDRANT_PORT
            )
            collections = client.get_collections()
            
            return {
                "healthy": True,
                "collections_count": len(collections.collections),
                "response_time": "OK"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_redis(self) -> Dict:
        """Check Redis connection"""
        import redis
        
        try:
            r = redis.Redis.from_url(settings.REDIS_URL)
            r.ping()
            
            return {
                "healthy": True,
                "memory_used": r.info().get('used_memory_human', 'N/A'),
                "response_time": "OK"
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def _check_api_service(self) -> Dict:
        """Check external API service"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{settings.MOCK_API_URL}/api/health")
                
                return {
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": f"{response.elapsed.total_seconds():.3f}s"
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_disk_space(self) -> Dict:
        """Check disk space"""
        try:
            disk = psutil.disk_usage('/')
            free_percent = (disk.free / disk.total) * 100
            
            return {
                "healthy": free_percent > 10,  # At least 10% free
                "total_gb": round(disk.total / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "free_percent": round(free_percent, 2)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_memory(self) -> Dict:
        """Check memory usage"""
        try:
            memory = psutil.virtual_memory()
            used_percent = memory.percent
            
            return {
                "healthy": used_percent < 90,  # Less than 90% used
                "total_gb": round(memory.total / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "used_percent": round(used_percent, 2)
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _get_system_metrics(self) -> Dict:
        """Get system metrics"""
        return {
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime": round(time.time() - psutil.boot_time()),
            "process_count": len(psutil.pids())
        }