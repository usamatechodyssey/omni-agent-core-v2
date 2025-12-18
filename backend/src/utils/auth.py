import secrets # Cryptographically strong random numbers generate karne ke liye
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from backend.src.core.config import settings

# Password Hasher (Bcrypt/Argon2)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def verify_password(plain_password, hashed_password):
    """Check karein ke user ka password sahi hai ya nahi"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Password ko encrypt karein taake DB mein plain text save na ho"""
    return pwd_context.hash(password)

def create_access_token(data: dict):
    """User ke liye Login Token (Badge) banayein"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    secret_key = settings.SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt

# --- NEW: SaaS API KEY GENERATOR (🔐) ---
def generate_api_key():
    """
    Ek unique aur secure API Key banata hai.
    Format: omni_as87d... (64 characters long)
    """
    # 32 bytes ka random token jo URL-safe string ban jayega
    random_string = secrets.token_urlsafe(32)
    return f"omni_{random_string}"