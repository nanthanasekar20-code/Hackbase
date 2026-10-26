import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import Badge from "../components/ui/Badge.jsx";
import Chip from "../components/ui/Chip.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonLine } from "../components/ui/Skeleton.jsx";
import { IconExternal } from "../components/ui/icons.jsx";
import { getLiveHackathons } from "../api/client.js";
import styles from "./LiveHackathons.module.css";

/**
 * Full "Live Hackathons" listing — the destination for the pulsing-dot
 * teaser on Home. Was previously rendered inline on Home itself; moved
 * here unchanged (same loading/error/empty states, same row markup) so
 * Home can stay a quick scan rather than a long scroll, see
 * app/core/live_hackathons.py for where this data comes from (a separate,
 * periodically-refreshed feed — not the RAG/problem-corpus pipeline).
 *
 * Title search + platform filter are applied client-side over the one
 * fetch below — same convention Discover's own chip/score filters already
 * use (filter whatever's already in memory, no new request per
 * keystroke), appropriate here too since the whole feed is a few dozen
 * items. GET /live-hackathons also accepts source/search server-side now
 * (see backend app/api/routes/live_hackathons.py) for any caller that
 * does want that — this page just doesn't need to be one.
 */
export default function LiveHackathons() {
  const navigate = useNavigate();
  const [liveHackathons, setLiveHackathons] = useState({ status: "loading", hackathons: [], perSourceCounts: {} });
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");

  useEffect(() => {
    let cancelled = false;
    getLiveHackathons()
      .then((data) => {
        if (cancelled) return;
        setLiveHackathons({
          status: "done",
          hackathons: data?.hackathons || [],
          perSourceCounts: data?.per_source_counts || {},
        });
      })
      .catch(() => {
        if (cancelled) return;
        setLiveHackathons({ status: "error", hackathons: [], perSourceCounts: {} });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Only a platform that actually has at least one open hackathon right
  // now gets a chip — same "don't show a filter with nothing behind it"
  // rule Discover's own facet groups use.
  const availableSources = useMemo(
    () =>
      Object.entries(liveHackathons.perSourceCounts)
        .filter(([, count]) => count > 0)
        .map(([source]) => source),
    [liveHackathons.perSourceCounts]
  );

  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return liveHackathons.hackathons.filter((h) => {
      if (sourceFilter && h.source !== sourceFilter) return false;
      if (needle && !(h.title || "").toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [liveHackathons.hackathons, sourceFilter, search]);

  const hasActiveFilter = Boolean(search || sourceFilter);

  function clearFilters() {
    setSearch("");
    setSourceFilter("");
  }

  return (
    <main className="page be-scope">
      <div className="container">
        <button className={styles.back} onClick={() => navigate(-1)}>
          ← Back
        </button>

        <div className={styles.header}>
          <span className="eyebrow">
            <IconExternal width={13} height={13} /> Live Hackathons
          </span>
          <h1 className={styles.h1}>Open for registration right now</h1>
          <p>Pulled periodically from Devpost, MLH, Devfolio, Taikai, HackerEarth, Hack2Skill and AngelHack.</p>
          {liveHackathons.status === "done" && liveHackathons.hackathons.length > 0 && (
            <span className={["be-label", styles.resultCount].join(" ")}>{filtered.length} open</span>
          )}
        </div>

        {liveHackathons.status === "done" && liveHackathons.hackathons.length > 0 && (
          <div className={styles.filterBar}>
            <input
              className={styles.searchInput}
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title…"
              aria-label="Search live hackathons by title"
            />
            {availableSources.length > 1 && (
              <div className={styles.sourceChips}>
                {availableSources.map((source) => (
                  <Chip
                    key={source}
                    active={sourceFilter === source}
                    onClick={() => setSourceFilter((prev) => (prev === source ? "" : source))}
                  >
                    {source}
                  </Chip>
                ))}
              </div>
            )}
            {hasActiveFilter && (
              <button type="button" className={styles.clearFilters} onClick={clearFilters}>
                Clear filters
              </button>
            )}
          </div>
        )}

        {liveHackathons.status === "loading" && (
          <div className={styles.liveList}>
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className={styles.liveRow}>
                <SkeletonLine width="40%" height={16} />
              </div>
            ))}
          </div>
        )}

        {liveHackathons.status === "error" && (
          <ErrorState description="Couldn't load live hackathons from the HackBase API right now." />
        )}

        {liveHackathons.status === "done" && liveHackathons.hackathons.length === 0 && (
          <EmptyState
            title="No live hackathons right now"
            description="HackBase checks several platforms periodically for hackathons currently open for registration — nothing to show from the latest check."
          />
        )}

        {liveHackathons.status === "done" && liveHackathons.hackathons.length > 0 && filtered.length === 0 && (
          <EmptyState
            title="No hackathons match these filters"
            description="Try a different search term, or clear the platform filter."
            action={
              <button type="button" className={styles.clearFilters} onClick={clearFilters}>
                Clear filters
              </button>
            }
          />
        )}

        {liveHackathons.status === "done" && filtered.length > 0 && (
          <div className={["be-crop", styles.liveList].join(" ")}>
            {filtered.map((h, i) => (
              <a
                key={`${h.source}-${h.url}-${i}`}
                className={styles.liveRow}
                href={h.url}
                target="_blank"
                rel="noreferrer"
              >
                <Badge tone="sky">{h.source}</Badge>
                <span className={styles.liveTitle}>{h.title}</span>
                {h.deadline && <span className={styles.liveDeadline}>{h.deadline}</span>}
                <IconExternal width={15} height={15} className={styles.liveIcon} />
              </a>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
