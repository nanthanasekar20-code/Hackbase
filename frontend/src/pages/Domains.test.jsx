import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Domains from "./Domains.jsx";
import { getProblems } from "../api/client.js";
import { DOMAINS } from "../utils/taxonomy.js";

vi.mock("../api/client.js", () => ({
  getProblems: vi.fn(),
}));

function renderDomains() {
  return render(
    <MemoryRouter initialEntries={["/domains"]}>
      <Routes>
        <Route path="/domains" element={<Domains />} />
        <Route path="/discover" element={<div>Discover Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Domains page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows every taxonomy domain with its real count from GET /problems, never a fabricated number", async () => {
    getProblems.mockImplementation(({ domain }) =>
      Promise.resolve({ total: domain === "AI/ML" ? 42 : domain === "Healthcare" ? 7 : 0 })
    );

    renderDomains();

    expect(await screen.findByText("42 problems")).toBeInTheDocument();
    expect(screen.getByText("7 problems")).toBeInTheDocument();
    // Every domain gets a card, including ones with zero matches so far —
    // hidden-until-populated would misrepresent what the corpus has.
    expect(screen.getAllByText("0 problems").length).toBe(DOMAINS.length - 2);
    DOMAINS.forEach((domain) => expect(screen.getByText(domain)).toBeInTheDocument());
  });

  it("fetches each domain's count with a cheap page_size=1 request, one per domain", async () => {
    getProblems.mockResolvedValue({ total: 0 });
    renderDomains();

    await screen.findAllByText("0 problems");

    expect(getProblems).toHaveBeenCalledTimes(DOMAINS.length);
    expect(getProblems).toHaveBeenCalledWith({ domain: DOMAINS[0], pageSize: 1 });
  });

  it("uses the singular 'problem' for a count of exactly one", async () => {
    getProblems.mockImplementation(({ domain }) => Promise.resolve({ total: domain === "FinTech" ? 1 : 0 }));

    renderDomains();

    expect(await screen.findByText("1 problem")).toBeInTheDocument();
  });

  it("clicking a domain card navigates to Discover pre-filtered to that domain", async () => {
    getProblems.mockResolvedValue({ total: 3 });
    renderDomains();

    const card = await screen.findByRole("button", { name: /Healthcare/i });
    await userEvent.click(card);

    expect(await screen.findByText("Discover Page")).toBeInTheDocument();
  });

  it("shows an error state when a domain count request fails", async () => {
    getProblems.mockRejectedValue(new Error("network error"));

    renderDomains();

    expect(await screen.findByText(/Couldn't load domain counts/i)).toBeInTheDocument();
  });
});
