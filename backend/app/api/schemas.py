import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.chem.formula import parse_formula
from app.exercises.catalog import get_exercise
from app.nmr_engine.models import MAX_PEAKS, Peak
from app.store.models import MessageRow, SessionRow
from app.store.repo import as_aware

AssistMode = Literal["tutor", "hint", "verify", "solution"]
ExperimentIn = Literal["1H"]  # Experiment enum declares 13C/DEPT/COSY/HSQC/HMBC for later; MVP accepts only 1H


class SessionMetadata(BaseModel):
    frequency_mhz: float | None = Field(default=None, gt=0, le=2000)
    solvent: str | None = Field(default=None, max_length=40)
    molecular_formula: str | None = Field(default=None, max_length=60)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("molecular_formula")
    @classmethod
    def _formula(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        parse_formula(v)
        return v.strip()


class CreateSessionIn(BaseModel):
    experiment: ExperimentIn = "1H"
    metadata: SessionMetadata = Field(default_factory=SessionMetadata)
    peaks: list[Peak] = Field(default_factory=list, max_length=MAX_PEAKS)
    exercise_id: str | None = Field(default=None, max_length=64)
    title: str | None = Field(default=None, max_length=200)


class UpdateSessionIn(BaseModel):
    metadata: SessionMetadata | None = None
    peaks: list[Peak] | None = Field(default=None, max_length=MAX_PEAKS)
    assist_mode: AssistMode | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)


class MessageOut(BaseModel):
    seq: int
    role: Literal["user", "assistant"]
    text: str
    mode: str | None
    created_at: datetime


class ExerciseInfo(BaseModel):
    id: str
    title: str
    reviewed: bool
    notes: str | None


class SessionOut(BaseModel):
    id: uuid.UUID
    title: str
    experiment: str
    metadata: dict
    exercise: ExerciseInfo | None
    has_image: bool
    peaks: list[Peak]
    chem_state: dict
    assist_mode: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut]


class SessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    exercise_id: str | None
    updated_at: datetime


class ParsePeaksIn(BaseModel):
    text: str = Field(max_length=20000)


class ParseErrorOut(BaseModel):
    line: int
    message: str


class ParsePeaksOut(BaseModel):
    peaks: list[Peak]
    errors: list[ParseErrorOut]


class SpectrumOut(BaseModel):
    x: list[float]
    y: list[float]
    warnings: list[str]


class StructureCheckIn(BaseModel):
    smiles: str = Field(min_length=1, max_length=300)


def session_out(row: SessionRow, messages: list[MessageRow]) -> SessionOut:
    exercise = get_exercise(row.exercise_id) if row.exercise_id else None
    return SessionOut(
        id=row.id,
        title=row.title,
        experiment=row.experiment,
        metadata=row.meta or {},
        exercise=ExerciseInfo(id=exercise.id, title=exercise.title, reviewed=exercise.reviewed, notes=exercise.notes)
        if exercise
        else None,
        has_image=bool(row.image_blob) or exercise is not None,
        peaks=[Peak.model_validate(p) for p in row.peaks or []],
        chem_state=row.chem_state or {},
        assist_mode=row.assist_mode,
        created_at=as_aware(row.created_at),
        updated_at=as_aware(row.updated_at),
        messages=[
            MessageOut(seq=m.seq, role=m.role, text=m.display_text, mode=m.mode, created_at=as_aware(m.created_at))
            for m in messages
            if m.display_text is not None and m.role in ("user", "assistant")
        ],
    )
