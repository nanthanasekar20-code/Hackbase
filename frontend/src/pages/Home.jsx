import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchBar from "../components/ui/SearchBar.jsx";
import Chip from "../components/ui/Chip.jsx";
import Button from "../components/ui/Button.jsx";
import ProblemCard from "../components/problem/ProblemCard.jsx";
import GumballMachine from "../components/home/GumballMachine.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonCard } from "../components/ui/Skeleton.jsx";
import { IconSparkle, IconArrowRight, IconRefresh } from "../components/ui/icons.jsx";
import { searchHackathons, getRandomProblems, getLiveHackathons } from "../api/client.js";
import { cacheProblem } from "../hooks/useProjects.js";
import styles from "./Home.module.css";

const EXAMPLES = [
  "AI accessibility tool for rural healthcare",
  "Climate risk dashboard from satellite data",
  "Fraud detection for UPI transactions",
  "Campus mental-health support chatbot",
  "Offline-first crop advisory app",
];

// A broad, real search used to populate "Featured" — not fabricated data,
// just the Search/Ranking agents' current output for a general query.
const FEATURED_QUERY = "innovative hackathon problem statements";

// Module-level, not component state, on purpose: clicking any Featured
// card navigates to /problem/:id, which unmounts Home entirely — without
// this, coming back would always remount from scratch and re-run the
// fixed FEATURED_QUERY search again, silently discarding whatever the
// user had Refreshed to (see handleRefresh below, which also writes
// here). Survives remounts within the same tab/session; resets on an
// actual full page reload, same as any other in-memory module state —
// no backend/persistence needed for what's meant to be a session-only
// convenience. Only ever holds a real completed result (never an error
// state), so "cache has a value" and "cache has a real result worth
// showing immediately" are the same check.
let featuredCache = null;

// Test-only: lets Home.test.jsx reset the module-level cache between test
// cases, so each test's fresh render behaves like a genuine first visit
// instead of leaking a previous test's cached Featured result (the same
// kind of real cross-test leak sessionStorage-backed state needs
// clearing for elsewhere, e.g. Discover.test.jsx).
export function __resetFeaturedCacheForTests() {
  featuredCache = null;
}

