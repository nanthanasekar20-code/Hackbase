import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ProblemDetails from "./ProblemDetails.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { useProjects } from "../hooks/useProjects.js";

vi.mock("../hooks/useAuth.js");
vi.mock("../hooks/useProjects.js");
vi.mock("../api/client.js", () => ({
  exportFavoritePptx: vi.fn(),
  viewFavoritePdf: vi.fn(),
  apiErrorMessage: (err, fallback) => fallback,
}));

const BASE_RESULT = {
  id: "sih:p1",
  title: "AI Crop Disease Detection",
  source: "sih",
  summary: "Detect crop disease from leaf images.",
  score: 0.8,
  resume_value_score: 8.5,
};

function renderWithResult(result) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: "/problem/sih:p1", state: result }]}>
      <Routes>
        <Route path="/problem/:id" element={<ProblemDetails />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProblemDetails — Portfolio value section's newer scores", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ isAuthenticated: false });
    useProjects.mockReturnValue({ saveProblem: vi.fn(), getProject: () => null });
  });

  it("only shows rows for scores that are actually present, never fabricated ones", () => {
    renderWithResult({ ...BASE_RESULT, novelty_score: 8.2, social_impact_score: 7.0 });

    expect(screen.getByText("Novelty")).toBeInTheDocument();
    expect(screen.getByText("Social impact")).toBeInTheDocument();
    // Resume value (the original field) is always shown once the section renders at all.
    expect(screen.getByText("Resume value")).toBeInTheDocument();
    // Not present on this result — the row must not appear.
    expect(screen.queryByText("Dataset availability")).not.toBeInTheDocument();
    expect(screen.queryByText("Hardware needed")).not.toBeInTheDocument();
    expect(screen.queryByText("Competition potential")).not.toBeInTheDocument();
    expect(screen.queryByText("Hackathon feasibility")).not.toBeInTheDocument();
  });

  it("shows all six newer score rows when every field is present", () => {
    renderWithResult({
      ...BASE_RESULT,
      novelty_score: 8.2,
      dataset_availability_score: 4.0,
      hardware_requirement_score: 9.0,
      competition_potential_score: 6.1,
      social_impact_score: 7.0,
      feasibility_score: 3.0,
    });

    expect(screen.getByText("Novelty")).toBeInTheDocument();
    expect(screen.getByText("Dataset availability")).toBeInTheDocument();
    expect(screen.getByText("Hardware needed")).toBeInTheDocument();
    expect(screen.getByText("Competition potential")).toBeInTheDocument();
    expect(screen.getByText("Social impact")).toBeInTheDocument();
    expect(screen.getByText("Hackathon feasibility")).toBeInTheDocument();
  });

  it("shows no Portfolio value section at all when the problem has never been enriched", () => {
    const { resume_value_score, ...unenriched } = BASE_RESULT;
    renderWithResult(unenriched);

    expect(screen.queryByText("Portfolio value")).not.toBeInTheDocument();
  });

  it("shows each portfolio score's real value in its own row", () => {
    renderWithResult({ ...BASE_RESULT, novelty_score: 8.2 });

    expect(screen.getByText("8.5")).toBeInTheDocument(); // resume_value_score
    expect(screen.getByText("8.2")).toBeInTheDocument(); // novelty_score
  });
});

describe("ProblemDetails — match score", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ isAuthenticated: false });
    useProjects.mockReturnValue({ saveProblem: vi.fn(), getProject: () => null });
  });

  it("shows the Match score ring for a real RAG search result", () => {
    renderWithResult({ ...BASE_RESULT, score: 0.82 });
    expect(screen.getByText("Match score")).toBeInTheDocument();
  });

  it("hides the Match score ring entirely for a problem reached via a plain browse (no real score)", () => {
    // e.g. opened from Domains/AllProblems' GET /problems — never ranked
    // against a query, so there's no honest number to show. Regression
    // test: this used to render a hollow "—" ring that looked broken.
    const { score, ...noScore } = BASE_RESULT;
    renderWithResult(noScore);

    expect(screen.queryByText("Match score")).not.toBeInTheDocument();
  });
});

describe("ProblemDetails — domain tags", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ isAuthenticated: false });
    useProjects.mockReturnValue({ saveProblem: vi.fn(), getProject: () => null });
  });

  it("renders every domain in the array as its own readable badge, not one smushed string", () => {
    // Regression test for a real bug: rendering the array directly as a
    // single Badge's children concatenated every tag with no separator
    // ("AI/MLHealthcareIoTSustainability & Climate").
    renderWithResult({ ...BASE_RESULT, domain: ["AI/ML", "Healthcare", "IoT", "Sustainability & Climate"] });

    expect(screen.getByText("AI/ML")).toBeInTheDocument();
    expect(screen.getByText("Healthcare")).toBeInTheDocument();
    expect(screen.getByText("IoT")).toBeInTheDocument();
    expect(screen.getByText("Sustainability & Climate")).toBeInTheDocument();
    expect(screen.queryByText("AI/MLHealthcareIoTSustainability & Climate")).not.toBeInTheDocument();
  });

  it("falls back to category when there's no domain array at all", () => {
    const { domain, ...rest } = { ...BASE_RESULT, category: "Software" };
    renderWithResult(rest);

    expect(screen.getByText("Software")).toBeInTheDocument();
  });
});
