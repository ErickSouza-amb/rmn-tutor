import logging
from dataclasses import dataclass
from functools import lru_cache
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.chem.compare import compare_structure_with_data, same_structure
from app.chem.formula import degrees_of_unsaturation, hydrogen_count
from app.chem.rdkit_tools import SmilesError, molecular_formula, validate_smiles
from app.nmr_engine.models import Peak
from app.nmr_engine.queries import delta_between, find_peak, integrate_region, peaks_in_region
from app.nmr_tools.envelope import error, not_available, ok
from app.nmr_tools.state_ops import ChemState, StateOpError, apply_ops

logger = logging.getLogger("rmn.tools")

NO_PEAKS_REASON = (
    "Nenhuma lista de picos foi fornecida nesta sessão. Não estime valores numéricos a partir da imagem; "
    "peça ao aluno que digite a lista de picos se precisar de números."
)
INTEGRAL_LIMITATION = "Integrais vêm da tabela informada (usuário/exercício); não são medidas da imagem."
J_LIMITATION = "No MVP, J não é estimado a partir da imagem; só valores informados na tabela."


@dataclass
class ToolContext:
    peaks: list[Peak]
    metadata: dict
    chem_state: ChemState
    assist_mode: str
    has_image: bool
    experiment: str = "1H"
    answer_smiles: str | None = None


@dataclass
class ToolOutcome:
    result: dict
    new_state: ChemState | None = None
    structure_check: dict | None = None


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NoInput(_Strict):
    pass


class RegionInput(_Strict):
    ppm_start: float = Field(ge=-5, le=20, description="Limite da região em ppm.")
    ppm_end: float = Field(ge=-5, le=20, description="Outro limite da região em ppm (qualquer ordem).")


class PeakQueryInput(_Strict):
    peak_id: str | None = Field(default=None, description="ID do pico, ex. 'P2'.")
    ppm: float | None = Field(default=None, description="Deslocamento aproximado em ppm.")
    tolerance_ppm: float = Field(default=0.05, gt=0, le=1, description="Tolerância ao buscar por ppm.")

    @model_validator(mode="after")
    def _exactly_one(self) -> "PeakQueryInput":
        if (self.peak_id is None) == (self.ppm is None):
            raise ValueError("informe exatamente um entre peak_id e ppm")
        return self


class TwoPeaksInput(_Strict):
    peak_a: str = Field(description="ID do primeiro pico.")
    peak_b: str = Field(description="ID do segundo pico.")


class PeakIdInput(_Strict):
    peak_id: str = Field(description="ID do pico, ex. 'P1'.")


class SmilesInput(_Strict):
    smiles: str = Field(min_length=1, max_length=300, description="Estrutura em SMILES.")


class DbeInput(_Strict):
    formula: str | None = Field(default=None, description="Fórmula molecular, ex. 'C4H8O2'.")
    smiles: str | None = Field(default=None, description="Alternativamente, uma estrutura em SMILES.")


class StateInput(_Strict):
    ops: list[dict] = Field(
        min_length=1,
        max_length=20,
        description=(
            "Lista de operações aplicadas em ordem (todas ou nenhuma). Formatos: "
            "{op:'set_stage', stage:'observe|evidence|hypothesis|confront|assemble|check'}; "
            "{op:'add_signal_note', peak_id:'P1', interpretation:'...', status:'proposed|supported|rejected'}; "
            "{op:'add_hypothesis', text:'...', by:'student|tutor', evidence:['P1']}; "
            "{op:'set_hypothesis_status', hypothesis_id:'H1', status:'open|supported|rejected'}; "
            "{op:'add_unresolved', text:'...'}; {op:'resolve_unresolved', text:'...'}."
        ),
    )


def _peak_dict(p: Peak) -> dict:
    return {
        "id": p.id,
        "ppm": p.ppm,
        "integral": p.integral,
        "multiplicity": str(p.multiplicity) if p.multiplicity else None,
        "j_hz": p.j_hz,
        "note": p.note,
    }


