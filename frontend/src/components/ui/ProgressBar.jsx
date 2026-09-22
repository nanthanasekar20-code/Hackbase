import styles from "./ProgressBar.module.css";

export default function ProgressBar({ value = 0, label }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div className={styles.wrap}>
      {label && (
        <div className={styles.labelRow}>
          <span>{label}</span>
          <span className="mono">{pct}%</span>
        </div>
      )}
      <div className={styles.track} role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className={styles.fill} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
