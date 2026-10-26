import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ForgotPassword from "./ForgotPassword.jsx";
import { forgotPassword } from "../api/client.js";

vi.mock("../api/client.js", async () => {
  const actual = await vi.importActual("../api/client.js");
  return { ...actual, forgotPassword: vi.fn() };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/forgot-password"]}>
      <Routes>
        <Route path="/forgot-password" element={<ForgotPassword />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ForgotPassword", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends the email and shows the generic confirmation message", async () => {
    forgotPassword.mockResolvedValue({ message: "If an account exists for that email, a reset link has been sent." });

    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    await userEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(forgotPassword).toHaveBeenCalledWith("alice@example.com");
    expect(await screen.findByText(/reset link has been sent/i)).toBeInTheDocument();
  });

  it("shows the backend's error message when the request fails", async () => {
    forgotPassword.mockRejectedValue({
      response: { data: { detail: "Email sending is not configured on this server." } },
    });

    renderPage();
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    await userEvent.click(screen.getByRole("button", { name: /send reset link/i }));

    expect(await screen.findByText("Email sending is not configured on this server.")).toBeInTheDocument();
  });
});
