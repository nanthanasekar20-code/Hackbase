import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Login from "./Login.jsx";
import { useAuth } from "../hooks/useAuth.js";

vi.mock("../hooks/useAuth.js");

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<div>Home Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("logs in with the entered credentials and navigates home on success", async () => {
    const login = vi.fn().mockResolvedValue("fake-token");
    useAuth.mockReturnValue({ login });

    renderLogin();
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    // Exact match — a regex here also matches the show/hide-password
    // toggle button's aria-label ("Show password").
    await userEvent.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(login).toHaveBeenCalledWith("alice@example.com", "correct-horse-battery");
    expect(await screen.findByText("Home Page")).toBeInTheDocument();
  });

  it("shows the backend's error message and does not navigate on failure", async () => {
    const login = vi.fn().mockRejectedValue({
      response: { data: { detail: "Incorrect email or password." } },
    });
    useAuth.mockReturnValue({ login });

    renderLogin();
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
    expect(screen.queryByText("Home Page")).not.toBeInTheDocument();
  });

  it("toggles password visibility when the eye icon is clicked", async () => {
    useAuth.mockReturnValue({ login: vi.fn() });
    renderLogin();

    const passwordInput = screen.getByLabelText("Password");
    expect(passwordInput).toHaveAttribute("type", "password");

    await userEvent.click(screen.getByRole("button", { name: /show password/i }));
    expect(passwordInput).toHaveAttribute("type", "text");

    await userEvent.click(screen.getByRole("button", { name: /hide password/i }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });

  it("links to the forgot-password page", () => {
    useAuth.mockReturnValue({ login: vi.fn() });
    renderLogin();

    expect(screen.getByRole("link", { name: /forgot password/i })).toHaveAttribute("href", "/forgot-password");
  });
});
