import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { SimulatedTutorBanner } from "./SimulatedTutorBanner";

afterEach(() => vi.restoreAllMocks());

describe("SimulatedTutorBanner", () => {
  it("warns when the backend runs the simulated tutor", async () => {
    vi.spyOn(api, "health").mockResolvedValue({ status: "ok", db: "ok", tutor: "simulated" });
    render(<SimulatedTutorBanner />);
    expect(await screen.findByTestId("simulated-banner")).toHaveTextContent("tutor simulado");
  });

  it("stays hidden with the real tutor", async () => {
    const spy = vi.spyOn(api, "health").mockResolvedValue({ status: "ok", db: "ok", tutor: "claude" });
    render(<SimulatedTutorBanner />);
    await vi.waitFor(() => expect(spy).toHaveBeenCalled());
    expect(screen.queryByTestId("simulated-banner")).toBeNull();
  });
});
