import logging

from fastapi import APIRouter, HTTPException

from app.rag.gemini_client import GeminiNotConfiguredError, GeminiUnavailableError
from app.schemas.plan import PlanRequest, PlanResponse
from app.agents.planning_agent import PlanningAgent
from app.agents.resource_agent import ResourceAgent

logger = logging.getLogger(__name__)

router = APIRouter()

planning_agent = PlanningAgent()
resource_agent = ResourceAgent()


@router.post("/plan", response_model=PlanResponse)
def generate_plan(request: PlanRequest):
    """
    Selected problem statement -> project roadmap + starter resources.

    The roadmap comes from Gemini (see app.agents.planning_agent) — if it
    isn't configured or the call fails, this returns a clear HTTP error
    rather than a fabricated/generic roadmap. Resources are unaffected
    (the Resource Agent doesn't depend on Gemini).

    PPT export lives at GET /favorites/{problem_id}/export-pptx now, not
    here — it needs this plan already saved to a favorite (so the PPT can
    be cached and re-served instead of rebuilt on every download); see
    app/api/routes/favorites.py.
    """
    try:
        plan = planning_agent.run(request.problem_statement)
    except GeminiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except GeminiUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        # Empty problem_statement, or Gemini returned something we
        # couldn't parse into a valid plan.
        raise HTTPException(status_code=502, detail=f"Could not generate a roadmap: {exc}") from exc
    except Exception as exc:  # network error, rate limit, etc.
        logger.exception("planning_agent.run failed")
        raise HTTPException(status_code=502, detail=f"Roadmap generation failed: {exc}") from exc

    resources = resource_agent.run(request.problem_statement)
    return PlanResponse(**plan, resources=resources)
