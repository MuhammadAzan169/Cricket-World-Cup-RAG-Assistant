# vector_store.py
import faiss
import numpy as np
import pickle
import os
from config import INDEX_PATH

class VectorStore:
    def __init__(self, dimension: int):
        self.dimension = dimension
        self.index = None
        self.metadata = []

    def create_index(self, embeddings, metadata):
        if embeddings is None or len(embeddings) == 0:
            raise ValueError("No embeddings provided")
        embeddings_np = np.array(embeddings, dtype="float32")
        cpu_index = faiss.IndexFlatL2(self.dimension)
        try:
            # If GPU available, convert; else keep CPU
            if faiss.get_num_gpus() > 0:
                res = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(res, 0, cpu_index)
                print("✅ Using GPU FAISS index")
            else:
                self.index = cpu_index
                print("⚠️ Using CPU FAISS index")
        except Exception as e:
            print(f"FAISS GPU init error: {e}; using CPU index")
            self.index = cpu_index

        self.index.add(embeddings_np)
        self.metadata = metadata
        print(f"✅ FAISS index created with {len(embeddings_np)} vectors")

    def search(self, query_embedding, k: int = 20):
        if self.index is None:
            raise ValueError("Index not initialized")
        try:
            q = np.array(query_embedding, dtype="float32")
        except Exception:
            q = query_embedding.detach().cpu().numpy().astype("float32")
        if q.ndim == 1:
            q = q.reshape(1, -1)
        k = min(k, max(1, int(self.index.ntotal)))
        distances, indices = self.index.search(q, k)
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            results.append({"content": meta.get("content",""), "metadata": meta, "distance": float(distances[0][i])})
        return results

    def save_index(self):
        # Convert GPU index to CPU for saving
        try:
            cpu_index = faiss.index_gpu_to_cpu(self.index) if hasattr(faiss, "index_gpu_to_cpu") and self.index is not None and faiss.get_num_gpus()>0 else self.index
        except Exception:
            cpu_index = self.index
        faiss.write_index(cpu_index, f"{INDEX_PATH}.faiss")
        with open(f"{INDEX_PATH}_metadata.pkl", "wb") as f:
            pickle.dump(self.metadata, f)
        print(f"💾 Index saved to {INDEX_PATH}.faiss")

    def load_index(self) -> bool:
        idx_path = f"{INDEX_PATH}.faiss"
        meta_path = f"{INDEX_PATH}_metadata.pkl"
        if os.path.exists(idx_path) and os.path.exists(meta_path):
            self.index = faiss.read_index(idx_path)
            with open(meta_path, "rb") as f:
                self.metadata = pickle.load(f)
            print(f"✅ Loaded existing index with {self.index.ntotal} vectors")
            return True
        return False
