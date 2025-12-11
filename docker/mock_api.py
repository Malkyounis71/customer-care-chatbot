"""
Mock External API for Customer Care Chatbot.
Simulates external services like appointment scheduling, CRM, etc.
"""

from fastapi import FastAPI, HTTPException
from datetime import datetime, timedelta
import uuid
import random
from typing import Dict, List, Optional
from pydantic import BaseModel, EmailStr
import uvicorn
from loguru import logger

# Initialize FastAPI app
app = FastAPI(
    title="Mock External API",
    description="Mock API simulating external services for Customer Care Chatbot",
    version="1.0.0"
)

# In-memory storage for mock data
appointments_db = []
users_db = []
support_tickets_db = []

# Models
class AppointmentRequest(BaseModel):
    service_type: str
    date: str
    time: str
    customer_name: str
    email: EmailStr
    phone: Optional[str] = None
    notes: Optional[str] = None

class AppointmentResponse(BaseModel):
    success: bool
    appointment_id: str
    message: str
    scheduled_time: str
    confirmation_email_sent: bool

class SupportTicketRequest(BaseModel):
    user_id: str
    issue_type: str
    description: str
    priority: str = "medium"

class UserRegistration(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Mock External API",
        "version": "1.0.0",
        "endpoints": {
            "appointments": {
                "schedule": "POST /api/appointments",
                "list": "GET /api/appointments",
                "get": "GET /api/appointments/{appointment_id}",
                "cancel": "DELETE /api/appointments/{appointment_id}"
            },
            "support": {
                "create_ticket": "POST /api/support/tickets",
                "list_tickets": "GET /api/support/tickets"
            },
            "users": {
                "register": "POST /api/users",
                "list": "GET /api/users"
            },
            "health": "GET /api/health"
        }
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "mock_api",
        "timestamp": datetime.now().isoformat(),
        "uptime": "24h",  # Mock value
        "database": {
            "appointments": len(appointments_db),
            "users": len(users_db),
            "support_tickets": len(support_tickets_db)
        }
    }

@app.post("/api/appointments", response_model=AppointmentResponse)
async def schedule_appointment(request: AppointmentRequest):
    """Mock endpoint for scheduling appointments"""
    try:
        # Validate date/time (simplified validation)
        appointment_date = datetime.strptime(request.date, "%Y-%m-%d")
        
        # Check if date is in the past
        if appointment_date.date() < datetime.now().date():
            raise HTTPException(status_code=400, detail="Cannot schedule appointment in the past")
        
        # Check if time is within business hours (9 AM - 6 PM)
        hour = int(request.time.split(":")[0])
        if not 9 <= hour <= 18:
            raise HTTPException(status_code=400, detail="Appointments available 9 AM - 6 PM only")
        
        # Generate appointment ID
        appointment_id = f"APPT-{uuid.uuid4().hex[:8].upper()}"
        
        # Create appointment record
        appointment = {
            "appointment_id": appointment_id,
            "service_type": request.service_type,
            "date": request.date,
            "time": request.time,
            "customer_name": request.customer_name,
            "email": request.email,
            "phone": request.phone,
            "notes": request.notes,
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "confirmation_code": f"CODE-{random.randint(1000, 9999)}"
        }
        
        # Store appointment
        appointments_db.append(appointment)
        
        # Simulate email sending (80% success rate)
        email_sent = random.random() > 0.2
        
        logger.info(f"✅ Mock appointment scheduled: {appointment_id} for {request.customer_name}")
        
        return AppointmentResponse(
            success=True,
            appointment_id=appointment_id,
            message="Appointment scheduled successfully",
            scheduled_time=f"{request.date} {request.time}",
            confirmation_email_sent=email_sent
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date/time format: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error scheduling appointment: {e}")
        raise HTTPException(status_code=500, detail="Failed to schedule appointment")

@app.get("/api/appointments")
async def list_appointments(limit: int = 10, offset: int = 0):
    """List all appointments"""
    return {
        "appointments": appointments_db[offset:offset + limit],
        "total": len(appointments_db),
        "limit": limit,
        "offset": offset
    }

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(appointment_id: str):
    """Get specific appointment"""
    for appointment in appointments_db:
        if appointment["appointment_id"] == appointment_id:
            return appointment
    
    raise HTTPException(status_code=404, detail="Appointment not found")

@app.delete("/api/appointments/{appointment_id}")
async def cancel_appointment(appointment_id: str):
    """Cancel an appointment"""
    for i, appointment in enumerate(appointments_db):
        if appointment["appointment_id"] == appointment_id:
            # Update status
            appointments_db[i]["status"] = "cancelled"
            appointments_db[i]["updated_at"] = datetime.now().isoformat()
            
            logger.info(f"🗑️  Mock appointment cancelled: {appointment_id}")
            
            return {
                "success": True,
                "message": "Appointment cancelled successfully",
                "appointment_id": appointment_id
            }
    
    raise HTTPException(status_code=404, detail="Appointment not found")

@app.post("/api/support/tickets")
async def create_support_ticket(request: SupportTicketRequest):
    """Create a support ticket"""
    ticket_id = f"TICKET-{uuid.uuid4().hex[:8].upper()}"
    
    ticket = {
        "ticket_id": ticket_id,
        "user_id": request.user_id,
        "issue_type": request.issue_type,
        "description": request.description,
        "priority": request.priority,
        "status": "open",
        "created_at": datetime.now().isoformat(),
        "assigned_to": None,
        "estimated_resolution": (datetime.now() + timedelta(hours=random.randint(2, 48))).isoformat()
    }
    
    support_tickets_db.append(ticket)
    
    logger.info(f"🎫 Mock support ticket created: {ticket_id}")
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "message": "Support ticket created successfully",
        "estimated_resolution": ticket["estimated_resolution"]
    }

