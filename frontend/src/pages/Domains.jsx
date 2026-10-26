import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Card from "../components/ui/Card.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonLine } from "../components/ui/Skeleton.jsx";
import { IconArrowRight } from "../components/ui/icons.jsx";
import { getProblems } from "../api/client.js";
import { DOMAINS } from "../utils/taxonomy.js";
import styles from "./Domains.module.css";

/**
 * One card per taxonomy domain (app/core/taxonomy.py's DOMAINS, mirrored
 * in utils/taxonomy.js) with a real live count — no new backend counting
 * endpoint: GET /problems already returns `total` for a domain-filtered
 * query, so this just asks it once per domain (page_size=1, so each
 * request is as cheap as a count can be without a dedicated endpoint).
 * Clicking a card hands off to Discover's own existing filter state
 * (?domain=<value>) rather than building a second filtering UI here.
 */
export default function Domains() {
  const navigate = useNavigate();
  const [state, setState] = useState({ status: "loading", counts: {} });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, status: "loading" }));
    Promise.all(DOMAINS.map((domain) => getProblems({ domain, pageSize: 1 }).then((data) => [domain, data?.total || 0])))
      .then((pairs) => {
        if (cancelled) return;
        setState({ status: "done", counts: Object.fromEntries(pairs) });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ status: "error", counts: {} });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function openDomain(domain) {
    navigate(`/discover?domain=${encodeURIComponent(domain)}`);
  }

  return (
    <main className="page be-scope">
      <div className="container">
        <button className={styles.back} onClick={() => navigate(-1)}>
          ← Back
        </button>

        <div className={styles.header}>
          <span className="eyebrow">Browse</span>
          <h1 className={styles.h1}>Browse by domain</h1>
          <p>Pick a field to jump straight into Discover, pre-filtered to problems tagged with it.</p>
        </div>

        {state.status === "error" && (
          <ErrorState description="Couldn't load domain counts from the HackBase API right now." />
        )}

        {state.status !== "error" && (
          <div className={styles.grid}>
            {DOMAINS.map((domain) => (
              <Card
                as="button"
                type="button"
                key={domain}
                interactive
                className={styles.domainCard}
                onClick={() => openDomain(domain)}
                disabled={state.status === "loading"}
              >
                <span className={styles.domainName}>{domain}</span>
                <span className={styles.domainMeta}>
                  {state.status === "loading" ? (
                    <SkeletonLine width={60} height={14} />
                  ) : (
                    <span className={styles.domainCount}>
                      {state.counts[domain]} {state.counts[domain] === 1 ? "problem" : "problems"}
                    </span>
                  )}
                  <IconArrowRight width={15} height={15} />
                </span>
              </Card>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
