import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ChemState } from "@/lib/types";
import { StatePanel } from "./StatePanel";

const state: ChemState = {
  schema_version: 1,
  stage: "hypothesis",
  signal_notes: [{ peak_id: "P1", interpretation: "OCH2 vizinho a CH3", status: "supported" }],
  hypotheses: [{ id: "H1", text: "grupo etila ligado a O", by: "student", status: "open", evidence: ["P1", "P3"] }],
  unresolved: ["singleto em 2,05 ppm"],
  hints_given: 2,
  proposed_structures: [],
};

describe("StatePanel", () => {
  it("shows stage, hypotheses, notes and pending items", () => {
    render(<StatePanel state={state} />);
    expect(screen.getByText("Hipótese")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("grupo etila ligado a O")).toBeInTheDocument();
    expect(screen.getByText(/OCH2 vizinho a CH3/)).toBeInTheDocument();
    expect(screen.getByText("singleto em 2,05 ppm")).toBeInTheDocument();
    expect(screen.getByText("Dicas usadas: 2")).toBeInTheDocument();
  });
});
