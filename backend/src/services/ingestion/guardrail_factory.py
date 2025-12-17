from sentence_transformers import CrossEncoder
from functools import lru_cache
import asyncio

# Global Cache
_model_instance = None

def get_guardrail_model():
    """
    Model ko sirf ek baar load karega.
    """
    global _model_instance
    if _model_instance is None:
        print("⏳ INFO: Loading AI Guardrail Model into RAM (First Time Only)...")
        # 'nli-distilroberta-base' thoda heavy hai, agar PC slow hai to 'cross-encoder/ms-marco-TinyBERT-L-2' use karein
        _model_instance = CrossEncoder('cross-encoder/nli-distilroberta-base')
        print("✅ INFO: AI Guardrail Model Loaded!")
    return _model_instance

async def predict_with_model(text, label):
    """
    Prediction ko background thread mein chalata hai taake server hang na ho.
    """
    model = get_guardrail_model()
    
    # Ye line magic hai: Heavy kaam ko alag thread mein bhej do
    scores = await asyncio.to_thread(model.predict, [(text, label)])
    return scores[0]