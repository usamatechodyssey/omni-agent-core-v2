import asyncio
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.src.services.vector_store.qdrant_adapter import get_vector_store

async def process_url(url: str, session_id: str):
    """
    Ek URL se data scrape karta hai, chunks banata hai aur Qdrant mein save karta hai.
    """
    print(f"INFO: [Ingestion] Starting scraping for URL: {url}")
    
    try:
        # 1. Load Data from URL
        # Hum loader ko async thread mein chalayenge taake server block na ho
        def load_data():
            loader = WebBaseLoader(url)
            return loader.load()
        
        docs = await asyncio.to_thread(load_data)
        
        if not docs:
            print(f"WARNING: [Ingestion] No content found at {url}")
            return 0
            
        print(f"INFO: [Ingestion] Successfully fetched content. Length: {len(docs[0].page_content)} chars.")

    except Exception as e:
        print(f"ERROR: [Ingestion] Failed to scrape URL {url}: {e}")
        raise e # Error upar bhejenge taake API user ko bata sake

    # 2. Split Text into Chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    split_docs = text_splitter.split_documents(docs)
    
    # 3. Add Metadata (Bohat Zaroori)
    for doc in split_docs:
        doc.metadata["session_id"] = session_id
        doc.metadata["source"] = url # Taake pata chale ye data kahan se aaya
        doc.metadata["type"] = "web_scrape"

    # 4. Save to Qdrant
    try:
        vector_store = get_vector_store()
        await vector_store.aadd_documents(split_docs)
        print(f"SUCCESS: [Ingestion] Processed {len(split_docs)} chunks from {url}")
        return len(split_docs)
    except Exception as e:
        print(f"ERROR: [Ingestion] Failed to upload to Qdrant: {e}")
        return 0