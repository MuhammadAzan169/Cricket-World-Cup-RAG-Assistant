# query_processor.py
from embedding_manager import EmbeddingManager
from vector_store import VectorStore
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
from config import OPENAI_API_BASE, OPENAI_API_KEY, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS

# Create a ChatOpenAI instance pointing at Ollama (OpenAI-compatible)
llm = ChatOpenAI(
    model_name=LLM_MODEL,
    temperature=LLM_TEMPERATURE,
    max_tokens=LLM_MAX_TOKENS,
    openai_api_base=OPENAI_API_BASE,
    openai_api_key=OPENAI_API_KEY,
)

# Prompt template: context will be inserted (pre-built from retrieved chunks)
PROMPT_TMPL = """You are a cricket world-cup expert assistant. Use ONLY the provided CONTEXT to answer the user's question.
Do not hallucinate. If the exact answer is not present, reply exactly:
"I don't have enough information from the available data."

CONTEXT (each section includes source_file and chunk_id for citation):
{context}

USER QUESTION:
{question}

INSTRUCTIONS:
- Answer concisely and cite the chunk(s) you used in square brackets like [file.json#3].
- If multiple chunks are relevant, list them in a parenthetical comma-separated citation.
- Include match details when available (teams, date, venue, scores, players).
- If you provide a numeric/statistical claim, try to include the chunk that contains the statistic.

FINAL ANSWER:
"""

PROMPT = PromptTemplate(input_variables=["context", "question"], template=PROMPT_TMPL)

class QueryProcessor:
    def __init__(self, embedding_manager: EmbeddingManager, vector_store: VectorStore):
        self.embedding_manager = embedding_manager
        self.vector_store = vector_store
        self.llm = llm  # LangChain ChatOpenAI instance

    def process_query(self, query: str, max_results: int = 20) -> str:
        try:
            print(f"Processing query: '{query}'")
            q_emb = self.embedding_manager.get_embeddings([query])[0]
            print("✓ Query embedding generated")

            results = self.vector_store.search(q_emb, max_results)
            print(f"✓ Found {len(results)} relevant results")

            if not results:
                return "I couldn't find relevant match data to answer your question based on the available cricket match information."

            # Build a prioritized context string: include content + short citation header
            context_sections = []
            used_citations = []
            total_len = 0
            # Add top-k results but keep overall context size bounded
            for r in results:
                meta = r["metadata"]
                content = meta.get("content", "")
                citation = f"{meta.get('source_file','unknown')}#{meta.get('chunk_id','?')}"
                # prepare short header
                header = f"[{citation}] Teams: {', '.join(meta.get('teams', []))} | Date: {meta.get('date','')}"
                # include content but truncate to safe size
                CHUNK_PASS_LIMIT = 2000  # characters per chunk passed into prompt
                snippet = content if len(content) <= CHUNK_PASS_LIMIT else content[:CHUNK_PASS_LIMIT] + "\n... (truncated) ..."
                section = f"{header}\n{snippet}"
                context_sections.append(section)
                used_citations.append(citation)
                total_len += len(section)
                # stop if context becomes too long (safety)
                if total_len > 20000:
                    break

            context_text = "\n\n".join(context_sections)

            prompt_input = PROMPT.format(context=context_text, question=query)
            print("Sending prompt to LLM...")
            # Use LangChain's chat model to predict
            response = self.llm.predict(prompt_input)
            return response

        except Exception as e:
            print(f"❌ Error in process_query: {e}")
            return f"I encountered an error while processing your query: {str(e)}. Please try again."
