import { useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Badge from "../components/ui/Badge.jsx";
import Chip from "../components/ui/Chip.jsx";
import Button from "../components/ui/Button.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import { IconBookmark, IconCheck, IconArrowRight, IconSearch } from "../components/ui/icons.jsx";
import { useProjects, getCachedProblem } from "../hooks/useProjects.js";
import { useAuth } from "../hooks/useAuth.js";
import { problemId } from "../utils/slug.js";
import styles from "./ProblemDetails.module.css";

export default function ProblemDetails() {
  const { id } = useParams();
  const location = useLocation();
  const { state } = location;
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { saveProblem, getProject } = useProjects();
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const result = useMemo(() => state || getCachedProblem(id), [state, id]);
  const project = isAuthenticated ? getProject(id) : null;
  const alreadySaved = saved || Boolean(project);

  if (!result) {
    return (
      <main className="page">
        <div className="container">
          <EmptyState
            icon={<IconSearch width={22} height={22} />}
            title="We couldn't find that problem"
            description="This can happen after a refresh if it wasn't saved yet. Head back to Discover and search again."
            action={
              <Button to="/discover" size="sm">
                Back to Discover
              </Button>
            }
          />
        </div>
      </main>
    );
  }

  const techs = result.technologies || result.tech_stack || [];
  const skills = result.skills || [];
  const problemText = result.problem_statement || result.summary;
  const matchReason = result.match_reason || result.explanation;
  const thisId = problemId(result);

  async function handleSave() {
    if (!isAuthenticated) {
      navigate("/login", { state: { from: location } });
      return;
    }
    setSaveError(null);
    try {
      await saveProblem(result);
      setSaved(true);
    } catch {
      setSaveError("Could not save this problem — try again.");
    }
  }

  function goRoadmap() {
    const dest = { pathname: `/roadmap/${thisId}` };
    if (!isAuthenticated) {
      navigate("/login", { state: { from: dest } });
      return;
    }
    navigate(dest.pathname, { state: { problem: result } });
  }

  return (
    <main className="page">
      <div className="container">
        <button className={styles.back} onClick={() => navigate(-1)}>
          ← Back
        </button>

        <div className={styles.headerRow}>
          <div className={styles.headerMain}>
            <div className={styles.tags}>
              {result.source && <Badge tone="sky">{result.source}</Badge>}
              {(result.domain || result.category) && <Badge tone="sand">{result.domain || result.category}</Badge>}
              {result.difficulty && <Badge tone="clay">{result.difficulty}</Badge>}
            </div>
            <h1 className={styles.title}>{result.title}</h1>
          </div>
          <div className={styles.scoreCol}>
            <ScoreBadge score={result.score} size={72} />
            <span className={styles.scoreLabel}>Match score</span>
          </div>
        </div>

        <div className={styles.layout}>
          <div className={styles.main}>
            <section className={styles.block}>
              <h2 className={styles.blockTitle}>Problem statement</h2>
              <p className={styles.problemText}>{problemText || "No description provided."}</p>
            </section>

            {(techs.length > 0 || skills.length > 0) && (
              <section className={styles.block}>
                <h2 className={styles.blockTitle}>Skills & technologies</h2>
                <div className={styles.chipRow}>
                  {techs.map((t) => (
                    <Chip key={t}>{t}</Chip>
                  ))}
                  {skills.map((s) => (
                    <Chip key={s}>{s}</Chip>
                  ))}
                </div>
              </section>
            )}

            {result.resume_value_score != null && (
              <section className={styles.block}>
                <h2 className={styles.blockTitle}>Portfolio value</h2>
                <p className={styles.competitiveCaveat}>
                  A one-time Gemini estimate of this project's value as a resume/portfolio piece — not
                  personalized to you, and not live-verified market data.
                </p>
                <div className={styles.portfolioRow}>
                  <div className={styles.scoreCol}>
                    <ScoreBadge score={result.resume_value_score} size={64} />
                    <span className={styles.scoreLabel}>Resume value</span>
                  </div>
                  {result.industry_relevance_score != null && (
                    <div className={styles.scoreCol}>
                      <ScoreBadge score={result.industry_relevance_score} size={64} />
                      <span className={styles.scoreLabel}>Industry relevance</span>
                    </div>
                  )}
                  {result.technical_depth_score != null && (
                    <div className={styles.scoreCol}>
                      <ScoreBadge score={result.technical_depth_score} size={64} />
                      <span className={styles.scoreLabel}>Technical depth</span>
                    </div>
                  )}
                </div>
              </section>
            )}

            <section className={styles.block}>
              <h2 className={styles.blockTitle}>Why this matches you</h2>
              <p>
                {matchReason ||
                  "This problem was surfaced by HackBase's ranking agent based on semantic similarity between your search query and this problem statement — the closer the match, the higher the score above."}
              </p>
            </section>

            <section className={styles.block}>
              <h2 className={styles.blockTitle}>Related</h2>
              <p>Want to see more like this?</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate(`/discover?q=${encodeURIComponent(result.title)}`)}
                icon={<IconSearch width={16} height={16} />}
              >
                Find similar problems
              </Button>
            </section>
          </div>

          <aside className={styles.side}>
            <div className={styles.actionCard}>
              <h3 className={styles.actionTitle}>Ready to build this?</h3>
              <p className={styles.actionDesc}>
                Generate a phased roadmap with tasks, milestones and starter resources.
              </p>
              <Button fullWidth onClick={goRoadmap} icon={<IconArrowRight width={17} height={17} />}>
                Generate roadmap
              </Button>
              <Button
                fullWidth
                variant={alreadySaved ? "secondary" : "ghost"}
                onClick={handleSave}
                disabled={alreadySaved}
                icon={alreadySaved ? <IconCheck width={16} height={16} /> : <IconBookmark width={16} height={16} />}
              >
                {alreadySaved ? "Saved to My Projects" : isAuthenticated ? "Save problem" : "Log in to save"}
              </Button>
              {saveError && <p className={styles.localNote}>{saveError}</p>}
              {!saveError && <p className={styles.localNote}>Saved to your account — see My Projects.</p>}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
