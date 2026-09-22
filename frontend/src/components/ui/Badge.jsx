import styles from "./Badge.module.css";

/**
 * Small label used for source / status / category tags.
 * tone: "sky" | "sand" | "clay" | "success" | "warning" | "danger" | "neutral"
 */
export default function Badge({ tone = "neutral", className = "", children }) {
  return <span className={[styles.badge, styles[tone], className].filter(Boolean).join(" ")}>{children}</span>;
}
