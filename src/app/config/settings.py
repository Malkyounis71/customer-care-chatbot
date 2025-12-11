import os
from typing import Optional
from pydantic_settings import BaseSettings
from loguru import logger
import json



class Settings(BaseSettings):
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # App Settings
    APP_NAME: str = "COB Customer Care Chatbot"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    
    # Security Settings 
    ENCRYPTION_KEY: str = "c3VwZXItc2VjcmV0LWtleS0xMjM0NTY3ODkwMTIzNDU2"
    SECRET_KEY: str = "your-secret-key-for-auth"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # NLP Settings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.3
    INTENT_CONFIDENCE_THRESHOLD: float = 0.6
    
    # Qdrant Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "cob_knowledge_base"
    QDRANT_VECTOR_SIZE: int = 384
    
    # Redis Settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Chat Settings
    MAX_HISTORY_LENGTH: int = 10
    SESSION_TIMEOUT: int = 1800  # 30 minutes
    
    # API Settings
    MOCK_API_URL: str = "http://localhost:8001"
    APPOINTMENT_API_ENDPOINT: str = "/api/schedule_appointment"
    
    # Sentiment Analysis
    SENTIMENT_THRESHOLD: float = -0.5

    #  Email Configuration with proper type annotations
    EMAIL_ENABLED: bool = True  
    EMAIL_HOST: str = "smtp.gmail.com"  
    EMAIL_PORT: int = 587  
    EMAIL_USE_TLS: bool = True  
    EMAIL_HOST_USER: str = "malkyounes71@gmail.com"  
    EMAIL_HOST_PASSWORD: str = "uscz gxlw pasx gbvw"  
    EMAIL_FROM: str = "malkyounes71@gmail.com"  
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

settings = Settings()

# DEBUG: Check what was loaded
print(f"\n=== SETTINGS LOADED ===")
print(f"ENCRYPTION_KEY in settings: {'SET' if settings.ENCRYPTION_KEY else 'NOT SET'}")
if settings.ENCRYPTION_KEY:
    print(f"Key length in settings: {len(settings.ENCRYPTION_KEY)}")

