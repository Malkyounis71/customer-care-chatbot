#!/usr/bin/env python
import sys
import os
from pathlib import Path

# Add the src directory to Python path
src_dir = Path(__file__).parent
sys.path.insert(0, str(src_dir))

def main():
    """Start the application"""
    import uvicorn
    from app.config.settings import settings
    
    print("=" * 50)
    print(f"Starting {settings.app_name}")
    print(f"Environment: {'Development' if settings.debug else 'Production'}")
    print(f"Host: {settings.host}:{settings.port}")
    print(f"Knowledge base: {settings.knowledge_base_path}")
    print("=" * 50)
    
    # Create necessary directories
    create_directories()
    
    # Start the application
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )

def create_directories():
    """Create necessary directories"""
    from app.config.settings import settings
    
    directories = [
        settings.knowledge_base_path,
        settings.logs_path,
        Path("data/qdrant_storage"),
        Path("data/redis_data")
    ]
    
    for directory in directories:
        if isinstance(directory, str):
            directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        print(f"✓ Directory ready: {directory}")

if __name__ == "__main__":
    main()