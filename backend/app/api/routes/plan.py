import logging
import re

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.rag.gemini_client import GeminiNotConfiguredError, GeminiUnavailableError
from app.schemas.plan import PlanRequest, PlanResponse, PptxExportRequest
from app.agents.planning_agent import PlanningAgent
from app.agents.resource_agent import ResourceAgent
from app.services.pptx_builder import build_pptx

logger = logging.getLogger(__name__)

router = APIRouter()

planning_agent = PlanningAgent()
resource_agent = ResourceAgent()

PPTX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


@router.post("/plan", response_model=PlanResponse)
def generate_plan(request: PlanRequest):
    """
    Selected problem statement -> project roadmap + starter resources.

    The roadmap comes from Gemini (see app.agents.planning_agent) — if it
    isn't configured or the call fails, this returns a clear HTTP error
    rather than a fabricated/generic roadmap. Resources are unaffected
    (the Resource Agent doesn't depend on Gemini).
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


@router.post("/plan/export-pptx")
def export_plan_pptx(request: PptxExportRequest):
    """
    Formats a plan the frontend already has (from a prior POST /plan) into
    a downloadable .pptx — see app.services.pptx_builder. Deliberately
    takes the plan as input rather than re-running the Planning Agent, so
    exporting costs no additional Gemini calls.
    """
    buffer = build_pptx(
        problem_title=request.problem_title,
        problem_statement=request.problem_statement,
        plan=request.plan.model_dump(),
        source=request.source,
        hackathon_name=request.hackathon_name,
    )
    filename = re.sub(r"[^A-Za-z0-9]+", "-", request.problem_title).strip("-").lower() or "roadmap"
    return StreamingResponse(
        buffer,
        media_type=PPTX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}.pptx"'},
    )
