<h1 align="center">🏏 Cricket World Cup RAG Assistant</h1>
<p align="center">
  <b>Retrieval-Augmented Generation (RAG) system for Cricket World Cups (2003–2023)</b>  
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-blue?logo=python" />
  <img src="https://img.shields.io/badge/FAISS-Vector%20DB-green?logo=facebook" />
  <img src="https://img.shields.io/badge/LLM-Ollama%20%7C%20OpenAI-orange?logo=openai" />
  <img src="https://img.shields.io/badge/Embeddings-SBERT-purple?logo=pytorch" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" />
</p>

---

## 📖 Overview
The **Cricket World Cup RAG Assistant** is a Python-based project that answers natural language queries about Cricket World Cups (2003–2023).  
It uses **vector search (FAISS)** + **SentenceTransformers embeddings** + a **local/remote LLM** to retrieve match details and generate factual, context-grounded answers.

✨ **Example:**  
> ❓ *Who won the 2011 World Cup final?*  
> ✅ *India defeated Sri Lanka by 6 wickets on April 2, 2011, at Wankhede Stadium, Mumbai.*  

---

## ✨ Features
- ⚡ Fast vector search with **FAISS**
- 🧠 Contextual embeddings via **SentenceTransformers**
- 🤖 Works with **Ollama, GPT, or any OpenAI-compatible LLM**
- 📂 Query **real cricket JSON datasets (2003–2023)**
- 🛑 Zero-hallucination design → answers only from context

---

## 📂 Project Structure
```bash
Cricket-RAG/
│── app.py                 # (Optional) Flask/FastAPI app for web use
│── main.py                # CLI entrypoint
│── data_processor.py       # Loads & chunks cricket JSON files
│── embedding_manager.py    # Embedding generation
│── query_processor.py      # Retrieval + prompting
│── vector_store.py         # FAISS vector DB
│── local_llm_client.py     # Local LLM API client (Ollama/OpenAI)
│── question_generator.py   # Practice query generator
│── config_template.py      # Safe config template (no secrets)
│── requirements.txt        # Dependencies
│── README.md               # This file
