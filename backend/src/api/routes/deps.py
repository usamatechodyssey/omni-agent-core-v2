# # backend/src/api/routes/deps.py
# from fastapi import Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer
# from jose import jwt, JWTError
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select

# from backend.src.core.config import settings
# from backend.src.db.session import get_db
# from backend.src.models.user import User
# from backend.src.utils.auth import ALGORITHM

# # Ye Swagger UI ko batata hai ke Token kahan se lena hai (/auth/login se)
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# async def get_current_user(
#     token: str = Depends(oauth2_scheme), 
#     db: AsyncSession = Depends(get_db)
# ) -> User:
#     """
#     Ye function har protected route se pehle chalega.
#     Ye Token ko verify karega aur Database se User nikal kar dega.
#     """
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
    
#     try:
#         # Token Decode karo
#         payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
#         user_id: str = payload.get("sub")
#         if user_id is None:
#             raise credentials_exception
#     except JWTError:
#         raise credentials_exception
        
#     # Database mein User check karo
#     result = await db.execute(select(User).where(User.id == int(user_id)))
#     user = result.scalars().first()
    
#     if user is None:
#         raise credentials_exception
        
#     return user
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.src.core.config import settings
from backend.src.db.session import get_db
from backend.src.models.user import User
from backend.src.utils.auth import ALGORITHM

# Ye Swagger UI ko batata hai ke Token kahan se lena hai (/auth/login se)
# Ye Dashboard access ke liye zaroori hai
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

# ============================================================
# 1. JWT AUTHENTICATION (For Dashboard / Settings Access)
# ============================================================
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Ye function Internal Dashboard ke liye hai (Login required).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Token Decode karo
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Database mein User check karo
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    return user

# ============================================================
# 2. API KEY AUTHENTICATION (For Public Widgets: Chat/Visual) 🔐
# ============================================================
async def get_current_user_by_api_key(
    # Frontend se header aayega: 'x-api-key: omni_abcdef...'
    api_key_header: str = Header(..., alias="x-api-key"), 
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Ye function External Widgets (Chatbot, Visual Search) ke liye hai.
    Ye JWT nahi maangta, sirf API Key maangta hai.
    """
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="API Key missing in header"
        )

    # 1. Database mein API Key check karo
    # Hum 'User' table mein dhoond rahe hain jiske paas ye key ho
    stmt = select(User).where(User.api_key == api_key_header)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    # 2. Validation
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key provided."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive."
        )
        
    return user