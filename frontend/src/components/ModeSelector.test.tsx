import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModeSelector } from "./ModeSelector";

describe("ModeSelector", () => {
  it("switches modes directly except solution", async () => {
    const onChange = vi.fn();
    render(<ModeSelector mode="tutor" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Dica" }));
    expect(onChange).toHaveBeenCalledWith("hint");
    await userEvent.click(screen.getByRole("button", { name: "Solução completa" }));
    expect(onChange).not.toHaveBeenCalledWith("solution");
    await userEvent.click(screen.getByRole("button", { name: "Sim, mostrar a solução" }));
    expect(onChange).toHaveBeenCalledWith("solution");
  });

  it("can cancel the solution confirmation", async () => {
    const onChange = vi.fn();
    render(<ModeSelector mode="tutor" onChange={onChange} />);
    await userEvent.click(screen.getByRole("button", { name: "Solução completa" }));
    await userEvent.click(screen.getByRole("button", { name: "Cancelar" }));
    expect(onChange).not.toHaveBeenCalled();
  });
});
