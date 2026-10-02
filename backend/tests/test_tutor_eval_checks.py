import importlib.util
from pathlib import Path

from app.exercises.catalog import get_exercise

_spec = importlib.util.spec_from_file_location("tutor_eval", Path(__file__).resolve().parents[1] / "scripts" / "tutor_eval.py")
te = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(te)

EX = get_exercise("ex02")


def test_no_answer():
    assert te.check_no_answer("O que você observa em P1 (4,12 ppm)?", EX) is None
    assert te.check_no_answer("A resposta é acetato de etila.", EX) == "revelou a resposta"
    assert te.check_no_answer("Seria CCOC(C)=O.", EX) == "revelou a resposta"


def test_cites_peak():
    assert te.check_cites_peak(["Veja o sinal P2."]) is None
    assert te.check_cites_peak(["Veja o singleto."]) is not None


def test_no_invented_j():
    assert te.check_no_invented_j(["J = 7,1 Hz em P1"], EX) is None
    assert "6.5" in te.check_no_invented_j(["J de 6,5 Hz"], EX)
    assert te.check_no_invented_j(["Δ = 1144 Hz"], EX) is None  # > 30 Hz is not a J


def test_parse_sse():
    events = te.parse_sse('event: text_delta\ndata: {"text": "a"}\n\nevent: done\ndata: {"text": "a"}\n\n')
    assert [n for n, _ in events] == ["text_delta", "done"]
