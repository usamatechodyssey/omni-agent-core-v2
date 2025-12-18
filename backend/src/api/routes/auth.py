from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr

from backend.src.db.session import get_db
from backend.src.models.user import User
# generate_api_key ko import kiya 👇
from backend.src.utils.auth import get_password_hash, verify_password, create_access_token, generate_api_key

router = APIRouter()

# --- Schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None

# Response model ko extend kiya taake registration par API Key nazar aaye
class RegistrationResponse(BaseModel):
    access_token: str
    token_type: str
    api_key: str # User ko registeration par hi uski chabi mil jayegi 🔑

class Token(BaseModel):
    access_token: str
    token_type: str

# --- 1. Registration Endpoint ---
@router.post("/auth/register", response_model=RegistrationResponse)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check agar email pehle se exist karta hai
    result = await db.execute(select(User).where(User.email == user_in.email))
    existing_user = result.scalars().first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    # Naya User Banao + API Key Generate Karo (🔐)
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        api_key=generate_api_key(), # <--- Yeh line jadoo karegi
        allowed_domains="*" # Default: Har jagah allow karo, user baad mein settings se lock kar lega
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Direct Login Token do
    access_token = create_access_token(data={"sub": str(new_user.id)})
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "api_key": new_user.api_key # Registeration ke waqt hi key show kar di
    }

# --- 2. Login Endpoint ---
@router.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username)) 
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}