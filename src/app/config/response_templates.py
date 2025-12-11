"""
Response templates for the chatbot.
"""

from typing import Dict, Any


class ResponseTemplates:
    """Templates for chatbot responses."""
    
    @staticmethod
    def greeting() -> str:
        """Greeting template."""
        return """Hello! 👋 Welcome to COB Company Customer Care.

I'm here to help you with:
• Product information
• Scheduling appointments
• Technical support
• General inquiries

How can I assist you today?"""
    
    @staticmethod
    def goodbye() -> str:
        """Goodbye template."""
        return """Thank you for contacting COB Company! Have a wonderful day! 😊

Feel free to return anytime you need assistance."""
    
    @staticmethod
    def escalation(reason: str) -> str:
        """Escalation template."""
        return f"""👨‍💼 **Connecting to Human Agent**

**Reason:** {reason}

Please hold while I transfer you to our next available agent.

⏳ **Average wait time:** 2-3 minutes

Your conversation history will be shared with the agent to help them assist you better.

Thank you for your patience! 🙏"""
    
    @staticmethod
    def appointment_question(question_type: str, appointment_data: Dict[str, Any]) -> str:
        """Generate appointment questions."""
        # Check if it's a demo appointment
        is_demo = appointment_data.get('service_type') == 'demo'
        demo_product = appointment_data.get('demo_product', '')
        
        product_display = {
            'enterprise_suite': 'COB Enterprise Suite',
            'analytics_pro': 'COB Analytics Pro',
            'cloud_services': 'COB Cloud Services',
            'general': 'Product'
        }.get(demo_product, 'Product')
        
        if is_demo and question_type == 'date':
            return f"""🎥 **Schedule {product_display} Demo**

    I'd be happy to schedule a demo of {product_display} for you!

    **When would you like to schedule your demo?**

    Please provide a date:
    • Today/Tomorrow
    • Next Monday/Tuesday/etc.
    • Specific date like December 15
    • Day of week like Friday"""
        
        
        responses = {
            'service_type': """**Let's schedule your appointment! 📅**

    What type of service are you looking for?
    **Available options:**
    1. **Consultation** - Strategic planning and advisory services
    2. **Support** - Technical assistance and troubleshooting  
    3. **Installation** - System setup and implementation
    4. **Maintenance** - Regular upkeep and optimization
    5. **Training** - User education and skill development
    6. **Demo** - Product demonstration and walkthrough

    **Please indicate your choice by number or name.**""",
            
            'date': """**Great! Now, when would you like your appointment?**

    Please provide a date:
    • **Today/Tomorrow**
    • **Next Monday/Tuesday/etc.**
    • **Specific date:** December 15, 2024-12-15
    • **Day of week:** Friday""",
            
            'time': """**Perfect! What time works best for you?**

    Examples:
    • **Standard time:** 2:00 PM, 3:30 PM
    • **24-hour format:** 14:00, 16:30
    • **Relative time:** Morning, Afternoon, Evening""",
            
            'customer_name': """**Now I need your name for the booking.**

    What's your full name? (e.g., John Smith)""",
            
            'email': """**One last step!** 📧

    Please provide your email address for confirmation:
    • **Example:** name@example.com
    • **Format:** user@domain.com

    This is where we'll send your appointment confirmation."""
        }
        
        # Get base response
        response = responses.get(question_type, f"Please provide the {question_type} information.")
        
        # Add context if we have some info already
        collected = []
        if appointment_data.get('service_type'):
            service_type = appointment_data['service_type']
            if service_type == 'demo':
                collected.append(f"• **Service:** {product_display} Demo")
            else:
                collected.append(f"• **Service:** {service_type.title()}")
        if appointment_data.get('date'):
            collected.append(f"• **Date:** {appointment_data['date']}")
        if appointment_data.get('time'):
            collected.append(f"• **Time:** {appointment_data['time']}")
        if appointment_data.get('customer_name'):
            collected.append(f"• **Name:** {appointment_data['customer_name']}")
        
        if collected:
            context = "\n\n📋 **Currently booked:**\n" + "\n".join(collected)
            response = context + "\n\n" + response
        
        return response
    
    @staticmethod
    def appointment_confirmation(appointment_data: Dict[str, Any], appointment_id: str) -> str:
        """Generate appointment confirmation."""
        return f"""📋 **Please confirm your appointment details:**

• **Service:** {appointment_data.get('service_type', '').title()}
• **Date:** {appointment_data.get('date', '')}
• **Time:** {appointment_data.get('time', '')}
• **Name:** {appointment_data.get('customer_name', '')}
• **Email:** {appointment_data.get('email', '')}

**Please reply with:**
✅ **"Yes"** to confirm and book this appointment
❌ **"No"** to make changes

*(Just type "yes" or "no")*"""
    
    @staticmethod
    def appointment_modification_confirmation(appointment_data: Dict[str, Any], appointment_id: str) -> str:
        """Generate appointment modification confirmation."""
        return f"""📋 **Please confirm your appointment changes** (ID: {appointment_id}):

• **Service:** {appointment_data.get('service_type', '').title()}
• **Date:** {appointment_data.get('date', '')}
• **Time:** {appointment_data.get('time', '')}
• **Name:** {appointment_data.get('customer_name', '')}
• **Email:** {appointment_data.get('email', '')}

**Please reply with:**
✅ **"Yes"** to confirm and update this appointment
❌ **"No"** to make more changes

*(Just type "yes" or "no")*"""
    
    @staticmethod
    def support_menu() -> str:
        """Support menu template."""
        return """I understand you need technical support. I'd be happy to help! 🔧

**How would you like to proceed?**

1. **Connect with a support specialist** immediately 👨‍💼
2. **Schedule a support appointment** at your convenience 📅  
3. **Tell me more** about your issue and I'll search our knowledge base 🔍

Please reply with 1, 2, or 3, or describe your issue in detail."""
    
    @staticmethod
    def product_menu() -> str:
        """Product menu template."""
        return """**What would you like to do next?**
1. **Schedule a product demo** 🎥
2. **Get detailed pricing** 💰
3. **Compare different products** ⚖️
4. **Speak with a specialist** 👨‍💼

Reply with 1, 2, 3, or 4."""
    
    @staticmethod
    def no_knowledge_found(query: str) -> str:
        """No knowledge found template."""
        return f"""I couldn't find specific information about "{query}" in our knowledge base. 🔍

**Here's what I can help with:**
• Product information
• Appointment scheduling  
• Technical support
• Pricing details

Would you like me to:
1. **Connect you with a specialist**
2. **Schedule an appointment**
3. **Try searching with different keywords**

Please reply with 1, 2, or 3."""
    
    @staticmethod
    def get_pricing_details() -> str:
        """Get pricing details."""
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
    
    @staticmethod
    def get_product_comparison() -> str:
        """Get product comparison."""
        return """**⚖️ Product Comparison**

**COB Enterprise Suite vs COB Analytics Pro:**

| Feature | Enterprise Suite | Analytics Pro |
|---------|-----------------|---------------|
| Core Function | Business Management | Data Analysis |
| Best For | Daily operations | Data-driven decisions |
| Key Features | CRM, HR, Finance | Dashboards, Predictive Analytics |
| Users | 5-200+ | 1-50 |
| Starting Price | $99/user/month | $149/month |

**Which product aligns better with your needs?**"""