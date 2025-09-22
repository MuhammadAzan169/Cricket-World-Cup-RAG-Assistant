# embedding_manager.py
import torch
import numpy as np
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, MODEL_CACHE_DIR, DEVICE

class EmbeddingManager:
    def __init__(self, device_preference: str = DEVICE):
        # prefer GPU if available
        if device_preference == "cuda" and torch.cuda.is_available():
            self.device = "cuda"
            print("✅ Using GPU (CUDA) for embeddings")
        else:
            self.device = "cpu"
            print("⚠️ Using CPU for embeddings")

        self.model = SentenceTransformer(EMBEDDING_MODEL, device=self.device, cache_folder=MODEL_CACHE_DIR)

    def get_embeddings(self, texts, batch_size: int = 128):
        """
        Returns embeddings as numpy.float32 (ready for FAISS).
        Accepts list of texts.
        """
        if not texts:
            return np.zeros((0, self.get_embedding_dimension()), dtype="float32")
        emb = self.model.encode(texts, convert_to_tensor=False, show_progress_bar=True, batch_size=batch_size)
        arr = np.array(emb, dtype="float32")
        return arr

    def get_embedding_dimension(self):
        return self.model.get_sentence_embedding_dimension()
