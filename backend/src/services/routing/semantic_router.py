from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

class SemanticRouter:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SemanticRouter, cls).__new__(cls)
            print("🧠 [Router] Loading Multilingual Embedding Model...")
            # --- CHANGE IS HERE ---
            # Ye model Hindi/Urdu/English sab samajhta hai
            cls._model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ [Router] Multilingual Model Loaded.")
        return cls._instance

    def route(self, query: str, tools_map: dict) -> str | None:
        if not tools_map:
            return None

        tool_names = list(tools_map.keys())
        descriptions = list(tools_map.values())

        # Encode (Query + Descriptions)
        all_texts = [query] + descriptions
        embeddings = self._model.encode(all_texts)

        query_vec = embeddings[0].reshape(1, -1)
        tool_vecs = embeddings[1:]

        # Scores Calculate karo
        scores = cosine_similarity(query_vec, tool_vecs)[0]

        # Debugging Print
        print(f"\n📊 [Router Logic] Query: '{query}'")
        for name, score in zip(tool_names, scores):
            print(f"   🔹 {name}: {score:.4f}")

        best_idx = np.argmax(scores)
        best_score = scores[best_idx]
        best_tool = tool_names[best_idx]

        # --- THRESHOLD ADJUSTMENT ---
        # Hinglish/Multilingual matching ke liye score thoda kam aata hai.
        # Hum 0.05 rakhenge taake agar halka sa bhi match ho to pakad le.
        if best_score < 0.05:
            print(f"⛔ [Router] Score too low ({best_score:.4f} < 0.05). Fallback.")
            return None
        
        return best_tool