# Customer Care AI Chatbot - API Documentation

## Overview
This document describes the REST API endpoints for the Customer Care AI Chatbot.

## Base URL
http://localhost:8000


## Authentication
Currently, no authentication is required for development. In production, API keys or JWT tokens would be used.

## Endpoints

### 1. Chat Interface
**Endpoint:** `GET /chat`
**Description:** Web-based chat interface
**Response:** HTML page

### 2. Chat API
**Endpoint:** `POST /api/chat`
**Description:** Main chat endpoint for processing messages

**Request Body:**
```json
{
  "message": "string (required)",
  "user_id": "string (optional)",
  "session_id": "string (optional)"
}

Response:
{
  "response": "string",
  "user_id": "string",
  "session_id": "string",
  "intent": "string",
  "needs_escalation": "boolean",
  "action_required": "boolean",
  "confidence": "number",
  "timestamp": "string",
  "response_time_ms": "number",
  "suggestions": ["string"]
}

3. Knowledge Base Search
Endpoint: GET /api/kb/search
Description: Search knowledge base directly

Query Parameters:
query: Search query (required)

top_k: Number of results (default: 3)

score_threshold: Relevance threshold (default: 0.3)

4. Appointment Management
4.1 Get All Appointments
Endpoint: GET /api/appointments
Description: Retrieve all appointments (PII masked)

4.2 Get User Appointments
Endpoint: GET /api/appointments/user/{user_id}
Description: Get appointments for specific user

4.3 Cancel Appointment
Endpoint: DELETE /api/appointments/{appointment_id}
Description: Cancel an appointment

5. Mock Appointment API (External)
Base URL: http://localhost:5001 (from mock_api.py)

5.1 Schedule Appointment
Endpoint: POST /api/appointments
Description: Mock endpoint for scheduling appointments

Request Body:

{
  "service_type": "string (e.g., 'consultation')",
  "date": "string (YYYY-MM-DD)",
  "time": "string (HH:MM AM/PM)",
  "customer_name": "string",
  "email": "string (valid email)",
  "phone": "string (optional)",
  "notes": "string (optional)"
}

Response:
{
  "success": true,
  "appointment_id": "APPT-XXXXXX",
  "message": "Appointment scheduled successfully",
  "scheduled_time": "string",
  "confirmation_email_sent": true
}

6. Health & Monitoring
6.1 Health Check
Endpoint: GET /api/health
Description: Comprehensive health check

6.2 Metrics
Endpoint: GET /api/metrics
Description: Prometheus metrics (for monitoring)

6.3 System Status
Endpoint: GET /api/system/status
Description: Detailed system status

7. Analytics
Endpoint: GET /api/analytics
Description: Get conversation analytics

Query Parameters:
start_date: Start date filter (optional)

end_date: End date filter (optional)

user_id: Filter by user (optional)

Error Responses
All endpoints may return the following error responses:

400 Bad Request:
{
  "error": "Validation error",
  "details": ["field: error message"]
}

404 Not Found:
{
  "error": "Resource not found",
  "resource": "appointment_id"
}

500 Internal Server Error:
{
  "error": "Internal server error",
  "error_id": "ERROR_ID",
  "message": "Please try again later"
}

Rate Limiting
Rate limit: 60 requests per minute per IP

Exceeded requests return HTTP 429


Security Notes
All PII (Personal Identifiable Information) is masked in logs and responses

Input sanitization is applied to all user inputs

Email validation is performed for appointment bookings

No sensitive data is stored in plain text



Testing the API
Using curl:

# Test chat endpoint
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, I need help"}'

# Test health check
curl http://localhost:8000/api/health

# Test knowledge base search
curl "http://localhost:8000/api/kb/search?query=product%20pricing"

Using Python requests:

import requests

response = requests.post(
    "http://localhost:8000/api/chat",
    json={"message": "Schedule an appointment"},
    timeout=10
)
print(response.json())

WebSocket Support (Optional)
For real-time chat, WebSocket endpoint is available at:

ws://localhost:8000/ws/chat

