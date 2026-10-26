import { StrictMode } from "react";
import { render, screen, within, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Discover from "./Discover.jsx";
import { searchHackathons, getProblems } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  searchHackathons: vi.fn(),
  getProblems: vi.fn(),
}));

function renderDiscover(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/discover" element={<Discover />} />
      </Routes>
    </MemoryRouter>
  );
}

// Real StrictMode, not MemoryRouter alone — src/main.jsx wraps the whole
// app in it, and it's what actually double-invokes effects in dev (the
// plain renderDiscover() above never does, so a bug that only shows up
// under that double-invoke can pass every other test here and still be
// broken in the real running app).
function renderDiscoverStrict(initialPath) {
  return render(
    <StrictMode>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/discover" element={<Discover />} />
        </Routes>
      </MemoryRouter>
    </StrictMode>
  );
}

const SAMPLE_RESULTS = {
  results: [
    {
      id: "sih:sih26001",
      title: "AI-Based Landslide Risk Monitoring System",
      source: "sih",
      summary: "Detects landslide risk from sensor data in real time.",
      score: 0.82,
    },
    {
      id: "sih:sih26002",
      title: "Flash Flood Prediction System",
      source: "sih",
      summary: "Predicts flash floods using rainfall and terrain data.",
      score: 0.71,
    },
  ],
};

describe("Discover", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Discover caches the last completed search in sessionStorage (see
    // Discover.jsx) so it survives navigating away and back — clear it
    // between tests so one test's search doesn't leak into the next.
    sessionStorage.clear();
  });

  it("shows a prompt to search when there's no query, without calling the API", () => {
    renderDiscover("/discover");

    expect(screen.getByText("Search to get started")).toBeInTheDocument();
    expect(searchHackathons).not.toHaveBeenCalled();
  });

  it("searches and renders real result cards for a query in the URL", async () => {
    searchHackathons.mockResolvedValue(SAMPLE_RESULTS);

    renderDiscover("/discover?q=landslide");

    expect(await screen.findByText("AI-Based Landslide Risk Monitoring System")).toBeInTheDocument();
    expect(screen.getByText("Flash Flood Prediction System")).toBeInTheDocument();
    expect(searchHackathons).toHaveBeenCalledWith("landslide", 12);
  });

  it("shows an empty state when the search returns no results", async () => {
    searchHackathons.mockResolvedValue({ results: [] });

    renderDiscover("/discover?q=nonexistent-topic");

    expect(await screen.findByText(/No problems matched your search/i)).toBeInTheDocument();
  });

  it("shows an error state when the search request fails", async () => {
    searchHackathons.mockRejectedValue(new Error("network error"));

    renderDiscover("/discover?q=landslide");

    expect(await screen.findByText("Something went wrong")).toBeInTheDocument();
  });

  it("restores the last search from sessionStorage when landing on a bare /discover", async () => {
    sessionStorage.setItem(
      "hackbase_discover_last_search",
      JSON.stringify({ query: "landslide", results: SAMPLE_RESULTS.results })
    );
    searchHackathons.mockResolvedValue(SAMPLE_RESULTS);

    renderDiscover("/discover");

    // Shown immediately from cache — not the "Search to get started" idle
    // state — even before the background revalidation fetch resolves.
    expect(screen.getByText("AI-Based Landslide Risk Monitoring System")).toBeInTheDocument();
    expect(screen.queryByText("Search to get started")).not.toBeInTheDocument();

    // Let the background revalidation fetch settle before the test ends.
    await screen.findByText("AI-Based Landslide Risk Monitoring System");
    expect(searchHackathons).toHaveBeenCalledWith("landslide", 12);
  });
});

