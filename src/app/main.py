from fastapi import FastAPI, HTTPException, Request, Depends, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, validator
from typing import Dict, List, Optional
import uuid
from datetime import datetime
import asyncio
import psutil
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.chatbot.dialog_manager import DialogManager
from app.chatbot.rag_engine import RAGEngine
from app.knowledge_base.loader import KnowledgeBaseLoader
from app.config.settings import settings
from app.utils.logger import setup_logger
from app.middleware.rate_limiter import RateLimiter
from app.health.health_check import HealthChecker
from app.analytics.conversation_analytics import ConversationAnalytics
from app.utils.security import SecurityManager
from app.utils.email_sender import email_sender

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="COB Company Customer Care AI Chatbot - Professional Customer Service Assistant",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    contact={
        "name": "COB Company Support",
        "email": "support@cobcompany.com",
    }
)

# Initialize components
dialog_manager = DialogManager()
rag_engine = RAGEngine()
kb_loader = KnowledgeBaseLoader()
health_checker = HealthChecker()
analytics = ConversationAnalytics()
security = SecurityManager(settings.ENCRYPTION_KEY)

# Initialize templates for web interface
import os
from pathlib import Path

# Initialize templates for web interface
# Get the directory where main.py is located
current_dir = Path(__file__).parent
templates_dir = current_dir / "templates"



templates = Jinja2Templates(directory=str(templates_dir))
# Track startup time
startup_time = datetime.now()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RateLimiter, requests_per_minute=60)


# Mount static files (for web interface)
static_dir = current_dir / "static"
print(f"🔧 Static path: {static_dir}")
print(f"🔧 Static exists: {static_dir.exists()}")
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
# Models with enhanced validation
class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        if len(v) > 1000:
            raise ValueError('Message too long (max 1000 characters)')
        return v.strip()

class ChatResponse(BaseModel):
    response: str
    user_id: str
    session_id: str
    intent: str
    needs_escalation: bool
    action_required: bool
    confidence: Optional[float] = None
    timestamp: str
    response_time_ms: Optional[int] = None
    suggestions: Optional[List[str]] = None

class AppointmentRequest(BaseModel):
    service_type: str
    date: str
    time: str
    customer_name: str
    email: EmailStr
    phone: Optional[str] = None
    notes: Optional[str] = None

class AnalyticsRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    user_id: Optional[str] = None

class EscalationStatsRequest(BaseModel):
    period_days: Optional[int] = 7

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    setup_logger()
    
    # Load initial knowledge base in background
    asyncio.create_task(load_knowledge_base())
    
    print(f"""
    {'='*60}
    {settings.APP_NAME} - v2.0.0
    {'='*60}
    Status: {'🚀 Development' if settings.DEBUG else '🏭 Production'}
    Environment: {'development' if settings.DEBUG else 'production'}  # Changed from settings.ENVIRONMENT
    Log Level: {settings.LOG_LEVEL}
    {'='*60}
    🌐 Web Interface: http://localhost:{settings.PORT}/chat
    📚 API Docs: http://localhost:{settings.PORT}/api/docs
    🏥 Health Check: http://localhost:{settings.PORT}/api/health
    💬 Chat Endpoint: POST /api/chat
    📊 Metrics: http://localhost:{settings.PORT}/api/metrics
    📈 Escalation Dashboard: http://localhost:{settings.PORT}/api/escalations
    {'='*60}
    """)

async def load_knowledge_base():
    """Load knowledge base asynchronously"""
    try:
        documents = kb_loader.load_all_documents()
        loaded_count = 0
        for doc in documents:
            rag_engine.index_document(doc)
            loaded_count += 1
        
        # Wait a moment for indexing to complete
        await asyncio.sleep(0.5)
        
        collection_info = rag_engine.get_collection_info()
        print(f"✅ Loaded {loaded_count} documents into knowledge base")
        
        # Handle the collection info safely
        if 'error' in collection_info:
            print(f"⚠️  Warning: Could not get collection info: {collection_info['error']}")
            print(f"📊 Knowledge Base: Documents processed successfully (collection info unavailable)")
        else:
            print(f"📊 Knowledge Base: {collection_info.get('points_count', 0)} chunks indexed")
            
    except Exception as e:
        print(f"❌ Error loading knowledge base: {e}")
        import traceback
        traceback.print_exc()

