import re
from typing import Tuple

class SecurityException(Exception):
    """Custom exception for security violations like prompt injection."""
    pass

class PIIScrubber:
    # Pre-compiling Regex patterns for performance
    
    # Email: Standard pattern
    EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # Phone: Matches +1-555-555-5555, (555) 555-5555, 555 555 5555
    # Logic: Look for digits with common separators, length approx 10-15
    PHONE_REGEX = re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b')
    
    # Credit Card: Matches 13-16 digits, with potential dashes or spaces
    # Logic: Look for groups of 4 digits or continuous strings
    CREDIT_CARD_REGEX = re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b|\b\d{13,16}\b')
    
    # IPv4 Address: 0.0.0.0 to 255.255.255.255
    IP_REGEX = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')

    # Basic Injection Keywords (Lowercased for case-insensitive check)
    INJECTION_KEYWORDS = [
        "ignore all previous instructions",
        "ignore previous instructions",
        "system override",
        "delete database",
        "drop table",
        "you are now",
        "bypass security"
    ]

    @staticmethod
    def scrub(text: str) -> str:
        """
        Sanitizes the input text by replacing PII with placeholders.
        """
        if not text:
            return ""

        # Apply redactions sequentially
        scrubbed_text = text
        scrubbed_text = PIIScrubber.EMAIL_REGEX.sub("[EMAIL_REDACTED]", scrubbed_text)
        scrubbed_text = PIIScrubber.PHONE_REGEX.sub("[PHONE_REDACTED]", scrubbed_text)
        scrubbed_text = PIIScrubber.CREDIT_CARD_REGEX.sub("[CC_REDACTED]", scrubbed_text)
        scrubbed_text = PIIScrubber.IP_REGEX.sub("[IP_REDACTED]", scrubbed_text)

        return scrubbed_text

    @staticmethod
    def check_for_injection(text: str) -> Tuple[bool, str]:
        """
        Checks for basic Prompt Injection attempts.
        Returns: (is_safe: bool, reason: str)
        """
        if not text:
            return True, ""

        lower_text = text.lower()
        for keyword in PIIScrubber.INJECTION_KEYWORDS:
            if keyword in lower_text:
                return False, f"Malicious keyword detected: '{keyword}'"
        
        return True, ""