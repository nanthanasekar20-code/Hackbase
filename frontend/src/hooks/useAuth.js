import { useCallback, useEffect, useSyncExternalStore } from "react";
import { subscribe } from "../utils/storage.js";
import { getAuthToken, setAuthToken, clearAuthToken } from "../utils/authToken.js";
import { loginUser, registerUser, getCurrentUser } from "../api/client.js";

function subscribeToken(onStoreChange) {
  return subscribe(onStoreChange);
}

// --- current-user profile cache: a small module-level store (same shape
// of idea as useProjects.js's project store), keyed by token so switching
// accounts can't leak one user's cached name/email into another's view.
let userStore = { user: null, forToken: null };
const userListeners = new Set();

function setUserStore(patch) {
  userStore = { ...userStore, ...patch };
  userListeners.forEach((l) => l());
}

function subscribeUser(listener) {
  userListeners.add(listener);
  return () => userListeners.delete(listener);
}

function getUserSnapshot() {
  return userStore;
}

async function ensureUserLoaded(token) {
  if (!token) {
    if (userStore.user !== null || userStore.forToken !== null) setUserStore({ user: null, forToken: null });
    return;
  }
  if (userStore.forToken === token && userStore.user) return;
  try {
    const user = await getCurrentUser();
    setUserStore({ user, forToken: token });
  } catch {
    setUserStore({ user: null, forToken: token });
  }
}

/** Reactive across tabs/components, same pattern as useProjects(). */
export function useAuth() {
  const token = useSyncExternalStore(subscribeToken, getAuthToken, getAuthToken);
  const userSnapshot = useSyncExternalStore(subscribeUser, getUserSnapshot, getUserSnapshot);

  useEffect(() => {
    ensureUserLoaded(token);
  }, [token]);

  const login = useCallback(async (email, password) => {
    const { access_token } = await loginUser(email, password);
    setAuthToken(access_token);
    return access_token;
  }, []);

  const register = useCallback(
    async (email, password, fullName) => {
      await registerUser(email, password, fullName);
      return login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    clearAuthToken();
  }, []);

  /** Re-fetches /auth/me — call after a profile update so cached name/email (e.g. NavBar's "Welcome, X") stay current. */
  const refreshUser = useCallback(async () => {
    const user = await getCurrentUser();
    setUserStore({ user, forToken: getAuthToken() });
    return user;
  }, []);

  // Derived synchronously (not from an effect) so a consumer's own effect
  // — e.g. RequireAuth deciding whether an admin-only route is allowed —
  // never runs once with a stale "not loading" reading before this hook's
  // fetch has had a chance to start. Same race class as useProjects.js's
  // `loading` — see that file's comment for the full explanation.
  const userLoading = Boolean(token) && userSnapshot.forToken !== token;

  return {
    token,
    isAuthenticated: Boolean(token),
    user: userSnapshot.user,
    userLoading,
    login,
    register,
    logout,
    refreshUser,
  };
}