export default function Home() {
  const navigate = useNavigate();
  const [featured, setFeatured] = useState(() => featuredCache || { status: "loading", results: [] });
  // Separate from `featured.status` on purpose: refreshing swaps in a new
  // random sample (see handleRefresh) without ever resetting featured back
  // to "loading" itself, so the old cards keep showing the whole time
  // instead of the grid blanking out while the new ones load.
  const [refreshing, setRefreshing] = useState(false);
  // Home only needs the live-hackathons *count* for its teaser now — the
  // full list lives on its own page (see LiveHackathons.jsx).
  const [liveCount, setLiveCount] = useState({ status: "loading", count: 0 });

  useEffect(() => {
    // Already have a real result (the default query's, or a prior
    // Refresh's) cached from before this mount — show it immediately
    // instead of re-fetching, so navigating away and back doesn't lose a
    // Refresh. Only a genuinely first visit this session (featuredCache
    // still null) runs the default query at all.
    if (featuredCache) return;

    let cancelled = false;
    setFeatured({ status: "loading", results: [] });
    searchHackathons(FEATURED_QUERY, 6)
      .then((data) => {
        if (cancelled) return;
        const results = data?.results || [];
        // Without this, opening a Featured card in a new tab (or landing
        // on /problem/:id after a refresh) has nothing to fall back on
        // once React Router's location.state isn't there, and shows "We
        // couldn't find that problem" for a problem that's right there.
        results.forEach(cacheProblem);
        const next = { status: "done", results };
        featuredCache = next;
        setFeatured(next);
      })
      .catch(() => {
        if (cancelled) return;
        // Deliberately not cached — a real failure should retry on the
        // next mount, not keep showing (or re-showing) an error forever.
        setFeatured({ status: "error", results: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getLiveHackathons()
      .then((data) => {
        if (cancelled) return;
        setLiveCount({ status: "done", count: data?.count ?? 0 });
      })
      .catch(() => {
        if (cancelled) return;
        setLiveCount({ status: "error", count: 0 });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function runSearch(query) {
    navigate(`/discover?q=${encodeURIComponent(query)}`);
  }

  // A real random sample (GET /problems/random), not the fixed RAG query
  // above — re-running that same query would always return the same six
  // results, so it's not a "refresh" at all. See backend
  // app/api/routes/problems.py.
  async function handleRefresh() {
    setRefreshing(true);
    try {
      const data = await getRandomProblems(6);
      const results = data?.problems || [];
      results.forEach(cacheProblem); // same "new tab / refresh" fallback as the default query above
      const next = { status: "done", results };
      featuredCache = next; // so this survives navigating away and back (see featuredCache above)
      setFeatured(next);
    } catch {
      // Real failure — leave the current cards (and cache) exactly as
      // they were rather than blanking them for a transient error.
    } finally {
      setRefreshing(false);
    }
  }

  const shownCount = featured.status === "done" ? Math.min(6, featured.results.length) : 0;

  return (
    <main className="be-scope">
      <section className={[styles.hero, "be-grid-bg"].join(" ")}>
        <div className="container">
          <div className={styles.heroInner}>
            <span className="eyebrow">Agentic RAG · Search → Rank → Plan → Resource</span>
            <h1 className={styles.h1}>
              Find the hackathon problem <span className={styles.accent}>worth building.</span>
            </h1>
            <p className={styles.lead}>
              Describe what you want to build, in your own words. HackBase's agents retrieve, rank, and turn
              matching problem statements into a working roadmap — so you spend the weekend building, not
              browsing listings.
            </p>

            <div className={["be-crop", styles.searchWrap].join(" ")}>
              <SearchBar onSubmit={runSearch} autoFocus />
            </div>

            <div className={styles.examples}>
              <span className={["be-label", styles.examplesLabel].join(" ")}>Try</span>
              {EXAMPLES.map((ex) => (
                <Chip key={ex} onClick={() => runSearch(ex)}>
                  {ex}
                </Chip>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="container">
        <button type="button" className={styles.liveTeaser} onClick={() => navigate("/live-hackathons")}>
          <span className={styles.liveIndicator}>
            <span className={styles.liveDot} aria-hidden="true" />
            <span className={styles.liveTag}>Live</span>
          </span>
          <span className={styles.liveTeaserText}>
            {liveCount.status === "done"
              ? `${liveCount.count} hackathon${liveCount.count === 1 ? "" : "s"} open now`
              : "Hackathons open now"}
          </span>
          <IconArrowRight width={14} height={14} />
        </button>

        <div className={["be-dim", styles.divider].join(" ")}>
          <span className="be-label">Search · Discover · Build</span>
        </div>

        <section className="section">
          <div className={styles.sectionHead}>
            <div>
              <span className="eyebrow">
                <IconSparkle width={13} height={13} /> Featured
              </span>
              <h2>Problems worth a look</h2>
              <p>Freshly surfaced by the search and ranking agents.</p>
            </div>
            <div className={styles.sectionHeadRight}>
              {shownCount > 0 && (
                <span className={["be-label", styles.resultCount].join(" ")}>{shownCount} shown</span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
                icon={<IconRefresh width={15} height={15} className={refreshing ? styles.spinning : undefined} />}
              >
                {refreshing ? "Refreshing…" : "Refresh"}
              </Button>
              <Button to="/problems" variant="secondary" size="sm" icon={<IconArrowRight width={16} height={16} />}>
                Browse all
              </Button>
            </div>
          </div>

          {featured.status === "loading" && (
            <div className={styles.skeletonGrid}>
              {Array.from({ length: 3 }).map((_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          )}

          {featured.status === "error" && (
            <ErrorState description="Couldn't load featured problems from the HackBase API right now. Try again, or head to Discover to search directly." />
          )}

          {featured.status === "done" && featured.results.length === 0 && (
            <EmptyState
              title="Featured problems are warming up"
              description="HackBase's index doesn't have results for this yet — search for something specific on Discover instead."
              action={
                <Button to="/discover" size="sm">
                  Go to Discover
                </Button>
              }
            />
          )}

          {featured.status === "done" && featured.results.length > 0 && (
            <div className={styles.grid}>
              {featured.results.slice(0, 6).map((r, i) => {
                const spanClass = i === 0 ? styles.leadCard : i === 1 ? styles.wideCard : styles.card;
                return (
                  <div key={`${r.title}-${i}`} className={spanClass}>
                    <ProblemCard result={r} />
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <GumballMachine />
      </div>
    </main>
  );
}
