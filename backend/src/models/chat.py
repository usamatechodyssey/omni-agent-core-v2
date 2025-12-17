# backend/src/models/chat.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from backend.src.db.base import Base

class ChatHistory(Base):
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True) # User ka Session ID
    human_message = Column(Text) # User ne kya kaha
    ai_message = Column(Text) # Bot ne kya jawab diya
    timestamp = Column(DateTime(timezone=True), server_default=func.now()) # Kab baat hui
    
    # Metadata (Optional: Konsa tool use hua, kitne tokens lage)
    provider = Column(String) 
    tokens_used = Column(Integer, default=0)