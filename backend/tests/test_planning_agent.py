"""
Tests for the Gemini-backed Planning Agent (Phase 5).

Only app.rag.gemini_client.generate_json() actually calls the network, so
everything else here — prompt building, response parsing/validation, and
PlanningAgent.run()'s wiring — is tested without a real Gemini call, by
monkeypatching that one function or (for the "not configured" case)
relying on the real, unconfigured settings.gemini_api_key in this test
environment.
"""

import json

import pytest

from app.agents.planning_agent import PlanningAgent, _build_prompt, _parse_response
from app.rag.gemini_client import GeminiNotConfiguredError

VALID_RESPONSE = {
    "problem_understanding": "The team needs to detect crop disease from images.",
    "tech_stack": ["Python", "TensorFlow", "React"],
    "architecture": "A mobile app uploads images to a Flask API that runs a CNN model.",
    "roadmap": [
        {"phase": "Research", "tasks": ["Survey datasets", "Pick a model architecture"], "milestones": ["Dataset chosen"]},
        {"phase": "MVP", "tasks": ["Train baseline model", "Build upload UI"], "milestones": []},
        {"phase": "Polish", "tasks": ["Improve accuracy", "Add demo mode"], "milestones": ["Demo works offline"]},
    ],
    "deliverables": ["Working demo", "Slide deck"],
}


def test_build_prompt_includes_problem_statement():
    prompt = _build_prompt("Detect crop disease from leaf images using computer vision.")
    assert "Detect crop disease from leaf images using computer vision." in prompt
    assert "roadmap" in prompt  # the required JSON shape is documented in the prompt


def test_build_prompt_tells_gemini_existing_solutions_are_not_live_research():
    prompt = _build_prompt("Detect crop disease from leaf images using computer vision.")
    assert "existing_solutions" in prompt
    assert "differentiation_ideas" in prompt
    assert "cannot browse the web" in prompt
    assert "do not invent a plausible-sounding name" in prompt


def test_parse_response_accepts_well_formed_json():
    result = _parse_response(json.dumps(VALID_RESPONSE))
    assert result["problem_understanding"] == VALID_RESPONSE["problem_understanding"]
    assert len(result["roadmap"]) == 3
    assert result["roadmap"][1]["milestones"] == []  # defaulted, was omitted-equivalent
    # VALID_RESPONSE omits these — must default to [] / None, never fabricated.
    assert result["existing_solutions"] == []
    assert result["differentiation_ideas"] == []
    assert result["feasibility"] is None
    assert result["advantages"] == []
    assert result["scalability"] is None
    assert result["cost_effectiveness"] is None


def test_parse_response_passes_through_existing_solutions_and_differentiation_ideas():
    with_new_fields = {
        **VALID_RESPONSE,
        "existing_solutions": ["Plantix", "PlantVillage Nuru"],
        "differentiation_ideas": ["Offline-first inference for low-connectivity farms"],
    }
    result = _parse_response(json.dumps(with_new_fields))
    assert result["existing_solutions"] == ["Plantix", "PlantVillage Nuru"]
    assert result["differentiation_ideas"] == ["Offline-first inference for low-connectivity farms"]


def test_parse_response_passes_through_feasibility_analysis():
    with_new_fields = {
        **VALID_RESPONSE,
        "feasibility": "Buildable in a hackathon with an off-the-shelf CNN, given labeled data is available.",
        "advantages": ["Works offline once the model is downloaded"],
        "scalability": "Could extend to more crop types with additional training data.",
        "cost_effectiveness": "Free-tier hosting is enough for a demo; production would need paid inference compute.",
    }
    result = _parse_response(json.dumps(with_new_fields))
    assert result["feasibility"] == with_new_fields["feasibility"]
    assert result["advantages"] == ["Works offline once the model is downloaded"]
    assert result["scalability"] == with_new_fields["scalability"]
    assert result["cost_effectiveness"] == with_new_fields["cost_effectiveness"]


def test_parse_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        _parse_response("this is not json at all {{{")


def test_parse_response_rejects_missing_required_keys():
    incomplete = {k: v for k, v in VALID_RESPONSE.items() if k != "roadmap"}
    with pytest.raises(ValueError, match="missing required key"):
        _parse_response(json.dumps(incomplete))


def test_parse_response_rejects_empty_roadmap():
    bad = {**VALID_RESPONSE, "roadmap": []}
    with pytest.raises(ValueError, match="non-empty list"):
        _parse_response(json.dumps(bad))


def test_parse_response_rejects_malformed_roadmap_phase():
    bad = {**VALID_RESPONSE, "roadmap": [{"phase": "Research"}]}  # missing "tasks"
    with pytest.raises(ValueError, match="malformed roadmap phase"):
        _parse_response(json.dumps(bad))


def test_run_raises_on_empty_problem_statement():
    agent = PlanningAgent()
    with pytest.raises(ValueError, match="must not be empty"):
        agent.run("")


def test_run_raises_gemini_not_configured_when_no_api_key(monkeypatch):
    """
    With GEMINI_API_KEY unset, run() must fail loudly and clearly, not
    silently return a fabricated/generic roadmap. Explicitly monkeypatched
    (rather than relying on ambient env state) so this passes regardless of
    whether a real key is configured in this environment's .env.
    """
    import app.rag.gemini_client as gemini_client_module

    monkeypatch.setattr(gemini_client_module.settings, "gemini_api_key", "")

    agent = PlanningAgent()
    with pytest.raises(GeminiNotConfiguredError, match="GEMINI_API_KEY"):
        agent.run("Build a crop disease detector.")


def test_run_returns_parsed_plan_with_mocked_gemini_call(monkeypatch):
    import app.agents.planning_agent as planning_agent_module

    monkeypatch.setattr(planning_agent_module, "get_gemini_model", lambda: object())
    monkeypatch.setattr(
        planning_agent_module, "generate_json", lambda model, prompt, **kwargs: json.dumps(VALID_RESPONSE)
    )

    agent = PlanningAgent()
    result = agent.run("Build a crop disease detector using computer vision.")

    assert result["tech_stack"] == VALID_RESPONSE["tech_stack"]
    assert len(result["roadmap"]) == 3
    assert result["existing_solutions"] == []
    assert result["differentiation_ideas"] == []
