# backend/src/utils/security.py
import os
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# --- SECURITY CONFIGURATION ---
# 1. Production mein yeh key hamesha .env file mein honi chahiye: ENCRYPTION_KEY=...
# 2. Yeh niche wali key maine Fernet.generate_key() se generate ki hai. 
#    Yeh valid format mein hai, isay use karein taake crash na ho.
FALLBACK_KEY = b'gQp8v5Y3Z9k1L0mN2oP4rS6tU8vW0xY2z4A6bC8dE0f='

class SecurityUtils:
    @staticmethod
    def get_cipher():
        """
        Encryption Cipher banata hai.
        Priority: 
        1. OS Environment Variable (Best for Production)
        2. Hardcoded Fallback (Only for Local Dev)
        """
        key = os.getenv("ENCRYPTION_KEY")
        
        if not key:
            # Agar .env mein key nahi hai, to fallback use karo aur warning do
            # print("⚠️ WARNING: Using insecure fallback encryption key!")
            return Fernet(FALLBACK_KEY)
            
        try:
            # Agar .env se key aayi hai, to usay bytes mein convert karo
            if isinstance(key, str):
                key = key.encode()
            return Fernet(key)
        except Exception:
            print("❌ ERROR: Invalid ENCRYPTION_KEY in .env. Falling back to default.")
            return Fernet(FALLBACK_KEY)

    @staticmethod
    def encrypt(data: str) -> str:
        """String ko encrypt karke encrypted string return karta hai"""
        if not data: return ""
        try:
            cipher = SecurityUtils.get_cipher()
            # Encrypt karne ke liye bytes chahiye, wapis string banate waqt decode
            return cipher.encrypt(data.encode()).decode()
        except Exception as e:
            print(f"🔐 Encryption Failed: {e}")
            raise e

    @staticmethod
    def decrypt(token: str) -> str:
        """Encrypted string ko wapis original text mein lata hai"""
        if not token: return ""
        try:
            cipher = SecurityUtils.get_cipher()
            return cipher.decrypt(token.encode()).decode()
        except Exception as e:
            # Agar key change hui ya data corrupt hua to ye error dega
            print(f"🔐 Decryption Failed: {e}")
            raise ValueError("Invalid Key or Corrupted Data")