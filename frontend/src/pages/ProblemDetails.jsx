import { useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import Badge from "../components/ui/Badge.jsx";
import Chip from "../components/ui/Chip.jsx";
import Button from "../components/ui/Button.jsx";
import ScoreBadge from "../components/ui/ScoreBadge.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import {
  IconBookmark,
  IconCheck,
  IconArrowRight,
  IconSearch,
  IconDownload,
  IconExternal,
} from "../components/ui/icons.jsx";
import { useProjects, getCachedProblem } from "../hooks/useProjects.js";
import { useAuth } from "../hooks/useAuth.js";
import { problemId } from "../utils/slug.js";
import { exportFavoritePptx, viewFavoritePdf, apiErrorMessage } from "../api/client.js";
import styles from "./ProblemDetails.module.css";

// The nine Gemini resume-value enrichment fields (see backend
// scripts/enrich_resume_value.py), rendered as a scannable table instead
// of nine separate circular badges — a row per field, shown only when
// that field is actually present (a problem not yet (re-)enriched just
// omits whichever ones it doesn't have yet). `inverted` marks
// hardware_requirement_score as the one field where a higher number isn't
// "better", just "needs more specialized hardware".
const PORTFOLIO_SCORE_FIELDS = [
  { field: "resume_value_score", label: "Resume value" },
  { field: "industry_relevance_score", label: "Industry relevance" },
  { field: "technical_depth_score", label: "Technical depth" },
  { field: "novelty_score", label: "Novelty" },
  { field: "dataset_availability_score", label: "Dataset availability" },
  { field: "hardware_requirement_score", label: "Hardware needed", inverted: true },
  { field: "competition_potential_score", label: "Competition potential" },
  { field: "social_impact_score", label: "Social impact" },
  { field: "feasibility_score", label: "Hackathon feasibility" },
];

export default function ProblemDetails() {
  const { id } = useParams();
  const location = useLocation();
  const { state } = location;
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { saveProblem, getProject } = useProjects();
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [pptxStatus, setPptxStatus] = useState("idle"); // idle | loading | error
  const [pdfStatus, setPdfStatus] = useState("idle"); // idle | loading | error

  const result = useMemo(() => state || getCachedProblem(id), [state, id]);
  const project = isAuthenticated ? getProject(id) : null;
  const alreadySaved = saved || Boolean(project);
  const hasRoadmap = Boolean(project?.plan);

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

  async function downloadPptx() {
    setPptxStatus("loading");
    try {
      await exportFavoritePptx(thisId);
      setPptxStatus("idle");
    } catch (err) {
      setPptxStatus("error");
      // eslint-disable-next-line no-console
      console.error(apiErrorMessage(err, "Could not export the PPT."));
    }
  }

  async function viewPdf() {
    setPdfStatus("loading");
    try {
      await viewFavoritePdf(thisId);
      setPdfStatus("idle");
    } catch (err) {
      setPdfStatus("error");
      // eslint-disable-next-line no-console
      console.error(apiErrorMessage(err, "Could not open the PPT."));
    }
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
              {/* result.domain is a real array (a problem can carry several
                  domain tags) — rendering it directly as one Badge's
                  children smushed every tag into a single unreadable
                  string with no separators. One badge per tag instead;
                  category is the fallback only when there's no domain
                  list at all. */}
              {(Array.isArray(result.domain) ? result.domain : [result.domain || result.category].filter(Boolean)).map(
                (d) => (
                  <Badge key={d} tone="sand">
                    {d}
                  </Badge>
                )
              )}
              {result.difficulty && <Badge tone="clay">{result.difficulty}</Badge>}
            </div>
            <h1 className={styles.title}>{result.title}</h1>
          </div>
          {typeof result.score === "number" && (
            // Only a RAG search result (POST /search) ever carries a real
            // `score` — a problem reached via Domains/AllProblems' plain
            // GET /problems browse was never ranked against a query, so
            // there's nothing honest to show here. A hollow "—" ring would
            // look like a broken/missing value rather than "not applicable".
            <div className={styles.scoreCol}>
              <ScoreBadge score={result.score} size={72} />
              <span className={styles.scoreLabel}>Match score</span>
            </div>
          )}
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
                <table className={styles.scoreTable}>
                  <tbody>
                    {PORTFOLIO_SCORE_FIELDS.filter(({ field }) => result[field] != null).map(
                      ({ field, label, inverted }) => (
                        <tr key={field}>
                          <th scope="row" className={styles.scoreTableLabel}>
                            {label}
                          </th>
                          <td className={styles.scoreTableBarCell}>
                            <div className={styles.scoreTableBarTrack}>
                              <div
                                className={[styles.scoreTableBarFill, inverted && styles.scoreTableBarFillInverted]
                                  .filter(Boolean)
                                  .join(" ")}
                                style={{ width: `${(result[field] / 10) * 100}%` }}
                              />
                            </div>
                          </td>
                          <td className={styles.scoreTableValue}>{result[field].toFixed(1)}</td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
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
                {hasRoadmap ? "View roadmap" : "Generate roadmap"}
              </Button>
              {hasRoadmap && (
                <Button
                  fullWidth
                  variant="secondary"
                  onClick={viewPdf}
                  disabled={pdfStatus === "loading"}
                  icon={<IconExternal width={16} height={16} />}
                >
                  {pdfStatus === "loading" ? "Opening…" : "View PPT"}
                </Button>
              )}
              {hasRoadmap && (
                <Button
                  fullWidth
                  variant="secondary"
                  onClick={downloadPptx}
                  disabled={pptxStatus === "loading"}
                  icon={<IconDownload width={16} height={16} />}
                >
                  {pptxStatus === "loading" ? "Preparing PPT…" : "Download PPT"}
                </Button>
              )}
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
              {pdfStatus === "error" && <p className={styles.localNote}>Could not open the PPT — try again.</p>}
              {pptxStatus === "error" && <p className={styles.localNote}>Could not download the PPT — try again.</p>}
              {!saveError && pdfStatus !== "error" && pptxStatus !== "error" && (
                <p className={styles.localNote}>Saved to your account — see My Projects.</p>
              )}
            </div>
          </aside>
        </div>
      </div>
    </main>
  );
}
