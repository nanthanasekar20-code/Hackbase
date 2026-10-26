import { useNavigate } from "react-router-dom";
import Card from "../ui/Card.jsx";
import Badge from "../ui/Badge.jsx";
import Chip from "../ui/Chip.jsx";
import ScoreBadge from "../ui/ScoreBadge.jsx";
import { IconDataset, IconTool } from "../ui/icons.jsx";
import { problemId } from "../../utils/slug.js";
import styles from "./ProblemCard.module.css";

// How many days a problem keeps showing the "New" badge after
// first_seen_at (see backend app.schemas.query.RankedResult). Kept as a
// plain constant rather than a prop since every card in the app should
// agree on what "new" means.
const NEW_BADGE_DAYS = 7;

function isRecentlyAdded(firstSeenAt) {
  if (!firstSeenAt) return false;
  const seen = new Date(firstSeenAt);
  if (Number.isNaN(seen.getTime())) return false;
  const ageMs = Date.now() - seen.getTime();
  return ageMs >= 0 && ageMs <= NEW_BADGE_DAYS * 24 * 60 * 60 * 1000;
}

// Compact badges for the six newer Gemini enrichment scores (see backend
// scripts/enrich_resume_value.py) — same 0-10 scale as the Portfolio
// value scores shown on ProblemDetails, just condensed to one decimal and
// a short label here since card space is tight. Only ever read from
// `result` (never computed/guessed client-side): a problem that hasn't
// been enriched yet just omits these, same optional-field handling the
// original three resume-value scores already use.
//
// Tone picks by polarity, not just "pick something": for every field
// except hardwareRequirement, a higher score is a more favorable signal
// (more original, more fundable-looking data, more likely to place well,
// more impact, more realistically buildable in a hackathon timeframe) —
// `success` fits. hardwareRequirement is the one field where higher means
// "needs more specialized hardware", a bigger practical ask rather than a
// quality judgment either way — `warning` (a heads-up, not a verdict)
// fits better than defaulting it to the same "success" styling as the rest.
const SCORE_BADGE_FIELDS = [
  { field: "novelty_score", label: "Novel", tone: "success" },
  { field: "dataset_availability_score", label: "Dataset", tone: "success", icon: IconDataset },
  { field: "hardware_requirement_score", label: "Hardware", tone: "warning", icon: IconTool },
  { field: "competition_potential_score", label: "Competitive", tone: "success" },
  { field: "social_impact_score", label: "Impact", tone: "success" },
  { field: "feasibility_score", label: "Feasible", tone: "success" },
];

/**
 * Renders a RankedResult from POST /api/v1/search. Only `title`, `source`,
 * `score` and `summary` are guaranteed by the current schema — anything
 * else (domain, technologies, difficulty, skills, first_seen_at, and the
 * nine Gemini enrichment scores) is rendered only if the backend actually
 * sends it, so nothing here is fabricated.
 */
export default function ProblemCard({ result }) {
  const navigate = useNavigate();
  const id = problemId(result);
  const techs = result.technologies || result.tech_stack || [];
  const skills = result.skills || [];
  const isNew = isRecentlyAdded(result.first_seen_at);
  const scoreBadges = SCORE_BADGE_FIELDS.filter(({ field }) => typeof result[field] === "number");

  function open() {
    navigate(`/problem/${id}`, { state: result });
  }

  return (
    <Card
      as="article"
      interactive
      className={styles.card}
      tabIndex={0}
      role="button"
      onClick={open}
      onKeyDown={(e) => (e.key === "Enter" ? open() : null)}
    >
      <div className={styles.top}>
        <div className={styles.tags}>
          {isNew && <Badge tone="success">New</Badge>}
          {result.source && <Badge tone="sky">{result.source}</Badge>}
          {result.category && <Badge tone="sand">{result.category}</Badge>}
          {/* result.domain is a real array (often several tags) — a card
              only has room for one representative badge, so just the
              first, not every domain smushed into one unreadable string
              with no separators (the bug ProblemDetails.jsx had). */}
          {result.domain && !result.category && (
            <Badge tone="sand">{Array.isArray(result.domain) ? result.domain[0] : result.domain}</Badge>
          )}
          {result.difficulty && <Badge tone="clay">{result.difficulty}</Badge>}
        </div>
        {/* Only a RAG search result carries a real match `score` — a card
            from AllProblems or a Domains browse (plain GET /problems, never
            ranked against a query) has none, and a hollow "—" ring there
            reads as broken rather than "not applicable". */}
        {typeof result.score === "number" && <ScoreBadge score={result.score} size={48} />}
      </div>

      <h3 className={styles.title}>{result.title}</h3>
      {result.summary && <p className={styles.summary}>{result.summary}</p>}

      {(techs.length > 0 || skills.length > 0) && (
        <div className={styles.chips}>
          {techs.slice(0, 4).map((t) => (
            <Chip key={t}>{t}</Chip>
          ))}
          {skills.slice(0, techs.length > 0 ? 2 : 4).map((s) => (
            <Chip key={s}>{s}</Chip>
          ))}
        </div>
      )}

      {scoreBadges.length > 0 && (
        <div className={styles.scoreTags}>
          {scoreBadges.map(({ field, label, tone, icon: Icon }) => (
            <Badge key={field} tone={tone}>
              {Icon && <Icon width={11} height={11} />}
              {label} {result[field].toFixed(1)}
            </Badge>
          ))}
        </div>
      )}

      <span className={styles.cta}>View problem →</span>
    </Card>
  );
}
