import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth.js";

/**
 * Redirects to /login (preserving the intended destination) if not signed
 * in. Pass requireAdmin to also gate on the logged-in user's role — the
 * profile fetch (user, userLoading) is async, so this deliberately waits
 * (renders nothing) rather than deciding on a still-loading profile,
 * which would otherwise briefly bounce a real admin away on every load.
 */
export default function RequireAuth({ children, requireAdmin = false }) {
  const { isAuthenticated, user, userLoading } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (requireAdmin) {
    if (userLoading) return null;
    if (user?.role !== "admin") return <Navigate to="/" replace />;
  }
  return children;
}
