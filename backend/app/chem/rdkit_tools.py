from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

MAX_SMILES_LEN = 300
MAX_HEAVY_ATOMS = 150


class SmilesError(ValueError):
    pass


def mol_from_smiles(smiles: str) -> Chem.Mol:
    s = (smiles or "").strip()
    if not s:
        raise SmilesError("SMILES vazio.")
    if len(s) > MAX_SMILES_LEN:
        raise SmilesError(f"SMILES longo demais (máx. {MAX_SMILES_LEN} caracteres).")
    if any(ch.isspace() for ch in s):
        raise SmilesError("SMILES não pode conter espaços.")
    mol = Chem.MolFromSmiles(s)
    if mol is None:
        raise SmilesError("SMILES inválido: não foi possível interpretar a estrutura.")
    if mol.GetNumAtoms() > MAX_HEAVY_ATOMS:
        raise SmilesError(f"Molécula grande demais para o tutor (máx. {MAX_HEAVY_ATOMS} átomos pesados).")
    return mol


def validate_smiles(smiles: str) -> dict:
    try:
        mol = mol_from_smiles(smiles)
    except SmilesError as exc:
        return {"valid": False, "error": str(exc)}
    return {"valid": True, "canonical_smiles": Chem.MolToSmiles(mol)}


def molecular_formula(smiles: str) -> dict:
    mol = mol_from_smiles(smiles)
    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "mw": round(Descriptors.MolWt(mol), 3),
        "exact_mass": round(Descriptors.ExactMolWt(mol), 4),
    }


def inchikey(smiles: str) -> str:
    return Chem.MolToInchiKey(mol_from_smiles(smiles))
