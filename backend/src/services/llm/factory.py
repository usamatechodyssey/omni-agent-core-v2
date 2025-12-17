
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from backend.src.core.config import settings

def get_llm_model(credentials: dict = None):
    """
    True Universal Factory (Fixed).
    Ab ye provider ke hisaab se sahi 'base_url' set karega.
    """
    
    # --- Default settings (Fallback) ---
    llm_provider = settings.LLM_PROVIDER.lower()
    llm_model_name = settings.LLM_MODEL_NAME
    llm_base_url = settings.LLM_BASE_URL
    llm_api_key = settings.LLM_API_KEY
    google_api_key = settings.GOOGLE_API_KEY

    # --- User-specific settings (Override) ---
    if credentials:
        # User ki settings use karo
        llm_provider = credentials.get("provider", llm_provider).lower()
        llm_model_name = credentials.get("model_name", llm_model_name)
        llm_base_url = credentials.get("base_url", llm_base_url)
        llm_api_key = credentials.get("api_key", llm_api_key)
        
        # Google ke liye
        if llm_provider == "google":
            google_api_key = llm_api_key
            
    # --- MAGIC FIX: Set Base URL for known providers ---
    if llm_provider == "groq" and not llm_base_url:
        llm_base_url = "https://api.groq.com/openai/v1"
        # Groq key .env se le lo agar user ne nahi di (fallback)
        llm_api_key = llm_api_key or settings.GROQ_API_KEY
        
    print(f"🤖 Loading AI Model: {llm_provider} -> {llm_model_name}")

    # --- BLOCK 1: GOOGLE GEMINI ---
    if llm_provider == "google":
        if not google_api_key:
            raise ValueError("Google API key not found.")
        return ChatGoogleGenerativeAI(
            model=llm_model_name,
            google_api_key=google_api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )

    # --- BLOCK 2: UNIVERSAL OPENAI-COMPATIBLE ---
    # Ye block Groq, OpenAI, Ollama, etc. sabko handle karega
    else:
        if not llm_api_key and "localhost" not in (llm_base_url or ""):
             print("⚠️ WARNING: No API Key provided for LLM. Trying global fallback.")
             # Fallback to global keys
             if settings.OPENAI_API_KEY and llm_provider == "openai":
                 llm_api_key = settings.OPENAI_API_KEY
             
        print(f"   -> Endpoint URL: {llm_base_url or 'Default OpenAI'}")
        
        return ChatOpenAI(
            model_name=llm_model_name,
            api_key=llm_api_key or "dummy-key",
            openai_api_base=llm_base_url,
            temperature=0.7
        )