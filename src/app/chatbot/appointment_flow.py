"""
Appointment flow management.
Handles the state machine for appointment booking and modification.
"""

from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
from loguru import logger

from app.config.business_rules import VALID_SERVICES
from app.config.response_templates import ResponseTemplates
from app.utils.date_time_parser import DateTimeParser


class AppointmentFlow:
    """Manages appointment booking and modification flows."""
    
    def __init__(self, appointment_service):
        self.appointment_service = appointment_service
        self.parser = DateTimeParser()
    
    def handle_flow(self, user_id: str, message: str, conv_state: Dict[str, Any], 
               intent_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment flow logic."""
        appointment_data = conv_state['appointment_data']
        current_question = conv_state.get('current_question')
        
        logger.info(f"Appointment flow - Current question: {current_question}")
        
        # Extract information from message
        extracted_info = self._extract_appointment_info(message, intent_details)
        
        # Update appointment data
        for key, value in extracted_info.items():
            if value:
                appointment_data[key] = value
                logger.info(f"✅ Updated {key}: {value}")
        
        # Validate extracted data
        validation_result = self._validate_extracted_data(appointment_data)
        if validation_result:
            return validation_result
        
        # Handle current question or determine next
        if not current_question:
            if conv_state.get('appointment_flow') == 'modifying':
                return self._handle_modification_request(message, conv_state)
            else:
                needed_info = self._get_next_appointment_info(appointment_data)
                conv_state['current_question'] = needed_info
                return self._ask_appointment_question(needed_info, appointment_data)
        
        # Check if current question was just answered 
        current_question_answered = False
        
        # Check if we extracted info for the current question
        if current_question in extracted_info and extracted_info[current_question]:
            value = appointment_data[current_question]
            
            # Special validation for date and time
            if current_question == 'date':
                is_valid, error_msg = self.appointment_service.validate_date(value)
                if not is_valid:
                    return {
                        'response': error_msg,
                        'intent': 'action',
                        'needs_escalation': False,
                        'action_required': True
                    }
            
            if current_question == 'time' and 'date' in appointment_data:
                is_valid, error_msg = self.appointment_service.validate_appointment(
                    appointment_data['date'], value
                )
                if not is_valid:
                    return {
                        'response': error_msg,
                        'intent': 'action',
                        'needs_escalation': False,
                        'action_required': True
                    }
            
            current_question_answered = True
        
        # handling for name when asked 
        # If we're asking for name and user provides something that's not a date/time, accept it
        if current_question == 'customer_name' and message.strip() and not current_question_answered:
            message_lower = message.lower().strip()
            
            # List of words that are NOT names
            not_names = [
                'today', 'tomorrow', 'yesterday', 'morning', 'afternoon', 'evening',
                'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
                'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                'september', 'october', 'november', 'december',
                'am', 'pm', 'noon', 'midnight',
                '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
            ]
            
            # Check if it's NOT a date/time word and not just a number
            is_not_name = any(word in message_lower for word in not_names) or re.match(r'^\d+$', message_lower)
            
            if not is_not_name and len(message.strip()) >= 2:
                appointment_data['customer_name'] = message.strip().title()
                current_question_answered = True
                logger.info(f"✅ Accepted as name: {message}")
        
        # Move to next question if current was answered
        if current_question_answered:
            # Check if all required info is collected
            if self._has_all_required_info(appointment_data):
                conv_state['current_question'] = None
                conv_state['waiting_for_confirmation'] = True
                
                if conv_state.get('modifying_existing_appointment'):
                    appointment_id = conv_state.get('existing_appointment_id')
                    return self._show_modification_confirmation(appointment_data, appointment_id)
                else:
                    return self._show_confirmation(appointment_data)
            else:
                next_question = self._get_next_appointment_info(appointment_data)
                conv_state['current_question'] = next_question
                return self._generate_smart_response(appointment_data, next_question)
        
        # If no extraction for current question, ask again
        return self._ask_appointment_question_again(current_question, message, appointment_data)
    
    def _extract_appointment_info(self, message: str, intent_details: Dict[str, Any]) -> Dict[str, str]:
        """Extract appointment information from message."""
        extracted = {}
        entities = intent_details.get('entities', {})
        
        # Extract service type
        if 'service_type' in entities:
            extracted['service_type'] = entities['service_type'][0]
        else:
            service_type = self._extract_service_type_from_text(message)
            if service_type:
                extracted['service_type'] = service_type
        
        # Extract date FIRST 
        parsed_date = self.parser.parse_date(message)
        if parsed_date:
            extracted['date'] = parsed_date
            logger.info(f"✅ Parsed date: {parsed_date}")
        elif 'date' in entities:
            # Entity extractor might have extracted "next sunday" as a date
            parsed_date = self.parser.parse_date(entities['date'][0])
            if parsed_date:
                extracted['date'] = parsed_date
                logger.info(f"✅ Parsed date from entity: {parsed_date}")
        
        # Extract time
        parsed_time = self.parser.parse_time(message)
        if parsed_time:
            extracted['time'] = parsed_time
            logger.info(f"✅ Parsed time: {parsed_time}")
        elif 'time' in entities:
            for entity_time in entities['time']:
                parsed_time = self.parser.parse_time(entity_time)
                if parsed_time:
                    extracted['time'] = parsed_time
                    logger.info(f"✅ Parsed time from entity: {parsed_time}")
                    break
        
        # NAME EXTRACTION 
        # Only extract name if it's NOT a date/time word
        message_lower = message.lower().strip()
        
        # List of common date/time words that should NOT be extracted as names
        date_time_words = [
            'today', 'tomorrow', 'yesterday', 'morning', 'afternoon', 'evening',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
            'september', 'october', 'november', 'december',
            'am', 'pm', 'noon', 'midnight'
        ]
        
        # Check if message contains date/time words
        is_date_time = any(word in message_lower for word in date_time_words)
        
        if not is_date_time:
            # Extract name - check multiple patterns
            name_patterns = [
                r'my name is\s+([A-Za-z\s]{2,})',
                r'i am\s+([A-Za-z\s]{2,})',
                r'i\'m\s+([A-Za-z\s]{2,})',
                r'call me\s+([A-Za-z\s]{2,})',
                r'this is\s+([A-Za-z\s]{2,})',
                r'name\s+is\s+([A-Za-z\s]{2,})',
                r'^([A-Za-z]{2,}\s+[A-Za-z]{2,})$'  # First Last only if not date/time
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, message.strip(), re.IGNORECASE)
                if match:
                    # Get the name group
                    if len(match.groups()) > 0:
                        name = match.group(1).strip()
                    else:
                        name = match.group(0).strip()
                    
                    # Clean up the name
                    name = re.sub(r'\s+', ' ', name)  # Remove extra spaces
                    name = name.title()  # Capitalize properly
                    
                    # Additional check: name should not be a single common word
                    common_words = ['hi', 'hello', 'hey', 'ok', 'yes', 'no', 'thanks', 'thank']
                    if (2 <= len(name) <= 50 and 
                        name.lower() not in common_words and
                        len(name.split()) <= 3):  # Max 3 words for a name
                        extracted['customer_name'] = name
                        logger.info(f"✅ Extracted valid name: {name}")
                        break
        
        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
        if email_match:
            extracted['email'] = email_match.group()
        
        logger.info(f"🔍 Extracted info: {extracted}")
        return extracted
    
    def _extract_service_type_from_text(self, text: str) -> Optional[str]:
        """Extract service type from text."""
        text_lower = text.lower()
        
        for service, keywords in [
            ('consultation', ['consultation', 'consult', 'advice', 'guidance']),
            ('support', ['support', 'help', 'assistance', 'fix', 'issue']),
            ('installation', ['installation', 'install', 'setup', 'implement']),
            ('maintenance', ['maintenance', 'maintain', 'service', 'checkup']),
            ('training', ['training', 'train', 'learn', 'teach', 'educate']),
            ('demo', ['demo', 'demonstration', 'show', 'presentation'])  
        ]:
            if any(keyword in text_lower for keyword in keywords):
                return service
        
        return None
    
    def _validate_extracted_data(self, appointment_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate extracted appointment data."""
        # Validate date if present
        if 'date' in appointment_data:
            is_valid, error_msg = self.appointment_service.validate_date(appointment_data['date'])
            if not is_valid:
                return {
                    'response': error_msg,
                    'intent': 'action',
                    'needs_escalation': False,
                    'action_required': True
                }
        
        # Validate time if date and time present
        if 'time' in appointment_data and 'date' in appointment_data:
            is_valid, error_msg = self.appointment_service.validate_appointment(
                appointment_data['date'], appointment_data['time']
            )
            if not is_valid:
                return {
                    'response': error_msg,
                    'intent': 'action',
                    'needs_escalation': False,
                    'action_required': True
                }
        
        return None
    
    def _handle_modification_request(self, message: str, conv_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle appointment modification request."""
        field_to_change = self._detect_field_to_change(message)
        
        if field_to_change:
            # Clear the field for update
            if field_to_change in conv_state['appointment_data']:
                conv_state['appointment_data'][field_to_change] = ''
            
            conv_state['current_question'] = field_to_change
            
            if field_to_change == 'service_type':
                response_text = """🔧 **Change Service Type**
                
What type of service would you like instead?
**Available options:**
1. **Consultation** - Strategic planning and advisory services
2. **Support** - Technical assistance and troubleshooting  
3. **Installation** - System setup and implementation
4. **Maintenance** - Regular upkeep and optimization
5. **Training** - User education and skill development

Please indicate your choice by number or name."""
            else:
                response_text = ResponseTemplates.appointment_question(field_to_change, conv_state['appointment_data'])
            
            return {
                'response': response_text,
                'intent': 'action',
                'needs_escalation': False,
                'action_required': True
            }
        else:
            return {
                'response': "I'm not sure what you want to change. Please tell me exactly what you want to change (e.g., 'service', 'date', 'time', 'name', or 'email').",
                'intent': 'action',
                'needs_escalation': False,
                'action_required': True
            }
    
    def _detect_field_to_change(self, message: str) -> Optional[str]:
        """Detect which field user wants to change."""
        message_lower = message.lower()
        
        field_map = {
            'service': 'service_type',
            'service type': 'service_type',
            'type': 'service_type',
            'date': 'date',
            'day': 'date',
            'time': 'time',
            'hour': 'time',
            'schedule': 'time',
            'name': 'customer_name',
            'email': 'email',
            'contact': 'email'
        }
        
        for keyword, field in field_map.items():
            if keyword in message_lower:
                return field
        
        return None
    
    def _has_all_required_info(self, appointment_data: Dict[str, Any]) -> bool:
        """Check if all required appointment info is collected."""
        required_fields = ['service_type', 'date', 'time', 'customer_name', 'email']
        return all(field in appointment_data and appointment_data[field] for field in required_fields)
    
    def _get_next_appointment_info(self, appointment_data: Dict[str, Any]) -> str:
        """Determine what information is needed next."""
        if 'service_type' not in appointment_data or not appointment_data['service_type']:
            return 'service_type'
        elif 'date' not in appointment_data or not appointment_data['date']:
            return 'date'
        elif 'time' not in appointment_data or not appointment_data['time']:
            return 'time'
        elif 'customer_name' not in appointment_data or not appointment_data['customer_name']:
            return 'customer_name'
        elif 'email' not in appointment_data or not appointment_data['email']:
            return 'email'
        else:
            return 'complete'
    
    def _ask_appointment_question(self, question_type: str, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ask for appointment information."""
        return {
            'response': ResponseTemplates.appointment_question(question_type, appointment_data),
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True
        }
    
    def _ask_appointment_question_again(self, question_type: str, message: str, 
                                   appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ask for appointment information again when extraction fails."""
        responses = {
            'service_type': f"I didn't understand '{message}' as a service type. Please choose from:\n1. Consultation\n2. Support\n3. Installation\n4. Maintenance\n5. Training\n\nOr type the service name directly.",
            'date': f"I couldn't parse the date from '{message}'. Please provide a date like:\n• Today/Tomorrow\n• Next Tuesday\n• December 15\n• 2024-12-15",
            'time': f"I couldn't parse the time from '{message}'. Please provide a time like:\n• 2:00 PM\n• 3:30 PM\n• Afternoon\n• Evening\n• 14:00",
            'customer_name': f"**I need your full name for the appointment booking.**\n\nPlease provide your name (e.g., John Smith or Jane Doe).",
            'email': f"**Please provide your email address** for confirmation:\n\n• Example: name@example.com\n• Format: user@domain.com"
        }
        
        # handling for name - be more conversational
        if question_type == 'customer_name':
            service_type = appointment_data.get('service_type', '').title()
            date_value = appointment_data.get('date', '')
            time_value = appointment_data.get('time', '')
            
            if all([service_type, date_value, time_value]):
                response = f"""✅ **Great! Almost done...**

I have your:
• **Service:** {service_type}
• **Date:** {date_value}  
• **Time:** {time_value}

**Now I need your name and email to complete the booking.**

**What's your full name?** (e.g., John Smith)"""
            else:
                response = responses['customer_name']
        
            return {
                'response': response,
                'intent': 'action',
                'needs_escalation': False,
                'action_required': True
            }
        
        return {
            'response': responses.get(question_type, f"Please provide the {question_type} information."),
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True
        }
    
    def _generate_smart_response(self, appointment_data: Dict[str, Any], next_question: str) -> Dict[str, Any]:
        """Generate intelligent response based on collected info."""
        service_type = appointment_data.get('service_type', '').title()
        date_value = appointment_data.get('date', '')
        time_value = appointment_data.get('time', '')
        
        has_service = 'service_type' in appointment_data and appointment_data['service_type']
        has_date = 'date' in appointment_data and appointment_data['date']
        has_time = 'time' in appointment_data and appointment_data['time']
        has_name = 'customer_name' in appointment_data and appointment_data['customer_name']
        
        # Generate appropriate response based on what we have
        if has_service and has_date and has_time and next_question == 'customer_name':
            response_text = f"""✅ **Excellent! I've captured all your preferences:**

• **Service:** {service_type}
• **Date:** {date_value}
• **Time:** {time_value}

**Now I just need your name and email to complete the booking.**
What's your full name? (e.g., John Smith)"""
        
        elif has_service and has_date and not has_time and next_question == 'time':
            response_text = f"""✅ **Perfect! I have your:**
• **Service:** {service_type}  
• **Date:** {date_value}

**What time on {date_value} works best for you?**"""
        
        elif has_service and has_date and has_time and has_name and next_question == 'email':
            customer_name = appointment_data.get('customer_name', '')
            response_text = f"""✅ **Almost done, {customer_name}!**

I have:
• **Service:** {service_type}
• **Date:** {date_value}
• **Time:** {time_value}
• **Name:** {customer_name}

**One last step: Please provide your email address for confirmation.**
Example: name@example.com"""
        
        else:
            return self._ask_appointment_question(next_question, appointment_data)
        
        return {
            'response': response_text,
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True
        }
    
    def _show_confirmation(self, appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Show appointment confirmation."""
        return {
            'response': ResponseTemplates.appointment_confirmation(appointment_data, "TEMP-ID"),
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True,
            'waiting_for_confirmation': True
        }
    
    def _show_modification_confirmation(self, appointment_data: Dict[str, Any], 
                                       appointment_id: str) -> Dict[str, Any]:
        """Show modification confirmation."""
        return {
            'response': ResponseTemplates.appointment_modification_confirmation(appointment_data, appointment_id),
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True,
            'waiting_for_confirmation': True
        }