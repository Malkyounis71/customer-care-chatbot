"""
Appointment service handling all appointment-related business logic.
Separated from dialog management for better maintainability.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import uuid
import re
from loguru import logger

from app.config.business_rules import BUSINESS_HOURS, VALID_SERVICES, APPOINTMENT_SLOTS


class AppointmentService:
    """Service for managing appointments."""
    
    def __init__(self):
        self.appointments: List[Dict] = []
    
    def create_appointment(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment."""
        appointment_id = self._generate_appointment_id()
        
        appointment = {
            'appointment_id': appointment_id,
            'user_id': user_id,
            'service_type': data.get('service_type'),
            'date': data.get('date'),
            'time': data.get('time'),
            'customer_name': data.get('customer_name'),
            'email': data.get('email'),
            'status': 'confirmed',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        self.appointments.append(appointment)
        logger.info(f"✅ Appointment created: {appointment_id} for user {user_id}")
        return appointment
    
    def update_appointment(self, appointment_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an existing appointment."""
        for appointment in self.appointments:
            if appointment['appointment_id'] == appointment_id:
                appointment.update(updates)
                appointment['updated_at'] = datetime.now().isoformat()
                appointment['status'] = 'updated'
                logger.info(f"🔄 Appointment updated: {appointment_id}")
                return appointment
        logger.warning(f"❌ Appointment not found: {appointment_id}")
        return None
    
    def get_user_appointments(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all appointments for a user."""
        return [apt for apt in self.appointments if apt['user_id'] == user_id]
    
    def get_appointment_by_id(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Get appointment by ID."""
        for appointment in self.appointments:
            if appointment['appointment_id'] == appointment_id:
                return appointment
        return None
    
    def validate_appointment(self, date_str: str, time_str: str) -> Tuple[bool, str]:
        """Validate appointment date and time."""
        try:
            # Validate date
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = appointment_date.weekday()
            
            # Check if it's a weekend
            if weekday >= 5:
                day_name = appointment_date.strftime('%A')
                return False, f"❌ **Weekend Appointment:** We're closed on weekends!\n\nYou selected **{day_name} ({date_str})**.\n\n📅 **Please choose a weekday (Monday-Friday):**"
            
            # Validate time
            time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)', time_str, re.IGNORECASE)
            if not time_match:
                return False, "I couldn't understand the time format. Please use formats like '2:30 PM' or '14:30'."
            
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            am_pm = time_match.group(3).upper()
            
            # Convert to 24-hour format
            if am_pm == 'PM' and hour != 12:
                hour += 12
            elif am_pm == 'AM' and hour == 12:
                hour = 0
            
            # Check business hours
            start_hour = BUSINESS_HOURS['start'].hour
            end_hour = BUSINESS_HOURS['end'].hour
            
            if hour < start_hour:  # Before start time
                start_time_str = BUSINESS_HOURS['start'].strftime('%I:%M %p')
                return False, f"❌ **Outside Business Hours:** Our appointments start at **{start_time_str}**.\n\nYou selected **{time_str}**."
            
            if hour >= end_hour:  # At or after end time
                end_time_str = BUSINESS_HOURS['end'].strftime('%I:%M %p')
                return False, f"❌ **Outside Business Hours:** Our last appointments are at **{end_time_str}**.\n\nYou selected **{time_str}**."
            
            # Check minutes - appointments on hour or half hour only
            if minute not in [0, 30]:
                return False, "We schedule appointments on the hour or half hour only. Please choose a time like '2:00 PM' or '2:30 PM'."
            
            return True, "Appointment time is valid."
            
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return False, f"I couldn't validate your appointment time. Please try a different format."
    
    def validate_date(self, date_str: str) -> Tuple[bool, str]:
        """Validate if date is a weekday."""
        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = appointment_date.weekday()
            
            if weekday >= 5:
                day_name = appointment_date.strftime('%A')
                return False, f"❌ **Weekend Appointment:** We're closed on weekends!\n\nYou selected **{day_name} ({date_str})**.\n\n📅 **Please choose a weekday (Monday-Friday):**"
            
            return True, "Date is valid."
        except ValueError as e:
            logger.error(f"Date validation error: {e}")
            return False, f"I couldn't understand the date format. Please use YYYY-MM-DD format."
    
    def get_available_times(self, date_str: str) -> List[str]:
        """Get available time slots for a date."""
        # For now, return all slots. In production, check against existing appointments.
        return APPOINTMENT_SLOTS
    
    def _generate_appointment_id(self) -> str:
        """Generate unique appointment ID."""
        return f"APT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"