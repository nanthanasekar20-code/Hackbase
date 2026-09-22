from app.agents.base_agent import BaseAgent
from app.core.resource_catalog import DOMAIN_RESOURCES, TECH_RESOURCES
from app.core.taxonomy import extract_technologies, map_domains

MAX_RESOURCES = 8


class ResourceAgent(BaseAgent):
    """
    Surfaces starter docs, repos, tutorials, and datasets for a problem
    statement.

    Per the Phase 1 scoping decision this is a curated, keyword-based
    lookup — no search API, no LLM call. It reuses the same heuristic
    domain/technology tagger the ingestion pipeline uses
    (app.core.taxonomy) to figure out what the problem is about from its
    text, then looks up real, curated resources for each match
    (app.core.resource_catalog). Domain matches are checked first (they
    tend to be the more specific signal for a hackathon problem), then
    technology matches fill in the rest up to MAX_RESOURCES.
    """

    name = "resource_agent"

    def run(self, problem_statement: str):
        if not problem_statement or not problem_statement.strip():
            return []

        domains = map_domains(problem_statement)
        technologies = extract_technologies(problem_statement)

        resources: list[dict] = []
        seen_urls: set[str] = set()

        def _add(resource: dict):
            if resource["url"] in seen_urls or len(resources) >= MAX_RESOURCES:
                return
            seen_urls.add(resource["url"])
            resources.append(resource)

        for domain in domains:
            for resource in DOMAIN_RESOURCES.get(domain, []):
                _add(resource)

        for tech in technologies:
            resource = TECH_RESOURCES.get(tech)
            if resource:
                _add(resource)

        return resources
