const PREFIX = "hackbase:";

/**
 * Thin, defensive wrapper around localStorage. Every "My Projects" /
 * "Roadmaps" / "Resources" feature is backed by this — there is no backend
 * persistence for saved problems or projects yet, so we keep it local and
 * clearly labelled as such in the UI rather than pretending it's synced.
 */
export function readJSON(key, fallback) {
  try {
    const raw = window.localStorage.getItem(PREFIX + key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

export function writeJSON(key, value) {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value));
    window.dispatchEvent(new CustomEvent("hackbase:storage", { detail: { key } }));
  } catch {
    // storage unavailable (private browsing, quota, etc.) — fail silently
  }
}

export function subscribe(callback) {
  const handler = () => callback();
  window.addEventListener("hackbase:storage", handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener("hackbase:storage", handler);
    window.removeEventListener("storage", handler);
  };
}