@app.get("/api/support/tickets")
async def list_support_tickets(status: Optional[str] = None, limit: int = 10):
    """List support tickets"""
    filtered_tickets = support_tickets_db
    
    if status:
        filtered_tickets = [t for t in support_tickets_db if t["status"] == status]
    
    return {
        "tickets": filtered_tickets[:limit],
        "total": len(filtered_tickets),
        "filtered_by_status": status
    }

@app.post("/api/users")
async def register_user(request: UserRegistration):
    """Register a new user"""
    user_id = f"USER-{uuid.uuid4().hex[:8].upper()}"
    
    user = {
        "user_id": user_id,
        "name": request.name,
        "email": request.email,
        "phone": request.phone,
        "registered_at": datetime.now().isoformat(),
        "status": "active"
    }
    
    users_db.append(user)
    
    logger.info(f"👤 Mock user registered: {user_id} - {request.name}")
    
    return {
        "success": True,
        "user_id": user_id,
        "message": "User registered successfully"
    }

@app.get("/api/users")
async def list_users(limit: int = 10):
    """List registered users"""
    return {
        "users": users_db[:limit],
        "total": len(users_db)
    }

@app.get("/api/system/status")
async def system_status():
    """System status endpoint"""
    return {
        "system": {
            "status": "operational",
            "version": "1.0.0",
            "uptime": f"{random.randint(100, 1000)} hours",
            "load_average": f"{random.uniform(0.1, 2.5):.2f}",
            "memory_usage_percent": random.randint(30, 80)
        },
        "services": {
            "database": "online",
            "email_service": "online" if random.random() > 0.1 else "degraded",
            "payment_gateway": "online" if random.random() > 0.05 else "offline",
            "sms_service": "online" if random.random() > 0.2 else "maintenance"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/notifications/send")
async def send_notification():
    """Mock notification sending endpoint"""
    notification_id = f"NOTIF-{uuid.uuid4().hex[:8].upper()}"
    
    # Simulate random success/failure
    success = random.random() > 0.15
    
    return {
        "success": success,
        "notification_id": notification_id,
        "message": "Notification sent successfully" if success else "Failed to send notification",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    logger.info("🚀 Starting Mock API Server...")
    logger.info("📚 API Documentation: http://localhost:5001/docs")
    logger.info("🏥 Health Check: http://localhost:5001/api/health")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5001,
        log_level="info"
    )