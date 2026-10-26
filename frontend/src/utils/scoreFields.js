/**
 * The nine Gemini resume-value enrichment fields (see backend
 * scripts/enrich_resume_value.py's SCORE_FIELDS) as frontend display
 * metadata — label text and threshold-filter polarity, used by
 * DiscoverFilters.jsx and pages/Discover.jsx. Not a backend mirror in the
 * sense that matters: this never decides what gets scored, only how an
 * already-scored field is labeled/compared once it shows up in a result.
 *
 * `polarity` is "min" for every field except hardware_requirement_score:
 * for "min" fields a higher score is better, so a threshold filter reads
 * as "at least this much" (≥). hardware_requirement_score is inverted —
 * higher means MORE specialized hardware is needed, not "better" — so its
 * threshold filter reads as "at most this much" (≤) instead.
 */
export const SCORE_FIELDS = [
  { key: "resume_value_score", label: "Resume value", polarity: "min" },
  { key: "industry_relevance_score", label: "Industry relevance", polarity: "min" },
  { key: "technical_depth_score", label: "Technical depth", polarity: "min" },
  { key: "novelty_score", label: "Novelty", polarity: "min" },
  { key: "dataset_availability_score", label: "Dataset availability", polarity: "min" },
  { key: "hardware_requirement_score", label: "Hardware needed", polarity: "max" },
  { key: "competition_potential_score", label: "Competition potential", polarity: "min" },
  { key: "social_impact_score", label: "Social impact", polarity: "min" },
  { key: "feasibility_score", label: "Hackathon feasibility", polarity: "min" },
];

// The slider value that means "not filtering on this field at all" — the
// bottom of the scale for a "min" (≥) field, the top for a "max" (≤) one.
// A score filter is considered active exactly when its stored threshold
// differs from this, so there's never an "active filter that excludes
// nothing" state to reason about separately.
export function neutralThreshold(field) {
  return field.polarity === "max" ? 10 : 0;
}

export function passesScoreThreshold(problem, field, threshold) {
  const value = problem[field.key];
  // Never treat "unscored" as 0 — a problem Gemini hasn't rated on this
  // field yet must be excluded while the filter is active, not silently
  // pass (or fail) a threshold it was never evaluated against.
  if (typeof value !== "number") return false;
  return field.polarity === "max" ? value <= threshold : value >= threshold;
}
