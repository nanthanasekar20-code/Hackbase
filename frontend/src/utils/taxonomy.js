/**
 * Mirrors backend/app/core/taxonomy.py's DOMAINS and SKILL_LEVELS exactly
 * — these are the only two vocabularies a user's optional personalization
 * preferences (Profile page) can be set to, so a value picked here must
 * line up byte-for-byte with what the backend validates against
 * (app/schemas/user.py's UserUpdate) and compares in its ranking boost
 * (app/rag/retriever.py).
 *
 * Deliberately duplicated rather than fetched: there's no existing
 * endpoint exposing either list, and both change rarely enough that
 * keeping them in sync by hand — the same "defined independently, synced
 * by a human, not an import" pattern this codebase already uses between
 * e.g. enrich_resume_value.SCORE_FIELDS and build_corpus.RESUME_VALUE_FIELDS
 * — is simpler than adding a new backend endpoint just for this.
 */
export const DOMAINS = [
  "AI/ML",
  "Web Development",
  "Mobile Development",
  "Cybersecurity",
  "IoT",
  "Healthcare",
  "FinTech",
  "Agriculture",
  "EdTech",
  "Sustainability & Climate",
  "Blockchain & Web3",
  "Data Science & Analytics",
];

// Values are what's actually sent to/stored by the backend; labels are
// display-only. See backend/app/core/taxonomy.py's SKILL_LEVELS docstring
// for why this is a conventional default rather than a vocabulary scraped
// from real problem data (no problem is actually tagged with a difficulty
// yet, so skill_level matching is a real no-op today — not a bug).
export const SKILL_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];
