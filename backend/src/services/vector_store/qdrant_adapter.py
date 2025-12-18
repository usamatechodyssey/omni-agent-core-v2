# backend/src/services/vector_store/qdrant_adapter.py
from qdrant_client import QdrantClient
from qdrant_client.http import models
from langchain_qdrant import QdrantVectorStore
from backend.src.services.embeddings.factory import get_embedding_model
from typing import Dict

def get_vector_store(credentials: Dict[str, str]):
    """
    Strict SaaS Vector Store Connector.
    NO GLOBAL FALLBACK. User MUST provide their own Cloud Qdrant.
    """
    if not credentials or not credentials.get("url"):
        # Yeh error seedha user ko dikhayi dega
        raise ValueError("Database Connection Missing: Please connect your Qdrant Cloud in 'User Settings' first.")

    qdrant_url = credentials.get("url")
    qdrant_api_key = credentials.get("api_key")
    collection_name = credentials.get("collection_name", "user_default_collection")

    # Cloud Check: Ensure HTTPS
    if "cloud.qdrant.io" in qdrant_url and not qdrant_url.startswith("https://"):
        qdrant_url = f"https://{qdrant_url}"

    print(f"📡 [VectorDB] Strictly connecting to User Database: {qdrant_url}")
    
    try:
        client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=30)
        
        # Collection check/create logic
        try:
            client.get_collection(collection_name=collection_name)
        except Exception:
            print(f"Creating new collection: {collection_name}")
            embedding_model = get_embedding_model()
            vector_size = len(embedding_model.embed_query("test"))
            client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
            )

        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=get_embedding_model(),
            content_payload_key="page_content",
            metadata_payload_key="metadata"
        )
    except Exception as e:
        raise ConnectionError(f"Qdrant Connection Failed: {str(e)}")