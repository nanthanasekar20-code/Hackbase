import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import SearchBar from "../components/ui/SearchBar.jsx";
import Chip from "../components/ui/Chip.jsx";
import Button from "../components/ui/Button.jsx";
import ProblemCard from "../components/problem/ProblemCard.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonCard } from "../components/ui/Skeleton.jsx";
import { IconSparkle, IconArrowRight } from "../components/ui/icons.jsx";
import { searchHackathons } from "../api/client.js";
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

export default function Home() {
  const navigate = useNavigate();
  const [featured, setFeatured] = useState({ status: "loading", results: [] });

  useEffect(() => {
    let cancelled = false;
    setFeatured({ status: "loading", results: [] });
    searchHackathons(FEATURED_QUERY, 6)
      .then((data) => {
        if (cancelled) return;
        setFeatured({ status: "done", results: data?.results || [] });
      })
      .catch(() => {
        if (cancelled) return;
        setFeatured({ status: "error", results: [] });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function runSearch(query) {
    navigate(`/discover?q=${encodeURIComponent(query)}`);
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
              <Button to="/discover" variant="secondary" size="sm" icon={<IconArrowRight width={16} height={16} />}>
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
      </div>
    </main>
  );
}
