import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from backend.src.models.integration import UserIntegration # SaaS Logic ke liye

async def process_url(url: str, session_id: str, user_id: str, db: AsyncSession):
    """
    SaaS Skill: Scrapes a URL strictly into the USER'S personal Cloud Qdrant.
    """
    print(f"INFO: [Ingestion] Verifying Database for User {user_id} before scraping: {url}")
    
    try:
        # 1. PEHLA KAAM: Database Verification (No Key, No Scrape)
        stmt = select(UserIntegration).where(
            UserIntegration.user_id == str(user_id),
            UserIntegration.provider == "qdrant",
            UserIntegration.is_active == True
        )
        result = await db.execute(stmt)
        integration = result.scalars().first()

        if not integration:
            print(f"❌ ERROR: User {user_id} has no Qdrant connected.")
            return -1 # 'No Database' code for the API to handle

        # 2. Extract User's Secret Credentials
        creds = json.loads(integration.credentials) if isinstance(integration.credentials, str) else integration.credentials
        
        # 3. Secure Connection to Cloud (Passing credentials)
        vector_store = get_vector_store(credentials=creds)

        # 4. Load Data from URL (Async Thread)
        def load_data():
            loader = WebBaseLoader(url)
            return loader.load()
        
        docs = await asyncio.to_thread(load_data)
        
        if not docs:
            print(f"WARNING: [Ingestion] No content found at {url}")
            return 0
            
        print(f"INFO: [Ingestion] Scrape Success. Content Length: {len(docs[0].page_content)} chars.")

        # 5. Text Splitting (Chunks)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        split_docs = text_splitter.split_documents(docs)
        
        # 6. Add Strict Metadata for Multi-tenancy
        for doc in split_docs:
            doc.metadata["session_id"] = session_id
            doc.metadata["user_id"] = user_id # Zaroori: Taake chat sirf apna data dhoonde
            doc.metadata["source"] = url 
            doc.metadata["type"] = "web_scrape"

        # 7. Upload to User's Vector DB
        await vector_store.aadd_documents(split_docs)
        print(f"SUCCESS: [Ingestion] {len(split_docs)} chunks synced to User's Cloud Database.")
        return len(split_docs)

    except Exception as e:
        print(f"ERROR: [Ingestion] Processing failed for {url}: {e}")
        return 0