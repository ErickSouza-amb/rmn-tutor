import pytest

from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.rdkit_tools import SmilesError
from app.nmr_engine.models import Peak

ETHYL_ACETATE = [
    Peak(id="P1", ppm=4.12, integral=2, multiplicity="q", j_hz=[7.1]),
    Peak(id="P2", ppm=2.05, integral=3, multiplicity="s"),
    Peak(id="P3", ppm=1.26, integral=3, multiplicity="t", j_hz=[7.1]),
]


def _status(result):
    return {c["name"]: c["status"] for c in result["checks"]}


def test_correct_structure_passes_all():
    r = compare_structure_with_data("CC(=O)OCC", ETHYL_ACETATE, "C4H8O2")
    assert _status(r) == {
        "formula": "pass",
        "h_count": "pass",
        "environment_count": "pass",
        "environment_integrals": "pass",
        "shift_ranges": "pass",
    }
    assert r["total_h"] == 8
    assert r["limitations"]


def test_wrong_formula_fails():
    r = compare_structure_with_data("CCC(C)=O", ETHYL_ACETATE, "C4H8O2")
    assert _status(r)["formula"] == "fail"


def test_isomer_with_same_checks_documents_limits():
    # methyl propanoate passes the coarse checks: the tutor must reason about shifts/multiplicity
    r = compare_structure_with_data("CCC(=O)OC", ETHYL_ACETATE, "C4H8O2")
    assert "fail" not in _status(r).values()


def test_missing_formula_and_integrals_are_inconclusive():
    peaks = [Peak(id="P1", ppm=1.0)]
    r = compare_structure_with_data("C", peaks, None)
    s = _status(r)
    assert s["formula"] == "inconclusive"
    assert s["h_count"] == "inconclusive"
    assert s["environment_integrals"] == "inconclusive"


def test_toluene_overlap_is_inconclusive_not_fail():
    peaks = [
        Peak(id="P1", ppm=7.25, integral=2, multiplicity="m"),
        Peak(id="P2", ppm=7.15, integral=3, multiplicity="m"),
        Peak(id="P3", ppm=2.36, integral=3, multiplicity="s"),
    ]
    s = _status(compare_structure_with_data("Cc1ccccc1", peaks, "C7H8"))
    assert s["environment_count"] == "inconclusive"
    assert s["h_count"] == "pass"
    assert s["shift_ranges"] == "pass"


def test_shift_range_fail_is_heuristic():
    peaks = [Peak(id="P1", ppm=1.0, integral=6, multiplicity="s")]
    r = compare_structure_with_data("c1ccccc1", peaks, "C6H6")
    check = next(c for c in r["checks"] if c["name"] == "shift_ranges")
    assert check["status"] == "fail" and check["heuristic"] is True


def test_invalid_smiles_raises():
    with pytest.raises(SmilesError):
        compare_structure_with_data("C1CC", ETHYL_ACETATE, None)


def test_same_structure():
    assert same_structure("CC(=O)OCC", "CCOC(C)=O")
    assert not same_structure("CC(=O)OCC", "CCC(=O)OC")
    assert not same_structure("C1CC", "CCO")
