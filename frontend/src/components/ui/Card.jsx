import styles from "./Card.module.css";

export default function Card({ as: Tag = "div", interactive = false, className = "", children, ...rest }) {
  const cls = [styles.card, interactive && styles.interactive, className].filter(Boolean).join(" ");
  return (
    <Tag className={cls} {...rest}>
      {children}
    </Tag>
  );
}
