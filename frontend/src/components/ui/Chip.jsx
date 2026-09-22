import styles from "./Chip.module.css";

/**
 * Chip is either static (skill/tech tag) or interactive (onClick supplied,
 * e.g. example-search prompts on the Home page).
 */
export default function Chip({ children, onClick, active = false, className = "" }) {
  const cls = [styles.chip, active && styles.active, onClick && styles.clickable, className]
    .filter(Boolean)
    .join(" ");

  if (onClick) {
    return (
      <button type="button" className={cls} onClick={onClick}>
        {children}
      </button>
    );
  }

  return <span className={cls}>{children}</span>;
}
