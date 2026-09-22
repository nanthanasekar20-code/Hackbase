from fastapi import APIRouter

from app.schemas.query import QueryRequest, QueryResponse
from app.agents.search_agent import SearchAgent
from app.agents.ranking_agent import RankingAgent

router = APIRouter()

search_agent = SearchAgent()
ranking_agent = RankingAgent()


@router.post("/search", response_model=QueryResponse)
def search(request: QueryRequest):
    """
    Natural-language query -> candidate hackathon problems -> ranked results.
    """
    candidates = search_agent.run(request.query, top_k=request.top_k)
    ranked = ranking_agent.run(query=request.query, candidates=candidates)
    return QueryResponse(query=request.query, results=ranked)
