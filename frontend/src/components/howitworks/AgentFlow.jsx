import { IconSearch, IconRank, IconPlan, IconResource } from "../ui/icons.jsx";
import styles from "./AgentFlow.module.css";

const AGENTS = [
  {
    key: "search",
    icon: IconSearch,
    name: "Search Agent",
    desc: "Embeds your query and retrieves candidate hackathon problem statements from the vector store.",
  },
  {
    key: "rank",
    icon: IconRank,
    name: "Ranking Agent",
    desc: "Scores each candidate against your query and profile, then re-orders by relevance.",
  },
  {
    key: "plan",
    icon: IconPlan,
    name: "Planning Agent",
    desc: "Turns the selected problem into a phased roadmap of tasks and milestones.",
  },
  {
    key: "resource",
    icon: IconResource,
    name: "Resource Agent",
    desc: "Surfaces starter docs, repos, tutorials and datasets relevant to the plan.",
  },
];

export default function AgentFlow({ compact = false }) {
  return (
    <div className={[styles.flow, compact && styles.compact].filter(Boolean).join(" ")}>
      {AGENTS.map((agent, i) => (
        <div className={styles.step} key={agent.key}>
          <div className={styles.node}>
            <div className={styles.iconWrap}>
              <agent.icon width={22} height={22} />
            </div>
            <h3 className={styles.name}>{agent.name}</h3>
            {!compact && <p className={styles.desc}>{agent.desc}</p>}
          </div>
          {i < AGENTS.length - 1 && <div className={styles.connector} aria-hidden="true" />}
        </div>
      ))}
    </div>
  );
}
