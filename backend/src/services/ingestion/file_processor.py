import os
import asyncio
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Specific Stable Loaders
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader,
    UnstructuredFileLoader
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.src.services.vector_store.qdrant_adapter import get_vector_store
from backend.src.models.integration import UserIntegration # Integration model zaroori hai

def get_loader(file_path: str):
    """
    Factory function jo file extension ke hisaab se
    loader return karta hai.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        return TextLoader(file_path, encoding="utf-8")
    elif ext == ".pdf":
        return PyPDFLoader(file_path)
    elif ext == ".csv":
        return CSVLoader(file_path, encoding="utf-8")
    elif ext in [".doc", ".docx"]:
        return Docx2txtLoader(file_path)
    elif ext == ".md":
        return TextLoader(file_path, encoding="utf-8")
    else:
        return UnstructuredFileLoader(file_path)

# --- UPDATED: Added user_id and db session ---
async def process_file(file_path: str, session_id: str, user_id: str, db: AsyncSession):
    """
    Processes a single uploaded file strictly using the USER'S database.
    """
    print(f"INFO: [Ingestion] Starting secure processing for user {user_id}: {file_path}")
    
    try:
        # 1. DATABASE VERIFICATION: Check if user has Qdrant connected
        stmt = select(UserIntegration).where(
            UserIntegration.user_id == str(user_id),
            UserIntegration.provider == "qdrant",
            UserIntegration.is_active == True
        )
        result = await db.execute(stmt)
        integration = result.scalars().first()

        if not integration:
            print(f"❌ ERROR: User {user_id} has no Qdrant connected.")
            return -1 # Special code for 'No Database'

        # 2. Extract Credentials
        creds = json.loads(integration.credentials) if isinstance(integration.credentials, str) else integration.credentials
        
        # 3. Connect to User's Cloud Qdrant (No Fallback to Localhost)
        vector_store = get_vector_store(credentials=creds)

        # 4. File Loading
        loader = get_loader(file_path)
        docs = await asyncio.to_thread(loader.load)
        
        if not docs:
            print(f"WARNING: No content extracted from {file_path}")
            return 0

        # 5. Chunks Creation
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        split_docs = text_splitter.split_documents(docs)
        
        # Metadata logic
        for doc in split_docs:
            doc.metadata["session_id"] = session_id
            doc.metadata["user_id"] = user_id
            doc.metadata["file_name"] = os.path.basename(file_path)
            doc.metadata["source"] = os.path.basename(file_path) # Search ke liye source zaroori hai

        # 6. Upload to User's Vector DB
        await vector_store.aadd_documents(split_docs)
        print(f"SUCCESS: Processed {len(split_docs)} chunks to user's Cloud Qdrant.")
        return len(split_docs)

    except Exception as e:
        print(f"ERROR: [Ingestion] Critical failure: {e}")
        return 0