import styles from "./ScoreBadge.module.css";
import { formatScore } from "../../utils/format.js";

/**
 * Circular match-score indicator. Accepts the raw `score` number returned
 * by the ranking agent — no assumptions beyond "higher is better".
 */
export default function ScoreBadge({ score, size = 56 }) {
  const { label, pct } = formatScore(score);
  const circumference = 2 * Math.PI * 20;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className={styles.wrap} style={{ width: size, height: size }} title="Match score">
      <svg viewBox="0 0 48 48" width={size} height={size}>
        <circle cx="24" cy="24" r="20" fill="none" stroke="var(--border)" strokeWidth="4" />
        <circle
          cx="24"
          cy="24"
          r="20"
          fill="none"
          stroke="var(--sky-deep)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform="rotate(-90 24 24)"
        />
      </svg>
      <span className={styles.label}>{label}</span>
    </div>
  );
}
