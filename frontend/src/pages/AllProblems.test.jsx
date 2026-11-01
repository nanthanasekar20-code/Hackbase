import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import AllProblems from "./AllProblems.jsx";
import { getProblems } from "../api/client.js";
import { getCachedProblem } from "../hooks/useProjects.js";

vi.mock("../api/client.js", () => ({
  getProblems: vi.fn(),
}));

function renderPage(initialPath = "/problems") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/problems" element={<AllProblems />} />
      </Routes>
    </MemoryRouter>
  );
}

const PAGE_1_PROBLEMS = Array.from({ length: 20 }, (_, i) => ({
  id: `p${i}`,
  title: `Problem ${i}`,
  source: "sih",
  summary: "A real summary.",
}));

describe("AllProblems", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("caches every fetched problem so opening one in a new tab (or after a refresh) still finds it", async () => {
    // Regression test for a real bug: this page never cached its results,
    // so ProblemDetails had nothing to fall back on once React Router's
    // location.state wasn't available (a new tab, or /problem/:id loaded
    // directly) — "We couldn't find that problem" for one that's right
    // there in the corpus. Discover.jsx already does this on every fetch;
    // this was the one gap.
    getProblems.mockResolvedValue({ page: 1, page_size: 20, total: 1, problems: [PAGE_1_PROBLEMS[0]] });

    renderPage();
    await screen.findByText("Problem 0");

    expect(getCachedProblem("p0")).toEqual(expect.objectContaining({ id: "p0", title: "Problem 0" }));
  });

  it("renders real problems and the total count", async () => {
    getProblems.mockResolvedValue({ page: 1, page_size: 20, total: 45, problems: PAGE_1_PROBLEMS });

    renderPage();

    expect(await screen.findByText("Problem 0")).toBeInTheDocument();
    expect(screen.getByText("45 total")).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 3")).toBeInTheDocument();
    expect(getProblems).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
  });

  it("disables Previous on the first page and Next on the last page", async () => {
    getProblems.mockResolvedValue({ page: 1, page_size: 20, total: 10, problems: PAGE_1_PROBLEMS.slice(0, 10) });

    renderPage();
    await screen.findByText("Problem 0");

    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled(); // only 1 page at total=10/pageSize=20
  });

  it("clicking Next advances the page and refetches", async () => {
    getProblems.mockResolvedValue({ page: 1, page_size: 20, total: 45, problems: PAGE_1_PROBLEMS });

    renderPage();
    await screen.findByText("Problem 0");

    getProblems.mockResolvedValueOnce({
      page: 2,
      page_size: 20,
      total: 45,
      problems: [{ id: "page2-item", title: "Page 2 Item", source: "sih", summary: "x" }],
    });
    await userEvent.click(screen.getByRole("button", { name: /next/i }));

    expect(await screen.findByText("Page 2 Item")).toBeInTheDocument();
    expect(getProblems).toHaveBeenLastCalledWith({ page: 2, pageSize: 20 });
  });

  it("starts from the page given in the URL", async () => {
    getProblems.mockResolvedValue({ page: 2, page_size: 20, total: 45, problems: PAGE_1_PROBLEMS });

    renderPage("/problems?page=2");
    await screen.findByText("Problem 0");

    expect(getProblems).toHaveBeenCalledWith({ page: 2, pageSize: 20 });
  });

  it("shows an honest empty state when the corpus has nothing, never fabricated cards", async () => {
    getProblems.mockResolvedValue({ page: 1, page_size: 20, total: 0, problems: [] });

    renderPage();

    expect(await screen.findByText("No problems to show")).toBeInTheDocument();
  });

  it("shows an error state when the request fails", async () => {
    getProblems.mockRejectedValue(new Error("network error"));

    renderPage();

    expect(await screen.findByText(/Couldn't load problems/i)).toBeInTheDocument();
  });
});
