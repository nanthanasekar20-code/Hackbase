import { useState } from "react";
import { Link } from "react-router-dom";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { forgotPassword, apiErrorMessage } from "../api/client.js";
import styles from "./AuthForm.module.css";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState(null);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await forgotPassword(email);
      setSent(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not send the reset email."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="page">
      <div className="container">
        <div className={styles.wrap}>
          <div className={styles.header}>
            <span className="eyebrow">Reset password</span>
            <h1>Forgot your password?</h1>
          </div>

          <Card className={styles.card}>
            {sent ? (
              <p>If an account exists for that email, a reset link has been sent. Check your inbox.</p>
            ) : (
              <form onSubmit={handleSubmit}>
                {error && <p className={styles.error}>{error}</p>}
                <p className={styles.hint}>
                  Enter the email on your account and we'll send you a link to set a new password.
                </p>

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

                <Button type="submit" fullWidth disabled={submitting}>
                  {submitting ? "Sending…" : "Send reset link"}
                </Button>
              </form>
            )}
          </Card>

          <p className={styles.footer}>
            <Link to="/login">Back to sign in</Link>
          </p>
        </div>
      </div>
    </main>
  );
}
