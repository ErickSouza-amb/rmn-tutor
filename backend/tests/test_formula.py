import pytest

from app.chem.formula import degrees_of_unsaturation, hydrogen_count, normalize_formula, parse_formula


def test_parse_formula():
    assert parse_formula("C4H8O2") == {"C": 4, "H": 8, "O": 2}
    assert parse_formula("CH3Cl") == {"C": 1, "H": 3, "Cl": 1}


@pytest.mark.parametrize("bad", ["", "c4h8", "C4H8O2)", "4CH"])
def test_parse_formula_rejects(bad):
    with pytest.raises(ValueError):
        parse_formula(bad)


def test_hydrogen_count():
    assert hydrogen_count("C7H8") == 8
    assert hydrogen_count("CCl4") == 0


@pytest.mark.parametrize(
    "formula,dbe",
    [("C2H6O", 0), ("C4H8O2", 1), ("C7H8", 4), ("C9H10O2", 5), ("C5H5N", 4), ("C2H5Br", 0)],
)
def test_degrees_of_unsaturation(formula, dbe):
    assert degrees_of_unsaturation(formula) == dbe


def test_normalize_formula_hill_order():
    assert normalize_formula("H8C4O2") == "C4H8O2"
    assert normalize_formula("OC2H6") == "C2H6O"
    assert normalize_formula("ClCH3") == "CH3Cl"
