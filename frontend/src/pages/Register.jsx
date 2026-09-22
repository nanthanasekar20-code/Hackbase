import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { apiErrorMessage } from "../api/client.js";
import styles from "./AuthForm.module.css";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(email, password, fullName || null);
      // "/tracking" is admin-only now — "/" works for every account.
      navigate("/", { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err, "Could not create an account."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <div className={styles.wrap}>
          <div className={styles.header}>
            <span className="eyebrow">Create account</span>
            <h1>Get started</h1>
          </div>

          <Card className={styles.card}>
            <form onSubmit={handleSubmit}>
              {error && <p className={styles.error}>{error}</p>}

              <div className={styles.field}>
                <label htmlFor="fullName">Name (optional)</label>
                <input
                  id="fullName"
                  type="text"
                  autoComplete="name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

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
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <Button type="submit" fullWidth disabled={submitting}>
                {submitting ? "Creating account…" : "Create account"}
              </Button>
            </form>
          </Card>

          <p className={styles.footer}>
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </main>
  );
}
