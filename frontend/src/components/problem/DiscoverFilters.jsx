import styles from "./DiscoverFilters.module.css";
import Chip from "../ui/Chip.jsx";

/**
 * Facets are derived purely from whatever fields the current result set
 * actually has — if the backend only sends {title, source, score, summary}
 * today, only the Source and Sort controls render. Add a field (domain,
 * technologies, difficulty, skills) to a future RankedResult and the
 * matching filter appears automatically.
 */
export default function DiscoverFilters({ facets, active, onToggle, sortBy, onSortChange, resultCount }) {
  const facetGroups = [
    { key: "source", label: "Source", values: facets.source },
    { key: "domain", label: "Domain", values: facets.domain },
    { key: "difficulty", label: "Difficulty", values: facets.difficulty },
    { key: "technologies", label: "Technology", values: facets.technologies },
  ].filter((g) => g.values.length > 1);

  return (
    <div className={styles.bar}>
      <div className={styles.groups}>
        {facetGroups.map((g) => (
          <div className={styles.group} key={g.key}>
            <span className={styles.groupLabel}>{g.label}</span>
            <div className={styles.chips}>
              {g.values.map((v) => (
                <Chip key={v} onClick={() => onToggle(g.key, v)} active={active[g.key]?.has(v)}>
                  {v}
                </Chip>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className={styles.sortWrap}>
        <span className={styles.count}>
          {resultCount} {resultCount === 1 ? "result" : "results"}
        </span>
        <label className={styles.sortLabel}>
          Sort
          <select className={styles.select} value={sortBy} onChange={(e) => onSortChange(e.target.value)}>
            <option value="relevance">Relevance</option>
            <option value="title">Title A–Z</option>
          </select>
        </label>
      </div>
    </div>
  );
}
