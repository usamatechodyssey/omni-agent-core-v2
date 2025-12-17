import asyncio
from backend.src.db.session import engine
from backend.src.db.base import Base

# --- Import ALL Models here ---
# Ye zaroori hai taake SQLAlchemy ko pata chale ke kaunse tables banane hain
from backend.src.models.chat import ChatHistory
from backend.src.models.ingestion import IngestionJob
from backend.src.models.integration import UserIntegration # <--- Isme naya column hai
from backend.src.models.user import User

async def init_database():
    print("🚀 Connecting to the database...")
    async with engine.begin() as conn:
        # --- CRITICAL FOR SCHEMA UPDATE ---
        # Hum purane tables DROP kar rahe hain taake naya 'profile_description' column add ho sake.
        # Note: Isse purana data udd jayega (Dev environment ke liye theek hai).
        print("🗑️ Dropping old tables to apply new Schema...")
        await conn.run_sync(Base.metadata.drop_all) 
        
        print("⚙️ Creating new tables (Users, Chats, Integrations, Jobs)...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully!")

if __name__ == "__main__":
    print("Starting database initialization...")
    asyncio.run(init_database())