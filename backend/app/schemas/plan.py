from typing import Literal, Optional

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    problem_statement: str


class RoadmapStep(BaseModel):
    phase: str
    tasks: list[str]
    milestones: list[str] = Field(default_factory=list)


class Resource(BaseModel):
    title: str
    url: str
    type: Literal["docs", "repo", "tutorial", "dataset", "tool", "api"]


class PlanResponse(BaseModel):
    # Optional so the current stub PlanningAgent (which only fills
    # `roadmap`/`resources`) keeps validating during Phase 0/1.
    problem_understanding: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    architecture: Optional[str] = None
    roadmap: list[RoadmapStep]
    deliverables: list[str] = Field(default_factory=list)
    # Gemini's own general knowledge, not live-verified competitor
    # research — it can't browse the web. A starting point for the team
    # to verify themselves, not a market-research substitute. See
    # PlanningAgent's PROMPT_TEMPLATE for the exact instruction given to
    # the model, and Roadmap.jsx for how this caveat is surfaced in the UI.
    existing_solutions: list[str] = Field(default_factory=list)
    differentiation_ideas: list[str] = Field(default_factory=list)
    # Feasibility analysis — same "Gemini's own knowledge, not live-verified
    # research" caveat as existing_solutions/differentiation_ideas above.
    feasibility: Optional[str] = None
    advantages: list[str] = Field(default_factory=list)
    scalability: Optional[str] = None
    cost_effectiveness: Optional[str] = None
    resources: list[Resource]
