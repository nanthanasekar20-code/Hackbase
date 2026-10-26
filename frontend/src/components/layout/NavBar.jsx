import { useEffect, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import Logo from "./Logo.jsx";
import ConfirmDialog from "../ui/ConfirmDialog.jsx";
import { useAuth } from "../../hooks/useAuth.js";
import styles from "./NavBar.module.css";

const BASE_LINKS = [
  { to: "/", label: "Home", end: true },
  { to: "/discover", label: "Discover" },
  { to: "/domains", label: "Domains" },
  { to: "/live-hackathons", label: "Live Hackathons" },
  { to: "/projects", label: "My Projects" },
  { to: "/how-it-works", label: "How It Works" },
];

export default function NavBar() {
  const [open, setOpen] = useState(false);
  const [confirmingLogout, setConfirmingLogout] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { isAuthenticated, user, logout } = useAuth();

  // Admin-only — matches the backend's require_admin gate on /tracking/runs.
  const LINKS = user?.role === "admin" ? [...BASE_LINKS, { to: "/tracking", label: "Tracking" }] : BASE_LINKS;

  function confirmLogout() {
    setConfirmingLogout(false);
    logout();
    navigate("/");
  }

  const displayName = user?.full_name || user?.email?.split("@")[0];

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <header className={styles.header}>
      <div className={[styles.bar, "container"].join(" ")}>
        <Logo />

        <nav className={styles.desktopNav} aria-label="Primary">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => [styles.link, isActive && styles.active].filter(Boolean).join(" ")}
            >
              {link.label}
            </NavLink>
          ))}
          {isAuthenticated ? (
            <>
              <NavLink
                to="/profile"
                className={({ isActive }) => [styles.link, styles.welcome, isActive && styles.active].filter(Boolean).join(" ")}
              >
                {displayName ? `Welcome, ${displayName}` : "Profile"}
              </NavLink>
              <button className={[styles.link, styles.linkButton].join(" ")} onClick={() => setConfirmingLogout(true)}>
                Log out
              </button>
            </>
          ) : (
            <NavLink
              to="/login"
              className={({ isActive }) => [styles.link, isActive && styles.active].filter(Boolean).join(" ")}
            >
              Log in
            </NavLink>
          )}
        </nav>

        <button
          className={styles.toggle}
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          <span className={[styles.bun, open && styles.bunOpenTop].filter(Boolean).join(" ")} />
          <span className={[styles.bun, open && styles.bunOpenMid].filter(Boolean).join(" ")} />
          <span className={[styles.bun, open && styles.bunOpenBot].filter(Boolean).join(" ")} />
        </button>
      </div>

      <div className={[styles.mobileNav, open && styles.mobileOpen].filter(Boolean).join(" ")}>
        <nav aria-label="Primary mobile">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) => [styles.mobileLink, isActive && styles.active].filter(Boolean).join(" ")}
            >
              {link.label}
            </NavLink>
          ))}
          {isAuthenticated ? (
            <>
              <NavLink
                to="/profile"
                className={({ isActive }) => [styles.mobileLink, isActive && styles.active].filter(Boolean).join(" ")}
              >
                {displayName ? `Welcome, ${displayName}` : "Profile"}
              </NavLink>
              <button
                className={[styles.mobileLink, styles.linkButton].join(" ")}
                onClick={() => setConfirmingLogout(true)}
              >
                Log out
              </button>
            </>
          ) : (
            <NavLink
              to="/login"
              className={({ isActive }) => [styles.mobileLink, isActive && styles.active].filter(Boolean).join(" ")}
            >
              Log in
            </NavLink>
          )}
        </nav>
      </div>

      <ConfirmDialog
        open={confirmingLogout}
        title="Log out?"
        description="You'll need to log back in to see My Projects and Tracking."
        confirmLabel="Log out"
        onConfirm={confirmLogout}
        onCancel={() => setConfirmingLogout(false)}
      />
    </header>
  );
}
