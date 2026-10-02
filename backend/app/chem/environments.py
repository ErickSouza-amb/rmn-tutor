from dataclasses import dataclass

from rdkit import Chem

# Approximate 1H shift windows in CDCl3 (heuristic, didactic).
H_CLASS_RANGES: dict[str, tuple[float, float]] = {
    "alkyl": (0.5, 2.0),
    "allylic_benzylic_alpha_carbonyl": (1.6, 2.9),
    "alkynyl": (1.7, 3.3),
    "alpha_heteroatom": (2.2, 4.8),
    "vinylic": (4.5, 7.0),
    "aromatic": (6.0, 8.8),
    "aldehyde": (9.0, 10.5),
    "carboxylic_acid": (9.5, 13.5),
    "exchangeable": (0.5, 6.0),
    "other": (-2.0, 16.0),
}
H_CLASS_LABELS: dict[str, str] = {
    "alkyl": "H alquílico",
    "allylic_benzylic_alpha_carbonyl": "H alílico/benzílico/α-carbonila",
    "alkynyl": "H acetilênico",
    "alpha_heteroatom": "H em carbono ligado a heteroátomo",
    "vinylic": "H vinílico",
    "aromatic": "H aromático",
    "aldehyde": "H de aldeído",
    "carboxylic_acid": "H de ácido carboxílico",
    "exchangeable": "H trocável (OH/NH/SH)",
    "other": "outro",
}
_HETERO = {"O", "N", "S", "F", "Cl", "Br", "I"}


@dataclass(frozen=True)
class HEnvironment:
    rank: int
    count: int
    h_class: str


def _double_bonded_to_o(atom: Chem.Atom) -> bool:
    return any(
        b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(atom).GetSymbol() == "O"
        for b in atom.GetBonds()
    )


def _is_sp2_carbon(atom: Chem.Atom) -> bool:
    return atom.GetSymbol() == "C" and (
        atom.GetIsAromatic() or atom.GetHybridization() == Chem.HybridizationType.SP2
    )


def classify_h(heavy: Chem.Atom) -> str:
    symbol = heavy.GetSymbol()
    if symbol in ("O", "N", "S"):
        if symbol == "O" and any(
            n.GetSymbol() == "C" and _double_bonded_to_o(n) for n in heavy.GetNeighbors()
        ):
            return "carboxylic_acid"
        return "exchangeable"
    if symbol != "C":
        return "other"
    if heavy.GetIsAromatic():
        return "aromatic"
    if _double_bonded_to_o(heavy):
        return "aldehyde"
    if any(
        b.GetBondType() == Chem.BondType.DOUBLE and b.GetOtherAtom(heavy).GetSymbol() == "C"
        for b in heavy.GetBonds()
    ):
        return "vinylic"
    if any(b.GetBondType() == Chem.BondType.TRIPLE for b in heavy.GetBonds()):
        return "alkynyl"
    neighbors = [n for n in heavy.GetNeighbors() if n.GetAtomicNum() != 1]
    if any(n.GetSymbol() in _HETERO for n in neighbors):
        return "alpha_heteroatom"
    if any(_is_sp2_carbon(n) or n.GetSymbol() == "C" and _double_bonded_to_o(n) for n in neighbors):
        return "allylic_benzylic_alpha_carbonyl"
    return "alkyl"


def h_environments(mol: Chem.Mol) -> list[HEnvironment]:
    molh = Chem.AddHs(mol)
    ranks = list(Chem.CanonicalRankAtoms(molh, breakTies=False))
    groups: dict[int, list[Chem.Atom]] = {}
    for atom in molh.GetAtoms():
        if atom.GetAtomicNum() != 1:
            continue
        heavy = atom.GetNeighbors()[0]
        groups.setdefault(ranks[atom.GetIdx()], []).append(heavy)
    return [
        HEnvironment(rank=rank, count=len(heavies), h_class=classify_h(heavies[0]))
        for rank, heavies in sorted(groups.items())
    ]
