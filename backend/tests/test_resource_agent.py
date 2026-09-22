"""
Tests for the curated, keyword-based Resource Agent (Phase 6). No network
calls, no LLM — these test the actual tagging + lookup + dedup logic.
"""

from app.agents.resource_agent import MAX_RESOURCES, ResourceAgent
from app.schemas.plan import Resource

VALID_TYPES = {"docs", "repo", "tutorial", "dataset", "tool", "api"}


def test_ai_agriculture_problem_returns_relevant_resources():
    agent = ResourceAgent()
    resources = agent.run(
        "Use AI and machine learning with TensorFlow to predict crop disease "
        "for farmers in rural agriculture regions."
    )
    urls = {r["url"] for r in resources}
    assert resources, "expected at least one resource"
    assert "https://www.tensorflow.org/learn" in urls
    assert any("faostat" in u or "kaggle" in u for u in urls)


def test_blockchain_problem_returns_ethereum_and_solidity_resources():
    agent = ResourceAgent()
    resources = agent.run(
        "Build a blockchain based smart contract system using Solidity for "
        "supply chain transparency."
    )
    urls = {r["url"] for r in resources}
    assert "https://ethereum.org/en/developers/docs/" in urls
    assert "https://docs.soliditylang.org/" in urls


def test_empty_problem_statement_returns_empty_list():
    agent = ResourceAgent()
    assert agent.run("") == []
    assert agent.run("   ") == []


def test_no_keyword_match_returns_empty_list_not_crash():
    agent = ResourceAgent()
    resources = agent.run("Xyzzy plugh wibble frobnicate qux.")
    assert resources == []


def test_results_are_deduplicated_by_url():
    agent = ResourceAgent()
    # "IoT" appears as both a domain and a technology keyword and both map
    # to the same Arduino docs URL in the catalog — must not duplicate.
    resources = agent.run(
        "An IoT based sensor system using Arduino and IoT sensors for smart "
        "irrigation on farms."
    )
    urls = [r["url"] for r in resources]
    assert len(urls) == len(set(urls)), f"expected no duplicate URLs, got {urls}"


def test_results_never_exceed_max_resources_cap():
    agent = ResourceAgent()
    # A problem statement engineered to hit many domains and technologies.
    resources = agent.run(
        "An AI/ML healthcare fintech agriculture blockchain cybersecurity IoT "
        "web application using Python JavaScript React TensorFlow PyTorch "
        "Docker Kubernetes AWS Blockchain Solidity Arduino MongoDB Firebase."
    )
    assert len(resources) <= MAX_RESOURCES


def test_result_shape_matches_resource_schema():
    agent = ResourceAgent()
    resources = agent.run("A React and Node.js web application for students.")
    assert resources, "expected at least one resource"
    for r in resources:
        assert set(r.keys()) == {"title", "url", "type"}
        assert r["type"] in VALID_TYPES
        # Also validate against the actual Pydantic schema used by PlanResponse.
        Resource(**r)
