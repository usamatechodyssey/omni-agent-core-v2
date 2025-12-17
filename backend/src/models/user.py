from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text # Text add kiya
from sqlalchemy.sql import func
from backend.src.db.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # --- NEW: Bot Customization ---
    bot_name = Column(String, default="Support Agent")
    bot_instruction = Column(Text, default="You are a helpful customer support agent. Only answer questions related to the provided data.")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())