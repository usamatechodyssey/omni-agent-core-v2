from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.src.core.config import settings

# Connection Arguments
connect_args = {}

# Agar Postgres hai, to command timeout badha do
if "postgresql" in settings.DATABASE_URL:
    connect_args = {
        "command_timeout": 60, # 60 seconds tak wait karega query ka
        "server_settings": {
            "jit": "off" # JIT compilation off karne se kabhi kabhi speed fast hoti hai
        }
    }

if "sqlite" in settings.DATABASE_URL:
    connect_args = {"check_same_thread": False}

# --- ROBUST ENGINE CREATION ---
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args=connect_args,
    pool_size=20,         # Pool size badhaya (Load handle karne ke liye)
    max_overflow=40,      # Overflow badhaya
    pool_recycle=300,     # Refresh every 5 mins
    pool_pre_ping=True,   # Connection check before query
    pool_timeout=60       # 🔥 Timeout aur badha diya (30s -> 60s)
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
        except Exception:
            # Agar koi logic error aaye to rollback karein
            await session.rollback()
            raise
        finally:
            # 🔥 FIX: Graceful Cleanup
            # Agar connection pehle hi close ho gaya ho (heavy load ki wajah se),
            # to dobara close karne par crash na ho.
            try:
                await session.close()
            except Exception:
                pass