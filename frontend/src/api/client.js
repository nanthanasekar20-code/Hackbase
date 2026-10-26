import axios from "axios";
import { getAuthToken } from "../utils/authToken.js";

// Preserved exactly from the original scaffold — same baseURL, same
// endpoints, same request/response shapes. Do not change without a matching
// backend change.
const client = axios.create({
  baseURL: "/api/v1",
});

client.interceptors.request.use((config) => {
  const token = getAuthToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// --- Auth (see backend app/api/routes/auth.py) ---
export const registerUser = (email, password, fullName) =>
  client.post("/auth/register", { email, password, full_name: fullName || null }).then((res) => res.data);

export const loginUser = (email, password) =>
  client.post("/auth/login", { email, password }).then((res) => res.data);

export const getCurrentUser = () => client.get("/auth/me").then((res) => res.data);

// patch: { full_name?, email?, new_password?, current_password?,
// interests?, skill_level? } — email or new_password changes require
// current_password (see UserUpdate); interests/skill_level don't.
// interests: [] and skill_level: "" explicitly clear those two (see
// UserUpdate's docstring) — omitting a key entirely leaves it unchanged.
export const updateProfile = (patch) => client.patch("/auth/me", patch).then((res) => res.data);

export const verifyPassword = (currentPassword) =>
  client.post("/auth/verify-password", { current_password: currentPassword }).then((res) => res.data);

export const forgotPassword = (email) => client.post("/auth/forgot-password", { email }).then((res) => res.data);

export const resetPassword = (token, newPassword) =>
  client.post("/auth/reset-password", { token, new_password: newPassword }).then((res) => res.data);

export const apiErrorMessage = (err, fallback = "Something went wrong.") => err?.response?.data?.detail || fallback;

export const searchHackathons = (query, topK = 5) =>
  client.post("/search", { query, top_k: topK }).then((res) => res.data);

// Non-RAG reads over the problem corpus (see backend app/api/routes/
// problems.py) — a genuinely reshuffled random sample (Home's "Refresh"
// on Featured) and a flat paginated browse-all ("Explore all"). Neither
// goes through the search/ranking agents, so results carry no `score`.
export const getRandomProblems = (count = 6) =>
  client.get("/problems/random", { params: { count } }).then((res) => res.data);

export const getProblems = ({ page = 1, pageSize = 20, domain, source, category, difficulty } = {}) =>
  client
    .get("/problems", { params: { page, page_size: pageSize, domain, source, category, difficulty } })
    .then((res) => res.data);

// Dedupes concurrent calls for the exact same problem statement into one
// real network request, keyed by module scope (not component state) so it
// survives both: (1) React 18 StrictMode's dev-only double-effect-invoke,
// which otherwise fires this twice for one user action since the second
// invocation runs before the first's result is cached anywhere, and (2) a
// user navigating away from a roadmap page and back again while the first
// generation is still in flight, which would otherwise see no cached plan
// yet and start a second one. Real, quota-consuming Gemini calls — see
// backend app/api/routes/plan.py, which has no server-side cache of its
// own and calls Gemini unconditionally on every hit.
const _inFlightPlanRequests = new Map();

export const generatePlan = (problemStatement) => {
  if (_inFlightPlanRequests.has(problemStatement)) {
    return _inFlightPlanRequests.get(problemStatement);
  }
  const request = client
    .post("/plan", { problem_statement: problemStatement })
    .then((res) => res.data)
    .finally(() => {
      _inFlightPlanRequests.delete(problemStatement);
    });
  _inFlightPlanRequests.set(problemStatement, request);
  return request;
};

// Downloads the .pptx for a saved project's roadmap — see backend
// GET /favorites/{problem_id}/export-pptx. Generated once there and
// cached on the favorite row, so calling this again later (from My
// Projects, Problem Details, or Roadmap) re-downloads the same file
// instantly instead of rebuilding it. Requires the project to already
// have a saved plan (favorite.plan set via updateFavorite/savePlan).
export const exportFavoritePptx = async (problemId) => {
  const response = await client.get(`/favorites/${encodeURIComponent(problemId)}/export-pptx`, {
    responseType: "blob",
  });

  const disposition = response.headers["content-disposition"] || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : "roadmap.pptx";

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// Opens a saved project's roadmap in-browser (the "View PPT" action) —
// see backend GET /favorites/{problem_id}/view-pdf. Browsers can't render
// .pptx natively, so that endpoint serves a real PDF rendering of the same
// plan content instead; this fetches it as an authenticated blob (a plain
// <a>/window.open to the URL wouldn't carry the auth header) and opens it
// in a new tab, where the browser's own PDF viewer takes over. The object
// URL is revoked after a minute — long enough for the new tab to finish
// loading it, short enough not to leak memory indefinitely.
export const viewFavoritePdf = async (problemId) => {
  const response = await client.get(`/favorites/${encodeURIComponent(problemId)}/view-pdf`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(response.data);
  window.open(url, "_blank", "noopener,noreferrer");
  setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
};

// Phase 7: real MLflow run history for the Planning Agent and Resume
// Value enrichment experiments — see backend app/api/routes/tracking.py.
export const getTrackingRuns = (limit = 20) =>
  client.get("/tracking/runs", { params: { limit } }).then((res) => res.data);

// "Live Hackathons" feed — hackathons currently open for registration,
// scraped separately from the problem-statement corpus (see backend
// scripts/run_live_hackathons.py). Just a periodically-refreshed JSON
// read, no live scrape per request. source/search are optional (used by
// the fuller /live-hackathons page's filter bar) — the Home teaser's
// no-arg call is unaffected either way.
export const getLiveHackathons = ({ source, search } = {}) =>
  client.get("/live-hackathons", { params: { source, search } }).then((res) => res.data);

// --- Favorites / "My Projects" (see backend app/api/routes/favorites.py) ---
// A user's real, server-backed saved problems, generated roadmaps, and
// checklist progress — replaces the old localStorage-only version.
export const getFavorites = () => client.get("/favorites").then((res) => res.data);

export const createFavorite = (problemId) =>
  client.post("/favorites", { problem_id: problemId }).then((res) => res.data);

export const updateFavorite = (problemId, patch) =>
  client.patch(`/favorites/${encodeURIComponent(problemId)}`, patch).then((res) => res.data);

export const deleteFavorite = (problemId) =>
  client.delete(`/favorites/${encodeURIComponent(problemId)}`).then((res) => res.data);

export default client;
