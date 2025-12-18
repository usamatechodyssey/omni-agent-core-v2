import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # <--- New Import
from fastapi.middleware.cors import CORSMiddleware
from backend.src.core.config import settings

# --- API Route Imports ---
from backend.src.api.routes import chat, ingestion, auth, settings as settings_route

# 1. App Initialize karein
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="OmniAgent Core API - The Intelligent Employee"
)

# 2. CORS Setup (Security)
# Frontend ko Backend se baat karne ki ijazat dena
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Production mein hum isay specific domain karenge
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Mount Static Files (Chat Widget ke liye) 🎨
# Ye check karta hai ke 'static' folder hai ya nahi, agar nahi to banata hai
if not os.path.exists("static"):
    os.makedirs("static")

# Is line ka matlab hai: Jo bhi file 'static' folder mein hogi, wo '/static/filename' par milegi
app.mount("/static", StaticFiles(directory="static"), name="static")

# 4. Health Check Route
@app.get("/")
async def root():
    return {
        "message": "Welcome to OmniAgent Core 🚀", 
        "status": "active",
        "widget_url": "/static/widget.js" # Widget ka link bhi bata diya
    }

# 5. API Router Includes
app.include_router(auth.router, prefix=settings.API_V1_STR, tags=["Authentication"])
app.include_router(settings_route.router, prefix=settings.API_V1_STR, tags=["User Settings"])
app.include_router(chat.router, prefix=settings.API_V1_STR, tags=["Chat"])
app.include_router(ingestion.router, prefix=settings.API_V1_STR, tags=["Ingestion"])

if __name__ == "__main__":
    import uvicorn
    # Server Run command (Debugging ke liye)
    uvicorn.run("backend.src.main:app", host="0.0.0.0", port=8000, reload=True)