"""
Test suite for Intent Classifier
"""
import sys
import os
import pytest


sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))


from app.chatbot.intent_classifier import IntentClassifier

@pytest.fixture
def classifier():
    """Create a fresh classifier instance for each test"""
    return IntentClassifier()

def extract_intent(result):
    """Extract intent name from result (handles both string and tuple returns)"""
    if isinstance(result, tuple) and len(result) >= 1:
        return result[0]  # Return first element of tuple
    return result  

class TestIntentClassifier:
    """Test cases for IntentClassifier"""
    
    def test_classify_appointment(self, classifier):
        """Test appointment intent classification"""
        # Common phrases for appointment scheduling
        test_cases = [
            ("I want to schedule an appointment", ["appointment", "action"]),
            ("Book a meeting", ["appointment", "action"]),
            ("Schedule a demo", ["appointment", "action"]),
            ("I need to make an appointment", ["appointment", "action"]),
            ("Can we set up a consultation?", ["appointment", "action"]),
            ("I'd like to book a session", ["appointment", "action"]),
        ]
        
        for text, expected_intents in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            assert intent_name in expected_intents, \
                f"Text: '{text}' | Expected one of: {expected_intents} | Got: '{intent_name}'"
    
    def test_classify_knowledge_base(self, classifier):
        """Test knowledge base query classification"""
        test_cases = [
            ("What are your business hours?", "knowledge_base"),
            ("Tell me about your products", "knowledge_base"),
            ("How do I reset my password?", "knowledge_base"),
            ("What is your refund policy?", "knowledge_base"),
            ("Where is your office located?", "knowledge_base"),
            ("Can you explain your pricing?", "knowledge_base"),
        ]
        
        for text, expected_intent in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            assert intent_name == expected_intent, \
                f"Text: '{text}' | Expected: '{expected_intent}' | Got: '{intent_name}'"
    
    def test_classify_escalation(self, classifier):
        """Test human agent escalation classification"""
        
        
        test_cases = [
            ("I want to speak to a human", "escalation"),
            ("Connect me with an agent", "escalation"),
            ("Let me talk to a real person", "escalation"),
            ("I need human assistance", ["escalation", "knowledge_base"]),
            ("This isn't working, I want a person", ["escalation", "knowledge_base"]),
            ("Transfer me to a representative", "escalation"),
        ]
        
        for text, expected in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            
            # Handle both single string and list of acceptable intents
            if isinstance(expected, list):
                assert intent_name in expected, \
                    f"Text: '{text}' | Expected one of: {expected} | Got: '{intent_name}'"
            else:
                assert intent_name == expected, \
                    f"Text: '{text}' | Expected: '{expected}' | Got: '{intent_name}'"
    
    def test_classify_greetings(self, classifier):
        """Test greeting classification"""
        test_cases = [
            ("Hello", ["greeting", "knowledge_base"]),
            ("Hi there", ["greeting", "knowledge_base"]),
            ("Good morning", ["greeting", "knowledge_base"]),
            ("Hey", ["greeting", "knowledge_base"]),
        ]
        
        for text, expected_intents in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            assert intent_name in expected_intents, \
                f"Unexpected intent for greeting: '{text}' -> '{intent_name}'"
    
    def test_classify_unknown(self, classifier):
        """Test unknown/unsupported queries"""
        test_cases = [
            ("Random gibberish text", ["unknown", "knowledge_base"]),
            ("Weather today", ["unknown", "knowledge_base"]),
            ("Tell me a joke", ["unknown", "knowledge_base"]),
            ("What's the meaning of life?", ["unknown", "knowledge_base"]),
        ]
        
        for text, expected_intents in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            assert intent_name in expected_intents, \
                f"Text: '{text}' | Expected one of: {expected_intents} | Got: '{intent_name}'"
    
    def test_classify_empty_input(self, classifier):
        """Test handling of empty input"""
        result = classifier.classify("")
        intent_name = extract_intent(result)
        assert intent_name in ["unknown", "error", "knowledge_base"], \
            f"Empty input should return 'unknown', 'error', or 'knowledge_base', got: '{intent_name}'"
    
    def test_classify_whitespace(self, classifier):
        """Test handling of whitespace-only input"""
        result = classifier.classify("   ")
        intent_name = extract_intent(result)
        assert intent_name in ["unknown", "error", "knowledge_base"], \
            f"Whitespace should return 'unknown', 'error', or 'knowledge_base', got: '{intent_name}'"
    
    def test_classify_with_punctuation(self, classifier):
        """Test classification with various punctuation"""
        test_cases = [
            ("Schedule appointment!!!", ["appointment", "action"]),
            ("Human agent???", ["escalation", "knowledge_base"]),
            ("What are hours...", "knowledge_base"),
        ]
        
        for text, expected in test_cases:
            result = classifier.classify(text.lower())
            intent_name = extract_intent(result)
            
            if isinstance(expected, list):
                assert intent_name in expected, \
                    f"Text: '{text}' | Expected one of: {expected} | Got: '{intent_name}'"
            else:
                assert intent_name == expected, \
                    f"Text: '{text}' | Expected: '{expected}' | Got: '{intent_name}'"

