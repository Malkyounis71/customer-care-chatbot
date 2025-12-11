import time
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge
import psutil
import os

# Prometheus metrics
REQUEST_COUNT = Counter('chatbot_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('chatbot_request_latency_seconds', 'Request latency')
INTENT_CLASSIFICATION_TIME = Histogram('intent_classification_seconds', 'Intent classification time')
ACTIVE_USERS = Gauge('chatbot_active_users', 'Active users')
ERROR_COUNT = Counter('chatbot_errors_total', 'Total errors')

class PerformanceMonitor:
    """Monitor chatbot performance metrics"""
    
    @staticmethod
    def track_latency(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            latency = time.time() - start_time
            REQUEST_LATENCY.observe(latency)
            return result
        return wrapper
    
    @staticmethod
    def get_system_metrics() -> dict:
        """Get system performance metrics"""
        process = psutil.Process(os.getpid())
        return {
            'cpu_percent': process.cpu_percent(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'threads': process.num_threads(),
            'active_users': len(process.connections())
        }