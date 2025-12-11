import base64
import re
import hashlib
import secrets
from typing import Optional
from cryptography.fernet import Fernet
from loguru import logger

class SecurityManager:
    """Enhanced security for sensitive data"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize security manager with encryption key"""
        
        if not encryption_key or encryption_key == "None":
            # Generate a new key if none provided
            logger.warning("No encryption key provided, generating new one")
            encryption_key = Fernet.generate_key().decode()
        
        # Clean the key
        encryption_key = str(encryption_key).strip().strip('"').strip("'")
        
        try:
            # Try to use the key
            self.cipher = Fernet(encryption_key.encode())
            self.encryption_key = encryption_key
            logger.info("Security manager initialized with encryption")
        except Exception as e:
            # If invalid, generate new key
            logger.warning(f"Invalid encryption key ({e}), generating new one")
            encryption_key = Fernet.generate_key().decode()
            self.cipher = Fernet(encryption_key.encode())
            self.encryption_key = encryption_key
            logger.info("Security manager initialized with new key")
    
    def sanitize_input(self, text: str) -> str:
        """
        Sanitize user input to prevent injection attacks
        
        Args:
            text: Raw user input
            
        Returns:
            Sanitized text safe for processing
        """
        if not text:
            return ""
        
        # Convert to string
        text = str(text)
        
        # Remove HTML/script tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove SQL injection patterns
        dangerous_patterns = [
            r'(\bDROP\b|\bDELETE\b|\bINSERT\b|\bUPDATE\b|\bCREATE\b|\bALTER\b)',
            r'(--|;|\/\*|\*\/)',
            r'(\bUNION\b.*\bSELECT\b)',
            r'(\bEXEC\b|\bEXECUTE\b)',
            r'(javascript:|onerror=|onload=)'
        ]
        
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit length to prevent DoS
        text = text[:1000]
        
        # Strip whitespace
        return text.strip()
    
    def mask_pii(self, text: str) -> str:
        """
        Mask personally identifiable information in text
        
        Args:
            text: Text potentially containing PII
            
        Returns:
            Text with PII masked
        """
        if not text:
            return ""
        
        # Mask emails
        text = re.sub(
            r'[\w\.-]+@[\w\.-]+\.\w+',
            lambda m: m.group(0)[0] + '***@' + m.group(0).split('@')[1] if '@' in m.group(0) else '[EMAIL]',
            text
        )
        
        # Mask phone numbers
        text = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', 'XXX-XXX-XXXX', text)
        
        # Mask SSN
        text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', 'XXX-XX-XXXX', text)
        
        # Mask credit cards
        text = re.sub(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b', 'XXXX-XXXX-XXXX-XXXX', text)
        
        return text
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive customer data"""
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive customer data"""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return encrypted_data
    
    def hash_identifier(self, identifier: str) -> str:
        """Hash user identifiers for privacy"""
        salt = secrets.token_hex(8)
        return hashlib.sha256(f"{identifier}{salt}".encode()).hexdigest()
    
    def hash_data(self, data: str) -> str:
        """Create a hash of data (one-way, no salt)"""
        return hashlib.sha256(data.encode()).hexdigest()
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def validate_phone(self, phone: str) -> bool:
        """Validate phone number format"""
        # Remove common separators
        clean_phone = re.sub(r'[-.\s()]', '', phone)
        # Check if it's 10 digits (US format)
        return bool(re.match(r'^\d{10}$', clean_phone))
    
    def detect_suspicious_patterns(self, text: str) -> bool:
        """
        Detect suspicious patterns that might indicate malicious intent
        
        Returns:
            True if suspicious patterns detected
        """
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'eval\(',
            r'\bDROP\s+TABLE\b',
            r'\.\./',  # Directory traversal
        ]
        
        text_lower = text.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_lower):
                logger.warning(f"Suspicious pattern detected: {pattern}")
                return True
        
        return False