import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import DiscoverFilters from "./DiscoverFilters.jsx";

const NOVELTY_FIELD = { key: "novelty_score", label: "Novelty", polarity: "min" };
const HARDWARE_FIELD = { key: "hardware_requirement_score", label: "Hardware needed", polarity: "max" };

const EMPTY_FACETS = { source: [], domain: [], difficulty: [], technologies: [] };

function renderFilters(overrides = {}) {
  const props = {
    facets: EMPTY_FACETS,
    active: {},
    onToggle: vi.fn(),
    scoreFields: [],
    scoreFilters: {},
    onScoreFilterChange: vi.fn(),
    hasActiveFilters: false,
    onClearAll: vi.fn(),
    sortBy: "relevance",
    onSortChange: vi.fn(),
    resultCount: 3,
    ...overrides,
  };
  render(<DiscoverFilters {...props} />);
  return props;
}

describe("DiscoverFilters — Scores group", () => {
  it("renders no Scores control at all when no score field has anything behind it", () => {
    renderFilters({ scoreFields: [] });
    expect(screen.queryByText("Scores")).not.toBeInTheDocument();
  });

  it("is collapsed by default and reveals the sliders on click", async () => {
    renderFilters({ scoreFields: [NOVELTY_FIELD] });

    expect(screen.queryByRole("slider", { name: "Novelty" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByText("Scores"));

    expect(screen.getByRole("slider", { name: "Novelty" })).toBeInTheDocument();
  });

  it("shows a ≥ minimum label for an ordinary field and a ≤ maximum label for hardware_requirement_score", async () => {
    renderFilters({ scoreFields: [NOVELTY_FIELD, HARDWARE_FIELD] });
    await userEvent.click(screen.getByText("Scores"));

    expect(screen.getByText("Novelty ≥ 0.0")).toBeInTheDocument();
    expect(screen.getByText("Hardware needed ≤ 10.0")).toBeInTheDocument();
  });

  it("calls onScoreFilterChange with the field object and the new numeric value", async () => {
    const { onScoreFilterChange } = renderFilters({ scoreFields: [NOVELTY_FIELD] });
    await userEvent.click(screen.getByText("Scores"));

    fireEvent.change(screen.getByRole("slider", { name: "Novelty" }), { target: { value: "7" } });

    expect(onScoreFilterChange).toHaveBeenCalledWith(NOVELTY_FIELD, 7);
  });

  it("shows an active count and a reset button only once a field has a stored threshold", async () => {
    const { onScoreFilterChange } = renderFilters({
      scoreFields: [NOVELTY_FIELD],
      scoreFilters: { novelty_score: 7 },
    });

    expect(screen.getByText("Scores (1)")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Scores (1)"));

    expect(screen.getByText("Novelty ≥ 7.0")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Clear Novelty filter" }));

    // Resetting calls back with this field's neutral (no-op) bound, 0.
    expect(onScoreFilterChange).toHaveBeenCalledWith(NOVELTY_FIELD, 0);
  });
});

describe("DiscoverFilters — persistent Clear all filters", () => {
  it("is hidden while no filter is active", () => {
    renderFilters({ hasActiveFilters: false });
    expect(screen.queryByText("Clear all filters")).not.toBeInTheDocument();
  });

  it("shows and calls onClearAll when any filter is active", async () => {
    const { onClearAll } = renderFilters({ hasActiveFilters: true });

    const button = screen.getByText("Clear all filters");
    await userEvent.click(button);

    expect(onClearAll).toHaveBeenCalled();
  });
});

describe("DiscoverFilters — existing chip facets still work", () => {
  it("still renders exact-value chip groups and reports toggles unchanged", async () => {
    const { onToggle } = renderFilters({
      facets: { source: ["sih", "unstop"], domain: [], difficulty: [], technologies: [] },
    });

    await userEvent.click(screen.getByRole("button", { name: "sih" }));

    expect(onToggle).toHaveBeenCalledWith("source", "sih");
  });
});
