from pydantic import BaseModel
from typing import Optional

class ChatRequest(BaseModel):
    message: str
    api_key: str  # <--- Unique key for security 🔑
    session_id: Optional[str] = None 

class ChatResponse(BaseModel):
    response: str
    session_id: Optional[str] = None 
    provider: str