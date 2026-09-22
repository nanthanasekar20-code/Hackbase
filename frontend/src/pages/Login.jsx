import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { apiErrorMessage } from "../api/client.js";
import styles from "./AuthForm.module.css";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      // "/tracking" is admin-only now — "/" is a sane default for every
      // account, admin or not, when there's no specific intended destination.
      navigate(location.state?.from?.pathname || "/", { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not log in."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <div className={styles.wrap}>
          <div className={styles.header}>
            <span className="eyebrow">Sign in</span>
            <h1>Welcome back</h1>
          </div>

          <Card className={styles.card}>
            <form onSubmit={handleSubmit}>
              {error && <p className={styles.error}>{error}</p>}

              <div className={styles.field}>
                <label htmlFor="email">Email</label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <Button type="submit" fullWidth disabled={submitting}>
                {submitting ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </Card>

          <p className={styles.footer}>
            No account yet? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>
    </main>
  );
}
