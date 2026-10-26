import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import SearchBar from "../components/ui/SearchBar.jsx";
import Chip from "../components/ui/Chip.jsx";
import DiscoverFilters from "../components/problem/DiscoverFilters.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { IconSearch, IconSpiral } from "../components/ui/icons.jsx";
import { searchHackathons, getProblems } from "../api/client.js";
import { cacheProblem } from "../hooks/useProjects.js";
import { problemId } from "../utils/slug.js";
import { SCORE_FIELDS, neutralThreshold, passesScoreThreshold } from "../utils/scoreFields.js";
import styles from "./Discover.module.css";

const TOP_K = 12;
// Plain (non-RAG) browse size when landing here via a domain filter with
// no search text yet (see DOMAIN_ONLY_BROWSE below) — same page-size
// spirit as AllProblems.jsx's flat browse, not a "top matches" count.
const DOMAIN_BROWSE_SIZE = 20;

// Persists the last completed search for this browser tab (sessionStorage,
// not module state — survives a full remount of Discover, which is what
// happens every time React Router unmounts it while you visit another
// page). The NavBar's "Discover" link always points at plain "/discover"
// with no ?q=, so without this, going Discover -> My Projects -> Discover
// would drop back to the empty "Search to get started" state even though
// you never cleared your search. Filters/sort aren't cached — only the
// query + results that were actually the complaint.
const SEARCH_CACHE_KEY = "hackbase_discover_last_search";

