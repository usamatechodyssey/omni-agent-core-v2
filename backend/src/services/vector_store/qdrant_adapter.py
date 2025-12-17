
import qdrant_client
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore
from backend.src.core.config import settings
from backend.src.services.embeddings.factory import get_embedding_model
from typing import Optional, Dict

# @lru_cache() HATA DIYA - We can't cache user-specific connections
def get_vector_store(credentials: Optional[Dict[str, str]] = None):
    """
    Dynamic Vector Store Connector.
    1. Agar 'credentials' hain, to unhein use karega (User's Cloud Qdrant).
    2. Agar nahi, to global settings use karega (Fallback/Admin).
    """
    embedding_model = get_embedding_model() # Ye local hai, isko keys nahi chahiye
    
    # --- DYNAMIC CONFIGURATION LOGIC ---
    if credentials:
        # User-specific Cloud settings
        qdrant_url = credentials.get("url")
        qdrant_api_key = credentials.get("api_key")
        collection_name = credentials.get("collection_name", "user_default_collection")
    else:
        # Global fallback settings
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = settings.QDRANT_API_KEY
        collection_name = settings.QDRANT_COLLECTION_NAME

    if not qdrant_url:
        raise ValueError("Qdrant URL is not configured for this user or globally.")

    print(f"INFO: [VectorDB] Connecting to Qdrant at '{qdrant_url}'...")
    
    # 1. Qdrant Client banayen (User ki keys ke sath)
    client = QdrantClient(
        url=qdrant_url,
        api_key=qdrant_api_key,
    )

    # 2. CHECK: Kya Collection exist karti hai?
    # Hum 'try-except' use karenge taake connection errors bhi pakde jayen
    try:
        # collection_exists is deprecated, use get_collection instead
        client.get_collection(collection_name=collection_name)
        print(f"INFO: [VectorDB] Collection '{collection_name}' already exists.")
    except Exception as e:
        # Agar error "Not found" hai, to collection banayenge
        if "404" in str(e) or "Not found" in str(e):
            print(f"INFO: Collection '{collection_name}' not found. Creating it now...")
            
            # Embedding size pata karna
            dummy_embedding = embedding_model.embed_query("test")
            vector_size = len(dummy_embedding)
            
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"SUCCESS: Created collection '{collection_name}' with vector size {vector_size}.")
        else:
            # Koi aur error (e.g., connection refused)
            raise ConnectionError(f"Failed to connect or access Qdrant: {e}")

    # 3. Vector Store object bana kar return karein
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=embedding_model,
        content_payload_key="page_content",
        metadata_payload_key="metadata"
    )

    return vector_store