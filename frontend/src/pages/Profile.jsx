import { useEffect, useState } from "react";
import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import Chip from "../components/ui/Chip.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { updateProfile, verifyPassword, apiErrorMessage } from "../api/client.js";
import { IconEye, IconEyeOff } from "../components/ui/icons.jsx";
import { formatDate } from "../utils/format.js";
import { DOMAINS, SKILL_LEVELS } from "../utils/taxonomy.js";
import formStyles from "./AuthForm.module.css";
import styles from "./Profile.module.css";

function PasswordField({ id, value, onChange, autoComplete, minLength }) {
  const [show, setShow] = useState(false);
  return (
    <div className={formStyles.passwordRow}>
      <input
        id={id}
        type={show ? "text" : "password"}
        autoComplete={autoComplete}
        minLength={minLength}
        value={value}
        onChange={onChange}
      />
      <button
        type="button"
        className={formStyles.eyeToggle}
        onClick={() => setShow((v) => !v)}
        aria-label={show ? "Hide password" : "Show password"}
        aria-pressed={show}
      >
        {show ? <IconEyeOff width={18} height={18} /> : <IconEye width={18} height={18} />}
      </button>
    </div>
  );
}

export default function Profile() {
  const { user, refreshUser } = useAuth();

  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [emailCurrentPassword, setEmailCurrentPassword] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Gated password change: the "new password" fields don't exist in the
  // DOM until the user has proven they know the current one — no fields
  // to immediately fill in and no new_password ever sent without a
  // verified current_password first.
  const [pwUnlocked, setPwUnlocked] = useState(false);
  const [pwCurrentPassword, setPwCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pwError, setPwError] = useState(null);
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwVerifying, setPwVerifying] = useState(false);
  const [pwSubmitting, setPwSubmitting] = useState(false);

  // Optional personalization (see app/rag/retriever.py's ranking boost) —
  // its own independent save action, same as the password section below,
  // so editing it never touches full_name/email and vice versa. Entirely
  // skippable: an untouched Profile leaves both null forever (see
  // backend app/models/user.py), and search behaves identically either way.
  const [interests, setInterests] = useState([]);
  const [skillLevel, setSkillLevel] = useState("");
  const [prefsError, setPrefsError] = useState(null);
  const [prefsSuccess, setPrefsSuccess] = useState(false);
  const [prefsSubmitting, setPrefsSubmitting] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setEmail(user.email || "");
      setInterests(user.interests || []);
      setSkillLevel(user.skill_level || "");
    }
  }, [user]);

  function toggleInterest(domain) {
    setInterests((prev) => (prev.includes(domain) ? prev.filter((d) => d !== domain) : [...prev, domain]));
  }

  function toggleSkillLevel(value) {
    setSkillLevel((prev) => (prev === value ? "" : value));
  }

  function clearPreferences() {
    setInterests([]);
    setSkillLevel("");
  }

  async function handleSavePreferences(e) {
    e.preventDefault();
    setPrefsError(null);
    setPrefsSuccess(false);
    setPrefsSubmitting(true);
    try {
      // interests: [] and skill_level: "" are the explicit "clear" values
      // (see UserUpdate's docstring) — always sending both here (rather
      // than only when changed) is what makes the Clear button above work
      // with this same Save action, no separate "clear and save instantly"
      // path needed.
      await updateProfile({ interests, skill_level: skillLevel });
      await refreshUser();
      setPrefsSuccess(true);
    } catch (err) {
      setPrefsError(apiErrorMessage(err, "Could not save preferences."));
    } finally {
      setPrefsSubmitting(false);
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const patch = {};
    if (fullName !== (user?.full_name || "")) patch.full_name = fullName;
    const emailChanged = email !== user?.email;

    if (emailChanged && !emailCurrentPassword) {
      setError("Enter your current password to change your email.");
      return;
    }

    if (emailChanged) patch.email = email;
    if (emailChanged) patch.current_password = emailCurrentPassword;

    if (Object.keys(patch).length === 0) {
      setSuccess(true);
      return;
    }

    setSubmitting(true);
    try {
      await updateProfile(patch);
      await refreshUser();
      setEmailCurrentPassword("");
      setSuccess(true);
    } catch (err) {
      setError(apiErrorMessage(err, "Could not save changes."));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleVerifyCurrentPassword(e) {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);
    if (!pwCurrentPassword) return;

    setPwVerifying(true);
    try {
      await verifyPassword(pwCurrentPassword);
      setPwUnlocked(true);
    } catch (err) {
      setPwError(apiErrorMessage(err, "Incorrect password."));
    } finally {
      setPwVerifying(false);
    }
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setPwError(null);
    setPwSuccess(false);

    if (newPassword.length < 8) {
      setPwError("New password must be at least 8 characters.");
      return;
    }
    if (newPassword !== confirmPassword) {
      setPwError("New password and confirmation don't match.");
      return;
    }

    setPwSubmitting(true);
    try {
      await updateProfile({ new_password: newPassword, current_password: pwCurrentPassword });
      setPwUnlocked(false);
      setPwCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setPwSuccess(true);
    } catch (err) {
      setPwError(apiErrorMessage(err, "Could not change your password."));
    } finally {
      setPwSubmitting(false);
    }
  }

  function cancelPasswordChange() {
    setPwUnlocked(false);
    setPwCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setPwError(null);
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

              {email !== user.email && (
                <div className={formStyles.field}>
                  <label htmlFor="emailCurrentPassword">Current password</label>
                  <PasswordField
                    id="emailCurrentPassword"
                    autoComplete="current-password"
                    value={emailCurrentPassword}
                    onChange={(e) => setEmailCurrentPassword(e.target.value)}
                  />
                  <span className={styles.meta}>Required to change your email.</span>
                </div>
              )}

              <Button type="submit" fullWidth disabled={submitting}>
                {submitting ? "Saving…" : "Save changes"}
              </Button>
            </form>
          </Card>

          <Card className={[formStyles.card, styles.passwordCard].join(" ")}>
            <h3 className={styles.sectionTitle}>Preferences</h3>
            <p className={styles.sectionDesc}>
              Optional — used only to nudge search results toward topics and difficulty you care about. Leave this
              blank and search behaves exactly the same.
            </p>

            {prefsError && <p className={formStyles.error}>{prefsError}</p>}
            {prefsSuccess && !prefsError && <p className={styles.success}>Saved.</p>}

            <form onSubmit={handleSavePreferences}>
              <div className={formStyles.field}>
                <span className={styles.meta}>Interests</span>
                <div className={styles.chipGrid}>
                  {DOMAINS.map((domain) => (
                    <Chip key={domain} onClick={() => toggleInterest(domain)} active={interests.includes(domain)}>
                      {domain}
                    </Chip>
                  ))}
                </div>
              </div>

              <div className={formStyles.field}>
                <span className={styles.meta}>Skill level</span>
                <div className={styles.chipGrid}>
                  {SKILL_LEVELS.map((level) => (
                    <Chip
                      key={level.value}
                      onClick={() => toggleSkillLevel(level.value)}
                      active={skillLevel === level.value}
                    >
                      {level.label}
                    </Chip>
                  ))}
                </div>
              </div>

              <div className={styles.pwActions}>
                <Button type="submit" disabled={prefsSubmitting}>
                  {prefsSubmitting ? "Saving…" : "Save preferences"}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={clearPreferences}
                  disabled={interests.length === 0 && !skillLevel}
                >
                  Clear
                </Button>
              </div>
            </form>
          </Card>

          <Card className={[formStyles.card, styles.passwordCard].join(" ")}>
            <h3 className={styles.sectionTitle}>Change password</h3>

            {pwError && <p className={formStyles.error}>{pwError}</p>}
            {pwSuccess && !pwError && <p className={styles.success}>Password changed.</p>}

            {!pwUnlocked ? (
              <form onSubmit={handleVerifyCurrentPassword}>
                <p className={styles.sectionDesc}>Enter your current password to change it.</p>
                <div className={formStyles.field}>
                  <label htmlFor="pwCurrentPassword">Current password</label>
                  <PasswordField
                    id="pwCurrentPassword"
                    autoComplete="current-password"
                    value={pwCurrentPassword}
                    onChange={(e) => setPwCurrentPassword(e.target.value)}
                  />
                </div>
                <Button type="submit" fullWidth disabled={pwVerifying || !pwCurrentPassword}>
                  {pwVerifying ? "Checking…" : "Continue"}
                </Button>
              </form>
            ) : (
              <form onSubmit={handleChangePassword}>
                <p className={styles.sectionDesc}>Choose a new password.</p>
                <div className={formStyles.field}>
                  <label htmlFor="newPassword">New password</label>
                  <PasswordField
                    id="newPassword"
                    autoComplete="new-password"
                    minLength={8}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>
                <div className={formStyles.field}>
                  <label htmlFor="confirmPassword">Confirm new password</label>
                  <PasswordField
                    id="confirmPassword"
                    autoComplete="new-password"
                    minLength={8}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                  />
                </div>
                <div className={styles.pwActions}>
                  <Button type="submit" disabled={pwSubmitting}>
                    {pwSubmitting ? "Saving…" : "Update password"}
                  </Button>
                  <Button type="button" variant="ghost" onClick={cancelPasswordChange}>
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </Card>
        </div>
      </div>
    </main>
  );
}
