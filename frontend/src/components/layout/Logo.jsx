import { Link } from "react-router-dom";
import styles from "./Logo.module.css";

export default function Logo({ onClick }) {
  return (
    <Link to="/" className={styles.logo} onClick={onClick} aria-label="HackBase home">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" className={styles.mark}>
        <rect x="1" y="1" width="26" height="26" rx="8" fill="var(--ink)" />
        <path d="M8 9v10M8 14h12M20 9v10" stroke="var(--sand)" strokeWidth="2.4" strokeLinecap="round" />
        <circle cx="20" cy="9" r="1.4" fill="var(--sky-light)" />
      </svg>
      <span className={styles.word}>
        Hack<span className={styles.accent}>Base</span>
      </span>
    </Link>
  );
}
