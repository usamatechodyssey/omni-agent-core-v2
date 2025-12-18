# --- EXTERNAL IMPORTS ---
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # ------------------- CORE PROJECT SETTINGS -------------------
    PROJECT_NAME: str = "OmniAgent Core"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # ------------------- SECURITY (NEW) -------------------
    # Ye bohot zaroori hai JWT tokens ke liye
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ------------------- NETWORK / HOSTING -------------------
    QDRANT_HOST: str = os.getenv("QDRANT_HOST", "localhost")
    QDRANT_PORT: int = 6333
    
    MONGO_HOST: str = os.getenv("MONGO_HOST", "localhost")
    MONGO_PORT: int = int(os.getenv("MONGO_PORT", 27018))
    MONGO_USER: str = os.getenv("MONGO_INITDB_ROOT_USERNAME", "admin")
    MONGO_PASS: str = os.getenv("MONGO_INITDB_ROOT_PASSWORD", "super_secret_admin_pass")

    # ------------------- DATABASES -------------------
    _DATABASE_URL: str = os.getenv("POSTGRES_URL", "sqlite+aiosqlite:///./omni_agent.db")

    @property
    def DATABASE_URL(self) -> str:
        url = self._DATABASE_URL
        if url and "?" in url:
            url = url.split("?")[0]
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url and url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

              # --- DEBUG PRINT (Ye add karein) ---
        print(f"🕵️ DEBUG: Connecting to DB URL: {url}") 
        # (Security Warning: Ye console mein password dikhayega, baad mein hata dena)
        return url

    @property
    def QDRANT_URL(self) -> str:
        if self.QDRANT_HOST.startswith("http"):
            return self.QDRANT_HOST
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"

    QDRANT_COLLECTION_NAME: str = "omni_agent_main_collection"
    QDRANT_API_KEY: str | None = None

    # ------------------- RAG / EMBEDDINGS -------------------
    EMBEDDING_PROVIDER: str = "local"
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"

    # ------------------- AI MODELS -------------------
    LLM_PROVIDER: str = "generic" 
    LLM_MODEL_NAME: str = "gpt-3.5-turbo"
    LLM_BASE_URL: str | None = None 
    LLM_API_KEY: str | None = None
    
    GROQ_API_KEY: str | None = None
    GOOGLE_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", env_file_encoding='utf-8')

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()