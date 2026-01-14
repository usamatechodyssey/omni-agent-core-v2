# # backend/src/api/routes/chat.py
# from fastapi import APIRouter, Depends, HTTPException, Request
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from backend.src.db.session import get_db
# from backend.src.schemas.chat import ChatRequest, ChatResponse
# from backend.src.services.chat_service import process_chat
# from backend.src.models.user import User

# router = APIRouter()

# @router.post("/chat", response_model=ChatResponse)
# async def chat_endpoint(
#     request_body: ChatRequest, 
#     request: Request, # Browser headers read karne ke liye
#     db: AsyncSession = Depends(get_db)
# ):
#     try:
#         # 1. API Key se Bot Owner (User) ko dhoondo
#         stmt = select(User).where(User.api_key == request_body.api_key)
#         result = await db.execute(stmt)
#         bot_owner = result.scalars().first()

#         if not bot_owner:
#             raise HTTPException(status_code=401, detail="Invalid API Key. Unauthorized access.")

#         # 2. DOMAIN LOCK LOGIC (Whitelisting)
#         # Browser automatically 'origin' ya 'referer' header bhejta hai
#         client_origin = request.headers.get("origin") or request.headers.get("referer") or ""
        
#         if bot_owner.allowed_domains != "*":
#             allowed = [d.strip() for d in bot_owner.allowed_domains.split(",")]
#             # Check if client_origin contains any of the allowed domains
#             is_authorized = any(domain in client_origin for domain in allowed)
            
#             if not is_authorized:
#                 print(f"🚫 Blocked unauthorized domain: {client_origin}")
#                 raise HTTPException(status_code=403, detail="Domain not authorized to use this bot.")

#         # 3. Process Chat (Using the bot_owner's credentials)
#         session_id = request_body.session_id or f"guest_{bot_owner.id}"
        
#         response_text = await process_chat(
#             message=request_body.message,
#             session_id=session_id,
#             user_id=str(bot_owner.id), # Owner ki ID use hogi DB lookup ke liye
#             db=db
#         )
        
#         return ChatResponse(
#             response=response_text,
#             session_id=session_id,
#             provider="omni_agent" 
#         )
        
#     except HTTPException as he: raise he
#     except Exception as e:
#         print(f"❌ Chat Error: {e}")
#         raise HTTPException(status_code=500, detail="AI Service Interrupted.")
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.src.db.session import get_db
from backend.src.schemas.chat import ChatRequest, ChatResponse
from backend.src.services.chat_service import process_chat
from backend.src.models.user import User

router = APIRouter()

# --- HELPER: DOMAIN SECURITY (Standardized) ---
def verify_domain_access(user: User, request: Request):
    """
    Checks if the incoming request is from an allowed domain.
    """
    # 1. Browser headers check karein
    client_origin = request.headers.get("origin") or request.headers.get("referer") or ""
    
    # 2. Agar user ne "*" set kiya hai, to sab allow hai
    if user.allowed_domains == "*":
        return True
        
    # 3. Allowed domains ki list banao
    allowed = [d.strip() for d in user.allowed_domains.split(",")]
    
    # 4. Check karo ke origin match karta hai ya nahi
    is_authorized = any(domain in client_origin for domain in allowed)
    
    if not is_authorized:
        print(f"🚫 [Chat Security] Blocked unauthorized domain: {client_origin}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Domain not authorized to use this bot."
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request_body: ChatRequest, 
    request: Request, # Browser headers read karne ke liye
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. AUTH: API Key se Bot Owner (User) ko dhoondo
        # (Note: Chat Widget Body mein key bhejta hai, isliye hum Header wala dependency use nahi kar rahe yahan)
        stmt = select(User).where(User.api_key == request_body.api_key)
        result = await db.execute(stmt)
        bot_owner = result.scalars().first()

        if not bot_owner:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid API Key. Unauthorized access."
            )
        
        # Check if user is active
        if not bot_owner.is_active:
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Bot owner account is inactive."
            )

        # 2. SECURITY: Domain Lock Check 🔐
        verify_domain_access(bot_owner, request)

        # 3. PROCESS: Chat Logic (Using the bot_owner's credentials)
        session_id = request_body.session_id or f"guest_{bot_owner.id}"
        
        response_text = await process_chat(
            message=request_body.message,
            session_id=session_id,
            user_id=str(bot_owner.id), # Owner ki ID use hogi DB lookup ke liye
            db=db
        )
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            provider="omni_agent" 
        )
        
    except HTTPException as he: raise he
    except Exception as e:
        print(f"❌ Chat Error: {e}")
        raise HTTPException(status_code=500, detail="AI Service Interrupted.")