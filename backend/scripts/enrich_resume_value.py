"""
Phase 2 (+ its later extension): one-time Gemini enrichment pass that
scores every problem in data/processed/problems.json on nine metrics
(each 0-10, decimals allowed):

    resume_value_score          - how good a portfolio/resume project this is
    industry_relevance_score    - how relevant to real industry needs today
    technical_depth_score       - how much genuine technical depth it requires
    novelty_score                - how original/non-generic the idea is
    dataset_availability_score  - how easy it'd be to find/build a usable dataset
    hardware_requirement_score  - how much specialized hardware beyond a laptop
                                   (higher = needs MORE — a bigger ask, not a
                                   "worse" score; the one field here where higher
                                   isn't "better")
    competition_potential_score - how well this could place in a hackathon's judging
    social_impact_score         - how much real-world positive impact it could have
    feasibility_score            - can a small student team realistically build
                                   this in a hackathon timeframe (scope-fit, not
                                   skill depth — see technical_depth_score for
                                   that). Distinct from the longer qualitative
                                   feasibility paragraph the Planning Agent
                                   generates per-roadmap once a problem is
                                   actually chosen (app/agents/planning_agent.py)
                                   — this is a lighter corpus-level number shown
                                   while still browsing/comparing problems.

Computed ONCE per problem at ingestion time (not per search query), based
on the problem's technical depth, industry relevance, technologies/skills
involved, real-world impact, uniqueness, and portfolio value. This is
deliberately NOT a resume upload/parsing feature — it's an estimate of a
project's portfolio value, independent of any individual user.

Run as: python scripts/enrich_resume_value.py [--force] [--batch-size N]

Idempotent by default: problems that already have ALL NINE score fields
set are skipped (see is_fully_scored() below), so re-running after
`python scripts/build_corpus.py` regenerates data/processed/problems.json
only spends API calls on new/changed records, or ones only partially
scored from before a field was added here (--force re-scores everything
regardless).

Also exposes enrich_one(problem_id), a single-problem variant used by
app/api/routes/favorites.py to lazily score a problem the first time a
user actually saves it, instead of this batch pass having to run against
every newly-scraped problem regardless of interest — see
app/services/refresh_job.py's docstring for why the scheduled refresh job
deliberately doesn't call this script itself.

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
SCORE_FIELDS = (
    "resume_value_score",
    "industry_relevance_score",
    "technical_depth_score",
    "novelty_score",
    "dataset_availability_score",
    "hardware_requirement_score",
    "competition_potential_score",
    "social_impact_score",
    "feasibility_score",
)


def is_fully_scored(problem: dict) -> bool:
    """True only if every one of SCORE_FIELDS is already set on `problem`.

    This, not "resume_value_score is None", is the correct "does this
    problem still need enrichment" check — used by both enrich()'s batch
    gating below and enrich_one()'s lazy per-save gate, plus
    app/api/routes/favorites.py's decision to even schedule enrich_one().
    A problem scored before the six newer fields (novelty_score etc.)
    existed already has resume_value_score set, so checking that one
    field alone would wrongly treat it as permanently done and it would
    never pick up the rest."""
    return all(problem.get(field) is not None for field in SCORE_FIELDS)


# _build_batch_prompt/_parse_batch_response (below) both iterate SCORE_FIELDS
# generically — adding a field here is enough to cover the batch script AND
# enrich_one()'s lazy per-save path (app/api/routes/favorites.py), since both
# call the same two functions. No separate Gemini call per field/problem.
PROMPT_TEMPLATE = """\
You are evaluating hackathon problem statements across several criteria \
useful to a student deciding what to build. This is NOT about any \
individual's resume — these are estimates of the project itself, \
independent of any one person.

Score each of the {count} problems below on nine 0-10 scales (decimals \
allowed, e.g. 8.5). For all of them except hardware_requirement_score, \
higher means more favorable; hardware_requirement_score is the one \
exception — higher there just means MORE specialized hardware is needed, \
which is a practical constraint to flag, not a quality judgment:
- resume_value_score: overall value as a resume/portfolio project
- industry_relevance_score: relevance to real industry needs today
- technical_depth_score: technical depth/difficulty required to build it well
- novelty_score: how original/non-generic this idea is, vs. an overdone concept
- dataset_availability_score: how easy it would be to find or build a usable \
dataset for this (10 = real public datasets are readily available; 0 = would \
need extensive novel data collection)
- hardware_requirement_score: how much specialized hardware this needs beyond \
a normal laptop (10 = needs serious specialized hardware, e.g. robotics rigs, \
custom sensors, edge/embedded devices; 0 = a laptop is enough)
- competition_potential_score: how well-positioned this is to place well in a \
hackathon's judging (originality + impact + how demo-able it is)
- social_impact_score: how much real-world positive impact this could have if \
built well
- feasibility_score: can a small student team realistically build a working \
version of this within a hackathon's timeframe — about scope fitting the time \
available, distinct from technical_depth_score's skill-depth judgment

Problems:
{problems_block}

Respond with ONLY a JSON array (no markdown, no commentary), one object \
per problem, in this exact shape:
[
  {{"id": "<the exact id given above>", "resume_value_score": <0-10>, "industry_relevance_score": <0-10>, "technical_depth_score": <0-10>, "novelty_score": <0-10>, "dataset_availability_score": <0-10>, "hardware_requirement_score": <0-10>, "competition_potential_score": <0-10>, "social_impact_score": <0-10>, "feasibility_score": <0-10>}}
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

    todo = [p for p in problems if force or not is_fully_scored(p)]
    if not todo:
        logger.info(
            "nothing to enrich — every problem already has all %d score fields (use --force to re-score)",
            len(SCORE_FIELDS),
        )
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


def enrich_one(problem_id: str) -> bool:
    """Lazily scores a single problem — used by app/api/routes/favorites.py
    the first time a signed-in user saves that problem, instead of only
    via the batch enrich() pass above. Returns True if (new) scores were
    written, False if the problem already had all nine fields, wasn't
    found, or Gemini didn't return a usable score for it (including if
    GEMINI_API_KEY isn't configured — get_gemini_model() raises, and the
    caller is expected to treat this whole function as best-effort).

    Deliberately skips track_run()/MLflow logging (unlike enrich()) — an
    MLflow run per single favorite-save is unwarranted overhead for what
    is, from the app's perspective, an incidental side effect of a save,
    not a real "enrichment experiment"."""
    if not PROCESSED_PATH.exists():
        return False

    problems = json.loads(PROCESSED_PATH.read_text(encoding="utf-8"))
    by_id = {p["id"]: p for p in problems}
    problem = by_id.get(problem_id)
    if problem is None or is_fully_scored(problem):
        return False

    model = get_gemini_model()
    prompt = _build_batch_prompt([problem])
    raw_text = generate_json(model, prompt, timeout=20, retry_timeout=15)
    scores_by_id = _parse_batch_response(raw_text, {problem_id})
    scores = scores_by_id.get(problem_id)
    if not scores:
        return False

    problem.update(scores)
    PROCESSED_PATH.write_text(
        json.dumps(list(by_id.values()), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info("enrich_one: scored %s on save", problem_id)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="re-score every problem, even already-scored ones")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    args = parser.parse_args()
    enrich(force=args.force, batch_size=args.batch_size)
