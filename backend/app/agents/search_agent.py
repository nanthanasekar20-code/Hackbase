from app.agents.base_agent import BaseAgent
from app.rag.retriever import Retriever


class SearchAgent(BaseAgent):
    """Retrieves candidate hackathon problem statements for a query."""

    name = "search_agent"

    def __init__(self):
        self.retriever = Retriever()

    def run(self, query: str, top_k: int = 10):
        # TODO: replace with real vector search once RAG core is built
        return self.retriever.retrieve(query, top_k=top_k)
