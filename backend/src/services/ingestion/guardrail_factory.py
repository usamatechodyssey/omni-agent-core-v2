from sentence_transformers import CrossEncoder
import asyncio
import os

# Global Cache for Singleton Pattern
_model_instance = None

def get_guardrail_model():
    """
    Skill: AI Guardrail Loader. Loads model into RAM only once.
    Optimized for SaaS performance.
    """
    global _model_instance
    if _model_instance is None:
        # Railway RAM optimization: Agar heavy model crash kare, toh TinyBERT use karein
        # Default: nli-distilroberta-base
        model_name = os.getenv("GUARDRAIL_MODEL", "cross-encoder/nli-distilroberta-base")
        
        print(f"⏳ [AI-Guardrail] Loading Model: {model_name}...")
        try:
            _model_instance = CrossEncoder(model_name)
            print("✅ [AI-Guardrail] Model ready for inference.")
        except Exception as e:
            print(f"❌ [AI-Guardrail] Failed to load model: {e}")
            raise e
            
    return _model_instance

async def predict_with_model(text: str, label: str):
    """
    Skill: Asynchronous AI Prediction.
    Ensures that heavy CPU tasks don't block the FastAPI event loop.
    """
    try:
        model = get_guardrail_model()
        
        # Heavy computation offloaded to a separate thread (Non-blocking SaaS)
        scores = await asyncio.to_thread(model.predict, [(text, label)])
        
        # Returning only the score list
        return scores[0]
    except Exception as e:
        print(f"⚠️ [AI-Guardrail] Prediction Error: {e}")
        # Default score return (Neutral/Allow) in case of error to keep ingestion running
        return [0.0, 0.0, 0.0]