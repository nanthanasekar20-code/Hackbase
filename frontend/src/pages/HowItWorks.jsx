import AgentFlow from "../components/howitworks/AgentFlow.jsx";
import RagFlow from "../components/howitworks/RagFlow.jsx";
import Button from "../components/ui/Button.jsx";
import { IconArrowRight } from "../components/ui/icons.jsx";
import styles from "./HowItWorks.module.css";

export default function HowItWorks() {
  return (
    <main className="page">
      <div className="container">
        <div className={styles.header}>
          <span className="eyebrow">Under the hood</span>
          <h1>How HackBase works</h1>
          <p className={styles.lead}>
            HackBase turns a natural-language query into ranked hackathon recommendations, a project roadmap,
            and starter resources — using a four-agent pipeline on top of a retrieval-augmented generation
            (RAG) core.
          </p>
        </div>

        <section className="section">
          <div className={styles.sectionHead}>
            <h2>The agent pipeline</h2>
            <p>Each agent has one job and hands its output to the next.</p>
          </div>
          <AgentFlow />
        </section>

        <section className="section">
          <div className={styles.sectionHead}>
            <h2>The RAG recommendation flow</h2>
            <p>What actually happens between your query and a response, end to end.</p>
          </div>
          <RagFlow />
        </section>

        <section className={[styles.stack, "section"].join(" ")}>
          <div className={styles.stackCard}>
            <h3>Vector store</h3>
            <p>Problem statements from SIH, Devpost, Unstop and HackerEarth are chunked, embedded, and indexed in Chroma / FAISS so semantically similar problems can be retrieved fast.</p>
          </div>
          <div className={styles.stackCard}>
            <h3>Orchestration</h3>
            <p>LangChain / LangGraph coordinates the four agents, passing structured state between search, ranking, planning and resourcing steps.</p>
          </div>
          <div className={styles.stackCard}>
            <h3>Generation</h3>
            <p>The Gemini API drafts phased roadmaps and match explanations grounded in the retrieved problem statement — not generic advice.</p>
          </div>
        </section>

        <section className={[styles.cta, "section"].join(" ")}>
          <div>
            <h2>Ready to try it?</h2>
            <p>Describe what you want to build and see the pipeline in action.</p>
          </div>
          <Button to="/discover" size="lg" icon={<IconArrowRight width={18} height={18} />}>
            Start searching
          </Button>
        </section>
      </div>
    </main>
  );
}
