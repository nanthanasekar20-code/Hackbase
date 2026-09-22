import styles from "./RagFlow.module.css";
import { IconArrowRight } from "../ui/icons.jsx";

const STEPS = [
  { label: "Your query", desc: "“What do you want to build?”" },
  { label: "Embedding", desc: "Query is embedded into vector space" },
  { label: "Vector retrieval", desc: "Chroma / FAISS returns nearest problem statements" },
  { label: "Contextual ranking", desc: "Candidates re-scored against your query" },
  { label: "Generation", desc: "Gemini drafts the roadmap & explanation" },
  { label: "Response", desc: "Ranked results, roadmap, resources" },
];

export default function RagFlow() {
  return (
    <div className={styles.flow}>
      {STEPS.map((step, i) => (
        <div className={styles.item} key={step.label}>
          <div className={styles.card}>
            <span className={styles.index}>{String(i + 1).padStart(2, "0")}</span>
            <h4 className={styles.label}>{step.label}</h4>
            <p className={styles.desc}>{step.desc}</p>
          </div>
          {i < STEPS.length - 1 && (
            <div className={styles.arrow} aria-hidden="true">
              <IconArrowRight width={16} height={16} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
