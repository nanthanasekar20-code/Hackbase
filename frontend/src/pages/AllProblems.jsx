import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Button from "../components/ui/Button.jsx";
import ProblemCard from "../components/problem/ProblemCard.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonCard } from "../components/ui/Skeleton.jsx";
import { IconArrowRight } from "../components/ui/icons.jsx";
import { getProblems } from "../api/client.js";
import { cacheProblem } from "../hooks/useProjects.js";
import styles from "./AllProblems.module.css";

const PAGE_SIZE = 20;

/**
 * A true flat browse-all over the whole problem corpus — distinct from
 * /discover, which is search-box-first and only shows anything once you
 * type a query. Page number lives in the URL (?page=N) so it survives a
 * refresh/back-navigation, same pattern as Discover's ?q=.
 */
export default function AllProblems() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const page = Math.max(1, parseInt(searchParams.get("page"), 10) || 1);

  const [state, setState] = useState({ status: "loading", problems: [], total: 0 });

  useEffect(() => {
    let cancelled = false;
    setState((prev) => ({ ...prev, status: "loading" }));
    getProblems({ page, pageSize: PAGE_SIZE })
      .then((data) => {
        if (cancelled) return;
        const problems = data?.problems || [];
        // Without this, ProblemDetails has nothing to fall back on when
        // React Router's location.state isn't available — opening a card
        // in a new tab, or landing on /problem/:id after a page refresh —
        // and shows "We couldn't find that problem" even though it's
        // right there in the corpus. Discover.jsx already does this on
        // every result it fetches; this page was the one gap.
        problems.forEach(cacheProblem);
        setState({ status: "done", problems, total: data?.total || 0 });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ status: "error", problems: [], total: 0 });
      });
    return () => {
      cancelled = true;
    };
  }, [page]);

  const totalPages = Math.max(1, Math.ceil(state.total / PAGE_SIZE));

  function goToPage(next) {
    if (next < 1 || next > totalPages) return;
    setSearchParams({ page: String(next) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <main className="page be-scope">
      <div className="container">
        <button className={styles.back} onClick={() => navigate(-1)}>
          ← Back
        </button>

        <div className={styles.header}>
          <span className="eyebrow">Full corpus</span>
          <h1 className={styles.h1}>Every problem statement</h1>
          <p>
            Every problem HackBase has indexed, in one flat list — no search query required. Use Discover instead
            if you know roughly what you're looking for.
          </p>
          {state.status === "done" && state.total > 0 && (
            <span className={["be-label", styles.resultCount].join(" ")}>{state.total} total</span>
          )}
        </div>

        {state.status === "loading" && (
          <div className={styles.grid}>
            {Array.from({ length: 6 }).map((_, i) => (
              <SkeletonCard key={i} />
            ))}
          </div>
        )}

        {state.status === "error" && (
          <ErrorState description="Couldn't load problems from the HackBase API right now. Try again." />
        )}

        {state.status === "done" && state.problems.length === 0 && (
          <EmptyState
            title="No problems to show"
            description="The corpus doesn't have anything indexed yet."
            action={
              <Button to="/discover" size="sm">
                Try Discover instead
              </Button>
            }
          />
        )}

        {state.status === "done" && state.problems.length > 0 && (
          <>
            <div className={styles.grid}>
              {state.problems.map((p) => (
                <ProblemCard key={p.id} result={p} />
              ))}
            </div>

            <div className={styles.pagination}>
              <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => goToPage(page - 1)}>
                ← Previous
              </Button>
              <span className={styles.pageInfo}>
                Page {page} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => goToPage(page + 1)}
                icon={<IconArrowRight width={15} height={15} />}
              >
                Next
              </Button>
            </div>
          </>
        )}
      </div>
    </main>
  );
}
