"""
Date and time parsing utilities.
"""

from datetime import datetime, timedelta
import re
from typing import Optional, Tuple
from loguru import logger


class DateTimeParser:
    """Parse dates and times from natural language."""
    
    def __init__(self):
        self._init_date_patterns()
        self._init_time_patterns()
    
    def _init_date_patterns(self):
        """Initialize date parsing patterns."""
        self.days_of_week = {
            'monday': 0, 'mon': 0,
            'tuesday': 1, 'tue': 1, 'tues': 1,
            'wednesday': 2, 'wed': 2,
            'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
            'friday': 4, 'fri': 4,
            'saturday': 5, 'sat': 5,
            'sunday': 6, 'sun': 6
        }
        
        self.months = {
            'january': 1, 'jan': 1,
            'february': 2, 'feb': 2,
            'march': 3, 'mar': 3,
            'april': 4, 'apr': 4,
            'may': 5,
            'june': 6, 'jun': 6,
            'july': 7, 'jul': 7,
            'august': 8, 'aug': 8,
            'september': 9, 'sep': 9, 'sept': 9,
            'october': 10, 'oct': 10,
            'november': 11, 'nov': 11,
            'december': 12, 'dec': 12
        }
    
    def _init_time_patterns(self):
        """Initialize time parsing patterns."""
        self.time_periods = {
            'morning': '9:00 AM',
            'afternoon': '2:00 PM',
            'evening': '6:00 PM',
            'noon': '12:00 PM',
            'midnight': '12:00 AM'
        }
    
    def parse_date(self, text: str) -> Optional[str]:
        """Parse date from natural language."""
        today = datetime.now()
        text_lower = text.lower().strip()
        
        logger.info(f"🔍 Parsing date from: '{text}'")
        
        # Handle "today"
        if 'today' in text_lower:
            result = today.strftime('%Y-%m-%d')
            logger.info(f"✅ Parsed 'today' as: {result}")
            return result
        
        # Handle "tomorrow"
        if 'tomorrow' in text_lower:
            result = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            logger.info(f"✅ Parsed 'tomorrow' as: {result}")
            return result
        
        # Handle "next monday", "next tuesday", etc.
        for day_name, target_weekday in self.days_of_week.items():
            if day_name in text_lower:
                current_weekday = today.weekday()
                days_ahead = target_weekday - current_weekday
                if days_ahead <= 0:
                    days_ahead += 7
                
                # Check for "next" keyword
                if 'next' in text_lower:
                    days_ahead += 7
                
                target_date = today + timedelta(days=days_ahead)
                result = target_date.strftime('%Y-%m-%d')
                logger.info(f"✅ Parsed '{day_name}' as: {result}")
                return result
        
        # Handle month day format (December 15, Dec 15)
        for month_name, month_num in self.months.items():
            if month_name in text_lower:
                # Look for day number
                day_match = re.search(r'\b(\d{1,2})(?:\s|st|nd|rd|th)?\b', text_lower)
                if day_match:
                    day = int(day_match.group(1))
                    year = today.year
                    
                    # Create the date
                    try:
                        target_date = datetime(year, month_num, day)
                        
                        # If date is in the past, use next year
                        if target_date < today:
                            target_date = datetime(year + 1, month_num, day)
                        
                        result = target_date.strftime('%Y-%m-%d')
                        logger.info(f"✅ Parsed '{month_name} {day}' as: {result}")
                        return result
                    except ValueError as e:
                        logger.error(f"❌ Error parsing date: {e}")
                        return None
        
        # Handle numeric formats (12/15, 12-15, 12/15/2024)
        date_match = re.search(r'(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?', text)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            year = date_match.group(3)
            
            if year:
                year = int(year)
                if year < 100:
                    year += 2000
            else:
                year = today.year
            
            try:
                target_date = datetime(year, month, day)
                # If date is in the past, use next year
                if target_date < today:
                    target_date = datetime(year + 1, month, day)
                
                result = target_date.strftime('%Y-%m-%d')
                logger.info(f"✅ Parsed numeric date as: {result}")
                return result
            except ValueError as e:
                logger.error(f"❌ Error parsing numeric date: {e}")
                return None
        
        # Handle "in X days"
        days_match = re.search(r'in\s+(\d+)\s+days?', text_lower)
        if days_match:
            days = int(days_match.group(1))
            target_date = today + timedelta(days=days)
            result = target_date.strftime('%Y-%m-%d')
            logger.info(f"✅ Parsed 'in {days} days' as: {result}")
            return result
        
        logger.info(f"❌ Could not parse date from: '{text}'")
        return None
    
    def parse_time(self, text: str) -> Optional[str]:
        """Parse time from natural language."""
        text_lower = text.lower().strip()
        
        logger.info(f"🔍 Parsing time from: '{text}'")
        
        # Handle descriptive times
        for period, time_value in self.time_periods.items():
            if period in text_lower:
                logger.info(f"✅ Parsed descriptive '{period}' as: {time_value}")
                return time_value
        
        # Handle "3.30 pm" or "3.30pm" (with dot)
        match = re.search(r'(\d{1,2})[\.:](\d{2})\s*(am|pm|a\.m\.|p\.m\.)', text_lower, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            am_pm = match.group(3).upper()
            
            # Handle a.m./p.m. notation
            if '.' in am_pm:
                am_pm = 'AM' if 'a' in am_pm.lower() else 'PM'
            else:
                am_pm = 'AM' if 'am' in am_pm.lower() else 'PM'
            
            result = f"{hour}:{minute} {am_pm}"
            logger.info(f"✅ Parsed '{text}' as: {result}")
            return result
        
        # Handle "8:30 pm", "2:30 PM"
        match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm|a\.m\.|p\.m\.)', text_lower, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            am_pm = match.group(3).upper()
            
            if '.' in am_pm:
                am_pm = 'AM' if 'a' in am_pm.lower() else 'PM'
            else:
                am_pm = 'AM' if 'am' in am_pm.lower() else 'PM'
            
            result = f"{hour}:{minute} {am_pm}"
            logger.info(f"✅ Parsed '{text}' as: {result}")
            return result
        
        # Handle "8pm", "2pm", "11 am", "3 pm"
        match = re.search(r'(\d{1,2})\s*(am|pm|a\.m\.|p\.m\.)', text_lower, re.IGNORECASE)
        if match:
            hour = int(match.group(1))
            am_pm = match.group(2).upper()
            
            if '.' in am_pm:
                am_pm = 'AM' if 'a' in am_pm.lower() else 'PM'
            else:
                am_pm = 'AM' if 'am' in am_pm.lower() else 'PM'
            
            result = f"{hour}:00 {am_pm}"
            logger.info(f"✅ Parsed '{text}' as: {result}")
            return result
        
        # Handle 24-hour format "14:00", "08:30"
        match = re.search(r'\b([01]?\d|2[0-3])[\.:]?([0-5]\d)\b', text_lower)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            am_pm = 'AM' if hour < 12 else 'PM'
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            result = f"{display_hour}:{minute} {am_pm}"
            logger.info(f"✅ Parsed 24-hour '{text}' as: {result}")
            return result
        
        # Handle "8:30" without am/pm
        match = re.search(r'(\d{1,2})[\.:](\d{2})', text_lower)
        if match:
            hour = int(match.group(1))
            minute = match.group(2)
            
            # Assume reasonable business hours
            if hour < 8:
                result = f"{hour}:{minute} PM"  # Assume PM for early numbers
            elif hour < 12:
                result = f"{hour}:{minute} AM"
            else:
                am_pm = 'PM' if hour >= 12 else 'AM'
                display_hour = hour if hour <= 12 else hour - 12
                if display_hour == 0:
                    display_hour = 12
                result = f"{display_hour}:{minute} {am_pm}"
            
            logger.info(f"✅ Parsed time-only '{text}' as: {result}")
            return result
        
        logger.info(f"❌ Could not parse time from: '{text}'")
        return None
    
    def parse_combined_datetime(self, text: str) -> Optional[Tuple[str, str]]:
        """Parse combined date-time phrases like 'next Tuesday afternoon'."""
        text_lower = text.lower().strip()
        
        patterns = [
            (r'(next|this|following)\s+(\w+)\s+(morning|afternoon|evening|noon)', 'day_period'),
            (r'(\w+)\s+(morning|afternoon|evening)', 'day_period'),
            (r'(today|tomorrow)\s+(morning|afternoon|evening)', 'today_tomorrow')
        ]
        
        for pattern, pattern_type in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if pattern_type == 'day_period':
                    if 'next' in match.group(1) or 'following' in match.group(1):
                        day_word = match.group(2)
                        date_value = self.parse_date(f"next {day_word}")
                    else:
                        day_word = match.group(1)
                        date_value = self.parse_date(day_word)
                    
                    period = match.group(3)
                    time_value = self.time_periods.get(period, '2:00 PM')
                    
                    if date_value:
                        return date_value, time_value
                
                elif pattern_type == 'today_tomorrow':
                    day = match.group(1)
                    period = match.group(2)
                    
                    date_value = self.parse_date(day)
                    time_value = self.time_periods.get(period, '2:00 PM')
                    
                    if date_value:
                        return date_value, time_value
        
        return None