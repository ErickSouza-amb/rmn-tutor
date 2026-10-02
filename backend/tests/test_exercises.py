import pytest

from app.chem.compare import compare_structure_with_data
from app.chem.formula import normalize_formula
from app.chem.rdkit_tools import molecular_formula
from app.exercises.catalog import exercise_image_path, get_exercise, load_exercises

IDS = ["ex01", "ex02", "ex03", "ex04", "ex05"]


def test_catalog_loads_in_order():
    assert list(load_exercises()) == IDS


def test_public_dict_hides_answers():
    for ex in load_exercises().values():
        d = ex.public_dict()
        assert "answer_smiles" not in d and "answer_name" not in d
        assert ex.answer_name.lower() not in str(d).lower()
        assert d["reviewed"] is False


@pytest.mark.parametrize("exercise_id", IDS)
def test_answer_matches_formula_and_data(exercise_id):
    ex = get_exercise(exercise_id)
    formula = molecular_formula(ex.answer_smiles)["formula"]
    assert normalize_formula(formula) == normalize_formula(ex.metadata["molecular_formula"])
    result = compare_structure_with_data(ex.answer_smiles, ex.peaks, ex.metadata["molecular_formula"])
    assert all(c["status"] != "fail" for c in result["checks"]), result["checks"]


def test_peaks_are_numbered_and_marked_exercise():
    ex = get_exercise("ex02")
    assert [p.id for p in ex.peaks] == ["P1", "P2", "P3"]
    assert all(p.source == "exercise" for p in ex.peaks)


def test_unknown_exercise():
    assert get_exercise("nope") is None


@pytest.mark.parametrize("exercise_id", IDS)
def test_images_exist(exercise_id):
    path = exercise_image_path(exercise_id)
    assert path.exists() and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