describe("Discover — score threshold filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  const SCORED_RESULTS = {
    results: [
      {
        id: "sih:a",
        title: "Well Rounded Problem",
        source: "sih",
        summary: "Scored on both novelty and hardware.",
        score: 0.9,
        novelty_score: 8.0,
        hardware_requirement_score: 2.0,
      },
      {
        id: "sih:b",
        title: "Low Novelty Problem",
        source: "sih",
        summary: "Scored, but low novelty and high hardware need.",
        score: 0.8,
        novelty_score: 3.0,
        hardware_requirement_score: 9.0,
      },
      {
        id: "sih:c",
        title: "Unscored Problem",
        source: "sih",
        summary: "Never enriched yet — missing both score fields.",
        score: 0.7,
      },
    ],
  };

  async function openScoresGroup() {
    const toggle = await screen.findByText("Scores");
    await userEvent.click(toggle);
  }

  it("only shows a score filter for a field at least one current result actually has", async () => {
    searchHackathons.mockResolvedValue(SCORED_RESULTS);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    await openScoresGroup();

    expect(screen.getByRole("slider", { name: "Novelty" })).toBeInTheDocument();
    expect(screen.getByRole("slider", { name: "Hardware needed" })).toBeInTheDocument();
    // Dataset availability isn't on any of the three results — no control for it.
    expect(screen.queryByRole("slider", { name: "Dataset availability" })).not.toBeInTheDocument();
  });

  it("excludes unscored problems from a threshold filter instead of treating them as 0", async () => {
    searchHackathons.mockResolvedValue(SCORED_RESULTS);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    await openScoresGroup();
    fireEvent.change(screen.getByRole("slider", { name: "Novelty" }), { target: { value: "5" } });

    // Novelty >= 5: "Well Rounded" (8.0) passes, "Low Novelty" (3.0) and the
    // never-enriched "Unscored Problem" (no novelty_score at all) do not.
    expect(screen.getByText("Well Rounded Problem")).toBeInTheDocument();
    expect(screen.queryByText("Low Novelty Problem")).not.toBeInTheDocument();
    expect(screen.queryByText("Unscored Problem")).not.toBeInTheDocument();
  });

  it("treats hardware_requirement_score as a maximum (<=), not another minimum", async () => {
    searchHackathons.mockResolvedValue(SCORED_RESULTS);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    await openScoresGroup();
    fireEvent.change(screen.getByRole("slider", { name: "Hardware needed" }), { target: { value: "3" } });

    // Hardware <= 3: "Well Rounded" (2.0) passes; "Low Novelty" (9.0, needs
    // much more hardware) and the unscored problem are excluded.
    expect(screen.getByText("Well Rounded Problem")).toBeInTheDocument();
    expect(screen.queryByText("Low Novelty Problem")).not.toBeInTheDocument();
    expect(screen.queryByText("Unscored Problem")).not.toBeInTheDocument();
  });

  it("combines a score filter with an existing exact-value facet", async () => {
    const mixed = {
      results: [
        ...SCORED_RESULTS.results,
        {
          id: "unstop:d",
          title: "Different Source High Novelty",
          source: "unstop",
          summary: "High novelty but from a different source.",
          score: 0.6,
          novelty_score: 9.0,
        },
      ],
    };
    searchHackathons.mockResolvedValue(mixed);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    // The Source facet's "sih" chip is an interactive <button>; the same
    // text also shows as a plain (non-clickable) tag on each result card,
    // so the role query is what disambiguates the real filter control.
    await userEvent.click(screen.getByRole("button", { name: "sih" }));
    await openScoresGroup();
    fireEvent.change(screen.getByRole("slider", { name: "Novelty" }), { target: { value: "5" } });

    // Source=sih AND novelty>=5 — only "Well Rounded Problem" satisfies both;
    // the high-novelty unstop result is excluded by the source facet alone.
    expect(screen.getByText("Well Rounded Problem")).toBeInTheDocument();
    expect(screen.queryByText("Different Source High Novelty")).not.toBeInTheDocument();
    expect(screen.queryByText("Low Novelty Problem")).not.toBeInTheDocument();
  });

  it("shows a persistent Clear all filters control once any filter is active, and it clears both chip and score filters", async () => {
    searchHackathons.mockResolvedValue(SCORED_RESULTS);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    expect(screen.queryByText("Clear all filters")).not.toBeInTheDocument();

    await openScoresGroup();
    fireEvent.change(screen.getByRole("slider", { name: "Novelty" }), { target: { value: "5" } });

    expect(screen.queryByText("Low Novelty Problem")).not.toBeInTheDocument();
    const clearAll = await screen.findByText("Clear all filters");

    await userEvent.click(clearAll);

    expect(screen.getByText("Low Novelty Problem")).toBeInTheDocument();
    expect(screen.getByText("Unscored Problem")).toBeInTheDocument();
    expect(screen.queryByText("Clear all filters")).not.toBeInTheDocument();
  });

  it("turns a score filter back off when the slider is returned to its neutral bound", async () => {
    searchHackathons.mockResolvedValue(SCORED_RESULTS);
    renderDiscover("/discover?q=landslide");
    await screen.findByText("Well Rounded Problem");

    await openScoresGroup();
    const slider = screen.getByRole("slider", { name: "Novelty" });
    fireEvent.change(slider, { target: { value: "5" } });
    expect(screen.queryByText("Low Novelty Problem")).not.toBeInTheDocument();

    fireEvent.change(slider, { target: { value: "0" } });

    // Back at the neutral minimum (0) — filter is off again, including the
    // never-enriched problem, which a merely-numeric "0" bound must not exclude.
    expect(screen.getByText("Low Novelty Problem")).toBeInTheDocument();
    expect(screen.getByText("Unscored Problem")).toBeInTheDocument();
    expect(screen.queryByText("Clear all filters")).not.toBeInTheDocument();
  });
});

