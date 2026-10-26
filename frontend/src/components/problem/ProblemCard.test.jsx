import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import ProblemCard from "./ProblemCard.jsx";

const BASE_RESULT = {
  id: "sih:p1",
  title: "AI Crop Disease Detection",
  source: "sih",
  summary: "Detect crop disease from leaf images.",
  score: 0.8,
};

function renderCard(result) {
  return render(
    <MemoryRouter>
      <ProblemCard result={result} />
    </MemoryRouter>
  );
}

describe("ProblemCard — enrichment score badges", () => {
  it("shows no score badges when the problem hasn't been enriched yet", () => {
    renderCard(BASE_RESULT);
    expect(screen.queryByText(/Novel/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Dataset/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hardware/)).not.toBeInTheDocument();
  });

  it("renders only the badges for scores that are actually present, never fabricated ones", () => {
    renderCard({ ...BASE_RESULT, novelty_score: 8.2, social_impact_score: 7.0 });

    expect(screen.getByText("Novel 8.2")).toBeInTheDocument();
    expect(screen.getByText("Impact 7.0")).toBeInTheDocument();
    // Not present on this result — must not appear.
    expect(screen.queryByText(/Dataset/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Hardware/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Competitive/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Feasible/)).not.toBeInTheDocument();
  });

  it("renders all six badges, correctly rounded to one decimal, when every score is present", () => {
    renderCard({
      ...BASE_RESULT,
      novelty_score: 8.25,
      dataset_availability_score: 4,
      hardware_requirement_score: 9.333,
      competition_potential_score: 6.1,
      social_impact_score: 7.95,
      feasibility_score: 3,
    });

    expect(screen.getByText("Novel 8.3")).toBeInTheDocument();
    expect(screen.getByText("Dataset 4.0")).toBeInTheDocument();
    expect(screen.getByText("Hardware 9.3")).toBeInTheDocument();
    expect(screen.getByText("Competitive 6.1")).toBeInTheDocument();
    expect(screen.getByText("Impact 8.0")).toBeInTheDocument();
    expect(screen.getByText("Feasible 3.0")).toBeInTheDocument();
  });
});

describe("ProblemCard — match score and domain tag", () => {
  it("hides the match-score ring entirely when the result has no real score (a plain browse, not a ranked search)", () => {
    const { score, ...noScore } = BASE_RESULT;
    renderCard(noScore);
    expect(screen.queryByTitle("Match score")).not.toBeInTheDocument();
  });

  it("shows only the first domain as the fallback tag, not every domain smushed together", () => {
    // Regression test: rendering a multi-value `domain` array directly as
    // one Badge's children concatenated every tag with no separator.
    renderCard({ ...BASE_RESULT, domain: ["AI/ML", "Healthcare", "IoT"] });

    expect(screen.getByText("AI/ML")).toBeInTheDocument();
    expect(screen.queryByText("AI/MLHealthcareIoT")).not.toBeInTheDocument();
  });
});
