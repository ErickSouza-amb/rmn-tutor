import pytest

from app.chem.environments import h_environments
from app.chem.rdkit_tools import SmilesError, inchikey, mol_from_smiles, molecular_formula, validate_smiles


def test_validate_smiles_ok_and_canonical():
    r = validate_smiles("OCC")
    assert r == {"valid": True, "canonical_smiles": "CCO"}


@pytest.mark.parametrize("bad", ["", "C1CC", "C C", "X" * 301])
def test_validate_smiles_rejects(bad):
    r = validate_smiles(bad)
    assert r["valid"] is False and r["error"]


def test_too_many_atoms():
    with pytest.raises(SmilesError):
        mol_from_smiles("C" * 151)


def test_molecular_formula_ethyl_acetate():
    r = molecular_formula("CC(=O)OCC")
    assert r["formula"] == "C4H8O2"
    assert r["mw"] == pytest.approx(88.106, abs=0.01)
    assert r["exact_mass"] == pytest.approx(88.0524, abs=0.001)


def test_inchikey_same_for_equivalent_smiles():
    assert inchikey("CCO") == inchikey("OCC")


def _env_summary(smiles):
    return sorted((e.count, e.h_class) for e in h_environments(mol_from_smiles(smiles)))


def test_environments_ethanol():
    assert _env_summary("CCO") == [(1, "exchangeable"), (2, "alpha_heteroatom"), (3, "alkyl")]


def test_environments_toluene_four_groups():
    assert _env_summary("Cc1ccccc1") == [
        (1, "aromatic"),
        (2, "aromatic"),
        (2, "aromatic"),
        (3, "allylic_benzylic_alpha_carbonyl"),
    ]


def test_environments_classes_misc():
    assert ("aldehyde" in {e.h_class for e in h_environments(mol_from_smiles("CC=O"))})
    assert ("carboxylic_acid" in {e.h_class for e in h_environments(mol_from_smiles("CC(=O)O"))})
    assert ("vinylic" in {e.h_class for e in h_environments(mol_from_smiles("C=CC"))})
