import { useMemo } from "react";
import Card from "../components/ui/Card.jsx";
import Badge from "../components/ui/Badge.jsx";
import ResourceCard from "../components/resources/ResourceCard.jsx";
import EmptyState from "../components/ui/EmptyState.jsx";
import Button from "../components/ui/Button.jsx";
import { IconResource } from "../components/ui/icons.jsx";
import { useProjects } from "../hooks/useProjects.js";
import styles from "./Resources.module.css";

/**
 * One card per saved project (its title is the project's topic), holding
 * only that project's own resources — real Resource Agent output, no
 * cross-project mixing and no empty placeholder sections.
 */
export default function Resources() {
  const { projects } = useProjects();

  const projectsWithResources = useMemo(
    () => projects.filter((project) => (project.plan?.resources || []).length > 0),
    [projects]
  );

  return (
    <main className="page">
      <div className="container">
        <div className={styles.header}>
          <span className="eyebrow">Resource Agent output</span>
          <h1>Resources</h1>
          <p>
            Documentation, repos, tutorials and datasets gathered automatically as you generate roadmaps —
            organized here by project so you don't lose track of them.
          </p>
        </div>

        {projectsWithResources.length === 0 ? (
          <EmptyState
            icon={<IconResource width={22} height={22} />}
            title="No resources yet"
            description="Generate a roadmap for a problem you're interested in — its starter resources will show up here, grouped by project."
            action={
              <Button to="/discover" size="sm">
                Find a problem
              </Button>
            }
          />
        ) : (
          projectsWithResources.map((project) => {
            const resources = project.plan.resources;
            return (
              <Card as="section" className={styles.projectCard} key={project.id}>
                <div className={styles.projectHeader}>
                  <h2 className={styles.projectTitle}>{project.title}</h2>
                  {project.domain && <Badge tone="sand">{project.domain}</Badge>}
                </div>
                <div className={styles.grid}>
                  {resources.map((res, i) => (
                    <ResourceCard key={res.url || `${project.id}-${i}`} resource={res} />
                  ))}
                </div>
              </Card>
            );
          })
        )}
      </div>
    </main>
  );
}