describe("Discover — arriving via a Domains.jsx card (?domain=)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("browses that domain via GET /problems when there's no search query yet", async () => {
    getProblems.mockResolvedValue({
      problems: [
        { id: "a", title: "Healthcare Problem A", source: "sih", domain: ["Healthcare"] },
        { id: "b", title: "Healthcare Problem B", source: "sih", domain: ["Healthcare"] },
      ],
    });

    renderDiscover("/discover?domain=Healthcare");

    expect(await screen.findByText("Healthcare Problem A")).toBeInTheDocument();
    expect(screen.getByText("Healthcare Problem B")).toBeInTheDocument();
    expect(getProblems).toHaveBeenCalledWith({ domain: "Healthcare", page: 1, pageSize: 20 });
    expect(searchHackathons).not.toHaveBeenCalled();
  });

  it("still browses the domain under React StrictMode's dev-only double effect invoke", async () => {
    // Regression test for a real bug: an earlier version "consumed" the
    // domain from a ref by nulling it out inside the fetch effect. Under
    // real StrictMode (src/main.jsx wraps the whole app in it), React
    // runs that effect twice on mount — the first, throwaway run nulled
    // the ref, so the second, real run saw no domain left and silently
    // fell back to the plain idle "Search to get started" state instead
    // of ever calling GET /problems. Only a StrictMode-wrapped render
    // catches this — see renderDiscoverStrict's own comment.
    getProblems.mockResolvedValue({
      problems: [{ id: "a", title: "Healthcare Problem A", source: "sih", domain: ["Healthcare"] }],
    });

    renderDiscoverStrict("/discover?domain=Healthcare");

    expect(await screen.findByText("Healthcare Problem A")).toBeInTheDocument();
    expect(screen.queryByText("Search to get started")).not.toBeInTheDocument();
    expect(getProblems).toHaveBeenCalledWith({ domain: "Healthcare", page: 1, pageSize: 20 });
  });

  it("pre-activates that domain's filter chip, so a non-matching result is hidden until the chip is toggled off", async () => {
    getProblems.mockResolvedValue({
      problems: [
        { id: "a", title: "Healthcare Problem", source: "sih", domain: ["Healthcare"] },
        { id: "b", title: "Other Domain Problem", source: "sih", domain: ["FinTech"] },
      ],
    });

    renderDiscover("/discover?domain=Healthcare");
    await screen.findByText("Healthcare Problem");

    // Pre-activated: the FinTech-only result is filtered out immediately,
    // without the user ever clicking the Healthcare chip themselves.
    expect(screen.queryByText("Other Domain Problem")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Healthcare" }));
    expect(screen.getByText("Other Domain Problem")).toBeInTheDocument();
  });

  it("shows a domain-specific empty state (not the search-query one) when the domain has nothing yet", async () => {
    getProblems.mockResolvedValue({ problems: [] });

    renderDiscover("/discover?domain=Cybersecurity");

    expect(await screen.findByText("No problems in this domain yet")).toBeInTheDocument();
    expect(screen.getByText(/"Cybersecurity"/)).toBeInTheDocument();
  });

  it("still runs the normal search when both q and domain are present, applying domain as a filter on top", async () => {
    searchHackathons.mockResolvedValue({
      results: [
        { id: "a", title: "Matched Healthcare Result", source: "sih", domain: ["Healthcare"] },
        { id: "b", title: "Matched FinTech Result", source: "sih", domain: ["FinTech"] },
      ],
    });

    renderDiscover("/discover?q=telemedicine&domain=Healthcare");

    expect(await screen.findByText("Matched Healthcare Result")).toBeInTheDocument();
    expect(screen.queryByText("Matched FinTech Result")).not.toBeInTheDocument();
    expect(searchHackathons).toHaveBeenCalledWith("telemedicine", 12);
    expect(getProblems).not.toHaveBeenCalled();
  });
});

