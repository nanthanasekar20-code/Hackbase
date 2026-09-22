import { useEffect, useState } from "react";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { updateProfile, apiErrorMessage } from "../api/client.js";
import { formatDate } from "../utils/format.js";
import formStyles from "./AuthForm.module.css";
import styles from "./Profile.module.css";

export default function Profile() {
  const { user, refreshUser } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setEmail(user.email || "");
    }
  }, [user]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const patch = {};
    if (fullName !== (user?.full_name || "")) patch.full_name = fullName;
    const emailChanged = email !== user?.email;
    const wantsPasswordChange = newPassword.length > 0;

    if (wantsPasswordChange && newPassword !== confirmPassword) {
      setError("New password and confirmation don't match.");
      return;
    }
    if ((emailChanged || wantsPasswordChange) && !currentPassword) {
      setError("Enter your current password to change your email or password.");
      return;
    }

    if (emailChanged) patch.email = email;
    if (wantsPasswordChange) patch.new_password = newPassword;
    if (emailChanged || wantsPasswordChange) patch.current_password = currentPassword;

    if (Object.keys(patch).length === 0) {
      setSuccess(true);
      return;
    }

    setSubmitting(true);
    try {
      await updateProfile(patch);
      await refreshUser();
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setSuccess(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save changes."));
    } finally {
      setSubmitting(false);
    }
  }

  if (!user) {
    return (
      <main className="page">
        <div className="container">
          <div className={formStyles.wrap} />
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <div className="container">
        <div className={formStyles.wrap}>
          <div className={formStyles.header}>
            <span className="eyebrow">Account</span>
            <h1>Profile</h1>
          </div>

          <Card className={formStyles.card}>
            <form onSubmit={handleSubmit}>
              {error && <p className={formStyles.error}>{error}</p>}
              {success && !error && <p className={styles.success}>Saved.</p>}

              <div className={formStyles.field}>
                <label htmlFor="fullName">Full name</label>
                <input id="fullName" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </div>

              <div className={formStyles.field}>
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

              <p className={styles.meta}>Member since {formatDate(user.created_at)}</p>

              <div className={styles.section}>
                <h3 className={styles.sectionTitle}>Change password</h3>
                <p className={styles.sectionDesc}>Leave blank to keep your current password.</p>

                <div className={formStyles.field}>
                  <label htmlFor="newPassword">New password</label>
                  <input
                    id="newPassword"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>

                <div className={formStyles.field}>
                  <label htmlFor="confirmPassword">Confirm new password</label>
                  <input
                    id="confirmPassword"
                    type="password"
                    autoComplete="new-password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>
              </div>

              <div className={formStyles.field}>
                <label htmlFor="currentPassword">Current password</label>
                <input
                  id="currentPassword"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
                <span className={styles.meta}>Required only if you changed your email or password above.</span>
              </div>

              <Button type="submit" fullWidth disabled={submitting}>
                {submitting ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </Card>
        </div>
      </div>
    </main>
  );
}
