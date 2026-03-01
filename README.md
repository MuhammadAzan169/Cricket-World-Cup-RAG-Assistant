# 🏏 Cricket World Cup Chatbot

A CLI-based RAG chatbot for ICC Cricket World Cup queries (2003–2023). Uses semantic search with FAISS and AI-powered responses via OpenRouter.

## ✨ Features

- **🤖 AI-Powered Responses**: Uses OpenRouter models for natural, contextual answers
- **🔍 Semantic Search**: FAISS-powered vector search across cricket match data
- **📚 RAG Integration**: Retrieval-Augmented Generation for accurate, sourced responses
- **💬 Interactive CLI**: Command-line interface with conversation history
- **🎯 Cricket-Focused**: Specialized for World Cup data with 20+ years of matches
- **⚡ Local Processing**: Embeddings generated locally (no API costs)

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure OpenRouter
Create a `.env` file with your credentials:
```
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-3-haiku
LLM_API_KEY=sk-or-v1-xxxxxxxxxxxxx
LLM_BASE_URL=https://openrouter.ai/api/v1
LLM_MAX_TOKENS=1500
LLM_TEMPERATURE=0.3
```

### 3. Build the Index (First Time Only)
```bash
python main.py --build-index
```

### 4. Start Chatting
```bash
# Interactive mode
python main.py

# Or ask a single question
python main.py --query "Who won the 2011 World Cup?"
```

## 💻 Usage

### Interactive CLI
```bash
python main.py
```
Commands available:
- `/status` — Show system status
- `/history` — Show chat history from history.txt
- `/clear` — Clear conversation history and delete history.txt
- `/build` — Rebuild embeddings index
- `/help` — Show help
- `/quit` — Exit

### Single Question Mode
```bash
python main.py --query "Which team won the 2019 World Cup?"
```

### System Status
```bash
python main.py --status
```

## 🏗️ Project Structure

```
Cricket World Cup Chatbot/
├── main.py                 # Main chatbot application & CLI
├── embeddings_utils.py     # Embeddings manager & search utilities
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── .env                   # OpenRouter credentials (required)
├── Embedding/             # Core ML components
│   ├── embeddings.py      # Sentence-transformer embeddings
│   ├── vector_store.py    # FAISS vector database
│   ├── chunking.py        # Text chunking engine
│   └── ingestion.py       # Data ingestion pipeline
├── index/                 # FAISS indexes & metadata
│   ├── faiss.index        # Vector index
│   ├── chunks.json        # Text chunks
│   └── metadata.md        # Index information
├── Cricket Data/          # Source datasets
│   ├── cleaned_matches/   # Match JSON files
│   ├── embeddings/        # Text embeddings
│   ├── metadata/          # Tournament data
│   └── statistical_analysis/ # Performance stats
└── __init__.py           # Package initialization
```

## ⚙️ Configuration

### Environment Variables (.env)

All variables are **required** - no fallbacks or defaults:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider name | `openrouter` |
| `LLM_MODEL` | AI model to use | `anthropic/claude-3-haiku` |
| `LLM_API_KEY` | Your OpenRouter API key | `sk-or-v1-...` |
| `LLM_BASE_URL` | API base URL | `https://openrouter.ai/api/v1` |
| `LLM_MAX_TOKENS` | Max response tokens | `1500` |
| `LLM_TEMPERATURE` | Response creativity | `0.3` |

### Supported OpenRouter Models

- `anthropic/claude-3-haiku` (fast, cost-effective)
- `anthropic/claude-3-sonnet` (balanced performance)
- `openai/gpt-4o-mini` (good balance)
- `meta-llama/llama-3.1-8b-instruct` (free tier)

## 🎯 Example Queries

- "Who won the 2011 World Cup?"
- "Compare India's performance in 2003 vs 2023"
- "What were the biggest upsets in World Cup history?"
- "Who scored the most centuries in 2019?"
- "Which bowler took the most wickets in 2015?"

## 🔧 How It Works

1. **Query Processing**: User question → semantic embedding
2. **Vector Search**: FAISS finds most similar cricket data chunks
3. **Context Assembly**: Top chunks combined into coherent context
4. **AI Generation**: OpenRouter model generates natural answer using context
5. **Response**: Accurate, sourced answer returned to user

## 🐛 Troubleshooting

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"API key not found"**
- Check `.env` file exists and has correct values
- Ensure no extra spaces or quotes

**"Knowledge base not initialized"**
- Run `python main.py --build-index` first
- Check that Cricket Data folder exists

**Poor answer quality**
- Try different OpenRouter models
- Check if embeddings index is built
- Verify query is specific to cricket World Cups

## 📈 System Requirements

- **Python**: 3.8+
- **RAM**: 4GB+ (for FAISS index loading)
- **Storage**: ~50MB (for indexes and data)
- **Internet**: Required for OpenRouter API calls

## 📄 License

This project uses cricket data from public ICC sources. AI responses generated using your OpenRouter account.

# Initialize
kb = CricketKB()
kb.initialize()

# Ask questions
answer = kb.ask_question("Who scored the most runs in 2023 World Cup?")
print(answer)

