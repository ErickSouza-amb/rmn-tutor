import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Peak } from "@/lib/types";
import { PeakTableEditor } from "./PeakTableEditor";

const P1: Peak = { id: "P1", ppm: 4.12, integral: 2, multiplicity: "q", j_hz: [7.1], source: "user", note: null };

describe("PeakTableEditor", () => {
  it("renders rows and edits values", async () => {
    const onChange = vi.fn();
    render(<PeakTableEditor peaks={[P1]} onChange={onChange} />);
    expect(screen.getAllByTestId("peak-row")).toHaveLength(1);
    const ppm = screen.getByLabelText("δ de P1");
    await userEvent.clear(ppm);
    await userEvent.type(ppm, "4.1");
    expect(onChange).toHaveBeenLastCalledWith([{ ...P1, ppm: 4.1 }]);
  });

  it("parses J list and removes rows", async () => {
    const onChange = vi.fn();
    render(<PeakTableEditor peaks={[P1]} onChange={onChange} />);
    const j = screen.getByLabelText("J de P1");
    await userEvent.clear(j);
    await userEvent.type(j, "8,0; 2,0");
    expect(onChange).toHaveBeenLastCalledWith([{ ...P1, j_hz: [8, 2] }]);
    await userEvent.click(screen.getByRole("button", { name: "Remover P1" }));
    expect(onChange).toHaveBeenLastCalledWith([]);
  });

  it("pastes a list through the parser and shows errors", async () => {
    const onChange = vi.fn();
    const parse = vi.fn().mockResolvedValue({ peaks: [P1], errors: [{ line: 2, message: "termo não reconhecido: 'x'" }] });
    render(<PeakTableEditor peaks={[]} onChange={onChange} parse={parse} />);
    await userEvent.type(screen.getByTestId("peak-paste"), "4.12 2 q 7.1");
    await userEvent.click(screen.getByRole("button", { name: "Interpretar lista" }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith([P1]));
    expect(screen.getByText("Linha 2: termo não reconhecido: 'x'")).toBeInTheDocument();
  });
});
