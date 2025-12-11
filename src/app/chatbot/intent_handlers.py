"""
Intent-specific handlers for different conversation flows.
"""

from typing import Dict, Any, Optional
from loguru import logger
import re

from app.config.response_templates import ResponseTemplates


class IntentHandlers:
    """Handlers for different intents."""
    
    @staticmethod
    def handle_greeting(intent_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle greeting intent."""
        return {
            'response': ResponseTemplates.greeting(),
            'intent': 'greeting',
            'needs_escalation': False
        }
    
    @staticmethod
    def handle_goodbye(intent_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle goodbye intent."""
        return {
            'response': ResponseTemplates.goodbye(),
            'intent': 'goodbye',
            'needs_escalation': False
        }
    
    @staticmethod
    def handle_escalation(user_id: str, reason: str) -> Dict[str, Any]:
        """DEPRECATED: Use EscalationHandler instead"""
        logger.warning(f"DEPRECATED: Using old escalation handler. Use EscalationHandler instead.")
        # Return a message indicating escalation will be handled by new system
        return {
            'response': f"I'll connect you with a specialist. Please hold...\n\nReason: {reason}",
            'intent': 'escalation',
            'needs_escalation': True
        }
    
    @staticmethod
    def handle_error() -> Dict[str, Any]:
        """Handle error intent."""
        return {
            'response': "I'm having trouble processing your request. Please try rephrasing or contact support.",
            'intent': 'error',
            'needs_escalation': True
        }
    
    @staticmethod
    def handle_menu_selection(selection: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle menu selections with improved context detection."""
        last_message = context.get('last_bot_message', '').lower()
        
        logger.info(f"🔍 Handling menu selection: '{selection}'")
        logger.info(f"🔍 Last bot message preview: '{last_message[:200]}...'")
        
        #  menu type detection 
        menu_type = None
        
        # Check for PRODUCT menu (after product inquiry)
        if any(phrase in last_message for phrase in [
            'what would you like to do next?',
            'reply with 1, 2, 3, or 4',
            'schedule a product demo',
            'get detailed pricing',
            'compare different products',
            'speak with a specialist'
        ]):
            # Specifically check if it's the standard product menu
            if ('schedule a product demo' in last_message and 
                'get detailed pricing' in last_message and
                'compare different products' in last_message and
                'speak with a specialist' in last_message):
                menu_type = 'product'
        
        # Check for PRODUCT DETAILS menu (after asking about specific features)
        elif any(phrase in last_message for phrase in [
            'would you like to:',
            'get specific product features',
            'see pricing details',
            'schedule a product demo',
            'compare different products',
            'reply with 1, 2, 3, or 4'
        ]):
            if ('would you like to:' in last_message or
                'get specific product features' in last_message):
                menu_type = 'product_details'
        
        # Check for SUPPORT menu
        elif any(phrase in last_message for phrase in [
            'would you like:',
            'connect with a support specialist',
            'schedule a support appointment',
            'more information about this issue'
        ]):
            menu_type = 'support'
        
        # Check for COMPARISON menu
        elif 'which product aligns better with your needs?' in last_message:
            menu_type = 'comparison'
        
        logger.info(f"🔍 Detected menu type: {menu_type}")
        
        # Route to appropriate handler
        if menu_type == 'product':
            return IntentHandlers._handle_product_menu(selection)
        elif menu_type == 'product_details':
            return IntentHandlers._handle_product_details_menu(selection)
        elif menu_type == 'support':
            return IntentHandlers._handle_support_menu(selection)
        elif menu_type == 'comparison':
            return IntentHandlers._handle_comparison_menu(selection)
        else:
            # Default to general menu if we can't determine
            return IntentHandlers._handle_general_menu(selection)
    
    @staticmethod
    def _handle_product_menu(selection: str) -> Dict[str, Any]:
        """Handle main product menu selections (after product inquiry)."""
        from app.config.response_templates import ResponseTemplates
        
        menu_map = {
            '1': {
                'response': "I'd be happy to schedule a product demo for you! Let's get started...",
                'intent': 'action',
                'needs_escalation': False,
                'start_demo_flow': True
            },
            '2': {
                'response': ResponseTemplates.get_pricing_details(),
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '3': {
                'response': ResponseTemplates.get_product_comparison(),
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '4': {
                'response': "",  # Will be set by DialogManager
                'intent': 'escalation',
                'needs_escalation': True,
                'escalation_reason': "User requested product specialist from menu selection 4"
            }
        }
        
        response = menu_map.get(selection, {
            'response': "Please select 1, 2, 3, or 4.",
            'intent': 'unknown',
            'needs_escalation': False
        })
        
        return response
    
    @staticmethod
    def _handle_product_details_menu(selection: str) -> Dict[str, Any]:
        """Handle product details menu (after asking about specific features)."""
        from app.config.response_templates import ResponseTemplates
        
        menu_map = {
            '1': {
                'response': """**COB Enterprise Suite Features:**

    **Core Modules:**
    • **Financial Management** - Accounting, invoicing, financial reporting
    • **CRM System** - Customer relationship management with sales tracking
    • **HR & Payroll** - Employee management, payroll, benefits administration
    • **Inventory Control** - Smart inventory with automated reordering
    • **Business Intelligence** - Advanced analytics and customizable dashboards
    • **Project Management** - Team collaboration with task tracking
    • **Mobile App** - Full functionality on iOS and Android

    **Would you like details about any specific module?**""",
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '2': {
                'response': ResponseTemplates.get_pricing_details(),
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '3': {
                'response': "I'd be happy to schedule a product demo for you! Let's get started...",
                'intent': 'action',
                'needs_escalation': False,
                'start_demo_flow': True 
            },
            '4': {
                'response': ResponseTemplates.get_product_comparison(),
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        }
        
        return menu_map.get(selection, {
            'response': "Please select 1, 2, 3, or 4.",
            'intent': 'unknown',
            'needs_escalation': False
        })
        
    @staticmethod
    def _handle_support_menu(selection: str) -> Dict[str, Any]:
        """Handle support menu selections."""
        menu_map = {
            '1': {
                'response': "",  # Will be set by DialogManager
                'intent': 'escalation',
                'needs_escalation': True,
                'escalation_reason': "Support requested from menu"
            },
            '2': {
                'response': "I'd be happy to help you schedule a support appointment!",
                'intent': 'action',
                'needs_escalation': False,
                'start_support_flow': True
            },
            '3': {
                'response': "Please tell me more about your issue so I can search our knowledge base for specific solutions.",
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        }
        
        return menu_map.get(selection, {
            'response': "Please select 1, 2, or 3.",
            'intent': 'unknown',
            'needs_escalation': False
        })

    
    
    @staticmethod
    def _handle_comparison_menu(selection: str) -> Dict[str, Any]:
        """Handle comparison menu selections."""
        menu_map = {
            '1': {
                'response': """**Detailed Feature Comparison:**

    **COB Enterprise Suite - Best for Business Management:**
    • **Financial Management:** Full accounting suite with AR/AP
    • **CRM:** Complete customer lifecycle management
    • **HR & Payroll:** End-to-end employee management
    • **Inventory:** Real-time stock management
    • **BI:** Integrated business intelligence

    **COB Analytics Pro - Best for Data Analysis:**
    • **Dashboards:** Real-time data visualization
    • **Predictive Analytics:** AI-powered forecasting
    • **Data Integration:** 100+ data sources
    • **Custom Reports:** Automated reporting
    • **API Access:** Full REST API integration

    **Which features are most important for your business?**""",
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '2': {
                'response': """**Pricing Comparison:**

    **COB Enterprise Suite:**
    - Basic: $99/user/month (Core features)
    - Professional: $199/user/month (Advanced features)
    - Enterprise: Custom pricing (All features + dedicated support)

    **COB Analytics Pro:**
    - Starter: $149/month (5 data sources)
    - Business: $299/month (20 data sources)
    - Enterprise: Custom pricing (Unlimited)

    **Which pricing model better fits your needs?**""",
                'intent': 'knowledge_base',
                'needs_escalation': False
            },
            '3': {
                'response': "",  # Will be set by DialogManager
                'intent': 'escalation',
                'needs_escalation': True,
                'escalation_reason': "Comparison specialist requested from menu"
            },
            '4': {
                'response': "Let me schedule a consultation where we can discuss which product is best for you.",
                'intent': 'action',
                'needs_escalation': False,
                'start_consultation_flow': True
            }
        }
        
        return menu_map.get(selection, {
            'response': "Please select 1, 2, 3, or 4.",
            'intent': 'unknown',
            'needs_escalation': False
        })

    
    @staticmethod
    def _handle_general_menu(selection: str) -> Dict[str, Any]:
        """Handle general menu selections (fallback)."""
        menu_map = {
            '1': {
                'response': "",  # Will be set by DialogManager
                'intent': 'escalation',
                'needs_escalation': True,
                'escalation_reason': "Specialist requested from general menu"
            },
            '2': {
                'response': "I'd be happy to help you schedule an appointment!",
                'intent': 'action',
                'needs_escalation': False,
                'start_appointment_flow': True
            },
            '3': {
                'response': "Please tell me more about what you need help with.",
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        }
        
        return menu_map.get(selection, {
            'response': "Please select 1, 2, or 3.",
            'intent': 'unknown',
            'needs_escalation': False
        })
