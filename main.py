# main.py
import os
import time
from data_processor import DataProcessor
from embedding_manager import EmbeddingManager
from vector_store import VectorStore
from query_processor import QueryProcessor
from config import DATA_DIR

def initialize_system():
    print("Initializing Cricket RAG System...")

    if not os.path.exists(DATA_DIR):
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    # Load JSON files
    dp = DataProcessor()
    dp.load_json_files()
    if not dp.matches_data:
        raise ValueError("No match data loaded. Place your JSON files in DATA_DIR.")

    # Create text chunks
    dp.create_chunks()
    chunks, metadata = dp.get_chunks()
    if not chunks:
        raise ValueError("No chunks created from the dataset.")

    # Initialize embedding manager and vector store
    em = EmbeddingManager()
    dim = em.get_embedding_dimension()
    vs = VectorStore(dim)

    if not vs.load_index():
        print("Generating embeddings for chunks...")
        t0 = time.time()
        embeddings = em.get_embeddings(chunks, batch_size=64)
        print(f"Embeddings generated in {time.time() - t0:.2f}s")

        # Attach content explicitly to metadata
        for i, m in enumerate(metadata):
            if "content" not in m:
                m["content"] = chunks[i]

        vs.create_index(embeddings, metadata)
        vs.save_index()
    else:
        print("Loaded existing FAISS index")

    qp = QueryProcessor(em, vs)
    return qp

def interactive_mode(qp: QueryProcessor):
    print("\nCricket RAG System Ready. Type your question or 'quit' to exit.\n")
    while True:
        try:
            query = input("Your question: ").strip()
            if query.lower() in ("quit", "exit", "q"):
                print("Exiting...")
                break
            if not query:
                continue

            t0 = time.time()
            ans = qp.process_query(query, max_results=60)
            print(f"\nAnswer (took {time.time() - t0:.2f}s):\n{ans}\n")
        except KeyboardInterrupt:
            print("\nInterrupted by user. Exiting...")
            break
        except Exception as e:
            print(f"Error processing query: {e}")

def main():
    try:
        qp = initialize_system()
        interactive_mode(qp)
    except Exception as e:
        print(f"Initialization failed: {e}")

if __name__ == "__main__":
    main()
