import re

_TOKEN = re.compile(r"([A-Z][a-z]?)(\d*)")
_FULL = re.compile(r"(?:[A-Z][a-z]?\d*)+")
HALOGENS = {"F", "Cl", "Br", "I"}


def parse_formula(formula: str) -> dict[str, int]:
    f = (formula or "").strip().replace(" ", "")
    if not f or not _FULL.fullmatch(f):
        raise ValueError(f"fórmula inválida: {formula!r}")
    counts: dict[str, int] = {}
    for element, n in _TOKEN.findall(f):
        counts[element] = counts.get(element, 0) + (int(n) if n else 1)
    return counts


def hydrogen_count(formula: str) -> int:
    return parse_formula(formula).get("H", 0)


def degrees_of_unsaturation(formula: str) -> float:
    c = parse_formula(formula)
    carbons = c.get("C", 0)
    hydrogens = c.get("H", 0)
    nitrogens = c.get("N", 0) + c.get("P", 0)
    halogens = sum(c.get(x, 0) for x in HALOGENS)
    return carbons - (hydrogens + halogens) / 2 + nitrogens / 2 + 1


def normalize_formula(formula: str) -> str:
    c = parse_formula(formula)
    order = [e for e in ("C", "H") if e in c] + sorted(e for e in c if e not in ("C", "H"))
    return "".join(f"{e}{c[e] if c[e] != 1 else ''}" for e in order)
