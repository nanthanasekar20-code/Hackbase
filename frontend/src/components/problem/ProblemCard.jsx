import { useNavigate } from "react-router-dom";
import Card from "../ui/Card.jsx";
import Badge from "../ui/Badge.jsx";
import Chip from "../ui/Chip.jsx";
import ScoreBadge from "../ui/ScoreBadge.jsx";
import { problemId } from "../../utils/slug.js";
import styles from "./ProblemCard.module.css";

/**
 * Renders a RankedResult from POST /api/v1/search. Only `title`, `source`,
 * `score` and `summary` are guaranteed by the current schema — anything
 * else (domain, technologies, difficulty, skills) is rendered only if the
 * backend actually sends it, so nothing here is fabricated.
 */
export default function ProblemCard({ result }) {
  const navigate = useNavigate();
  const id = problemId(result);
  const techs = result.technologies || result.tech_stack || [];
  const skills = result.skills || [];

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
          {result.source && <Badge tone="sky">{result.source}</Badge>}
          {result.category && <Badge tone="sand">{result.category}</Badge>}
          {result.domain && !result.category && <Badge tone="sand">{result.domain}</Badge>}
          {result.difficulty && <Badge tone="clay">{result.difficulty}</Badge>}
        </div>
        <ScoreBadge score={result.score} size={48} />
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

      <span className={styles.cta}>View problem →</span>
    </Card>
  );
}
