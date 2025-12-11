import re
import string
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.sentiment import SentimentIntensityAnalyzer
from loguru import logger

class NLPProcessor:
    """Enhanced NLP processor with improved entity extraction and context handling"""
    
    def __init__(self):
        self._ensure_nltk_data()
        
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
        # Enhanced patterns with better regex
        self.patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
            'date': self._compile_date_patterns(),
            'time': self._compile_time_patterns()
        }
        
        # Service type keywords
        self.service_keywords = {
            'consultation': ['consultation', 'consult', 'consulting', 'advice', 'guidance', 'discuss'],
            'support': ['support', 'help', 'assistance', 'issue', 'problem', 'fix', 'troubleshoot'],
            'installation': ['install', 'installation', 'setup', 'set up', 'configure', 'implement'],
            'maintenance': ['maintenance', 'maintain', 'service', 'checkup', 'inspection', 'update'],
            'training': ['training', 'train', 'learn', 'educate', 'workshop', 'course', 'teach']
        }
    
    def _ensure_nltk_data(self):
        """Ensure all required NLTK data is downloaded"""
        required_data = [
            ('tokenizers/punkt', 'punkt'),
            ('corpora/wordnet', 'wordnet'),
            ('corpora/stopwords', 'stopwords'),
            ('sentiment/vader_lexicon', 'vader_lexicon')
        ]
        
        for path, name in required_data:
            try:
                nltk.data.find(path)
            except LookupError:
                nltk.download(name, quiet=True)
    
    def _compile_date_patterns(self) -> List[str]:
        """Compile comprehensive date patterns"""
        return [
            # Explicit dates: 12/15, 12-15-2024, Dec 15
            r'\b\d{1,2}[-/]\d{1,2}(?:[-/]\d{2,4})?\b',
            # Month names: December 15, Dec 15th
            r'\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*(?:\d{4})?\b',
            # Weekdays: Monday, next Tuesday
            r'\b(?:next\s+|this\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',
            # Relative: today, tomorrow
            r'\b(?:today|tomorrow|next\s+week)\b'
        ]
    
    def _compile_time_patterns(self) -> List[str]:
        """Compile comprehensive time patterns"""
        return [
            # Standard: 3:30 PM, 15:30
            r'\b\d{1,2}[:.]\d{2}\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)?\b',
            # Simple: 3 PM, 3pm
            r'\b\d{1,2}\s*(?:AM|PM|am|pm|a\.m\.|p\.m\.)\b',
            # Descriptive: morning, afternoon, evening
            r'\b(?:morning|afternoon|evening|noon|midnight)\b'
        ]
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text for ML"""
        text = text.lower().strip()
        text = re.sub(r'[^\w\s]', ' ', text)
        tokens = word_tokenize(text)
        tokens = [
            self.lemmatizer.lemmatize(token) 
            for token in tokens 
            if token not in self.stop_words and token not in string.punctuation
        ]
        return ' '.join(tokens)
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract all entities from text with improved accuracy"""
        entities = {}
        
        # Extract emails
        emails = re.findall(self.patterns['email'], text, re.IGNORECASE)
        if emails:
            entities['email'] = list(set(emails))
        
        # Extract phone numbers
        phones = re.findall(self.patterns['phone'], text)
        if phones:
            entities['phone'] = list(set(phones))
        
        # Extract dates
        dates = self._extract_dates(text)
        if dates:
            entities['date'] = dates
        
        # Extract times
        times = self._extract_times(text)
        if times:
            entities['time'] = times
        
        # Extract service types
        services = self._extract_service_types(text)
        if services:
            entities['service_type'] = services
        
        # Extract names (capitalized words that might be names)
        names = self._extract_names(text)
        if names:
            entities['name'] = names
        
        return entities
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract and normalize dates"""
        dates = []
        text_lower = text.lower()
        
        # Check each date pattern
        for pattern in self.patterns['date']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_dates = []
        for date in dates:
            if date.lower() not in seen:
                seen.add(date.lower())
                unique_dates.append(date)
        
        return unique_dates
    
    def _extract_times(self, text: str) -> List[str]:
        """Extract and normalize times"""
        times = []
        
        for pattern in self.patterns['time']:
            matches = re.findall(pattern, text, re.IGNORECASE)
            times.extend(matches)
        
        # Remove duplicates
        return list(set(times))
    
    def _extract_service_types(self, text: str) -> List[str]:
        """Extract service types with fuzzy matching"""
        detected_services = []
        text_lower = text.lower()
        
        for service, keywords in self.service_keywords.items():
            for keyword in keywords:
                # Use word boundaries to avoid partial matches
                pattern = r'\b' + re.escape(keyword) + r's?\b'
                if re.search(pattern, text_lower):
                    detected_services.append(service)
                    break  # Found one keyword for this service
        
        return list(set(detected_services))
    
    def _extract_names(self, text: str) -> List[str]:
        """Extract potential names from text"""
        # Look for capitalized words (potential names)
        # Format: "FirstName LastName" or after "my name is"
        names = []
        
        # Pattern 1: "my name is X" or "I am X"
        name_intro_pattern = r'(?:my name is|i am|i\'m|call me|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        matches = re.findall(name_intro_pattern, text, re.IGNORECASE)
        names.extend(matches)
        
        # Pattern 2: Capitalized words that look like names (2-4 words)
        capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
        matches = re.findall(capitalized_pattern, text)
        
        # Filter out common words that might be capitalized
        common_caps = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 
                       'Saturday', 'Sunday', 'January', 'February', 'March', 
                       'April', 'May', 'June', 'July', 'August', 'September',
                       'October', 'November', 'December'}
        
        for match in matches:
            if match not in common_caps and len(match.split()) <= 4:
                names.append(match)
        
        return list(set(names))
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Analyze sentiment with VADER"""
        scores = self.sentiment_analyzer.polarity_scores(text)
        return scores
    
    def is_frustrated(self, text: str, history: Optional[List[str]] = None) -> bool:
        """Detect user frustration with multiple signals"""
        sentiment = self.analyze_sentiment(text)
        text_lower = text.lower()
        
        # Signal 1: Very negative sentiment
        if sentiment['compound'] < -0.5:
            return True
        
        # Signal 2: Frustration keywords
        frustration_keywords = [
            'angry', 'frustrated', 'annoyed', 'upset', 'disappointed',
            'terrible', 'awful', 'horrible', 'worst', 'useless', 'stupid',
            'not working', 'broken', 'again', 'still', 'waste',
            'never works', 'give up', 'forget it', 'ridiculous'
        ]
        
        if any(keyword in text_lower for keyword in frustration_keywords):
            return True
        
        # Signal 3: Multiple exclamation marks or excessive caps
        if text.count('!') >= 2:
            return True
        
        if len(text) > 10:
            caps_ratio = sum(1 for c in text if c.isupper()) / len(text)
            if caps_ratio > 0.5:
                return True
        
        # Signal 4: Repeated issues in conversation history
        if history and len(history) >= 3:
            issue_keywords = ['problem', 'issue', 'error', 'not work', "doesn't work"]
            recent_issues = sum(
                1 for msg in history[-3:] 
                if any(keyword in msg.lower() for keyword in issue_keywords)
            )
            if recent_issues >= 2:
                return True
        
        return False
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into words"""
        return word_tokenize(text)
    
    def get_word_frequencies(self, text: str) -> Dict[str, int]:
        """Calculate word frequencies"""
        tokens = self.tokenize(text)
        tokens = [t.lower() for t in tokens if t.isalpha()]
        
        frequencies = {}
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        
        return frequencies
    
    def extract_intent_from_context(self, text: str, previous_question: Optional[str] = None) -> Dict:
        """Extract intent considering conversational context"""
        text_lower = text.lower().strip()
        
        # Detect acknowledgments
        acknowledgments = ['yes', 'yeah', 'yep', 'sure', 'ok', 'okay', 'fine', 'alright', 'correct']
        is_acknowledgment = text_lower in acknowledgments or any(ack in text_lower.split() for ack in acknowledgments)
        
        # Detect questions
        is_question = '?' in text or any(
            text_lower.startswith(q) 
            for q in ['what', 'when', 'where', 'who', 'why', 'how', 'can', 'could', 
                     'would', 'is', 'are', 'do', 'does', 'should']
        )
        
        # Detect negations
        negations = ['no', 'nope', 'not', 'never', "don't", "won't", "can't", "shouldn't"]
        is_negative = any(neg in text_lower.split() for neg in negations)
        
        return {
            'is_acknowledgment': is_acknowledgment,
            'is_question': is_question,
            'is_negative': is_negative,
            'text_length': len(text.split()),
            'has_specific_info': self._has_specific_information(text),
            'previous_question': previous_question
        }
    
    def _has_specific_information(self, text: str) -> bool:
        """Check if text contains specific information"""
        # Check for dates, times, emails, phone numbers
        for pattern_list in [self.patterns['date'], self.patterns['time']]:
            if isinstance(pattern_list, list):
                for pattern in pattern_list:
                    if re.search(pattern, text, re.IGNORECASE):
                        return True
            elif re.search(pattern_list, text, re.IGNORECASE):
                return True
        
        # Check for numbers
        if re.search(r'\d+', text):
            return True
        
        return False