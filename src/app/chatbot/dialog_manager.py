"""
Refactored Dialog Manager - Main orchestrator.
Now delegates to specialized services and handlers.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import re
from loguru import logger

from app.chatbot.intent_classifier import IntentClassifier
from app.chatbot.rag_engine import RAGEngine
from app.chatbot.nlp_processor import NLPProcessor
from app.chatbot.api_client import APIClient
from app.utils.security import SecurityManager
from app.config.settings import settings
from app.knowledge_base.loader import KnowledgeBaseLoader

# Import new modules
from app.config.business_rules import BUSINESS_HOURS, VALID_SERVICES
from app.config.response_templates import ResponseTemplates
from app.chatbot.appointment_service import AppointmentService
from app.chatbot.knowledge_service import KnowledgeService
from app.chatbot.intent_handlers import IntentHandlers
from app.chatbot.appointment_flow import AppointmentFlow
from app.chatbot.escalation_handler import EscalationHandler


class DialogManager:
    """Main dialog manager orchestrating conversation flows."""
    
    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.rag_engine = RAGEngine()
        self.nlp = NLPProcessor()
        self.api_client = APIClient()
        self.security = SecurityManager(settings.ENCRYPTION_KEY)
        self.knowledge_loader = KnowledgeBaseLoader()
        
        # Initialize services
        self.appointment_service = AppointmentService()
        self.knowledge_service = KnowledgeService(self.rag_engine)
        self.appointment_flow = AppointmentFlow(self.appointment_service)
        self.escalation_handler = EscalationHandler(self.security)  
        
        # Load knowledge base
        self._load_knowledge_base()
        
        # Conversation states
        self.conversations: Dict[str, Dict] = {}
        
        logger.info("✅ Dialog Manager initialized with refactored structure")
    
    def _load_knowledge_base(self):
        """Load documents into knowledge base."""
        try:
            documents = self.knowledge_loader.load_all_documents()
            logger.info("🔄 Loading documents into knowledge base...")
            for doc in documents:
                self.rag_engine.index_document(doc)
            
            # Test the knowledge base
            test_results = self.rag_engine.search("product", top_k=3, score_threshold=0.1)
            logger.info(f"📚 Knowledge base loaded. Test query found {len(test_results)} results")
            
        except Exception as e:
            logger.error(f"❌ Error loading knowledge base: {e}")
    
    def _init_conversation_state(self) -> Dict:
        """Initialize a new conversation state."""
        return {
            'history': [],
            'context': {},
            'appointment_flow': None,
            'appointment_data': {},
            'current_question': None,
            'waiting_for_confirmation': False,
            'start_time': datetime.now().isoformat(),
            'message_count': 0,
            'last_intent': None,
            'demo_flow': False,
            'last_menu': None,
            'modifying_existing_appointment': False,
            'existing_appointment_id': None,
            'failure_reasons': [],  
            'last_escalation_check': None  
        }
    
    def _log_processing_info(self, user_id: str, message: str, 
                            intent_details: Dict, conv_state: Dict):
        """Log processing information."""
        logger.info(f"\n{'='*60}")
        logger.info(f"User: {user_id}")
        logger.info(f"Message: '{message}'")
        logger.info(f"Intent: {intent_details['intent']} (confidence: {intent_details.get('confidence', 0):.2f})")
        logger.info(f"Entities: {intent_details.get('entities', {})}")
        logger.info(f"Flow: {conv_state.get('appointment_flow')}")
        logger.info(f"Failure count: {len(conv_state.get('failure_reasons', []))}")
        logger.info(f"{'='*60}\n")
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Main entry point for processing messages."""
        try:
            clean_message = message.strip().strip('"\'')
            sanitized_message = self.security.sanitize_input(clean_message)
            
            # Get or create conversation state
            if user_id not in self.conversations:
                self.conversations[user_id] = self._init_conversation_state()
            
            conv_state = self.conversations[user_id]
            conv_state['message_count'] += 1
            
            # Build context for intent classification
            context = {
                'last_bot_message': conv_state['history'][-1].get('bot', '') if conv_state['history'] else '',
                'appointment_flow': conv_state.get('appointment_flow'),
                'waiting_for_confirmation': conv_state.get('waiting_for_confirmation', False),
                'modifying_existing_appointment': conv_state.get('modifying_existing_appointment', False),
                'history': [h.get('user', '') for h in conv_state['history'][-5:]]
            }
            
            # Get intent with context
            intent_details = self.intent_classifier.get_intent_details(sanitized_message, context)
            conv_state['last_intent'] = intent_details['intent']
            
            #  Check for escalation BEFORE normal routing
            escalation_context = {
                'current_message': sanitized_message,
                'last_bot_message': context.get('last_bot_message', ''),
                'history': [h.get('user', '') for h in conv_state['history'][-5:]],
                'intent_confidence': intent_details.get('confidence', 1.0),
                'current_question': conv_state.get('current_question'),
                'waiting_for_confirmation': conv_state.get('waiting_for_confirmation', False)
            }
            
            escalation_decision = self.escalation_handler.should_escalate(
                user_id, 
                sanitized_message, 
                escalation_context
            )
            
            if escalation_decision['should_escalate']:
                logger.warning(f"🚨 Escalation triggered: {escalation_decision['reason']}")
                
                # Initiate escalation
                escalation_ticket = self.escalation_handler.initiate_escalation(
                    user_id,
                    {
                        'user_id': user_id,
                        'history': conv_state['history'][-10:] if conv_state['history'] else [],
                        'failure_reasons': conv_state.get('failure_reasons', []),
                        'current_context': escalation_context
                    },
                    escalation_decision['reason']
                )
                
                # Add failure reason to track
                conv_state['failure_reasons'].append(escalation_decision['reason'])
                
                return {
                    'response': self.escalation_handler.get_escalation_message(escalation_ticket['ticket_id']),
                    'intent': 'escalation',
                    'needs_escalation': True,
                    'escalation_ticket_id': escalation_ticket['ticket_id'],
                    'escalation_reason': escalation_decision['reason'],
                    'priority': escalation_decision['priority']
                }
            
            # Log processing info
            self._log_processing_info(user_id, sanitized_message, intent_details, conv_state)
            
            # Route message
            response = self._route_message(user_id, sanitized_message, intent_details, conv_state, context)
            
            #  Check if response indicates failure
            if response.get('intent') in ['error', 'unknown'] and response.get('confidence', 1) < 0.3:
                failure_reason = f"Low confidence response for intent: {response.get('intent')}"
                conv_state['failure_reasons'].append(failure_reason)
                logger.warning(f"⚠️ Conversation failure recorded: {failure_reason}")
            
            # Update history
            self._update_history(conv_state, sanitized_message, response, intent_details)
            
            # Reset failure tracker on successful interaction
            if response.get('intent') in ['appointment_confirmed', 'knowledge_base', 'greeting']:
                if conv_state.get('failure_reasons'):
                    self.escalation_handler.reset_user_tracker(user_id)
                    conv_state['failure_reasons'] = []
                    logger.info(f"🔄 Reset failure tracker for user {user_id} after successful interaction")
            
            # Cleanup old conversations
            self._cleanup_old_conversations()
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in process_message: {str(e)}", exc_info=True)
            return IntentHandlers.handle_error()
    
    def _update_history(self, conv_state: Dict, message: str, response: Dict, intent_details: Dict):
        """Update conversation history."""
        conv_state['history'].append({
            'user': self.security.mask_pii(message),
            'bot': self.security.mask_pii(response.get('response', '')),
            'timestamp': datetime.now().isoformat(),
            'intent': intent_details['intent'],
            'needs_escalation': response.get('needs_escalation', False)
        })
    
    def _determine_demo_product(self, conv_state: Dict) -> str:
        """Determine which product to demo based on conversation history."""
        # Look for product mentions in recent conversation history
        history = conv_state.get('history', [])
        
        # Check last few messages for product mentions
        for i in range(min(5, len(history))):
            item = history[-(i+1)]  # Look backwards from most recent
            user_msg = item.get('user', '').lower()
            bot_msg = item.get('bot', '').lower()
            
            # Check user messages
            if 'enterprise' in user_msg or 'suite' in user_msg:
                return 'enterprise_suite'
            elif 'analytics' in user_msg:
                return 'analytics_pro'
            elif 'cloud' in user_msg:
                return 'cloud_services'
            
            # Check bot messages
            if 'enterprise suite' in bot_msg:
                return 'enterprise_suite'
            elif 'analytics pro' in bot_msg:
                return 'analytics_pro'
            elif 'cloud services' in bot_msg:
                return 'cloud_services'
        
        # Default to general demo
        return 'general'

    def _route_message(self, user_id: str, message: str, intent_details: Dict, 
                conv_state: Dict, context: Dict) -> Dict:
        """Route message to appropriate handler."""
        intent = intent_details['intent']
        
        #  Check appointment flow FIRST (including service selection) 
        if (conv_state.get('appointment_flow') in ['started', 'collecting_details', 'modifying'] and 
            conv_state.get('current_question') == 'service_type'):
            
            # Check if message is a number (1-6) for service selection
            if message.strip() in ['1', '2', '3', '4', '5', '6']:
                logger.info(f"🔍 In appointment flow, service type selection: {message}")
                return self._handle_appointment_number_selection(message.strip(), conv_state)
            
            # Check if message is a service type name
            service_type = self._extract_service_type_from_text(message)
            if service_type:
                logger.info(f"🔍 Extracted service type from text: {service_type}")
                conv_state['appointment_data']['service_type'] = service_type
                
                # Determine next question using appointment_flow
                next_question = self.appointment_flow._get_next_appointment_info(conv_state['appointment_data'])
                conv_state['current_question'] = next_question
                
                if next_question == 'complete':
                    conv_state['waiting_for_confirmation'] = True
                    return self._show_confirmation(conv_state['appointment_data'])
                
                return self.appointment_flow._generate_smart_response(conv_state['appointment_data'], next_question)
        
       
       #  Handle menu selections (but only if NOT in appointment flow) 
        if intent == 'menu_selection':
            # Check if we're in appointment flow - if so, treat as regular message
            if conv_state.get('appointment_flow'):
                logger.info(f"⚠️ Menu selection '{message}' while in appointment flow, treating as text")
                # Fall through to appointment flow handler
            else:
                # Handle menu selection
                response = IntentHandlers.handle_menu_selection(message, context)
                
                #  Handle menu-based escalations 
                if response.get('needs_escalation') and response.get('intent') == 'escalation':
                    logger.info(f"🚨 Menu selection '{message}' requires escalation")
                    
                    # Create escalation ticket using the DialogManager's escalation handler
                    escalation_ticket = self.escalation_handler.initiate_escalation(
                        user_id,  # Use ACTUAL user_id
                        {
                            'user_id': user_id,
                            'history': conv_state['history'][-10:] if conv_state['history'] else [],
                            'menu_selection': message,
                            'context': context.get('last_bot_message', '')[:100]
                        },
                        response.get('escalation_reason', f'Menu selection {message} requested specialist')
                    )
                    
                    # Get the proper escalation message
                    escalation_message = self.escalation_handler.get_escalation_message(escalation_ticket['ticket_id'])
                    
                    return {
                        'response': escalation_message,
                        'intent': 'escalation',
                        'needs_escalation': True,
                        'escalation_ticket_id': escalation_ticket['ticket_id'],
                        'escalation_reason': response.get('escalation_reason', 'Menu selection')
                    }
                
                # Check if this menu selection should start a demo flow
                if response.get('start_demo_flow'):
                    logger.info(f"🚀 Starting demo flow from menu selection: '{message}'")
                    
                    # Determine which product to demo based on conversation history
                    demo_product = self._determine_demo_product(conv_state)
                    
                    # Start demo appointment flow
                    conv_state['appointment_flow'] = 'started'
                    conv_state['appointment_data'] = {
                        'service_type': 'demo',
                        'demo_type': 'product_demo',
                        'demo_product': demo_product
                    }
                    conv_state['current_question'] = 'date'
                    conv_state['waiting_for_confirmation'] = False
                    
                    product_display = {
                        'enterprise_suite': 'COB Enterprise Suite',
                        'analytics_pro': 'COB Analytics Pro', 
                        'cloud_services': 'COB Cloud Services',
                        'general': 'our products'
                    }.get(demo_product, 'our products')
                    
                    return {
                        'response': f"""🎥 **Schedule a {product_display} Demo**

        I'd be happy to schedule a demo of {product_display} for you!

        **When would you like to schedule your demo?**

        Please provide a date:
        • Today/Tomorrow
        • Next Monday/Tuesday/etc.
        • Specific date like December 15
        • Day of week like Friday""",
                        'intent': 'action',
                        'needs_escalation': False,
                        'action_required': True
                    }
                
                return response
        
        # ========== Original routing logic ==========
        # PRIORITY 1: Handle confirmations
        if conv_state.get('waiting_for_confirmation'):
            return self._handle_confirmation(user_id, message, conv_state)
        
        # Also handle confirmation intent even if not flagged yet
        if intent == 'confirmation' and conv_state.get('appointment_flow') == 'started':
            conv_state['waiting_for_confirmation'] = True
            return self._handle_confirmation(user_id, message, conv_state)
        
        # PRIORITY 2: Handle appointment flow (including modification flow)
        if conv_state.get('appointment_flow') in ['started', 'collecting_details', 'modifying']:
            if self._is_cancellation_request(message):
                return self._cancel_appointment_flow(user_id, conv_state)
            
            # Check if it's a number selection in appointment flow (for other questions)
            if message.strip() in ['1', '2', '3', '4', '5', '6']:
                return self._handle_appointment_number_selection(message.strip(), conv_state)
            
            return self.appointment_flow.handle_flow(user_id, message, conv_state, intent_details)
        
        # Check if appointment was completed and user is asking something else 
        if (conv_state.get('appointment_flow') is None and 
            conv_state.get('last_intent') == 'appointment_confirmed' and
            intent not in ['confirmation', 'action']):
            
            # User is asking something new after appointment was booked
            logger.info(f"🔄 Handling new query after appointment booking")
            
            # Reset the last_intent so we don't keep thinking it's appointment related
            conv_state['last_intent'] = intent
            
            # Route to appropriate handler
            if intent == 'menu_selection':
                return IntentHandlers.handle_menu_selection(message, context)
            elif intent == 'greeting':
                return IntentHandlers.handle_greeting(intent_details)
            elif intent == 'goodbye':
                return IntentHandlers.handle_goodbye(intent_details)
            elif intent == 'knowledge_base':
                return self.knowledge_service.handle_query(message, intent_details)
            elif intent == 'escalation':
                # Use escalation handler instead of IntentHandlers
                escalation_ticket = self.escalation_handler.initiate_escalation(
                    user_id,
                    {
                        'user_id': user_id,
                        'history': conv_state['history'][-10:] if conv_state['history'] else []
                    },
                    "User requested assistance"
                )
                
                return {
                    'response': self.escalation_handler.get_escalation_message(escalation_ticket['ticket_id']),
                    'intent': 'escalation',
                    'needs_escalation': True,
                    'escalation_ticket_id': escalation_ticket['ticket_id']
                }
        
        #  UPDATED: Handle frustration/escalation using escalation handler 
        if intent_details.get('is_frustrated') or intent == 'escalation':
            escalation_ticket = self.escalation_handler.initiate_escalation(
                user_id,
                {
                    'user_id': user_id,
                    'history': conv_state['history'][-10:] if conv_state['history'] else [],
                    'failure_reasons': conv_state.get('failure_reasons', [])
                },
                "User appears frustrated or requested escalation"
            )
            
            return {
                'response': self.escalation_handler.get_escalation_message(escalation_ticket['ticket_id']),
                'intent': 'escalation',
                'needs_escalation': True,
                'escalation_ticket_id': escalation_ticket['ticket_id']
            }
        
        # PRIORITY 5: Handle appointment change request
        if self._is_appointment_change_request(message):
            return self._handle_appointment_change_request(user_id, message, conv_state)
        
        # PRIORITY 6: Handle specific intents
        if intent == 'action':
            return self._start_appointment_flow(user_id, message, intent_details)
        elif intent == 'greeting':
            return IntentHandlers.handle_greeting(intent_details)
        elif intent == 'goodbye':
            return IntentHandlers.handle_goodbye(intent_details)
        elif intent == 'knowledge_base':
            return self.knowledge_service.handle_query(message, intent_details)
        
        # DEFAULT: Treat as knowledge query
        return self.knowledge_service.handle_query(message, intent_details)
    
    def _extract_service_type_from_text(self, message: str) -> Optional[str]:
        """Extract service type from text."""
        message_lower = message.lower().strip()
        
        service_map = {
            'consultation': ['consultation', 'consult', 'advice', 'guidance'],
            'support': ['support', 'help', 'assistance', 'fix', 'issue', 'problem'],
            'installation': ['installation', 'install', 'setup', 'implement'],
            'maintenance': ['maintenance', 'maintain', 'service', 'checkup'],
            'training': ['training', 'train', 'learn', 'teach', 'educate'],
            'demo': ['demo', 'demonstration', 'show', 'presentation']
        }
        
        for service, keywords in service_map.items():
            if any(keyword in message_lower for keyword in keywords):
                return service
        
        return None
    
    def _is_appointment_change_request(self, message: str) -> bool:
        """Check if user wants to change an appointment."""
        change_keywords = ['change', 'modify', 'update', 'edit', 'reschedule']
        appointment_mentions = ['appointment', 'meeting', 'schedule', 'booking', 'demo']
        
        message_lower = message.lower()
        
        for keyword in change_keywords:
            if keyword in message_lower:
                for appointment_word in appointment_mentions:
                    if appointment_word in message_lower:
                        return True
        
        return False
    
    def _handle_appointment_change_request(self, user_id: str, message: str, conv_state: Dict) -> Dict:
        """Handle requests to change an appointment."""
        user_appointments = self.appointment_service.get_user_appointments(user_id)
        
        if not user_appointments:
            return {
                'response': "I couldn't find any existing appointments for you. Would you like to schedule a new appointment instead?",
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        
        if len(user_appointments) == 1:
            appointment = user_appointments[0]
            return self._start_appointment_modification(user_id, appointment, conv_state)
        
        # Multiple appointments - ask which one
        appointments_list = "\n".join([
            f"{i+1}. **{apt['service_type'].title()}** on {apt['date']} at {apt['time']} (ID: {apt['appointment_id']})"
            for i, apt in enumerate(user_appointments[:5])
        ])
        
        conv_state['pending_appointment_selection'] = True
        conv_state['available_appointments'] = user_appointments
        
        return {
            'response': f"""🔄 **Which appointment would you like to change?**

You have {len(user_appointments)} appointment(s):

{appointments_list}

Please reply with the number (1-{len(user_appointments)}) of the appointment you want to change.""",
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True
        }
    
    def _start_appointment_modification(self, user_id: str, appointment: Dict, conv_state: Dict) -> Dict:
        """Start modifying an existing appointment."""
        conv_state['appointment_flow'] = 'modifying'
        conv_state['modifying_existing_appointment'] = True
        conv_state['existing_appointment_id'] = appointment['appointment_id']
        conv_state['appointment_data'] = {
            'service_type': appointment.get('service_type', ''),
            'date': appointment.get('date', ''),
            'time': appointment.get('time', ''),
            'customer_name': appointment.get('customer_name', ''),
            'email': appointment.get('email', '')
        }
        conv_state['current_question'] = None
        conv_state['waiting_for_confirmation'] = False
        
        current_details = []
        for field, value in conv_state['appointment_data'].items():
            if value and field != 'demo_type':
                current_details.append(f"• **{field.replace('_', ' ').title()}**: {value}")
        
        details_text = "\n".join(current_details)
        
        return {
            'response': f"""🔄 **Modifying Appointment** (ID: {appointment['appointment_id']})

Here are your current appointment details:
{details_text}

**What would you like to change?**
You can change:
• Service type
• Date  
• Time
• Name
• Email

Please tell me exactly what you want to change (e.g., "change the date" or "change the service").""",
            'intent': 'action',
            'needs_escalation': False,
            'action_required': True
        }
    
    def _start_appointment_flow(self, user_id: str, message: str, intent_details: Dict) -> Dict:
        """Start appointment booking."""
        conv_state = self.conversations[user_id]
        
        if conv_state.get('appointment_flow') not in ['started', 'collecting_details', 'modifying']:
            conv_state['appointment_flow'] = 'started'
            conv_state['appointment_data'] = {}
            conv_state['current_question'] = None
            conv_state['waiting_for_confirmation'] = False
        
        # Extract info using appointment flow
        response = self.appointment_flow.handle_flow(user_id, message, conv_state, intent_details)
        
        # Add greeting only if just started
        if len([h for h in conv_state.get('history', []) if 'appointment' in h.get('bot', '').lower()]) == 0:
            greeting = "I'd be happy to help you schedule an appointment! 📅\n\n"
            response['response'] = greeting + response['response']
        
        return response
    
    def _handle_appointment_number_selection(self, selection: str, conv_state: Dict) -> Dict:
        """Handle number selections when in appointment flow."""
        appointment_data = conv_state['appointment_data']
        current_question = conv_state.get('current_question')
        
        logger.info(f"🔍 Handling appointment number selection: {selection} for question: {current_question}")
        
        # Map numbers to service types - ONLY FOR SERVICE TYPE SELECTION
        service_mapping = {
            '1': 'consultation',
            '2': 'support', 
            '3': 'installation',
            '4': 'maintenance',
            '5': 'training'
        }
        
        # Handle service type selection
        if current_question == 'service_type' and selection in service_mapping:
            appointment_data['service_type'] = service_mapping[selection]
            logger.info(f"✅ Selected service type: {appointment_data['service_type']}")
            
            # Determine next question using appointment_flow
            next_question = self.appointment_flow._get_next_appointment_info(appointment_data)
            conv_state['current_question'] = next_question
            
            # If all fields are complete, show confirmation immediately
            if next_question == 'complete':
                conv_state['waiting_for_confirmation'] = True
                logger.info("✅ All fields complete, showing confirmation immediately")
                
                # Check if we're modifying an existing appointment
                if conv_state.get('modifying_existing_appointment'):
                    appointment_id = conv_state.get('existing_appointment_id')
                    return self._show_modification_confirmation(appointment_data, appointment_id)
                else:
                    return self._show_confirmation(appointment_data)
            
            return self.appointment_flow._generate_smart_response(appointment_data, next_question)
        
        # If not service type selection, treat as regular text
        logger.info(f"❌ Selection '{selection}' not for service type, treating as text")
        return self.appointment_flow.handle_flow(
            "user_127_0_0_1",  # user_id placeholder
            selection,
            conv_state,
            {'intent': 'unknown', 'entities': {}}
        )
    
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
    
    def _handle_confirmation(self, user_id: str, message: str, conv_state: Dict) -> Dict:
        """Handle yes/no confirmation responses."""
        text_lower = message.lower().strip()
        
        yes_responses = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'correct', 'right', 'confirm', 'confirmed', 'y', 'yea']
        no_responses = ['no', 'nope', 'nah', 'wrong', 'incorrect', 'change', 'edit', 'n']
        
        is_yes = any(word == text_lower for word in yes_responses)
        is_no = any(word == text_lower for word in no_responses)
        
        if not is_yes:
            is_yes = any(word in text_lower.split() for word in yes_responses)
        
        if not is_no:
            is_no = any(word in text_lower.split() for word in no_responses)
        
        logger.info(f"🔍 Confirmation check - Is yes: {is_yes}, Is no: {is_no}")
        
        if is_yes:
            conv_state['waiting_for_confirmation'] = False
            
            if conv_state.get('modifying_existing_appointment'):
                appointment_id = conv_state.get('existing_appointment_id')
                return self._update_existing_appointment(user_id, conv_state['appointment_data'], appointment_id)
            else:
                return self._complete_appointment(user_id, conv_state['appointment_data'])
        
        elif is_no:
            conv_state['waiting_for_confirmation'] = False
            conv_state['appointment_flow'] = 'modifying'
            conv_state['current_question'] = None
            
            modifying_existing = conv_state.get('modifying_existing_appointment', False)
            appointment_id = conv_state.get('existing_appointment_id')
            
            if modifying_existing and appointment_id:
                response_text = f"""🔄 **What would you like to change in your appointment?** (ID: {appointment_id})

You can change:
• Service type
• Date  
• Time
• Name
• Email

Please tell me exactly what you want to change (e.g., "change the date" or "change the service")."""
            else:
                response_text = """🔄 **What would you like to change?**

You can change:
• Service type
• Date  
• Time
• Name
• Email

Please tell me exactly what you want to change (e.g., "change the date" or "change the service")."""
            
            return {
                'response': response_text,
                'intent': 'action',
                'needs_escalation': False,
                'action_required': True
            }
        
        else:
            # Show confirmation again
            modifying_existing = conv_state.get('modifying_existing_appointment', False)
            
            if modifying_existing:
                appointment_id = conv_state.get('existing_appointment_id')
                confirmation_message = ResponseTemplates.appointment_modification_confirmation(
                    conv_state['appointment_data'], appointment_id
                )
            else:
                confirmation_message = ResponseTemplates.appointment_confirmation(
                    conv_state['appointment_data'], "PENDING"
                )
            
            confirmation_message += "\n\n**Please reply with:**\n✅ **\"Yes\"** to confirm\n❌ **\"No\"** to make changes\n\n*(Just type \"yes\" or \"no\")*"
            
            return {
                'response': confirmation_message,
                'intent': 'action',
                'needs_escalation': False,
                'action_required': True,
                'waiting_for_confirmation': True
            }
    
    def _complete_appointment(self, user_id: str, appointment_data: Dict) -> Dict:
        """Complete appointment booking."""
        try:
            appointment = self.appointment_service.create_appointment(user_id, appointment_data)
            
            # Try to send email
            email_sent = False
            try:
                from app.utils.email_sender import email_sender
                email_sent = email_sender.send_appointment_confirmation(
                    appointment_data.get('email', ''),
                    appointment
                )
                if email_sent:
                    logger.info(f"✅ Confirmation email sent")
                else:
                    logger.warning(f"⚠️ Could not send email")
            except Exception as e:
                logger.warning(f"Email sending error: {e}")
                email_sent = False
            
            # COMPLETELY CLEAR APPOINTMENT STATE 
            conv_state = self.conversations[user_id]
            
            # Save the appointment details for confirmation message
            appointment_details = {
                'service_type': appointment_data.get('service_type', ''),
                'date': appointment_data.get('date', ''),
                'time': appointment_data.get('time', ''),
                'customer_name': appointment_data.get('customer_name', ''),
                'email': appointment_data.get('email', '')
            }
            
            # CRITICAL: Reset ALL appointment-related state
            conv_state['appointment_flow'] = None
            conv_state['appointment_data'] = {}
            conv_state['current_question'] = None
            conv_state['waiting_for_confirmation'] = False
            conv_state['modifying_existing_appointment'] = False
            conv_state['existing_appointment_id'] = None
            conv_state['pending_appointment_selection'] = False
            conv_state['available_appointments'] = None
            
            # Reset failure tracker on successful appointment
            self.escalation_handler.reset_user_tracker(user_id)
            conv_state['failure_reasons'] = []
            
            logger.info(f"✅ Appointment {appointment['appointment_id']} booked and state cleared")
            
            # Create success message
            email_status = "✅ Confirmation email has been sent" if email_sent else "⚠️ Could not send confirmation email"
            
            confirmation = f"""✅ **Appointment Successfully Booked!**

📋 **Your Appointment Details:**
━━━━━━━━━━━━━━━━━━━━━━
• **Service:** {appointment_details.get('service_type', '').title()}
• **Date:** {appointment_details.get('date', '')}
• **Time:** {appointment_details.get('time', '')}
• **Name:** {appointment_details.get('customer_name', '')}
━━━━━━━━━━━━━━━━━━━━━━

{email_status} to: **{appointment_details.get('email', '')}**

**Appointment ID:** `{appointment['appointment_id']}`

Thank you for choosing COB Company! 🎉

Is there anything else I can help you with?"""
            
            return {
                'response': confirmation,
                'intent': 'appointment_confirmed',
                'needs_escalation': False,
                'appointment_id': appointment['appointment_id']
            }
                
        except Exception as e:
            logger.error(f"❌ Error completing appointment: {e}")
            # Record this as a failure for escalation tracking
            conv_state = self.conversations.get(user_id, {})
            failure_reason = f"Appointment booking error: {str(e)[:50]}"
            conv_state['failure_reasons'] = conv_state.get('failure_reasons', []) + [failure_reason]
            
            return IntentHandlers.handle_escalation(user_id, f"Technical error: {str(e)[:50]}")   
    
    def _update_existing_appointment(self, user_id: str, appointment_data: Dict, appointment_id: str) -> Dict:
        """Update an existing appointment."""
        try:
            updated = self.appointment_service.update_appointment(appointment_id, appointment_data)
            
            if updated:
                # Clear appointment state
                conv_state = self.conversations[user_id]
                conv_state['appointment_flow'] = None
                conv_state['appointment_data'] = {}
                conv_state['current_question'] = None
                conv_state['waiting_for_confirmation'] = False
                conv_state['modifying_existing_appointment'] = False
                conv_state['existing_appointment_id'] = None
                
                logger.info(f"✅ Appointment {appointment_id} updated")
                
                return {
                    'response': f"""✅ **Appointment Successfully Updated!**

Your appointment (ID: {appointment_id}) has been updated with the new details.

📋 **Updated Appointment Details:**
━━━━━━━━━━━━━━━━━━━━━
• **Service:** {appointment_data.get('service_type', '').title()}
• **Date:** {appointment_data.get('date', '')}
• **Time:** {appointment_data.get('time', '')}
• **Name:** {appointment_data.get('customer_name', '')}
• **Email:** {appointment_data.get('email', '')}
━━━━━━━━━━━━━━━━━━━━━

A confirmation email has been sent to {appointment_data.get('email', '')}.

Is there anything else I can help you with?""",
                    'intent': 'appointment_updated',
                    'needs_escalation': False
                }
            else:
                # Record failure for escalation tracking
                conv_state = self.conversations.get(user_id, {})
                failure_reason = "Could not find appointment to update"
                conv_state['failure_reasons'] = conv_state.get('failure_reasons', []) + [failure_reason]
                
                return IntentHandlers.handle_escalation(user_id, "Could not find appointment to update")
                
        except Exception as e:
            logger.error(f"❌ Error updating appointment: {e}")
            # Record failure for escalation tracking
            conv_state = self.conversations.get(user_id, {})
            failure_reason = f"Update error: {str(e)[:50]}"
            conv_state['failure_reasons'] = conv_state.get('failure_reasons', []) + [failure_reason]
            
            return IntentHandlers.handle_escalation(user_id, f"Update error: {str(e)[:50]}")
    
    def _is_cancellation_request(self, message: str) -> bool:
        """Check if user wants to cancel."""
        cancel_words = ['cancel', 'stop', 'exit', 'nevermind', 'forget it', 'abort']
        return any(word in message.lower() for word in cancel_words)
    
    def _cancel_appointment_flow(self, user_id: str, conv_state: Dict) -> Dict:
        """Cancel appointment flow."""
        conv_state['appointment_flow'] = None
        conv_state['appointment_data'] = {}
        conv_state['current_question'] = None
        conv_state['waiting_for_confirmation'] = False
        conv_state['modifying_existing_appointment'] = False
        conv_state['existing_appointment_id'] = None
        
        return {
            'response': "Appointment booking cancelled. How else can I help you today?",
            'intent': 'cancel',
            'needs_escalation': False
        }
    
    def _cleanup_old_conversations(self, max_age_minutes: int = 60):
        """Clean up old conversations."""
        current_time = datetime.now()
        to_remove = []
        
        for user_id, conv in self.conversations.items():
            start_time = datetime.fromisoformat(conv.get('start_time', current_time.isoformat()))
            age = (current_time - start_time).total_seconds() / 60
            
            if age > max_age_minutes:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            # Clean up escalation tracker too
            self.escalation_handler.reset_user_tracker(user_id)
            del self.conversations[user_id]
            logger.info(f"🗑️  Cleaned up old conversation for user: {user_id}")
    
    # Public methods for API
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        """Get conversation history."""
        return self.conversations.get(user_id, {}).get('history', [])
    
    def get_active_conversations(self) -> List[str]:
        """Get active conversations."""
        return list(self.conversations.keys())
    
    def get_all_appointments(self) -> List[Dict]:
        """Get all appointments."""
        return self.appointment_service.appointments
    
    def get_user_appointments(self, user_id: str) -> List[Dict]:
        """Get user's appointments."""
        return self.appointment_service.get_user_appointments(user_id)
    
    def clear_conversation(self, user_id: str):
        """Clear conversation."""
        if user_id in self.conversations:
            # Also reset escalation tracker
            self.escalation_handler.reset_user_tracker(user_id)
            del self.conversations[user_id]
            logger.info(f"🗑️  Cleared conversation for user: {user_id}")
    
    # NEW: Escalation-related methods
    def get_escalation_queue(self) -> List[Dict]:
        """Get escalation queue (for admin/monitoring)."""
        return self.escalation_handler.get_escalation_queue()
    
    def get_user_escalation_history(self, user_id: str) -> List[Dict]:
        """Get escalation history for a user."""
        return self.escalation_handler.get_user_escalation_history(user_id)
    
    def reset_user_escalation_tracker(self, user_id: str):
        """Reset user's escalation tracker (admin/testing)."""
        self.escalation_handler.reset_user_tracker(user_id)
        logger.info(f"🔄 Reset escalation tracker for user: {user_id}")