import json
from typing import Any, Dict
from datetime import datetime

def json_serializer(obj: Any) -> str:
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def safe_json_dumps(data: Dict) -> str:
    """Safely convert dict to JSON string"""
    return json.dumps(data, default=json_serializer, ensure_ascii=False)

def validate_email(email: str) -> bool:
    """Simple email validation"""
    import re
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

def truncate_text(text: str, max_length: int = 200) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."