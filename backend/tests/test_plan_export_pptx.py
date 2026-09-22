"""
HTTP-level test for POST /api/v1/plan/export-pptx — formats a plan the
frontend already has into a downloadable .pptx. Makes no Gemini call (the
plan is passed in, not regenerated), so this needs no mocking of
gemini_client.
"""

import io

from fastapi.testclient import TestClient
from pptx import Presentation

from app.main import app

client = TestClient(app)

PLAN_PAYLOAD = {
    "problem_title": "Crop Disease Detector",
    "problem_statement": "Detect crop disease from leaf images.",
    "source": "sih",
    "hackathon_name": "Smart India Hackathon 2025",
    "plan": {
        "problem_understanding": "Farmers need to detect crop disease early from photos.",
        "tech_stack": ["Python", "TensorFlow"],
        "architecture": "A mobile app uploads photos to an API running a CNN classifier.",
        "roadmap": [{"phase": "MVP", "tasks": ["Train baseline model"], "milestones": []}],
        "deliverables": ["Working demo"],
        "existing_solutions": ["Plantix"],
        "differentiation_ideas": ["Offline-first inference"],
        "feasibility": "Buildable in a hackathon timeframe with a pretrained model.",
        "advantages": ["Works offline"],
        "scalability": "Could extend to more crop types.",
        "cost_effectiveness": "Free-tier hosting covers a demo.",
        "resources": [],
    },
}


def test_export_pptx_returns_a_valid_eight_slide_presentation():
    response = client.post("/api/v1/plan/export-pptx", json=PLAN_PAYLOAD)

    assert response.status_code == 200
    assert response.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    assert "crop-disease-detector" in response.headers["content-disposition"]

    prs = Presentation(io.BytesIO(response.content))
    assert len(prs.slides) == 8
    assert list(prs.slides)[0].shapes.title.text == "Crop Disease Detector"


def test_export_pptx_rejects_a_missing_required_field():
    bad_payload = {k: v for k, v in PLAN_PAYLOAD.items() if k != "plan"}
    response = client.post("/api/v1/plan/export-pptx", json=bad_payload)
    assert response.status_code == 422
