from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

Stage = Literal["observe", "evidence", "hypothesis", "confront", "assemble", "check"]
NoteStatus = Literal["proposed", "supported", "rejected"]
HypStatus = Literal["open", "supported", "rejected"]
MAX_OPS = 20
MAX_NOTES = 100
MAX_HYPOTHESES = 50
MAX_UNRESOLVED = 50


class SignalNote(BaseModel):
    peak_id: str
    interpretation: str = Field(max_length=300)
    status: NoteStatus = "proposed"


class Hypothesis(BaseModel):
    id: str
    text: str = Field(max_length=300)
    by: Literal["student", "tutor"]
    status: HypStatus = "open"
    evidence: list[str] = Field(default_factory=list)


class ProposedStructure(BaseModel):
    smiles: str
    check_id: str | None = None


class ChemState(BaseModel):
    schema_version: Literal[1] = 1
    stage: Stage = "observe"
    signal_notes: list[SignalNote] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    hints_given: int = 0
    proposed_structures: list[ProposedStructure] = Field(default_factory=list)


class SetStage(BaseModel):
    op: Literal["set_stage"]
    stage: Stage


class AddSignalNote(BaseModel):
    op: Literal["add_signal_note"]
    peak_id: str
    interpretation: str = Field(min_length=1, max_length=300)
    status: NoteStatus = "proposed"


class AddHypothesis(BaseModel):
    op: Literal["add_hypothesis"]
    text: str = Field(min_length=1, max_length=300)
    by: Literal["student", "tutor"]
    evidence: list[str] = Field(default_factory=list, max_length=20)


class SetHypothesisStatus(BaseModel):
    op: Literal["set_hypothesis_status"]
    hypothesis_id: str
    status: HypStatus


class AddUnresolved(BaseModel):
    op: Literal["add_unresolved"]
    text: str = Field(min_length=1, max_length=200)


class ResolveUnresolved(BaseModel):
    op: Literal["resolve_unresolved"]
    text: str


StateOp = Annotated[
    Union[SetStage, AddSignalNote, AddHypothesis, SetHypothesisStatus, AddUnresolved, ResolveUnresolved],
    Field(discriminator="op"),
]
_OPS = TypeAdapter(list[StateOp])


class StateOpError(ValueError):
    pass


def apply_ops(state: ChemState, raw_ops: list, valid_peak_ids: set[str]) -> ChemState:
    if not isinstance(raw_ops, list) or not raw_ops:
        raise StateOpError("Forneça uma lista 'ops' não vazia.")
    if len(raw_ops) > MAX_OPS:
        raise StateOpError(f"No máximo {MAX_OPS} operações por chamada.")
    try:
        ops = _OPS.validate_python(raw_ops)
    except ValidationError as exc:
        first = exc.errors()[0]
        raise StateOpError(f"operação inválida: {first['msg']} em {list(first['loc'])}") from exc

    new = state.model_copy(deep=True)
    for op in ops:
        if isinstance(op, SetStage):
            new.stage = op.stage
        elif isinstance(op, AddSignalNote):
            if op.peak_id not in valid_peak_ids:
                raise StateOpError(f"Pico desconhecido: {op.peak_id}.")
            new.signal_notes = [n for n in new.signal_notes if n.peak_id != op.peak_id]
            new.signal_notes.append(SignalNote(peak_id=op.peak_id, interpretation=op.interpretation, status=op.status))
        elif isinstance(op, AddHypothesis):
            unknown = [e for e in op.evidence if e not in valid_peak_ids]
            if unknown:
                raise StateOpError(f"Evidência cita picos desconhecidos: {', '.join(unknown)}.")
            if len(new.hypotheses) >= MAX_HYPOTHESES:
                raise StateOpError("Limite de hipóteses atingido.")
            new.hypotheses.append(
                Hypothesis(id=f"H{len(new.hypotheses) + 1}", text=op.text, by=op.by, evidence=op.evidence)
            )
        elif isinstance(op, SetHypothesisStatus):
            hyp = next((h for h in new.hypotheses if h.id == op.hypothesis_id), None)
            if hyp is None:
                raise StateOpError(f"Hipótese desconhecida: {op.hypothesis_id}.")
            hyp.status = op.status
        elif isinstance(op, AddUnresolved):
            if op.text not in new.unresolved:
                if len(new.unresolved) >= MAX_UNRESOLVED:
                    raise StateOpError("Limite de pendências atingido.")
                new.unresolved.append(op.text)
        elif isinstance(op, ResolveUnresolved):
            if op.text not in new.unresolved:
                raise StateOpError(f"Pendência não encontrada: {op.text}.")
            new.unresolved.remove(op.text)
    if len(new.signal_notes) > MAX_NOTES:
        raise StateOpError("Limite de notas de sinal atingido.")
    return new
