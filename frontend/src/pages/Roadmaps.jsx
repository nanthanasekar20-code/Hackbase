import ProjectCard from "../components/projects/ProjectCard.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Button from "../components/ui/Button.jsx";
import { IconPlan } from "../components/ui/icons.jsx";
import { useProjects } from "../hooks/useProjects.js";
import styles from "./Roadmaps.module.css";

export default function Roadmaps() {
  const { projects, setStatus, removeProject } = useProjects();
  const withPlans = projects.filter((p) => p.plan);

  return (
    <main className="page">
      <div className="container">
        <div className={styles.header}>
          <span className="eyebrow">Planning Agent output</span>
          <h1>Your roadmaps</h1>
          <p>Every roadmap you've generated, synced to your account with your task progress.</p>
        </div>

        {withPlans.length === 0 ? (
          <EmptyState
            icon={<IconPlan width={22} height={22} />}
            title="No roadmaps yet"
            description="Open a problem from Discover and hit Generate Roadmap to create your first one."
            action={
              <Button to="/discover" size="sm">
                Go to Discover
              </Button>
            }
          />
        ) : (
          <div className={styles.grid}>
            {withPlans.map((p) => (
              <ProjectCard key={p.id} project={p} onStatusChange={setStatus} onRemove={removeProject} />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
