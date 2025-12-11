"""
Conversation analytics and tracking module.
Tracks conversation metrics, user behavior, and chatbot performance.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger


class ConversationAnalytics:
    """Tracks and analyzes conversation metrics"""
    
    def __init__(self):
        self.conversations: List[Dict] = []
        self.metrics = {
            'total_conversations': 0,
            'total_messages': 0,
            'average_response_time_ms': 0,
            'escalation_rate': 0.0,
            'intent_distribution': defaultdict(int),
            'user_satisfaction_scores': [],
            'active_users': set(),
            'hourly_activity': defaultdict(int)
        }
        
        # Store conversations by user for faster lookups
        self.conversations_by_user: Dict[str, List[Dict]] = defaultdict(list)
        
        logger.info("📊 Conversation analytics initialized")
    
    def track_conversation(self, conversation_data: Dict[str, Any]):
        """Track a single conversation exchange"""
        try:
            # Add timestamp if not present
            if 'timestamp' not in conversation_data:
                conversation_data['timestamp'] = datetime.now().isoformat()
            
            # Add unique ID
            if 'conversation_id' not in conversation_data:
                conversation_data['conversation_id'] = f"conv_{len(self.conversations) + 1}"
            
            # Store conversation
            self.conversations.append(conversation_data)
            
            # Update user-specific tracking
            user_id = conversation_data.get('user_id')
            if user_id:
                self.conversations_by_user[user_id].append(conversation_data)
                self.metrics['active_users'].add(user_id)
            
            # Update metrics
            self._update_metrics(conversation_data)
            
            logger.debug(f"📝 Tracked conversation for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error tracking conversation: {e}")
    
    def _update_metrics(self, conversation_data: Dict[str, Any]):
        """Update analytics metrics with new conversation data"""
        # Increment counters
        self.metrics['total_conversations'] += 1
        self.metrics['total_messages'] += 1
        
        # Track intent distribution
        intent = conversation_data.get('intent', 'unknown')
        self.metrics['intent_distribution'][intent] += 1
        
        # Track hourly activity
        timestamp = conversation_data.get('timestamp')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                hour_key = f"{dt.hour:02d}:00"
                self.metrics['hourly_activity'][hour_key] += 1
            except:
                pass
        
        # Update average response time
        response_time = conversation_data.get('response_time')
        if response_time:
            current_avg = self.metrics['average_response_time_ms']
            count = self.metrics['total_conversations']
            self.metrics['average_response_time_ms'] = (
                (current_avg * (count - 1) + response_time) / count
            )
        
        # Update escalation rate
        needs_escalation = conversation_data.get('needs_escalation', False)
        if needs_escalation:
            total_conv = self.metrics['total_conversations']
            escalations = sum(1 for conv in self.conversations if conv.get('needs_escalation'))
            self.metrics['escalation_rate'] = (escalations / total_conv) * 100 if total_conv > 0 else 0
    
    def get_conversation_insights(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get insights for specific user or all users"""
        if user_id and user_id in self.conversations_by_user:
            user_conversations = self.conversations_by_user[user_id]
            return self._analyze_user_conversations(user_id, user_conversations)
        else:
            return self._analyze_all_conversations()
    
    def _analyze_user_conversations(self, user_id: str, conversations: List[Dict]) -> Dict[str, Any]:
        """Analyze conversations for a specific user"""
        if not conversations:
            return {
                'user_id': user_id,
                'message': 'No conversations found',
                'total_conversations': 0
            }
        
        # Calculate user-specific metrics
        total_conversations = len(conversations)
        recent_conversations = conversations[-10:]  # Last 10 conversations
        
        # Intent analysis
        intents = [conv.get('intent', 'unknown') for conv in recent_conversations]
        most_common_intent = max(set(intents), key=intents.count) if intents else 'unknown'
        
        # Response time analysis
        response_times = [conv.get('response_time', 0) for conv in recent_conversations if conv.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Escalation analysis
        escalations = [conv for conv in recent_conversations if conv.get('needs_escalation')]
        
        return {
            'user_id': user_id,
            'total_conversations': total_conversations,
            'recent_conversations_count': len(recent_conversations),
            'most_common_intent': most_common_intent,
            'intent_distribution': {intent: intents.count(intent) for intent in set(intents)},
            'average_response_time_ms': round(avg_response_time, 2),
            'escalation_count': len(escalations),
            'escalation_rate': (len(escalations) / len(recent_conversations)) * 100 if recent_conversations else 0,
            'recent_escalations': [
                {
                    'timestamp': esc.get('timestamp'),
                    'reason': esc.get('escalation_reason', 'Unknown'),
                    'ticket_id': esc.get('escalation_ticket_id')
                }
                for esc in escalations[-5:]  # Last 5 escalations
            ],
            'last_interaction': conversations[-1].get('timestamp') if conversations else None,
            'conversation_frequency': self._calculate_conversation_frequency(conversations)
        }
    
    def _analyze_all_conversations(self) -> Dict[str, Any]:
        """Analyze all conversations"""
        if not self.conversations:
            return {
                'message': 'No conversations tracked yet',
                'total_conversations': 0
            }
        
        recent_conversations = self.conversations[-50:]  # Last 50 conversations
        
        # Calculate overall metrics
        total_users = len(self.metrics['active_users'])
        
        # Response time analysis
        response_times = [conv.get('response_time', 0) for conv in recent_conversations if conv.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Intent analysis
        intents = [conv.get('intent', 'unknown') for conv in recent_conversations]
        intent_distribution = {intent: intents.count(intent) for intent in set(intents)}
        
        # Escalation analysis
        escalations = [conv for conv in recent_conversations if conv.get('needs_escalation')]
        
        # User engagement
        active_today = self._get_active_users_today()
        
        return {
            'total_conversations': self.metrics['total_conversations'],
            'total_users': total_users,
            'active_users_today': len(active_today),
            'average_response_time_ms': round(avg_response_time, 2),
            'escalation_rate': self.metrics['escalation_rate'],
            'intent_distribution': intent_distribution,
            'hourly_activity': dict(self.metrics['hourly_activity']),
            'recent_escalations': [
                {
                    'user_id': esc.get('user_id'),
                    'timestamp': esc.get('timestamp'),
                    'reason': esc.get('escalation_reason', 'Unknown'),
                    'ticket_id': esc.get('escalation_ticket_id')
                }
                for esc in escalations[-10:]  # Last 10 escalations
            ],
            'top_intents': sorted(intent_distribution.items(), key=lambda x: x[1], reverse=True)[:5],
            'peak_hours': sorted(self.metrics['hourly_activity'].items(), key=lambda x: x[1], reverse=True)[:3]
        }
    
    def _calculate_conversation_frequency(self, conversations: List[Dict]) -> Dict[str, Any]:
        """Calculate conversation frequency for a user"""
        if len(conversations) < 2:
            return {'average_gap_minutes': 0, 'frequency': 'low'}
        
        # Calculate time gaps between conversations
        timestamps = []
        for conv in conversations:
            try:
                ts = datetime.fromisoformat(conv.get('timestamp', '').replace('Z', '+00:00'))
                timestamps.append(ts)
            except:
                pass
        
        if len(timestamps) < 2:
            return {'average_gap_minutes': 0, 'frequency': 'low'}
        
        # Sort and calculate gaps
        timestamps.sort()
        gaps = []
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i-1]).total_seconds() / 60
            gaps.append(gap)
        
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        
        # Determine frequency level
        if avg_gap < 5:
            frequency = 'very_high'
        elif avg_gap < 15:
            frequency = 'high'
        elif avg_gap < 60:
            frequency = 'medium'
        elif avg_gap < 240:
            frequency = 'low'
        else:
            frequency = 'very_low'
        
        return {
            'average_gap_minutes': round(avg_gap, 2),
            'frequency': frequency,
            'conversations_per_day': len(conversations) / max((timestamps[-1] - timestamps[0]).days, 1)
        }
    
    def _get_active_users_today(self) -> List[str]:
        """Get users active in the last 24 hours"""
        active_users = set()
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for conv in self.conversations[-100:]:  # Check recent 100 conversations
            timestamp = conv.get('timestamp')
            user_id = conv.get('user_id')
            
            if timestamp and user_id:
                try:
                    conv_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if conv_time > cutoff_time:
                        active_users.add(user_id)
                except:
                    continue
        
        return list(active_users)
    
    def get_daily_report(self) -> Dict[str, Any]:
        """Generate daily report"""
        today = datetime.now().strftime('%Y-%m-%d')
        today_conversations = [
            conv for conv in self.conversations
            if conv.get('timestamp', '').startswith(today)
        ]
        
        if not today_conversations:
            return {
                'date': today,
                'message': 'No conversations today',
                'total_conversations': 0
            }
        
        # Calculate today's metrics
        today_users = set(conv.get('user_id') for conv in today_conversations if conv.get('user_id'))
        
        # Intent distribution for today
        today_intents = [conv.get('intent', 'unknown') for conv in today_conversations]
        intent_distribution = {intent: today_intents.count(intent) for intent in set(today_intents)}
        
        # Escalations today
        today_escalations = [conv for conv in today_conversations if conv.get('needs_escalation')]
        
        # Response times today
        response_times = [conv.get('response_time', 0) for conv in today_conversations if conv.get('response_time')]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Hourly breakdown for today
        hourly_breakdown = defaultdict(int)
        for conv in today_conversations:
            timestamp = conv.get('timestamp')
            if timestamp:
                try:
                    hour = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).hour
                    hourly_breakdown[f"{hour:02d}:00"] += 1
                except:
                    pass
        
        return {
            'date': today,
            'total_conversations': len(today_conversations),
            'unique_users': len(today_users),
            'average_response_time_ms': round(avg_response_time, 2),
            'escalation_count': len(today_escalations),
            'escalation_rate': (len(today_escalations) / len(today_conversations)) * 100 if today_conversations else 0,
            'intent_distribution': intent_distribution,
            'hourly_breakdown': dict(hourly_breakdown),
            'top_intents_today': sorted(intent_distribution.items(), key=lambda x: x[1], reverse=True)[:3],
            'peak_hour_today': max(hourly_breakdown.items(), key=lambda x: x[1]) if hourly_breakdown else ('00:00', 0),
            'busiest_hour': max(hourly_breakdown.items(), key=lambda x: x[1]) if hourly_breakdown else ('00:00', 0)
        }
    
    def get_earliest_conversation_date(self) -> Optional[str]:
        """Get date of earliest conversation"""
        if not self.conversations:
            return None
        
        earliest = min(
            conv.get('timestamp') for conv in self.conversations 
            if conv.get('timestamp')
        )
        return earliest
    
    def clear_old_conversations(self, days_to_keep: int = 30):
        """Clear conversations older than specified days"""
        if not self.conversations:
            return
        
        cutoff_time = datetime.now() - timedelta(days=days_to_keep)
        initial_count = len(self.conversations)
        
        # Filter conversations
        self.conversations = [
            conv for conv in self.conversations
            if self._is_conversation_recent(conv, cutoff_time)
        ]
        
        removed = initial_count - len(self.conversations)
        if removed > 0:
            logger.info(f"🗑️  Cleared {removed} old conversations (older than {days_to_keep} days)")
            
            # Rebuild user index
            self.conversations_by_user.clear()
            for conv in self.conversations:
                user_id = conv.get('user_id')
                if user_id:
                    self.conversations_by_user[user_id].append(conv)
    
    def _is_conversation_recent(self, conversation: Dict, cutoff_time: datetime) -> bool:
        """Check if conversation is recent"""
        timestamp = conversation.get('timestamp')
        if not timestamp:
            return False
        
        try:
            conv_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return conv_time > cutoff_time
        except:
            return False
    
    def export_conversations(self, format: str = 'json') -> Any:
        """Export conversations in specified format"""
        if format == 'json':
            return self.conversations
        elif format == 'csv':
            # Simple CSV export (in real implementation, use csv module)
            headers = ['timestamp', 'user_id', 'intent', 'response_time_ms', 'needs_escalation']
            csv_lines = [','.join(headers)]
            
            for conv in self.conversations:
                row = [
                    conv.get('timestamp', ''),
                    conv.get('user_id', ''),
                    conv.get('intent', ''),
                    str(conv.get('response_time', '')),
                    str(conv.get('needs_escalation', False))
                ]
                csv_lines.append(','.join(row))
            
            return '\n'.join(csv_lines)
        else:
            raise ValueError(f"Unsupported format: {format}")