from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

PPM_MIN = -2.0
PPM_MAX = 16.0
MAX_PEAKS = 200


class Multiplicity(StrEnum):
    s = "s"
    d = "d"
    t = "t"
    q = "q"
    quint = "quint"
    sext = "sext"
    sept = "sept"
    m = "m"
    dd = "dd"
    dt = "dt"
    td = "td"
    ddd = "ddd"
    br_s = "br_s"


class Experiment(StrEnum):
    H1 = "1H"
    C13 = "13C"
    DEPT = "DEPT"
    COSY = "COSY"
    HSQC = "HSQC"
    HMBC = "HMBC"


class Peak(BaseModel):
    id: str = Field(pattern=r"^P\d{1,3}$")
    ppm: float = Field(ge=PPM_MIN, le=PPM_MAX)
    integral: float | None = Field(default=None, gt=0, le=1000)
    multiplicity: Multiplicity | None = None
    j_hz: list[float] | None = None
    source: Literal["user", "exercise", "engine"] = "user"
    note: str | None = Field(default=None, max_length=200)

    @field_validator("j_hz")
    @classmethod
    def _check_j(cls, v: list[float] | None) -> list[float] | None:
        if v is None:
            return v
        if len(v) > 4:
            raise ValueError("no máximo 4 constantes J por pico")
        for j in v:
            if not (0 < j <= 30):
                raise ValueError("J deve estar entre 0 e 30 Hz")
        return v


class PeakList(BaseModel):
    peaks: list[Peak] = Field(default_factory=list, max_length=MAX_PEAKS)

    @model_validator(mode="after")
    def _unique_ids(self) -> "PeakList":
        ids = [p.id for p in self.peaks]
        if len(ids) != len(set(ids)):
            raise ValueError("IDs de pico duplicados")
        return self


def renumber(peaks: list[Peak]) -> list[Peak]:
    ordered = sorted(peaks, key=lambda p: -p.ppm)
    return [p.model_copy(update={"id": f"P{i + 1}"}) for i, p in enumerate(ordered)]
