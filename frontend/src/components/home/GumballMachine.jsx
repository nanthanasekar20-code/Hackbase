import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../ui/Button.jsx";
import { IconDice, IconArrowRight } from "../ui/icons.jsx";
import { getRandomProblems } from "../../api/client.js";
import { cacheProblem } from "../../hooks/useProjects.js";
import { problemId } from "../../utils/slug.js";
import { DOMAINS } from "../../utils/taxonomy.js";
import styles from "./GumballMachine.module.css";

const SPIN_TICKS = 16;

/**
 * "Feeling lucky?" picker — a two-step reveal, not a single click:
 *   1. Spin the machine -> a purely decorative local animation (cycles
 *      through real taxonomy domain names, no network call) that lands on
 *      a ball sitting in the glass.
 *   2. Click the ball -> the actual network call (GET /problems/random,
 *      count=1), revealing one genuinely random real problem. Splitting
 *      these in two means the "roll" never has to wait on a request, and
 *      the human curiosity beat (click the ball to see what's inside)
 *      only fires once, for a real result — never a fabricated one.
 */
export default function GumballMachine() {
  const navigate = useNavigate();
  // idle -> spinning -> ready -> loading -> revealed (or error, from loading)
  const [phase, setPhase] = useState("idle");
  const [spinLabel, setSpinLabel] = useState("");
  const [problem, setProblem] = useState(null);

  function handleSpin() {
    if (phase === "spinning" || phase === "loading") return;
    setPhase("spinning");
    setProblem(null);
    let tick = 0;
    function cycle() {
      setSpinLabel(DOMAINS[Math.floor(Math.random() * DOMAINS.length)]);
      tick++;
      if (tick < SPIN_TICKS) {
        // Eases out — starts fast, slows toward the end, like a real wheel.
        setTimeout(cycle, 55 + tick * 7);
      } else {
        setPhase("ready");
      }
    }
    cycle();
  }

  async function handleOpenBall() {
    if (phase !== "ready") return;
    setPhase("loading");
    try {
      const data = await getRandomProblems(1);
      const picked = data?.problems?.[0];
      if (!picked) {
        setPhase("error");
        return;
      }
      cacheProblem(picked);
      setProblem(picked);
      setPhase("revealed");
    } catch {
      setPhase("error");
    }
  }

  function viewProblem() {
    if (!problem) return;
    navigate(`/problem/${problemId(problem)}`, { state: problem });
  }

  const domainLabel = problem?.domain?.[0] || problem?.category;

  return (
    <section className={["section", styles.wrap].join(" ")}>
      <div className={styles.sectionHead}>
        <span className="eyebrow">
          <IconDice width={13} height={13} /> Feeling lucky?
        </span>
        <h2>Spin for a random problem</h2>
        <p>No searching — pull the lever, then crack open the ball to see what you get.</p>
      </div>

      <div className={["be-crop", styles.machine].join(" ")}>
        <div className={styles.glass}>
          {phase === "idle" && <span className={styles.hint}>Press spin to begin</span>}

          {phase === "spinning" && (
            <>
              <span className={styles.domainPill}>{spinLabel}</span>
              <span className={styles.hint}>Rolling…</span>
            </>
          )}

          {(phase === "ready" || phase === "loading") && (
            <>
              <button
                type="button"
                className={[styles.ball, phase === "loading" && styles.ballLoading].filter(Boolean).join(" ")}
                onClick={handleOpenBall}
                disabled={phase === "loading"}
                aria-label="Open your ball to reveal a random problem"
              />
              <span className={styles.hint}>{phase === "loading" ? "Opening…" : "Click the ball to open it"}</span>
            </>
          )}

          {phase === "revealed" && problem && (
            <div className={styles.reveal}>
              {domainLabel && <span className={styles.domainPill}>{domainLabel}</span>}
              <span className={styles.pickTitle}>{problem.title}</span>
            </div>
          )}

          {phase === "error" && (
            <span className={styles.errorText}>Couldn't fetch a problem right now — try again.</span>
          )}
        </div>

        <div className={styles.actions}>
          {phase === "revealed" ? (
            <>
              <Button variant="primary" size="sm" onClick={viewProblem} icon={<IconArrowRight width={16} height={16} />}>
                View problem
              </Button>
              <Button variant="ghost" size="sm" onClick={handleSpin}>
                Spin again
              </Button>
            </>
          ) : (
            <Button
              variant="accent"
              size="sm"
              onClick={handleSpin}
              disabled={phase === "spinning" || phase === "loading"}
              icon={<IconDice width={16} height={16} />}
            >
              {phase === "spinning" ? "Rolling…" : phase === "error" ? "Try again" : "Spin the machine"}
            </Button>
          )}
        </div>
      </div>
    </section>
  );
}
