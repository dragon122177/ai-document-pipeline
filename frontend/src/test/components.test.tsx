import { fireEvent, render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth";
import { StatusBadge } from "../components/StatusBadge";
import { UploadDialog } from "../components/UploadDialog";
import { LoginPage } from "../pages/LoginPage";

describe("workspace components", () => {
  it("renders a readable document status", () => {
    render(<StatusBadge status="NEEDS_REVIEW" />);
    expect(screen.getByText("Needs Review")).toBeInTheDocument();
  });

  it("switches between upload and pasted text ingestion", () => {
    render(
      <UploadDialog open onClose={vi.fn()} onCreated={vi.fn()} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /paste text/i }));
    expect(
      screen.getByPlaceholderText(/paste an invoice/i),
    ).toBeInTheDocument();
  });

  it("offers role-specific demo identities on the login screen", () => {
    render(
      <BrowserRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </BrowserRouter>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Reviewer" }));
    expect(screen.getByDisplayValue("reviewer@docuflux.demo")).toBeInTheDocument();
  });
});
