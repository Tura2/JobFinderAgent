import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import MatchCard from "../MatchCard";

const mockMatch = {
  id: 1,
  score: 88,
  reasoning: "Strong React fit.",
  status: "new",
  matched_at: "2026-04-17T10:00:00Z",
  job_title: "Senior Frontend Engineer",
  company_name: "Vercel",
};

describe("MatchCard", () => {
  it("renders job title and company", () => {
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={vi.fn()} />
    );
    expect(screen.getByText("Senior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Vercel")).toBeInTheDocument();
  });

  it("shows score badge", () => {
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={vi.fn()} />
    );
    expect(screen.getByText("88%")).toBeInTheDocument();
  });

  it("calls onSkip when Skip is clicked", () => {
    const onSkip = vi.fn();
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={onSkip} onApply={vi.fn()} />
    );
    fireEvent.click(screen.getByText("Skip"));
    expect(onSkip).toHaveBeenCalledWith(1);
  });

  it("calls onApply when Apply is clicked", () => {
    const onApply = vi.fn();
    render(
      <MatchCard match={mockMatch} onTap={vi.fn()} onSkip={vi.fn()} onApply={onApply} />
    );
    fireEvent.click(screen.getByText("Apply"));
    expect(onApply).toHaveBeenCalledWith(1);
  });
});
