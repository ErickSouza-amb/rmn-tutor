import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.config import Settings
from app.exercises.catalog import exercise_image_path, get_exercise
from app.logging import log_event
from app.nmr_engine.models import Peak
from app.nmr_tools.registry import ToolContext, execute_tool, tool_definitions
from app.nmr_tools.state_ops import ChemState, ProposedStructure
from app.store import repo
from app.store.blob import BlobStore
from app.tutor.context import IMAGE_MARKER, build_api_messages, has_image_marker
from app.tutor.llm import LLMClient, LLMError
from app.tutor.prompts import SYSTEM_PROMPT, build_turn_context

logger = logging.getLogger("rmn.tutor")
SYSTEM_BLOCKS = [{"type": "text", "text": SYSTEM_PROMPT}]
LLM_UNAVAILABLE = "O tutor está indisponível no momento. Sua mensagem foi salva; tente reenviar em instantes."


@dataclass
class TurnEvent:
    event: str
    data: dict


async def _load_image(row, exercise, blob: BlobStore) -> tuple[bytes, str] | None:
    if exercise is not None:
        return exercise_image_path(exercise.id).read_bytes(), "image/png"
    if row.image_blob:
        return await blob.get(row.image_blob), row.image_media_type or "image/png"
    return None


def _text_of(content: list[dict]) -> str:
    return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


async def run_turn(
    *,
    session_id: uuid.UUID,
    user_text: str,
    mode: str | None,
    llm: LLMClient,
    blob: BlobStore,
    settings: Settings,
    sessionmaker,
) -> AsyncIterator[TurnEvent]:
    started = time.perf_counter()
    async with sessionmaker() as db:
        row = await repo.get_session(db, session_id)
        if mode:
            row.assist_mode = mode
        mode = row.assist_mode
        state = ChemState.model_validate(row.chem_state or {})
        if mode == "hint":
            state.hints_given += 1
        peaks = [Peak.model_validate(p) for p in row.peaks or []]
        exercise = get_exercise(row.exercise_id) if row.exercise_id else None
        has_image = exercise is not None or bool(row.image_blob)

        history = await repo.list_messages(db, session_id)
        user_blocks: list = []
        if has_image and not any(has_image_marker(r.content) for r in history):
            user_blocks.append(dict(IMAGE_MARKER))
        user_blocks.append({"type": "text", "text": user_text})
        user_rows = await repo.add_messages(
            db, session_id, [repo.NewMessage("user", user_blocks, display_text=user_text, mode=mode)], commit=False
        )
        row.chem_state = state.model_dump()
        await repo.save(db, row)
        history = history + user_rows

        image = await _load_image(row, exercise, blob) if has_image else None
        context_text = build_turn_context(
            metadata=row.meta or {}, peaks=peaks, chem_state=state, mode=mode,
            has_image=has_image, is_exercise=exercise is not None,
        )
        api_messages = build_api_messages(history, image) + [{"role": "system", "content": context_text}]
        pending: list[repo.NewMessage] = [repo.NewMessage("system", context_text, mode=mode)]
        ctx = ToolContext(
            peaks=peaks, metadata=row.meta or {}, chem_state=state, assist_mode=mode,
            has_image=has_image, experiment=row.experiment,
            answer_smiles=exercise.answer_smiles if exercise else None,
        )
        tools = tool_definitions()
        texts: list[str] = []
        checks: list[tuple[str, dict]] = []
        tool_names: list[str] = []
        usage_total = {"input_tokens": 0, "output_tokens": 0}
        last_assistant: repo.NewMessage | None = None
        hit_limit = False

        try:
            for iteration in range(settings.tutor_max_tool_iterations):
                final = None
                async for ev in llm.stream(system=SYSTEM_BLOCKS, tools=tools, messages=api_messages):
                    if ev.type == "text_delta":
                        yield TurnEvent("text_delta", {"text": ev.text})
                    else:
                        final = ev.message
                if final is None:
                    raise LLMError("stream ended without a final message")
                content = final["content"]
                for k in usage_total:
                    usage_total[k] += int(final.get("usage", {}).get(k) or 0)
                last_assistant = repo.NewMessage("assistant", content, mode=mode, usage=final.get("usage"))
                pending.append(last_assistant)
                api_messages.append({"role": "assistant", "content": content})
                if text := _text_of(content):
                    texts.append(text)
                stop = final.get("stop_reason")
                if stop == "pause_turn":
                    continue
                tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
                if stop != "tool_use" or not tool_uses:
                    if stop == "refusal":
                        texts.append("Não posso continuar com esse pedido. Vamos voltar à interpretação do espectro?")
                    break
                results = []
                for tu in tool_uses:
                    tool_names.append(tu["name"])
                    yield TurnEvent("tool_call", {"name": tu["name"], "input": tu.get("input", {})})
                    outcome = execute_tool(tu["name"], tu.get("input"), ctx)
                    if outcome.new_state is not None:
                        ctx.chem_state = outcome.new_state
                        yield TurnEvent("state_updated", {"chem_state": outcome.new_state.model_dump()})
                    if outcome.structure_check is not None:
                        checks.append((str(tu.get("input", {}).get("smiles", "")), outcome.structure_check))
                    yield TurnEvent("tool_result", {"name": tu["name"], "ok": outcome.result["ok"]})
                    block = {
                        "type": "tool_result",
                        "tool_use_id": tu["id"],
                        "content": json.dumps(outcome.result, ensure_ascii=False, sort_keys=True),
                    }
                    if not outcome.result["ok"]:
                        block["is_error"] = True
                    results.append(block)
                pending.append(repo.NewMessage("user", results, mode=mode))
                api_messages.append({"role": "user", "content": results})
            else:
                hit_limit = True
        except LLMError as exc:
            log_event(logger, "turn_failed", session_id=str(session_id), error=str(exc))
            yield TurnEvent("error", {"code": "llm_unavailable", "message": LLM_UNAVAILABLE})
            return

        if hit_limit:
            texts.append("(O tutor atingiu o limite de consultas neste turno. Envie uma nova mensagem para continuar.)")
        display = "\n\n".join(t.strip() for t in texts if t.strip())
        if last_assistant is not None:
            last_assistant.display_text = display

        final_state = ctx.chem_state
        for smiles, result in checks:
            check_row = await repo.add_structure_check(db, session_id, smiles, result, commit=False)
            final_state.proposed_structures.append(ProposedStructure(smiles=smiles, check_id=str(check_row.id)))
        await repo.add_messages(db, session_id, pending, commit=False)
        row.chem_state = final_state.model_dump()
        await repo.save(db, row)
        log_event(
            logger,
            "turn_done",
            session_id=str(session_id),
            mode=mode,
            tools=tool_names,
            ms=round((time.perf_counter() - started) * 1000),
            **usage_total,
        )
        yield TurnEvent("done", {"text": display, "chem_state": final_state.model_dump(), "assist_mode": mode})
