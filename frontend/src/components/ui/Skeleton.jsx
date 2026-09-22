import styles from "./Skeleton.module.css";

export function SkeletonLine({ width = "100%", height = 14, className = "" }) {
  return <span className={[styles.line, className].join(" ")} style={{ width, height }} />;
}

export function SkeletonCard() {
  return (
    <div className={styles.card}>
      <div className={styles.row}>
        <SkeletonLine width="35%" height={12} />
        <SkeletonLine width={44} height={44} className={styles.circle} />
      </div>
      <SkeletonLine width="80%" height={20} />
      <SkeletonLine width="100%" height={12} />
      <SkeletonLine width="92%" height={12} />
      <div className={styles.row}>
        <SkeletonLine width={70} height={22} />
        <SkeletonLine width={70} height={22} />
        <SkeletonLine width={70} height={22} />
      </div>
    </div>
  );
}
