import { useEffect, useMemo, useSyncExternalStore } from "react";
import { readJSON, writeJSON } from "../utils/storage.js";
import { problemId } from "../utils/slug.js";
import { useAuth } from "./useAuth.js";
import { getFavorites, createFavorite, updateFavorite, deleteFavorite } from "../api/client.js";

const PROBLEMS_KEY = "problems";

export const STATUS = {
  SAVED: "saved",
  IN_PROGRESS: "in_progress",
  DONE: "done",
};

export const STATUS_LABEL = {
  [STATUS.SAVED]: "Saved",
  [STATUS.IN_PROGRESS]: "In progress",
  [STATUS.DONE]: "Done",
};

function getProblems() {
  return readJSON(PROBLEMS_KEY, {});
}

/**
 * Cache a search result so Problem Details / Roadmap survive a page
 * refresh. Deliberately still local-only (not sent to the backend): it's
 * just a denormalized lookup for /search results (which aren't persisted
 * server-side), independent of whether the problem is saved as a project —
 * see useProjects() below for the real, backend-backed "My Projects" data.
 */
export function cacheProblem(result) {
  if (!result) return null;
  const id = problemId(result);
  const problems = getProblems();
  problems[id] = { ...result, id, cachedAt: new Date().toISOString() };
  writeJSON(PROBLEMS_KEY, problems);
  return id;
}

export function getCachedProblem(id) {
  return getProblems()[id] || null;
}

// --- "My Projects" store: a user's saved problems + generated roadmaps +
// checklist progress, backed by the real /favorites API (see
// backend app/api/routes/favorites.py). A small module-level pub-sub
// store, same shape of idea as the old localStorage version's
// useSyncExternalStore usage, except the source of truth is now the
// network — `forToken` tracks whose data is cached so switching accounts
// (or logging out) can't leak one user's projects into another's view.

function fromApi(fav) {
  return {
    id: fav.problem_id,
    title: fav.title,
    source: fav.source,
    summary: fav.summary,
    domain: fav.domain,
    status: fav.status,
    plan: fav.plan,
    taskProgress: fav.task_progress || {},
    savedAt: fav.created_at,
    updatedAt: fav.updated_at,
  };
}

let store = { projects: [], phase: "idle", forToken: null }; // phase: idle | loading | loaded | error
const listeners = new Set();

function setStore(patch) {
  store = { ...store, ...patch };
  listeners.forEach((l) => l());
}

function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return store;
}

async function ensureLoaded(token) {
  if (!token) {
    if (store.phase !== "idle" || store.projects.length) setStore({ projects: [], phase: "idle", forToken: null });
    return;
  }
  if (store.forToken === token && (store.phase === "loaded" || store.phase === "loading")) return;
  setStore({ phase: "loading", forToken: token });
  try {
    const favorites = await getFavorites();
    setStore({ projects: favorites.map(fromApi), phase: "loaded", forToken: token });
  } catch {
    setStore({ projects: [], phase: "error", forToken: token });
  }
}

function upsertProject(project) {
  const next = store.projects.filter((p) => p.id !== project.id);
  next.unshift(project);
  setStore({ projects: next });
}

async function saveProblem(result) {
  const id = cacheProblem(result);
  const fav = await createFavorite(id);
  upsertProject(fromApi(fav));
  return id;
}

async function savePlan(id, plan) {
  const existing = store.projects.find((p) => p.id === id);
  if (!existing) {
    await createFavorite(id);
  }
  const nextStatus = existing?.status === STATUS.DONE ? STATUS.DONE : STATUS.IN_PROGRESS;
  const fav = await updateFavorite(id, { plan, status: nextStatus });
  upsertProject(fromApi(fav));
}

async function setStatus(id, status) {
  const fav = await updateFavorite(id, { status });
  upsertProject(fromApi(fav));
}

async function toggleTask(id, taskKey) {
  const existing = store.projects.find((p) => p.id === id);
  if (!existing) return;
  const taskProgress = { ...(existing.taskProgress || {}) };
  taskProgress[taskKey] = !taskProgress[taskKey];
  const fav = await updateFavorite(id, { task_progress: taskProgress });
  upsertProject(fromApi(fav));
}

async function removeProject(id) {
  await deleteFavorite(id);
  setStore({ projects: store.projects.filter((p) => p.id !== id) });
}

/** React hook exposing the full "My Projects" store — real, backend-backed, follows the logged-in user. */
export function useProjects() {
  const { token } = useAuth();
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  useEffect(() => {
    ensureLoaded(token);
  }, [token]);

  const projects = useMemo(
    () => [...snapshot.projects].sort((a, b) => new Date(b.updatedAt || b.savedAt) - new Date(a.updatedAt || a.savedAt)),
    [snapshot.projects]
  );

  // Derived synchronously from (token, snapshot.forToken) rather than
  // waiting for the effect above to flip snapshot.phase to "loading" —
  // an effect's closure is fixed at the render that scheduled it, so a
  // *consumer's* effect (e.g. Roadmap.jsx deciding whether to regenerate
  // a plan) can otherwise run once with a stale "not loading" reading
  // before this hook's own effect has had a chance to update the store,
  // racing ahead on an empty project list. This is true from the very
  // first render whenever there's a token we haven't loaded data for yet.
  const loading = Boolean(token) && (snapshot.forToken !== token || snapshot.phase === "loading");

  return {
    projects,
    loading,
    error: snapshot.phase === "error",
    getProject: (id) => snapshot.projects.find((p) => p.id === id) || null,
    saveProblem,
    savePlan,
    setStatus,
    toggleTask,
    removeProject,
  };
}

/** Percent of roadmap tasks checked off for a project, or null if no plan yet. */
export function planProgress(project) {
  if (!project?.plan?.roadmap?.length) return null;
  let total = 0;
  let done = 0;
  project.plan.roadmap.forEach((stage, si) => {
    (stage.tasks || []).forEach((_, ti) => {
      total += 1;
      if (project.taskProgress?.[`${si}-${ti}`]) done += 1;
    });
  });
  if (total === 0) return null;
  return Math.round((done / total) * 100);
}
