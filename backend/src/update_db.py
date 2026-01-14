import asyncio
from sqlalchemy import text
from backend.src.db.session import engine

async def upgrade_database():
    print("⚙️ Updating Database Schema (Without Deleting Data)...")
    
    async with engine.begin() as conn:
        # --- 1. Users Table mein 'api_key' add karna ---
        try:
            print("   -> Adding 'api_key' column to users...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN api_key VARCHAR;"))
        except Exception as e:
            print("      (Skipped: Column shayad pehle se hai)")

        # --- 2. Users Table mein 'allowed_domains' add karna ---
        try:
            print("   -> Adding 'allowed_domains' column to users...")
            await conn.execute(text("ALTER TABLE users ADD COLUMN allowed_domains VARCHAR DEFAULT '*';"))
        except Exception as e:
            print("      (Skipped: Column shayad pehle se hai)")

        # --- 3. Integrations Table mein 'profile_description' add karna ---
        try:
            print("   -> Adding 'profile_description' column to user_integrations...")
            await conn.execute(text("ALTER TABLE user_integrations ADD COLUMN profile_description TEXT;"))
        except Exception as e:
            print("      (Skipped: Column shayad pehle se hai)")

    print("✅ Database Update Complete! Aapka purana data safe hai.")

    # --- 4. Purane Users ke liye API Key Generate karna ---
    # Kyunki purane users ki API Key NULL hogi, unhein nayi key deni padegi.
    from backend.src.utils.auth import generate_api_key
    from sqlalchemy.future import select
    from backend.src.models.user import User
    from backend.src.db.session import AsyncSessionLocal

    print("🔑 Generating API Keys for existing users...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        
        count = 0
        for user in users:
            if not user.api_key: # Agar key nahi hai
                user.api_key = generate_api_key()
                user.allowed_domains = "*"
                db.add(user)
                count += 1
                print(f"   -> Key generated for: {user.email}")
        
        await db.commit()
        print(f"✅ {count} Users updated with new API Keys.")

if __name__ == "__main__":
    asyncio.run(upgrade_database())