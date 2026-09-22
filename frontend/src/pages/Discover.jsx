import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import SearchBar from "../components/ui/SearchBar.jsx";
import Chip from "../components/ui/Chip.jsx";
import DiscoverFilters from "../components/problem/DiscoverFilters.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { IconSearch, IconSpiral } from "../components/ui/icons.jsx";
import { searchHackathons } from "../api/client.js";
import { cacheProblem } from "../hooks/useProjects.js";
import { problemId } from "../utils/slug.js";
import styles from "./Discover.module.css";

const TOP_K = 12;

function addToFacet(map, key, val) {
  if (!val) return;
  if (!map[key]) map[key] = new Set();
  if (Array.isArray(val)) val.forEach((v) => map[key].add(v));
  else map[key].add(val);
}

export default function Discover() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") || "";

  const [status, setStatus] = useState(query ? "loading" : "idle");
  const [results, setResults] = useState([]);
  const [sortBy, setSortBy] = useState("relevance");
  const [active, setActive] = useState({});
  const [reloadToken, setReloadToken] = useState(0);

  // The lab color system needs to reach the navbar too (see
  // experimental-lab.css), but NavBar renders as a SIBLING of this page's
  // <main> (see components/layout/Layout.jsx), not a descendant — so a
  // class on <main> alone can never cascade to it. document.body is a
  // real ancestor of both, so the scope is toggled there instead, only
  // while this page is mounted.
  useEffect(() => {
    document.body.classList.add("lab-scope");
    return () => {
      document.body.classList.remove("lab-scope");
    };
  }, []);

  useEffect(() => {
    if (!query) {
      setStatus("idle");
      setResults([]);
      return;
    }
    let cancelled = false;
    setStatus("loading");
    setActive({});
    searchHackathons(query, TOP_K)
      .then((data) => {
        if (cancelled) return;
        const r = data?.results || [];
        r.forEach(cacheProblem);
        setResults(r);
        setStatus("done");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [query, reloadToken]);

  const facets = useMemo(() => {
    const map = {};
    results.forEach((r) => {
      addToFacet(map, "source", r.source);
      addToFacet(map, "domain", r.domain || r.category);
      addToFacet(map, "difficulty", r.difficulty);
      addToFacet(map, "technologies", r.technologies || r.tech_stack);
    });
    return {
      source: Array.from(map.source || []),
      domain: Array.from(map.domain || []),
      difficulty: Array.from(map.difficulty || []),
      technologies: Array.from(map.technologies || []),
    };
  }, [results]);

  function toggleFacet(key, value) {
    setActive((prev) => {
      const next = { ...prev };
      const set = new Set(next[key] || []);
      set.has(value) ? set.delete(value) : set.add(value);
      next[key] = set;
      return next;
    });
  }

  const filtered = useMemo(() => {
    let list = results.filter((r) => {
      for (const key of ["source", "domain", "difficulty", "technologies"]) {
        const set = active[key];
        if (!set || set.size === 0) continue;
        const field = key === "domain" ? r.domain || r.category : key === "technologies" ? r.technologies || r.tech_stack : r[key];
        const values = Array.isArray(field) ? field : [field];
        if (!values.some((v) => set.has(v))) return false;
      }
      return true;
    });
    if (sortBy === "title") {
      list = [...list].sort((a, b) => (a.title || "").localeCompare(b.title || ""));
    } else {
      list = [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    }
    return list;
  }, [results, active, sortBy]);

  function handleSearch(q) {
    setSearchParams({ q });
  }

  function openResult(r) {
    navigate(`/problem/${problemId(r)}`, { state: r });
  }

  return (
    <main className={["page", styles.paperBg].join(" ")}>
      <div className="container">
        <div className={styles.header}>
          <IconSpiral width={30} height={30} className={styles.spiralMark} aria-hidden="true" />
          <div>
            <span className="eyebrow">Discover</span>
            <h1 className={styles.h1}>What are you trying to build?</h1>
          </div>
        </div>
        <div className={styles.searchWrap}>
          <SearchBar
            value={query}
            onSubmit={handleSearch}
            size="lg"
            loading={status === "loading"}
            placeholder="Describe the problem you want to solve…"
          />
        </div>

        {status === "idle" && (
          <EmptyState
            icon={<IconSearch width={22} height={22} />}
            title="Search to get started"
            description="Describe the kind of problem you want to build — HackBase's search and ranking agents will surface matches."
            className={styles.idleState}
          />
        )}

        {status === "loading" && (
          <div className={styles.skeletonList}>
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={styles.skeletonRow} />
            ))}
          </div>
        )}

        {status === "error" && <ErrorState onRetry={() => setReloadToken((t) => t + 1)} />}

        {status === "done" && results.length === 0 && (
          <EmptyState
            icon={<IconSearch width={22} height={22} />}
            title="No problems matched your search"
            description={`Nothing came back for "${query}". Try broader or different keywords.`}
          />
        )}

        {status === "done" && results.length > 0 && (
          <>
            <div className={styles.statusRow}>
              <span className={styles.statusCount}>{filtered.length}</span>
              <span className={styles.statusLabel}>
                {filtered.length === 1 ? "result" : "results"} ·{" "}
                {sortBy === "relevance" ? "sorted by semantic relevance" : "sorted alphabetically"}
              </span>
            </div>

            <DiscoverFilters
              facets={facets}
              active={active}
              onToggle={toggleFacet}
              sortBy={sortBy}
              onSortChange={setSortBy}
              resultCount={filtered.length}
            />

            {filtered.length === 0 ? (
              <EmptyState
                title="No results match these filters"
                description="Clear a filter to widen your results."
                action={
                  <button className={styles.clearBtn} onClick={() => setActive({})}>
                    Clear filters
                  </button>
                }
              />
            ) : (
              <div className={["lab-stripe", styles.entries].join(" ")}>
                {filtered.map((r, i) => {
                  const id = problemId(r);
                  const tags = [
                    r.source,
                    ...(r.domain || (r.category ? [r.category] : [])),
                    ...(r.technologies || r.tech_stack || []).slice(0, 3),
                  ].filter(Boolean);
                  const hasMatch = typeof r.score === "number";
                  const hasPortfolioValue = typeof r.resume_value_score === "number";
                  return (
                    <article
                      key={`${id}-${i}`}
                      className={styles.entry}
                      tabIndex={0}
                      role="button"
                      onClick={() => openResult(r)}
                      onKeyDown={(e) => (e.key === "Enter" ? openResult(r) : null)}
                    >
                      <span className={styles.entryIndex}>{String(i + 1).padStart(2, "0")}</span>
                      <div className={styles.entryMain}>
                        <h2 className={styles.entryTitle}>{r.title}</h2>
                        {tags.length > 0 && (
                          <div className={styles.entryTags}>
                            {tags.map((t) => (
                              <Chip key={t}>{t}</Chip>
                            ))}
                          </div>
                        )}
                        {r.summary && <p className={styles.entrySummary}>{r.summary}</p>}
                        {(hasMatch || hasPortfolioValue) && (
                          <>
                            <div className={styles.entryDivider} />
                            <div className={styles.entryStats}>
                              {hasMatch && (
                                <div className={styles.stat}>
                                  <span className={styles.statValue}>{Math.round(r.score * 100)}%</span>
                                  <span className={styles.statLabel}>Match</span>
                                </div>
                              )}
                              {hasPortfolioValue && (
                                <div className={styles.stat}>
                                  <span className={[styles.statValue, styles.violet].join(" ")}>
                                    {r.resume_value_score.toFixed(1)}
                                  </span>
                                  <span className={styles.statLabel}>Portfolio value</span>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                      <span className={styles.entryAction}>View →</span>
                    </article>
                  );
                })}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
