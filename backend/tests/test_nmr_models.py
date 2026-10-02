import pytest
from pydantic import ValidationError

from app.nmr_engine.models import Experiment, Multiplicity, Peak, PeakList, renumber


def test_peak_accepts_minimal_fields():
    p = Peak(id="P1", ppm=4.12)
    assert p.integral is None and p.multiplicity is None and p.j_hz is None
    assert p.source == "user"


def test_peak_rejects_out_of_range_ppm():
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=17.0)


def test_peak_rejects_bad_j():
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=1.0, j_hz=[0.0])
    with pytest.raises(ValidationError):
        Peak(id="P1", ppm=1.0, j_hz=[1, 2, 3, 4, 5])


def test_peak_list_rejects_duplicate_ids():
    with pytest.raises(ValidationError):
        PeakList(peaks=[Peak(id="P1", ppm=1.0), Peak(id="P1", ppm=2.0)])


def test_renumber_sorts_descending():
    peaks = renumber([Peak(id="P1", ppm=1.26), Peak(id="P2", ppm=4.12), Peak(id="P3", ppm=2.05)])
    assert [(p.id, p.ppm) for p in peaks] == [("P1", 4.12), ("P2", 2.05), ("P3", 1.26)]


def test_enums():
    assert Multiplicity("br_s") is Multiplicity.br_s
    assert Experiment("1H") is Experiment.H1
    assert {e.value for e in Experiment} == {"1H", "13C", "DEPT", "COSY", "HSQC", "HMBC"}
