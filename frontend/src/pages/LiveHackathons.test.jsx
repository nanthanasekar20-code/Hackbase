import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import LiveHackathons from "./LiveHackathons.jsx";
import { getLiveHackathons } from "../api/client.js";

vi.mock("../api/client.js", () => ({
  getLiveHackathons: vi.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <LiveHackathons />
    </MemoryRouter>
  );
}

describe("LiveHackathons page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders real hackathons with working links, never placeholder data", async () => {
    getLiveHackathons.mockResolvedValue({
      hackathons: [
        {
          title: "InterWell Hack2.0",
          source: "devpost",
          url: "https://interwell-hack2-0.devpost.com/",
          deadline: "Oct 03 - 31, 2026",
        },
        { title: "HACK.COMS 2026", source: "mlh", url: "https://events.mlh.io/events/14418-hack-coms-2026" },
      ],
    });

    renderPage();

    const link1 = await screen.findByRole("link", { name: /InterWell Hack2\.0/i });
    expect(link1).toHaveAttribute("href", "https://interwell-hack2-0.devpost.com/");
    expect(link1).toHaveAttribute("target", "_blank");

    const link2 = screen.getByRole("link", { name: /HACK\.COMS 2026/i });
    expect(link2).toHaveAttribute("href", "https://events.mlh.io/events/14418-hack-coms-2026");

    expect(screen.getByText("2 open")).toBeInTheDocument();
  });

  it("shows an honest empty state when nothing is currently open, never fabricated entries", async () => {
    getLiveHackathons.mockResolvedValue({ hackathons: [] });

    renderPage();

    expect(await screen.findByText("No live hackathons right now")).toBeInTheDocument();
  });

  it("shows an error state when the live-hackathons request fails", async () => {
    getLiveHackathons.mockRejectedValue(new Error("network error"));

    renderPage();

    expect(await screen.findByText(/Couldn't load live hackathons/i)).toBeInTheDocument();
  });
});

describe("LiveHackathons page — search and platform filter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getLiveHackathons.mockResolvedValue({
      per_source_counts: { devpost: 2, mlh: 1 },
      hackathons: [
        { title: "AI Buildathon", source: "devpost", url: "https://a.devpost.com/" },
        { title: "Climate Hack", source: "devpost", url: "https://b.devpost.com/" },
        { title: "AI for Health", source: "mlh", url: "https://c.mlh.io/" },
      ],
    });
  });

  it("filters by title as you type, client-side (no extra fetch)", async () => {
    renderPage();
    await screen.findByText("AI Buildathon");

    await userEvent.type(screen.getByRole("searchbox", { name: /search live hackathons/i }), "climate");

    expect(screen.getByText("Climate Hack")).toBeInTheDocument();
    expect(screen.queryByText("AI Buildathon")).not.toBeInTheDocument();
    expect(screen.queryByText("AI for Health")).not.toBeInTheDocument();
    expect(getLiveHackathons).toHaveBeenCalledTimes(1); // only the initial mount fetch
  });

  it("filters by platform via a chip, and clicking it again clears it", async () => {
    renderPage();
    await screen.findByText("AI Buildathon");

    await userEvent.click(screen.getByRole("button", { name: "mlh" }));
    expect(screen.getByText("AI for Health")).toBeInTheDocument();
    expect(screen.queryByText("AI Buildathon")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "mlh" }));
    expect(screen.getByText("AI Buildathon")).toBeInTheDocument();
    expect(screen.getByText("AI for Health")).toBeInTheDocument();
  });

  it("combines the search box and the platform filter", async () => {
    renderPage();
    await screen.findByText("AI Buildathon");

    await userEvent.click(screen.getByRole("button", { name: "devpost" }));
    await userEvent.type(screen.getByRole("searchbox", { name: /search live hackathons/i }), "climate");

    expect(screen.getByText("Climate Hack")).toBeInTheDocument();
    expect(screen.queryByText("AI Buildathon")).not.toBeInTheDocument();
    expect(screen.queryByText("AI for Health")).not.toBeInTheDocument();
  });

  it("shows a filtered-empty state (not the generic one) when nothing matches, with its own Clear filters", async () => {
    renderPage();
    await screen.findByText("AI Buildathon");

    await userEvent.type(screen.getByRole("searchbox", { name: /search live hackathons/i }), "nonexistent-topic");

    expect(await screen.findByText("No hackathons match these filters")).toBeInTheDocument();

    // Both the persistent filter-bar button and the empty-state's own
    // action render "Clear filters" once there's nothing left to show.
    const clearButtons = screen.getAllByRole("button", { name: "Clear filters" });
    await userEvent.click(clearButtons[0]);

    expect(await screen.findByText("AI Buildathon")).toBeInTheDocument();
  });

  it("only shows a platform chip for a source with at least one open hackathon", async () => {
    getLiveHackathons.mockResolvedValue({
      per_source_counts: { devpost: 1, kaggle: 0 },
      hackathons: [{ title: "Solo Devpost Hack", source: "devpost", url: "https://x.devpost.com/" }],
    });
    renderPage();
    await screen.findByText("Solo Devpost Hack");

    // A single available source isn't worth a filter chip either — same
    // "nothing to filter between" rule as Discover's facet groups.
    expect(screen.queryByRole("button", { name: "devpost" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "kaggle" })).not.toBeInTheDocument();
  });
});
