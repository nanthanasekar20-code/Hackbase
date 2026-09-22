import { IconCheck } from "../ui/icons.jsx";
import styles from "./RoadmapStage.module.css";

export default function RoadmapStage({ stage, index, isLast, taskProgress, onToggleTask }) {
  const tasks = stage.tasks || [];
  const doneCount = tasks.filter((_, ti) => taskProgress?.[`${index}-${ti}`]).length;

  return (
    <div className={styles.stage}>
      <div className={styles.rail}>
        <span className={styles.dot}>{index + 1}</span>
        {!isLast && <span className={styles.line} />}
      </div>
      <div className={styles.body}>
        <div className={styles.head}>
          <h3 className={styles.phase}>{stage.phase}</h3>
          <span className={styles.count}>
            {doneCount}/{tasks.length}
          </span>
        </div>
        <ul className={styles.tasks}>
          {tasks.map((task, ti) => {
            const key = `${index}-${ti}`;
            const checked = Boolean(taskProgress?.[key]);
            return (
              <li key={key} className={styles.task}>
                <button
                  type="button"
                  className={[styles.checkbox, checked && styles.checked].filter(Boolean).join(" ")}
                  onClick={() => onToggleTask(key)}
                  aria-pressed={checked}
                  aria-label={checked ? `Mark "${task}" as not done` : `Mark "${task}" as done`}
                >
                  {checked && <IconCheck width={12} height={12} />}
                </button>
                <span className={checked ? styles.doneText : undefined}>{task}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
