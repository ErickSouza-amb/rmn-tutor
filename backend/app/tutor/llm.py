import copy
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal, Protocol

import anthropic

from app.config import Settings

BETAS = ["compact-2026-01-12", "server-side-fallback-2026-07-01"]


@dataclass
class LLMEvent:
    type: Literal["text_delta", "final"]
    text: str | None = None
    message: dict | None = None


class LLMError(Exception):
    pass


class LLMClient(Protocol):
    def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]: ...


class AnthropicLLM:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, max_retries=1, timeout=120.0)

    async def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]:
        s = self.settings
        try:
            async with self.client.beta.messages.stream(
                model=s.tutor_model,
                max_tokens=s.tutor_max_tokens,
                system=system,
                tools=tools,
                messages=messages,
                output_config={"effort": s.tutor_effort},
                cache_control={"type": "ephemeral"},
                betas=BETAS,
                context_management={"edits": [{"type": "compact_20260112"}]},
                fallbacks="default",
            ) as stream:
                async for event in stream:
                    if event.type == "text":
                        yield LLMEvent("text_delta", text=event.text)
                final = await stream.get_final_message()
        except anthropic.APIStatusError as exc:
            raise LLMError(f"API status {exc.status_code} (request_id={getattr(exc, 'request_id', None)})") from exc
        except anthropic.APIConnectionError as exc:
            raise LLMError("API connection error") from exc
        yield LLMEvent(
            "final",
            message={
                "content": [b.model_dump(mode="json", exclude_none=True) for b in final.content],
                "stop_reason": final.stop_reason,
                "usage": final.usage.model_dump(mode="json", exclude_none=True) if final.usage else {},
            },
        )


class FakeLLM:
    """Deterministic stand-in used in tests, local dev without a key, and E2E (FAKE_LLM=1).

    Default behaviour per user turn: first call asks for get_peak_list; after a tool_result it answers
    with a Socratic question mentioning P1. A script (list of final-message dicts) overrides it.
    """

    def __init__(self, script: list[dict] | None = None) -> None:
        self.script = list(script or [])
        self.calls: list[list[dict]] = []
        self._n = 0

    async def stream(self, *, system: list[dict], tools: list[dict], messages: list[dict]) -> AsyncIterator[LLMEvent]:
        self.calls.append(copy.deepcopy(messages))
        self._n += 1
        if self.script:
            message = self.script.pop(0)
        else:
            last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
            after_tool = isinstance(last_user and last_user["content"], list) and any(
                isinstance(b, dict) and b.get("type") == "tool_result" for b in last_user["content"]
            )
            if after_tool:
                message = {
                    "content": [{"type": "text", "text": "Ótimo. Olhando a tabela, o que você observa no sinal P1? Quantos vizinhos ele sugere?"}],
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 120, "output_tokens": 30},
                }
            else:
                message = {
                    "content": [
                        {"type": "text", "text": "Vou consultar a lista de picos. "},
                        {"type": "tool_use", "id": f"toolu_fake_{self._n}", "name": "get_peak_list", "input": {}},
                    ],
                    "stop_reason": "tool_use",
                    "usage": {"input_tokens": 100, "output_tokens": 20},
                }
        for block in message["content"]:
            if block.get("type") == "text":
                yield LLMEvent("text_delta", text=block["text"])
        yield LLMEvent("final", message=copy.deepcopy(message))


def get_llm(settings: Settings) -> LLMClient:
    if settings.fake_llm or not settings.anthropic_api_key:
        return FakeLLM()
    return AnthropicLLM(settings)
