# backend/src/services/visual/engine.py

import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image
import numpy as np
from io import BytesIO

# Global variable taake Model sirf ek baar load ho (Memory Bachane ke liye)
_visual_model_instance = None
_preprocess_instance = None

def get_visual_model():
    """
    Singleton Pattern: ResNet50 ko sirf tab load karega jab pehli baar zaroorat hogi.
    Railway/Serverless par RAM bachane ke liye zaroori hai.
    """
    global _visual_model_instance, _preprocess_instance
    
    if _visual_model_instance is None:
        print("👁️ [Visual Engine] Loading ResNet50 AI Model...")
        # 1. Load Standard ResNet50
        full_model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        full_model.eval() # Inference mode (Training off)
        
        # 2. Remove the last Classification Layer
        # Humein "Cat/Dog" label nahi chahiye, humein features (vectors) chahiye.
        _visual_model_instance = torch.nn.Sequential(*(list(full_model.children())[:-1]))
        
        # 3. Define Image Preprocessing steps
        _preprocess_instance = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        print("✅ [Visual Engine] Model Loaded Successfully.")
        
    return _visual_model_instance, _preprocess_instance

def get_image_embedding(image_bytes: bytes) -> list:
    """
    Image ke bytes leta hai -> ResNet50 se guzarta hai -> 2048 numbers ki list wapis karta hai.
    """
    model, preprocess = get_visual_model()
    
    try:
        # 1. Convert Bytes to Image
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
        
        # 2. Preprocess
        img_tensor = preprocess(img)
        batch_img_tensor = torch.unsqueeze(img_tensor, 0) # Batch dimension add karein
        
        # 3. Generate Embedding
        with torch.no_grad():
            embedding = model(batch_img_tensor)
        
        # 4. Flatten & Normalize (Cosine Similarity ke liye zaroori)
        embedding_np = embedding.flatten().numpy()
        norm = np.linalg.norm(embedding_np)
        
        # Zero division se bachne ke liye
        if norm == 0:
            return embedding_np.tolist()
            
        normalized_embedding = (embedding_np / norm).astype('float32')
        
        return normalized_embedding.tolist()
        
    except Exception as e:
        print(f"❌ [Visual Engine] Error processing image: {e}")
        return None