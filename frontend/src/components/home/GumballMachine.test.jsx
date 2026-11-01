import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import GumballMachine from "./GumballMachine.jsx";
import { getRandomProblems } from "../../api/client.js";

vi.mock("../../api/client.js", () => ({
  getRandomProblems: vi.fn(),
}));

function renderMachine() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<GumballMachine />} />
        <Route path="/problem/:id" element={<div>Problem Details Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

const PICKED_PROBLEM = {
  id: "sih:p1",
  title: "AI-Powered Crop Disease Detector",
  source: "sih",
  domain: ["Agriculture"],
  summary: "Detect crop disease from leaf photos.",
};

describe("GumballMachine", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts idle, with no ball and no network call yet", () => {
    renderMachine();
    expect(screen.getByText("Press spin to begin")).toBeInTheDocument();
    expect(getRandomProblems).not.toHaveBeenCalled();
  });

  it("spinning the machine is purely local — lands on a clickable ball without calling the API", async () => {
    renderMachine();

    await userEvent.click(screen.getByRole("button", { name: /spin the machine/i }));

    expect(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 })).toBeInTheDocument();
    expect(getRandomProblems).not.toHaveBeenCalled();
  });

  it("clicking the ball fetches one real random problem and reveals it", async () => {
    getRandomProblems.mockResolvedValue({ problems: [PICKED_PROBLEM] });
    renderMachine();

    await userEvent.click(screen.getByRole("button", { name: /spin the machine/i }));
    const ball = await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 });
    await userEvent.click(ball);

    expect(await screen.findByText("AI-Powered Crop Disease Detector")).toBeInTheDocument();
    expect(screen.getByText("Agriculture")).toBeInTheDocument();
    expect(getRandomProblems).toHaveBeenCalledWith(1);
    expect(getRandomProblems).toHaveBeenCalledTimes(1); // never called during the spin itself
  });

  it("View problem navigates to the real problem's detail page", async () => {
    getRandomProblems.mockResolvedValue({ problems: [PICKED_PROBLEM] });
    renderMachine();

    await userEvent.click(screen.getByRole("button", { name: /spin the machine/i }));
    await userEvent.click(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 }));
    await screen.findByText("AI-Powered Crop Disease Detector");

    await userEvent.click(screen.getByRole("button", { name: /view problem/i }));

    expect(await screen.findByText("Problem Details Page")).toBeInTheDocument();
  });

  it("Spin again resets back to a fresh spin, discarding the previous pick", async () => {
    getRandomProblems.mockResolvedValue({ problems: [PICKED_PROBLEM] });
    renderMachine();

    await userEvent.click(screen.getByRole("button", { name: /spin the machine/i }));
    await userEvent.click(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 }));
    await screen.findByText("AI-Powered Crop Disease Detector");

    await userEvent.click(screen.getByRole("button", { name: /spin again/i }));

    expect(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.queryByText("AI-Powered Crop Disease Detector")).not.toBeInTheDocument();
  });

  it("shows a real error (not a fabricated problem) when the request fails, and Try again recovers", async () => {
    getRandomProblems.mockRejectedValueOnce(new Error("network error"));
    renderMachine();

    await userEvent.click(screen.getByRole("button", { name: /spin the machine/i }));
    await userEvent.click(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 }));

    expect(await screen.findByText(/couldn't fetch a problem/i)).toBeInTheDocument();

    getRandomProblems.mockResolvedValue({ problems: [PICKED_PROBLEM] });
    await userEvent.click(screen.getByRole("button", { name: /try again/i }));
    await userEvent.click(await screen.findByRole("button", { name: /open your ball/i }, { timeout: 3000 }));

    expect(await screen.findByText("AI-Powered Crop Disease Detector")).toBeInTheDocument();
  });
});
