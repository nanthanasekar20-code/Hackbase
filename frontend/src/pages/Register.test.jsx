import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import Register from "./Register.jsx";
import { useAuth } from "../hooks/useAuth.js";

vi.mock("../hooks/useAuth.js");

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<Register />} />
        <Route path="/" element={<div>Home Page</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("Register", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("registers with email/password/name and navigates home on success", async () => {
    const register = vi.fn().mockResolvedValue("fake-token");
    useAuth.mockReturnValue({ register });

    renderRegister();
    await userEvent.type(screen.getByLabelText(/name/i), "Alice");
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(register).toHaveBeenCalledWith("alice@example.com", "correct-horse-battery", "Alice");
    expect(await screen.findByText("Home Page")).toBeInTheDocument();
  });

  it("shows the backend's error message on a duplicate email", async () => {
    const register = vi.fn().mockRejectedValue({
      response: { data: { detail: "An account with this email already exists." } },
    });
    useAuth.mockReturnValue({ register });

    renderRegister();
    await userEvent.type(screen.getByLabelText(/email/i), "alice@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "correct-horse-battery");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByText("An account with this email already exists.")).toBeInTheDocument();
    expect(screen.queryByText("Home Page")).not.toBeInTheDocument();
  });
});
