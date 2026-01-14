# backend/src/main.py
# --- EXTERNAL IMPORTS ---
import os
import asyncio
import sys 
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles 
from fastapi.middleware.cors import CORSMiddleware
from backend.src.core.config import settings

# --- API Route Imports ---
from backend.src.api.routes import visual, chat, ingestion, auth, settings as settings_route

# ==========================================
# 🔥 WINDOWS FIX FOR DB TIMEOUTS 🔥
# ==========================================
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 1. App Initialize karein
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="OmniAgent Core API - The Intelligent Employee"
)

# 2. CORS Setup (Security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Static Files
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Health Check Route
@app.get("/")
async def root():
    return {
        "message": "Welcome to OmniAgent Core 🚀", 
        "status": "active",
        "widget_url": "/static/widget.js"
    }

# 5. API Router Includes
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(settings_route.router, prefix=settings.API_V1_STR, tags=["User Settings"])
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Chat"])
app.include_router(ingestion.router, prefix=settings.API_V1_STR, tags=["Ingestion"])
app.include_router(visual.router, prefix=settings.API_V1_STR, tags=["Visual Search"])

# ==========================================
# 🔥 UNIVERSAL START LOGIC 🔥
# ==========================================
if __name__ == "__main__":
    import uvicorn
    # Environment se PORT uthao, agar na mile to 8000 use karo
    # Yeh logic Local + Deployment dono jagah chalegi
    port = int(os.environ.get("PORT", 8000))
    
    print(f"🚀 Starting Server on Port: {port}")
    uvicorn.run("backend.src.main:app", host="0.0.0.0", port=port, reload=True)