import { useState, useEffect } from "react";
import styles from "./SearchBar.module.css";

export default function SearchBar({
  value,
  onSubmit,
  placeholder = "What do you want to build?",
  loading = false,
  size = "lg",
  autoFocus = false,
}) {
  const [query, setQuery] = useState(value ?? "");

  useEffect(() => {
    if (typeof value === "string") setQuery(value);
  }, [value]);

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    onSubmit(trimmed);
  }

  return (
    <form className={[styles.form, styles[size]].join(" ")} onSubmit={handleSubmit} role="search">
      <svg className={styles.icon} width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
        <path d="M21 21L16.65 16.65" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
      <input
        className={styles.input}
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder}
        autoFocus={autoFocus}
        aria-label="Search hackathon problems"
      />
      <button className={styles.submit} type="submit" disabled={loading || !query.trim()}>
        {loading ? <span className={styles.spinner} aria-hidden="true" /> : "Search"}
      </button>
    </form>
  );
}
