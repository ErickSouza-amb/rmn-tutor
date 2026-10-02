import pytest

from app.nmr_tools.state_ops import ChemState, StateOpError, apply_ops

PEAKS = {"P1", "P2", "P3"}


def test_default_state():
    s = ChemState()
    assert s.stage == "observe" and s.hints_given == 0 and s.schema_version == 1


def test_apply_ops_sequence():
    s = apply_ops(
        ChemState(),
        [
            {"op": "set_stage", "stage": "hypothesis"},
            {"op": "add_signal_note", "peak_id": "P1", "interpretation": "CH2 ao lado de CH3"},
            {"op": "add_hypothesis", "text": "grupo etila ligado a O", "by": "student", "evidence": ["P1", "P3"]},
            {"op": "add_unresolved", "text": "singleto em 2,05"},
        ],
        PEAKS,
    )
    assert s.stage == "hypothesis"
    assert s.signal_notes[0].peak_id == "P1"
    assert s.hypotheses[0].id == "H1" and s.hypotheses[0].status == "open"
    assert s.unresolved == ["singleto em 2,05"]
    s2 = apply_ops(
        s,
        [
            {"op": "add_signal_note", "peak_id": "P1", "interpretation": "OCH2", "status": "supported"},
            {"op": "set_hypothesis_status", "hypothesis_id": "H1", "status": "supported"},
            {"op": "resolve_unresolved", "text": "singleto em 2,05"},
        ],
        PEAKS,
    )
    assert len(s2.signal_notes) == 1 and s2.signal_notes[0].interpretation == "OCH2"
    assert s2.hypotheses[0].status == "supported"
    assert s2.unresolved == []
    assert s.hypotheses[0].status == "open"  # original untouched


def test_all_or_nothing():
    s = ChemState()
    with pytest.raises(StateOpError, match="P9"):
        apply_ops(s, [{"op": "set_stage", "stage": "check"}, {"op": "add_signal_note", "peak_id": "P9", "interpretation": "x"}], PEAKS)
    assert s.stage == "observe"


@pytest.mark.parametrize(
    "ops,match",
    [
        ([], "não vazia"),
        ([{"op": "explode"}], "operação inválida"),
        ([{"op": "set_hypothesis_status", "hypothesis_id": "H7", "status": "rejected"}], "H7"),
        ([{"op": "resolve_unresolved", "text": "nada"}], "(?i)pendência"),
        ([{"op": "set_stage", "stage": "observe"}] * 21, "20"),
    ],
)
def test_invalid_ops(ops, match):
    with pytest.raises(StateOpError, match=match):
        apply_ops(ChemState(), ops, PEAKS)
