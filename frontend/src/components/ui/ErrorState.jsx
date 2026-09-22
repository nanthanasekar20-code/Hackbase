import Button from "./Button.jsx";
import styles from "./ErrorState.module.css";

export default function ErrorState({
  title = "Something went wrong",
  description = "We couldn't reach the HackBase backend. Check that the API server is running and try again.",
  onRetry,
}) {
  return (
    <div className={styles.wrap} role="alert">
      <div className={styles.icon}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 9v4M12 17h.01M10.29 3.86l-8.18 14.18A1.5 1.5 0 0 0 3.4 20.5h17.2a1.5 1.5 0 0 0 1.3-2.46L13.71 3.86a1.5 1.5 0 0 0-2.6 0Z"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <h3 className={styles.title}>{title}</h3>
      <p className={styles.desc}>{description}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
