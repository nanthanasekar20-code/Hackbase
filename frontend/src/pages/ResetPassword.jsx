import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { IconEye, IconEyeOff } from "../components/ui/icons.jsx";
import { resetPassword, apiErrorMessage } from "../api/client.js";
import styles from "./AuthForm.module.css";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token") || "";

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }

    setSubmitting(true);
    try {
      await resetPassword(token, newPassword);
      setDone(true);
      setTimeout(() => navigate("/login", { replace: true }), 1800);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not reset your password."));
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
            <h1>Set a new password</h1>
          </div>

          <Card className={styles.card}>
            {!token ? (
              <p className={styles.error}>
                This link is missing its reset token. Request a new one from the{" "}
                <Link to="/forgot-password">forgot password</Link> page.
              </p>
            ) : done ? (
              <p>Password updated. Taking you to sign in…</p>
            ) : (
              <form onSubmit={handleSubmit}>
                {error && <p className={styles.error}>{error}</p>}

                <div className={styles.field}>
                  <label htmlFor="newPassword">New password</label>
                  <div className={styles.passwordRow}>
                    <input
                      id="newPassword"
                      type={showPassword ? "text" : "password"}
                      autoComplete="new-password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                    />
                    <button
                      type="button"
                      className={styles.eyeToggle}
                      onClick={() => setShowPassword((v) => !v)}
                      aria-label={showPassword ? "Hide password" : "Show password"}
                      aria-pressed={showPassword}
                    >
                      {showPassword ? <IconEyeOff width={18} height={18} /> : <IconEye width={18} height={18} />}
                    </button>
                  </div>
                </div>

                <div className={styles.field}>
                  <label htmlFor="confirmPassword">Confirm new password</label>
                  <input
                    id="confirmPassword"
                    type={showPassword ? "text" : "password"}
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>

                <Button type="submit" fullWidth disabled={submitting}>
                  {submitting ? "Saving…" : "Set new password"}
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
