from rdkit import Chem
from rdkit.Chem import rdMolDescriptors

from app.chem.environments import H_CLASS_LABELS, H_CLASS_RANGES, h_environments
from app.chem.formula import normalize_formula
from app.chem.rdkit_tools import SmilesError, inchikey, mol_from_smiles
from app.nmr_engine.models import Peak

LIMITATIONS = [
    "Ambientes de H contados por simetria topológica: não distingue H diastereotópicos nem considera troca rápida.",
    "Faixas de deslocamento são aproximadas (CDCl3) e heurísticas.",
    "Estas checagens não são um veredito de 'estrutura correta'; isômeros podem passar em todas.",
]
SHIFT_TOLERANCE = 0.2


def _check(name: str, status: str, detail: str, heuristic: bool = False) -> dict:
    return {"name": name, "status": status, "detail": detail, "heuristic": heuristic}


def compare_structure_with_data(smiles: str, peaks: list[Peak], molecular_formula: str | None) -> dict:
    mol = mol_from_smiles(smiles)
    formula = rdMolDescriptors.CalcMolFormula(mol)
    envs = h_environments(mol)
    total_h = sum(e.count for e in envs)
    checks: list[dict] = []

    if not molecular_formula:
        checks.append(_check("formula", "inconclusive", "Fórmula molecular não informada."))
    else:
        try:
            same = normalize_formula(molecular_formula) == normalize_formula(formula)
            checks.append(
                _check(
                    "formula",
                    "pass" if same else "fail",
                    f"Estrutura: {formula}; fórmula informada: {normalize_formula(molecular_formula)}.",
                )
            )
        except ValueError:
            checks.append(_check("formula", "inconclusive", "Não foi possível comparar as fórmulas."))

    integrals = [p.integral for p in peaks]
    scaled: list[float] | None = None
    if not peaks:
        checks.append(_check("h_count", "inconclusive", "Nenhum pico informado."))
    elif any(i is None for i in integrals):
        checks.append(_check("h_count", "inconclusive", "Há picos sem integral."))
    else:
        scale = total_h / sum(integrals)
        scaled = [i * scale for i in integrals]
        ok = all(abs(s - round(s)) <= 0.2 and round(s) >= 1 for s in scaled)
        shown = ", ".join(f"{s:.2f}" for s in scaled)
        checks.append(
            _check(
                "h_count",
                "pass" if ok else "fail",
                f"{total_h} H na estrutura; integrais reescaladas para esse total: [{shown}].",
            )
        )

    n_env, n_sig = len(envs), len(peaks)
    if n_env == n_sig:
        checks.append(
            _check("environment_count", "pass", f"{n_env} ambientes de H e {n_sig} sinais.", heuristic=True)
        )
    else:
        checks.append(
            _check(
                "environment_count",
                "inconclusive",
                f"{n_env} ambientes de H previstos e {n_sig} sinais; a diferença pode vir de sobreposição "
                "de sinais, H diastereotópicos, troca rápida ou de uma estrutura incompatível.",
                heuristic=True,
            )
        )

    if scaled is not None and n_env == n_sig:
        expected = sorted(e.count for e in envs)
        observed = sorted(round(s) for s in scaled)
        checks.append(
            _check(
                "environment_integrals",
                "pass" if expected == observed else "fail",
                f"H por ambiente previsto: {expected}; integrais observadas: {observed}.",
                heuristic=True,
            )
        )
    else:
        checks.append(
            _check(
                "environment_integrals",
                "inconclusive",
                "Comparação exige integrais em todos os picos e mesmo número de ambientes e sinais.",
                heuristic=True,
            )
        )

    if not peaks:
        checks.append(_check("shift_ranges", "inconclusive", "Nenhum pico informado.", heuristic=True))
    else:
        missing = []
        for cls in sorted({e.h_class for e in envs}):
            lo, hi = H_CLASS_RANGES[cls]
            if not any(lo - SHIFT_TOLERANCE <= p.ppm <= hi + SHIFT_TOLERANCE for p in peaks):
                missing.append(f"{H_CLASS_LABELS[cls]} ({lo:g}–{hi:g} ppm)")
        if missing:
            checks.append(
                _check(
                    "shift_ranges",
                    "fail",
                    "Nenhum sinal na faixa esperada para: " + "; ".join(missing) + ".",
                    heuristic=True,
                )
            )
        else:
            checks.append(
                _check(
                    "shift_ranges",
                    "pass",
                    "Todos os tipos de H previstos têm algum sinal na faixa aproximada esperada.",
                    heuristic=True,
                )
            )

    return {
        "canonical_smiles": Chem.MolToSmiles(mol),
        "formula": formula,
        "total_h": total_h,
        "h_environments": [
            {
                "count": e.count,
                "h_class": e.h_class,
                "label": H_CLASS_LABELS[e.h_class],
                "expected_range_ppm": list(H_CLASS_RANGES[e.h_class]),
            }
            for e in envs
        ],
        "checks": checks,
        "limitations": LIMITATIONS,
    }


def same_structure(smiles_a: str, smiles_b: str) -> bool:
    try:
        return inchikey(smiles_a) == inchikey(smiles_b)
    except SmilesError:
        return False
