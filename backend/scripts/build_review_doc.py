"""Generate docs/exercises/REVIEW.md (checklist for the human reviewer).

Run from backend/:  python scripts/build_review_doc.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.chem.rdkit_tools import molecular_formula  # noqa: E402
from app.exercises.catalog import load_exercises  # noqa: E402

OUT = ROOT.parent / "docs" / "exercises" / "REVIEW.md"
SKILL_FILES = [
    "SKILL.md",
    "proton-nmr.md",
    "carbon-nmr.md",
    "coupling.md",
    "2d-nmr.md",
    "structure-elucidation.md",
]


def main() -> None:
    lines = [
        "# Revisão dos dados químicos — RMN Tutor",
        "",
        "> **Contém as respostas dos exercícios.** Documento para o revisor (professor/autor).",
        "> Gerado por `backend/scripts/build_review_doc.py`; edite os YAML em",
        "> `backend/app/exercises/data/` e rode o script de novo.",
        "",
        "Ao concluir a revisão de um exercício: corrija o YAML se necessário, preencha",
        "`reviewed: true`, `reviewed_by: \"Nome\"`, `sources: [...]`, rode",
        "`python scripts/render_exercise_images.py` e este script, e faça commit.",
        "",
    ]
    for ex in load_exercises().values():
        info = molecular_formula(ex.answer_smiles)
        m = ex.metadata
        lines += [
            f"## {ex.id} — {ex.title}",
            "",
            f"- Resposta: **{ex.answer_name}** — `{ex.answer_smiles}` ({info['formula']}, MW {info['mw']})",
            f"- Condições: {m.get('frequency_mhz')} MHz, {m.get('solvent')}; fórmula informada {m.get('molecular_formula')}",
            f"- Status: reviewed = `{str(ex.reviewed).lower()}`, revisor = {ex.reviewed_by or '—'}",
            "",
            "| ID | δ (ppm) | Integral | Mult. | J (Hz) | Nota |",
            "|---|---|---|---|---|---|",
        ]
        for p in ex.peaks:
            j = ", ".join(f"{v:g}" for v in p.j_hz) if p.j_hz else "—"
            lines.append(
                f"| {p.id} | {p.ppm:g} | {p.integral if p.integral is not None else '—'} | "
                f"{p.multiplicity or '—'} | {j} | {p.note or ''} |"
            )
        lines += [
            "",
            f"![{ex.id}](../../backend/app/exercises/images/{ex.id}.png)",
            "",
            "- [ ] Deslocamentos químicos conferidos",
            "- [ ] Integrais conferidas",
            "- [ ] Multiplicidades conferidas",
            "- [ ] Constantes J conferidas",
            "- [ ] Solvente/frequência coerentes",
            "- [ ] Fonte bibliográfica registrada em `sources`",
            "",
        ]
    lines += [
        "## Skill `nmr-spectroscopy` (conteúdo químico)",
        "",
        "Arquivos em `.claude/skills/nmr-spectroscopy/`. Conferir definições, faixas e fontes citadas.",
        "",
    ]
    lines += [f"- [ ] `{name}`" for name in SKILL_FILES]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
