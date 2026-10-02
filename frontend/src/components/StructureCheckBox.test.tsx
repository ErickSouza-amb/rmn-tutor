import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { StructureCheckBox } from "./StructureCheckBox";

afterEach(() => vi.restoreAllMocks());

describe("StructureCheckBox", () => {
  it("shows check results", async () => {
    vi.spyOn(api, "structureCheck").mockResolvedValue({
      canonical_smiles: "CCOC(C)=O",
      formula: "C4H8O2",
      total_h: 8,
      h_environments: [],
      checks: [
        { name: "formula", status: "pass", detail: "Estrutura: C4H8O2", heuristic: false },
        { name: "shift_ranges", status: "fail", detail: "Nenhum sinal na faixa", heuristic: true },
      ],
      limitations: ["Não é veredito."],
      check_id: "c1",
    });
    const onChecked = vi.fn();
    render(<StructureCheckBox sessionId="s1" onChecked={onChecked} />);
    await userEvent.type(screen.getByTestId("smiles-input"), "CCOC(C)=O");
    await userEvent.click(screen.getByRole("button", { name: "Verificar estrutura" }));
    expect(await screen.findByTestId("check-formula")).toHaveTextContent("Estrutura: C4H8O2");
    expect(screen.getByTestId("check-shift_ranges")).toHaveTextContent("heurística");
    expect(onChecked).toHaveBeenCalled();
  });
});
