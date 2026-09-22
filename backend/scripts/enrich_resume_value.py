"""
Phase 2: one-time Gemini enrichment pass that scores every problem in
data/processed/problems.json on three metrics (each 0-10):

    resume_value_score       - how good a portfolio/resume project this is
    industry_relevance_score - how relevant to real industry needs today
    technical_depth_score    - how much genuine technical depth it requires

Computed ONCE per problem at ingestion time (not per search query), based
on the problem's technical depth, industry relevance, technologies/skills
involved, real-world impact, uniqueness, and portfolio value. This is
deliberately NOT a resume upload/parsing feature — it's an estimate of a
project's portfolio value, independent of any individual user.

Run as: python scripts/enrich_resume_value.py [--force] [--batch-size N]

Idempotent by default: problems that already have a resume_value_score are
skipped, so re-running after `python scripts/build_corpus.py` regenerates
data/processed/problems.json only spends API calls on the new/changed
records (--force re-scores everything).

Requires GEMINI_API_KEY (see .env.example / app/rag/gemini_client.py).
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from app.core.tracking import RESUME_VALUE_ENRICHMENT_EXPERIMENT, track_run
from app.rag.gemini_client import generate_json, get_gemini_model

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# scripts/enrich_resume_value.py -> parents[1] = <project_root>/backend ->
# need parents[2] to reach <project_root> (scripts/, backend/, root).
ROOT = Path(__file__).resolve().parents[2]
PROCESSED_PATH = ROOT / "data" / "processed" / "problems.json"

DEFAULT_BATCH_SIZE = 8
SCORE_FIELDS = ("resume_value_score", "industry_relevance_score", "technical_depth_score")

PROMPT_TEMPLATE = """\
You are evaluating hackathon problem statements for how valuable each \
would be as a portfolio/resume project for a student. This is NOT about \
any individual's resume — it's an estimate of the project's own portfolio \
value, judged on: technical depth required, relevance to real industry \
needs today, the technologies/skills a student would gain, real-world \
impact, uniqueness (vs. an overdone idea), and overall portfolio value.

Score each of the {count} problems below on three 0-10 scales (decimals \
allowed, e.g. 8.5):
- resume_value_score: overall value as a resume/portfolio project
- industry_relevance_score: relevance to real industry needs today
- technical_depth_score: technical depth/difficulty required to build it well

Problems:
{problems_block}

Respond with ONLY a JSON array (no markdown, no commentary), one object \
per problem, in this exact shape:
[
  {{"id": "<the exact id given above>", "resume_value_score": <0-10>, "industry_relevance_score": <0-10>, "technical_depth_score": <0-10>}}
]
"""


def _format_problem(problem: dict) -> str:
    domain = ", ".join(problem.get("domain") or []) or "unspecified"
    technologies = ", ".join(problem.get("technologies") or []) or "unspecified"
    return (
        f"- id: {problem['id']}\n"
        f"  title: {problem['title']}\n"
        f"  domain: {domain}\n"
        f"  technologies: {technologies}\n"
        f"  summary: {problem['summary']}"
    )


def _build_batch_prompt(batch: list[dict]) -> str:
    problems_block = "\n".join(_format_problem(p) for p in batch)
    return PROMPT_TEMPLATE.format(count=len(batch), problems_block=problems_block)


def _parse_batch_response(text: str, expected_ids: set[str]) -> dict[str, dict]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Gemini did not return valid JSON: {exc}\nRaw response: {text[:500]}") from exc

    if not isinstance(data, list):
        raise ValueError(f"expected a JSON array, got {type(data).__name__}")

    scores_by_id: dict[str, dict] = {}
    for entry in data:
        if not isinstance(entry, dict) or "id" not in entry:
            logger.warning("skipping malformed score entry: %r", entry)
            continue
        entry_id = entry["id"]
        if entry_id not in expected_ids:
            logger.warning("skipping score for unknown id %r (not in this batch)", entry_id)
            continue
        try:
            scores = {field: float(entry[field]) for field in SCORE_FIELDS}
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("skipping entry %r with missing/invalid score field(s): %s", entry_id, exc)
            continue
        for field, value in scores.items():
            if not (0.0 <= value <= 10.0):
                logger.warning("clamping out-of-range %s=%.2f for %r into [0, 10]", field, value, entry_id)
        scores = {field: max(0.0, min(10.0, value)) for field, value in scores.items()}
        scores_by_id[entry_id] = scores

    missing = expected_ids - scores_by_id.keys()
    if missing:
        logger.warning("Gemini response did not include score(s) for %d id(s): %s", len(missing), sorted(missing))

    return scores_by_id


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def enrich(force: bool = False, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    if not PROCESSED_PATH.exists():
        raise FileNotFoundError(
            f"{PROCESSED_PATH} does not exist — run `python scripts/build_corpus.py` first."
        )
    problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in problems}

    todo = [p for p in problems if force or p.get("resume_value_score") is None]
    if not todo:
        logger.info("nothing to enrich — every problem already has a resume_value_score (use --force to re-score)")
        return 0

    logger.info("enriching %d/%d problem(s) in batches of %d", len(todo), len(problems), batch_size)

    scored = 0
    with track_run(
        RESUME_VALUE_ENRICHMENT_EXPERIMENT,
        params={"batch_size": batch_size, "force": force, "total_problems": len(problems), "todo_count": len(todo)},
    ) as run:
        model = get_gemini_model()
        for batch_index, batch in enumerate(_chunks(todo, batch_size)):
            expected_ids = {p["id"] for p in batch}
            prompt = _build_batch_prompt(batch)
            # This is an offline batch job (not the interactive /plan
            # endpoint), and a large multi-problem JSON response can take
            # longer than the 15s/10s defaults tuned for interactive use —
            # especially on a smaller model. Give it real time to finish
            # rather than shrinking the batch and spending extra real
            # Gemini calls just to fit a deadline meant for a live request.
            raw_text = generate_json(model, prompt, timeout=60, retry_timeout=55)
            scores_by_id = _parse_batch_response(raw_text, expected_ids)
            for problem_id, scores in scores_by_id.items():
                by_id[problem_id].update(scores)
                scored += 1

            # Checkpoint after every batch, not just at the end: a later
            # batch can fail (e.g. Gemini free-tier daily quota exhausted
            # mid-run), and without this, a crash would discard every
            # already-scored batch from this run since nothing was written
            # until the end.
            PROCESSED_PATH.write_text(
                json.dumps(list(by_id.values()), indent=2, ensure_ascii=False), encoding="utf-8"
            )
            logger.info("scored %d/%d so far (checkpointed)", scored, len(todo))
            run.log_metric("scored_so_far", scored, step=batch_index)

        run.log_metric("total_scored", scored)

    logger.info("wrote %d newly-scored problem(s) back to %s", scored, PROCESSED_PATH)
    return scored


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-score every problem, even already-scored ones")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    enrich(force=args.force, batch_size=args.batch_size)
