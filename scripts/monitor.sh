#!/bin/bash

echo "📊 COB Chatbot Monitoring Dashboard"
echo "==================================="

# Check service status
echo ""
echo "🔄 Service Status:"
docker-compose ps

echo ""
echo "📈 Resource Usage:"
docker stats --no-stream $(docker-compose ps -q)

echo ""
echo "🔍 Health Checks:"
curl -s http://localhost:8000/api/health | python3 -m json.tool

echo ""
echo "💬 Active Conversations:"
curl -s http://localhost:8000/api/analytics | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Total Conversations: {data[\"metrics\"][\"total_conversations\"]}')
print(f'Active Conversations: {data[\"metrics\"].get(\"active_conversations\", \"N/A\")}')
print(f'Success Rate: {data[\"daily_report\"][\"completion_rate\"]}%')
print(f'Escalation Rate: {data[\"daily_report\"][\"escalation_rate\"]}%')
"

echo ""
echo "📚 Knowledge Base:"
curl -s http://localhost:8000/api/kb/search?query=test | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(f'Collection Size: {data[\"collection_info\"].get(\"points_count\", 0)} documents')
print(f'Search Results: {data[\"count\"]}')
"

echo ""
echo "🐳 Container Logs (last 5 lines each):"
for service in chatbot qdrant redis; do
    echo ""
    echo "$service:"
    docker-compose logs --tail=5 "$service" 2>/dev/null || echo "No logs available"
done