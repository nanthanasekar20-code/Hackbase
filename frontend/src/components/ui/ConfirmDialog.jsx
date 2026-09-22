import Button from "./Button.jsx";
import Card from "./Card.jsx";
import styles from "./ConfirmDialog.module.css";

/**
 * Small reusable "are you sure?" modal. Renders nothing when `open` is
 * false. Escape and clicking the overlay both cancel.
 */
export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmVariant = "primary",
  onConfirm,
  onCancel,
}) {
  if (!open) return null;

  return (
    <div
      className={styles.overlay}
      role="presentation"
      onClick={onCancel}
      onKeyDown={(e) => (e.key === "Escape" ? onCancel() : null)}
    >
      <Card
        className={styles.dialog}
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-dialog-title" className={styles.title}>
          {title}
        </h3>
        {description && <p className={styles.desc}>{description}</p>}
        <div className={styles.actions}>
          <Button variant="ghost" size="sm" onClick={onCancel}>
            {cancelLabel}
          </Button>
          <Button variant={confirmVariant} size="sm" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </div>
      </Card>
    </div>
  );
}
