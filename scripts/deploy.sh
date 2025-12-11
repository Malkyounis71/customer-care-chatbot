#!/bin/bash

set -e  # Exit on error

echo "🚀 Deploying COB Customer Care Chatbot..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Load environment
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating from template..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Please update .env file with your configuration and run again."
        exit 1
    else
        echo "❌ .env.example not found. Cannot proceed."
        exit 1
    fi
fi

# Source environment
source .env

# Create directories
echo "📁 Creating necessary directories..."
mkdir -p data/qdrant_storage data/redis_data logs static models

# Generate encryption key if not set
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "🔑 Generating encryption key..."
    ENCRYPTION_KEY=$(openssl rand -hex 32)
    echo "ENCRYPTION_KEY=$ENCRYPTION_KEY" >> .env
    echo "Generated and saved encryption key to .env"
fi

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check service health
echo "🏥 Checking service health..."
for service in chatbot qdrant redis mock-api; do
    if docker-compose ps | grep "$service" | grep -q "Up"; then
        echo "✅ $service is running"
    else
        echo "❌ $service failed to start"
        docker-compose logs "$service"
        exit 1
    fi
done

# Load initial knowledge base
echo "📚 Loading knowledge base..."
docker-compose exec chatbot python -c "
from app.knowledge_base.loader import KnowledgeBaseLoader
from app.chatbot.rag_engine import RAGEngine
import asyncio

async def load_kb():
    loader = KnowledgeBaseLoader()
    engine = RAGEngine()
    
    documents = loader.load_all_documents()
    for doc in documents:
        engine.index_document(doc)
    
    print(f'Loaded {len(documents)} documents')
    print('Knowledge base ready!')

asyncio.run(load_kb())
"

# Run tests
echo "🧪 Running tests..."
docker-compose exec chatbot python -m pytest tests/ -v

echo "========================================"
echo "✅ Deployment completed successfully!"
echo "========================================"
echo ""
echo "🌐 Services:"
echo "   Chatbot API:      http://localhost:${CHATBOT_PORT:-8000}"
echo "   API Documentation: http://localhost:${CHATBOT_PORT:-8000}/api/docs"
echo "   Web Interface:    http://localhost:${CHATBOT_PORT:-8000}/chat"
echo "   Qdrant:          http://localhost:6333/dashboard"
echo "   Redis Commander: http://localhost:8081"
echo ""
echo "📊 Monitoring (if enabled):"
echo "   Prometheus:      http://localhost:9090"
echo "   Grafana:         http://localhost:3000 (admin/${GRAFANA_PASSWORD:-admin})"
echo ""
echo "🔧 Management:"
echo "   View logs:       docker-compose logs -f"
echo "   Stop services:   docker-compose down"
echo "   Restart:         docker-compose restart"
echo "   Scale chatbot:   docker-compose up -d --scale chatbot=3"
echo ""
echo "📞 Test the chatbot:"
echo "   curl -X POST http://localhost:8000/api/chat \\"
echo "        -H 'Content-Type: application/json' \\"
echo "        -d '{\"message\": \"Hello, what can you help with?\"}'"
echo ""