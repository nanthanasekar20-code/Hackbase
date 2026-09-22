import { useEffect, useState } from "react";
import Badge from "../components/ui/Badge.jsx";
import Card from "../components/ui/Card.jsx";
import ErrorState from "../components/ui/ErrorState.jsx";
import { SkeletonLine } from "../components/ui/Skeleton.jsx";
import { getTrackingRuns } from "../api/client.js";
import { formatDuration, timeAgo } from "../utils/format.js";
import styles from "./Tracking.module.css";

const EXPERIMENT_LABELS = {
  planning_agent: "Planning Agent",
  resume_value_enrichment: "Resume Value Enrichment",
};

function statusTone(status) {
  if (status === "success") return "success";
  if (status === "failed") return "danger";
  return "neutral";
}

function RunCard({ run }) {
  const params = Object.entries(run.params || {});
  const metrics = Object.entries(run.metrics || {});

  return (
    <Card className={styles.runCard}>
      <div className={styles.runHead}>
        <Badge tone={statusTone(run.status)}>{run.status}</Badge>
        <span className={styles.runTime}>{timeAgo(new Date(run.start_time_ms).toISOString())}</span>
      </div>

      {(params.length > 0 || metrics.length > 0) && (
        <div className={styles.kv}>
          {params.map(([key, value]) => (
            <span className={styles.kvItem} key={`param-${key}`}>
              <span className={styles.kvKey}>{key}</span>
              <span className={[styles.kvVal, "mono"].join(" ")}>{value}</span>
            </span>
          ))}
          {metrics.map(([key, value]) => (
            <span className={styles.kvItem} key={`metric-${key}`}>
              <span className={styles.kvKey}>{key}</span>
              <span className={[styles.kvVal, "mono"].join(" ")}>
                {key === "latency_seconds" ? formatDuration(value) : value}
              </span>
            </span>
          ))}
        </div>
      )}

      {run.error && <p className={styles.error}>{run.error}</p>}
    </Card>
  );
}

export default function Tracking() {
  const [status, setStatus] = useState("loading");
  const [experiments, setExperiments] = useState([]);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    getTrackingRuns(20)
      .then((data) => {
        if (cancelled) return;
        setExperiments(data?.experiments || []);
        setStatus("done");
      })
      .catch(() => {
        if (cancelled) return;
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  return (
    <main className="page">
      <div className="container">
        <div className={styles.header}>
          <span className="eyebrow">Phase 7 · Observability</span>
          <h1>Experiment Tracking</h1>
          <p>
            Real MLflow run history for HackBase's Gemini-backed agents — the Planning Agent and the Resume
            Value enrichment script. Every run below actually happened; nothing here is simulated.
          </p>
        </div>

        {status === "loading" && (
          <div className={styles.grid}>
            {Array.from({ length: 3 }).map((_, i) => (
              <div className={styles.skeletonCard} key={i}>
                <SkeletonLine width="30%" height={20} />
                <SkeletonLine width="100%" height={14} />
                <SkeletonLine width="80%" height={14} />
              </div>
            ))}
          </div>
        )}

        {status === "error" && <ErrorState onRetry={() => setReloadToken((t) => t + 1)} />}

        {status === "done" &&
          experiments.map((exp) => (
            <section className={styles.section} key={exp.name}>
              <h2 className={styles.sectionTitle}>{EXPERIMENT_LABELS[exp.name] || exp.name}</h2>
              {exp.runs.length === 0 ? (
                <p className={styles.emptyNote}>No runs recorded yet.</p>
              ) : (
                <div className={styles.grid}>
                  {exp.runs.map((run) => (
                    <RunCard run={run} key={run.run_id} />
                  ))}
                </div>
              )}
            </section>
          ))}
      </div>
    </main>
  );
}
