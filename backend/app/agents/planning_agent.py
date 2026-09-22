"""
Generates a project roadmap for a selected problem statement, using
Gemini (see app.rag.gemini_client). No hardcoded/generic fallback roadmap
is returned on failure — if Gemini isn't configured or the call fails,
this raises a clear error rather than silently faking a plan (see
app.api.routes.plan for how that error surfaces over HTTP).

Prompt-building and response-parsing are pure functions, separate from the
one line that actually calls Gemini (run_safe... calling
gemini_client.generate_json), so the request/response shape can be
unit-tested without a real network call.

The response also includes existing_solutions/differentiation_ideas —
these come entirely from Gemini's own training knowledge. Gemini cannot
browse the web from here, so this is NOT live-verified competitor
research; it's a knowledgeable starting point the team should verify
themselves. The prompt below instructs Gemini accordingly, and the
frontend (Roadmap.jsx) surfaces the same caveat next to these sections.
"""

from __future__ import annotations

import json
import logging

from app.agents.base_agent import BaseAgent
from app.core.config import settings
from app.core.tracking import PLANNING_AGENT_EXPERIMENT, track_run
from app.rag.gemini_client import generate_json, get_gemini_model

logger = logging.getLogger(__name__)

REQUIRED_KEYS = {"problem_understanding", "tech_stack", "architecture", "roadmap", "deliverables"}

PROMPT_TEMPLATE = """\
You are helping a student team plan a hackathon project. Given the \
problem statement below, produce a practical, realistic project roadmap \
for a small team building this over the course of a hackathon (roughly \
24-48 hours of build time, not a production system).

Problem statement:
\"\"\"
{problem_statement}
\"\"\"

Respond with ONLY a JSON object (no markdown, no commentary) with exactly \
this shape:
{{
  "problem_understanding": "<2-4 sentence plain-language restatement of what the problem is actually asking for>",
  "tech_stack": ["<technology 1>", "<technology 2>", "..."],
  "architecture": "<2-4 sentence plain-language description of the high-level system architecture/components>",
  "roadmap": [
    {{
      "phase": "<phase name, e.g. 'Research', 'MVP', 'Polish'>",
      "tasks": ["<concrete task>", "..."],
      "milestones": ["<concrete, checkable milestone>", "..."]
    }}
  ],
  "deliverables": ["<concrete expected deliverable, e.g. 'working demo', 'slide deck'>", "..."],
  "existing_solutions": ["<a real product, project, or approach you know of that addresses a similar problem>", "..."],
  "differentiation_ideas": ["<a concrete way this team's project could stand out from those existing solutions>", "..."],
  "feasibility": "<2-4 sentence assessment of whether this is realistically buildable by a small student team in a hackathon timeframe, and what the main risks/blockers are>",
  "advantages": ["<a concrete benefit or strength of this project idea>", "..."],
  "scalability": "<2-3 sentence assessment of how this could grow beyond the hackathon MVP — more users, more data, more features>",
  "cost_effectiveness": "<2-3 sentence assessment of the likely cost to build and run this (APIs, infra, hosting) and whether that's reasonable for what it delivers>"
}}

Requirements:
- "roadmap" must have 3 to 5 phases, ordered from first to last.
- Every phase must have at least 2 tasks.
- Be specific to THIS problem statement — do not give generic advice that \
would apply to any hackathon project.
- tech_stack should list actual technology/framework/tool names, not vague \
categories.
- "existing_solutions": list 2-5 solutions from your own training \
knowledge — you cannot browse the web, so do not present this as current \
or verified market research. If you aren't confident a named solution \
still exists or matches, describe the general approach instead of a \
specific product name. An empty list is fine if you genuinely don't know \
of anything relevant — do not invent a plausible-sounding name to fill \
the list.
- "differentiation_ideas": 2-4 concrete ways this team's project could \
meaningfully differ from those existing solutions, grounded in the \
problem statement above — not generic advice like "better UI" or "use AI".
- "advantages": 2-4 concrete strengths specific to this project idea, not \
generic claims.
- "feasibility", "scalability", "cost_effectiveness": grounded, honest \
assessments — it is fine (and expected) to name real risks or limitations \
rather than presenting everything as effortless.
"""


def _build_prompt(problem_statement: str) -> str:
    return PROMPT_TEMPLATE.format(problem_statement=problem_statement.strip())


def _parse_response(text: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {exc}\nRaw response: {text[:500]}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(f"Gemini response is missing required key(s): {sorted(missing)}")

    roadmap = data["roadmap"]
    if not isinstance(roadmap, list) or not roadmap:
        raise ValueError("'roadmap' must be a non-empty list of phases")
    for step in roadmap:
        if not isinstance(step, dict) or "phase" not in step or "tasks" not in step:
            raise ValueError(f"malformed roadmap phase (needs 'phase' and 'tasks'): {step!r}")
        step.setdefault("milestones", [])

    data.setdefault("tech_stack", [])
    data.setdefault("deliverables", [])
    data.setdefault("existing_solutions", [])
    data.setdefault("differentiation_ideas", [])
    data.setdefault("feasibility", None)
    data.setdefault("advantages", [])
    data.setdefault("scalability", None)
    data.setdefault("cost_effectiveness", None)
    return data


class PlanningAgent(BaseAgent):
    """Generates a project roadmap for a selected problem statement."""

    name = "planning_agent"

    def run(self, problem_statement: str) -> dict:
        if not problem_statement or not problem_statement.strip():
            raise ValueError("problem_statement must not be empty")

        with track_run(
            PLANNING_AGENT_EXPERIMENT,
            params={
                "model_name": settings.gemini_model_name,
                "problem_statement_chars": len(problem_statement),
            },
        ) as run:
            model = get_gemini_model()
            prompt = _build_prompt(problem_statement)
            # The default 15s/10s budget in gemini_client.py is tuned for
            # the faster Flash models. On gemini-3.6-flash (in use while on
            # the free tier — see settings.gemini_model_name / .env) a
            # single roadmap's structured JSON output can genuinely take
            # longer than 10s to generate; give it more room rather than
            # failing an otherwise-working request.
            raw_text = generate_json(model, prompt, timeout=45, retry_timeout=40)
            result = _parse_response(raw_text)
            run.log_metric("roadmap_phases", len(result["roadmap"]))
            run.log_metric("tech_stack_size", len(result["tech_stack"]))
            run.log_metric("deliverables_count", len(result["deliverables"]))
            run.log_metric("existing_solutions_count", len(result["existing_solutions"]))
            run.log_metric("differentiation_ideas_count", len(result["differentiation_ideas"]))
            return result
