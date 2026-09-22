import { readJSON, writeJSON } from "./storage.js";

const TOKEN_KEY = "auth_token";

/**
 * Storage-only half of auth (no React) — split out from hooks/useAuth.js so
 * api/client.js can read the token for its request interceptor without a
 * circular import (client.js <- useAuth.js <- client.js).
 */
export function getAuthToken() {
  return readJSON(TOKEN_KEY, null);
}

export function setAuthToken(token) {
  writeJSON(TOKEN_KEY, token);
}

export function clearAuthToken() {
  writeJSON(TOKEN_KEY, null);
}
