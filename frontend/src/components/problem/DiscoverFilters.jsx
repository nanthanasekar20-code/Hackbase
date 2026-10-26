import { useState } from "react";
import styles from "./DiscoverFilters.module.css";
import Chip from "../ui/Chip.jsx";
import { neutralThreshold } from "../../utils/scoreFields.js";

/**
 * Facets are derived purely from whatever fields the current result set
 * actually has — if the backend only sends {title, source, score, summary}
 * today, only the Source and Sort controls render. Add a field (domain,
 * technologies, difficulty, skills) to a future RankedResult and the
 * matching filter appears automatically.
 *
 * `scoreFields` follows the same "nothing behind it, don't show it" rule
 * but for the 9 numeric Gemini enrichment scores — see
 * pages/Discover.jsx's availableScoreFields. It's a separate, collapsible
 * "Scores" group rather than more chip rows: these are threshold filters,
 * not exact-value toggles, and up to 9 of them at once next to the
 * existing chip groups would overwhelm the bar (see this component's own
 * module docstring in the repo notes on this — flagged rather than
 * guessed at).
 */
export default function DiscoverFilters({
  facets,
  active,
  onToggle,
  scoreFields = [],
  scoreFilters = {},
  onScoreFilterChange,
  hasActiveFilters,
  onClearAll,
  sortBy,
  onSortChange,
  resultCount,
}) {
  const [scoresOpen, setScoresOpen] = useState(false);

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

        {scoreFields.length > 0 && (
          <div className={styles.group}>
            <button
              type="button"
              className={styles.scoresToggle}
              onClick={() => setScoresOpen((v) => !v)}
              aria-expanded={scoresOpen}
            >
              <span className={styles.groupLabel}>
                Scores{Object.keys(scoreFilters).length > 0 ? ` (${Object.keys(scoreFilters).length})` : ""}
              </span>
              <span className={styles.scoresChevron}>{scoresOpen ? "▾" : "▸"}</span>
            </button>

            {scoresOpen && (
              <div className={styles.scoreRows}>
                {scoreFields.map((field) => {
                  const neutral = neutralThreshold(field);
                  const value = scoreFilters[field.key] ?? neutral;
                  const isActive = field.key in scoreFilters;
                  const symbol = field.polarity === "max" ? "≤" : "≥";
                  return (
                    <div className={styles.scoreRow} key={field.key}>
                      <div className={styles.scoreRowHead}>
                        <span className={[styles.scoreLabel, isActive && styles.scoreLabelActive].join(" ")}>
                          {field.label} {symbol} {value.toFixed(1)}
                        </span>
                        {isActive && (
                          <button
                            type="button"
                            className={styles.scoreReset}
                            onClick={() => onScoreFilterChange(field, neutral)}
                            aria-label={`Clear ${field.label} filter`}
                          >
                            ×
                          </button>
                        )}
                      </div>
                      <input
                        type="range"
                        className={styles.scoreSlider}
                        aria-label={field.label}
                        min={0}
                        max={10}
                        step={0.5}
                        value={value}
                        onChange={(e) => onScoreFilterChange(field, Number(e.target.value))}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {hasActiveFilters && (
          <button type="button" className={styles.clearAll} onClick={onClearAll}>
            Clear all filters
          </button>
        )}
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
