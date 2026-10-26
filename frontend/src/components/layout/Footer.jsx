import { Link } from "react-router-dom";
import Logo from "./Logo.jsx";
import styles from "./Footer.module.css";

export default function Footer() {
  return (
    <footer className={styles.footer}>
      <div className={[styles.inner, "container"].join(" ")}>
        <div>
          <Logo />
          <p className={styles.tag}>
            Agentic AI-powered hackathon problem discovery. Search agent → ranking agent → planning agent →
            resource agent.
          </p>
        </div>
        <nav className={styles.links} aria-label="Footer">
          <Link to="/discover">Discover</Link>
          <Link to="/projects">My Projects</Link>
          <Link to="/how-it-works">How It Works</Link>
        </nav>
      </div>
      <div className={[styles.bottom, "container"].join(" ")}>

    
      </div>
    </footer>
  );
}
