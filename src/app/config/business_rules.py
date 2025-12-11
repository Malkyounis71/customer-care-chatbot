"""
Business rules and constants for the chatbot.
Separates business logic from dialog management.
"""

from datetime import time
from typing import Dict, List, Any

# Business hours and scheduling rules
BUSINESS_HOURS = {
    'start': time(14, 0),  # 2:00 PM
    'end': time(22, 0),    # 10:00 PM
    'weekdays': [0, 1, 2, 3, 4],  # Monday-Friday
}

# Valid service types with descriptions
VALID_SERVICES: Dict[str, str] = {
    'consultation': 'Strategic planning and advisory services',
    'support': 'Technical assistance and troubleshooting',
    'installation': 'System setup and implementation',
    'maintenance': 'Regular upkeep and optimization',
    'training': 'User education and skill development',
    'demo': 'Product demonstration' 
}

# Appointment time slots (in minutes from start hour)
APPOINTMENT_SLOTS = [
    "2:00 PM", "2:30 PM", "3:00 PM", "3:30 PM",
    "4:00 PM", "4:30 PM", "5:00 PM", "5:30 PM",
    "6:00 PM", "6:30 PM", "7:00 PM", "7:30 PM",
    "8:00 PM", "8:30 PM", "9:00 PM"
]

# Product information structure
PRODUCT_CATEGORIES = {
    'enterprise_suite': {
        'name': 'COB Enterprise Suite',
        'description': 'All-in-one business management platform',
        'keywords': ['enterprise', 'suite', 'business', 'management', 'platform']
    },
    'analytics_pro': {
        'name': 'COB Analytics Pro',
        'description': 'Advanced data analytics platform',
        'keywords': ['analytics', 'data', 'reporting', 'dashboard', 'insights']
    },
    'cloud_services': {
        'name': 'COB Cloud Services',
        'description': 'Secure, scalable cloud hosting',
        'keywords': ['cloud', 'hosting', 'storage', 'infrastructure']
    }
}

# Support escalation thresholds
ESCALATION_RULES = {
    'frustration_score': 0.8,
    'failed_attempts': 3,
    'timeout_minutes': 5,
    'emergency_keywords': ['urgent', 'emergency', 'critical', 'broken', 'down']
}

# Conversation settings
CONVERSATION_SETTINGS = {
    'max_history_length': 10,
    'session_timeout_minutes': 30,
    'cleanup_interval_minutes': 60,
    'max_message_length': 1000
}