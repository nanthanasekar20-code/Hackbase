import { forwardRef } from "react";
import { Link } from "react-router-dom";
import styles from "./Button.module.css";

/**
 * Shared button primitive. Renders a <button>, or a router <Link> / <a>
 * when `to` / `href` is supplied, so CTAs share one visual language.
 */
const Button = forwardRef(function Button(
  { variant = "primary", size = "md", as, to, href, className = "", icon, fullWidth = false, children, ...rest },
  ref
) {
  const cls = [styles.btn, styles[variant], styles[size], fullWidth && styles.fullWidth, className]
    .filter(Boolean)
    .join(" ");

  if (to) {
    return (
      <Link ref={ref} to={to} className={cls} {...rest}>
        {icon && <span className={styles.icon}>{icon}</span>}
        {children}
      </Link>
    );
  }

  if (href) {
    return (
      <a ref={ref} href={href} className={cls} target="_blank" rel="noreferrer" {...rest}>
        {icon && <span className={styles.icon}>{icon}</span>}
        {children}
      </a>
    );
  }

  const Tag = as || "button";
  return (
    <Tag ref={ref} className={cls} {...rest}>
      {icon && <span className={styles.icon}>{icon}</span>}
      {children}
    </Tag>
  );
});

export default Button;
