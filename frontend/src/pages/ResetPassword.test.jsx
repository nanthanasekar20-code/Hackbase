import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ResetPassword from "./ResetPassword.jsx";
import { resetPassword } from "../api/client.js";

vi.mock("../api/client.js", async () => {
  const actual = await vi.importActual("../api/client.js");
  return { ...actual, resetPassword: vi.fn() };
});

function renderPage(initialPath) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/login" element={<div>Login Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResetPassword", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows a message instead of a form when the link has no token", () => {
    renderPage("/reset-password");

    expect(screen.getByText(/missing its reset token/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/new password/i)).not.toBeInTheDocument();
  });

  it("submits the token and new password from the URL", async () => {
    resetPassword.mockResolvedValue({ message: "Password updated." });

    renderPage("/reset-password?token=abc123");
    await userEvent.type(screen.getByLabelText("New password"), "brand-new-password1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "brand-new-password1");
    await userEvent.click(screen.getByRole("button", { name: /set new password/i }));

    expect(resetPassword).toHaveBeenCalledWith("abc123", "brand-new-password1");
    expect(await screen.findByText(/password updated/i)).toBeInTheDocument();
  });

  it("rejects mismatched passwords without calling the API", async () => {
    renderPage("/reset-password?token=abc123");
    await userEvent.type(screen.getByLabelText("New password"), "brand-new-password1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "something-else1");
    await userEvent.click(screen.getByRole("button", { name: /set new password/i }));

    expect(await screen.findByText(/don't match/i)).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("shows the backend's error message for an expired token", async () => {
    resetPassword.mockRejectedValue({
      response: { data: { detail: "This reset link is invalid or has expired." } },
    });

    renderPage("/reset-password?token=expired");
    await userEvent.type(screen.getByLabelText("New password"), "brand-new-password1");
    await userEvent.type(screen.getByLabelText("Confirm new password"), "brand-new-password1");
    await userEvent.click(screen.getByRole("button", { name: /set new password/i }));

    expect(await screen.findByText("This reset link is invalid or has expired.")).toBeInTheDocument();
  });
});
