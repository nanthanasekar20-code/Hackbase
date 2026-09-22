export function slugify(input = "") {
  return (
    input
      .toString()
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "") || "problem"
  );
}

/**
 * Builds a stable id for a search result so it can be cached / linked to /
 * saved as a favorite. Prefers the real corpus id the backend already
 * returns on every search result (see app/rag/retriever.py's `doc_id`) —
 * that's what backend favorites are keyed by, so using anything else here
 * would silently break hydration (title/summary/source) for saved
 * projects. Falls back to a title+source slug only for a result that
 * somehow has no real id.
 */
export function problemId(result) {
  if (result?.id) return result.id;
  const base = slugify(result?.title || "problem");
  const src = result?.source ? slugify(result.source) : "src";
  return `${base}--${src}`;
}
