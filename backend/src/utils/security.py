from cryptography.fernet import Fernet
import base64

# --- FIX: A Valid, Consistent 32-byte Base64 Key ---
# Ye key change nahi hogi, to decryption hamesha chalega.
DEFAULT_KEY = b'8_sW7x9y2z4A5b6C8d9E0f1G2h3I4j5K6l7M8n9O0pQ='

class SecurityUtils:
    @staticmethod
    def get_cipher():
        # Production mein ye .env se aana chahiye
        # Development ke liye hum hardcoded valid key use kar rahe hain
        return Fernet(DEFAULT_KEY)

    @staticmethod
    def encrypt(data: str) -> str:
        if not data: return ""
        cipher = SecurityUtils.get_cipher()
        return cipher.encrypt(data.encode()).decode()

    @staticmethod
    def decrypt(token: str) -> str:
        if not token: return ""
        cipher = SecurityUtils.get_cipher()
        try:
            return cipher.decrypt(token.encode()).decode()
        except Exception as e:
            print(f"🔐 Decryption Failed: {e}")
            raise ValueError("Invalid Key or Corrupted Data")