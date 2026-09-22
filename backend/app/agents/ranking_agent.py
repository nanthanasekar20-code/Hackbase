from app.agents.base_agent import BaseAgent


class RankingAgent(BaseAgent):
    """Scores and re-ranks candidates returned by the Search agent."""

    name = "ranking_agent"

    def run(self, query: str, candidates: list):
        # TODO: replace with LLM-based or learned ranking
        return sorted(candidates, key=lambda c: c.get("score", 0), reverse=True)