# Get raw context for custom processing
context = kb.get_rag_context("Compare India vs Australia in 2023")
print(context['context_text'])
print("Sources:", context['sources'])
```

### Command Line Interface

```bash
# Ask questions
python main.py "Which team won the 2019 World Cup?"

# Check system status
python main.py --status

# Get help
python main.py
```

### Advanced Usage

```python
# Custom context retrieval
context = kb.get_rag_context("Batting records", top_k=10)

# Access raw components
from Embedding.embeddings import EmbeddingGenerator
embedder = EmbeddingGenerator()
vector = embedder.embed_query("cricket question")
```

## 🏗️ Project Structure

```
Cricket Knowledge Base/
├── main.py                 # Main CricketKB class & CLI
├── __init__.py            # Package exports
├── __main__.py            # Module entry point
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── .env                   # OpenRouter credentials (create this)
├── README.md              # This file
├── Embedding/             # Core ML components
│   ├── embeddings.py      # Sentence-transformer embeddings
│   ├── vector_store.py    # FAISS vector database
│   ├── chunking.py        # Text chunking engine
│   └── ingestion.py       # Data ingestion pipeline
├── index/                 # FAISS indexes & metadata
│   ├── faiss.index        # Vector index
│   ├── chunks.json        # Text chunks
│   └── vectors.json       # Vector mappings
├── Cricket Data/          # Source datasets
│   ├── cleaned_matches/   # 299 match JSONs
│   ├── embeddings/        # Text embeddings
│   ├── metadata/          # Tournament data
│   └── statistical_analysis/ # Performance stats
└── documents/             # Additional documents
```

## 🔧 API Reference

### CricketKB Class

#### Methods

- **`initialize()`**: Load FAISS index and prepare for queries
- **`ask_question(question: str) -> str`**: Get AI-generated answer
- **`get_rag_context(query: str, top_k: int = 5) -> dict`**: Retrieve relevant context
- **`get_status() -> dict`**: Get system status and statistics

#### Context Response Format

```python
{
    "context_text": "Combined text from relevant chunks...",
    "sources": [
        {"file": "2011_tournament_summary.txt", "score": 0.85, "type": "summary"},
        # ... more sources
    ],
    "query": "original query",
    "model": "openrouter model name"
}
```

## ⚙️ Configuration

### Environment Variables (.env)

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | Your OpenRouter API key | `sk-or-v1-...` |
| `OPENROUTER_MODEL` | AI model to use | `anthropic/claude-3-haiku` |

### Supported OpenRouter Models

- `anthropic/claude-3-haiku` (fast, cost-effective)
- `anthropic/claude-3-sonnet` (balanced performance)
- `openai/gpt-4o-mini` (good balance)
- `meta-llama/llama-3.1-8b-instruct` (free tier)
- `microsoft/wizardlm-2-8x22b` (good for cricket analysis)

## 🎯 Example Queries

### Basic Questions
- "Who won the 2011 World Cup?"
- "Which country hosted the 2007 World Cup?"
- "Who was the captain of Australia in 2003?"

### Analytical Questions
- "Compare India's performance in 2003 vs 2023"
- "What were the biggest upsets in World Cup history?"
- "Who scored the most centuries in 2019?"

### Statistical Questions
- "Which bowler took the most wickets in 2015?"
- "What was the highest individual score in 2023?"
- "How many matches did South Africa win in 2011?"

## 🔍 How It Works

1. **Query Processing**: User question → semantic embedding
2. **Vector Search**: FAISS finds most similar cricket data chunks
3. **Context Assembly**: Top chunks combined into coherent context
4. **AI Generation**: OpenRouter model generates natural answer using context
5. **Response**: Accurate, sourced answer returned to user

## 🐛 Troubleshooting

### Common Issues

**"Module not found" errors**
```bash
pip install -r requirements.txt
```

**"API key not found"**
- Check `.env` file exists and has correct values
- Ensure no extra spaces or quotes

**"Knowledge base not initialized"**
```python
kb = CricketKB()
kb.initialize()  # Don't forget this step!
```

**Poor answer quality**
- Try different OpenRouter models
- Check if cricket data is properly indexed
- Verify query is specific to cricket World Cups

### Performance Tips

- Use `top_k=3-5` for faster responses
- Choose smaller models for speed (Haiku, GPT-4o-mini)
- Larger models (Sonnet, GPT-4) give better analysis

## 📈 System Requirements

- **Python**: 3.8+
- **RAM**: 4GB+ (for FAISS index loading)
- **Storage**: ~50MB (for indexes and data)
- **Internet**: Required for OpenRouter API calls

## 🤝 Contributing

The system is designed for cricket Q&A but can be adapted for other domains by:
1. Replacing cricket data with your domain data
2. Re-indexing with `IngestionPipeline`
3. Updating prompts for your use case

## 📄 License

This project uses cricket data from public ICC sources. AI responses generated using your OpenRouter account.

---

**Ready to explore cricket history?** 🏏✨

```bash
python main.py "Tell me about the greatest World Cup moments"
```