describe("Discover — domain-browse pagination", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
  });

  it("shows the real total (not just this page's count) and only this many problems at a time", async () => {
    getProblems.mockResolvedValue({
      total: 169,
      problems: [{ id: "a", title: "AI Problem A", source: "sih", domain: ["AI/ML"] }],
    });

    renderDiscover("/discover?domain=AI%2FML");

    await screen.findByText("AI Problem A");
    expect(screen.getByText(/of 169 in AI\/ML/)).toBeInTheDocument();
    expect(getProblems).toHaveBeenCalledWith({ domain: "AI/ML", page: 1, pageSize: 20 });
  });

  it("Next fetches page 2 and updates the URL; Previous is disabled on page 1", async () => {
    getProblems.mockResolvedValue({
      total: 169,
      problems: [{ id: "a", title: "AI Problem Page 1", source: "sih", domain: ["AI/ML"] }],
    });

    renderDiscover("/discover?domain=AI%2FML");
    await screen.findByText("AI Problem Page 1");

    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();

    getProblems.mockResolvedValue({
      total: 169,
      problems: [{ id: "b", title: "AI Problem Page 2", source: "sih", domain: ["AI/ML"] }],
    });
    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText("AI Problem Page 2")).toBeInTheDocument();
    expect(getProblems).toHaveBeenCalledWith({ domain: "AI/ML", page: 2, pageSize: 20 });
  });

  it("Next is disabled on the last page", async () => {
    // 169 total at 20/page -> 9 pages; land directly on the last one.
    getProblems.mockResolvedValue({
      total: 169,
      problems: [{ id: "i", title: "Last Page Problem", source: "sih", domain: ["AI/ML"] }],
    });

    renderDiscover("/discover?domain=AI%2FML&page=9");
    await screen.findByText("Last Page Problem");

    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    expect(screen.getByText("Page 9 of 9")).toBeInTheDocument();
  });

  it("does not show pagination controls at all for a normal search (RAG top-k, not paginated)", async () => {
    searchHackathons.mockResolvedValue({
      results: [{ id: "a", title: "Searched Problem", source: "sih", domain: ["AI/ML"] }],
    });

    renderDiscover("/discover?q=ai");
    await screen.findByText("Searched Problem");

    expect(screen.queryByRole("button", { name: /next/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /previous/i })).not.toBeInTheDocument();
  });
});
