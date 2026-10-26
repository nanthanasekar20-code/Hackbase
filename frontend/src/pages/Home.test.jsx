import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Home, { __resetFeaturedCacheForTests } from "./Home.jsx";
import { searchHackathons, getRandomProblems, getLiveHackathons } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  searchHackathons: vi.fn(),
  getRandomProblems: vi.fn(),
  getLiveHackathons: vi.fn(),
}));

function renderHome() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/live-hackathons" element={<div>Live Hackathons Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const PROBLEM_A = { id: "a", title: "Problem A", source: "sih", summary: "Summary A" };
const PROBLEM_B = { id: "b", title: "Problem B", source: "sih", summary: "Summary B" };
const PROBLEM_C = { id: "c", title: "Problem C", source: "sih", summary: "Summary C" };

describe("Home — Live Hackathons teaser", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetFeaturedCacheForTests();
    searchHackathons.mockResolvedValue({ results: [PROBLEM_A, PROBLEM_B, PROBLEM_C] });
  });

  it("shows the real count from GET /live-hackathons and links to the dedicated page", async () => {
    getLiveHackathons.mockResolvedValue({ count: 7, hackathons: [] });

    renderHome();

    const teaser = await screen.findByText("7 hackathons open now");
    expect(teaser.closest("button")).toHaveAttribute("type", "button");

    await userEvent.click(teaser);
    expect(await screen.findByText("Live Hackathons Page")).toBeInTheDocument();
  });

  it("uses singular phrasing for exactly one hackathon", async () => {
    getLiveHackathons.mockResolvedValue({ count: 1, hackathons: [] });

    renderHome();

    expect(await screen.findByText("1 hackathon open now")).toBeInTheDocument();
  });

  it("degrades to a generic label (never a fabricated count) while loading or on error", async () => {
    getLiveHackathons.mockRejectedValue(new Error("network error"));

    renderHome();

    // Still navigable even though the count failed to load.
    expect(await screen.findByText("Hackathons open now")).toBeInTheDocument();
  });
});

describe("Home — Featured Refresh", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetFeaturedCacheForTests();
    getLiveHackathons.mockResolvedValue({ count: 0, hackathons: [] });
    searchHackathons.mockResolvedValue({ results: [PROBLEM_A, PROBLEM_B, PROBLEM_C] });
  });

  it("swaps in a genuinely random sample via GET /problems/random, not the fixed RAG query", async () => {
    const randomProblem = { id: "z", title: "Random Problem Z", source: "devpost", summary: "Summary Z" };
    getRandomProblems.mockResolvedValue({ problems: [randomProblem] });

    renderHome();
    await screen.findByText("Problem A");

    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

    expect(await screen.findByText("Random Problem Z")).toBeInTheDocument();
    expect(getRandomProblems).toHaveBeenCalledWith(6);
    expect(searchHackathons).toHaveBeenCalledTimes(1); // refresh never re-ran the fixed query
  });

  it("keeps showing the old cards (doesn't blank the grid) while refreshing", async () => {
    let resolveRefresh;
    getRandomProblems.mockReturnValue(
      new Promise((resolve) => {
        resolveRefresh = resolve;
      })
    );

    renderHome();
    await screen.findByText("Problem A");

    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

    // Still visible while the request is in flight.
    expect(screen.getByText("Problem A")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /refreshing/i })).toBeDisabled();

    // resolveRefresh() fires from outside any render/user-event call, so
    // React's state update needs an explicit act() to flush — otherwise
    // findByText's polling can miss an update that lands purely via
    // microtask resolution with no macrotask boundary in between.
    await act(async () => {
      resolveRefresh({ problems: [PROBLEM_B] });
    });
    expect(await screen.findByText("Problem B")).toBeInTheDocument();
  });

  it("leaves the existing cards in place if the refresh request fails", async () => {
    getRandomProblems.mockRejectedValue(new Error("network error"));

    renderHome();
    await screen.findByText("Problem A");

    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));

    expect(await screen.findByText("Problem A")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^refresh$/i })).not.toBeDisabled();
  });
});

describe("Home — Browse all", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetFeaturedCacheForTests();
  });

  it("links to the real browse-all page, not /discover", async () => {
    searchHackathons.mockResolvedValue({ results: [] });
    getLiveHackathons.mockResolvedValue({ count: 0, hackathons: [] });

    renderHome();

    const link = await screen.findByRole("link", { name: /browse all/i });
    expect(link).toHaveAttribute("href", "/problems");
  });
});

describe("Home — Featured survives navigating away and back", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    __resetFeaturedCacheForTests();
    getLiveHackathons.mockResolvedValue({ count: 0, hackathons: [] });
  });

  it("shows a prior Refresh's results immediately on remount, without re-running the fixed query", async () => {
    searchHackathons.mockResolvedValue({ results: [PROBLEM_A, PROBLEM_B, PROBLEM_C] });
    const randomProblem = { id: "z", title: "Random Problem Z", source: "devpost", summary: "Summary Z" };
    getRandomProblems.mockResolvedValue({ problems: [randomProblem] });

    const { unmount } = renderHome();
    await screen.findByText("Problem A");
    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await screen.findByText("Random Problem Z");
    expect(searchHackathons).toHaveBeenCalledTimes(1);

    // Simulates navigating to a problem's page (unmounts Home) and back
    // (remounts it fresh) — same lifecycle a real router navigation causes.
    unmount();
    renderHome();

    // The refreshed result shows immediately — no loading flash back to
    // the original fixed-query cards, and the fixed query is never re-run.
    expect(screen.getByText("Random Problem Z")).toBeInTheDocument();
    expect(searchHackathons).toHaveBeenCalledTimes(1);
    // Lets the remount's own getLiveHackathons effect settle before the
    // test ends, so its state update doesn't land outside any act() scope.
    await screen.findByText("Random Problem Z");
  });

  it("still runs the default query on a genuine first visit (cache empty)", async () => {
    searchHackathons.mockResolvedValue({ results: [PROBLEM_A] });

    renderHome();

    expect(await screen.findByText("Problem A")).toBeInTheDocument();
    expect(searchHackathons).toHaveBeenCalledTimes(1);
  });

  it("does not cache a failed refresh — a later remount still shows the last good result, not an error", async () => {
    searchHackathons.mockResolvedValue({ results: [PROBLEM_A] });
    getRandomProblems.mockRejectedValue(new Error("network error"));

    const { unmount } = renderHome();
    await screen.findByText("Problem A");
    await userEvent.click(screen.getByRole("button", { name: /refresh/i }));
    await screen.findByText("Problem A"); // refresh failed — original cards still showing

    unmount();
    renderHome();

    // The last good ("done") state was cached before the failed refresh —
    // still shows immediately on remount, no re-fetch, no error state.
    expect(screen.getByText("Problem A")).toBeInTheDocument();
    expect(searchHackathons).toHaveBeenCalledTimes(1);
    // Lets the remount's own getLiveHackathons effect settle before the
    // test ends, so its state update doesn't land outside any act() scope.
    await screen.findByText("Problem A");
  });
});
