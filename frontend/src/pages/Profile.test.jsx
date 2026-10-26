import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Profile from "./Profile.jsx";
import { useAuth } from "../hooks/useAuth.js";
import { verifyPassword, updateProfile } from "../api/client.js";

vi.mock("../hooks/useAuth.js");
vi.mock("../api/client.js", async () => {
  const actual = await vi.importActual("../api/client.js");
  return { ...actual, verifyPassword: vi.fn(), updateProfile: vi.fn() };
});

const USER = { full_name: "Alice", email: "alice@example.com", created_at: "2026-01-01T00:00:00Z" };

function renderProfile() {
  return render(
    <MemoryRouter>
      <Profile />
    </MemoryRouter>
  );
}

describe("Profile — change password gate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuth.mockReturnValue({ user: USER, refreshUser: vi.fn() });
  });

  it("does not show new-password fields until the current password is verified", () => {
    renderProfile();

    expect(screen.getByLabelText("Current password")).toBeInTheDocument();
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Confirm new password")).not.toBeInTheDocument();
  });

  it("shows an error and keeps new-password fields hidden when the current password is wrong", async () => {
    verifyPassword.mockRejectedValue({ response: { data: { detail: "Incorrect password." } } });

    renderProfile();
    await userEvent.type(screen.getByLabelText("Current password"), "wrong-one");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(await screen.findByText("Incorrect password.")).toBeInTheDocument();
    expect(screen.queryByLabelText("New password")).not.toBeInTheDocument();
  });

  it("reveals new-password fields once the current password verifies, and submits both to updateProfile", async () => {
    verifyPassword.mockResolvedValue({ message: "Password verified." });
    updateProfile.mockResolvedValue({ ...USER });

    renderProfile();
    await userEvent.type(screen.getByLabelText("Current password"), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(verifyPassword).toHaveBeenCalledWith("correct-horse-battery");
    const newPasswordField = await screen.findByLabelText("New password");
    await userEvent.type(newPasswordField, "brand-new-password1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "brand-new-password1");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByText("Password changed.")).toBeInTheDocument();
    expect(updateProfile).toHaveBeenCalledWith({
      new_password: "brand-new-password1",
      current_password: "correct-horse-battery",
    });
  });

  it("rejects mismatched new passwords without calling updateProfile", async () => {
    verifyPassword.mockResolvedValue({ message: "Password verified." });

    renderProfile();
    await userEvent.type(screen.getByLabelText("Current password"), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: /continue/i }));

    await userEvent.type(await screen.findByLabelText("New password"), "brand-new-password1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "something-else1");
    await userEvent.click(screen.getByRole("button", { name: /update password/i }));

    expect(await screen.findByText(/don't match/i)).toBeInTheDocument();
    expect(updateProfile).not.toHaveBeenCalled();
  });
});

describe("Profile — optional personalization (interests / skill level)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with nothing selected for a user who never set preferences, and saves that as-is", async () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: null }, refreshUser: vi.fn() });
    updateProfile.mockResolvedValue({ ...USER });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: [], skill_level: "" });
  });

  it("pre-selects whatever the user already has saved (round-tripped via an unchanged save)", async () => {
    useAuth.mockReturnValue({
      user: { ...USER, interests: ["Healthcare", "FinTech"], skill_level: "advanced" },
      refreshUser: vi.fn(),
    });
    updateProfile.mockResolvedValue({ ...USER });
    renderProfile();

    // Saved without touching anything — if the two fields weren't really
    // pre-selected from `user`, this would send [] / "" instead.
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: ["Healthcare", "FinTech"], skill_level: "advanced" });
  });

  it("toggling interests and saving sends exactly the selected set to updateProfile", async () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: null }, refreshUser: vi.fn() });
    updateProfile.mockResolvedValue({ ...USER, interests: ["AI/ML", "FinTech"], skill_level: null });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "AI/ML" }));
    await userEvent.click(screen.getByRole("button", { name: "FinTech" }));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: ["AI/ML", "FinTech"], skill_level: "" });
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("selecting a skill level is single-select — picking a second one replaces the first", async () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: null }, refreshUser: vi.fn() });
    updateProfile.mockResolvedValue({ ...USER });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "Beginner" }));
    await userEvent.click(screen.getByRole("button", { name: "Advanced" }));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: [], skill_level: "advanced" });
  });

  it("clicking an already-selected skill level deselects it", async () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: "beginner" }, refreshUser: vi.fn() });
    updateProfile.mockResolvedValue({ ...USER });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "Beginner" }));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: [], skill_level: "" });
  });

  it("Clear resets both fields locally, and the next save sends the explicit clear values", async () => {
    useAuth.mockReturnValue({
      user: { ...USER, interests: ["Healthcare"], skill_level: "advanced" },
      refreshUser: vi.fn(),
    });
    updateProfile.mockResolvedValue({ ...USER, interests: [], skill_level: null });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "Clear" }));
    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(updateProfile).toHaveBeenCalledWith({ interests: [], skill_level: "" });
  });

  it("the Clear button is disabled when there's nothing to clear", () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: null }, refreshUser: vi.fn() });
    renderProfile();

    expect(screen.getByRole("button", { name: "Clear" })).toBeDisabled();
  });

  it("shows an error instead of silently failing when the save fails", async () => {
    useAuth.mockReturnValue({ user: { ...USER, interests: [], skill_level: null }, refreshUser: vi.fn() });
    updateProfile.mockRejectedValue({ response: { data: { detail: "Something went wrong." } } });
    renderProfile();

    await userEvent.click(screen.getByRole("button", { name: "Save preferences" }));

    expect(await screen.findByText("Something went wrong.")).toBeInTheDocument();
  });
});