def test_intent_classifier_initialization():
    """Test that classifier initializes correctly"""
    classifier = IntentClassifier()
    assert classifier is not None
    # Check if classifier has the expected method
    assert hasattr(classifier, 'classify')
    assert callable(classifier.classify)

def test_intent_classifier_performance(classifier):
    """Test classifier performance with multiple inputs"""
    test_texts = [
        "schedule appointment",
        "what are hours",
        "speak to human",
        "book meeting",
        "tell me about products",
    ]
    
    for text in test_texts:
        result = classifier.classify(text)
        intent_name = extract_intent(result)
        assert intent_name in ["appointment", "action", "knowledge_base", "escalation", "unknown", "greeting"], \
            f"Unexpected intent: '{intent_name}' for text: '{text}'"

def test_intent_classifier_returns_tuple(classifier):
    """Test that classifier returns proper format"""
    result = classifier.classify("test")
   
    assert isinstance(result, (str, tuple)), f"Expected str or tuple, got {type(result)}"
    
    if isinstance(result, tuple):
        assert len(result) >= 1, "Tuple should have at least intent name"
        assert isinstance(result[0], str), "First element should be string"

def test_intent_classifier_confidence_scores(classifier):
    """Test that confidence scores are reasonable"""
    test_texts = [
        "schedule appointment",
        "hello",
        "what are business hours",
        "i want human agent",
    ]
    
    for text in test_texts:
        result = classifier.classify(text)
        
        if isinstance(result, tuple):
            intent, confidence = result[0], result[1]
            assert 0 <= confidence <= 1, f"Confidence should be between 0 and 1, got {confidence}"
            assert isinstance(intent, str), f"Intent should be string, got {type(intent)}"
        else:
            assert isinstance(result, str), f"Result should be string if not tuple, got {type(result)}"

def test_intent_classifier_consistency(classifier):
    """Test that similar inputs produce consistent results"""
    test_cases = [
        ("schedule appointment", "schedule an appointment"),
        ("hello", "hi"),
        ("i need help", "can you help me"),
    ]
    
    for text1, text2 in test_cases:
        result1 = classifier.classify(text1)
        result2 = classifier.classify(text2)
        
        intent1 = extract_intent(result1)
        intent2 = extract_intent(result2)
        
        # They don't have to be identical, but should be in similar categories
        if intent1 in ["appointment", "action"]:
            assert intent2 in ["appointment", "action", "knowledge_base"], \
                f"Similar phrases should have similar intents: '{text1}'->'{intent1}', '{text2}'->'{intent2}'"
        elif intent1 in ["escalation"]:
            assert intent2 in ["escalation", "knowledge_base"], \
                f"Similar phrases should have similar intents: '{text1}'->'{intent1}', '{text2}'->'{intent2}'"

if __name__ == "__main__":
    # Run tests directly if needed
    classifier = IntentClassifier()
    test = TestIntentClassifier()
    test.test_classify_appointment(classifier)
    test.test_classify_knowledge_base(classifier)
    test.test_classify_escalation(classifier)
    print("✅ All manual tests passed!")