def _formula_h(ctx: ToolContext) -> int | None:
    formula = (ctx.metadata or {}).get("molecular_formula")
    try:
        return hydrogen_count(formula) if formula else None
    except ValueError:
        return None


def _t_metadata(ctx: ToolContext, _: NoInput) -> ToolOutcome:
    m = ctx.metadata or {}
    formula = m.get("molecular_formula")
    try:
        dbe = degrees_of_unsaturation(formula) if formula else None
    except ValueError:
        dbe = None
    data = {
        "experiment": ctx.experiment,
        "frequency_mhz": m.get("frequency_mhz"),
        "solvent": m.get("solvent"),
        "molecular_formula": formula,
        "degrees_of_unsaturation": dbe,
        "n_peaks": len(ctx.peaks),
        "all_peaks_have_integrals": bool(ctx.peaks) and all(p.integral is not None for p in ctx.peaks),
        "image_available": ctx.has_image,
    }
    missing = [k for k in ("frequency_mhz", "solvent", "molecular_formula") if not m.get(k)]
    warnings = [f"Não informado: {', '.join(missing)}."] if missing else []
    return ToolOutcome(ok("get_spectrum_metadata", data, warnings))


def _t_peak_list(ctx: ToolContext, _: NoInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peak_list", NO_PEAKS_REASON))
    return ToolOutcome(ok("get_peak_list", {"peaks": [_peak_dict(p) for p in ctx.peaks]}))


def _t_region(ctx: ToolContext, inp: RegionInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peaks_in_region", NO_PEAKS_REASON))
    found = peaks_in_region(ctx.peaks, inp.ppm_start, inp.ppm_end)
    warnings = [] if found else ["Nenhum pico da tabela nesta região."]
    lo, hi = sorted((inp.ppm_start, inp.ppm_end))
    data = {"region_ppm": [lo, hi], "peaks": [_peak_dict(p) for p in found]}
    return ToolOutcome(ok("get_peaks_in_region", data, warnings))


def _t_peak(ctx: ToolContext, inp: PeakQueryInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_peak", NO_PEAKS_REASON))
    p = find_peak(ctx.peaks, peak_id=inp.peak_id, ppm=inp.ppm, tolerance_ppm=inp.tolerance_ppm)
    if p is None:
        return ToolOutcome(not_available("get_peak", "Nenhum pico corresponde à consulta."))
    return ToolOutcome(ok("get_peak", {"peak": _peak_dict(p)}))


def _t_integration(ctx: ToolContext, inp: RegionInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("get_integration", NO_PEAKS_REASON))
    r = integrate_region(ctx.peaks, inp.ppm_start, inp.ppm_end, _formula_h(ctx))
    if r["missing_integrals"]:
        return ToolOutcome(
            not_available(
                "get_integration",
                f"Picos sem integral na região: {', '.join(r['missing_integrals'])}.",
                [INTEGRAL_LIMITATION],
            )
        )
    warnings = [] if r["peak_ids"] else ["Nenhum pico da tabela nesta região."]
    if r["peak_ids"] and r["normalized_h"] is None:
        warnings.append("Sem normalização: falta fórmula molecular ou integral em algum pico do espectro.")
    return ToolOutcome(ok("get_integration", r, warnings, [INTEGRAL_LIMITATION]))


def _t_delta(ctx: ToolContext, inp: TwoPeaksInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("calculate_delta", NO_PEAKS_REASON))
    a = find_peak(ctx.peaks, peak_id=inp.peak_a)
    b = find_peak(ctx.peaks, peak_id=inp.peak_b)
    missing = [pid for pid, p in ((inp.peak_a, a), (inp.peak_b, b)) if p is None]
    if missing:
        return ToolOutcome(error("calculate_delta", "unknown_peak", f"Pico(s) desconhecido(s): {', '.join(missing)}."))
    freq = (ctx.metadata or {}).get("frequency_mhz")
    data = {"peak_a": inp.peak_a, "peak_b": inp.peak_b, **delta_between(a, b, freq)}
    warnings = [] if freq else ["Frequência não informada: Δ em Hz indisponível."]
    return ToolOutcome(ok("calculate_delta", data, warnings))


def _t_j(ctx: ToolContext, inp: PeakIdInput) -> ToolOutcome:
    if not ctx.peaks:
        return ToolOutcome(not_available("calculate_j", NO_PEAKS_REASON, [J_LIMITATION]))
    p = find_peak(ctx.peaks, peak_id=inp.peak_id)
    if p is None:
        return ToolOutcome(error("calculate_j", "unknown_peak", f"Pico desconhecido: {inp.peak_id}."))
    if not p.j_hz:
        return ToolOutcome(not_available("calculate_j", f"J não informado para {p.id}.", [J_LIMITATION]))
    data = {"peak_id": p.id, "multiplicity": str(p.multiplicity) if p.multiplicity else None, "j_hz": p.j_hz}
    return ToolOutcome(ok("calculate_j", data, limitations=[J_LIMITATION]))


def _t_validate(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    return ToolOutcome(ok("validate_smiles", validate_smiles(inp.smiles)))


def _t_formula(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    try:
        return ToolOutcome(ok("molecular_formula", molecular_formula(inp.smiles)))
    except SmilesError as exc:
        return ToolOutcome(error("molecular_formula", "invalid_smiles", str(exc)))


def _t_dbe(ctx: ToolContext, inp: DbeInput) -> ToolOutcome:
    try:
        if inp.formula:
            formula = inp.formula
        elif inp.smiles:
            formula = molecular_formula(inp.smiles)["formula"]
        else:
            formula = (ctx.metadata or {}).get("molecular_formula")
        if not formula:
            return ToolOutcome(not_available("degrees_of_unsaturation", "Nenhuma fórmula disponível."))
        value = degrees_of_unsaturation(formula)
    except SmilesError as exc:
        return ToolOutcome(error("degrees_of_unsaturation", "invalid_smiles", str(exc)))
    except ValueError as exc:
        return ToolOutcome(error("degrees_of_unsaturation", "invalid_formula", str(exc)))
    return ToolOutcome(ok("degrees_of_unsaturation", {"formula": formula, "degrees_of_unsaturation": value}))


def _t_compare(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    try:
        result = compare_structure_with_data(inp.smiles, ctx.peaks, (ctx.metadata or {}).get("molecular_formula"))
    except SmilesError as exc:
        return ToolOutcome(error("compare_structure_with_data", "invalid_smiles", str(exc)))
    return ToolOutcome(
        ok("compare_structure_with_data", result, limitations=result["limitations"]),
        structure_check=result,
    )


def _t_state(ctx: ToolContext, inp: StateInput) -> ToolOutcome:
    try:
        new = apply_ops(ctx.chem_state, inp.ops, {p.id for p in ctx.peaks})
    except StateOpError as exc:
        return ToolOutcome(error("update_session_state", "invalid_state_op", str(exc)))
    return ToolOutcome(ok("update_session_state", {"chem_state": new.model_dump()}), new_state=new)


def _t_answer(ctx: ToolContext, inp: SmilesInput) -> ToolOutcome:
    name = "check_against_answer"
    if not ctx.answer_smiles:
        return ToolOutcome(error(name, "not_available_for_session", "Disponível apenas em sessões de exercício."))
    if ctx.assist_mode not in ("verify", "solution"):
        return ToolOutcome(error(name, "mode_not_allowed", "Disponível apenas nos modos Verificação ou Solução."))
    check = validate_smiles(inp.smiles)
    if not check["valid"]:
        return ToolOutcome(error(name, "invalid_smiles", check["error"]))
    return ToolOutcome(
        ok(
            name,
            {"same_structure": same_structure(inp.smiles, ctx.answer_smiles)},
            limitations=["Compara apenas identidade estrutural (InChIKey); não revela a resposta."],
        )
    )


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[[ToolContext, BaseModel], ToolOutcome]


TOOLS: list[ToolSpec] = [
    ToolSpec("get_spectrum_metadata", "Metadados da sessão: experimento, frequência, solvente, fórmula molecular, IDH, número de picos e se há imagem.", NoInput, _t_metadata),
    ToolSpec("get_peak_list", "Lista oficial de picos (δ em ppm, integral, multiplicidade, J em Hz). Use estes valores, nunca estimativas da imagem.", NoInput, _t_peak_list),
    ToolSpec("get_peaks_in_region", "Picos da tabela dentro de uma região de deslocamento químico.", RegionInput, _t_region),
    ToolSpec("get_peak", "Um pico pelo ID ou pelo deslocamento aproximado.", PeakQueryInput, _t_peak),
    ToolSpec("get_integration", "Soma das integrais informadas numa região e, se houver fórmula, o número de H correspondente.", RegionInput, _t_integration),
    ToolSpec("calculate_delta", "Diferença de deslocamento entre dois picos, em ppm e Hz.", TwoPeaksInput, _t_delta),
    ToolSpec("calculate_j", "Constantes de acoplamento J informadas para um pico (não estima J da imagem).", PeakIdInput, _t_j),
    ToolSpec("validate_smiles", "Valida um SMILES e devolve a forma canônica.", SmilesInput, _t_validate),
    ToolSpec("molecular_formula", "Fórmula molecular, massa molar e massa exata de um SMILES.", SmilesInput, _t_formula),
    ToolSpec("degrees_of_unsaturation", "Índice de deficiência de hidrogênio (IDH) de uma fórmula, de um SMILES ou da fórmula da sessão.", DbeInput, _t_dbe),
    ToolSpec("compare_structure_with_data", "Checagens determinísticas de uma estrutura proposta contra os dados: fórmula, total de H, ambientes de H, integrais e faixas de δ (heurísticas). Não é veredito.", SmilesInput, _t_compare),
    ToolSpec("update_session_state", "Registra o estado do raciocínio: etapa, notas por sinal, hipóteses e pendências.", StateInput, _t_state),
    ToolSpec("check_against_answer", "Somente em exercícios, nos modos Verificação ou Solução: diz se o SMILES é a mesma estrutura da resposta, sem revelá-la.", SmilesInput, _t_answer),
]
TOOL_NAMES = [t.name for t in TOOLS]
_BY_NAME = {t.name: t for t in TOOLS}


def _strip_titles(obj):
    if isinstance(obj, dict):
        return {k: _strip_titles(v) for k, v in obj.items() if k != "title"}
    if isinstance(obj, list):
        return [_strip_titles(v) for v in obj]
    return obj


@lru_cache
def _definitions() -> tuple[dict, ...]:
    return tuple(
        {"name": t.name, "description": t.description, "input_schema": _strip_titles(t.input_model.model_json_schema())}
        for t in TOOLS
    )


def tool_definitions() -> list[dict]:
    return [dict(d) for d in _definitions()]


def execute_tool(name: str, raw_input, ctx: ToolContext) -> ToolOutcome:
    spec = _BY_NAME.get(name)
    if spec is None:
        return ToolOutcome(error(name, "unknown_tool", f"Ferramenta desconhecida: {name}."))
    try:
        inp = spec.input_model.model_validate(raw_input if isinstance(raw_input, dict) else None)
    except ValidationError as exc:
        first = exc.errors()[0]
        return ToolOutcome(error(name, "invalid_input", f"{first['msg']} em {list(first['loc'])}"))
    try:
        return spec.handler(ctx, inp)
    except Exception:
        logger.exception("tool_failed", extra={"fields": {"tool": name}})
        return ToolOutcome(error(name, "internal_error", "Falha interna ao executar a ferramenta."))
