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
    await userEvent.type(screen.getByLabelText(/password/i), "correct-horse-battery");
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
    await userEvent.type(screen.getByLabelText(/password/i), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
    expect(screen.queryByText("Home Page")).not.toBeInTheDocument();
  });
});
