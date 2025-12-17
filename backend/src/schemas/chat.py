from pydantic import BaseModel
from typing import Optional

# User jab sawal bhejegaecho $GOOGLE_API_KEY
class ChatRequest(BaseModel):
    message: str
    # Isay Optional bana diya. Default value None hai.
    session_id: Optional[str] = None 

# Server jab jawab dega
class ChatResponse(BaseModel):
    response: str
    # Yahan bhi Optional, kyunki guest ke paas ID nahi hogi
    session_id: Optional[str] = None 
    provider: str