@app.get("/")
async def root():
    """Root endpoint redirects to chat interface"""
    return RedirectResponse(url="/chat")

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Serve the professional chat interface"""
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "app_name": settings.APP_NAME,
        "version": "2.0.0",
        "year": datetime.now().year
    })

@app.get("/api/health")
async def health_check(background_tasks: BackgroundTasks):
    """Comprehensive health check endpoint"""
    health_data = await health_checker.check_health()
    
    # Add system metrics
    try:
        health_data['system'] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime_seconds": (datetime.now() - startup_time).total_seconds()
        }
        
        # Get escalation stats from dialog manager
        escalation_queue = dialog_manager.get_escalation_queue()
        
        health_data['service'] = {
            "active_conversations": len(dialog_manager.get_active_conversations()),
            "kb_documents": rag_engine.get_collection_info().get('points_count', 0),
            "conversations_tracked": len(analytics.conversations),
            "appointments_count": len(dialog_manager.get_all_appointments()),
            "pending_escalations": len([t for t in escalation_queue if t.get('status') == 'pending']),
            "total_escalations": len(escalation_queue),
            "escalation_rate": f"{len(escalation_queue) / max(len(analytics.conversations), 1) * 100:.1f}%" if analytics.conversations else "0%"
        }
    except Exception as e:
        health_data['system_error'] = str(e)
    
    response = JSONResponse(content=health_data)
    response.headers["X-Health-Check"] = "true"
    response.headers["X-Service-Version"] = "2.0.0"
    response.headers["X-Uptime-Seconds"] = str((datetime.now() - startup_time).total_seconds())
    
    return response

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request, background_tasks: BackgroundTasks):
    """Main chat endpoint with analytics tracking"""
    start_time = datetime.now()
    
    try:
        # Generate or use user ID
        if request.user_id:
            user_id = request.user_id
        elif request.session_id:
            user_id = request.session_id
        else:
            # Use client IP as user identifier
            client_ip = req.client.host if req.client.host else "127.0.0.1"
            user_id = f"user_{client_ip.replace('.', '_')}"
        
        # Process message
        response_data = dialog_manager.process_message(user_id, request.message)
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Track conversation for analytics
        conversation_data = {
            'user_id': user_id,
            'message': security.mask_pii(request.message),
            'response': security.mask_pii(response_data.get('response', '')),
            'intent': response_data.get('intent', 'unknown'),
            'needs_escalation': response_data.get('needs_escalation', False),
            'action_required': response_data.get('action_required', False),
            'action_completed': response_data.get('action_completed', False),
            'confidence': response_data.get('confidence', 0),
            'response_time': response_time,
            'start_time': start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'escalation_ticket_id': response_data.get('escalation_ticket_id'),
            'escalation_reason': response_data.get('escalation_reason')
        }
        
        # Add to analytics in background
        background_tasks.add_task(analytics.track_conversation, conversation_data)
        
        # Create response
        response = ChatResponse(
            response=response_data.get('response', ''),
            user_id=user_id,
            session_id=request.session_id or str(uuid.uuid4()),
            intent=response_data.get('intent', 'unknown'),
            needs_escalation=response_data.get('needs_escalation', False),
            action_required=response_data.get('action_required', False),
            confidence=response_data.get('confidence'),
            timestamp=datetime.now().isoformat(),
            response_time_ms=int(response_time),
            suggestions=response_data.get('suggestions')
        )
        
        return response
        
    except Exception as e:
        # Log error
        error_id = str(uuid.uuid4())[:8]
        print(f"❌ Error {error_id}: {e}")
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Internal server error",
                "error_id": error_id,
                "message": "Please try again later",
                "timestamp": datetime.now().isoformat()
            }
        )

#  ESCALATION ENDPOINTS

@app.get("/api/escalations")
async def get_escalation_queue():
    """Get current escalation queue (admin only)"""
    # In production, add authentication
    queue = dialog_manager.get_escalation_queue()
    
    # Apply PII masking for security
    masked_queue = []
    for ticket in queue:
        masked_ticket = ticket.copy()
        if 'conversation_summary' in masked_ticket:
            masked_ticket['conversation_summary'] = security.mask_pii(
                masked_ticket['conversation_summary']
            )
        masked_queue.append(masked_ticket)
    
    return {
        "queue": masked_queue,
        "count": len(queue),
        "pending_count": len([t for t in queue if t.get('status') == 'pending']),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/escalations/user/{user_id}")
async def get_user_escalations(user_id: str):
    """Get escalation history for a user"""
    history = dialog_manager.get_user_escalation_history(user_id)
    
    # Apply PII masking
    masked_history = []
    for ticket in history:
        masked_ticket = ticket.copy()
        if 'conversation_summary' in masked_ticket:
            masked_ticket['conversation_summary'] = security.mask_pii(
                masked_ticket['conversation_summary']
            )
        masked_history.append(masked_ticket)
    
    return {
        "user_id": user_id,
        "escalations": masked_history,
        "count": len(history),
        "last_escalation": history[-1]['timestamp'] if history else None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/escalations/reset/{user_id}")
async def reset_user_escalation(user_id: str):
    """Reset user's failure tracker (admin/testing)"""
    dialog_manager.reset_user_escalation_tracker(user_id)
    
    return {
        "message": f"Reset escalation tracker for user {user_id}",
        "success": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/escalations/stats")
async def get_escalation_stats():
    """Get escalation statistics"""
    try:
        queue = dialog_manager.get_escalation_queue()
        
        # Calculate stats
        total_pending = len([t for t in queue if t.get('status') == 'pending'])
        total_resolved = len([t for t in queue if t.get('status') == 'resolved'])
        
        # Count by priority
        by_priority = {}
        for ticket in queue:
            priority = ticket.get('priority', 'normal')
            by_priority[priority] = by_priority.get(priority, 0) + 1
        
        # Count by trigger type
        by_trigger = {}
        for ticket in queue:
            trigger = ticket.get('trigger_type', 'unknown')
            by_trigger[trigger] = by_trigger.get(trigger, 0) + 1
        
        # Calculate escalation rate
        total_conversations = len(analytics.conversations)
        escalation_rate = (len(queue) / max(total_conversations, 1)) * 100
        
        # Get recent escalations (last 24 hours)
        recent_escalations = []
        for ticket in queue[-10:]:  # Last 10 tickets
            recent_escalations.append({
                'ticket_id': ticket.get('ticket_id'),
                'user_id': ticket.get('user_id'),
                'priority': ticket.get('priority'),
                'reason': ticket.get('reason')[:100] if ticket.get('reason') else '',
                'timestamp': ticket.get('timestamp')
            })
        
        stats = {
            "total_pending": total_pending,
            "total_resolved": total_resolved,
            "total_all_time": len(queue),
            "by_priority": by_priority,
            "by_trigger": by_trigger,
            "escalation_rate_percent": round(escalation_rate, 1),
            "avg_resolution_time_minutes": "N/A",  # Would need resolution timestamps
            "recent_escalations": recent_escalations,
            "common_reasons": self._get_common_escalation_reasons(queue),
            "timestamp": datetime.now().isoformat()
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting escalation stats: {str(e)}")

def _get_common_escalation_reasons(queue):
    """Extract common reasons from escalation tickets"""
    reasons = {}
    for ticket in queue:
        reason = ticket.get('reason', 'Unknown')
        if reason:
            # Extract main reason (first sentence)
            main_reason = reason.split('.')[0] if '.' in reason else reason
            main_reason = main_reason[:50]  # Limit length
            reasons[main_reason] = reasons.get(main_reason, 0) + 1
    
    # Sort by frequency
    sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_reasons[:5])  # Top 5 reasons

@app.post("/api/escalations/{ticket_id}/resolve")
async def resolve_escalation(ticket_id: str):
    """Mark an escalation ticket as resolved (admin)"""
    try:
        queue = dialog_manager.get_escalation_queue()
        
        # Find and update the ticket
        for ticket in queue:
            if ticket.get('ticket_id') == ticket_id:
                ticket['status'] = 'resolved'
                ticket['resolved_at'] = datetime.now().isoformat()
                ticket['resolved_by'] = 'admin'  # In production, get from auth
                
                # Clear resolved tickets periodically
                dialog_manager.clear_resolved_tickets()
                
                return {
                    "success": True,
                    "message": f"Escalation ticket {ticket_id} marked as resolved",
                    "ticket_id": ticket_id,
                    "resolved_at": ticket['resolved_at'],
                    "timestamp": datetime.now().isoformat()
                }
        
        raise HTTPException(status_code=404, detail=f"Escalation ticket {ticket_id} not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/escalations/dashboard")
async def escalation_dashboard():
    """Get escalation dashboard data"""
    try:
        queue = dialog_manager.get_escalation_queue()
        
        # Process for dashboard
        dashboard_data = {
            "summary": {
                "total_pending": len([t for t in queue if t.get('status') == 'pending']),
                "high_priority": len([t for t in queue if t.get('priority') == 'high']),
                "escalated_today": len([t for t in queue if t.get('timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d'))]),
                "avg_wait_time_minutes": _calculate_avg_wait_time(queue)
            },
            "by_hour": _get_escalations_by_hour(queue),
            "by_reason": _get_top_escalation_reasons(queue),
            "recent_tickets": _get_recent_tickets(queue, limit=10)
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating dashboard: {str(e)}")

def _calculate_avg_wait_time(queue):
    """Calculate average wait time for pending escalations"""
    pending_tickets = [t for t in queue if t.get('status') == 'pending']
    if not pending_tickets:
        return 0
    
    total_wait = 0
    for ticket in pending_tickets:
        ticket_time = datetime.fromisoformat(ticket.get('timestamp'))
        wait_time = (datetime.now() - ticket_time).total_seconds() / 60
        total_wait += wait_time
    
    return round(total_wait / len(pending_tickets), 1)

def _get_escalations_by_hour(queue):
    """Group escalations by hour of day"""
    by_hour = {f"{hour:02d}:00": 0 for hour in range(24)}
    
    for ticket in queue:
        if ticket.get('timestamp'):
            try:
                ticket_time = datetime.fromisoformat(ticket['timestamp'])
                hour_key = f"{ticket_time.hour:02d}:00"
                by_hour[hour_key] = by_hour.get(hour_key, 0) + 1
            except:
                pass
    
    return by_hour


def _get_top_escalation_reasons(queue, limit=5):
    """Get top escalation reasons"""
    reasons = {}
    for ticket in queue:
        reason = ticket.get('reason', 'Unknown')
        if reason:
            # Simplify reason for grouping
            simple_reason = reason.split(':')[0] if ':' in reason else reason
            simple_reason = simple_reason.split('.')[0] if '.' in simple_reason else simple_reason
            simple_reason = simple_reason.strip()
            if len(simple_reason) > 50:
                simple_reason = simple_reason[:47] + "..."
            reasons[simple_reason] = reasons.get(simple_reason, 0) + 1
    
    sorted_reasons = sorted(reasons.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_reasons[:limit])


def _get_recent_tickets(queue, limit=10):
    """Get recent escalation tickets"""
    recent = []
    sorted_queue = sorted(queue, key=lambda x: x.get('timestamp', ''), reverse=True)
    
    for ticket in sorted_queue[:limit]:
        recent.append({
            'ticket_id': ticket.get('ticket_id'),
            'user_id': ticket.get('user_id'),
            'priority': ticket.get('priority', 'normal'),
            'reason': ticket.get('reason', '')[:80],
            'timestamp': ticket.get('timestamp'),
            'status': ticket.get('status', 'pending'),
            'assigned_agent': ticket.get('assigned_agent')
        })
    
    return recent



@app.get("/api/conversation/{user_id}")
async def get_conversation(user_id: str):
    """Get conversation history for a user"""
    history = dialog_manager.get_conversation_history(user_id)
    
    # Apply PII masking for security
    masked_history = []
    for entry in history:
        masked_entry = entry.copy()
        masked_entry['user'] = security.mask_pii(entry.get('user', ''))
        masked_entry['bot'] = security.mask_pii(entry.get('bot', ''))
        masked_history.append(masked_entry)
    
    return {
        "user_id": user_id,
        "history": masked_history,
        "count": len(history),
        "masked": True,
        "retrieved_at": datetime.now().isoformat()
    }

@app.post("/api/kb/documents")
async def add_document(request: Dict):
    """Add document to knowledge base"""
    try:
        document = {
            "content": request.get("content", ""),
            "metadata": request.get("metadata", {})
        }
        
        rag_engine.index_document(document)
        
        return {
            "success": True,
            "message": "Document added to knowledge base",
            "document_id": request.get("metadata", {}).get("id", "unknown"),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/kb/search")
async def search_knowledge_base(query: str, top_k: int = 3, score_threshold: float = 0.3):
    """Search knowledge base"""
    try:
        if not query or not query.strip():
            return {
                "query": query,
                "results": [],
                "count": 0,
                "message": "Query cannot be empty"
            }
        
        results = rag_engine.search(query, top_k=top_k, score_threshold=score_threshold)
        
        # Mask any PII in results
        for result in results:
            result['content'] = security.mask_pii(result.get('content', ''))
        
        return {
            "query": query,
            "results": results,
            "count": len(results),
            "collection_info": rag_engine.get_collection_info(),
            "search_params": {
                "top_k": top_k,
                "score_threshold": score_threshold
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics(request: AnalyticsRequest = Depends()):
    """Get analytics data"""
    try:
        if request.user_id:
            insights = analytics.get_conversation_insights(request.user_id)
            user_info = f"for user {request.user_id}"
        else:
            insights = analytics.get_conversation_insights()
            user_info = "all users"
        
        daily_report = analytics.get_daily_report()
        
        return {
            "analytics_for": user_info,
            "period": {
                "start_date": request.start_date,
                "end_date": request.end_date,
                "requested_at": datetime.now().isoformat()
            },
            "insights": insights,
            "daily_report": daily_report,
            "metrics": analytics.metrics,
            "total_conversations_tracked": len(analytics.conversations),
            "data_collection_since": analytics.get_earliest_conversation_date()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/metrics")
async def get_metrics():
    """Get Prometheus metrics"""
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.get("/api/system/status")
async def system_status():
    """Get detailed system status"""
    try:
        # Get escalation queue
        escalation_queue = dialog_manager.get_escalation_queue()
        
        return {
            "system": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent,
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                "process_create_time": startup_time.isoformat()
            },
            "service": {
                "active_conversations": len(dialog_manager.get_active_conversations()),
                "kb_documents": rag_engine.get_collection_info().get('points_count', 0),
                "uptime": str(datetime.now() - startup_time),
                "uptime_seconds": (datetime.now() - startup_time).total_seconds(),
                "conversations_tracked": len(analytics.conversations),
                "total_appointments": len(dialog_manager.get_all_appointments()),
                "pending_escalations": len([t for t in escalation_queue if t.get('status') == 'pending']),
                "total_escalations": len(escalation_queue)
            },
            "status": "operational",
            "timestamp": datetime.now().isoformat(),
            "version": "2.0.0"
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/appointments")
async def get_all_appointments():
    """Get all appointments"""
    try:
        appointments = dialog_manager.get_all_appointments()
        
        # Mask PII in appointments
        masked_appointments = []
        for apt in appointments:
            masked_apt = apt.copy()
            masked_apt['email'] = security.mask_pii(apt['email'])
            masked_apt['customer_name'] = security.mask_pii(apt['customer_name'])
            masked_appointments.append(masked_apt)
        
        return {
            "appointments": masked_appointments,
            "count": len(appointments),
            "success": True,
            "retrieved_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/appointments/user/{user_id}")
async def get_user_appointments(user_id: str):
    """Get appointments for a specific user"""
    try:
        appointments = dialog_manager.get_user_appointments(user_id)
        
        return {
            "user_id": user_id,
            "appointments": appointments,
            "count": len(appointments),
            "success": True,
            "retrieved_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: str):
    """Get a specific appointment by ID"""
    try:
        appointment = dialog_manager.get_appointment_by_id(appointment_id)
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        return {
            "appointment": appointment,
            "success": True,
            "retrieved_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    try:
        appointment = dialog_manager.get_appointment_by_id(appointment_id)
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Update status to cancelled
        appointment['status'] = 'cancelled'
        appointment['updated_at'] = datetime.now().isoformat()
        
        return {
            "message": "Appointment cancelled successfully",
            "appointment_id": appointment_id,
            "success": True,
            "cancelled_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/appointments/stats")
async def get_appointment_stats():
    """Get appointment statistics"""
    try:
        appointments = dialog_manager.get_all_appointments()
        
        # Calculate stats
        total = len(appointments)
        by_status = {}
        by_service = {}
        
        for apt in appointments:
            status = apt.get('status', 'unknown')
            service = apt.get('service_type', 'unknown')
            
            by_status[status] = by_status.get(status, 0) + 1
            by_service[service] = by_service.get(service, 0) + 1
        
        return {
            "total_appointments": total,
            "by_status": by_status,
            "by_service": by_service,
            "success": True,
            "calculated_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/test-email")
async def test_email():
    """Test email sending"""
    try:
        from app.utils.email_sender import email_sender
        
        # Test connection first
        connection_ok = email_sender.test_connection()
        if not connection_ok:
            return {
                "success": False,
                "error": "SMTP connection failed. Check your credentials!",
                "tested_at": datetime.now().isoformat()
            }
        
        # Send test email
        test_appointment = {
            'appointment_id': 'TEST-12345',
            'service_type': 'consultation',
            'date': '2024-12-18',
            'time': '3:30 PM',
            'customer_name': 'Test User',
            'email': 'test@cobcompany.com'
        }
        
        success = email_sender.send_appointment_confirmation(
            'test@cobcompany.com',
            test_appointment
        )
        
        return {
            "success": success,
            "message": "Email sent!" if success else "Email failed",
            "check": "Check your inbox at test@cobcompany.com",
            "tested_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "success": False, 
            "error": str(e),
            "tested_at": datetime.now().isoformat()
        }

@app.get("/api/status")
async def api_status():
    """API status information"""
    return {
        "service": settings.APP_NAME,
        "version": "2.0.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "uptime": str(datetime.now() - startup_time),
        "endpoints": {
            "web_interface": "/chat",
            "api_documentation": "/api/docs",
            "health_check": "/api/health",
            "chat": "POST /api/chat",
            "knowledge_base": "GET /api/kb/search",
            "analytics": "GET /api/analytics",
            "appointments": "GET /api/appointments",
            "metrics": "GET /api/metrics",
            "escalations": "GET /api/escalations",
            "escalation_stats": "GET /api/escalations/stats",
            "escalation_dashboard": "GET /api/escalations/dashboard"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/clear-conversations")
async def clear_conversations(background_tasks: BackgroundTasks):
    """Clear all conversations (admin endpoint)"""
    try:
        # Get count before clearing
        conversations = dialog_manager.get_active_conversations()
        count = len(conversations)
        
        # Clear conversations in background
        def clear_all():
            for user_id in conversations:
                dialog_manager.clear_conversation(user_id)
        
        background_tasks.add_task(clear_all)
        
        return {
            "message": f"Scheduled cleanup of {count} conversations",
            "count": count,
            "scheduled_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )