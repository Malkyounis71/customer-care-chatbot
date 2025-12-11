
# Customer Care AI Chatbot Agent

An intelligent conversational agent for COB Company capable of handling customer inquiries, scheduling appointments, and intelligently escalating to human agents.

## Features

✅ **Knowledge Base Queries** - RAG-powered answers from documents  
✅ **Appointment Scheduling** - Guided conversational flows  
✅ **Intent Classification** - Smart routing to appropriate handlers  
✅ **Human Escalation** - Intelligent frustration detection and transfer  
✅ **Web Interface** - Professional chat interface  
✅ **Analytics** - Conversation tracking and insights  
✅ **Mock API** - Simulated external services  
✅ **Docker Support** - Containerized deployment  

## Architecture
customer-care-chatbot/
├── src/ # Source code
│ ├── app/ # Main application
│ │ ├── chatbot/ # Chatbot core logic
│ │ │ ├── intent_classifier.py
│ │ │ ├── dialog_manager.py
│ │ │ ├── rag_engine.py
│ │ │ ├── escalation_handler.py # NEW: Human escalation
│ │ │ └── ...
│ │ ├── config/ # Configuration
│ │ ├── middleware/ # Rate limiting, etc.
│ │ └── ...
├── sample_data/ # Knowledge base documents
├── docs/ # Documentation
├── docker/ # Docker configuration

![Chatbot Architecture Diagram](architecture.png)

## Quick Start

### Prerequisites
- Python 3.9+
- Docker (optional)
- Qdrant vector database

### Installation

1. **Clone and setup:**
```bash
git clone <repository-url>
cd customer-care-chatbot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Start Qdrant (vector database):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

3.Start the application:
```bash
# Option 1: Using Python
python main.py

# Option 2: Using Docker
docker-compose up
```

### 4.Access the application:

Web Interface: http://localhost:8000/chat

API Documentation: http://localhost:8000/api/docs

Health Check: http://localhost:8000/api/health

### Configuration
## Environment Variables
Create .env file from .env.example:

```bash
cp .env.example .env
```
## Key variables:
```bash
# Application
DEBUG=True
PORT=8000
LOG_LEVEL=INFO

# Qdrant (Vector Database)
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=cob_knowledge_base

# Mock API
MOCK_API_URL=http://localhost:5001
```

## Knowledge Base Setup
Place your documents in sample_data/:

faqs.md - Frequently Asked Questions

products.md - Product information

Add more markdown files as needed

## Usage Examples
1. Knowledge Base Queries
```bash
User: "What are your business hours?"

Bot: "Our business hours are Monday-Friday, 9 AM to 6 PM..."

User: "Tell me about your enterprise product"

Bot: "COB Enterprise Suite includes CRM, analytics..."

```

## 2. Appointment Scheduling

```bash
User: "I want to schedule a consultation"

Bot: "I'd be happy to help! What type of service..."

[Guided conversation collects date, time, name, email]

```

## 3. Human Escalation
```bash
User: "I need to speak with a human"
Bot: "I'm connecting you with a specialist..."

User: "This isn't working!" (frustration detected)
Bot: "Let me transfer you to an agent who can help..."
```

### API Usage
## Chat Endpoint


curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Schedule appointment for tomorrow"}'

## Health Check
curl http://localhost:8000/api/health


### Monitoring
## Metrics
Prometheus metrics: http://localhost:8000/api/metrics

System status: http://localhost:8000/api/system/status

## Logs
Application logs: logs/app.log

Access logs: logs/access.log

### Deployment
## Docker Deployment

```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f
```

## Production Considerations
1. Set DEBUG=False in .env

2. Configure proper database connections

3. Set up SSL/TLS certificates

4. Configure firewall rules

5. Set up monitoring and alerts

### Development
## Project Structure
src/app/chatbot/ - Core chatbot logic

src/app/config/ - Configuration and templates

src/app/middleware/ - HTTP middleware

src/app/utils/ - Utility functions

sample_data/ - Knowledge base content

## Adding New Features
Add intent patterns in intent_classifier.py

Add response templates in config/response_templates.py

Add business rules in config/business_rules.py

Update knowledge base documents

### Troubleshooting
## Common Issues
1. Qdrant connection failed:
``` bash
# Check if Qdrant is running
docker ps | grep qdrant

# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant
```

2. Port already in use:
``` bash
# Change port in .env
PORT=8001
```

3. Missing dependencies:
``` bash
pip install -r requirements.txt
PORT=8001
```

### 4. Knowledge base not loading:

Check sample_data/ directory exists

Ensure documents are in markdown format

Check application logs for errors

### Getting Help
Check the logs in logs/ directory

Review API documentation at /api/docs

Check health endpoint at /api/health

### Contributing
Fork the repository

Create a feature branch

Add tests for new features

Submit a pull request






