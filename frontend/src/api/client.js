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

// patch: { full_name?, email?, new_password?, current_password? } — email
// or new_password changes require current_password (see UserUpdate).
export const updateProfile = (patch) => client.patch("/auth/me", patch).then((res) => res.data);

export const apiErrorMessage = (err, fallback = "Something went wrong.") => err?.response?.data?.detail || fallback;

export const searchHackathons = (query, topK = 5) =>
  client.post("/search", { query, top_k: topK }).then((res) => res.data);

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

// Formats a plan the frontend already has into a downloadable .pptx —
// see backend app/services/pptx_builder.py. Deliberately sends the plan
// itself as the request body rather than a problem id, so the backend
// never needs to re-run the Planning Agent (no extra Gemini call per
// export). Triggers a real browser file download from the returned blob.
export const exportRoadmapPptx = async ({ problemTitle, problemStatement, source, hackathonName, plan }) => {
  const response = await client.post(
    "/plan/export-pptx",
    {
      problem_title: problemTitle,
      problem_statement: problemStatement || "",
      source: source || null,
      hackathon_name: hackathonName || null,
      plan,
    },
    { responseType: "blob" }
  );

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

// Phase 7: real MLflow run history for the Planning Agent and Resume
// Value enrichment experiments — see backend app/api/routes/tracking.py.
export const getTrackingRuns = (limit = 20) =>
  client.get("/tracking/runs", { params: { limit } }).then((res) => res.data);

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
