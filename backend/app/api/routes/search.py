from fastapi import APIRouter, Depends

from app.api.deps import get_optional_user
from app.models.user import User
from app.schemas.query import QueryRequest, QueryResponse
from app.agents.search_agent import SearchAgent
from app.agents.ranking_agent import RankingAgent

router = APIRouter()

search_agent = SearchAgent()
ranking_agent = RankingAgent()


@router.post("/search", response_model=QueryResponse)
def search(request: QueryRequest, current_user: User | None = Depends(get_optional_user)):
    """
    Natural-language query -> candidate hackathon problems -> ranked results.

    Never requires login — get_optional_user returns None for an
    anonymous/invalid-token caller, same as today. Personalization (see
    app.rag.retriever.Retriever.retrieve) only activates for a logged-in
    user who has actually set interests/skill_level on their profile; an
    anonymous caller, or a logged-in one who never touched Profile's
    optional preferences, gets identical candidates/order to before this
    existed.
    """
    interests = current_user.interests if current_user else None
    skill_level = current_user.skill_level if current_user else None
    candidates = search_agent.run(request.query, top_k=request.top_k, interests=interests, skill_level=skill_level)
    ranked = ranking_agent.run(query=request.query, candidates=candidates)
    return QueryResponse(query=request.query, results=ranked)
