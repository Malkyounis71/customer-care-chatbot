import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import re
from loguru import logger
from app.chatbot.nlp_processor import NLPProcessor

class IntentClassifier:
    """Enhanced intent classifier with better pattern matching and context awareness"""
    
    def __init__(self):
        self.nlp = NLPProcessor()
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=1000,
                ngram_range=(1, 3),  # Increased to capture more context
                stop_words='english',
                min_df=1
            )),
            ('classifier', RandomForestClassifier(
                n_estimators=150,
                max_depth=20,
                random_state=42
            ))
        ])
        
        self.training_data = self._get_training_data()
        self._train_model()
        
        # Context-aware pattern matching
        self.intent_patterns = self._init_patterns()
    
    def _init_patterns(self) -> Dict[str, List[str]]:
        """Initialize comprehensive intent patterns"""
        return {
            'appointment': [
                r'\b(schedule|book|make|set up|arrange|reserve)\s+(an?\s+)?(appointment|meeting|call|demo|consultation|session)\b',
                r'\bi\s+(want|need|would like)\s+to\s+(schedule|book|set up)\b',
                r'\bcan\s+(i|we)\s+(schedule|book|arrange)\b',
                r'\bappointment\s+(for|on|at)\b',
                r'\b(demo|consultation)\s+(at|on|for)\b'
            ],
            'support': [
                r'\b(technical\s+)?(support|help|assistance|issue|problem)\b',
                r'\bneed\s+(help|support|assistance)\s+with\b',
                r'\b(not\s+working|broken|error|fix|troubleshoot)\b',
                r'\bhave\s+(a|an)\s+(problem|issue)\b',
                r'\bcan\s+you\s+(help|assist|support)\b'
            ],
            'product_inquiry': [
                r'\b(what|tell|show|explain)\s+(me\s+)?(about\s+)?your\s+(product|service|feature|solution)',
                r'\bproduct\s+(information|details|features|catalog)\b',
                r'\b(pricing|price|cost|plan)\s+(for|of|about)\b',
                r'\bwant\s+to\s+(know|learn)\s+(more\s+)?about\s+(product|service)',
                r'\bcompare\s+(product|service|plan|feature)'
            ],
            'pricing': [
                r'\b(how\s+much|what.*cost|price|pricing|plan.*price)\b',
                r'\b(enterprise|custom|unlimited)\s+(pricing|plan|cost)\b',
                r'\bget\s+(pricing|quote|estimate)\b'
            ],
            'escalation': [
                r'\b(human|real\s+person|live\s+agent|manager|supervisor)\b',
                r'\b(talk|speak|connect)\s+to\s+(human|person|agent)\b',
                r'\btransfer\s+(me\s+)?to\b',
                r'\b(not\s+helping|useless|frustrated)\b'
            ],
            'greeting': [
                r'^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings)[\s!?.]*$'
            ],
            'goodbye': [
                r'^(bye|goodbye|see\s+you|thanks|thank\s+you|that\'s\s+all)[\s!?.]*$',
                r'\bno\s+(more\s+)?(question|help)\b',
                r'\bi\'m\s+(done|finished|all\s+set)\b'
            ]
        }
    
    def _get_training_data(self) -> Tuple[List[str], List[str]]:
        """Comprehensive training data with balanced examples"""
        texts = []
        labels = []
        
        # Knowledge base queries (general information)
        kb_examples = [
            "what are your business hours", "how can i contact support",
            "what products do you offer", "tell me about your return policy",
            "what services do you provide", "explain your platform",
            "information about your solutions", "describe your offerings",
            "what can you tell me about your services", "show me your features",
            "i have a question about your products", "details about analytics",
            "tell me about enterprise suite", "cloud services information",
            "what is crm", "explain your features", "product catalog"
        ]
        texts.extend(kb_examples)
        labels.extend(['knowledge_base'] * len(kb_examples))
        
        # Support requests
        support_examples = [
            "i need technical support", "i need help with a problem",
            "something is not working", "can you help me fix this",
            "i have an issue", "technical assistance needed",
            "my product is broken", "troubleshooting help",
            "error message", "system not working", "need customer support",
            "help with my account", "fix this problem", "assistance required"
        ]
        texts.extend(support_examples)
        labels.extend(['knowledge_base'] * len(support_examples))
        
        # Appointment requests
        appointment_examples = [
            "i want to book an appointment", "schedule a meeting",
            "book a consultation", "set up a call", "arrange a demo",
            "i need to schedule service", "make an appointment",
            "reserve a time slot", "can i schedule an appointment",
            "i want to set up a meeting", "book me for a session",
            "schedule a demo for tuesday", "appointment at 3pm",
            "demo on friday afternoon"
        ]
        texts.extend(appointment_examples)
        labels.extend(['action'] * len(appointment_examples))
        
        # Escalation requests
        escalation_examples = [
            "i want to talk to a human", "connect me with an agent",
            "let me speak to a manager", "transfer to a person",
            "i need a real person", "this is not helping",
            "get me a human", "speak with support agent",
            "connect to live agent", "talk to supervisor"
        ]
        texts.extend(escalation_examples)
        labels.extend(['escalation'] * len(escalation_examples))
        
        # Greetings
        greeting_examples = [
            "hello", "hi", "hey", "good morning",
            "good afternoon", "good evening", "greetings", "hi there"
        ]
        texts.extend(greeting_examples)
        labels.extend(['greeting'] * len(greeting_examples))
        
        # Goodbyes
        goodbye_examples = [
            "goodbye", "bye", "see you", "thanks",
            "thank you", "that's all", "no more questions",
            "i'm done", "all set", "nothing else"
        ]
        texts.extend(goodbye_examples)
        labels.extend(['goodbye'] * len(goodbye_examples))
        
        # Menu selections (numbers)
        menu_examples = ["1", "2", "3", "4", "5", "option 1", "option 2"]
        texts.extend(menu_examples)
        labels.extend(['menu_selection'] * len(menu_examples))
        
        return texts, labels
    
    def _train_model(self):
        """Train the classification model"""
        try:
            texts, labels = self.training_data
            processed_texts = [self.nlp.preprocess_text(text) for text in texts]
            self.pipeline.fit(processed_texts, labels)
            logger.info(f"✅ Intent classifier trained with {len(texts)} examples")
        except Exception as e:
            logger.error(f"❌ Training error: {e}")
    
    def classify(self, text: str, context: Optional[Dict] = None) -> Tuple[str, float]:
        """
        Classify intent with context awareness
        
        Args:
            text: User input text
            context: Optional context including last_bot_message, history, etc.
        """
        try:
            text_lower = text.lower().strip()
            
            # PRIORITY 1: Check if this is a menu selection response
            if context and context.get('last_bot_message'):
                intent = self._check_menu_context(text_lower, context['last_bot_message'])
                if intent:
                    logger.info(f"🎯 Context-based classification: {intent}")
                    return intent, 0.95
            
            # PRIORITY 2: Single number without context (treat as menu)
            if re.match(r'^[1-5]$', text_lower):
                return 'menu_selection', 0.85
            
            # PRIORITY 3: Rule-based pattern matching
            for intent_name, patterns in self.intent_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, text_lower, re.IGNORECASE):
                        logger.info(f"🎯 Pattern match: '{intent_name}' from pattern")
                        confidence = 0.90
                        
                        # Map to correct intent category
                        if intent_name == 'appointment':
                            return 'action', confidence
                        elif intent_name in ['support', 'product_inquiry', 'pricing']:
                            return 'knowledge_base', confidence
                        else:
                            return intent_name, confidence
            
            # PRIORITY 4: Machine learning classification
            if hasattr(self.pipeline, 'classes_'):
                processed_text = self.nlp.preprocess_text(text)
                intent = self.pipeline.predict([processed_text])[0]
                probabilities = self.pipeline.predict_proba([processed_text])[0]
                confidence = max(probabilities)
                
                # Override low confidence ML predictions
                if confidence < 0.6:
                    logger.info(f"⚠️ Low ML confidence ({confidence:.2f}), defaulting to knowledge_base")
                    return 'knowledge_base', 0.6
                
                logger.info(f"🤖 ML classification: '{intent}' (confidence: {confidence:.2f})")
                return intent, confidence
            
            # FALLBACK: Default to knowledge_base
            return 'knowledge_base', 0.5
            
        except Exception as e:
            logger.error(f"❌ Classification error: {e}")
            return 'knowledge_base', 0.5
    
    def _check_menu_context(self, text: str, last_bot_message: str) -> Optional[str]:
        """Check if user is responding to a menu"""
        last_msg_lower = last_bot_message.lower()
        
        # Check for menu indicators
        menu_indicators = [
            'reply with', 'please reply', 'would you like',
            'option 1', 'option 2', 'option 3', 'option 4',
            '1.', '2.', '3.', '4.',
            'select', 'choose', 'pick'
        ]
        
        has_menu = any(indicator in last_msg_lower for indicator in menu_indicators)
        
        if has_menu and text in ['1', '2', '3', '4', '5']:
            return 'menu_selection'
        
        # Check for confirmation questions
        confirmation_phrases = [
            'is this correct', 'confirm', 'please confirm',
            'reply yes', 'reply no', 'yes or no'
        ]
        
        has_confirmation = any(phrase in last_msg_lower for phrase in confirmation_phrases)
        
        if has_confirmation and text in ['yes', 'no', 'yeah', 'yep', 'nope']:
            return 'confirmation'
        
        return None
    
    def get_intent_details(self, text: str, context: Optional[Dict] = None) -> Dict:
        """Get detailed intent analysis with context"""
        intent, confidence = self.classify(text, context)
        
        # Extract entities
        entities = self.nlp.extract_entities(text)
        
        # Enhanced entity extraction for specific intents
        if intent == 'knowledge_base':
            entities = self._extract_knowledge_entities(text, entities)
        
        # Analyze sentiment and frustration
        sentiment = self.nlp.analyze_sentiment(text)
        is_frustrated = self.nlp.is_frustrated(text)
        
        return {
            'intent': intent,
            'confidence': confidence,
            'sentiment': sentiment,
            'entities': entities,
            'is_frustrated': is_frustrated,
            'processed_text': self.nlp.preprocess_text(text)
        }
    
    def _extract_knowledge_entities(self, text: str, entities: Dict) -> Dict:
        """Extract product/feature entities from knowledge queries"""
        text_lower = text.lower()
        
        feature_keywords = {
            'crm': ['crm', 'customer relationship', 'customer management'],
            'analytics': ['analytics', 'analysis', 'dashboard', 'reporting'],
            'financial': ['financial', 'accounting', 'billing', 'invoice'],
            'support': ['support', 'help desk', 'customer service'],
            'cloud': ['cloud', 'hosting', 'server', 'storage'],
            'mobile': ['mobile', 'app', 'ios', 'android'],
            'enterprise': ['enterprise', 'custom pricing', 'unlimited']
        }
        
        if 'entities' not in entities:
            entities['entities'] = {}
        
        for entity_type, keywords in feature_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                if entity_type not in entities['entities']:
                    entities['entities'][entity_type] = []
                entities['entities'][entity_type].append(keywords[0])
        
        return entities
    
    def save_model(self, path: str):
        """Save trained model"""
        with open(path, 'wb') as f:
            pickle.dump(self.pipeline, f)
        logger.info(f"✅ Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model"""
        with open(path, 'rb') as f:
            self.pipeline = pickle.load(f)
        logger.info(f"✅ Model loaded from {path}")