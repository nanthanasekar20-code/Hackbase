import Card from "../ui/Card.jsx";
import { IconGithub, IconBook, IconDataset, IconTool, IconExternal } from "../ui/icons.jsx";
import styles from "./ResourceCard.module.css";

const ICONS = {
  repo: IconGithub,
  docs: IconBook,
  dataset: IconDataset,
  tutorial: IconTool,
};

export default function ResourceCard({ resource }) {
  const Icon = ICONS[resource.type] || IconExternal;
  return (
    <Card as="a" href={resource.url} target="_blank" rel="noreferrer" interactive className={styles.card}>
      <div className={styles.icon}>
        <Icon width={18} height={18} />
      </div>
      <div className={styles.body}>
        <h4 className={styles.title}>{resource.title}</h4>
        <span className={styles.url}>{safeHost(resource.url)}</span>
      </div>
      <IconExternal width={15} height={15} className={styles.ext} />
    </Card>
  );
}

function safeHost(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}
