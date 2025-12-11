"""
Knowledge service for handling queries against the knowledge base.
Separates knowledge logic from dialog flow.
"""

from typing import Dict, List, Optional, Any
import re
from loguru import logger

from app.chatbot.rag_engine import RAGEngine
from app.config.business_rules import PRODUCT_CATEGORIES


class KnowledgeService:
    """Service for handling knowledge base queries."""
    
    def __init__(self, rag_engine: RAGEngine):
        self.rag_engine = rag_engine
    
    def handle_query(self, query: str, intent_details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle knowledge base query with intelligent routing."""
        logger.info(f"🔍 Knowledge query: '{query}'")
        
        # Route to specialized handlers
        if self._is_support_request(query):
            return self._handle_support_request(query)
        elif self._is_product_inquiry(query, intent_details):
            return self._handle_product_inquiry(query)
        elif self._is_pricing_query(query):
            return self._handle_pricing_query(query)
        else:
            return self._handle_general_knowledge(query)
    
    def _is_support_request(self, message: str) -> bool:
        """Check if message is requesting support."""
        support_keywords = [
            'support', 'help', 'assistance', 'technical', 'problem', 
            'issue', 'not working', 'broken', 'error', 'trouble',
            'fix', 'resolve', 'assist me', 'help me'
        ]
        
        message_lower = message.lower()
        
        for keyword in support_keywords:
            if keyword in message_lower:
                return True
        
        support_patterns = [
            r'need.*(help|support|assistance)',
            r'want.*(help|support|assistance)',
            r'looking for.*(help|support|assistance)',
            r'(help|support|assistance).*with'
        ]
        
        for pattern in support_patterns:
            if re.search(pattern, message_lower):
                return True
        
        return False
    
    def _is_product_inquiry(self, message: str, entities: Dict[str, Any]) -> bool:
        """Check if message is about products."""
        product_keywords = ['product', 'service', 'solution', 'enterprise', 'analytics', 
                           'cloud', 'feature', 'capability', 'platform']
        
        if entities.get('enterprise') or entities.get('analytics'):
            return True
        
        return any(keyword in message.lower() for keyword in product_keywords)
    
    def _is_pricing_query(self, message: str) -> bool:
        """Check if message is about pricing."""
        pricing_keywords = ['price', 'pricing', 'cost', 'plan', 'subscription', 
                           'how much', 'fee', 'payment']
        return any(keyword in message.lower() for keyword in pricing_keywords)
    
    def _handle_support_request(self, message: str) -> Dict[str, Any]:
        """Handle support requests."""
        logger.info(f"🆘 Support request: '{message}'")
        
        # Check if user wants a specialist
        if any(phrase in message.lower() for phrase in ['speak with', 'talk to', 'connect with', 'human', 'agent', 'specialist']):
            return {
                'response': "I'll connect you with a specialist right away. Please hold while I transfer you...\n\n**Transferring to specialist...** ⏳",
                'intent': 'escalation',
                'needs_escalation': True
            }
        
        # Search knowledge base
        results = self.rag_engine.search(message, top_k=5, score_threshold=0.1)
        
        if results:
            answer = self.rag_engine.generate_answer(message, results)
            answer = self._clean_up_answer(answer)
            
            answer += "\n\n**Would you like:**\n"
            answer += "1. **Connect with a support specialist** 👨‍💼\n"
            answer += "2. **Schedule a support appointment** 📅\n"
            answer += "3. **More information** about this issue ℹ️\n\n"
            answer += "Reply with 1, 2, or 3, or ask another question."
            
            return {
                'response': answer,
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        else:
            from app.config.response_templates import ResponseTemplates
            return {
                'response': ResponseTemplates.support_menu(),
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
    
    def _handle_product_inquiry(self, message: str) -> Dict[str, Any]:
        """Handle product inquiries."""
        logger.info(f"🔍 Product inquiry: '{message}'")
        
        results = self.rag_engine.search(message, top_k=8, score_threshold=0.05)
        
        if not results:
            return self._no_product_info_response()
        
        answer = self.rag_engine.generate_answer(message, results)
        answer = self._clean_up_answer(answer)
        
        # Add structured product info
        structured_info = self._get_structured_product_info(message, results)
        if structured_info:
            answer = structured_info + "\n\n" + answer
        
        from app.config.response_templates import ResponseTemplates
        answer += "\n\n" + ResponseTemplates.product_menu()
        
        return {
            'response': answer,
            'intent': 'knowledge_base',
            'needs_escalation': False
        }
    
    def _handle_pricing_query(self, message: str) -> Dict[str, Any]:
        """Handle pricing queries."""
        pricing_info = self._get_pricing_details()
        return {
            'response': pricing_info,
            'intent': 'knowledge_base',
            'needs_escalation': False
        }
    
    def _handle_general_knowledge(self, message: str) -> Dict[str, Any]:
        """Handle general knowledge queries."""
        logger.info(f"🔍 General query: '{message}'")
        
        results = self.rag_engine.search(message, top_k=5, score_threshold=0.1)
        
        if results:
            answer = self.rag_engine.generate_answer(message, results)
            answer = self._clean_up_answer(answer)
            
            follow_up = self._get_knowledge_follow_up(message, results)
            answer += follow_up
            
            return {
                'response': answer,
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
        else:
            from app.config.response_templates import ResponseTemplates
            return {
                'response': ResponseTemplates.no_knowledge_found(message),
                'intent': 'knowledge_base',
                'needs_escalation': False
            }
    
    def _clean_up_answer(self, answer: str) -> str:
        """Clean up RAG-generated answer."""
        import re
        
        # Remove markdown headers
        answer = re.sub(r'#{1,6}\s*', '', answer)
        # Remove category labels
        answer = re.sub(r'\*\*.*?:\*\*', '', answer)
        # Fix bullet point formatting
        answer = answer.replace('•', '•')
        # Remove extra whitespace
        answer = re.sub(r'\n\s*\n\s*\n', '\n\n', answer)
        # Capitalize first letter
        if answer and answer[0].islower():
            answer = answer[0].upper() + answer[1:]
        
        return answer.strip()
    
    def _get_structured_product_info(self, message: str, results: List[Dict]) -> str:
        """Extract structured product information."""
        message_lower = message.lower()
        
        for product_key, product_info in PRODUCT_CATEGORIES.items():
            if any(keyword in message_lower for keyword in product_info['keywords']):
                return f"""**{product_info['name']}**
                
**Overview:** {product_info['description']}

**Learn more in our knowledge base or ask for specific features!**"""
        
        return ""
    
    def _get_pricing_details(self) -> str:
        """Get detailed pricing information."""
        return """**📋 Pricing Details**

**COB Enterprise Suite:**
- Basic: $99/user/month (5-50 users) - Core features, email support
- Professional: $199/user/month (50-200 users) - Advanced features, phone support
- Enterprise: Custom pricing (200+ users) - All features, dedicated support

**COB Analytics Pro:**
- Starter: $149/month (up to 5 data sources) - Basic dashboards
- Business: $299/month (up to 20 data sources) - Advanced analytics
- Enterprise: Custom pricing (unlimited) - All features

**COB Cloud Services:** Starting at $199/month

**Special Offers:**
- Annual plans: Get 2 months free
- Bundle discounts available
- 30-day free trial (no credit card required)"""
    
    def _no_product_info_response(self) -> Dict[str, Any]:
        """Response when no product information found."""
        return {
            'response': """I couldn't find specific product information. 

**Here's what I can help with:**
• COB Enterprise Suite - Business management platform
• COB Analytics Pro - Data analytics solution
• COB Cloud Services - Cloud infrastructure
• Scheduling product demos
• Pricing information

What would you like to know more about?""",
            'intent': 'knowledge_base',
            'needs_escalation': False
        }
    
    def _get_knowledge_follow_up(self, message: str, results: List[Dict]) -> str:
        """Get appropriate follow-up based on query type."""
        message_lower = message.lower()
        
        # Check what type of information was found
        found_product_info = any('product' in result.get('content', '').lower() 
                                or 'enterprise' in result.get('content', '').lower()
                                or 'analytics' in result.get('content', '').lower() 
                                for result in results)
        
        found_consultation_info = any('consultation' in result.get('content', '').lower() 
                                    for result in results)
        
        found_support_info = any('support' in result.get('content', '').lower() 
                                for result in results)
        
        follow_up = "\n\n"
        
        #  Use consistent menu options 
        if found_product_info:
            follow_up += "**What would you like to do next?**\n"
            follow_up += "1. **Schedule a product demo** 🎥\n"
            follow_up += "2. **Get detailed pricing** 💰\n"
            follow_up += "3. **Compare different products** ⚖️\n"
            follow_up += "4. **Speak with a specialist** 👨‍💼\n\n"
            follow_up += "Reply with 1, 2, 3, or 4."
        
        elif found_consultation_info:
            follow_up += "**Interested in our consultation services?**\n"
            follow_up += "1. **Schedule a free consultation**\n"
            follow_up += "2. **Get pricing information**\n"
            follow_up += "3. **Learn about implementation process**\n"
            follow_up += "4. **Speak with a consultant**\n\n"
            follow_up += "Reply with 1, 2, 3, or 4."
        
        elif found_support_info:
            follow_up += "**Need support?**\n"
            follow_up += "1. **Connect with support specialist**\n"
            follow_up += "2. **Schedule support appointment**\n"
            follow_up += "3. **Check support plans & pricing**\n"
            follow_up += "4. **View support resources**\n\n"
            follow_up += "Reply with 1, 2, 3, or 4."
        
        else:
            follow_up += "**Would you like to:**\n"
            follow_up += "1. **Get more detailed information**\n"
            follow_up += "2. **Speak with a specialist**\n"
            follow_up += "3. **Schedule an appointment**\n"
            follow_up += "4. **Ask a different question**\n\n"
            follow_up += "Reply with 1, 2, 3, or 4."
        
        return follow_up