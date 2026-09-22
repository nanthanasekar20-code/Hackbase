import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Discover from "./Discover.jsx";
import { searchHackathons } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  searchHackathons: vi.fn(),
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
});
