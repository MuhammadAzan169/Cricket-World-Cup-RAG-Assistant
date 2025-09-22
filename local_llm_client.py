# local_llm_client.py
from openai import OpenAI
from config import OPENAI_BASE_URL, OPENAI_API_KEY, LLM_MODEL

class LocalLLMClient:
    def __init__(self):
        # Works with Ollama or any OpenAI-compatible local server
        self.client = OpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=OPENAI_API_KEY,
        )
        self.model = LLM_MODEL

    def generate_response(self, query: str, context: str) -> str:
        prompt = self._build_prompt(query, context)
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a cricket expert assistant. Answer questions "
                            "based only on the provided match data. Be specific about dates, "
                            "teams, scores, and players. If the answer is not in the context, say "
                            "\"I don't have enough information from the available data.\""
                        )
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            return completion.choices[0].message.content
        except Exception as e:
            # return the error string so the caller can see what happened
            return f"Error generating response: {str(e)}"

    def _build_prompt(self, query, context):
        return (
            "Based on the following cricket World Cup data (2003–2023), answer the question.\n\n"
            f"CONTEXT:\n{context}\n\n"
            f"QUESTION: {query}\n\n"
            "INSTRUCTIONS:\n"
            "1) Answer ONLY from the context.\n"
            "2) Mention match details (teams, scores, dates, venues, players) if available.\n"
            "3) If not answerable, reply exactly: I don't have enough information from the available data.\n"
            "4) Be concise but specific.\n\n"
            "ANSWER:"
        )
