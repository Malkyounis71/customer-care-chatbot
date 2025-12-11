"""
Escalation handler for transferring to human agents.
Detects frustration, repeated failures, and sensitive cases.
"""

import re  # ← MUST HAVE THIS
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from loguru import logger

from app.config.settings import settings
from app.utils.security import SecurityManager


class EscalationHandler:
    """Handles escalation to human agents with intelligent triggers"""
    
    def __init__(self, security: SecurityManager):
        self.security = security
        self.escalation_queue: List[Dict] = []
        self.user_escalation_history: Dict[str, List[Dict]] = {}
        self.conversation_failure_tracker: Dict[str, Dict] = {}
        
        # Escalation triggers configuration
        self.ESCALATION_CONFIG = {
            'max_consecutive_failures': 3,
            'frustration_score_threshold': -0.6,
            'sensitive_keywords': [
                'legal', 'lawsuit', 'attorney', 'lawyer', 'sue',
                'cancel service', 'terminate', 'breach', 'privacy',
                'data breach', 'compensation', 'refund', 'complain',
                'formal complaint', 'escalate', 'manager', 'supervisor',
                'ceo', 'executive', 'board', 'regulatory', 'compliance'
            ],
            'time_window_minutes': 30,
            'min_messages_for_analysis': 3
        }
    
    def should_escalate(self, user_id: str, message: str, context: Dict) -> Dict[str, Any]:
        """
        Determine if conversation should be escalated.
        Returns escalation decision with reason.
        """
        escalation_decision = {
            'should_escalate': False,
            'reason': '',
            'priority': 'normal',
            'confidence': 0.0
        }
        
        # Check all escalation triggers
        triggers = []
        
        # Trigger 1: Explicit escalation request
        if self._is_explicit_escalation_request(message):
            triggers.append(('explicit_request', 1.0, "User explicitly requested human agent"))
        
        # Trigger 2: Frustration detection
        frustration_check = self._detect_frustration(message, context)
        if frustration_check['is_frustrated']:
            triggers.append(('frustration', frustration_check['confidence'], 
                           f"User appears frustrated: {frustration_check['reason']}"))
        
        # Trigger 3: Repeated failures
        failure_check = self._check_repeated_failures(user_id, context)
        if failure_check['should_escalate']:
            triggers.append(('repeated_failures', failure_check['confidence'],
                           f"Multiple failed interactions: {failure_check['failures']} failures"))
        
        # Trigger 4: Sensitive topics
        sensitive_check = self._contains_sensitive_topic(message)
        if sensitive_check['contains_sensitive']:
            triggers.append(('sensitive_topic', sensitive_check['confidence'],
                           f"Sensitive topic detected: {sensitive_check['topic']}"))
        
        # Trigger 5: Complex query beyond capabilities
        complexity_check = self._is_complex_query(message, context)
        if complexity_check['is_complex']:
            triggers.append(('complex_query', complexity_check['confidence'],
                           f"Complex query beyond chatbot capabilities: {complexity_check['reason']}"))
        
        # Evaluate triggers
        if triggers:
            # Sort by confidence
            triggers.sort(key=lambda x: x[1], reverse=True)
            
            # Get highest confidence trigger
            best_trigger = triggers[0]
            
            escalation_decision.update({
                'should_escalate': True,
                'reason': best_trigger[2],
                'priority': self._determine_priority(best_trigger[0], best_trigger[1]),
                'confidence': best_trigger[1],
                'trigger_type': best_trigger[0],
                'all_triggers': triggers
            })
        
        return escalation_decision
    
    def _is_explicit_escalation_request(self, message: str) -> bool:
        """Check if user explicitly requests human agent"""
        explicit_phrases = [
            'talk to a human', 'speak to a person', 'real person',
            'human agent', 'live agent', 'customer service representative',
            'connect me with someone', 'get me a person', 'agent please',
            'representative', 'support agent', 'customer support agent'
        ]
        
        message_lower = message.lower()
        return any(phrase in message_lower for phrase in explicit_phrases)
    
    def _detect_frustration(self, message: str, context: Dict) -> Dict[str, Any]:
        """Detect user frustration using multiple signals"""
        message_lower = message.lower()
        signals = []
        
        # Signal 1: Negative sentiment words
        negative_words = [
            'frustrated', 'angry', 'annoyed', 'upset', 'disappointed',
            'terrible', 'awful', 'horrible', 'ridiculous', 'useless',
            'stupid', 'idiotic', 'waste of time', 'not helpful',
            'fed up', 'had enough', 'give up', 'not working'
        ]
        
        negative_count = sum(1 for word in negative_words if word in message_lower)
        if negative_count > 0:
            signals.append(('negative_words', min(negative_count * 0.3, 1.0)))
        
        # Signal 2: Multiple exclamation marks/caps
        if message.count('!') >= 2:
            signals.append(('excessive_punctuation', 0.4))
        
        if len(message) > 10:
            caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
            if caps_ratio > 0.5:
                signals.append(('all_caps', 0.5))
        
        # Signal 3: Short, abrupt messages
        words = message.split()
        if len(words) <= 3 and any(word in message_lower for word in ['help', 'fix', 'problem', 'issue']):
            signals.append(('abrupt_message', 0.3))
        
        # Signal 4: Repetition in conversation history
        if context.get('history'):
            recent_messages = context['history'][-3:]  # Last 3 user messages
            if len(recent_messages) >= 2:
                # Check if same issue mentioned multiple times
                issue_keywords = ['not work', 'broken', 'error', 'problem', 'issue']
                issue_count = sum(
                    1 for msg in recent_messages 
                    if any(keyword in msg.lower() for keyword in issue_keywords)
                )
                if issue_count >= 2:
                    signals.append(('repeated_issue', 0.6))
        
        # Calculate overall frustration confidence
        if signals:
            confidence = sum(score for _, score in signals) / len(signals)
            return {
                'is_frustrated': True,
                'confidence': min(confidence, 1.0),
                'signals': signals,
                'reason': f"Detected {len(signals)} frustration signals"
            }
        
        return {'is_frustrated': False, 'confidence': 0.0, 'reason': ''}
    
    def _check_repeated_failures(self, user_id: str, context: Dict) -> Dict[str, Any]:
        """Track and detect repeated conversation failures"""
        # Initialize tracker for user
        if user_id not in self.conversation_failure_tracker:
            self.conversation_failure_tracker[user_id] = {
                'failures': 0,
                'last_failure_time': None,
                'failure_reasons': []
            }
        
        tracker = self.conversation_failure_tracker[user_id]
        
        # Check current message for failure indicators
        current_failure = self._is_current_message_failure(context)
        
        if current_failure['is_failure']:
            tracker['failures'] += 1
            tracker['last_failure_time'] = datetime.now()
            tracker['failure_reasons'].append(current_failure['reason'])
            
            # Clean old failures outside time window
            self._clean_old_failures(user_id)
            
            logger.info(f"📊 User {user_id} failures: {tracker['failures']}")
        
        # Check if we should escalate due to repeated failures
        if tracker['failures'] >= self.ESCALATION_CONFIG['max_consecutive_failures']:
            return {
                'should_escalate': True,
                'confidence': min(tracker['failures'] * 0.3, 1.0),
                'failures': tracker['failures'],
                'reasons': tracker['failure_reasons'][-3:]  # Last 3 reasons
            }
        
        return {'should_escalate': False, 'confidence': 0.0, 'failures': tracker['failures']}
    
    def _is_current_message_failure(self, context: Dict) -> Dict[str, Any]:
        """Check if current interaction indicates a failure"""
        # Failure indicators:
        # 1. User is correcting/restating after bot response
        # 2. User says "that's not what I asked"
        # 3. User repeats same question
        # 4. Low confidence from intent classifier
        
        message = context.get('current_message', '').lower()
        last_bot_response = context.get('last_bot_message', '').lower()
        
        failure_indicators = [
            ('correction', r'(no|not|wrong|that\'s not|incorrect|misunderstood)'),
            ('repetition', r'(i said|as i said|again|still)'),
            ('clarification', r'(what i mean is|let me rephrase|i meant)'),
            ('dissatisfaction', r'(not helpful|not answering|not what i asked)')
        ]
        
        for indicator_type, pattern in failure_indicators:
            if re.search(pattern, message):
                return {
                    'is_failure': True,
                    'reason': f"{indicator_type}: User correcting/clarifying",
                    'type': indicator_type
                }
        
        # Check if intent confidence was low
        if context.get('intent_confidence', 1.0) < 0.3:
            return {
                'is_failure': True,
                'reason': f"Low intent confidence: {context.get('intent_confidence')}",
                'type': 'low_confidence'
            }
        
        return {'is_failure': False, 'reason': ''}
    
    def _clean_old_failures(self, user_id: str):
        """Remove failures outside the time window"""
        if user_id not in self.conversation_failure_tracker:
            return
        
        tracker = self.conversation_failure_tracker[user_id]
        
        if tracker['last_failure_time']:
            time_window = timedelta(minutes=self.ESCALATION_CONFIG['time_window_minutes'])
            cutoff_time = datetime.now() - time_window
            
            # Reset if last failure is too old
            if tracker['last_failure_time'] < cutoff_time:
                tracker['failures'] = 0
                tracker['failure_reasons'] = []
                logger.info(f"🕐 Reset failures for user {user_id} (time window expired)")
    
    def _contains_sensitive_topic(self, message: str) -> Dict[str, Any]:
        """Check for sensitive/legal topics requiring human handling"""
        message_lower = message.lower()
        
        for keyword in self.ESCALATION_CONFIG['sensitive_keywords']:
            if keyword in message_lower:
                return {
                    'contains_sensitive': True,
                    'confidence': 0.9,
                    'topic': keyword,
                    'message': 'Sensitive topic detected'
                }
        
        return {'contains_sensitive': False, 'confidence': 0.0, 'topic': ''}
    
    def _is_complex_query(self, message: str, context: Dict) -> Dict[str, Any]:
        """Determine if query is too complex for chatbot"""
        # Complexity indicators
        message_lower = message.lower()
        
        # Check for multiple requirements in one message
        conjunction_count = sum(1 for conj in [' and ', ' also ', ' plus ', ' furthermore '] 
                              if conj in message_lower)
        
        # Check length and structure
        word_count = len(message.split())
        
        # Complex if: long message with multiple requirements
        if word_count > 25 and conjunction_count >= 2:
            return {
                'is_complex': True,
                'confidence': 0.7,
                'reason': f"Complex multi-part query ({word_count} words, {conjunction_count} conjunctions)"
            }
        
        # Check for advanced technical terms
        technical_terms = ['api integration', 'custom development', 'enterprise architecture',
                          'migration strategy', 'data migration', 'system integration',
                          'custom workflow', 'advanced configuration']
        
        if any(term in message_lower for term in technical_terms):
            return {
                'is_complex': True,
                'confidence': 0.8,
                'reason': "Advanced technical/architectural query"
            }
        
        return {'is_complex': False, 'confidence': 0.0, 'reason': ''}
    
    def _determine_priority(self, trigger_type: str, confidence: float) -> str:
        """Determine escalation priority"""
        if trigger_type in ['sensitive_topic', 'explicit_request']:
            return 'high'
        elif confidence > 0.8:
            return 'high'
        elif confidence > 0.5:
            return 'medium'
        else:
            return 'normal'
    
    def initiate_escalation(self, user_id: str, conversation_context: Dict, 
                          escalation_reason: str) -> Dict[str, Any]:
        """
        Initiate escalation to human agent.
        Returns escalation ticket information.
        """
        # Create escalation ticket
        ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
        
        escalation_ticket = {
            'ticket_id': ticket_id,
            'user_id': user_id,
            'timestamp': datetime.now().isoformat(),
            'reason': escalation_reason,
            'priority': 'high' if 'sensitive' in escalation_reason.lower() else 'medium',
            'status': 'pending',
            'assigned_agent': None,
            'estimated_wait_time': '5-10 minutes',
            'conversation_summary': self._generate_conversation_summary(conversation_context)
        }
        
        # Add to escalation queue
        self.escalation_queue.append(escalation_ticket)
        
        # Update user escalation history
        if user_id not in self.user_escalation_history:
            self.user_escalation_history[user_id] = []
        self.user_escalation_history[user_id].append(escalation_ticket)
        
        # Log escalation
        logger.info(f"🚨 Escalation initiated: {ticket_id} for user {user_id}")
        logger.info(f"   Reason: {escalation_reason}")
        
        return escalation_ticket
    
    def _generate_conversation_summary(self, context: Dict) -> str:
        """Generate summary of conversation for human agent"""
        summary_parts = []
        
        # Add user info if available
        if context.get('user_id'):
            summary_parts.append(f"User: {context['user_id']}")
        
        # Add last few messages
        if context.get('history'):
            recent_history = context['history'][-5:]  # Last 5 exchanges
            summary_parts.append("\nRecent conversation:")
            for exchange in recent_history:
                user_msg = self.security.mask_pii(exchange.get('user', ''))[:100]
                bot_msg = self.security.mask_pii(exchange.get('bot', ''))[:100]
                summary_parts.append(f"  User: {user_msg}")
                summary_parts.append(f"  Bot: {bot_msg}")
        
        # Add detected issues
        if context.get('failure_reasons'):
            summary_parts.append("\nDetected issues:")
            for reason in context.get('failure_reasons', [])[-3:]:
                summary_parts.append(f"  - {reason}")
        
        return "\n".join(summary_parts)
    
    def get_escalation_message(self, ticket_id: str = None) -> str:
        """Get user-friendly escalation message"""
        if ticket_id:
            return f"""🚨 **Transferring to Human Agent**

I'm connecting you with one of our customer support specialists who can better assist you.

**Your Support Ticket:** `{ticket_id}`
**Estimated Wait Time:** 5-10 minutes

Please hold while I transfer you. A specialist will be with you shortly.

💡 *Tip: Have your account information ready for faster service.*"""
        else:
            return """🚨 **Transferring to Human Agent**

I'm connecting you with one of our customer support specialists who can better assist you.

**Estimated Wait Time:** 5-10 minutes

Please hold while I transfer you. A specialist will be with you shortly.

💡 *Tip: Have your account information ready for faster service.*"""
    
    def get_escalation_queue(self) -> List[Dict]:
        """Get current escalation queue (for admin/monitoring)"""
        return self.escalation_queue
    
    def get_user_escalation_history(self, user_id: str) -> List[Dict]:
        """Get escalation history for a user"""
        return self.user_escalation_history.get(user_id, [])
    
    def clear_resolved_tickets(self):
        """Clear resolved tickets from queue"""
        unresolved = [ticket for ticket in self.escalation_queue 
                     if ticket.get('status') != 'resolved']
        removed_count = len(self.escalation_queue) - len(unresolved)
        self.escalation_queue = unresolved
        
        if removed_count > 0:
            logger.info(f"🗑️  Cleared {removed_count} resolved escalation tickets")
    
    def reset_user_tracker(self, user_id: str):
        """Reset failure tracker for user (after successful interaction)"""
        if user_id in self.conversation_failure_tracker:
            self.conversation_failure_tracker[user_id] = {
                'failures': 0,
                'last_failure_time': None,
                'failure_reasons': []
            }
            logger.info(f"🔄 Reset failure tracker for user {user_id}")