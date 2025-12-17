from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from backend.src.core.config import settings

# Password Hasher (Bcrypt)
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
    
    # Secret Key config se lenge (Ensure karein ke config mein ho)
    secret_key = settings.SECRET_KEY
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=ALGORITHM)
    return encoded_jwt