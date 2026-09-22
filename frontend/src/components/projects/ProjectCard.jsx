import { useNavigate } from "react-router-dom";
import Card from "../ui/Card.jsx";
import Badge from "../ui/Badge.jsx";
import ProgressBar from "../ui/ProgressBar.jsx";
import { IconTrash } from "../ui/icons.jsx";
import { STATUS, STATUS_LABEL } from "../../hooks/useProjects.js";
import { planProgress } from "../../hooks/useProjects.js";
import { timeAgo } from "../../utils/format.js";
import styles from "./ProjectCard.module.css";

const STATUS_TONE = {
  [STATUS.SAVED]: "neutral",
  [STATUS.IN_PROGRESS]: "sky",
  [STATUS.DONE]: "success",
};

export default function ProjectCard({ project, onStatusChange, onRemove }) {
  const navigate = useNavigate();
  const progress = planProgress(project);
  const hasPlan = Boolean(project.plan);

  function open() {
    navigate(hasPlan ? `/roadmap/${project.id}` : `/problem/${project.id}`);
  }

  return (
    <Card className={styles.card}>
      <div className={styles.top}>
        <div className={styles.tags}>
          {project.source && <Badge tone="sky">{project.source}</Badge>}
          <Badge tone={STATUS_TONE[project.status] || "neutral"}>{STATUS_LABEL[project.status] || "Saved"}</Badge>
        </div>
        <button className={styles.remove} onClick={() => onRemove(project.id)} aria-label="Remove project">
          <IconTrash width={16} height={16} />
        </button>
      </div>

      <h3 className={styles.title} onClick={open} role="button" tabIndex={0}>
        {project.title}
      </h3>
      {project.summary && <p className={styles.summary}>{project.summary}</p>}

      {progress !== null && (
        <div className={styles.progress}>
          <ProgressBar value={progress} label="Roadmap progress" />
        </div>
      )}

      <div className={styles.footer}>
        <span className={styles.meta}>
          {hasPlan ? "Roadmap ready" : "No roadmap yet"} · saved {timeAgo(project.savedAt)}
        </span>
        <select
          className={styles.statusSelect}
          value={project.status}
          onChange={(e) => onStatusChange(project.id, e.target.value)}
        >
          {Object.entries(STATUS_LABEL).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </Card>
  );
}
