import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Badge from "../components/ui/Badge.jsx";
import Button from "../components/ui/Button.jsx";
import ProgressBar from "../components/ui/ProgressBar.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonLine } from "../components/ui/Skeleton.jsx";
import RoadmapStage from "../components/roadmap/RoadmapStage.jsx";
import ResourceCard from "../components/resources/ResourceCard.jsx";
import { IconSparkle, IconArrowRight, IconDownload } from "../components/ui/icons.jsx";
import { generatePlan, exportRoadmapPptx, apiErrorMessage } from "../api/client.js";
import { useProjects, getCachedProblem, planProgress } from "../hooks/useProjects.js";
import styles from "./Roadmap.module.css";

export default function Roadmap() {
  const { id } = useParams();
  const { state } = useLocation();
  const navigate = useNavigate();
  const { projects, savePlan, toggleTask, loading: projectsLoading } = useProjects();

  const project = projects.find((p) => p.id === id);
  const problem = state?.problem || getCachedProblem(id) || project;

  const [plan, setPlan] = useState(null);
  const [status, setStatus] = useState("loading");
  const [errorMessage, setErrorMessage] = useState(null);
  const [regenToken, setRegenToken] = useState(0);
  const [exportStatus, setExportStatus] = useState("idle"); // idle | loading | error
  const [exportError, setExportError] = useState(null);

  useEffect(() => {
    // projects load asynchronously from the backend now (unlike the old
    // localStorage version, which was synchronous) — wait for that to
    // settle before deciding whether a plan already exists. Deciding on a
    // still-empty `projects` would call the real Gemini API (and burn
    // quota) to regenerate a plan that's actually already saved.
    if (projectsLoading) return;

    const cachedPlan = projects.find((p) => p.id === id)?.plan;
    if (cachedPlan && regenToken === 0) {
      setPlan(cachedPlan);
      setStatus("done");
      return;
    }
    const problemText = problem?.problem_statement || problem?.summary;
    if (!problemText) {
      setStatus("missing");
      return;
    }
    let cancelled = false;
    setStatus("loading");
    setErrorMessage(null);
    generatePlan(problemText)
      .then(async (data) => {
        if (cancelled) return;
        setPlan(data);
        await savePlan(id, data);
        if (cancelled) return;
        setStatus("done");
      })
      .catch((err) => {
        if (cancelled) return;
        // The backend gives a real, specific reason (e.g. Gemini quota
        // exceeded) — surface that instead of a generic "can't reach the
        // server" message, which is actively misleading when the server
        // is reachable and responded with a clear error.
        setErrorMessage(apiErrorMessage(err, "Could not generate a roadmap. Try again."));
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, regenToken, projectsLoading]);

  const progress = useMemo(() => planProgress(project), [project]);

  async function handleExportPptx() {
    setExportStatus("loading");
    setExportError(null);
    try {
      await exportRoadmapPptx({
        problemTitle: problem?.title || "Roadmap",
        problemStatement: problem?.problem_statement || problem?.summary || "",
        source: problem?.source,
        hackathonName: problem?.hackathon_name,
        plan,
      });
      setExportStatus("idle");
    } catch (err) {
      setExportError(apiErrorMessage(err, "Could not export the PPT. Try again."));
      setExportStatus("error");
    }
  }

  if (status === "missing") {
    return (
      <main className="page be-scope">
        <div className="container">
          <EmptyState
            title="Pick a problem first"
            description="Roadmaps are generated for a specific problem statement. Head to Discover, open a problem, then hit Generate Roadmap."
            action={
              <Button to="/discover" size="sm">
                Go to Discover
              </Button>
            }
          />
        </div>
      </main>
    );
  }

  return (
    <main className="page be-scope">
      <div className="container">
        <button className={styles.back} onClick={() => navigate(-1)}>
          ← Back
        </button>

        <div className={styles.header}>
          <span className="eyebrow">
            <IconSparkle width={13} height={13} /> Planning Agent
          </span>
          <h1 className={styles.h1}>{problem?.title || "Your roadmap"}</h1>
          <div className={styles.headerMeta}>
            {problem?.source && <Badge tone="sky">{problem.source}</Badge>}
            {status === "done" && (
              <Button variant="ghost" size="sm" onClick={() => setRegenToken((t) => t + 1)}>
                Regenerate roadmap
              </Button>
            )}
          </div>
          {progress !== null && (
            <div className={styles.progressWrap}>
              <ProgressBar value={progress} label="Overall progress" />
            </div>
          )}
        </div>

        {status === "loading" && (
          <div className={styles.loading}>
            <div className={styles.loadingDot} />
            <div>
              <p className={styles.loadingText}>The planning agent is drafting your roadmap…</p>
              <SkeletonLine width="60%" height={14} />
            </div>
          </div>
        )}

        {status === "error" && (
          <ErrorState
            title="Couldn't generate a roadmap"
            description={errorMessage || "Something went wrong generating this roadmap. Try again."}
            onRetry={() => setRegenToken((t) => t + 1)}
          />
        )}

        {status === "done" && plan && (
          <div className={styles.layout}>
            <div className={styles.stages}>
              {plan.roadmap?.length > 0 && (
                <div className={styles.stagesHead}>
                  <span className="be-label">{plan.roadmap.length} phases</span>
                  <span className="be-dim" style={{ flex: 1 }} />
                </div>
              )}
              {(plan.roadmap || []).map((stage, i) => (
                <RoadmapStage
                  key={i}
                  stage={stage}
                  index={i}
                  isLast={i === plan.roadmap.length - 1}
                  taskProgress={project?.taskProgress}
                  onToggleTask={(key) => toggleTask(id, key)}
                />
              ))}
              {(!plan.roadmap || plan.roadmap.length === 0) && (
                <EmptyState title="No roadmap stages returned" description="Try regenerating the roadmap." />
              )}

              {(plan.existing_solutions?.length > 0 || plan.differentiation_ideas?.length > 0) && (
                <section className={styles.competitive}>
                  <h3 className={styles.sideTitle}>Existing solutions &amp; differentiation</h3>
                  <p className={styles.competitiveCaveat}>
                    From Gemini's general training knowledge, not live-verified market research — worth
                    double-checking yourself before relying on it.
                  </p>

                  {plan.existing_solutions?.length > 0 && (
                    <div className={styles.competitiveBlock}>
                      <h4 className={styles.competitiveBlockTitle}>Existing solutions</h4>
                      <ul className={styles.competitiveList}>
                        {plan.existing_solutions.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {plan.differentiation_ideas?.length > 0 && (
                    <div className={styles.competitiveBlock}>
                      <h4 className={styles.competitiveBlockTitle}>Differentiation ideas</h4>
                      <ul className={styles.competitiveList}>
                        {plan.differentiation_ideas.map((item, i) => (
                          <li key={i}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </section>
              )}
            </div>

            <aside className={styles.side}>
              <h3 className={styles.sideTitle}>Starter resources</h3>
              {plan.resources && plan.resources.length > 0 ? (
                <div className={["be-crop", styles.resources].join(" ")}>
                  {plan.resources.map((r, i) => (
                    <ResourceCard key={i} resource={r} />
                  ))}
                </div>
              ) : (
                <p className={styles.noResources}>
                  The resource agent didn't return anything for this problem yet.
                </p>
              )}

              <div className="be-dim" />

              <Button
                variant="secondary"
                size="sm"
                fullWidth
                onClick={handleExportPptx}
                disabled={exportStatus === "loading"}
                icon={<IconDownload width={15} height={15} />}
              >
                {exportStatus === "loading" ? "Preparing PPT…" : "Export as PPT"}
              </Button>
              {exportStatus === "error" && <p className={styles.localNote}>{exportError}</p>}

              <Button
                to="/projects"
                variant="secondary"
                size="sm"
                fullWidth
                icon={<IconArrowRight width={15} height={15} />}
              >
                View in My Projects
              </Button>
              <p className={styles.localNote}>Progress and roadmap are saved to your account.</p>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
