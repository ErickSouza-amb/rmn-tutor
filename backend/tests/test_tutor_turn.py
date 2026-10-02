import io

import pytest
from PIL import Image

from app.config import get_settings
from app.nmr_tools.state_ops import ChemState
from app.store import repo
from app.store.blob import MemoryBlobStore
from app.store.db import create_all, get_sessionmaker
from app.tutor.context import has_image_marker
from app.tutor.llm import FakeLLM, LLMError
from app.tutor.turn import run_turn


@pytest.fixture
async def sm():
    await create_all()
    return get_sessionmaker()


async def _session(sm, exercise_id="ex02", peaks=None):
    async with sm() as db:
        if exercise_id:
            from app.exercises.catalog import get_exercise

            ex = get_exercise(exercise_id)
            peaks = [p.model_dump(mode="json") for p in ex.peaks]
            meta = ex.metadata
        else:
            meta = {}
        row = await repo.create_session(
            db, owner_uid="u", title="t", experiment="1H", metadata=meta, peaks=peaks or [],
            exercise_id=exercise_id, chem_state=ChemState().model_dump(),
        )
        return row.id


async def _run(sm, sid, text, llm, mode=None, blob=None):
    events = []
    async for ev in run_turn(
        session_id=sid, user_text=text, mode=mode, llm=llm, blob=blob or MemoryBlobStore(),
        settings=get_settings(), sessionmaker=sm,
    ):
        events.append(ev)
    return events


async def _rows(sm, sid):
    async with sm() as db:
        return await repo.list_messages(db, sid)


async def test_default_fake_turn_uses_tool_and_persists_append_only(sm):
    sid = await _session(sm)
    llm = FakeLLM()
    events = await _run(sm, sid, "Vejo três sinais.", llm)
    kinds = [e.event for e in events]
    assert kinds[0] == "text_delta" and "tool_call" in kinds and kinds[-1] == "done"
    done = events[-1].data
    assert "P1" in done["text"]
    rows = await _rows(sm, sid)
    assert [r.role for r in rows] == ["user", "system", "assistant", "user", "assistant"]
    assert rows[0].content[0] == {"type": "rmn_image_ref"}  # exercise has an image
    assert rows[0].display_text == "Vejo três sinais."
    assert rows[-1].display_text == done["text"]
    first_call = llm.calls[0]
    assert first_call[0]["content"][0]["type"] == "image"
    assert first_call[-1]["role"] == "system" and "Tabela de picos" in first_call[-1]["content"]


async def test_second_turn_resends_identical_history(sm):
    sid = await _session(sm)
    llm = FakeLLM()
    await _run(sm, sid, "Primeira.", llm)
    await _run(sm, sid, "Segunda.", llm)
    first_turn_final = llm.calls[1]  # request after tool_result in turn 1
    second_turn = llm.calls[2]
    assert second_turn[: len(first_turn_final)] == first_turn_final
    rows = await _rows(sm, sid)
    assert sum(1 for r in rows if has_image_marker(r.content)) == 1


async def test_hint_mode_increments_counter_and_sets_mode(sm):
    sid = await _session(sm)
    await _run(sm, sid, "Me dá uma dica", FakeLLM(), mode="hint")
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.assist_mode == "hint" and row.chem_state["hints_given"] == 1


