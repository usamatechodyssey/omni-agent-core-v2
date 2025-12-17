# backend/src/services/embeddings/factory.py
from langchain_community.embeddings import (
    SentenceTransformerEmbeddings,
    OpenAIEmbeddings,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.src.core.config import settings
from functools import lru_cache
from langchain_huggingface import HuggingFaceEmbeddings

# Ye function cache karega, taake model baar baar load na ho
@lru_cache()
def get_embedding_model():
    """
    Ye hamari "Embedding Factory" hai.
    Ye config file ko padhti hai aur sahi embedding model load karti hai.
    Modular design ka ye sabse ahem hissa hai.
    """
    provider = settings.EMBEDDING_PROVIDER.lower()
    model_name = settings.EMBEDDING_MODEL_NAME

    print(f"INFO: Loading embedding model from provider: '{provider}' using model '{model_name}'")

    if provider == "local":
        # Ye model local computer par chalta hai. Koi API key nahi chahiye.
        return HuggingFaceEmbeddings(
            model_name=model_name,
            # cache_folder="./models_cache" # Uncomment if you want to specify a cache folder
        )

    elif provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ValueError("OpenAI API key not found in .env file")
        return OpenAIEmbeddings(
            model=model_name, 
            openai_api_key=settings.OPENAI_API_KEY
        )

    elif provider == "google":
        if not settings.GOOGLE_API_KEY:
            raise ValueError("Google API key not found in .env file")
        return GoogleGenerativeAIEmbeddings(
            model=model_name,
            google_api_key=settings.GOOGLE_API_KEY,
            task_type="retrieval_document" 
        )
    else:
        raise ValueError(f"Unsupported embedding provider: {provider}")