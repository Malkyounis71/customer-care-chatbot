
# Customer Care AI Chatbot - Demo Script

## Demo Overview
This script demonstrates the chatbot's key capabilities:
1. Knowledge Base Queries
2. Appointment Scheduling
3. Human Escalation
4. Error Handling

## Preparation
1. Start the application: `python main.py`
2. Open browser: http://localhost:8000/chat
3. Clear previous conversations if needed

## Demo Sequence

### Part 1: Knowledge Base Queries (2 minutes)
**Goal:** Show accurate information retrieval

1. **Basic Information:**
   - User: "What are your business hours?"
   - Expected: Clear hours with timezone

2. **Product Information:**
   - User: "Tell me about your analytics product"
   - Expected: Detailed product features with menu options

3. **Pricing Query:**
   - User: "How much does the enterprise plan cost?"
   - Expected: Pricing details with tier information

4. **Support Query:**
   - User: "I need help with installation"
   - Expected: Support information with escalation options

### Part 2: Appointment Scheduling (3 minutes)
**Goal:** Show guided conversational flow

1. **Start Appointment:**
   - User: "I want to schedule a consultation"
   - Bot: Asks for service type (shows options 1-6)

2. **Service Selection:**
   - User: "1" (for consultation)
   - Bot: Asks for date

3. **Provide Details:**
   - User: "Next Tuesday"
   - Bot: Asks for time
   - User: "2 PM"
   - Bot: Asks for name
   - User: "John Smith"
   - Bot: Asks for email
   - User: "john@example.com"

4. **Confirmation:**
   - Bot: Shows appointment summary
   - User: "Yes"
   - Bot: Confirms booking with appointment ID

### Part 3: Human Escalation (2 minutes)
**Goal:** Show intelligent escalation

1. **Explicit Request:**
   - User: "I need to speak with a human agent"
   - Bot: Transfers with ticket ID and wait time

2. **Frustration Detection:**
   - User: "This isn't working! I've asked three times!"
   - Bot: Detects frustration, initiates transfer

3. **Sensitive Topic:**
   - User: "I need to discuss a legal complaint"
   - Bot: High-priority escalation for sensitive topics

4. **Repeated Failures:**
   - User: (Ask same question 3 times with corrections)
   - Bot: Detects repeated failures, escalates

### Part 4: Error Handling (1 minute)
**Goal:** Show robustness

1. **Gibberish Input:**
   - User: "asdfghjkl"
   - Bot: Graceful fallback to knowledge base

2. **Empty Input:**
   - User: ""
   - Bot: Validation error message

3. **System Error Simulation:**
   - Stop Qdrant service temporarily
   - User: "What products do you have?"
   - Bot: Degrades gracefully, offers alternative help

### Part 5: Advanced Features (2 minutes)
**Goal:** Show sophistication

1. **Context Awareness:**
   - User: "Change my appointment time"
   - Bot: Asks which appointment, shows modification flow

2. **Multiple Appointments:**
   - Schedule 2 appointments
   - User: "Show my appointments"
   - Bot: Lists appointments with details

3. **Analytics:**
   - Show `/api/analytics` endpoint
   - Demonstrate conversation insights

## Demo Tips

### For Presenters:
1. **Practice the flows** - Know the expected responses
2. **Show the code** - Briefly highlight key modules
3. **Explain the architecture** - Use the architecture diagram
4. **Demonstrate scalability** - Mention Docker and monitoring
5. **Highlight security** - Show PII masking

### For Technical Audience:
1. **Show RAG pipeline** - Explain embedding and retrieval
2. **Demonstrate intent classification** - Show patterns vs ML
3. **Explain escalation logic** - Show trigger thresholds
4. **Show monitoring** - Demonstrate Prometheus metrics

### For Business Audience:
1. **Focus on user experience** - Show natural conversation flow
2. **Highlight efficiency** - Demonstrate quick resolution
3. **Show analytics** - Business insights from conversations
4. **Emphasize security** - PII protection

## Troubleshooting During Demo

**If something goes wrong:**
1. Check logs: `tail -f logs/app.log`
2. Check health: http://localhost:8000/api/health
3. Restart if needed: `Ctrl+C` then `python main.py`
4. Have backup screenshots ready

**Common demo pitfalls:**
- Qdrant not running
- Port conflicts
- Missing knowledge base documents
- Network issues

## Success Metrics to Highlight
1. **Accuracy:** 95%+ on knowledge queries
2. **Speed:** < 2 second response time
3. **Escalation Rate:** < 10% of conversations
4. **User Satisfaction:** Built-in sentiment tracking

## Post-Demo Q&A Preparation

**Technical Questions:**
- How does RAG work with your documents?
- What ML model are you using?
- How do you handle multiple languages?
- What's your vector database choice?

**Business Questions:**
- How much does this reduce support costs?
- What's the implementation timeline?
- Can it integrate with our CRM?
- How do you ensure data privacy?

**Architecture Questions:**
- How do you handle scale?
- What's your deployment strategy?
- How do you monitor performance?
- What's your disaster recovery plan?