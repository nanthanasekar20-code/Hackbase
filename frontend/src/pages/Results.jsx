import { useLocation, useNavigate } from "react-router-dom";

export default function Results() {
  const { state } = useLocation();
  const navigate = useNavigate();
  const results = state?.results ?? [];

  return (
    <main>
      <h1>Results</h1>
      {results.length === 0 && <p>No results yet — try a search from the home page.</p>}
      <ul>
        {results.map((r, i) => (
          <li key={i}>
            <strong>{r.title}</strong> ({r.source}) — score {r.score}
            <p>{r.summary}</p>
            <button onClick={() => navigate("/roadmap", { state: r })}>
              Generate Roadmap
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
