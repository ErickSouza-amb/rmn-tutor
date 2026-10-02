from types import SimpleNamespace

from app.nmr_engine.models import Peak
from app.nmr_tools.state_ops import ChemState
from app.tutor.context import IMAGE_MARKER, build_api_messages, has_image_marker
from app.tutor.prompts import MODE_INSTRUCTIONS, SYSTEM_PROMPT, build_turn_context

PEAKS = [Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]), Peak(id="P2", ppm=2.05, integral=3, multiplicity="s")]


def test_system_prompt_is_stable_and_has_rules():
    assert "P1" in SYSTEM_PROMPT or "ID" in SYSTEM_PROMPT
    for phrase in ["não invente", "hipótese", "tabela"]:
        assert phrase in SYSTEM_PROMPT.lower()
    assert set(MODE_INSTRUCTIONS) == {"tutor", "hint", "verify", "solution"}


def test_turn_context_with_table():
    text = build_turn_context(
        metadata={"frequency_mhz": 400, "solvent": "CDCl3", "molecular_formula": "C4H8O2"},
        peaks=PEAKS,
        chem_state=ChemState(),
        mode="hint",
        has_image=True,
        is_exercise=True,
    )
    assert "| P1 | 4.12 | 2 | q | 7.1 |" in text
    assert "IDH = 1" in text
    assert MODE_INSTRUCTIONS["hint"] in text
    assert '"stage": "observe"' in text


def test_turn_context_without_peaks_says_so():
    text = build_turn_context(metadata={}, peaks=[], chem_state=ChemState(), mode="tutor", has_image=True, is_exercise=False)
    assert "Nenhuma lista de picos" in text
    assert "não informada" in text


def _row(role, content):
    return SimpleNamespace(role=role, content=content)


def test_build_api_messages_injects_image_once():
    rows = [
        _row("user", [IMAGE_MARKER, {"type": "text", "text": "oi"}]),
        _row("system", "ctx"),
        _row("assistant", [{"type": "text", "text": "olá"}]),
    ]
    msgs = build_api_messages(rows, (b"\x89PNGdata", "image/png"))
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"][0]["type"] == "image"
    assert msgs[0]["content"][0]["source"]["media_type"] == "image/png"
    assert msgs[1] == {"role": "system", "content": "ctx"}
    assert msgs[2]["content"] == [{"type": "text", "text": "olá"}]
    assert has_image_marker(rows[0].content) and not has_image_marker(rows[2].content)


def test_build_api_messages_drops_marker_without_image():
    msgs = build_api_messages([_row("user", [IMAGE_MARKER, {"type": "text", "text": "oi"}])], None)
    assert msgs[0]["content"] == [{"type": "text", "text": "oi"}]
