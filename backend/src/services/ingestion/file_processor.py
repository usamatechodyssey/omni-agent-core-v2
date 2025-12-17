# backend/src/services/ingestion/file_processor.py
import os
import asyncio
# Specific Stable Loaders
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)
# Fallback loader (agar upar walon mein se koi na ho)
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from backend.src.services.vector_store.qdrant_adapter import get_vector_store

def get_loader(file_path: str):
    """
    Factory function jo file extension ke hisaab se
    sabse stable loader return karta hai.
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".txt":
        # TextLoader sabse fast aur safe hai
        return TextLoader(file_path, encoding="utf-8")
    
    elif ext == ".pdf":
        # PyPDFLoader pure python hai, hang nahi hota
        return PyPDFLoader(file_path)
    
    elif ext == ".csv":
        return CSVLoader(file_path, encoding="utf-8")
    
    elif ext in [".doc", ".docx"]:
        # Docx2txtLoader light hai
        return Docx2txtLoader(file_path)
    
    elif ext == ".md":
        # Markdown ko hum TextLoader se bhi parh sakte hain agar Unstructured tang kare
        return TextLoader(file_path, encoding="utf-8")
    
    else:
        # Agar koi ajeeb format ho, tab hum Heavy 'Unstructured' loader try karenge
        print(f"INFO: Unknown format '{ext}', attempting to use UnstructuredFileLoader...")
        return UnstructuredFileLoader(file_path)

async def process_file(file_path: str, session_id: str):
    """
    Processes a single uploaded file and adds it to the Vector DB.
    Supports: TXT, PDF, CSV, DOCX, MD and others.
    """
    print(f"INFO: [Ingestion] Starting processing for file: {file_path}")
    
    try:
        # 1. Sahi Loader select karein
        loader = get_loader(file_path)
        
        # 2. File Load karein (Thread mein taake server block na ho)
        # Note: 'aload()' har loader ke paas nahi hota, isliye hum standard 'load()' ko async wrap karte hain
        docs = await asyncio.to_thread(loader.load)
        
    except Exception as e:
        print(f"ERROR: [Ingestion] Failed to load file {file_path}: {e}")
        return 0
    
    if not docs:
        print(f"WARNING: [Ingestion] Could not extract any content from {file_path}")
        return 0

    # 3. Document ko chunks mein todein
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    split_docs = text_splitter.split_documents(docs)
    
    # Metadata update (Source tracking ke liye)
    for doc in split_docs:
        doc.metadata["session_id"] = session_id
        doc.metadata["file_name"] = os.path.basename(file_path)
        # Extension bhi store kar lete hain filter karne ke liye
        doc.metadata["file_type"] = os.path.splitext(file_path)[1].lower()

    # 4. Qdrant mein upload karein
    try:
        vector_store = get_vector_store()
        await vector_store.aadd_documents(split_docs)
        print(f"SUCCESS: [Ingestion] Processed {len(split_docs)} chunks from {file_path}")
        return len(split_docs)
    except Exception as e:
        print(f"ERROR: [Ingestion] Failed to upload to Qdrant: {e}")
        return 0