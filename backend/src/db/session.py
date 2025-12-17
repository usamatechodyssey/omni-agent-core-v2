from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from backend.src.core.config import settings

# Connection Arguments
connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

# --- ROBUST ENGINE CREATION (The Fix) ---
# Ye settings Neon/Serverless ke liye best hain
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_size=5,  # 5 connections ka pool rakho
    max_overflow=10, # Agar zaroorat pade to 10 aur bana lo
    pool_recycle=300, # Har 5 minute (300s) mein purane connections ko refresh karo (Sleep issue fix)
    pool_pre_ping=True, # Har query se pehle check karo ke connection zinda hai ya nahi
)

# Session Maker
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Dependency Injection
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()