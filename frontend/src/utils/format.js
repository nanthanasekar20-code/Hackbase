/**
 * The backend's RankedResult.score is an unbounded float — we don't know
 * yet whether it will be a 0-1 similarity score or something else, so this
 * formats defensively instead of assuming a range.
 */
export function formatScore(score) {
  if (typeof score !== "number" || Number.isNaN(score)) {
    return { label: "—", pct: 0 };
  }
  if (score >= 0 && score <= 1) {
    const pct = Math.round(score * 100);
    return { label: `${pct}%`, pct };
  }
  // Outside 0-1: show the raw value, clamp the ring visual to 100%.
  return { label: score.toFixed(1), pct: Math.min(100, Math.abs(score) * 10) };
}

export function formatDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return "";
  }
}

export function formatDuration(seconds) {
  if (typeof seconds !== "number" || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  if (mins < 60) return `${mins}m ${secs}s`;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  return `${hrs}h ${remMins}m`;
}

export function timeAgo(iso) {
  if (!iso) return "";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(iso);
}

const RESOURCE_TYPE_LABELS = {
  docs: "Documentation",
  repo: "GitHub Repositories",
  tutorial: "Tutorials",
  dataset: "Datasets",
};

export function resourceTypeLabel(type) {
  return RESOURCE_TYPE_LABELS[type] || "Other";
}