function loadCachedSearch() {
  try {
    const raw = sessionStorage.getItem(SEARCH_CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed.query === "string" ? parsed : null;
  } catch {
    return null;
  }
}

function saveCachedSearch(data) {
  try {
    sessionStorage.setItem(SEARCH_CACHE_KEY, JSON.stringify(data));
  } catch {
    // private browsing / storage disabled — just won't persist, not fatal
  }
}

function addToFacet(map, key, val) {
  if (!val) return;
  if (!map[key]) map[key] = new Set();
  if (Array.isArray(val)) val.forEach((v) => map[key].add(v));
  else map[key].add(val);
}

export default function Discover() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlQuery = searchParams.get("q") || "";
  // Set only when arriving via a Domains.jsx card (/discover?domain=<value>)
  // — read once at mount and never written to again (deliberately NOT
  // mutated inside the fetch effect below — an earlier version nulled it
  // out there to "consume" it once, which broke under React 18 StrictMode:
  // dev mode double-invokes a new effect's body, and that first, discarded
  // invocation's mutation was still visible to the second, real one,
  // making it see the domain as already consumed and silently fall back
  // to the plain idle state instead of ever fetching anything — the
  // domain-card-to-Discover handoff looked like it did nothing at all).
  // Safe to re-derive the seeded filter from this on every fresh fetch:
  // a fresh query/retry already resets `active` to a clean slate today
  // regardless, so folding the domain into that reset is no different.
  const initialDomainRef = useRef(searchParams.get("domain") || null);

  // Computed once per mount (not on every render) — the query this mount
  // should show, and whichever cached result set (if any) matches it.
  const restoredRef = useRef(null);
  if (restoredRef.current === null) {
    // A domain-card navigation (?domain=X, no ?q=) is an explicit "browse
    // this domain" intent — it must win over resurrecting whatever query
    // happens to be cached from an earlier, unrelated Discover visit this
    // same session, not get silently clobbered by it.
    const cached = initialDomainRef.current ? null : loadCachedSearch();
    restoredRef.current = { query: urlQuery || cached?.query || "", cache: cached };
  }
  const query = urlQuery || restoredRef.current.query;
  const cacheMatches =
    restoredRef.current.cache && restoredRef.current.cache.query === query ? restoredRef.current.cache : null;

  const [status, setStatus] = useState(cacheMatches ? "done" : query ? "loading" : "idle");
  const [results, setResults] = useState(cacheMatches ? cacheMatches.results : []);
  const [sortBy, setSortBy] = useState("relevance");
  const [active, setActive] = useState({});
  // Score-threshold filters (Novelty >= 7, Hardware needed <= 3, etc.) —
  // kept separate from `active` since these are numeric thresholds, not
  // exact-value toggles. A field only has a key here while its filter is
  // genuinely on; see utils/scoreFields.js's neutralThreshold().
  const [scoreFilters, setScoreFilters] = useState({});
  const [reloadToken, setReloadToken] = useState(0);
  // Only meaningful in domain-browse mode (see below) — GET /problems'
  // real total for the domain, so "20 of 169" can be shown honestly
  // instead of silently capping at one page's worth with no indication
  // there's 149 more.
  const [domainTotal, setDomainTotal] = useState(0);
  const domainPage = Math.max(1, parseInt(searchParams.get("page"), 10) || 1);
  // True once we know this mount is a domain-only browse (no search text)
  // — drives both the fetch effect's branch and what the results header/
  // pagination controls render. initialDomainRef is stable for the whole
  // mount (see its own comment), so this is too.
  const isDomainBrowse = !query && Boolean(initialDomainRef.current);

  // Landed on a bare /discover (e.g. via the NavBar link) but there was a
  // query from earlier this session — put it back in the URL so the fetch
  // effect below picks it up and everything (search box, filters, back
  // button) stays consistent with a real navigation to that search.
  useEffect(() => {
    if (!urlQuery && restoredRef.current.query) {
      setSearchParams({ q: restoredRef.current.query }, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  // Pure read, never mutates initialDomainRef — see that ref's own comment
  // for why mutating it here was the actual bug.
  function activeSeededFromDomain() {
    const domain = initialDomainRef.current;
    return domain ? { domain: new Set([domain]) } : {};
  }

  useEffect(() => {
    if (!query) {
      const domain = initialDomainRef.current;
      if (domain) {
        // Arrived via a Domains.jsx card with no search text yet — a RAG
        // query needs real text to run on, so this does a plain domain
        // browse instead (same GET /problems AllProblems.jsx already
        // uses), rather than leaving Discover on its "Search to get
        // started" idle state for a domain-only visit.
        let cancelled = false;
        setStatus("loading");
        setActive(activeSeededFromDomain());
        getProblems({ domain, page: domainPage, pageSize: DOMAIN_BROWSE_SIZE })
          .then((data) => {
            if (cancelled) return;
            const r = data?.problems || [];
            r.forEach(cacheProblem);
            setResults(r);
            setDomainTotal(data?.total || 0);
            setStatus("done");
          })
          .catch(() => {
            if (cancelled) return;
            setStatus("error");
          });
        return () => {
          cancelled = true;
        };
      }
      setStatus("idle");
      setResults([]);
      return;
    }
    let cancelled = false;
    // If this is the very first render of a restored search, we already
    // seeded `results`/`status` from the cache above — don't flash back to
    // a loading skeleton for a query the user already saw results for.
    // Still do the real fetch underneath so what's shown stays accurate.
    const isRestoredMatch = restoredRef.current?.cache?.query === query && results.length > 0 && status === "done";
    if (!isRestoredMatch) {
      setStatus("loading");
      setActive(activeSeededFromDomain());
      setScoreFilters({});
    }
    searchHackathons(query, TOP_K)
      .then((data) => {
        if (cancelled) return;
        const r = data?.results || [];
        r.forEach(cacheProblem);
        setResults(r);
        setStatus("done");
        saveCachedSearch({ query, results: r });
      })
      .catch(() => {
        if (cancelled) return;
        if (!isRestoredMatch) setStatus("error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, reloadToken, domainPage]);

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

  // Same "don't show a filter with nothing behind it" rule as the facet
  // groups above, applied to the 9 score fields — scoring is still being
  // backfilled across the corpus (see scripts/backfill_missing_score_fields.py),
  // so at any given time only a subset of results may have a given field.
  const availableScoreFields = useMemo(
    () => SCORE_FIELDS.filter((field) => results.some((r) => typeof r[field.key] === "number")),
    [results]
  );

  function toggleFacet(key, value) {
    setActive((prev) => {
      const next = { ...prev };
      const set = new Set(next[key] || []);
      set.has(value) ? set.delete(value) : set.add(value);
      next[key] = set;
      return next;
    });
  }

  // Setting a score field back to its neutral bound (0 for a ≥ filter, 10
  // for a ≤ one) turns the filter off entirely, same as unchecking a chip
  // — there's no "active filter that excludes nothing" state left around.
  function setScoreFilter(field, value) {
    setScoreFilters((prev) => {
      const next = { ...prev };
      if (value === neutralThreshold(field)) delete next[field.key];
      else next[field.key] = value;
      return next;
    });
  }

  function clearAllFilters() {
    setActive({});
    setScoreFilters({});
  }

  const hasActiveFilters =
    Object.values(active).some((set) => set && set.size > 0) || Object.keys(scoreFilters).length > 0;

  const filtered = useMemo(() => {
    let list = results.filter((r) => {
      for (const key of ["source", "domain", "difficulty", "technologies"]) {
        const set = active[key];
        if (!set || set.size === 0) continue;
        const field = key === "domain" ? r.domain || r.category : key === "technologies" ? r.technologies || r.tech_stack : r[key];
        const values = Array.isArray(field) ? field : [field];
        if (!values.some((v) => set.has(v))) return false;
      }
      for (const [key, threshold] of Object.entries(scoreFilters)) {
        const field = SCORE_FIELDS.find((f) => f.key === key);
        if (field && !passesScoreThreshold(r, field, threshold)) return false;
      }
      return true;
    });
    if (sortBy === "title") {
      list = [...list].sort((a, b) => (a.title || "").localeCompare(b.title || ""));
    } else {
      list = [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    }
    return list;
  }, [results, active, scoreFilters, sortBy]);

  function handleSearch(q) {
    setSearchParams({ q });
  }

  const domainTotalPages = Math.max(1, Math.ceil(domainTotal / DOMAIN_BROWSE_SIZE));

  function goToDomainPage(next) {
    if (next < 1 || next > domainTotalPages) return;
    setSearchParams((prev) => {
      const nextParams = new URLSearchParams(prev);
      nextParams.set("page", String(next));
      return nextParams;
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
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
            title={query ? "No problems matched your search" : "No problems in this domain yet"}
            description={
              query
                ? `Nothing came back for "${query}". Try broader or different keywords.`
                : `HackBase doesn't have anything tagged "${searchParams.get("domain")}" yet.`
            }
          />
        )}

        {status === "done" && results.length > 0 && (
          <>
            <div className={styles.statusRow}>
              <span className={styles.statusCount}>{filtered.length}</span>
              <span className={styles.statusLabel}>
                {isDomainBrowse ? (
                  // Honest about pagination: this page's (filtered) count is
                  // not the whole domain — say so, rather than implying
                  // these are the only problems tagged with it (see
                  // Domains.jsx, which shows the real total up front).
                  <>
                    of {domainTotal} in {searchParams.get("domain")} · page {domainPage} of {domainTotalPages}
                  </>
                ) : (
                  <>
                    {filtered.length === 1 ? "result" : "results"} ·{" "}
                    {sortBy === "relevance" ? "sorted by semantic relevance" : "sorted alphabetically"}
                  </>
                )}
              </span>
            </div>

            <DiscoverFilters
              facets={facets}
              active={active}
              onToggle={toggleFacet}
              scoreFields={availableScoreFields}
              scoreFilters={scoreFilters}
              onScoreFilterChange={setScoreFilter}
              hasActiveFilters={hasActiveFilters}
              onClearAll={clearAllFilters}
              sortBy={sortBy}
              onSortChange={setSortBy}
              resultCount={filtered.length}
            />

            {filtered.length === 0 ? (
              <EmptyState
                title="No results match these filters"
                description="Clear a filter to widen your results."
                action={
                  <button className={styles.clearBtn} onClick={clearAllFilters}>
                    Clear filters
                  </button>
                }
              />
            ) : (
              <div className={["lab-stripe", styles.entries].join(" ")}>
                {filtered.map((r, i) => {
                  const id = problemId(r);
                  // De-duped: a real problem can list the same string in
                  // both `domain` and `technologies` (e.g. domain includes
                  // "IoT" and technologies also lists "IoT") — rendering it
                  // twice was both a duplicate React key (console warning)
                  // and a genuinely redundant chip shown to the user.
                  const tags = [
                    ...new Set(
                      [
                        r.source,
                        ...(r.domain || (r.category ? [r.category] : [])),
                        ...(r.technologies || r.tech_stack || []).slice(0, 3),
                      ].filter(Boolean)
                    ),
                  ];
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

            {isDomainBrowse && domainTotalPages > 1 && (
              <div className={styles.pagination}>
                <button
                  className={styles.clearBtn}
                  disabled={domainPage <= 1}
                  onClick={() => goToDomainPage(domainPage - 1)}
                >
                  ← Previous
                </button>
                <span className={styles.pageInfo}>
                  Page {domainPage} of {domainTotalPages}
                </span>
                <button
                  className={styles.clearBtn}
                  disabled={domainPage >= domainTotalPages}
                  onClick={() => goToDomainPage(domainPage + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </main>
  );
}