async def test_state_tool_updates_chem_state(sm):
    sid = await _session(sm)
    script = [
        {
            "content": [
                {"type": "tool_use", "id": "toolu_1", "name": "update_session_state",
                 "input": {"ops": [{"op": "add_hypothesis", "text": "etila", "by": "student", "evidence": ["P1"]}]}}
            ],
            "stop_reason": "tool_use",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
        {"content": [{"type": "text", "text": "Anotei sua hipótese."}], "stop_reason": "end_turn", "usage": {"input_tokens": 12, "output_tokens": 4}},
    ]
    events = await _run(sm, sid, "Acho que é uma etila.", FakeLLM(script))
    assert any(e.event == "state_updated" for e in events)
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.chem_state["hypotheses"][0]["text"] == "etila"


async def test_structure_check_from_tool_is_persisted(sm):
    sid = await _session(sm)
    script = [
        {"content": [{"type": "tool_use", "id": "toolu_1", "name": "compare_structure_with_data", "input": {"smiles": "CCOC(C)=O"}}],
         "stop_reason": "tool_use", "usage": {}},
        {"content": [{"type": "text", "text": "Vamos analisar as checagens."}], "stop_reason": "end_turn", "usage": {}},
    ]
    await _run(sm, sid, "É acetato de etila?", FakeLLM(script), mode="verify")
    async with sm() as db:
        row = await repo.get_session(db, sid)
    assert row.chem_state["proposed_structures"][0]["smiles"] == "CCOC(C)=O"


async def test_llm_failure_persists_only_user_message(sm):
    sid = await _session(sm)

    class Boom(FakeLLM):
        async def stream(self, *, system, tools, messages):
            raise LLMError("indisponível")
            yield  # pragma: no cover

    events = await _run(sm, sid, "Olá", Boom())
    assert events[-1].event == "error" and events[-1].data["code"] == "llm_unavailable"
    rows = await _rows(sm, sid)
    assert [r.role for r in rows] == ["user"]
    # next turn still produces a valid sequence (consecutive user messages are allowed)
    llm = FakeLLM()
    await _run(sm, sid, "Tentando de novo", llm)
    roles = [m["role"] for m in llm.calls[0]]
    assert roles == ["user", "user", "system"]


async def test_failure_mid_tool_loop_discards_partial_turn(sm):
    sid = await _session(sm)

    class HalfBoom(FakeLLM):
        async def stream(self, *, system, tools, messages):
            if any(isinstance(m["content"], list) and any(b.get("type") == "tool_result" for b in m["content"] if isinstance(b, dict)) for m in messages):
                raise LLMError("caiu no meio")
            async for ev in super().stream(system=system, tools=tools, messages=messages):
                yield ev

    events = await _run(sm, sid, "Olá", HalfBoom())
    assert events[-1].event == "error"
    assert [r.role for r in await _rows(sm, sid)] == ["user"]


async def test_image_uploaded_later_goes_to_next_user_message(sm):
    sid = await _session(sm, exercise_id=None, peaks=[{"id": "P1", "ppm": 1.0}])
    await _run(sm, sid, "Sem imagem ainda", FakeLLM())
    blob = MemoryBlobStore()
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, "PNG")
    path = await blob.put("sessions/x/spectrum.png", buf.getvalue(), "image/png")
    async with sm() as db:
        row = await repo.get_session(db, sid)
        row.image_blob, row.image_media_type = path, "image/png"
        await repo.save(db, row)
    before = await _rows(sm, sid)
    llm = FakeLLM()
    await _run(sm, sid, "Agora com imagem", llm, blob=blob)
    after = await _rows(sm, sid)
    assert [r.content for r in after[: len(before)]] == [r.content for r in before]  # history untouched
    new_user = after[len(before)]
    assert new_user.role == "user" and new_user.content[0] == {"type": "rmn_image_ref"}
    image_blocks = [b for m in llm.calls[0] if isinstance(m["content"], list) for b in m["content"] if b.get("type") == "image"]
    assert len(image_blocks) == 1


async def test_image_only_session_context_says_no_table(sm):
    sid = await _session(sm, exercise_id=None, peaks=[])
    llm = FakeLLM()
    await _run(sm, sid, "Oi", llm)
    assert "Nenhuma lista de picos" in llm.calls[0][-1]["content"]


async def test_answer_never_in_context(sm):
    sid = await _session(sm, "ex02")
    llm = FakeLLM()
    await _run(sm, sid, "Oi", llm, mode="solution")
    blob = str(llm.calls)
    assert "CCOC(C)=O" not in blob and "acetato de etila" not in blob


async def test_tool_iteration_limit(sm, monkeypatch):
    monkeypatch.setenv("TUTOR_MAX_TOOL_ITERATIONS", "2")
    get_settings.cache_clear()
    sid = await _session(sm)
    loop_msg = {"content": [{"type": "tool_use", "id": "toolu_x", "name": "get_peak_list", "input": {}}], "stop_reason": "tool_use", "usage": {}}
    events = await _run(sm, sid, "Oi", FakeLLM([dict(loop_msg), dict(loop_msg), dict(loop_msg)]))
    assert events[-1].event == "done"
    assert "limite" in events[-1].data["text"].lower()
