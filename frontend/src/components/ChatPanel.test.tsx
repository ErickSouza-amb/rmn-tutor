import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";
import type { SessionData, TurnEvent } from "@/lib/types";
import { ChatPanel } from "./ChatPanel";

const session = {
  id: "s1",
  title: "t",
  experiment: "1H",
  metadata: {},
  exercise: null,
  has_image: false,
  peaks: [],
  chem_state: { schema_version: 1, stage: "observe", signal_notes: [], hypotheses: [], unresolved: [], hints_given: 0, proposed_structures: [] },
  assist_mode: "tutor",
  created_at: "",
  updated_at: "",
  messages: [],
} as SessionData;

afterEach(() => vi.restoreAllMocks());

describe("ChatPanel", () => {
  it("streams the tutor answer with tool chips", async () => {
    vi.spyOn(api, "updateSession").mockResolvedValue(session);
    vi.spyOn(api, "sendMessage").mockImplementation(async (_id, _text, _mode, onEvent: (e: TurnEvent) => void) => {
      onEvent({ event: "text_delta", data: { text: "Vou consultar. " } });
      onEvent({ event: "tool_call", data: { name: "get_peak_list", input: {} } });
      onEvent({ event: "text_delta", data: { text: "O que você vê em P1?" } });
      onEvent({ event: "done", data: { text: "Vou consultar.\n\nO que você vê em P1?", chem_state: session.chem_state, assist_mode: "tutor" } });
    });
    const onStateChange = vi.fn();
    render(<ChatPanel session={session} onStateChange={onStateChange} onModeChange={() => {}} />);
    await userEvent.type(screen.getByTestId("chat-input"), "Vejo três sinais");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("Vejo três sinais")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("assistant-message")).toHaveTextContent("O que você vê em P1?"));
    expect(screen.getByTestId("tool-chip")).toHaveTextContent("consultou a lista de picos");
    expect(onStateChange).toHaveBeenCalled();
  });

  it("shows API errors and keeps the input enabled", async () => {
    vi.spyOn(api, "sendMessage").mockRejectedValue(new ApiError(409, "turn_in_progress", "O tutor ainda está respondendo."));
    render(<ChatPanel session={session} onStateChange={() => {}} onModeChange={() => {}} />);
    await userEvent.type(screen.getByTestId("chat-input"), "Oi");
    await userEvent.click(screen.getByRole("button", { name: "Enviar" }));
    expect(await screen.findByText("O tutor ainda está respondendo.")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).not.toBeDisabled();
  });
});
