import { useMemo, useState } from "react";
import ProjectCard from "../components/projects/ProjectCard.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Button from "../components/ui/Button.jsx";
import Chip from "../components/ui/Chip.jsx";
import { IconBookmark } from "../components/ui/icons.jsx";
import { useProjects, STATUS, STATUS_LABEL } from "../hooks/useProjects.js";
import styles from "./MyProjects.module.css";

const FILTERS = ["all", ...Object.values(STATUS)];

export default function MyProjects() {
  const { projects, setStatus, removeProject } = useProjects();
  const [filter, setFilter] = useState("all");

  const filtered = useMemo(
    () => (filter === "all" ? projects : projects.filter((p) => p.status === filter)),
    [projects, filter]
  );

  return (
    <main className="page">
      <div className="container">
        <div className={styles.header}>
          <span className="eyebrow">Your workspace</span>
          <h1>My Projects</h1>
          <p>Problems you've saved and roadmaps you've generated, all in one place — synced to your account.</p>
        </div>

        {projects.length > 0 && (
          <div className={styles.filters}>
            {FILTERS.map((f) => (
              <Chip key={f} active={filter === f} onClick={() => setFilter(f)}>
                {f === "all" ? "All" : STATUS_LABEL[f]}
              </Chip>
            ))}
          </div>
        )}

        {projects.length === 0 ? (
          <EmptyState
            icon={<IconBookmark width={22} height={22} />}
            title="Nothing saved yet"
            description="Save a problem from Discover, or generate a roadmap, to start tracking it here."
            action={
              <Button to="/discover" size="sm">
                Browse problems
              </Button>
            }
          />
        ) : filtered.length === 0 ? (
          <EmptyState title="No projects with this status" description="Try a different filter." />
        ) : (
          <div className={styles.grid}>
            {filtered.map((p) => (
              <ProjectCard key={p.id} project={p} onStatusChange={setStatus} onRemove={removeProject} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
