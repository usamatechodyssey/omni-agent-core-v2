
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.db.session import get_db
from backend.src.schemas.chat import ChatRequest, ChatResponse
from backend.src.services.chat_service import process_chat
from backend.src.core.config import settings

# --- Security Imports ---
from backend.src.api.routes.deps import get_current_user
from backend.src.models.user import User

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user) # <-- User Logged in hai
):
    """
    Protected Chat Endpoint.
    Only accessible with a valid JWT Token.
    """
    try:
        # User ki ID token se aayegi (Secure)
        # Session ID user maintain kar sakta hai taake alag-alag chats yaad rahein
        user_id = str(current_user.id)
        session_id = request.session_id or user_id # Fallback
        
        # --- FIX IS HERE: 'user_id' pass kiya ja raha hai ---
        response_text = await process_chat(
            message=request.message,
            session_id=session_id,
            user_id=user_id, # <--- Ye hum bhool gaye thay
            db=db
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            # 'provider' ab chat_service se aayega, humein yahan hardcode nahi karna
            provider="omni_agent" 
        )
        
    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc() # Poora error print karega
        raise HTTPException(status_code=500, detail=str(e))